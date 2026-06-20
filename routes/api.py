"""REST API for the dashboard: config, campaigns, and live post preview."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import facebook
import instagram
from database import get_db
from models import PLATFORMS, Campaign, Config

logger = logging.getLogger("api")
router = APIRouter(prefix="/api")


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
