"""
Security middleware for the FastAPI application.

Provides:
- Security headers
- Request ID tracking
- Request logging with security context
- Rate limiting
- CORS hardening
"""

import secrets
import time
from collections.abc import Callable
from typing import Any, ClassVar, cast

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache import redis_client
from app.core.config import settings

# =============================================================================
# Security Headers Middleware
# =============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Implements defense-in-depth through HTTP headers.
    """

    # Content Security Policy - strict by default
    CSP_DIRECTIVES: ClassVar[dict[str, str]] = {
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline'",  # Adjust for your frontend
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: blob: https:",
        "font-src": "'self' data:",
        "connect-src": "'self' https:",
        "frame-ancestors": "'none'",
        "form-action": "'self'",
        "base-uri": "'self'",
        "object-src": "'none'",
    }

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        response: Response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        # Content Security Policy
        csp = "; ".join(f"{k} {v}" for k, v in self.CSP_DIRECTIVES.items())
        response.headers["Content-Security-Policy"] = csp

        # HSTS (only in production with HTTPS)
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Cache control for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


# =============================================================================
# Request ID Middleware
# =============================================================================


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to all requests for tracing.

    The request ID is passed to logging and returned in responses.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        # Check for existing request ID (from load balancer/reverse proxy)
        request_id = request.headers.get("X-Request-ID", secrets.token_urlsafe(16))

        # Store in request state for access in handlers
        request.state.request_id = request_id

        response: Response = await call_next(request)

        # Include in response headers
        response.headers["X-Request-ID"] = request_id

        return response


# =============================================================================
# Request Logging Middleware
# =============================================================================


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all requests with security-relevant information.

    Captures timing, status codes, and potential security events.
    """

    # Paths to exclude from logging (health checks, etc.)
    EXCLUDED_PATHS: ClassVar[set[str]] = {"/health", "/ready", "/metrics"}

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return cast("Response", await call_next(request))

        start_time = time.time()

        # Extract security-relevant information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        request_id = getattr(request.state, "request_id", "unknown")

        # Process request
        response: Response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log the request
        await self._log_request(
            request=request,
            response=response,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            duration_ms=duration_ms,
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP considering proxies."""
        # Check X-Forwarded-For header (set by reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        return request.client.host if request.client else "unknown"

    async def _log_request(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        user_agent: str,
        request_id: str,
        duration_ms: float,
    ) -> None:
        """Log request with security context."""
        import logging
        from datetime import datetime

        logger = logging.getLogger("security")

        log_data = {
            "timestamp": datetime.now(tz=datetime.UTC).isoformat(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
            "user_agent": user_agent[:200],  # Truncate long UAs
        }

        # Add user context if available
        if hasattr(request.state, "user_id"):
            log_data["user_id"] = str(request.state.user_id)

        # Detect suspicious patterns
        is_suspicious = self._detect_suspicious_request(request, response)
        if is_suspicious:
            log_data["suspicious"] = True
            log_data["suspicion_reason"] = is_suspicious

        # Log at appropriate level
        if response.status_code >= 500:
            logger.error("Request failed", extra=log_data)
        elif response.status_code >= 400 or is_suspicious:
            logger.warning("Request issue", extra=log_data)
        else:
            logger.info("Request completed", extra=log_data)

        # Track failed authentications for rate limiting
        if response.status_code == 401:
            await self._track_failed_auth(client_ip)

    def _detect_suspicious_request(
        self,
        request: Request,
        response: Response,
    ) -> str | None:
        """Detect potentially malicious requests."""
        path = request.url.path.lower()

        # Common attack patterns
        suspicious_patterns = [
            ("../" in path, "path_traversal"),
            ("/etc/passwd" in path, "path_traversal"),
            ("/proc/" in path, "path_traversal"),
            (".php" in path, "php_probe"),
            (".asp" in path, "asp_probe"),
            ("wp-admin" in path, "wordpress_probe"),
            ("wp-login" in path, "wordpress_probe"),
            ("/admin" in path and response.status_code == 404, "admin_probe"),
            ("<script" in path, "xss_attempt"),
            ("union select" in path.replace("+", " "), "sql_injection"),
            ("' or " in path.replace("+", " "), "sql_injection"),
        ]

        for condition, reason in suspicious_patterns:
            if condition:
                return reason

        return None

    async def _track_failed_auth(self, client_ip: str) -> None:
        """Track failed authentication attempts."""
        key = f"security:failed_auth:{client_ip}"

        # Increment counter
        count = await redis_client.increment_counter(key, window_seconds=3600)

        # Log if threshold exceeded
        if count > 10:
            import logging

            logger = logging.getLogger("security")
            logger.warning(f"Multiple failed auth attempts from {client_ip}: {count} in last hour")


# =============================================================================
# Rate Limiting Middleware
# =============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware.

    Provides basic rate limiting; use the rate_limit_dependency
    for more granular control.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return cast("Response", await call_next(request))

        client_ip = request.client.host if request.client else "unknown"

        # Check global rate limit
        key = f"ratelimit:global:{client_ip}"
        is_allowed, remaining = await redis_client.check_rate_limit(
            key,
            max_requests=settings.RATE_LIMIT_PER_MINUTE * 2,  # Global is 2x endpoint limit
            window_seconds=60,
        )

        if not is_allowed:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE * 2),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
            )

        response: Response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


# =============================================================================
# IP Blocking Middleware
# =============================================================================


class IPBlockingMiddleware(BaseHTTPMiddleware):
    """
    Block requests from banned IP addresses.

    IPs can be blocked via admin action or automated rules.
    """

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        client_ip = request.client.host if request.client else None

        if client_ip:
            # Check if IP is blocked
            is_blocked = await redis_client.exists(f"security:blocked_ip:{client_ip}")

            if is_blocked:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied"},
                )

        return cast("Response", await call_next(request))


# =============================================================================
# Middleware Registration
# =============================================================================


def register_security_middleware(app: FastAPI) -> None:
    """
    Register all security middleware with the FastAPI app.

    Order matters! Middleware is executed in reverse order of registration.
    """
    # IP blocking (first to execute, blocks before any processing)
    app.add_middleware(IPBlockingMiddleware)

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Request ID (needed for logging)
    app.add_middleware(RequestIdMiddleware)

    # Security logging
    app.add_middleware(SecurityLoggingMiddleware)

    # Security headers (last to execute, adds headers to response)
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS (using FastAPI's built-in)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )


# =============================================================================
# Security Utilities
# =============================================================================


async def block_ip(ip_address: str, duration_seconds: int = 86400, reason: str = "") -> None:
    """Block an IP address."""
    import json
    from datetime import datetime

    await redis_client.set(
        f"security:blocked_ip:{ip_address}",
        json.dumps(
            {
                "blocked_at": datetime.now(tz=datetime.UTC).isoformat(),
                "duration": duration_seconds,
                "reason": reason,
            }
        ),
        ttl=duration_seconds,
    )


async def unblock_ip(ip_address: str) -> None:
    """Unblock an IP address."""
    await redis_client.delete(f"security:blocked_ip:{ip_address}")


async def get_security_stats(_time_window_hours: int = 24) -> dict[str, Any]:
    """Get security statistics for monitoring."""
    # This would query Redis/logs for security metrics
    # TODO: Implement security stats retrieval from Redis/logs
    return {
        "blocked_ips": 0,  # Count from Redis
        "failed_auths": 0,  # Count from Redis
        "suspicious_requests": 0,  # Count from logs
        "rate_limit_hits": 0,  # Count from Redis
    }
