"""
Rate limiting configuration for API endpoints.

Implements tiered rate limiting based on user type and endpoint category.
Uses slowapi for rate limiting with Redis backend support.
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException, Request, status
from starlette.responses import Response

# Rate limit tiers by user type
RATE_LIMITS = {
    "anonymous": {
        "default": "10/minute",
        "auth": "5/minute",  # Login, register attempts
        "search": "20/minute",
        "health": "100/minute",
    },
    "free": {
        "default": "60/minute",
        "auth": "20/minute",
        "search": "100/minute",
        "generation": "10/hour",  # AI generation is expensive
        "upload": "20/hour",
        "export": "30/hour",
    },
    "pro": {
        "default": "300/minute",
        "auth": "60/minute",
        "search": "500/minute",
        "generation": "100/hour",
        "upload": "200/hour",
        "export": "500/hour",
    },
    "enterprise": {
        "default": "1000/minute",
        "auth": "200/minute",
        "search": "2000/minute",
        "generation": "500/hour",
        "upload": "1000/hour",
        "export": "2000/hour",
    },
}

# Endpoint category mapping
ENDPOINT_CATEGORIES = {
    # Auth endpoints
    "/api/v1/auth/login": "auth",
    "/api/v1/auth/register": "auth",
    "/api/v1/auth/forgot-password": "auth",
    "/api/v1/auth/reset-password": "auth",
    # Search endpoints
    "/api/v1/templates/search": "search",
    "/api/v1/files/search": "search",
    "/api/v1/projects/search": "search",
    # Generation endpoints
    "/api/v1/generate": "generation",
    "/api/v1/designs/generate": "generation",
    # Upload endpoints
    "/api/v1/files/upload": "upload",
    "/api/v1/projects/upload": "upload",
    # Export endpoints
    "/api/v1/files/export": "export",
    "/api/v1/designs/export": "export",
    "/api/v1/users/me/audit-logs/export": "export",
    # Health check (should be very permissive)
    "/api/v1/health": "health",
    "/health": "health",
}


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter for development/testing.
    For production, use Redis-backed rate limiting.
    """

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}

    def _parse_rate(self, rate: str) -> tuple[int, int]:
        """Parse rate string like '10/minute' to (count, seconds)."""
        parts = rate.split("/")
        count = int(parts[0])
        period = parts[1].lower()

        period_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }

        return count, period_seconds.get(period, 60)

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate rate limit key."""
        return f"{identifier}:{endpoint}"

    def _cleanup_old(self, key: str, window: int) -> None:
        """Remove requests outside the time window."""
        if key not in self._requests:
            return

        cutoff = time.time() - window
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def is_allowed(self, identifier: str, endpoint: str, rate: str) -> tuple[bool, dict[str, str]]:
        """
        Check if request is allowed.

        Returns:
            Tuple of (allowed, headers dict with rate limit info)
        """
        count, window = self._parse_rate(rate)
        key = self._get_key(identifier, endpoint)

        # Cleanup old requests
        self._cleanup_old(key, window)

        # Get current request count
        if key not in self._requests:
            self._requests[key] = []

        current_count = len(self._requests[key])
        remaining = max(0, count - current_count)

        # Calculate reset time
        if self._requests[key]:
            reset_time = int(self._requests[key][0] + window)
        else:
            reset_time = int(time.time() + window)

        headers = {
            "X-RateLimit-Limit": str(count),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }

        if current_count >= count:
            headers["Retry-After"] = str(reset_time - int(time.time()))
            return False, headers

        # Record this request
        self._requests[key].append(time.time())
        headers["X-RateLimit-Remaining"] = str(remaining - 1)

        return True, headers


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()


def get_rate_limit(
    user_tier: str,
    endpoint: str,
) -> str:
    """Get rate limit for user tier and endpoint."""
    # Determine endpoint category
    category = "default"
    for pattern, cat in ENDPOINT_CATEGORIES.items():
        if endpoint.startswith(pattern) or pattern in endpoint:
            category = cat
            break

    # Get tier limits
    tier_limits = RATE_LIMITS.get(user_tier, RATE_LIMITS["anonymous"])

    # Return category-specific limit or default
    return tier_limits.get(category, tier_limits["default"])


def get_identifier(request: Request) -> str:
    """Get unique identifier for rate limiting."""
    # Try to get user ID from request state (set by auth middleware)
    if hasattr(request.state, "user") and request.state.user:
        user_id: Any = request.state.user.id
        return f"user:{user_id}"

    # Fall back to IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    client = request.client
    if client:
        return f"ip:{client.host}"

    return "ip:unknown"


def get_user_tier(request: Request) -> str:
    """Get user tier for rate limiting."""
    if hasattr(request.state, "user") and request.state.user:
        user = request.state.user
        # Check for tier attribute
        if hasattr(user, "tier"):
            tier: str = user.tier
            return tier
        # Check for admin status
        if hasattr(user, "is_admin") and user.is_admin:
            return "enterprise"
        return "free"

    return "anonymous"


async def rate_limit_middleware(request: Request, call_next: Callable[..., Any]) -> Response:
    """
    Rate limiting middleware.

    Applies rate limits based on user tier and endpoint category.
    """
    # Get rate limit parameters
    identifier = get_identifier(request)
    user_tier = get_user_tier(request)
    endpoint = request.url.path
    rate = get_rate_limit(user_tier, endpoint)

    # Check rate limit
    allowed, headers = _rate_limiter.is_allowed(identifier, endpoint, rate)

    if not allowed:
        error_response = Response(
            content='{"detail": "Rate limit exceeded. Please try again later."}',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            media_type="application/json",
        )
        for key, value in headers.items():
            error_response.headers[key] = value
        return error_response

    # Process request
    response: Response = await call_next(request)

    # Add rate limit headers to response
    for key, value in headers.items():
        response.headers[key] = value

    return response


def rate_limit(rate: str | None = None, category: str | None = None) -> Callable[..., Any]:
    """
    Decorator for rate limiting specific endpoints.

    Usage:
        @rate_limit("10/minute")
        async def my_endpoint():
            ...

        @rate_limit(category="generation")
        async def generate():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            # Determine rate to use
            if rate:
                limit = rate
            elif category:
                user_tier = get_user_tier(request)
                tier_limits = RATE_LIMITS.get(user_tier, RATE_LIMITS["anonymous"])
                limit = tier_limits.get(category, tier_limits["default"])
            else:
                limit = "60/minute"  # Default

            # Check rate limit
            identifier = get_identifier(request)
            endpoint = request.url.path
            allowed, headers = _rate_limiter.is_allowed(identifier, endpoint, limit)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers=headers,
                )

            # Call the actual function
            return await func(request, *args, **kwargs)

            # Note: Headers would need to be added at the response level

        return wrapper

    return decorator


# Export configuration for documentation
def get_rate_limit_docs() -> dict[str, Any]:
    """Get rate limit configuration for API documentation."""
    return {
        "tiers": RATE_LIMITS,
        "endpoint_categories": ENDPOINT_CATEGORIES,
        "description": (
            "Rate limits are applied based on user tier and endpoint category. "
            "Anonymous users have stricter limits. Rate limit headers are included "
            "in all responses: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset."
        ),
    }
