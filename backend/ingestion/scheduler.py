import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from config import Settings
from ingestion.job import run_ingestion

logger = logging.getLogger(__name__)


def start_scheduler(settings: Settings) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_ingestion,
        "interval",
        minutes=settings.ingestion_interval_minutes,
        id="polymarket-ingestion",
        max_instances=1,
        coalesce=True,
        # First run shortly after startup so a fresh deploy has data quickly.
        next_run_time=datetime.now(UTC) + timedelta(seconds=10),
    )
    scheduler.start()
    logger.info(
        "Scheduler started: ingesting every %d minutes", settings.ingestion_interval_minutes
    )
    return scheduler
