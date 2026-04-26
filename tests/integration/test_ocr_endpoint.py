"""Integration tests for ``POST /v1/ocr`` covering happy paths and all error codes."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("filename", "extension", "expected_text"),
    [
        (
            "invoice.pdf",
            "pdf",
            "Mock OCR result for PDF document.\nFilename: invoice.pdf\nPages: 3",
        ),
        (
            "scan.png",
            "png",
            "Mock OCR result for PNG image.\nFilename: scan.png\nDimensions: 1024x768",
        ),
        (
            "notes.txt",
            "txt",
            "Mock OCR result for text file.\nFilename: notes.txt\nLines: 42",
        ),
    ],
)
def test_happy_path_per_extension(
    client: TestClient,
    filename: str,
    extension: str,
    expected_text: str,
) -> None:
    r = client.post(
        "/v1/ocr", files={"file": (filename, b"some bytes", "application/octet-stream")}
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "success": True,
        "data": {
            "text": expected_text,
            "extension": extension,
            "filename": filename,
            "engine": "fake-v0",
        },
        "error": None,
    }


def test_no_file_returns_400(client: TestClient) -> None:
    r = client.post("/v1/ocr")
    assert r.status_code == 400
    assert r.json() == {
        "success": False,
        "data": None,
        "error": {"code": "no_file", "message": "No file part 'file' in request"},
    }


def test_missing_extension_returns_415(client: TestClient) -> None:
    r = client.post("/v1/ocr", files={"file": ("README", b"x", "text/plain")})
    assert r.status_code == 415
    body = r.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "missing_extension"
    assert body["error"]["message"] == "File 'README' has no extension; cannot determine handler."


def test_trailing_dot_returns_missing_extension(client: TestClient) -> None:
    """A basename ending with '.' has no usable extension segment."""
    r = client.post("/v1/ocr", files={"file": ("weird.", b"x", "application/octet-stream")})
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "missing_extension"


def test_unsupported_extension_returns_415(client: TestClient) -> None:
    r = client.post("/v1/ocr", files={"file": ("data.xyz", b"x", "application/octet-stream")})
    assert r.status_code == 415
    body = r.json()
    assert body["error"]["code"] == "unsupported_extension"
    assert (
        body["error"]["message"] == "Extension '.xyz' is not supported. Allowed: .pdf, .png, .txt"
    )


def test_file_too_large_returns_413(client: TestClient) -> None:
    """One byte over the 10 MiB limit triggers the size error with the documented format."""
    over = b"x" * (10 * 1024 * 1024 + 1)
    r = client.post("/v1/ocr", files={"file": ("huge.pdf", over, "application/pdf")})
    assert r.status_code == 413
    body = r.json()
    assert body["error"]["code"] == "file_too_large"
    assert body["error"]["message"].endswith(" MB exceeds 10 MB limit")
    assert body["error"]["message"].startswith("File size ")


def test_compound_extension_matches_last_segment(client: TestClient) -> None:
    """archive.tar.gz → 'gz' → unsupported."""
    r = client.post(
        "/v1/ocr",
        files={"file": ("archive.tar.gz", b"x", "application/gzip")},
    )
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_extension"


def test_case_insensitive_extension(client: TestClient) -> None:
    """INVOICE.PDF is treated as a pdf."""
    r = client.post("/v1/ocr", files={"file": ("INVOICE.PDF", b"x", "application/pdf")})
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["extension"] == "pdf"
    # Filename is echoed as the basename of what the client sent — case preserved.
    assert body["data"]["filename"] == "INVOICE.PDF"


def test_path_components_stripped(client: TestClient) -> None:
    """A multipart filename with path components is reduced to its basename."""
    r = client.post(
        "/v1/ocr",
        files={"file": ("subdir/invoice.pdf", b"x", "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["data"]["filename"] == "invoice.pdf"


def test_windows_path_components_stripped(client: TestClient) -> None:
    r = client.post(
        "/v1/ocr",
        files={"file": (r"C:\Users\foo\invoice.pdf", b"x", "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["data"]["filename"] == "invoice.pdf"
