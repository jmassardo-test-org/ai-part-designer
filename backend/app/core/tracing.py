"""
OpenTelemetry distributed tracing configuration.

Provides distributed tracing for debugging cross-service issues with full
request path visibility and timing for each operation. Integrates with
Jaeger for trace visualization and analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = get_logger(__name__)


def configure_tracing() -> TracerProvider | None:
    """
    Configure OpenTelemetry tracing with appropriate exporters.

    Sets up tracing based on environment configuration:
    - Production: Exports to Jaeger or OTLP collector
    - Development: Exports to console and Jaeger (if configured)
    - Test: Uses in-memory exporter

    Returns:
        Configured TracerProvider instance, or None if tracing is disabled.
    """
    settings = get_settings()

    # Check if tracing is enabled
    if not settings.TRACING_ENABLED:
        logger.info("tracing_disabled", reason="TRACING_ENABLED=False")
        return None

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": settings.APP_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure exporters based on environment
    if settings.ENVIRONMENT == "test":
        # Use console exporter for tests (can be suppressed in CI)
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        logger.info("tracing_configured", exporter="console", mode="test")
    else:
        # Check if Jaeger is configured
        jaeger_host = settings.JAEGER_HOST
        jaeger_port = settings.JAEGER_PORT

        try:
            # Try Jaeger exporter first
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_host,
                agent_port=jaeger_port,
            )
            provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            logger.info(
                "tracing_configured",
                exporter="jaeger",
                host=jaeger_host,
                port=jaeger_port,
            )
        except Exception as e:
            logger.warning(
                "jaeger_exporter_failed",
                error=str(e),
                fallback="otlp",
            )

            # Fallback to OTLP if Jaeger fails
            try:
                otlp_endpoint = settings.OTLP_ENDPOINT
                otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                logger.info(
                    "tracing_configured",
                    exporter="otlp",
                    endpoint=otlp_endpoint,
                )
            except Exception as otlp_error:
                logger.warning(
                    "otlp_exporter_failed",
                    error=str(otlp_error),
                    fallback="console",
                )
                # Last resort: console exporter
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
                logger.info("tracing_configured", exporter="console", mode="fallback")

        # In development, also add console exporter for debugging
        if settings.DEBUG:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.info("tracing_debug_enabled", exporter="console")

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    return provider


def instrument_fastapi(app: FastAPI) -> None:
    """
    Instrument FastAPI application with OpenTelemetry.

    Adds automatic tracing for all HTTP requests with:
    - Request method and path
    - Response status code
    - Request duration
    - Automatic span naming

    Args:
        app: FastAPI application instance to instrument.
    """
    try:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=trace.get_tracer_provider(),
            excluded_urls="health,metrics,docs,redoc,openapi.json",
        )
        logger.info("fastapi_instrumented")
    except Exception as e:
        logger.warning("fastapi_instrumentation_failed", error=str(e))


def instrument_database(engine: AsyncEngine) -> None:
    """
    Instrument SQLAlchemy engine with OpenTelemetry.

    Adds automatic tracing for all database operations:
    - SQL queries with timing
    - Connection pool metrics
    - Transaction boundaries

    Args:
        engine: SQLAlchemy async engine instance to instrument.
    """
    try:
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,
            tracer_provider=trace.get_tracer_provider(),
        )
        logger.info("database_instrumented")
    except Exception as e:
        logger.warning("database_instrumentation_failed", error=str(e))


def instrument_redis() -> None:
    """
    Instrument Redis client with OpenTelemetry.

    Adds automatic tracing for all Redis operations:
    - Command names and timing
    - Connection information
    - Error tracking
    """
    try:
        RedisInstrumentor().instrument(
            tracer_provider=trace.get_tracer_provider(),
        )
        logger.info("redis_instrumented")
    except Exception as e:
        logger.warning("redis_instrumentation_failed", error=str(e))


def instrument_httpx() -> None:
    """
    Instrument httpx HTTP client with OpenTelemetry.

    Adds automatic tracing for all HTTP requests to external APIs:
    - Request method and URL
    - Response status code
    - Request duration
    - Automatic context propagation

    This enables distributed tracing across service boundaries.
    """
    try:
        HTTPXClientInstrumentor().instrument(
            tracer_provider=trace.get_tracer_provider(),
        )
        logger.info("httpx_instrumented")
    except Exception as e:
        logger.warning("httpx_instrumentation_failed", error=str(e))


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer for manual span creation.

    Use this to create custom spans for specific operations that need
    detailed tracing beyond automatic instrumentation.

    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("custom_operation") as span:
            span.set_attribute("custom.attribute", "value")
            # ... operation code ...

    Args:
        name: Tracer name, typically __name__ of the module.

    Returns:
        Tracer instance for creating spans.
    """
    return trace.get_tracer(name)


def shutdown_tracing() -> None:
    """
    Gracefully shutdown tracing and flush pending spans.

    Should be called during application shutdown to ensure all
    traces are exported before termination.
    """
    try:
        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
        logger.info("tracing_shutdown_complete")
    except Exception as e:
        logger.warning("tracing_shutdown_failed", error=str(e))
