import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

_tmpdir = tempfile.mkdtemp()
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.sqlite3"
os.environ["CLERK_JWKS_URL"] = "https://clerk.example.test/.well-known/jwks.json"
os.environ["CLERK_ISSUER"] = "https://clerk.example.test"
os.environ["CLERK_AUTHORIZED_PARTIES"] = "http://localhost:3000"
os.environ["RATE_LIMIT"] = "10000/minute"

import jwt  # noqa: E402
import pytest  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from auth import ClerkVerifier, get_verifier  # noqa: E402
from config import get_settings  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from main import app  # noqa: E402
from models import Market, MarketSnapshot  # noqa: E402

PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@dataclass
class _Key:
    key: object


class FakeJWKSClient:
    def get_signing_key_from_jwt(self, token):
        return _Key(PRIVATE_KEY.public_key())


def make_token(sub="user_alice", key=PRIVATE_KEY, algorithm="RS256", **overrides):
    now = datetime.now(UTC)
    claims = {
        "sub": sub,
        "iss": "https://clerk.example.test",
        "azp": "http://localhost:3000",
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=1),
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=algorithm)


def auth_header(sub="user_alice", **overrides):
    return {"Authorization": f"Bearer {make_token(sub, **overrides)}"}


@pytest.fixture(autouse=True)
def _db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    app.dependency_overrides[get_verifier] = lambda: ClerkVerifier(
        get_settings(), jwks_client=FakeJWKSClient()
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_market(db):
    counter = {"n": 0}

    def _make(
        question="Will it rain?",
        category="weather",
        probability=0.5,
        volume=100.0,
        active=True,
        history=(),
    ):
        counter["n"] += 1
        now = datetime.now(UTC)
        market = Market(
            external_id=f"ext-{counter['n']}",
            question=question,
            category=category,
            probability=probability,
            volume=volume,
            liquidity=10.0,
            active=active,
        )
        db.add(market)
        db.flush()
        for hours_ago, prob in history:
            db.add(
                MarketSnapshot(
                    market_id=market.id,
                    probability=prob,
                    captured_at=now - timedelta(hours=hours_ago),
                )
            )
        db.commit()
        return market

    return _make
