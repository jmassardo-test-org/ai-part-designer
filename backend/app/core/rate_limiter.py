"""
Rate limiter dependency for FastAPI endpoints.

Provides configurable per-endpoint rate limiting using Redis.
Supports both user-based and IP-based limiting.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status

from app.core.cache import redis_client

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.models.user import User

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception with retry info."""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def get_client_ip(request: Request) -> str:
    """Extract client IP, considering proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """
    FastAPI dependency for rate limiting.

    Usage:
        @router.post("/endpoint", dependencies=[Depends(RateLimiter(10, 60))])
        async def endpoint():
            ...

    Or with custom key:
        @router.post("/endpoint")
        async def endpoint(
            _: None = Depends(RateLimiter(10, 60, key_func=lambda r, u: f"custom:{u.id}"))
        ):
            ...
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int = 60,
        key_prefix: str = "rate_limit",
        key_func: Callable[[Request, User | None], str] | None = None,
        use_user_id: bool = True,
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            key_prefix: Redis key prefix
            key_func: Custom key generation function
            use_user_id: Use user ID if authenticated (falls back to IP)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self.key_func = key_func
        self.use_user_id = use_user_id

    async def __call__(
        self,
        request: Request,
    ) -> None:
        """Check rate limit and raise if exceeded."""
        # Try to get user from request state if available
        user: Any = getattr(request.state, "user", None)

        # Build rate limit key
        if self.key_func:
            identifier = self.key_func(request, user)
        elif self.use_user_id and user:
            identifier = f"user:{user.id}"
        else:
            identifier = f"ip:{get_client_ip(request)}"

        key = f"{self.key_prefix}:{request.url.path}:{identifier}"

        # Check rate limit
        try:
            is_allowed, remaining = await redis_client.check_rate_limit(
                key=key,
                max_requests=self.max_requests,
                window_seconds=self.window_seconds,
            )
        except Exception as e:
            # If Redis is down, log and allow request (fail-open)
            logger.warning(f"Rate limiter error (allowing request): {e}")
            return

        if not is_allowed:
            ttl = await redis_client.ttl(key)
            retry_after = max(1, ttl)

            logger.warning(
                f"Rate limit exceeded: {key} (limit: {self.max_requests}/{self.window_seconds}s)"
            )

            raise RateLimitExceeded(retry_after=retry_after)

        # Add rate limit headers to response
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = self.max_requests
        request.state.rate_limit_reset = self.window_seconds


# =============================================================================
# Pre-configured Rate Limiters
# =============================================================================

# Strict limit for expensive operations (copy, generate, etc.)
expensive_operation_limit = RateLimiter(
    max_requests=10,
    window_seconds=60,
    key_prefix="rate_limit:expensive",
)

# Standard API limit
standard_api_limit = RateLimiter(
    max_requests=60,
    window_seconds=60,
    key_prefix="rate_limit:api",
)

# Strict limit for auth endpoints (login, register)
auth_limit = RateLimiter(
    max_requests=5,
    window_seconds=60,
    key_prefix="rate_limit:auth",
    use_user_id=False,  # Always use IP for auth
)

# Limit for design management operations
design_operation_limit = RateLimiter(
    max_requests=20,
    window_seconds=60,
    key_prefix="rate_limit:design",
)
