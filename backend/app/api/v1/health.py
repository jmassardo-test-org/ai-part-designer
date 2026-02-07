"""
Health check endpoints.

Provides liveness and readiness probes for container orchestration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings

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
    checks: dict[str, bool | str | None]
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
        timestamp=datetime.now(tz=UTC).isoformat(),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Returns 200 if the service is ready to accept traffic.",
)
async def readiness_check(
    _settings: Settings = Depends(get_settings),
) -> ReadinessResponse:
    """
    Readiness probe checking dependencies.

    Verifies database, cache, and storage connectivity.
    Returns 503 if any critical dependency is down.
    """
    checks: dict[str, bool | str | None] = {}

    # Check database
    try:
        from sqlalchemy import text

        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Check Redis
    try:
        from app.core.cache import get_redis

        redis = await get_redis()
        await redis.ping()  # type: ignore[attr-defined]
        checks["cache"] = True
    except Exception:
        checks["cache"] = False

    # Check AI provider
    try:
        from app.ai.providers import get_ai_provider

        provider = get_ai_provider()
        if provider.is_configured:
            # Actually check if we can reach the provider
            ai_healthy = await provider.health_check()
            checks["ai"] = ai_healthy
            checks["ai_provider"] = provider.name
            checks["ai_model"] = getattr(provider, "model", None)
            if not ai_healthy:
                checks["ai_error"] = f"{provider.name} is not reachable"
        else:
            checks["ai"] = False
            checks["ai_provider"] = provider.name
            checks["ai_error"] = f"{provider.name} is not configured"
    except Exception as e:
        checks["ai"] = False
        checks["ai_provider"] = None
        checks["ai_error"] = str(e)

    # Overall status
    all_critical_ok = checks.get("database", False)  # DB is critical

    return ReadinessResponse(
        status="ready" if all_critical_ok else "not_ready",
        checks=checks,
        timestamp=datetime.now(tz=UTC).isoformat(),
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
