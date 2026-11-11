from fastapi.testclient import TestClient

from app.main import SECURITY_HEADERS, app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_security_headers_on_every_response():
    for path in ("/", "/healthz", "/does-not-exist"):
        response = client.get(path)
        for header, value in SECURITY_HEADERS.items():
            assert response.headers[header] == value


def test_api_docs_are_disabled():
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_create_and_read_item():
    created = client.post("/api/v1/items", json={"name": "gpu-node", "quantity": 4})
    assert created.status_code == 201
    item = created.json()
    assert item["name"] == "gpu-node"

    fetched = client.get(f"/api/v1/items/{item['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == item


def test_input_validation_rejects_bad_names_and_quantities():
    bad_payloads = [
        {"name": "<script>alert(1)</script>", "quantity": 1},
        {"name": "", "quantity": 1},
        {"name": "x" * 65, "quantity": 1},
        {"name": "ok", "quantity": -1},
    ]
    for payload in bad_payloads:
        assert client.post("/api/v1/items", json=payload).status_code == 422


def test_missing_item_returns_404():
    assert client.get("/api/v1/items/999999").status_code == 404


def test_metrics_use_route_templates_not_raw_paths():
    client.get("/api/v1/items/424242")
    client.get("/no/such/path")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert 'route="/api/v1/items/{item_id}",status="404"' in body
    assert 'route="unmatched",status="404"' in body
    assert "/api/v1/items/424242" not in body
    assert "http_request_duration_seconds_bucket" in body


def test_unhandled_errors_are_counted_as_500():
    def boom() -> None:
        raise RuntimeError("simulated failure")

    app.add_api_route("/test-only/boom", boom)
    lenient = TestClient(app, raise_server_exceptions=False)
    assert lenient.get("/test-only/boom").status_code == 500
    assert 'route="/test-only/boom",status="500"' in client.get("/metrics").text
