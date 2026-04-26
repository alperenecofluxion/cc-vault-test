"""Unit tests for the deterministic OCR service.

These tests exercise the function in isolation, with no FastAPI involvement.
The router is responsible for input validation; this layer is responsible
only for the template lookup and substitution.
"""

import pytest

from app.services.ocr import run_ocr


def test_pdf_template_exact() -> None:
    assert run_ocr("invoice.pdf", "pdf") == (
        "Mock OCR result for PDF document.\nFilename: invoice.pdf\nPages: 3"
    )


def test_png_template_exact() -> None:
    assert run_ocr("scan.png", "png") == (
        "Mock OCR result for PNG image.\nFilename: scan.png\nDimensions: 1024x768"
    )


def test_txt_template_exact() -> None:
    assert run_ocr("notes.txt", "txt") == (
        "Mock OCR result for text file.\nFilename: notes.txt\nLines: 42"
    )


@pytest.mark.parametrize("ext", ["pdf", "png", "txt"])
def test_determinism_50_calls(ext: str) -> None:
    """Same input → byte-identical output, every time."""
    basename = f"sample.{ext}"
    first = run_ocr(basename, ext)
    for _ in range(50):
        assert run_ocr(basename, ext) == first


def test_filename_interpolated_literally() -> None:
    """Filename is interpolated as-is; no escaping, no path stripping at this layer."""
    weird = "a/b/c.weird name with spaces.pdf"
    out = run_ocr(weird, "pdf")
    assert "a/b/c.weird name with spaces.pdf" in out


@pytest.mark.parametrize("ext", ["PDF", "Pdf", "pDf", "pdf"])
def test_case_insensitive_extension(ext: str) -> None:
    """Extension matching is case-insensitive — normalised inside run_ocr."""
    out = run_ocr("a.pdf", ext)
    assert out == run_ocr("a.pdf", "pdf")
