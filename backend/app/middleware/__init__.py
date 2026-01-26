"""
Middleware package.
"""

from app.middleware.security import (
    SecurityHeadersMiddleware,
    RequestIdMiddleware,
    SecurityLoggingMiddleware,
    RateLimitMiddleware,
    IPBlockingMiddleware,
    register_security_middleware,
    block_ip,
    unblock_ip,
)
from app.middleware.abuse_protection import (
    AbuseProtectionMiddleware,
    GenerationGuardMiddleware,
    get_client_ip,
)

__all__ = [
    # Security
    "SecurityHeadersMiddleware",
    "RequestIdMiddleware",
    "SecurityLoggingMiddleware",
    "RateLimitMiddleware",
    "IPBlockingMiddleware",
    "register_security_middleware",
    "block_ip",
    "unblock_ip",
    # Abuse Protection
    "AbuseProtectionMiddleware",
    "GenerationGuardMiddleware",
    "get_client_ip",
]
