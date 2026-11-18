from datetime import UTC, datetime, timedelta

from ingestion.scheduler import STARTUP_DELAY, first_run_time
from models import Market, MarketSnapshot

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)


def _snapshot(db, external_id, captured_at):
    market = Market(external_id=external_id, question="Q?", probability=0.5)
    db.add(market)
    db.flush()
    db.add(MarketSnapshot(market_id=market.id, probability=0.5, captured_at=captured_at))
    db.commit()


def test_runs_soon_on_empty_database(db):
    assert first_run_time(db, HOUR, NOW) == NOW + STARTUP_DELAY


def test_waits_out_the_interval_after_a_recent_run(db):
    _snapshot(db, "real-1", NOW - timedelta(minutes=20))
    assert first_run_time(db, HOUR, NOW) == NOW + timedelta(minutes=40)


def test_runs_soon_when_last_run_is_overdue(db):
    _snapshot(db, "real-1", NOW - 3 * HOUR)
    assert first_run_time(db, HOUR, NOW) == NOW + STARTUP_DELAY


def test_ignores_seeded_snapshots(db):
    _snapshot(db, "seed-1", NOW - timedelta(minutes=5))
    assert first_run_time(db, HOUR, NOW) == NOW + STARTUP_DELAY
