"""Request-ID propagation: echo when client provides one, generate UUIDv4 hex otherwise."""

import string

from fastapi.testclient import TestClient

HEX = set(string.hexdigits.lower())


def test_client_provided_id_is_echoed_on_health(client: TestClient) -> None:
    r = client.get("/v1/health", headers={"X-Request-ID": "caller-supplied-123"})
    assert r.headers["X-Request-ID"] == "caller-supplied-123"


def test_generated_id_is_32_char_hex(client: TestClient) -> None:
    r = client.get("/v1/health")
    rid = r.headers["X-Request-ID"]
    assert len(rid) == 32
    assert set(rid).issubset(HEX)


def test_client_provided_id_is_echoed_on_ocr_success(client: TestClient) -> None:
    r = client.post(
        "/v1/ocr",
        headers={"X-Request-ID": "ocr-success-id"},
        files={"file": ("a.pdf", b"x", "application/pdf")},
    )
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == "ocr-success-id"


def test_client_provided_id_is_echoed_on_ocr_error(client: TestClient) -> None:
    """Error responses must carry X-Request-ID too — middleware runs around the handler."""
    r = client.post("/v1/ocr", headers={"X-Request-ID": "ocr-error-id"})
    assert r.status_code == 400
    assert r.headers["X-Request-ID"] == "ocr-error-id"
