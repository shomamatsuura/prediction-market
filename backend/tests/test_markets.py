def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]


def test_list_markets_filters_and_sorts(client, make_market):
    make_market("Rain in Paris?", category="weather", volume=10)
    make_market("BTC above 100k?", category="crypto", volume=500)
    make_market("Closed one", category="crypto", active=False)

    r = client.get("/markets")
    body = r.json()
    assert r.status_code == 200
    assert body["total"] == 2
    assert [m["question"] for m in body["items"]] == ["BTC above 100k?", "Rain in Paris?"]

    r = client.get("/markets", params={"category": "crypto"})
    assert [m["question"] for m in r.json()["items"]] == ["BTC above 100k?"]

    r = client.get("/markets", params={"q": "paris"})
    assert [m["question"] for m in r.json()["items"]] == ["Rain in Paris?"]


def test_search_treats_wildcards_literally(client, make_market):
    make_market("Plain question")
    r = client.get("/markets", params={"q": "%"})
    assert r.json()["total"] == 0


def test_list_markets_rejects_bad_params(client):
    assert client.get("/markets", params={"limit": 1000}).status_code == 422
    assert client.get("/markets", params={"category": "<script>"}).status_code == 422
    assert client.get("/markets", params={"sort": "id; drop"}).status_code == 422


def test_market_detail_and_snapshots(client, make_market):
    m = make_market(history=[(3, 0.4), (2, 0.45), (1, 0.5), (24 * 60, 0.1)])
    r = client.get(f"/markets/{m.id}")
    assert r.status_code == 200
    assert r.json()["question"] == "Will it rain?"

    r = client.get(f"/markets/{m.id}/snapshots")
    assert [s["probability"] for s in r.json()] == [0.4, 0.45, 0.5]


def test_market_not_found(client):
    assert client.get("/markets/999").status_code == 404
    assert client.get("/markets/999/snapshots").status_code == 404


def test_movers(client, make_market):
    up = make_market("Up", probability=0.8, history=[(20, 0.5), (1, 0.79)])
    down = make_market("Down", probability=0.2, history=[(10, 0.3)])
    make_market("Flat", probability=0.5, history=[(5, 0.5)])
    make_market("Old", probability=0.9, history=[(48, 0.1)])

    r = client.get("/markets/movers", params={"hours": 24})
    body = r.json()
    assert [x["market"]["id"] for x in body] == [up.id, down.id]
    assert round(body[0]["change"], 2) == 0.3
    assert round(body[1]["change"], 2) == -0.1

    r = client.get("/markets/movers", params={"direction": "down"})
    assert [x["market"]["id"] for x in r.json()] == [down.id]


def test_categories(client, make_market):
    make_market(category="crypto")
    make_market(category="crypto")
    make_market(category="sports")
    r = client.get("/markets/categories")
    assert r.json() == [{"category": "crypto", "count": 2}, {"category": "sports", "count": 1}]


def test_out_of_range_ids_are_rejected_not_500(client):
    for path in ("/markets/99999999999", "/markets/99999999999/snapshots", "/markets/0"):
        assert client.get(path).status_code == 422
