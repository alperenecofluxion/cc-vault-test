"""Pydantic envelope schemas for the response contract.

Implements ADR-002: every response from every endpoint, success or error,
validates against ``SuccessResponse[T]`` or ``ErrorResponse``. The envelope
keys are always present — ``data`` is null on error, ``error`` is null on
success — so clients can write a single parser.
"""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

from app.core.config import ENGINE_VERSION

T = TypeVar("T")


class OCRData(BaseModel):
    """Success payload for ``POST /v1/ocr``."""

    model_config = ConfigDict(extra="forbid")

    text: str
    extension: str
    filename: str
    engine: str = ENGINE_VERSION


class HealthData(BaseModel):
    """Success payload for ``GET /v1/health``."""

    model_config = ConfigDict(extra="forbid")

    status: str
    engine: str = ENGINE_VERSION


class ErrorDetail(BaseModel):
    """Error payload — machine-readable code plus human-readable message."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class SuccessResponse(BaseModel, Generic[T]):
    """Envelope for successful responses."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    data: T
    error: None = None


class ErrorResponse(BaseModel):
    """Envelope for error responses."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[False] = False
    data: None = None
    error: ErrorDetail
