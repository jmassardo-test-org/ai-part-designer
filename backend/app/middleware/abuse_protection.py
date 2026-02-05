"""
Abuse Protection Middleware

Integrates all abuse protection layers into FastAPI middleware:
1. Ban checking (IP and user)
2. Rate limiting (Redis-backed)
3. Usage limit enforcement
4. Request logging for pattern detection
"""

import time
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.redis_rate_limit import get_rate_limit_key, get_rate_limiter
from app.core.usage_limits import UserTier

# =============================================================================
# Configuration
# =============================================================================

# Endpoints that skip abuse checks
SKIP_ABUSE_CHECK_PATHS = {
    "/api/v1/health",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Rate limit configuration by endpoint pattern
ENDPOINT_RATE_LIMITS = {
    # Authentication - strict limits
    "/api/v1/auth/login": (5, 60),  # 5 per minute
    "/api/v1/auth/register": (3, 3600),  # 3 per hour
    "/api/v1/auth/forgot-password": (3, 3600),  # 3 per hour
    # Generation - expensive operation
    "/api/v1/generate": (10, 60),  # 10 per minute
    # Modification - also expensive
    "/api/v1/cad/modify": (20, 60),  # 20 per minute
    # File operations
    "/api/v1/files/upload": (30, 60),  # 30 per minute
    # Default
    "default": (100, 60),  # 100 per minute
}

# Headers that indicate potential API proxy abuse
SUSPICIOUS_HEADERS = {
    "x-automated-request",
    "x-proxy-origin",
    "x-original-url",
    "x-forwarded-host",  # Multiple different hosts
    "x-batch-id",
    "x-correlation-id",
}

# User-agents that indicate automation
SUSPICIOUS_USER_AGENTS = [
    "python-requests",
    "curl/",
    "wget/",
    "httpie/",
    "postman",
    "insomnia",
    # Note: We allow these but flag for monitoring
    # Actual blocking happens if combined with abuse patterns
]


# =============================================================================
# Helper Functions
# =============================================================================


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for forwarded headers (reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client
    if request.client:
        return request.client.host

    return "unknown"


def get_user_id(request: Request) -> UUID | None:
    """Get user ID from request state."""
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user.id
    return None


def get_user_tier(request: Request) -> UserTier:
    """Get user tier from request state."""
    if hasattr(request.state, "user") and request.state.user:
        user = request.state.user
        if hasattr(user, "tier"):
            return UserTier(user.tier)
        if hasattr(user, "is_admin") and user.is_admin:
            return UserTier.ADMIN
        return UserTier.FREE
    return UserTier.FREE


def get_rate_limit_for_path(path: str) -> tuple[int, int]:
    """Get rate limit (count, window_seconds) for a path."""
    for pattern, limits in ENDPOINT_RATE_LIMITS.items():
        if pattern != "default" and path.startswith(pattern):
            return limits
    return ENDPOINT_RATE_LIMITS["default"]


def should_skip_abuse_check(path: str) -> bool:
    """Check if path should skip abuse checks."""
    return path in SKIP_ABUSE_CHECK_PATHS or path.startswith("/static")


def check_suspicious_headers(request: Request) -> tuple[bool, list[str]]:
    """
    Check for headers that indicate API proxy abuse.

    Returns (is_suspicious, list of suspicious indicators)
    """
    indicators = []

    # Check for known suspicious headers
    for header in SUSPICIOUS_HEADERS:
        if request.headers.get(header):
            indicators.append(f"suspicious_header:{header}")

    # Check for multiple X-Forwarded-For entries (proxy chain)
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded.count(",") >= 3:  # More than 3 proxies is suspicious
        indicators.append("excessive_proxy_chain")

    # Check user agent
    user_agent = request.headers.get("User-Agent", "").lower()
    for ua_pattern in SUSPICIOUS_USER_AGENTS:
        if ua_pattern in user_agent:
            indicators.append(f"automated_client:{ua_pattern}")
            break

    # No user agent at all is suspicious
    if not user_agent:
        indicators.append("missing_user_agent")

    # Check for programmatic patterns
    accept = request.headers.get("Accept", "")
    if accept == "*/*" or accept == "application/json":
        # Very generic accept - might be automated
        # Only flag if combined with other indicators
        if indicators:
            indicators.append("generic_accept_header")

    return len(indicators) >= 2, indicators  # Suspicious if 2+ indicators


# =============================================================================
# Middleware
# =============================================================================


class AbuseProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive abuse protection.

    Order of checks:
    1. Skip check for whitelisted paths
    2. Check for suspicious request patterns (API proxy abuse)
    3. Check IP/user ban status
    4. Apply rate limiting
    5. Log request for pattern detection
    """

    def __init__(self, app, db_session_factory=None):
        super().__init__(app)
        self.db_session_factory = db_session_factory

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start_time = time.time()
        path = request.url.path

        # Skip checks for whitelisted paths
        if should_skip_abuse_check(path):
            return await call_next(request)

        client_ip = get_client_ip(request)

        # Store IP in request state for later use
        request.state.client_ip = client_ip

        # Check for suspicious request patterns (API proxy abuse)
        is_suspicious, indicators = check_suspicious_headers(request)
        request.state.suspicious_request = is_suspicious
        request.state.abuse_indicators = indicators

        # If suspicious AND hitting generation endpoint, flag for review
        if is_suspicious and path.startswith("/api/v1/generate"):
            await self._log_suspicious_request(request, client_ip, indicators)

        # Check ban status
        ban_response = await self._check_ban_status(request, client_ip)
        if ban_response:
            return ban_response

        # Apply rate limiting (stricter for suspicious requests)
        rate_limit_response = await self._check_rate_limit(request, client_ip, path, is_suspicious)
        if rate_limit_response:
            return rate_limit_response

        # Process request
        response = await call_next(request)

        # Add timing header
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

        # Log for pattern detection (async, don't wait)
        # await self._log_request(request, response, client_ip, process_time)

        return response

    async def _check_ban_status(
        self,
        request: Request,
        client_ip: str,
    ) -> Response | None:
        """Check if IP or user is banned."""
        if not self.db_session_factory:
            return None

        try:
            async with self.db_session_factory() as db:
                from app.services.abuse_detection import AbuseDetectionService

                service = AbuseDetectionService(db)
                user_id = get_user_id(request)

                is_banned, ban = await service.is_banned(
                    user_id=user_id,
                    ip_address=client_ip,
                )

                if is_banned and ban:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Access denied",
                            "reason": "Your account or IP has been banned",
                            "ban_type": ban.ban_type,
                            "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
                        },
                    )
        except Exception as e:
            # Log error but don't block request
            print(f"Ban check error: {e}")

        return None

    async def _check_rate_limit(
        self,
        request: Request,
        client_ip: str,
        path: str,
        is_suspicious: bool = False,
    ) -> Response | None:
        """Apply rate limiting."""
        try:
            limiter = await get_rate_limiter()
            user_id = get_user_id(request)

            # Get rate limit for this path
            limit, window = get_rate_limit_for_path(path)

            # Adjust limit based on user tier
            tier = get_user_tier(request)
            tier_multipliers = {
                UserTier.FREE: 1.0,
                UserTier.PRO: 3.0,
                UserTier.ENTERPRISE: 10.0,
                UserTier.ADMIN: 50.0,
            }
            limit = int(limit * tier_multipliers.get(tier, 1.0))

            # REDUCE limit for suspicious requests (potential API abuse)
            if is_suspicious:
                limit = max(1, limit // 4)  # 75% reduction

            # Create rate limit key
            key = get_rate_limit_key(
                user_id=str(user_id) if user_id else None,
                ip_address=client_ip,
                endpoint=path,
            )

            # Check rate limit
            result = await limiter.check(key, limit, window)

            if not result.allowed:
                response = JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": result.retry_after,
                    },
                )
                # Add rate limit headers
                for key, value in result.to_headers().items():
                    response.headers[key] = value

                return response

            # Store rate limit info for response headers
            request.state.rate_limit_headers = result.to_headers()

        except Exception as e:
            # Log error but don't block request
            print(f"Rate limit error: {e}")

        return None

    async def _log_suspicious_request(
        self,
        request: Request,
        client_ip: str,
        indicators: list[str],
    ) -> None:
        """Log suspicious request for review."""
        if not self.db_session_factory:
            return

        try:
            async with self.db_session_factory() as db:
                from app.services.abuse_detection import (
                    AbuseDetectionService,
                    ViolationEvent,
                    ViolationType,
                )

                service = AbuseDetectionService(db)
                user_id = get_user_id(request)

                # Record as potential API proxy abuse (warning level)
                violation = ViolationEvent(
                    violation_type=ViolationType.API_PROXY_ABUSE,
                    severity="low",  # Just logging, not banning yet
                    description="Suspicious request patterns detected",
                    evidence={
                        "path": request.url.path,
                        "indicators": indicators,
                        "user_agent": request.headers.get("User-Agent", ""),
                        "headers": dict(request.headers),
                    },
                    user_id=user_id,
                    ip_address=client_ip,
                )

                # Don't apply ban for single suspicious request
                # Just log for pattern detection
                await service.record_violation(violation, apply_ban=False)
                await db.commit()

        except Exception as e:
            print(f"Suspicious request logging error: {e}")


# =============================================================================
# Generation Guard Middleware
# =============================================================================


class GenerationGuardMiddleware:
    """
    Specialized middleware for generation endpoints.

    Enforces:
    - Content moderation on prompts
    - Daily/monthly generation limits
    - Concurrent generation limits
    """

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    async def check_generation_allowed(
        self,
        user_id: UUID,
        prompt: str,
        tier: UserTier,
        ip_address: str,
    ) -> tuple[bool, str | None, dict | None]:
        """
        Check if a generation request should be allowed.

        Returns:
            Tuple of (allowed, rejection_reason, moderation_result)
        """
        # 1. Content moderation
        from app.services.content_moderation import content_moderation

        mod_result = await content_moderation.check_prompt(
            prompt=prompt,
            user_id=user_id,
            use_ai=True,
        )

        if mod_result.is_rejected:
            # Record violation
            async with self.db_session_factory() as db:
                from app.services.abuse_detection import (
                    AbuseDetectionService,
                    ViolationEvent,
                    ViolationType,
                )

                service = AbuseDetectionService(db)

                # Determine violation type
                if any(f.category.value.startswith("firearm") for f in mod_result.flags):
                    violation_type = ViolationType.WEAPON_CONTENT
                elif any(f.category.value == "illegal_drug" for f in mod_result.flags):
                    violation_type = ViolationType.ILLEGAL_CONTENT
                else:
                    violation_type = ViolationType.ILLEGAL_CONTENT

                violation = ViolationEvent(
                    violation_type=violation_type,
                    severity="critical",
                    description="Prohibited content detected in generation prompt",
                    evidence={
                        "prompt": prompt[:500],
                        "flags": [
                            {"category": f.category.value, "severity": f.severity}
                            for f in mod_result.flags
                        ],
                    },
                    user_id=user_id,
                    ip_address=ip_address,
                )

                await service.record_violation(violation)

            rejection_message = content_moderation.get_rejection_message(mod_result)
            return (
                False,
                rejection_message,
                {
                    "decision": mod_result.decision.value,
                    "flags": len(mod_result.flags),
                },
            )

        # 2. Check usage limits
        async with self.db_session_factory() as db:
            from app.core.usage_limits import UsageLimitService

            service = UsageLimitService(db)

            # Check daily/monthly limits
            allowed, details = await service.check_limit(
                user_id=user_id,
                resource_type="generation",
                tier=tier,
            )

            if not allowed:
                return (
                    False,
                    f"Generation limit reached: {details.get('reason', 'limit exceeded')}",
                    details,
                )

            # Check concurrent limit
            concurrent_allowed, current = await service.check_concurrent_limit(
                user_id=user_id,
                operation_type="generation",
                tier=tier,
            )

            if not concurrent_allowed:
                return (
                    False,
                    "Too many concurrent generations. Please wait for current jobs to complete.",
                    {
                        "current": current,
                    },
                )

        return True, None, None

    async def record_generation_start(
        self,
        user_id: UUID,
        job_id: UUID,
        tier: UserTier,
    ) -> UUID:
        """Record that a generation has started."""
        async with self.db_session_factory() as db:
            from app.core.usage_limits import UsageLimitService

            service = UsageLimitService(db)

            # Increment usage counters
            await service.increment_usage(user_id, "generation", "day")
            await service.increment_usage(user_id, "generation", "month")

            # Register concurrent operation
            operation_id = await service.start_concurrent_operation(
                user_id=user_id,
                operation_type="generation",
                job_id=job_id,
                duration_minutes=30,
            )

            await db.commit()

            return operation_id

    async def record_generation_end(self, operation_id: UUID) -> None:
        """Record that a generation has completed."""
        async with self.db_session_factory() as db:
            from app.core.usage_limits import UsageLimitService

            service = UsageLimitService(db)
            await service.end_concurrent_operation(operation_id)
            await db.commit()
