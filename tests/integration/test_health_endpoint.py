"""Integration tests for ``GET /v1/health``."""

from fastapi.testclient import TestClient


def test_health_envelope(client: TestClient) -> None:
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json() == {
        "success": True,
        "data": {"status": "ok", "engine": "fake-v0"},
        "error": None,
    }


def test_health_sets_request_id_header(client: TestClient) -> None:
    r = client.get("/v1/health")
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) == 32


def test_health_generated_request_ids_are_unique(client: TestClient) -> None:
    """Two separate calls without a client-supplied X-Request-ID get distinct generated values."""
    r1 = client.get("/v1/health")
    r2 = client.get("/v1/health")
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]
