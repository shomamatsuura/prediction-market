"""Load sample markets and 7 days of hourly snapshots so the UI isn't empty.

Seeded markets use external IDs prefixed with "seed-". Refuses to run in production.
"""

import math
import random
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from config import get_settings
from database import SessionLocal
from models import Market, MarketSnapshot

SAMPLES = [
    ("Will the Fed cut interest rates at its next meeting?", "economics", 0.62),
    ("Will Bitcoin close above $150k by year end?", "crypto", 0.31),
    ("Will a new Marvel film top the box office this month?", "culture", 0.74),
    ("Will the incumbent win the next national election?", "politics", 0.48),
    ("Will SpaceX reach orbit with Starship this quarter?", "science", 0.57),
    ("Will the home team win the championship series?", "sports", 0.41),
    ("Will global average temperature set a new monthly record?", "science", 0.68),
    ("Will Ethereum ETF inflows exceed $1B this week?", "crypto", 0.22),
    ("Will a major AI lab release a new frontier model this month?", "tech", 0.83),
    ("Will unemployment rise above 4.5% in the next report?", "economics", 0.27),
    ("Will the trade deal be signed before the deadline?", "politics", 0.35),
    ("Will the top seed reach the tennis final?", "sports", 0.59),
]


def seed() -> None:
    if get_settings().is_production:
        sys.exit("Refusing to seed sample data in production.")
    rng = random.Random(42)
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    hours = 24 * 7
    with SessionLocal() as db:
        for i, (question, category, start) in enumerate(SAMPLES):
            external_id = f"seed-{i + 1}"
            if db.scalar(select(Market).where(Market.external_id == external_id)):
                continue
            # A smooth random walk, with one late swing so the movers board has content.
            p = start
            drift = rng.uniform(-0.002, 0.002)
            series = []
            for h in range(hours):
                p += drift + rng.gauss(0, 0.008) + 0.01 * math.sin(h / 17 + i)
                if h > hours - 24 and i % 3 == 0:
                    p += 0.006 if i % 2 == 0 else -0.006
                p = min(max(p, 0.02), 0.98)
                series.append(round(p, 4))
            volume = round(rng.uniform(50_000, 5_000_000), 2)
            market = Market(
                external_id=external_id,
                question=question,
                slug=None,  # no real Polymarket page to link to
                description="Sample market created by seed.py for local development.",
                category=category,
                end_date=now + timedelta(days=rng.randint(7, 120)),
                probability=series[-1],
                volume=volume,
                liquidity=round(volume * rng.uniform(0.02, 0.1), 2),
                active=True,
                created_at=now - timedelta(hours=hours),
                updated_at=now,
            )
            db.add(market)
            db.flush()
            db.add_all(
                MarketSnapshot(
                    market_id=market.id,
                    probability=prob,
                    volume=volume,
                    captured_at=now - timedelta(hours=hours - 1 - h),
                )
                for h, prob in enumerate(series)
            )
        db.commit()
    print(f"Seeded {len(SAMPLES)} sample markets.")


if __name__ == "__main__":
    seed()
