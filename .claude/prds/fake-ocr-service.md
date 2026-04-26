---
name: fake-ocr-service
description: Deterministic mock OCR service exposing POST /v1/ocr and GET /v1/health behind a production-shaped FastAPI scaffold; no real OCR engine.
status: backlog
created: 2026-04-26T08:13:52Z
---

# PRD: fake-ocr-service

## Executive Summary

A small FastAPI service that returns deterministic, byte-identical mock OCR
responses based on the uploaded file's extension and basename. The "OCR engine"
is intentionally fake — a pure Python function with no model, no I/O, no
randomness. The value is in the surrounding shape: layered architecture,
structured logging, request-ID propagation, ruff/pytest, uv-locked dependencies,
CI on every push. The service ships nothing useful by itself; it ships a
production-shaped skeleton against which the cc-best PM→Lead→Dev→QA workflow
can be exercised end-to-end.

## Problem Statement

This is a learning project. The implicit problem is "I do not yet have a
small, end-to-end, production-shaped Python service in this repo to exercise
my workflow against." Existing solutions (real OCR services, demo apps) are
either too large to reason about completely or too sloppy to learn good habits
from. We need something small enough to read in one sitting and shaped well
enough that every habit it teaches transfers to a real service.

The fake engine is the point, not a limitation: it removes the variable that
would otherwise dominate (model behaviour, latency, accuracy) and forces the
learning surface to be the parts that actually matter — request shape, error
contracts, observability, reproducibility.

## User Stories

### US-1: Client integrator — happy path
**As** a client integrator,
**I want** to POST a supported file to `/v1/ocr` and receive a deterministic
JSON envelope containing mock OCR text,
**so that** I can build and test consumers without running real OCR.

Acceptance criteria:
- Given a `multipart/form-data` upload of `invoice.pdf` (any bytes, ≤ 10 MB),
  the response is `200 OK` with body
  `{"success": true, "data": {"text": "Mock OCR result for PDF document.\nFilename: invoice.pdf\nPages: 3", "extension": "pdf", "filename": "invoice.pdf", "engine": "fake-v0"}, "error": null}`.
- The same call repeated 50 times yields byte-identical response bodies.
- Extensions are matched case-insensitively (`.PDF` ≡ `.pdf`).
- Compound extensions are not interpreted; only the last segment after the
  final `.` is used (`archive.tar.gz` → matches `gz` → unsupported).
- Filename in the response is always the basename; any path components in the
  uploaded filename are stripped before processing or echoing back.

### US-2: Client integrator — error paths
**As** a client integrator,
**I want** structured error responses for every failure mode,
**so that** I can program against errors instead of guessing.

Acceptance criteria:
- Unsupported extension → `415 Unsupported Media Type` with
  `{"success": false, "data": null, "error": {"code": "unsupported_extension", "message": "Extension '.xyz' is not supported. Allowed: .pdf, .png, .txt"}}`.
- File with no extension (e.g. `README`) → `415` with
  `error.code: "missing_extension"`, message
  `"File 'README' has no extension; cannot determine handler."`.
- No file part in the request → `400 Bad Request` with
  `error.code: "no_file"`.
- Upload exceeds 10 MB → `413 Payload Too Large` with
  `error.code: "file_too_large"`, message includes both observed and limit
  (e.g. `"File size 12.4 MB exceeds 10 MB limit"`).
- All error responses use the same envelope shape; `data` is always `null` on
  error and `error` is always `null` on success.

### US-3: Operator — health check
**As** an operator (or a load balancer),
**I want** a `GET /v1/health` endpoint,
**so that** I can verify the service is alive.

Acceptance criteria:
- `GET /v1/health` returns `200 OK` with body
  `{"success": true, "data": {"status": "ok", "engine": "fake-v0"}, "error": null}`.
- The endpoint does no I/O, performs no checks beyond returning the constant,
  and never returns non-200 in v1.

### US-4: Developer — log correlation
**As** a developer correlating logs across requests,
**I want** every response to carry an `X-Request-ID` header,
**so that** I can grep one ID through the log stream.

Acceptance criteria:
- If the client sends `X-Request-ID`, the server echoes the same value on
  every response (success or error, including health).
- If the client does not send `X-Request-ID`, the server generates a UUIDv4
  and returns it in the response header.
- Every structured log line for the request includes the `request_id` field
  with the same value as the response header.

### US-5: Contributor — fresh-clone reproducibility
**As** a contributor,
**I want** to run `uv sync && make check` from a fresh clone and have the test
suite pass green,
**so that** I can iterate without environment drift.

Acceptance criteria:
- `uv.lock` is committed.
- `.python-version` pins Python to `3.11`.
- `make check` runs ruff lint, ruff format --check, and pytest with coverage.
- All the above pass on a clone with no manual setup beyond `uv sync`.

## Functional Requirements

1. **Endpoints (versioned under `/v1`)**:
   - `POST /v1/ocr` — accepts `multipart/form-data` with a single file part
     named `file`. Returns the success envelope on supported extensions and
     the error envelope on any failure.
   - `GET /v1/health` — returns the success envelope with
     `data: {"status": "ok", "engine": "fake-v0"}`.

2. **Supported extensions and response templates** (filename-interpolated;
   trailing constants are part of the contract, not measured from the file):
   - `.pdf` →
     `"Mock OCR result for PDF document.\nFilename: <basename>\nPages: 3"`
   - `.png` →
     `"Mock OCR result for PNG image.\nFilename: <basename>\nDimensions: 1024x768"`
   - `.txt` →
     `"Mock OCR result for text file.\nFilename: <basename>\nLines: 42"`

3. **Response envelope** (consistent across all endpoints, success and error):
   ```json
   {"success": true,  "data": { ... }, "error": null}
   {"success": false, "data": null,    "error": {"code": "...", "message": "..."}}
   ```

4. **Extension handling**:
   - Normalise to lowercase before matching.
   - Use the last extension only (after the final `.`).
   - No extension at all → `missing_extension`.
   - Unknown extension → `unsupported_extension`.

5. **Filename handling**:
   - Strip path components before echoing into responses.
   - Never echo a raw path back to the client.

6. **Upload handling**:
   - Hard cap: 10 MB.
   - Read-and-discard the full body. The bytes transit; nothing is persisted
     or inspected beyond size.
   - `Content-Type` header on the upload part is ignored. Mismatched headers
     do not produce errors. (Documented non-goal.)

7. **Request ID middleware**:
   - Echo `X-Request-ID` if provided; otherwise generate UUIDv4.
   - Always set the header on every response.
   - Inject the value into the structured log context for the request.

8. **Engine version**:
   - Module-level constant `ENGINE_VERSION = "fake-v0"` in `app/core/config.py`.
   - Surfaced in `/v1/ocr` success responses and `/v1/health` responses.
   - Bumping it is a code change with a corresponding test update.

## Non-Functional Requirements

- **Determinism**: same input → byte-identical response, across processes,
  across machines, across runs. No timestamps, UUIDs, or randomness in
  response bodies.
- **Layered structure**:
  ```
  app/
    main.py            # app factory, lifespan, router mounting
    routers/
      ocr.py           # POST /v1/ocr
      health.py        # GET /v1/health
    services/
      ocr.py           # deterministic mock function (pure)
    core/
      config.py        # ENGINE_VERSION, MAX_UPLOAD_BYTES, supported extensions
      logging.py       # structured logging setup
      middleware.py    # X-Request-ID middleware
    schemas.py         # Pydantic envelope: SuccessResponse, ErrorResponse, OCRData, HealthData
  tests/
    unit/test_ocr_service.py
    integration/test_ocr_endpoint.py
    integration/test_health_endpoint.py
    integration/test_determinism.py
  ```
- **Logging**: structured JSON via `structlog`. One line per request with
  fields `request_id, method, path, status, duration_ms, filename, extension,
  response_size_bytes, client_ip`.
- **Test coverage**: ≥ 95% measured by `pytest --cov`.
- **Toolchain**: `uv` for dependency management, `ruff` for lint + format,
  `pytest` + `pytest-cov` for tests, `httpx` (via FastAPI's `TestClient`) for
  integration tests.
- **CI**: GitHub Actions on every push and PR — `uv sync && make check`.
- **Test suite runtime**: `uv run pytest` completes in under 30 seconds on a
  fresh clone.
- **Startup**: `uv sync && make run` starts the service with no manual steps.

## Success Criteria

1. All endpoints return the documented envelope shape; verified by
   integration tests.
2. 100% deterministic responses verified by a 50-call repeat test per
   supported extension.
3. Test coverage ≥ 95% measured by `pytest --cov`.
4. `ruff check` and `ruff format --check` pass with zero findings.
5. `uv run pytest` completes green from a fresh clone in under 30 seconds.
6. `uv sync && make run` starts the service on a fresh clone with no manual
   steps.
7. CI pipeline (`.github/workflows/ci.yml`) runs `make check` on every push
   and passes green.
8. Every response carries an `X-Request-ID` header (echoed if provided,
   generated otherwise); verified by integration test.

## Constraints & Assumptions

**Constraints**:
- Python 3.11.x only (`requires-python = ">=3.11,<3.12"`).
- FastAPI + uvicorn stack.
- No real OCR engine. This is locked at the architectural level; changing it
  requires an ADR in the vault.
- Configuration is module-level constants only. No environment variables for
  v1.
- Structured JSON logging only. No metrics, no tracing.
- Single deployment unit; no Docker for v1.
- Single-file uploads only; one `file` part per request.

**Assumptions**:
- The service is stateless across requests.
- Trust the extension; ignore `Content-Type`.
- Filenames are processed as basenames only (path separators stripped).
- Bytes are read but not persisted or inspected beyond size measurement.
- Test client is FastAPI's sync `TestClient`. Real-HTTP E2E (subprocess
  uvicorn) is a future ADR if it ever becomes necessary.

## Out of Scope

Explicit non-goals — included to prevent scope drift:

- Real OCR engine (Tesseract, PaddleOCR, etc.). Non-negotiable; requires ADR
  to change.
- Authentication / authorization.
- Rate limiting.
- Persistence (database, file storage, caching).
- Async/background processing (Celery, queues).
- File content validation beyond size + extension. The `Pages: 3` and
  `Dimensions: 1024x768` constants are part of the response template, **not**
  measured from the file.
- Multiple file uploads per request.
- Internationalisation of response text.
- Metrics / Prometheus / OpenTelemetry. Logs only for v1.
- Configuration via environment variables. Module-level constants for v1;
  env-driven config is a future ADR.
- CORS. Not exposed to browsers in v1.
- `Content-Type` header validation on the upload part.
- Dockerfile / container image. Deployment shape is a future ADR.
- Real-HTTP E2E layer (subprocess uvicorn). Future ADR.

## Dependencies

**Runtime**:
- `fastapi`
- `uvicorn[standard]`
- `python-multipart` (required for multipart parsing)
- `structlog`

**Development**:
- `pytest`
- `pytest-cov`
- `httpx` (transitive via `TestClient`, listed explicitly)
- `ruff`

**Toolchain / external**:
- `uv` (dependency manager and runner)
- GitHub Actions (CI)
- The vault at `C:/Users/alper/vault` for ADRs governing decisions outside
  this PRD's scope (engine swap, env-config, Docker, real-HTTP E2E).

**Internal dependencies**: none. The service has no internal callers yet;
this PRD defines the first one.
