"""
Prometheus metrics configuration.

Provides Prometheus metrics for monitoring application health, performance,
and business KPIs including request metrics, database pool metrics, Redis metrics,
and custom business metrics for CAD generation and exports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from app.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = get_logger(__name__)

# =============================================================================
# Custom Business Metrics
# =============================================================================

# CAD Generation Metrics
cad_generations_total = Counter(
    "cad_generations_total",
    "Total number of CAD model generations",
    ["status", "template_type"],
)

cad_generation_duration = Histogram(
    "cad_generation_duration_seconds",
    "Time spent generating CAD models",
    ["template_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf")),
)

# Export Metrics
exports_total = Counter(
    "exports_total",
    "Total number of file exports",
    ["format", "status"],
)

export_duration = Histogram(
    "export_duration_seconds",
    "Time spent exporting files",
    ["format"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, float("inf")),
)

# AI Interaction Metrics
ai_requests_total = Counter(
    "ai_requests_total",
    "Total number of AI API requests",
    ["provider", "model", "status"],
)

ai_request_duration = Histogram(
    "ai_request_duration_seconds",
    "Time spent on AI API requests",
    ["provider", "model"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")),
)

ai_tokens_used = Counter(
    "ai_tokens_used_total",
    "Total number of AI tokens consumed",
    ["provider", "model", "token_type"],
)

# User Activity Metrics
user_registrations_total = Counter(
    "user_registrations_total",
    "Total number of user registrations",
    ["method"],
)

user_logins_total = Counter(
    "user_logins_total",
    "Total number of user logins",
    ["method", "status"],
)

# Design Metrics
designs_created_total = Counter(
    "designs_created_total",
    "Total number of designs created",
    ["template_type"],
)

designs_shared_total = Counter(
    "designs_shared_total",
    "Total number of designs shared",
)

# =============================================================================
# Database Connection Pool Metrics
# =============================================================================

db_pool_size = Gauge(
    "db_pool_size",
    "Current database connection pool size",
)

db_pool_checked_out = Gauge(
    "db_pool_checked_out_connections",
    "Number of connections currently checked out from the pool",
)

db_pool_overflow = Gauge(
    "db_pool_overflow_connections",
    "Number of connections in the overflow pool",
)

db_pool_checkedin = Gauge(
    "db_pool_checkedin_connections",
    "Number of connections checked into the pool",
)

# =============================================================================
# Redis Metrics
# =============================================================================

redis_commands_total = Counter(
    "redis_commands_total",
    "Total number of Redis commands executed",
    ["command", "status"],
)

redis_command_duration = Histogram(
    "redis_command_duration_seconds",
    "Time spent executing Redis commands",
    ["command"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float("inf")),
)

redis_connection_errors = Counter(
    "redis_connection_errors_total",
    "Total number of Redis connection errors",
)

redis_connected = Gauge(
    "redis_connected",
    "Whether Redis is connected (1) or not (0)",
)


# =============================================================================
# Metrics Collection Functions
# =============================================================================


async def collect_db_pool_metrics() -> None:
    """
    Collect database connection pool metrics.

    Updates Prometheus gauges with current pool statistics from SQLAlchemy.
    """
    try:
        from app.core.database import engine

        pool = engine.pool
        db_pool_size.set(pool.size())
        db_pool_checked_out.set(pool.checkedout())
        db_pool_overflow.set(pool.overflow())
        # Checked-in connections = size - checked out - overflow
        checked_in = pool.size() - pool.checkedout() - pool.overflow()
        db_pool_checkedin.set(max(0, checked_in))
    except Exception as e:
        logger.warning("failed_to_collect_db_metrics", error=str(e))


async def collect_redis_metrics() -> None:
    """
    Collect Redis connection metrics.

    Updates Prometheus gauges with current Redis connection status.
    """
    try:
        from app.core.cache import redis_client

        # Check if Redis is connected
        if redis_client._client:
            try:
                await redis_client.client.ping()
                redis_connected.set(1)
            except Exception:
                redis_connected.set(0)
        else:
            redis_connected.set(0)
    except Exception as e:
        logger.warning("failed_to_collect_redis_metrics", error=str(e))
        redis_connected.set(0)


# =============================================================================
# Instrumentator Setup
# =============================================================================


def setup_metrics(app: FastAPI) -> Instrumentator:
    """
    Configure Prometheus metrics for the FastAPI application.

    Adds default HTTP metrics (requests, latency, status codes) and
    custom business metrics. Exposes metrics at /metrics endpoint.

    Args:
        app: The FastAPI application instance.

    Returns:
        Configured Instrumentator instance.
    """
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/docs", "/redoc", "/openapi.json"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    # Add default metrics
    instrumentator.add(
        metrics.request_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )
    instrumentator.add(
        metrics.response_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )
    instrumentator.add(
        metrics.latency(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 30.0, 60.0, float("inf")),
        )
    )
    instrumentator.add(metrics.requests())

    # Instrument the app and expose /metrics endpoint
    # Note: expose() must be chained with instrument() for proper route registration
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    logger.info("prometheus_metrics_configured")

    return instrumentator
