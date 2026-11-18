"""Client for Polymarket's public Gamma API.

Everything coming back from the API is treated as untrusted input: each market is validated
and normalized, and malformed entries are skipped instead of failing the whole run.
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class ParsedMarket:
    external_id: str
    question: str
    slug: str | None
    description: str | None
    category: str
    image_url: str | None
    end_date: datetime | None
    probability: float
    volume: float
    liquidity: float
    active: bool


def _clean_text(value, max_len: int) -> str | None:
    if not isinstance(value, str):
        return None
    value = "".join(ch for ch in value if ch.isprintable() or ch in "\n\t").strip()
    return value[:max_len] or None


def _to_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):  # NaN / inf
        return None
    return number


def _json_list(value) -> list | None:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return None
        return parsed if isinstance(parsed, list) else None
    return None


def _safe_image(value) -> str | None:
    url = _clean_text(value, 500)
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return url


def _parse_date(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _category(raw: dict) -> str:
    category = _clean_text(raw.get("category"), 64)
    if not category:
        events = raw.get("events")
        if isinstance(events, list) and events and isinstance(events[0], dict):
            category = _clean_text(events[0].get("category"), 64)
    if not category:
        return "other"
    return category.lower()


def parse_market(raw) -> ParsedMarket | None:
    """Return a normalized market, or None if the entry is unusable."""
    if not isinstance(raw, dict):
        return None
    external_id = _clean_text(str(raw.get("id", "")), 64)
    question = _clean_text(raw.get("question"), 500)
    if not external_id or not question:
        return None

    outcomes = _json_list(raw.get("outcomes")) or []
    prices = _json_list(raw.get("outcomePrices")) or []
    if not prices:
        return None
    # Binary markets: probability of the "Yes" outcome (first outcome otherwise).
    index = 0
    for i, outcome in enumerate(outcomes):
        if isinstance(outcome, str) and outcome.strip().lower() == "yes":
            index = i
            break
    if index >= len(prices):
        return None
    probability = _to_float(prices[index])
    if probability is None or not 0.0 <= probability <= 1.0:
        return None

    volume = _to_float(raw.get("volumeNum", raw.get("volume"))) or 0.0
    liquidity = _to_float(raw.get("liquidityNum", raw.get("liquidity"))) or 0.0
    return ParsedMarket(
        external_id=external_id,
        question=question,
        slug=_clean_text(raw.get("slug"), 300),
        description=_clean_text(raw.get("description"), 5000),
        category=_category(raw),
        image_url=_safe_image(raw.get("image") or raw.get("icon")),
        end_date=_parse_date(raw.get("endDate")),
        probability=round(probability, 6),
        volume=max(volume, 0.0),
        liquidity=max(liquidity, 0.0),
        active=bool(raw.get("active", True)) and not bool(raw.get("closed", False)),
    )


class PolymarketClient:
    def __init__(self, base_url: str, client: httpx.Client | None = None):
        parsed = urlparse(base_url)
        if parsed.scheme != "https":
            raise ValueError("Polymarket API URL must use https")
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(
            timeout=_TIMEOUT,
            follow_redirects=False,
            headers={"User-Agent": "prediction-market-analytics/1.0", "Accept": "application/json"},
        )

    def fetch_page(self, limit: int, offset: int) -> list:
        response = self._client.get(
            f"{self.base_url}/markets",
            params={
                "active": "true",
                "closed": "false",
                "limit": limit,
                "offset": offset,
                "order": "volume24hr",
                "ascending": "false",
            },
        )
        response.raise_for_status()
        if len(response.content) > _MAX_RESPONSE_BYTES:
            raise ValueError("Polymarket response too large")
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Unexpected Polymarket response shape")
        return data

    def fetch_active_markets(self, page_size: int, max_pages: int) -> list[ParsedMarket]:
        markets: dict[str, ParsedMarket] = {}
        skipped = 0
        for page in range(max_pages):
            raw_items = self.fetch_page(limit=page_size, offset=page * page_size)
            for raw in raw_items:
                parsed = parse_market(raw)
                if parsed is None:
                    skipped += 1
                else:
                    markets[parsed.external_id] = parsed
            if len(raw_items) < page_size:
                break
        if skipped:
            logger.info("Skipped %d malformed or non-binary markets", skipped)
        return list(markets.values())

    def close(self) -> None:
        self._client.close()
