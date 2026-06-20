"""SQLAlchemy models.

Config       — singleton row holding IG + FB credentials.
Campaign     — one tracked post + keywords + reply/DM text, per platform.
ProcessedComment — dedup table so a comment never fires twice.
PendingFollowup  — a user who got the first DM and owes a reply; when they
                   answer, we send the campaign's follow-up (the actual link).
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from database import Base

PLATFORMS = ("instagram", "facebook")


class Config(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True)
    # Instagram (Graph API via linked Facebook Page)
    instagram_access_token = Column(Text, default="")
    instagram_business_account_id = Column(String(64), default="")
    # Facebook Page
    facebook_page_id = Column(String(64), default="")
    facebook_page_access_token = Column(Text, default="")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    platform = Column(String(16), default="instagram")  # instagram | facebook
    name = Column(String(120), default="")
    post_id = Column(String(128), index=True)
    keywords = Column(Text, default="")  # comma-separated, matched case-insensitive/partial
    comment_reply = Column(Text, default="")
    dm_message = Column(Text, default="")
    # Optional second step: if set, dm_message asks the user to reply, and this
    # follow-up (e.g. the actual link) is sent once they answer. Replying moves
    # the thread into their main inbox, escaping the Message Requests folder.
    followup_message = Column(Text, default="")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "platform": self.platform,
            "name": self.name,
            "post_id": self.post_id,
            "keywords": self.keywords,
            "comment_reply": self.comment_reply,
            "dm_message": self.dm_message,
            "followup_message": self.followup_message,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProcessedComment(Base):
    __tablename__ = "processed_comments"

    id = Column(Integer, primary_key=True)
    comment_id = Column(String(128), unique=True, index=True)
    platform = Column(String(16))
    created_at = Column(DateTime, default=datetime.utcnow)


class PendingFollowup(Base):
    """One open follow-up per (platform, user). Created when the first DM goes
    out; consumed (deleted) when the user replies and we send the follow-up."""
    __tablename__ = "pending_followups"

    id = Column(Integer, primary_key=True)
    platform = Column(String(16), index=True)
    user_id = Column(String(128), index=True)  # PSID (FB) / IGSID (IG) of the commenter
    campaign_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
