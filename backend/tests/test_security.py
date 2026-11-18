import pytest
from limits import parse

from config import get_settings
from main import app

SECRET = "s" * 40


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


def test_forged_forwarded_for_is_ignored_without_trusted_proxy(client, limited):
    statuses = [
        client.get("/markets", headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code
        for i in range(4)
    ]
    assert statuses == [200, 200, 200, 429]


def test_only_the_proxy_appended_forwarded_for_entry_counts(client, limited, monkeypatch):
    monkeypatch.setattr(get_settings(), "trusted_proxy_hops", 1)
    # The client forges the left entry; the proxy appends the real address on the right.
    statuses = [
        client.get("/markets", headers={"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.7"}).status_code
        for i in range(4)
    ]
    assert statuses == [200, 200, 200, 429]
    # A different real client still has its own budget.
    r = client.get("/markets", headers={"X-Forwarded-For": "198.51.100.9"})
    assert r.status_code == 200


def test_frontend_forwarded_client_ip_needs_the_secret(client, limited, monkeypatch):
    monkeypatch.setattr(get_settings(), "internal_api_secret", SECRET)

    # With the secret, each browser gets its own budget even though all requests come
    # from the frontend server.
    for i in range(5):
        headers = {"X-Internal-Secret": SECRET, "X-Client-IP": f"198.51.100.{i}"}
        assert client.get("/markets", headers=headers).status_code == 200

    # Without it (or with a wrong one), X-Client-IP is ignored.
    forged = [
        client.get(
            "/markets", headers={"X-Internal-Secret": "wrong", "X-Client-IP": f"10.1.1.{i}"}
        ).status_code
        for i in range(4)
    ]
    assert forged == [200, 200, 200, 429]


def test_invalid_client_ip_falls_back_to_connection(client, limited, monkeypatch):
    monkeypatch.setattr(get_settings(), "internal_api_secret", SECRET)
    headers = {"X-Internal-Secret": SECRET, "X-Client-IP": "not-an-ip"}
    assert _statuses(client, 4, headers=headers) == [200, 200, 200, 429]


def test_short_internal_secret_is_rejected_in_production(monkeypatch):
    settings = get_settings().model_copy(
        update={
            "app_env": "production",
            "database_url": "postgresql+psycopg://u:p@db/x",
            "clerk_jwks_url": "https://clerk.example.test/.well-known/jwks.json",
            "clerk_issuer": "https://clerk.example.test",
            "clerk_authorized_parties": "https://app.example.test",
            "internal_api_secret": "short",
        }
    )
    with pytest.raises(RuntimeError, match="INTERNAL_API_SECRET"):
        settings.validate_for_production()
