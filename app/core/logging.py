"""Structured logging configuration.

One-liner JSON logs with ISO-8601 UTC timestamps. The single public entry
point ``configure_logging`` is idempotent: structlog's ``configure`` replaces
the prior configuration wholesale, so it is safe to call from a lifespan
hook in tests and in production without stacking processors.

Per-request context (``request_id``) is bound and cleared via
``bind_request_id`` and ``clear_request_id``, which delegate to
``structlog.contextvars`` so that any log call within the same async task
inherits the value automatically.
"""

import logging

import structlog


def configure_logging() -> None:
    """Configure structlog for JSON output. Idempotent."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_request_id(request_id: str) -> None:
    """Bind a ``request_id`` value to the current async-task log context."""
    structlog.contextvars.bind_contextvars(request_id=request_id)


def clear_request_id() -> None:
    """Remove the ``request_id`` from the current async-task log context."""
    structlog.contextvars.unbind_contextvars("request_id")
