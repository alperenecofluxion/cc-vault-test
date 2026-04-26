"""OCR endpoint.

``POST /v1/ocr`` validation sequence (order matters; earlier checks shadow
later ones):

1. ``no_file`` (400)        — multipart had no ``file`` part.
2. ``file_too_large`` (413) — body size > ``MAX_UPLOAD_BYTES``.
3. Strip path components from the upload's filename so we never echo a path.
4. ``missing_extension`` (415) — basename has no ``.`` or ends with one.
5. ``unsupported_extension`` (415) — last segment lowercased not in the set.
6. Happy path — delegate to ``run_ocr`` and return the ``OCRData`` envelope.

Implements ADR-001 (calls the pure function), ADR-002 (envelope on every
code path), ADR-003 (router lives in ``app/routers``).
"""

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import MAX_UPLOAD_BYTES, SUPPORTED_EXTENSIONS
from app.schemas import ErrorDetail, ErrorResponse, OCRData, SuccessResponse
from app.services.ocr import run_ocr

router = APIRouter(prefix="/v1")


def _allowed_list() -> str:
    """Render the sorted ``.ext`` list for human-readable error messages."""
    return ", ".join(f".{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))


def _err(status: int, code: str, message: str) -> JSONResponse:
    """Build an error envelope with the given HTTP status."""
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump(),
    )


@router.post("/ocr", response_model=SuccessResponse[OCRData])
async def ocr(file: UploadFile | None = File(None)):  # noqa: B008 — FastAPI dep-default idiom
    """Return deterministic mock OCR text for a supported file."""
    if file is None:
        return _err(400, "no_file", "No file part 'file' in request")

    content = await file.read()
    size = len(content)
    if size > MAX_UPLOAD_BYTES:
        observed_mb = f"{size / (1024 * 1024):.1f}"
        return _err(
            413,
            "file_too_large",
            f"File size {observed_mb} MB exceeds 10 MB limit",
        )

    raw = file.filename or ""
    basename = raw.replace("\\", "/").rsplit("/", 1)[-1]

    parts = basename.rsplit(".", 1)
    if len(parts) < 2 or not parts[1]:
        return _err(
            415,
            "missing_extension",
            f"File '{basename}' has no extension; cannot determine handler.",
        )

    extension = parts[1].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        return _err(
            415,
            "unsupported_extension",
            f"Extension '.{extension}' is not supported. Allowed: {_allowed_list()}",
        )

    text = run_ocr(basename, extension)
    return SuccessResponse[OCRData](
        data=OCRData(text=text, extension=extension, filename=basename),
    )
