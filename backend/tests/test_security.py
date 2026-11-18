import pytest
from limits import parse

from main import app


@pytest.fixture
def limited(monkeypatch):
    """Lower the rate limit to 3 requests per minute for one test."""
    limiter = app.state.rate_limiter
    monkeypatch.setattr(limiter, "limit", parse("3/minute"))
    limiter.reset()
    yield
    limiter.reset()


def _statuses(client, n, path="/markets", headers=None):
    return [client.get(path, headers=headers).status_code for _ in range(n)]


def test_rate_limit_applies_to_routes(client, limited):
    assert _statuses(client, 4) == [200, 200, 200, 429]
    r = client.get("/markets/categories")
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_rate_limit_applies_to_watchlists(client, limited):
    assert _statuses(client, 4, "/watchlists") == [401, 401, 401, 429]
