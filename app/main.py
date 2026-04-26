"""Application factory.

Wires the three DAG branches together: the logging branch (configured during
lifespan startup), the middleware branch (request-ID echo + log binding),
and the routing branch (health + ocr). No business logic, no constants, no
schemas defined here — just composition. ADR-003 (layered structure) puts
the factory in this exact file.

``app`` is exposed at module level so ``uv run uvicorn app.main:app`` works.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import ENGINE_VERSION
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.routers import health, ocr


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure structured logging on startup."""
    configure_logging()
    yield


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="fake-ocr-service",
        version=ENGINE_VERSION,
        lifespan=lifespan,
    )
    app.add_middleware(RequestIDMiddleware)
    app.include_router(health.router)
    app.include_router(ocr.router)
    return app


app = create_app()
