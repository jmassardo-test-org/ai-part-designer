"""
Request context middleware for structured logging.

Provides correlation tracking across async request boundaries using
context variables. Adds request_id, user_id, and request path to
all logs generated during request processing.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request, Response

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to bind request context to structured logs.

    Captures request_id, user_id, and path, binding them to the
    structlog context for the duration of the request. This ensures
    all logs during request processing include correlation data.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and bind context to logs.

        Args:
            request: The incoming request
            call_next: Next middleware or route handler

        Returns:
            Response from the application
        """
        start_time = time.time()

        # Get request ID (added by RequestIdMiddleware)
        request_id = getattr(request.state, "request_id", "unknown")

        # Get user ID if authenticated (may not be available yet)
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.id)

        # Bind context to all logs in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            user_id=user_id,
        )

        # Process request
        try:
            response = await call_next(request)

            # Log request completion
            duration_ms = (time.time() - start_time) * 1000

            # Update context with response info
            structlog.contextvars.bind_contextvars(
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Log based on status code
            if response.status_code >= 500:
                logger.error(
                    "request_completed",
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
            elif response.status_code >= 400:
                logger.warning(
                    "request_completed",
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
            else:
                logger.info(
                    "request_completed",
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )

            return response

        except Exception as exc:
            # Log exception with context
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(
                "request_failed",
                exc_info=exc,
                duration_ms=duration_ms,
            )
            raise

        finally:
            # Clear context after request
            structlog.contextvars.clear_contextvars()
