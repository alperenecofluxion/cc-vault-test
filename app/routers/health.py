"""Health endpoint.

``GET /v1/health`` returns a constant success envelope. No I/O, no liveness
probes, no dependency checks. PRD §US-3 is explicit: this endpoint exists
to answer "is the process alive enough to respond at all".

Health intentionally uses the envelope (ADR-002) — convention over
convenience.
"""

from fastapi import APIRouter

from app.schemas import HealthData, SuccessResponse

router = APIRouter(prefix="/v1")


@router.get("/health", response_model=SuccessResponse[HealthData])
async def health() -> SuccessResponse[HealthData]:
    """Return the constant health envelope."""
    return SuccessResponse[HealthData](data=HealthData(status="ok"))
