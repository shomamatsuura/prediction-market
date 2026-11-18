from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MarketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    slug: str | None
    category: str
    image_url: str | None
    end_date: datetime | None
    probability: float
    volume: float
    liquidity: float
    active: bool
    updated_at: datetime


class MarketDetailOut(MarketOut):
    description: str | None


class MarketPage(BaseModel):
    items: list[MarketOut]
    total: int
    limit: int
    offset: int


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    probability: float
    volume: float
    captured_at: datetime


class MoverOut(BaseModel):
    market: MarketOut
    previous_probability: float
    change: float


class CategoryOut(BaseModel):
    category: str
    count: int


class WatchlistCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("name must not be blank")
        return v


class WatchlistItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_id: int = Field(gt=0)


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market: MarketOut
    added_at: datetime


class WatchlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    items: list[WatchlistItemOut]
