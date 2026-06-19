"""Webhook endpoints for Instagram and Facebook.

Meta delivers comment events here. Each platform gets its own callback URL so you
can point the "instagram" and "page" webhook subscriptions independently, but both
share verification, signature validation, keyword matching, and dedup.
"""
import hashlib
import hmac
import json
import logging
import os

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

import facebook
import instagram
from database import get_db
from models import Campaign, Config, ProcessedComment

logger = logging.getLogger("webhook")
router = APIRouter()

VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "")
APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def verify_signature(payload: bytes, header: str) -> bool:
    """Validate X-Hub-Signature-256 against the app secret."""
    if not APP_SECRET:
        logger.warning("FACEBOOK_APP_SECRET not set — skipping signature validation (DEV ONLY)")
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(APP_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def handle_verify(request: Request) -> Response:
    """Answer Meta's GET verification challenge."""
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(content="Verification failed", status_code=403)


def keyword_match(text: str, keywords_csv: str) -> bool:
    """Case-insensitive partial match against any comma-separated keyword."""
    text_l = (text or "").lower()
    keywords = [k.strip().lower() for k in (keywords_csv or "").split(",") if k.strip()]
    return any(kw in text_l for kw in keywords) if keywords else False


def _already_processed(db: Session, comment_id: str) -> bool:
    return db.query(ProcessedComment).filter_by(comment_id=comment_id).first() is not None


def _mark_processed(db: Session, comment_id: str, platform: str) -> None:
    db.add(ProcessedComment(comment_id=comment_id, platform=platform))
    db.commit()


def process_comment(db, platform, post_id, comment_id, text, cfg):
    """Match a comment against active campaigns and fire reply + DM exactly once."""
    if not comment_id:
        return
    if _already_processed(db, comment_id):
        logger.info("Skip already-processed %s comment %s", platform, comment_id)
        return

    campaigns = (
        db.query(Campaign)
        .filter_by(platform=platform, post_id=str(post_id), active=True)
        .all()
    )
    matched = next((c for c in campaigns if keyword_match(text, c.keywords)), None)
    if not matched:
        return

    try:
        if platform == "facebook":
            token = cfg.facebook_page_access_token
            if matched.comment_reply:
                facebook.reply_to_comment(comment_id, matched.comment_reply, token)
            if matched.dm_message:
                facebook.send_dm(comment_id, matched.dm_message, token)
        else:  # instagram
            token = cfg.instagram_access_token
            if matched.comment_reply:
                instagram.reply_to_comment(comment_id, matched.comment_reply, token)
            if matched.dm_message:
                instagram.send_dm(comment_id, matched.dm_message, cfg.instagram_business_account_id, token)

        # Mark processed only after a successful run so transient failures can retry
        # on the next webhook delivery (Meta re-delivers unacked events).
        _mark_processed(db, comment_id, platform)
        logger.info("Fired %s campaign %s on comment %s", platform, matched.id, comment_id)
    except Exception as exc:  # noqa: BLE001 — never let one bad comment kill the webhook
        logger.exception("Failed to process %s comment %s: %s", platform, comment_id, exc)


# --------------------------------------------------------------------------- #
# Instagram
# --------------------------------------------------------------------------- #
@router.get("/webhook/instagram")
async def instagram_verify(request: Request):
    return handle_verify(request)


@router.post("/webhook/instagram")
async def instagram_receive(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    if not verify_signature(raw, request.headers.get("X-Hub-Signature-256", "")):
        logger.warning("Instagram webhook: bad signature")
        return Response(status_code=403)

    data = json.loads(raw or b"{}")
    cfg = db.query(Config).first()
    if not cfg:
        logger.warning("No Config saved — ignoring webhook")
        return {"status": "no-config"}

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "comments":
                continue
            value = change.get("value", {})
            from_id = (value.get("from") or {}).get("id")
            # Ignore the business's own replies to avoid reply loops.
            if from_id and from_id == cfg.instagram_business_account_id:
                continue
            media = value.get("media") or {}
            process_comment(
                db,
                "instagram",
                media.get("id"),
                value.get("id"),
                value.get("text", ""),
                cfg,
            )
    return {"status": "received"}


# --------------------------------------------------------------------------- #
# Facebook
# --------------------------------------------------------------------------- #
@router.get("/webhook/facebook")
async def facebook_verify(request: Request):
    return handle_verify(request)


@router.post("/webhook/facebook")
async def facebook_receive(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    if not verify_signature(raw, request.headers.get("X-Hub-Signature-256", "")):
        logger.warning("Facebook webhook: bad signature")
        return Response(status_code=403)

    data = json.loads(raw or b"{}")
    cfg = db.query(Config).first()
    if not cfg:
        logger.warning("No Config saved — ignoring webhook")
        return {"status": "no-config"}

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "feed":
                continue
            value = change.get("value", {})
            # Only new comments, not likes / posts / edits.
            if value.get("item") != "comment" or value.get("verb") != "add":
                continue
            from_id = (value.get("from") or {}).get("id")
            # Ignore the Page's own comments to avoid reply loops.
            if from_id and from_id == cfg.facebook_page_id:
                continue
            process_comment(
                db,
                "facebook",
                value.get("post_id"),
                value.get("comment_id"),
                value.get("message", ""),
                cfg,
            )
    return {"status": "received"}
