"""
AI Part Designer API.

FastAPI application entry point with middleware, routes, and lifecycle hooks.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api import api_router
from app.api.v2 import api_router as api_router_v2
from app.core.config import get_settings
from app.core.logging import configure_structlog, get_logger
from app.core.metrics import collect_db_pool_metrics, collect_redis_metrics, setup_metrics
from app.middleware.request_context import RequestContextMiddleware

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Configure structured logging
configure_structlog()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Handles startup and shutdown events:
    - Initialize database connections
    - Start background workers
    - Cleanup on shutdown
    """
    settings = get_settings()
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    # Startup
    try:
        # Initialize database
        from app.core.database import init_db

        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.warning("database_initialization_failed", error=str(e), exc_info=True)

    try:
        # Initialize cache
        from app.core.cache import redis_client

        await redis_client.connect()
        await redis_client.client.ping()
        logger.info("redis_connected")

        # Start WebSocket Redis subscriber
        from app.websocket.subscriber import start_redis_subscriber

        await start_redis_subscriber()
        logger.info("websocket_subscriber_started")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e), exc_info=True)

    # Check AI configuration
    try:
        from app.ai.providers import get_ai_provider

        provider = get_ai_provider()
        health_ok = await provider.health_check()
        if health_ok:
            logger.info(
                "ai_provider_ready",
                provider_name=provider.name,
                model=getattr(provider, "model", "N/A"),
            )
        else:
            logger.warning(
                "ai_provider_unhealthy",
                provider_name=provider.name,
            )
    except Exception as e:
        logger.warning("ai_provider_initialization_failed", error=str(e), exc_info=True)

    # Collect initial metrics
    try:
        await collect_db_pool_metrics()
        await collect_redis_metrics()
        logger.info("initial_metrics_collected")
    except Exception as e:
        logger.warning("initial_metrics_collection_failed", error=str(e), exc_info=True)

    yield

    # Shutdown
    logger.info("application_shutting_down")

    try:
        # Stop WebSocket Redis subscriber
        from app.websocket.subscriber import stop_redis_subscriber

        await stop_redis_subscriber()
        logger.info("websocket_subscriber_stopped")
    except Exception as e:
        logger.warning("redis_subscriber_shutdown_error", error=str(e), exc_info=True)

    try:
        from app.core.database import close_db

        await close_db()
        logger.info("database_connections_closed")
    except Exception as e:
        logger.warning("database_shutdown_error", error=str(e), exc_info=True)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered CAD part generation from natural language",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Add session middleware for OAuth state management
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie="session",
        max_age=3600,  # 1 hour session
        same_site="lax",
        https_only=settings.ENVIRONMENT == "production",
    )

    # Add request context middleware for structured logging
    app.add_middleware(RequestContextMiddleware)

    # Setup Prometheus metrics and expose /metrics endpoint
    setup_metrics(app)

    # Include API routes
    app.include_router(api_router)
    app.include_router(api_router_v2)

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Handle validation errors with clean messages."""
        errors = []
        for error in exc.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            errors.append(f"{loc}: {error['msg']}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "detail": errors,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception(
            "unhandled_exception",
            error_type=type(exc).__name__,
            error=str(exc),
            path=request.url.path,
            method=request.method,
        )

        # Get origin for CORS headers
        origin = request.headers.get("origin", "")
        cors_headers = {}
        if origin in settings.ALLOWED_ORIGINS:
            cors_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            }

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.DEBUG else None,
            },
            headers=cors_headers,
        )

    return app


# Create app instance
app = create_app()
