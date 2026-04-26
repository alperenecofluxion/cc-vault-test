---
name: fake-ocr-service
status: backlog
created: 2026-04-26T12:38:17Z
updated: 2026-04-26T13:24:35Z
progress: 0%
prd: .claude/prds/fake-ocr-service.md
github: (will be set on sync)
---

# Epic: fake-ocr-service

## Overview

Build a small FastAPI service whose value is its shape, not its function. The service exposes `POST /v1/ocr` (multipart file → deterministic mock text) and `GET /v1/health` (constant `{status: ok, engine: fake-v0}`). The "OCR engine" is a pure Python function returning a hardcoded template per supported extension — `.pdf`, `.png`, `.txt`. Nothing is loaded, nothing is randomised, nothing is timestamped. The codebase is scaffolded with the layered structure of a real production service so that habits learned here transfer when the service stops being a toy.

The implementation surface is intentionally tight: ~150 lines of real logic across ~10 files, plus tests that prove determinism and ≥95% coverage. The lesson is the layout, the envelope, the request-ID middleware, the lockfile, and the CI pipeline — not OCR.

## Architecture Decisions

Three ADRs in the vault govern this epic and are non-negotiable for v1. None of them is re-litigated here; this epic implements them.

- **[[2026-04-26-fake-ocr-engine-constraint]] (ADR-001) — Fake OCR engine constraint.** The "engine" is a pure deterministic Python function in `app/services/ocr.py` returning byte-identical strings from hardcoded per-extension templates. No model, no I/O, no randomness, no timestamps. `ENGINE_VERSION = "fake-v0"` is a module constant in `app/core/config.py`; bumping it is a code change with a test update. No `OCR_MODE` toggle, no real-OCR adapter, no mock library indirection.

- **[[2026-04-26-api-response-envelope-shape]] (ADR-002) — Response envelope shape.** All endpoints return `{"success": bool, "data": <payload|null>, "error": <{code, message}|null>}` on both success and error. Enforced server-side by Pydantic models in `app/schemas.py` (`SuccessResponse`, `ErrorResponse`, `OCRData`, `HealthData`). HTTP status codes still carry meaning (`200`, `400`, `413`, `415`); the envelope augments them. Health intentionally uses the envelope too — convention beats convenience.

- **[[2026-04-26-layered-project-structure]] (ADR-003) — Layered project structure.** The codebase is organised as `app/main.py` (factory) + `app/routers/{ocr,health}.py` + `app/services/ocr.py` + `app/core/{config,logging,middleware}.py` + `app/schemas.py`. The single mock function gets its own `services/` home not because the function is complex but because the *placement* is the lesson. No flat `main.py`, no hexagonal layout, no domain-grouped folders.

Two further decisions follow directly from the PRD's Constraints & Assumptions and are recorded here (not promoted to ADRs because they are PRD-derived, not novel):

- **Configuration via module-level constants in `app/core/config.py`.** No env vars, no `.env`, no `Settings` class for v1. PRD §Constraints. Future env-var config is a downstream ADR.
- **Structured logging via `structlog`, JSON output, one line per request.** PRD §Non-Functional Requirements. No metrics, no tracing, no OTel.

## Technical Approach

### Frontend Components

**N/A.** This is a backend service with no UI. The "client" is a generic HTTP consumer (curl, integration tests, eventual library users). The OpenAPI schema FastAPI auto-generates at `/docs` is a free byproduct, not a deliverable.

### Backend Services

The full module map, with each module's responsibility and its inbound dependencies:

| Module | Responsibility | Depends on |
|---|---|---|
| `app/core/config.py` | `ENGINE_VERSION`, `MAX_UPLOAD_BYTES = 10 * 1024 * 1024`, `SUPPORTED_EXTENSIONS = {"pdf", "png", "txt"}`, response template strings keyed by extension | stdlib only |
| `app/core/logging.py` | `structlog` configuration: JSON renderer, ISO timestamps, `request_id` context binding helper | `structlog` |
| `app/core/middleware.py` | `RequestIDMiddleware` — reads `X-Request-ID` header or generates UUIDv4; binds to log context; sets header on response | `app/core/logging` |
| `app/schemas.py` | Pydantic v2 models: `OCRData`, `HealthData`, `ErrorDetail`, `SuccessResponse`, `ErrorResponse`. Envelope shape per ADR-002 | `pydantic`, `app/core/config` (for engine version default) |
| `app/services/ocr.py` | `run_ocr(basename: str, extension: str) -> str` — pure function; reads templates from `app/core/config`; raises nothing (extension-validity is checked upstream in the router) | `app/core/config` |
| `app/routers/health.py` | `GET /v1/health` — returns `SuccessResponse(data=HealthData(status="ok", engine=ENGINE_VERSION))` | `app/schemas`, `app/core/config` |
| `app/routers/ocr.py` | `POST /v1/ocr` — multipart parsing, basename + extension extraction, size check (413), no-file check (400), missing-extension check (415), unsupported-extension check (415), call `run_ocr`, return `SuccessResponse` | `app/schemas`, `app/services/ocr`, `app/core/config` |
| `app/main.py` | App factory `create_app()`: configure logging on startup, register `RequestIDMiddleware`, mount routers under `/v1`, expose module-level `app = create_app()` for `uvicorn app.main:app` | all of the above |

**Key behavioural rules** (from the PRD, mapped to where they live):

- Extension is taken from the *last* dot only; `archive.tar.gz` → `gz` → unsupported. (`app/routers/ocr.py`)
- Extension matching is case-insensitive; normalise to lowercase before lookup. (`app/routers/ocr.py`)
- Filename echoed back is always the basename — strip path components before processing. (`app/routers/ocr.py`)
- Size limit is enforced by reading the body and measuring. `MAX_UPLOAD_BYTES = 10 * 1024 * 1024`. (`app/routers/ocr.py`)
- `Content-Type` on the upload part is **ignored**. PRD §Functional Requirements 6. (`app/routers/ocr.py`)
- `X-Request-ID` is echoed if provided, generated as UUIDv4 otherwise. Always set on response, always present in log lines. (`app/core/middleware.py`)

**Error code → HTTP status table** (canonical; tests assert this exactly):

| Condition | HTTP status | `error.code` | `error.message` shape |
|---|---|---|---|
| No `file` part | 400 | `no_file` | `"No file part 'file' in request"` |
| File has no extension | 415 | `missing_extension` | `"File '<basename>' has no extension; cannot determine handler."` |
| Unsupported extension | 415 | `unsupported_extension` | `"Extension '.<ext>' is not supported. Allowed: .pdf, .png, .txt"` |
| Size > 10 MB | 413 | `file_too_large` | `"File size <observed> MB exceeds 10 MB limit"` |

### Infrastructure

- **Toolchain.** `uv` manages dependencies and runs commands. `pyproject.toml` declares `requires-python = ">=3.11,<3.12"`, runtime deps (`fastapi`, `uvicorn[standard]`, `python-multipart`, `structlog`), dev deps (`pytest`, `pytest-cov`, `httpx`, `ruff`), and ruff config. `.python-version` pins `3.11`. `uv.lock` is committed.
- **Makefile.** `make check` = `uv run ruff check && uv run ruff format --check && uv run pytest --cov=app --cov-fail-under=95`. `make run` = `uv run uvicorn app.main:app --reload`.
- **CI.** `.github/workflows/ci.yml` runs `uv sync` then `make check` on every push and PR, on Python 3.11, on `ubuntu-latest`. Single job, no matrix.
- **No Dockerfile, no docker-compose.** PRD §Out of Scope.
- **No environment variables, no `.env`.** PRD §Constraints.

## Implementation Strategy

The build order is bottom-up along the dependency tree. Each phase has explicit inputs (what must exist before it can start) and outputs (what later phases will need). This ordering is not a suggestion — it is the order in which the modules can compile and be tested at all.

### Phase A — Project scaffold (no inbound deps; blocks everything)

**Inputs:** none.

**Outputs:**
- `pyproject.toml` with deps, ruff config, pytest config (`addopts = "--cov=app --cov-report=term-missing --cov-fail-under=95"`), `[tool.coverage.run] source = ["app"]`.
- `.python-version` → `3.11`.
- `uv.lock` (generated by `uv sync`, committed).
- `Makefile` with `check` and `run` targets.
- `.gitignore` covering `.venv/`, `__pycache__/`, `.pytest_cache/`, `.coverage`, `htmlcov/`, `.ruff_cache/`.
- Empty package markers: `app/__init__.py`, `app/routers/__init__.py`, `app/services/__init__.py`, `app/core/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`.
- `README.md` (one paragraph, fresh-clone reproducibility instructions per US-5).

**Gate:** `uv sync` succeeds on a fresh clone.

### Phase B — Core constants (depends on A)

**Inputs:** Phase A.

**Outputs:**
- `app/core/config.py` — `ENGINE_VERSION`, `MAX_UPLOAD_BYTES`, `SUPPORTED_EXTENSIONS`, `RESPONSE_TEMPLATES: dict[str, str]` (keyed by lowercase extension, values are format strings with a `{filename}` placeholder per PRD §Functional Requirements 2).

**Gate:** `python -c "from app.core import config; print(config.ENGINE_VERSION)"` works inside `uv run`.

### Phase C — Logging setup (depends on A; parallel with B)

**Inputs:** Phase A.

**Outputs:**
- `app/core/logging.py` — `configure_logging()` function setting up `structlog` JSON renderer with ISO-8601 timestamps and a `bind_request_id(request_id: str)` context manager / helper for middleware.

**Gate:** Logging configured via `configure_logging()` produces parseable JSON to stdout.

### Phase D — Pydantic schemas (depends on B)

**Inputs:** Phase B (uses `ENGINE_VERSION` for the `OCRData.engine` and `HealthData.engine` defaults).

**Outputs:**
- `app/schemas.py`:
  - `OCRData(text: str, extension: str, filename: str, engine: str = ENGINE_VERSION)`
  - `HealthData(status: str, engine: str = ENGINE_VERSION)`
  - `ErrorDetail(code: str, message: str)`
  - `SuccessResponse[T](success: Literal[True] = True, data: T, error: None = None)`
  - `ErrorResponse(success: Literal[False] = False, data: None = None, error: ErrorDetail)`

**Gate:** Models import cleanly; `SuccessResponse[OCRData](data=OCRData(text="x", extension="pdf", filename="a.pdf")).model_dump()` matches the envelope shape exactly.

### Phase E — OCR service (depends on B; parallel with C and D)

**Inputs:** Phase B (uses `RESPONSE_TEMPLATES`).

**Outputs:**
- `app/services/ocr.py` — `run_ocr(basename: str, extension: str) -> str`. Pure function. Looks up the lowercase `extension` in `RESPONSE_TEMPLATES`, formats with `basename`, returns the string. Caller is responsible for ensuring the extension is supported; the service does not validate.

**Gate:** Phase F-1 unit tests below pass against this module standalone.

### Phase F-1 — Unit tests for OCR service (depends on E)

**Inputs:** Phase E.

**Outputs:**
- `tests/unit/test_ocr_service.py`:
  - One test per supported extension covering the exact expected string.
  - One test asserting determinism: 50 calls → identical strings.
  - One test asserting filename is interpolated literally (no escaping, no path stripping at this layer — that's the router's job).

**Gate:** `uv run pytest tests/unit -v` green.

### Phase G — Request-ID middleware (depends on C)

**Inputs:** Phase C (uses `bind_request_id` helper).

**Outputs:**
- `app/core/middleware.py` — `RequestIDMiddleware` (Starlette `BaseHTTPMiddleware` subclass). Reads `X-Request-ID` from request headers; if absent generates `uuid.uuid4().hex` (or canonical form — pick one, document in module docstring). Binds to log context for the duration of the request. Sets `X-Request-ID` on the response.

**Gate:** Middleware can be instantiated and its `dispatch` method calls into the next handler without error in isolation.

### Phase H — Routers (depends on D, E for OCR; depends on D for health)

**Inputs:** Phase D, Phase E.

**Outputs:**
- `app/routers/health.py` — `router = APIRouter(prefix="/v1")`; `GET /health` returns `SuccessResponse[HealthData](data=HealthData(status="ok"))`. Uses `response_model=SuccessResponse[HealthData]`.
- `app/routers/ocr.py` — `router = APIRouter(prefix="/v1")`; `POST /ocr` accepts `file: UploadFile = File(...)`. Sequence:
  1. If no `file` part → return `JSONResponse(status_code=400, content=ErrorResponse(error=ErrorDetail(code="no_file", message=...)).model_dump())`.
  2. Read body, measure size; if `> MAX_UPLOAD_BYTES` → 413 `file_too_large`.
  3. Take basename of `file.filename` (strip path components).
  4. Split off last extension after the final `.`; if none → 415 `missing_extension`.
  5. Lowercase the extension; if not in `SUPPORTED_EXTENSIONS` → 415 `unsupported_extension`.
  6. Call `run_ocr(basename, extension)` → return `SuccessResponse[OCRData](data=OCRData(text=..., extension=extension, filename=basename))`.

**Gate:** Modules import without error; routers can be mounted on a bare `FastAPI()` instance and the OpenAPI schema generates.

### Phase I — App factory (depends on G and H)

**Inputs:** Phase G (middleware), Phase H (routers), Phase C (logging).

**Outputs:**
- `app/main.py` — `create_app() -> FastAPI` that:
  - Calls `configure_logging()` on startup (lifespan).
  - Instantiates `FastAPI(title="fake-ocr-service", version=ENGINE_VERSION)`.
  - Adds `RequestIDMiddleware`.
  - Includes `app/routers/health.router` and `app/routers/ocr.router`.
  - Returns the app.
- Module-level `app = create_app()` so `uvicorn app.main:app` works.

**Gate:** `uv run uvicorn app.main:app` starts without error; `curl http://localhost:8000/v1/health` returns the expected envelope.

### Phase J — Integration tests (depends on I)

**Inputs:** Phase I.

**Outputs:**
- `tests/integration/test_health_endpoint.py` — `TestClient` happy path; asserts envelope, status 200, `X-Request-ID` header present.
- `tests/integration/test_ocr_endpoint.py` — happy path per supported extension; all four error codes (`no_file`, `missing_extension`, `unsupported_extension`, `file_too_large`) with exact `code` and exact HTTP status.
- `tests/integration/test_determinism.py` — for each supported extension, 50 sequential POSTs with the same `(basename, bytes)` input → 50 byte-identical response bodies.
- Tests for `X-Request-ID` echo behaviour: client-provided ID is echoed; absence triggers server generation.

**Gate:** `uv run pytest -v` green; coverage ≥ 95%.

### Phase K — CI pipeline (depends on J — wired up only after the suite is green locally)

**Inputs:** Phase J.

**Outputs:**
- `.github/workflows/ci.yml` — single job, `ubuntu-latest`, Python 3.11, `astral-sh/setup-uv@v3`, `uv sync --frozen`, `make check`. Triggers: `push` and `pull_request`.

**Gate:** Workflow green on first push.

### Cross-cutting: parallelisation

The DAG has three branches that can be developed in parallel after Phase A and Phase B land:

- **Branch 1 (deepest):** B → D → H (routers) → I → J
- **Branch 2:** C → G, joins Branch 1 at I
- **Branch 3:** B → E → F-1, joins Branch 1 at H (router needs E)

A team of two could split Branch 2 from the rest. A solo run does them in order.

## Task Breakdown Preview

This is a **preview** of the high-level groupings the next phase (`/pm:epic-decompose`) will turn into numbered task files. **No tasks are created here.** Order matches the dependency graph above.

1. **Project scaffold** — `pyproject.toml`, `.python-version`, `Makefile`, `uv.lock`, `.gitignore`, package markers, `README.md`. (Phase A)
2. **Core constants** — `app/core/config.py`. (Phase B)
3. **Logging + middleware** — `app/core/logging.py`, `app/core/middleware.py`. (Phases C, G)
4. **Pydantic envelope schemas** — `app/schemas.py`. (Phase D)
5. **OCR service + unit tests** — `app/services/ocr.py`, `tests/unit/test_ocr_service.py`. (Phases E, F-1)
6. **Health router** — `app/routers/health.py`. (Phase H, partial)
7. **OCR router** — `app/routers/ocr.py` with all four error paths. (Phase H, partial)
8. **App factory** — `app/main.py` wiring middleware, routers, logging lifespan. (Phase I)
9. **Integration tests** — `tests/integration/test_health_endpoint.py`, `test_ocr_endpoint.py`, `test_determinism.py`, request-ID echo tests. (Phase J)
10. **CI workflow** — `.github/workflows/ci.yml`. (Phase K)

Target task count: **10**, matching the ccpm-recommended ceiling.

## Dependencies

**External / runtime packages:** `fastapi`, `uvicorn[standard]`, `python-multipart`, `structlog`, `pydantic` (transitive via FastAPI; pinned via lockfile).

**External / dev packages:** `pytest`, `pytest-cov`, `httpx`, `ruff`.

**External / toolchain:** `uv` (must be installed on the developer's machine and in CI), GitHub Actions runner with Python 3.11.

**Vault dependencies (decision authority):**
- [[2026-04-26-fake-ocr-engine-constraint]] — locks the engine to fake.
- [[2026-04-26-api-response-envelope-shape]] — locks the response shape.
- [[2026-04-26-layered-project-structure]] — locks the directory layout.

Any change that violates one of these ADRs requires a new ADR superseding it before code lands. Not a process suggestion — a hard gate.

**Internal dependencies:** none. This epic introduces the first service in the project; nothing currently consumes it.

**Prerequisite work:** none. The PRD is the only upstream artifact and it is already ratified.

## Success Criteria (Technical)

Mirrors the PRD's Success Criteria with implementation-level specificity. Each is a binary check that must hold before the epic can close.

1. **Envelope conformance.** Every response from `/v1/ocr` and `/v1/health`, success or error, validates against `SuccessResponse` or `ErrorResponse` Pydantic models. Verified by integration tests that round-trip the JSON through `model_validate`.
2. **Determinism.** For each of `.pdf`, `.png`, `.txt`, 50 sequential POSTs with the same `(basename, bytes)` produce 50 byte-identical response bodies. Verified by `test_determinism.py`.
3. **Error code matrix.** All four error conditions (`no_file` / 400, `missing_extension` / 415, `unsupported_extension` / 415, `file_too_large` / 413) emit the exact `code` and exact HTTP status documented above. Verified by integration tests, one assertion per row.
4. **Coverage ≥ 95%.** `pytest --cov=app --cov-fail-under=95` exits zero. The `--cov-fail-under` flag is set in `pyproject.toml` so the gate is enforced, not aspirational.
5. **Lint + format clean.** `ruff check` and `ruff format --check` exit zero with no findings.
6. **Fresh-clone reproducibility.** On a clean clone, `uv sync && make check` runs to green in under 30 seconds. Verified manually before merge; documented in `README.md`.
7. **Service starts.** `uv sync && make run` brings the service up with no manual steps; `curl http://localhost:8000/v1/health` returns the expected envelope.
8. **CI green.** `.github/workflows/ci.yml` passes on the first push of the branch.
9. **Request-ID propagation.** Every response carries `X-Request-ID`. Client-provided IDs are echoed verbatim; absent IDs are replaced with a UUIDv4. Verified by two integration tests.
10. **No real OCR.** No imports of `pytesseract`, `paddleocr`, `easyocr`, or any ML/vision library. Verified by a one-line test that imports `app` and asserts those modules are not in `sys.modules` after import. (Belt-and-braces given ADR-001.)

## Estimated Effort

**Overall timeline:** 1–2 working days for a solo developer who knows FastAPI; 2–3 days if learning the toolchain along the way (which is part of the point).

**Resource requirements:** one developer. No design, no infra, no review-by-committee.

**Critical-path items** (the longest chain through the DAG, in order, no parallelism):
1. Phase A scaffold — ~1–2 hours (mostly waiting on `uv sync` and lockfile resolution).
2. Phase B core constants — ~15 minutes.
3. Phase D schemas — ~30 minutes.
4. Phase H routers (both, sequentially) — ~2 hours including the four error paths.
5. Phase I app factory — ~30 minutes.
6. Phase J integration tests — ~2–3 hours; this is where coverage and the determinism assertion get earned.
7. Phase K CI — ~30 minutes; mostly fighting `uv` cache settings on first run.

**Total critical-path estimate:** ~7–9 hours of focused work. The non-critical branches (logging, middleware, OCR service + unit tests) add another ~2–3 hours but overlap with the above.

**Risk-adjusted buffer:** add 30% for the first time. ~12 hours wall-clock for a solo developer is a realistic ceiling.

## Tasks Created

- [ ] 001.md - Project scaffold (parallel: false)
- [ ] 002.md - Core constants (parallel: true)
- [ ] 003.md - Logging and request-ID middleware (parallel: true)
- [ ] 004.md - Pydantic envelope schemas (parallel: true)
- [ ] 005.md - OCR service and unit tests (parallel: true)
- [ ] 006.md - Health router (parallel: true)
- [ ] 007.md - OCR router (parallel: true)
- [ ] 008.md - App factory (parallel: false)
- [ ] 009.md - Integration tests (parallel: false)
- [ ] 010.md - CI workflow (parallel: false)

Total tasks: 10
Parallel tasks: 6
Sequential tasks: 4
Estimated total effort: ~12 hours (critical path) / ~10 hours (with parallelisation)
