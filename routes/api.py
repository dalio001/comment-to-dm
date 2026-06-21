"""REST API for the dashboard: config, campaigns, and live post preview."""
import json
import logging
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import facebook
import instagram
from database import get_db
from models import PLATFORMS, Campaign, Config

logger = logging.getLogger("api")
router = APIRouter(prefix="/api")

# Auto-arm pulls its campaign templates from this file (one per reel/keyword).
QUEUE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "campaign_queue.json")


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
class ConfigIn(BaseModel):
    instagram_access_token: str = ""
    instagram_business_account_id: str = ""
    facebook_page_id: str = ""
    facebook_page_access_token: str = ""


def _get_or_create_config(db: Session) -> Config:
    cfg = db.query(Config).first()
    if not cfg:
        cfg = Config()
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _mask(value: str) -> str:
    if not value:
        return ""
    return f"{value[:6]}…{value[-4:]}" if len(value) > 12 else "••••"


@router.get("/config")
def read_config(db: Session = Depends(get_db)):
    cfg = _get_or_create_config(db)
    return {
        "instagram_access_token_masked": _mask(cfg.instagram_access_token),
        "instagram_access_token_set": bool(cfg.instagram_access_token),
        "instagram_business_account_id": cfg.instagram_business_account_id,
        "facebook_page_id": cfg.facebook_page_id,
        "facebook_page_access_token_masked": _mask(cfg.facebook_page_access_token),
        "facebook_page_access_token_set": bool(cfg.facebook_page_access_token),
    }


@router.post("/config")
def save_config(data: ConfigIn, db: Session = Depends(get_db)):
    cfg = _get_or_create_config(db)
    # IDs always overwrite; tokens only overwrite when a new value is supplied,
    # so a blank token field on save doesn't wipe the stored secret.
    cfg.instagram_business_account_id = data.instagram_business_account_id.strip()
    cfg.facebook_page_id = data.facebook_page_id.strip()
    if data.instagram_access_token.strip():
        cfg.instagram_access_token = data.instagram_access_token.strip()
    if data.facebook_page_access_token.strip():
        cfg.facebook_page_access_token = data.facebook_page_access_token.strip()
    db.commit()
    return {"status": "saved"}


# --------------------------------------------------------------------------- #
# Campaigns
# --------------------------------------------------------------------------- #
class CampaignIn(BaseModel):
    platform: str = "instagram"
    name: str = ""
    post_id: str
    keywords: str = ""
    comment_reply: str = ""
    dm_message: str = ""
    followup_message: str = ""
    active: bool = True


def _validate_platform(platform: str):
    if platform not in PLATFORMS:
        raise HTTPException(status_code=400, detail=f"platform must be one of {PLATFORMS}")


@router.get("/campaigns")
def list_campaigns(db: Session = Depends(get_db)):
    rows = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return [c.to_dict() for c in rows]


@router.post("/campaigns")
def create_campaign(data: CampaignIn, db: Session = Depends(get_db)):
    _validate_platform(data.platform)
    if not data.post_id.strip():
        raise HTTPException(status_code=400, detail="post_id is required")
    campaign = Campaign(
        platform=data.platform,
        name=data.name.strip(),
        post_id=data.post_id.strip(),
        keywords=data.keywords.strip(),
        comment_reply=data.comment_reply,
        dm_message=data.dm_message,
        followup_message=data.followup_message,
        active=data.active,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign.to_dict()


@router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, data: CampaignIn, db: Session = Depends(get_db)):
    _validate_platform(data.platform)
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="campaign not found")
    campaign.platform = data.platform
    campaign.name = data.name.strip()
    campaign.post_id = data.post_id.strip()
    campaign.keywords = data.keywords.strip()
    campaign.comment_reply = data.comment_reply
    campaign.dm_message = data.dm_message
    campaign.followup_message = data.followup_message
    campaign.active = data.active
    db.commit()
    db.refresh(campaign)
    return campaign.to_dict()


@router.post("/campaigns/{campaign_id}/toggle")
def toggle_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="campaign not found")
    campaign.active = not campaign.active
    db.commit()
    return {"id": campaign.id, "active": campaign.active}


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="campaign not found")
    db.delete(campaign)
    db.commit()
    return {"status": "deleted"}


# --------------------------------------------------------------------------- #
# Auto-arm: turn a just-published reel into an active campaign
# --------------------------------------------------------------------------- #
class AutoArmIn(BaseModel):
    # Optional inline queue; when omitted, campaign_queue.json is used.
    queue: list[dict] | None = None
    limit: int = 15
    # Only consider posts published within this many hours (the reel is minutes
    # old when the nightly job runs). None -> default DEFAULT_MAX_AGE_HOURS.
    max_age_hours: float | None = None


DEFAULT_MAX_AGE_HOURS = 12.0


def _load_queue():
    if not os.path.exists(QUEUE_PATH):
        return []
    with open(QUEUE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _keyword_in_caption(keyword: str, caption: str) -> bool:
    """Case-SENSITIVE whole-word match.

    The brand always writes the CTA word in caps ("Comment SHELF", "Leave the
    word FLOCK"), while body prose uses lowercase ("runs through your own two
    hands"). Matching case-sensitively means the keyword only fires on the
    intended uppercase call-to-action, never on an incidental lowercase word.
    """
    if not keyword or not caption:
        return False
    return re.search(rf"\b{re.escape(keyword)}\b", caption) is not None


def _too_old(timestamp: str, max_age_hours: float) -> bool:
    """True if a post is older than the window. The just-published reel is only
    minutes old when the nightly job runs, so anything older isn't our target —
    this stops a stale post that happens to contain the word from matching."""
    if not timestamp or not max_age_hours:
        return False
    dt = None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            dt = datetime.strptime(timestamp, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        try:
            dt = datetime.fromisoformat(timestamp)
        except ValueError:
            return False  # unparseable -> don't exclude on age
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    return age_hours > max_age_hours


def run_auto_arm(db: Session, queue=None, limit: int = 15, max_age_hours: float = DEFAULT_MAX_AGE_HOURS):
    """Core auto-arm logic, callable from the HTTP endpoint or the in-app scheduler.

    Matches each queued keyword to a recently-published post and activates its campaign.
    Idempotent: a post that already has a campaign is skipped, so re-runs are safe.
    Only matches the uppercase CTA word on a post published within max_age_hours.
    """
    cfg = _get_or_create_config(db)
    if queue is None:
        queue = _load_queue()
    if not queue:
        return {"armed": [], "skipped": [], "note": "campaign queue is empty"}

    media_cache: dict[str, list] = {}

    def media_for(platform: str):
        if platform in media_cache:
            return media_cache[platform]
        if platform == "facebook":
            if not (cfg.facebook_page_id and cfg.facebook_page_access_token):
                raise HTTPException(status_code=400, detail="Facebook not configured in Settings")
            items = facebook.list_recent_media(cfg.facebook_page_id, cfg.facebook_page_access_token, limit)
        else:
            if not (cfg.instagram_business_account_id and cfg.instagram_access_token):
                raise HTTPException(status_code=400, detail="Instagram not configured in Settings")
            items = instagram.list_recent_media(cfg.instagram_business_account_id, cfg.instagram_access_token, limit)
        media_cache[platform] = items
        return items

    armed, skipped = [], []
    for tpl in queue:
        keyword = (tpl.get("keyword") or "").strip()
        platform = tpl.get("platform", "instagram")
        label = tpl.get("name") or keyword
        if platform not in PLATFORMS:
            skipped.append({"name": label, "reason": f"platform must be one of {PLATFORMS}"})
            continue
        if not keyword:
            skipped.append({"name": label, "reason": "template has no keyword"})
            continue
        try:
            items = media_for(platform)
        except HTTPException as exc:
            skipped.append({"name": label, "reason": exc.detail})
            continue
        # Newest matching post wins (Meta returns recent-first): the uppercase
        # CTA word must appear in a post published within the recency window.
        match = next(
            (m for m in items
             if _keyword_in_caption(keyword, m["caption"]) and not _too_old(m.get("timestamp"), max_age_hours)),
            None,
        )
        if not match:
            skipped.append({"name": label, "keyword": keyword, "reason": "no recent published post carries this CTA word yet"})
            continue
        if db.query(Campaign).filter(Campaign.post_id == match["id"]).first():
            skipped.append({"name": label, "keyword": keyword, "post_id": match["id"], "reason": "already armed"})
            continue
        campaign = Campaign(
            platform=platform,
            name=label,
            post_id=match["id"],
            keywords=keyword,
            comment_reply=tpl.get("comment_reply", ""),
            dm_message=tpl.get("dm_message", ""),
            followup_message=tpl.get("followup_message", ""),
            active=True,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        logger.info("Auto-armed campaign %s (%s) on post %s", campaign.id, keyword, match["id"])
        armed.append({"name": label, "keyword": keyword, "post_id": match["id"], "campaign_id": campaign.id})

    return {"armed": armed, "skipped": skipped}


@router.post("/campaigns/auto-arm")
def auto_arm(data: AutoArmIn = Body(default=AutoArmIn()), db: Session = Depends(get_db)):
    """HTTP entry point for auto-arm (cron / Render Cron Job / manual trigger)."""
    max_age = data.max_age_hours if data.max_age_hours is not None else DEFAULT_MAX_AGE_HOURS
    return run_auto_arm(db, queue=data.queue, limit=data.limit, max_age_hours=max_age)


# --------------------------------------------------------------------------- #
# Live post preview (used by the Add Campaign form on blur)
# --------------------------------------------------------------------------- #
@router.get("/post-preview")
def post_preview(platform: str, post_id: str, db: Session = Depends(get_db)):
    _validate_platform(platform)
    cfg = _get_or_create_config(db)
    try:
        if platform == "facebook":
            if not cfg.facebook_page_access_token:
                raise HTTPException(status_code=400, detail="Facebook token not configured in Settings")
            return facebook.get_post_details(post_id, cfg.facebook_page_access_token)
        if not cfg.instagram_access_token:
            raise HTTPException(status_code=400, detail="Instagram token not configured in Settings")
        return instagram.get_post_details(post_id, cfg.instagram_access_token)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
