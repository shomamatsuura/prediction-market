from datetime import UTC, datetime, timedelta

from tests.conftest import OTHER_KEY, auth_header, make_token


def test_watchlists_require_auth(client):
    assert client.get("/watchlists").status_code == 401
    assert client.post("/watchlists", json={"name": "x"}).status_code == 401


def test_rejects_invalid_tokens(client):
    past = datetime.now(UTC) - timedelta(hours=1)
    bad_tokens = [
        "not-a-jwt",
        make_token(key=OTHER_KEY),  # wrong signature
        make_token(exp=past, iat=past - timedelta(minutes=1), nbf=past - timedelta(minutes=1)),
        make_token(iss="https://evil.example"),
        make_token(azp="https://evil.example"),
        make_token(sub=None),
        make_token(exp=None),
    ]
    for token in bad_tokens:
        r = client.get("/watchlists", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, token


def test_rejects_hs256_algorithm_confusion(client):
    token = make_token(key="secret-shared-key-of-sufficient-length-0123456789", algorithm="HS256")
    r = client.get("/watchlists", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_watchlist_crud(client, make_market):
    market = make_market()
    h = auth_header()

    r = client.post("/watchlists", json={"name": "  My   picks "}, headers=h)
    assert r.status_code == 201
    wl = r.json()
    assert wl["name"] == "My picks"
    assert r.headers["Cache-Control"] == "no-store"

    r = client.post(f"/watchlists/{wl['id']}/items", json={"market_id": market.id}, headers=h)
    assert r.status_code == 201
    assert [i["market"]["id"] for i in r.json()["items"]] == [market.id]

    # Adding twice is idempotent.
    r = client.post(f"/watchlists/{wl['id']}/items", json={"market_id": market.id}, headers=h)
    assert len(r.json()["items"]) == 1

    r = client.get("/watchlists", headers=h)
    assert len(r.json()) == 1

    r = client.delete(f"/watchlists/{wl['id']}/items/{market.id}", headers=h)
    assert r.status_code == 204
    assert client.get("/watchlists", headers=h).json()[0]["items"] == []

    assert client.delete(f"/watchlists/{wl['id']}", headers=h).status_code == 204
    assert client.get("/watchlists", headers=h).json() == []


def test_duplicate_name_conflicts(client):
    h = auth_header()
    assert client.post("/watchlists", json={"name": "A"}, headers=h).status_code == 201
    assert client.post("/watchlists", json={"name": "A"}, headers=h).status_code == 409


def test_validation(client):
    h = auth_header()
    assert client.post("/watchlists", json={"name": ""}, headers=h).status_code == 422
    assert client.post("/watchlists", json={"name": "   "}, headers=h).status_code == 422
    assert client.post("/watchlists", json={"name": "x" * 101}, headers=h).status_code == 422
    extra_field = client.post("/watchlists", json={"name": "a", "user_id": 1}, headers=h)
    assert extra_field.status_code == 422


def test_users_cannot_touch_other_users_watchlists(client, make_market):
    market = make_market()
    alice, bob = auth_header("user_alice"), auth_header("user_bob")
    wl = client.post("/watchlists", json={"name": "Alice"}, headers=alice).json()
    client.post(f"/watchlists/{wl['id']}/items", json={"market_id": market.id}, headers=alice)

    assert client.get("/watchlists", headers=bob).json() == []
    r = client.post(f"/watchlists/{wl['id']}/items", json={"market_id": market.id}, headers=bob)
    assert r.status_code == 404
    r = client.delete(f"/watchlists/{wl['id']}/items/{market.id}", headers=bob)
    assert r.status_code == 404
    assert client.delete(f"/watchlists/{wl['id']}", headers=bob).status_code == 404
    assert len(client.get("/watchlists", headers=alice).json()[0]["items"]) == 1


def test_add_unknown_market(client):
    h = auth_header()
    wl = client.post("/watchlists", json={"name": "A"}, headers=h).json()
    r = client.post(f"/watchlists/{wl['id']}/items", json={"market_id": 12345}, headers=h)
    assert r.status_code == 404
