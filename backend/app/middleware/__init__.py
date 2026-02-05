"""
Middleware package.
"""

from app.middleware.abuse_protection import (
    AbuseProtectionMiddleware,
    GenerationGuardMiddleware,
    get_client_ip,
)
from app.middleware.security import (
    IPBlockingMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    SecurityLoggingMiddleware,
    block_ip,
    register_security_middleware,
    unblock_ip,
)

__all__ = [
    # Abuse Protection
    "AbuseProtectionMiddleware",
    "GenerationGuardMiddleware",
    "IPBlockingMiddleware",
    "RateLimitMiddleware",
    "RequestIdMiddleware",
    # Security
    "SecurityHeadersMiddleware",
    "SecurityLoggingMiddleware",
    "block_ip",
    "get_client_ip",
    "register_security_middleware",
    "unblock_ip",
]
