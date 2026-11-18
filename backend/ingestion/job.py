"""The ingestion job: upsert markets and record one snapshot per market per run."""

import logging
import threading
import time
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from config import Settings, get_settings
from database import SessionLocal, engine
from ingestion.polymarket import ParsedMarket, PolymarketClient
from models import Market, MarketSnapshot

logger = logging.getLogger(__name__)

_ADVISORY_LOCK_ID = 727_001  # arbitrary, app-specific
_local_lock = threading.Lock()


def store_markets(db: Session, markets: Iterable[ParsedMarket], now: datetime | None = None) -> int:
    """Upsert markets and insert a snapshot for each. Returns the number stored."""
    now = now or datetime.now(UTC)
    markets = list(markets)
    if not markets:
        return 0
    existing = {
        m.external_id: m
        for m in db.scalars(
            select(Market).where(Market.external_id.in_([p.external_id for p in markets]))
        )
    }
    for parsed in markets:
        market = existing.get(parsed.external_id)
        if market is None:
            market = Market(external_id=parsed.external_id, created_at=now)
            db.add(market)
        market.question = parsed.question
        market.slug = parsed.slug
        market.description = parsed.description
        market.category = parsed.category
        market.image_url = parsed.image_url
        market.end_date = parsed.end_date
        market.probability = parsed.probability
        market.volume = parsed.volume
        market.liquidity = parsed.liquidity
        market.active = parsed.active
        market.updated_at = now
        db.flush()
        db.add(
            MarketSnapshot(
                market_id=market.id,
                probability=parsed.probability,
                volume=parsed.volume,
                captured_at=now,
            )
        )
    # Markets that dropped out of the active feed are no longer active.
    seen = [p.external_id for p in markets]
    db.execute(
        update(Market)
        .where(Market.active.is_(True), Market.external_id.not_in(seen))
        .values(active=False)
    )
    db.commit()
    return len(markets)


@contextmanager
def _db_lock():
    """Prevent overlapping runs across processes with a PostgreSQL advisory lock.

    The lock is held on a dedicated connection for the whole run, because session-level
    advisory locks belong to the connection that took them.
    """
    if engine.dialect.name != "postgresql":
        yield True
        return
    with engine.connect() as conn:
        acquired = bool(
            conn.scalar(text("SELECT pg_try_advisory_lock(:id)"), {"id": _ADVISORY_LOCK_ID})
        )
        try:
            yield acquired
        finally:
            if acquired:
                conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": _ADVISORY_LOCK_ID})
            conn.rollback()


def run_ingestion(settings: Settings | None = None, client: PolymarketClient | None = None) -> int:
    """Run one ingestion cycle. Never raises: errors are logged so the scheduler keeps going."""
    settings = settings or get_settings()
    if not _local_lock.acquire(blocking=False):
        logger.warning("Ingestion already running in this process; skipping")
        return 0
    started = time.monotonic()
    own_client = client is None
    try:
        with _db_lock() as acquired:
            if not acquired:
                logger.warning("Ingestion already running elsewhere; skipping")
                return 0
            client = client or PolymarketClient(settings.polymarket_api_url)
            markets = client.fetch_active_markets(
                page_size=settings.ingestion_page_size, max_pages=settings.ingestion_max_pages
            )
            if not markets:
                logger.warning("Ingestion fetched no usable markets; nothing stored")
                return 0
            with SessionLocal() as db:
                stored = store_markets(db, markets)
            logger.info("Ingestion stored %d markets in %.1fs", stored, time.monotonic() - started)
            return stored
    except Exception:
        logger.exception("Ingestion run failed")
        return 0
    finally:
        if own_client and client is not None:
            client.close()
        _local_lock.release()
