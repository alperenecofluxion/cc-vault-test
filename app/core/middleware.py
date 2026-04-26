"""Request-ID middleware.

Honours an inbound ``X-Request-ID`` header verbatim if present; otherwise
generates a fresh UUIDv4 in canonical lowercase 32-character hex form
(``uuid.uuid4().hex``). The chosen value is bound to the structlog
contextvars for the duration of the request so that every log line emitted
during the request carries the same ``request_id``. Cleared in a ``finally``
block so the next request starts fresh, even if the handler raised.
"""

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import bind_request_id, clear_request_id

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Bind a request_id for log correlation; echo it on the response header."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        bind_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            clear_request_id()
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
