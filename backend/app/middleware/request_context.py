"""
Request context middleware for structured logging.

Binds request-specific context (request_id, user_id, path) to structlog's
context variables for automatic inclusion in all log messages during request processing.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request, Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to bind request context to structured logs.

    Extracts and binds the following context for all logs during request processing:
    - request_id: Unique identifier for request tracing (from X-Request-ID header or generated)
    - user_id: Authenticated user ID (if available)
    - path: Request path
    - method: HTTP method

    The context is automatically included in all log messages generated during
    the request lifecycle through structlog's context variables.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        """
        Process request and bind context to logs.

        Args:
            request: The incoming request.
            call_next: Next middleware/handler in chain.

        Returns:
            Response from downstream handlers.
        """
        # Clear any existing context
        structlog.contextvars.clear_contextvars()

        # Get or generate request ID
        # Precedence order:
        # 1. X-Request-ID header (from external proxy/load balancer)
        # 2. request.state.request_id (from other middleware)
        # 3. Generate new ID if none exists
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            # Check if it was set by another middleware
            request_id = getattr(request.state, "request_id", None)
        if not request_id:
            # Generate new request ID (22-char URL-safe base64 string)
            request_id = secrets.token_urlsafe(16)
            request.state.request_id = request_id

        # Bind request context
        context = {
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        }

        # Add user context if available
        if hasattr(request.state, "user_id"):
            context["user_id"] = str(request.state.user_id)
        elif hasattr(request.state, "user"):
            # Extract user ID from user object
            user = request.state.user
            if hasattr(user, "id"):
                context["user_id"] = str(user.id)

        # Bind context to structlog
        structlog.contextvars.bind_contextvars(**context)

        # Process request
        response: Response = await call_next(request)

        # Add request ID to response headers for client correlation
        response.headers["X-Request-ID"] = request_id

        return response
