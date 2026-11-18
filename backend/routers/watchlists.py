"""Per-user watchlists. Every query is scoped to the authenticated user.

A watchlist that belongs to someone else is reported as 404, so its existence isn't leaked.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from auth import get_current_user
from database import get_db
from models import Market, User, Watchlist, WatchlistItem
from schemas import WatchlistCreate, WatchlistItemCreate, WatchlistOut

router = APIRouter(prefix="/watchlists", tags=["watchlists"])

MAX_WATCHLISTS_PER_USER = 20
MAX_ITEMS_PER_WATCHLIST = 200


def _load_owned(db: Session, user: User, watchlist_id: int) -> Watchlist:
    watchlist = db.scalar(
        select(Watchlist)
        .where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id)
        .options(selectinload(Watchlist.items).selectinload(WatchlistItem.market))
    )
    if watchlist is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return watchlist


@router.get("", response_model=list[WatchlistOut])
def list_watchlists(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Watchlist]:
    return db.scalars(
        select(Watchlist)
        .where(Watchlist.user_id == user.id)
        .options(selectinload(Watchlist.items).selectinload(WatchlistItem.market))
        .order_by(Watchlist.created_at, Watchlist.id)
    ).all()


@router.post("", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
def create_watchlist(
    body: WatchlistCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Watchlist:
    count = db.scalar(select(func.count()).where(Watchlist.user_id == user.id)) or 0
    if count >= MAX_WATCHLISTS_PER_USER:
        raise HTTPException(status_code=409, detail="Watchlist limit reached")
    watchlist = Watchlist(user_id=user.id, name=body.name)
    db.add(watchlist)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A watchlist with that name already exists")
    return _load_owned(db, user, watchlist.id)


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(
    watchlist_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    watchlist = _load_owned(db, user, watchlist_id)
    db.delete(watchlist)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{watchlist_id}/items", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED
)
def add_item(
    watchlist_id: int,
    body: WatchlistItemCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Watchlist:
    watchlist = _load_owned(db, user, watchlist_id)
    if db.get(Market, body.market_id) is None:
        raise HTTPException(status_code=404, detail="Market not found")
    if any(item.market_id == body.market_id for item in watchlist.items):
        return watchlist  # idempotent
    if len(watchlist.items) >= MAX_ITEMS_PER_WATCHLIST:
        raise HTTPException(status_code=409, detail="Watchlist is full")
    db.add(WatchlistItem(watchlist_id=watchlist.id, market_id=body.market_id))
    try:
        db.commit()
    except IntegrityError:  # added concurrently
        db.rollback()
    db.expire_all()
    return _load_owned(db, user, watchlist_id)


@router.delete("/{watchlist_id}/items/{market_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    watchlist_id: int,
    market_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    watchlist = _load_owned(db, user, watchlist_id)
    item = next((i for i in watchlist.items if i.market_id == market_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Market is not in this watchlist")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
