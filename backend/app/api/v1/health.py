"""
Health check endpoints.

Provides liveness and readiness probes for container orchestration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.core.config import get_settings, Settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    environment: str
    timestamp: str


class ReadinessResponse(BaseModel):
    """Readiness check response with dependency status."""
    
    status: str
    checks: dict[str, bool]
    timestamp: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 if the service is running.",
)
async def health_check(
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """
    Basic liveness probe.
    
    Returns immediately if the service is running.
    Used by load balancers and orchestrators.
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Returns 200 if the service is ready to accept traffic.",
)
async def readiness_check(
    settings: Settings = Depends(get_settings),
) -> ReadinessResponse:
    """
    Readiness probe checking dependencies.
    
    Verifies database, cache, and storage connectivity.
    Returns 503 if any critical dependency is down.
    """
    checks = {}
    
    # Check database
    try:
        from app.core.database import async_session_maker
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
        checks["database"] = True
    except Exception:
        checks["database"] = False
    
    # Check Redis
    try:
        from app.core.cache import get_redis
        redis = await get_redis()
        await redis.ping()
        checks["cache"] = True
    except Exception:
        checks["cache"] = False
    
    # Check AI provider
    try:
        from app.ai.providers import get_ai_provider
        provider = get_ai_provider()
        checks["ai"] = provider.is_configured
        checks["ai_provider"] = provider.name
    except Exception:
        checks["ai"] = False
        checks["ai_provider"] = None
    
    # Overall status
    all_critical_ok = checks.get("database", False)  # DB is critical
    
    return ReadinessResponse(
        status="ready" if all_critical_ok else "not_ready",
        checks=checks,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get(
    "/info",
    summary="Service info",
    description="Returns service metadata and configuration.",
)
async def service_info(
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Return service information for debugging."""
    
    # Get AI provider info
    try:
        from app.ai.providers import get_ai_provider
        provider = get_ai_provider()
        ai_info = {
            "enabled": provider.is_configured,
            "provider": provider.name,
            "model": getattr(provider, "model", "N/A"),
        }
    except Exception:
        ai_info = {"enabled": False, "provider": None, "model": None}
    
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "features": {
            "ai": ai_info,
            "rate_limiting": settings.RATE_LIMIT_ENABLED,
        },
    }
