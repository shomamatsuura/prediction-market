import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import Settings
from database import SessionLocal
from ingestion.job import run_ingestion
from models import Market, MarketSnapshot

logger = logging.getLogger(__name__)

STARTUP_DELAY = timedelta(seconds=10)


def first_run_time(db: Session, interval: timedelta, now: datetime | None = None) -> datetime:
    """When the first ingestion run after startup should happen.

    Restarts (deploys, or every code change under `--reload`) must not add extra snapshots,
    so if the last real run was less than one interval ago, wait until that interval is up.
    Seeded sample data doesn't count as a run.
    """
    now = now or datetime.now(UTC)
    last = db.scalar(
        select(func.max(MarketSnapshot.captured_at))
        .join(Market, Market.id == MarketSnapshot.market_id)
        .where(Market.external_id.not_like("seed-%"))
    )
    if last is None:
        return now + STARTUP_DELAY
    if last.tzinfo is None:  # SQLite returns naive datetimes
        last = last.replace(tzinfo=UTC)
    return max(last + interval, now + STARTUP_DELAY)


def start_scheduler(settings: Settings) -> BackgroundScheduler:
    interval = timedelta(minutes=settings.ingestion_interval_minutes)
    try:
        with SessionLocal() as db:
            next_run = first_run_time(db, interval)
    except Exception:
        logger.exception("Could not read the last ingestion time; running soon")
        next_run = datetime.now(UTC) + STARTUP_DELAY

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_ingestion,
        "interval",
        minutes=settings.ingestion_interval_minutes,
        id="polymarket-ingestion",
        max_instances=1,
        coalesce=True,
        next_run_time=next_run,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: ingesting every %d minutes, next run at %s",
        settings.ingestion_interval_minutes,
        next_run.isoformat(timespec="seconds"),
    )
    return scheduler
