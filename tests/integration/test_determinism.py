"""Determinism contract: same input produces byte-identical responses, every time."""

import hashlib

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("filename", "extension"),
    [
        ("sample.pdf", "pdf"),
        ("sample.png", "png"),
        ("sample.txt", "txt"),
    ],
)
def test_50_sequential_calls_byte_identical(
    client: TestClient,
    filename: str,
    extension: str,
) -> None:
    """50 POSTs with identical input → 50 byte-identical response bodies."""
    payload = (filename, b"fixed-bytes-for-determinism", f"application/{extension}")
    r0 = client.post("/v1/ocr", files={"file": payload})
    assert r0.status_code == 200
    baseline_hash = hashlib.sha256(r0.content).hexdigest()
    for _ in range(49):
        r = client.post("/v1/ocr", files={"file": payload})
        assert r.status_code == 200
        assert hashlib.sha256(r.content).hexdigest() == baseline_hash
