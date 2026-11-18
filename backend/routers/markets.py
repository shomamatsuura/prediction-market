from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from database import get_db
from models import Market, MarketSnapshot
from schemas import (
    CategoryOut,
    MarketDetailOut,
    MarketOut,
    MarketPage,
    MoverOut,
    PathId,
    SnapshotOut,
)

router = APIRouter(prefix="/markets", tags=["markets"])

SORTS = {
    "volume": Market.volume.desc(),
    "liquidity": Market.liquidity.desc(),
    "probability": Market.probability.desc(),
    "ending": Market.end_date.asc(),
    "updated": Market.updated_at.desc(),
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=MarketPage)
def list_markets(
    db: Session = Depends(get_db),
    category: str | None = Query(None, max_length=64, pattern=r"^[A-Za-z0-9 &\-]+$"),
    q: str | None = Query(None, min_length=1, max_length=100),
    active: bool | None = Query(True),
    sort: Literal["volume", "liquidity", "probability", "ending", "updated"] = "volume",
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10_000),
) -> MarketPage:
    stmt = select(Market)
    if category:
        stmt = stmt.where(func.lower(Market.category) == category.lower())
    if active is not None:
        stmt = stmt.where(Market.active == active)
    if q:
        pattern = f"%{_escape_like(q.strip().lower())}%"
        stmt = stmt.where(
            or_(
                func.lower(Market.question).like(pattern, escape="\\"),
                func.lower(Market.category).like(pattern, escape="\\"),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(SORTS[sort], Market.id).limit(limit).offset(offset)).all()
    return MarketPage(
        items=[MarketOut.model_validate(m) for m in rows], total=total, limit=limit, offset=offset
    )


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    rows = db.execute(
        select(Market.category, func.count())
        .where(Market.active.is_(True))
        .group_by(Market.category)
        .order_by(func.count().desc())
        .limit(50)
    ).all()
    return [CategoryOut(category=c, count=n) for c, n in rows]


@router.get("/movers", response_model=list[MoverOut])
def biggest_movers(
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=24 * 30),
    limit: int = Query(10, ge=1, le=50),
    direction: Literal["any", "up", "down"] = "any",
) -> list[MoverOut]:
    """Markets with the largest probability change over the last `hours`.

    The baseline is each market's earliest snapshot inside the window.
    """
    since = datetime.now(UTC) - timedelta(hours=hours)
    first_in_window = (
        select(MarketSnapshot.market_id, func.min(MarketSnapshot.captured_at).label("first_at"))
        .where(MarketSnapshot.captured_at >= since)
        .group_by(MarketSnapshot.market_id)
        .subquery()
    )
    baseline = (
        select(MarketSnapshot.market_id, func.min(MarketSnapshot.probability).label("prob"))
        .join(
            first_in_window,
            (MarketSnapshot.market_id == first_in_window.c.market_id)
            & (MarketSnapshot.captured_at == first_in_window.c.first_at),
        )
        .group_by(MarketSnapshot.market_id)
        .subquery()
    )
    change = (Market.probability - baseline.c.prob).label("change")
    stmt = (
        select(Market, baseline.c.prob, change)
        .join(baseline, baseline.c.market_id == Market.id)
        .where(Market.active.is_(True))
    )
    if direction == "up":
        stmt = stmt.where(change > 0).order_by(change.desc())
    elif direction == "down":
        stmt = stmt.where(change < 0).order_by(change.asc())
    else:
        stmt = stmt.where(change != 0).order_by(func.abs(change).desc())
    rows = db.execute(stmt.order_by(Market.id).limit(limit)).all()
    return [
        MoverOut(market=MarketOut.model_validate(m), previous_probability=prev, change=round(ch, 6))
        for m, prev, ch in rows
    ]


def _get_market(db: Session, market_id: int) -> Market:
    market = db.get(Market, market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Market not found")
    return market


@router.get("/{market_id}", response_model=MarketDetailOut)
def get_market(market_id: PathId, db: Session = Depends(get_db)) -> Market:
    return _get_market(db, market_id)


@router.get("/{market_id}/snapshots", response_model=list[SnapshotOut])
def get_snapshots(
    market_id: PathId,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
) -> list[MarketSnapshot]:
    _get_market(db, market_id)
    since = datetime.now(UTC) - timedelta(days=days)
    return db.scalars(
        select(MarketSnapshot)
        .where(MarketSnapshot.market_id == market_id, MarketSnapshot.captured_at >= since)
        .order_by(MarketSnapshot.captured_at)
        .limit(5000)
    ).all()
