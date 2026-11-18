import json

import httpx
from sqlalchemy import func, select

from config import get_settings
from ingestion.job import run_ingestion, store_markets
from ingestion.polymarket import PolymarketClient, parse_market
from models import Market, MarketSnapshot


def raw(id_="1", question="Will X happen?", prices=("0.65", "0.35"), **extra):
    data = {
        "id": id_,
        "question": question,
        "slug": "will-x",
        "outcomes": json.dumps(["Yes", "No"]),
        "outcomePrices": json.dumps(list(prices)),
        "volumeNum": 1234.5,
        "liquidityNum": 99,
        "category": "Politics",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/x.png",
        "endDate": "2030-01-01T00:00:00Z",
        "active": True,
        "closed": False,
    }
    data.update(extra)
    return data


def test_parse_market_happy_path():
    m = parse_market(raw())
    assert m.external_id == "1"
    assert m.probability == 0.65
    assert m.category == "politics"
    assert m.volume == 1234.5
    assert m.end_date.year == 2030


def test_parse_market_rejects_bad_data():
    assert parse_market("nope") is None
    assert parse_market(raw(question=None)) is None
    assert parse_market(raw(prices=("1.5", "0"))) is None
    assert parse_market(raw(prices=("nan", "0"))) is None
    assert parse_market(raw(outcomePrices="not json")) is None


def test_parse_market_drops_unsafe_image_urls():
    assert parse_market(raw(image="javascript:alert(1)")).image_url is None
    assert parse_market(raw(image="http://insecure.example/x.png")).image_url is None


def test_store_markets_upserts_and_snapshots(db):
    store_markets(db, [parse_market(raw()), parse_market(raw("2", "Other?"))])
    store_markets(db, [parse_market(raw(prices=("0.7", "0.3")))])

    assert db.scalar(select(func.count()).select_from(Market)) == 2
    assert db.scalar(select(func.count()).select_from(MarketSnapshot)) == 3
    m1 = db.scalar(select(Market).where(Market.external_id == "1"))
    m2 = db.scalar(select(Market).where(Market.external_id == "2"))
    assert m1.probability == 0.7
    assert m2.active is False  # dropped out of the feed


def _client(handler):
    return PolymarketClient(
        "https://gamma.example.test", client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_run_ingestion_end_to_end(db):
    def handler(request):
        if request.url.params["offset"] == "0":
            return httpx.Response(200, json=[raw("1"), {"garbage": True}, raw("2", "Y?")])
        return httpx.Response(200, json=[])

    settings = get_settings().model_copy(update={"ingestion_page_size": 3})
    assert run_ingestion(settings, client=_client(handler)) == 2
    assert db.scalar(select(func.count()).select_from(MarketSnapshot)) == 2


def test_run_ingestion_survives_api_errors(db):
    client = _client(lambda request: httpx.Response(500))
    assert run_ingestion(get_settings(), client=client) == 0
    client = _client(lambda request: httpx.Response(200, json={"unexpected": "shape"}))
    assert run_ingestion(get_settings(), client=client) == 0
