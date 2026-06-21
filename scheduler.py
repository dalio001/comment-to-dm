"""In-app daily scheduler for auto-arming campaigns.

Runs `run_auto_arm` once a day, a few minutes after the reels publish, so the
just-published reel is turned into an active campaign automatically.

NOTE: a background scheduler only fires while the process is actually running.
On a free Render web service that sleeps after ~15 min idle, this thread is not
running at the scheduled time. For free-tier reliability, trigger the same
`/api/campaigns/auto-arm` endpoint with a Render Cron Job (or upgrade to an
always-on instance). When the app is always-on or run locally, this fires natively.
"""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _job():
    # Import lazily so module import stays cheap and avoids circular imports.
    from database import SessionLocal
    from routes.api import run_auto_arm

    db = SessionLocal()
    try:
        result = run_auto_arm(db)
        logger.info("Auto-arm run: armed=%s skipped=%s", result.get("armed"), len(result.get("skipped", [])))
    except Exception:  # noqa: BLE001 — never let a scheduled run crash the worker
        logger.exception("Auto-arm scheduled run failed")
    finally:
        db.close()


def start_scheduler():
    """Start the daily auto-arm job. Controlled by env:
    AUTO_ARM_ENABLED (default 1), AUTO_ARM_HOUR (default 0), AUTO_ARM_MINUTE
    (default 20), AUTO_ARM_TZ (default Europe/Berlin).
    """
    global _scheduler
    if os.getenv("AUTO_ARM_ENABLED", "1") not in ("1", "true", "True"):
        logger.info("Auto-arm scheduler disabled via AUTO_ARM_ENABLED")
        return
    if _scheduler is not None:
        return

    hour = int(os.getenv("AUTO_ARM_HOUR", "0"))
    minute = int(os.getenv("AUTO_ARM_MINUTE", "20"))
    tz = os.getenv("AUTO_ARM_TZ", "Europe/Berlin")

    _scheduler = BackgroundScheduler(timezone=tz)
    _scheduler.add_job(
        _job,
        CronTrigger(hour=hour, minute=minute, timezone=tz),
        id="daily_auto_arm",
        replace_existing=True,
        misfire_grace_time=3600,  # if the worker was briefly down, still run within the hour
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Auto-arm scheduler started: daily at %02d:%02d %s", hour, minute, tz)
