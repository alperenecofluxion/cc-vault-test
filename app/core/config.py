"""Module-level constants for the fake-ocr-service.

Single source of truth for engine identity, upload limits, the supported-extension
set, and the per-extension response templates. Downstream modules (schemas,
service, router) read from here and never hardcode these values.

Bumping ``ENGINE_VERSION`` is a code change with a corresponding test update
per ADR-001 — friction by design.
"""

ENGINE_VERSION: str = "fake-v0"

MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MiB

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({"pdf", "png", "txt"})

RESPONSE_TEMPLATES: dict[str, str] = {
    "pdf": "Mock OCR result for PDF document.\nFilename: {filename}\nPages: 3",
    "png": "Mock OCR result for PNG image.\nFilename: {filename}\nDimensions: 1024x768",
    "txt": "Mock OCR result for text file.\nFilename: {filename}\nLines: 42",
}
