"""Belt-and-braces test for ADR-001.

Importing ``app.main`` (which the ``client`` fixture already does) must NOT
pull in any real OCR or computer-vision library. This is mechanical
enforcement of the fake-engine constraint — if someone later adds a wrapper
that lazily imports ``pytesseract``, this test fires the moment
``app.main`` is imported in any scenario.
"""

import sys

import app.main  # noqa: F401  — import is the point of the test

FORBIDDEN_MODULES = frozenset(
    {
        "pytesseract",
        "paddleocr",
        "easyocr",
        "cv2",
        "PIL",
    }
)


def test_no_real_ocr_libraries_in_sys_modules() -> None:
    leaked = FORBIDDEN_MODULES & set(sys.modules)
    assert not leaked, f"Real OCR / vision libs leaked into sys.modules: {sorted(leaked)}"
