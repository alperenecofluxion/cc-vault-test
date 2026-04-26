"""Deterministic mock OCR engine.

Pure function, no I/O, no model, no randomness, no timestamps. Looks up the
lowercase extension in ``RESPONSE_TEMPLATES`` and formats with the basename.
Caller (the router) is responsible for ensuring the extension is supported
— this layer does no validation.

This is the literal implementation of ADR-001.
"""

from app.core.config import RESPONSE_TEMPLATES


def run_ocr(basename: str, extension: str) -> str:
    """Return the deterministic mock OCR text for a supported extension."""
    return RESPONSE_TEMPLATES[extension.lower()].format(filename=basename)
