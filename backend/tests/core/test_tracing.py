"""
Tests for OpenTelemetry distributed tracing configuration.

Tests tracing setup, instrumentation, and span export functionality.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.tracing import (
    configure_tracing,
    get_tracer,
    instrument_database,
    instrument_fastapi,
    instrument_httpx,
    instrument_redis,
    shutdown_tracing,
)

# =============================================================================
# Configuration Tests
# =============================================================================


class TestTracingConfiguration:
    """Tests for tracing configuration."""

    def test_configure_tracing_returns_provider(self, monkeypatch):
        """Test that configure_tracing returns a TracerProvider."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="development",
                APP_NAME="test-app",
                APP_VERSION="1.0.0",
                TRACING_ENABLED=True,
            ),
        )

        provider = configure_tracing()
        assert provider is not None
        assert isinstance(provider, TracerProvider)

    def test_configure_tracing_disabled(self, monkeypatch):
        """Test that tracing can be disabled via config."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="development",
                APP_NAME="test-app",
                APP_VERSION="1.0.0",
                TRACING_ENABLED=False,
            ),
        )

        provider = configure_tracing()
        assert provider is None

    def test_configure_tracing_production_uses_jaeger(self, monkeypatch):
        """Test that production environment attempts to use Jaeger exporter."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="production",
                APP_NAME="test-app",
                APP_VERSION="1.0.0",
                TRACING_ENABLED=True,
                JAEGER_HOST="jaeger.example.com",
                JAEGER_PORT=6831,
            ),
        )

        with patch("app.core.tracing.JaegerExporter") as mock_jaeger:
            mock_jaeger.return_value = MagicMock()
            provider = configure_tracing()

            assert provider is not None
            mock_jaeger.assert_called_once_with(
                agent_host_name="jaeger.example.com",
                agent_port=6831,
            )

    def test_configure_tracing_test_environment(self, monkeypatch):
        """Test that test environment uses console exporter."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="test",
                APP_NAME="test-app",
                APP_VERSION="1.0.0",
                TRACING_ENABLED=True,
            ),
        )

        provider = configure_tracing()
        assert provider is not None
        assert isinstance(provider, TracerProvider)

    def test_configure_tracing_sets_global_provider(self, monkeypatch):
        """Test that configure_tracing creates and returns a provider."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="test",
                APP_NAME="test-app",
                APP_VERSION="1.0.0",
                TRACING_ENABLED=True,
            ),
        )

        provider = configure_tracing()
        global_provider = trace.get_tracer_provider()

        # Verify provider is created and has correct resource attributes
        assert provider is not None
        assert isinstance(provider, TracerProvider)
        assert provider.resource.attributes["service.name"] == "test-app"
        assert provider.resource.attributes["service.version"] == "1.0.0"
        assert provider.resource.attributes["deployment.environment"] == "test"

        # Verify global provider was set (not the default NoOpTracerProvider)
        assert isinstance(global_provider, TracerProvider)


# =============================================================================
# Instrumentation Tests
# =============================================================================


class TestInstrumentation:
    """Tests for automatic instrumentation of libraries."""

    def test_instrument_fastapi_success(self):
        """Test that FastAPI instrumentation succeeds."""
        app = FastAPI()

        with patch("app.core.tracing.FastAPIInstrumentor") as mock_instrumentor:
            mock_instrumentor.instrument_app = MagicMock()
            instrument_fastapi(app)
            mock_instrumentor.instrument_app.assert_called_once()

    def test_instrument_fastapi_handles_error(self):
        """Test that FastAPI instrumentation handles errors gracefully."""
        app = FastAPI()

        with patch("app.core.tracing.FastAPIInstrumentor") as mock_instrumentor:
            mock_instrumentor.instrument_app.side_effect = Exception("Test error")
            # Should not raise exception
            instrument_fastapi(app)

    @pytest.mark.asyncio
    async def test_instrument_database_success(self):
        """Test that database instrumentation succeeds."""
        # Create a temporary in-memory SQLite engine for testing
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        with patch("app.core.tracing.SQLAlchemyInstrumentor") as mock_instrumentor:
            mock_instance = MagicMock()
            mock_instrumentor.return_value = mock_instance
            instrument_database(engine)
            mock_instance.instrument.assert_called_once()

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_instrument_database_handles_error(self):
        """Test that database instrumentation handles errors gracefully."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        with patch("app.core.tracing.SQLAlchemyInstrumentor") as mock_instrumentor:
            mock_instance = MagicMock()
            mock_instance.instrument.side_effect = Exception("Test error")
            mock_instrumentor.return_value = mock_instance
            # Should not raise exception
            instrument_database(engine)

        await engine.dispose()

    def test_instrument_redis_success(self):
        """Test that Redis instrumentation succeeds."""
        with patch("app.core.tracing.RedisInstrumentor") as mock_instrumentor:
            mock_instance = MagicMock()
            mock_instrumentor.return_value = mock_instance
            instrument_redis()
            mock_instance.instrument.assert_called_once()

    def test_instrument_redis_handles_error(self):
        """Test that Redis instrumentation handles errors gracefully."""
        with patch("app.core.tracing.RedisInstrumentor") as mock_instrumentor:
            mock_instance = MagicMock()
            mock_instance.instrument.side_effect = Exception("Test error")
            mock_instrumentor.return_value = mock_instance
            # Should not raise exception
            instrument_redis()

    def test_instrument_httpx_success(self):
        """Test that httpx instrumentation succeeds."""
        with patch("app.core.tracing.HTTPXClientInstrumentor") as mock_instrumentor:
            mock_instance = MagicMock()
            mock_instrumentor.return_value = mock_instance
            instrument_httpx()
            mock_instance.instrument.assert_called_once()

    def test_instrument_httpx_handles_error(self):
        """Test that httpx instrumentation handles errors gracefully."""
        with patch("app.core.tracing.HTTPXClientInstrumentor") as mock_instrumentor:
            mock_instance = MagicMock()
            mock_instance.instrument.side_effect = Exception("Test error")
            mock_instrumentor.return_value = mock_instance
            # Should not raise exception
            instrument_httpx()


# =============================================================================
# Tracer Tests
# =============================================================================


class TestTracer:
    """Tests for tracer functionality."""

    def test_get_tracer_returns_tracer(self, monkeypatch):
        """Test that get_tracer returns a valid tracer."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="test",
                APP_NAME="test-app",
                APP_VERSION="1.0.0",
                TRACING_ENABLED=True,
            ),
        )

        # Configure tracing first
        configure_tracing()

        tracer = get_tracer(__name__)
        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)

    def test_get_tracer_span_creation(self, monkeypatch):
        """Test that tracer can create spans."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="test",
                APP_NAME="test-app",
                APP_VERSION="1.0.0",
                TRACING_ENABLED=True,
            ),
        )

        # Configure tracing first
        configure_tracing()

        tracer = get_tracer(__name__)

        # Create a span
        with tracer.start_as_current_span("test_operation") as span:
            assert span is not None
            assert span.is_recording()
            span.set_attribute("test.attribute", "test_value")


# =============================================================================
# Shutdown Tests
# =============================================================================


class TestShutdown:
    """Tests for tracing shutdown."""

    def test_shutdown_tracing_success(self, monkeypatch):
        """Test that shutdown_tracing completes successfully."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="test",
                APP_NAME="test-app",
                APP_VERSION="1.0.0",
                TRACING_ENABLED=True,
            ),
        )

        # Configure tracing first
        provider = configure_tracing()
        assert provider is not None

        # Should not raise exception
        shutdown_tracing()

    def test_shutdown_tracing_handles_error(self):
        """Test that shutdown_tracing handles errors gracefully."""
        with patch("app.core.tracing.trace.get_tracer_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.shutdown.side_effect = Exception("Test error")
            mock_get_provider.return_value = mock_provider

            # Should not raise exception
            shutdown_tracing()

    def test_shutdown_tracing_without_shutdown_method(self):
        """Test that shutdown_tracing handles providers without shutdown method."""
        with patch("app.core.tracing.trace.get_tracer_provider") as mock_get_provider:
            # Provider without shutdown method
            mock_provider = object()
            mock_get_provider.return_value = mock_provider

            # Should not raise exception
            shutdown_tracing()


# =============================================================================
# Integration Tests
# =============================================================================


class TestTracingIntegration:
    """Integration tests for tracing with other components."""

    @pytest.mark.asyncio
    async def test_tracing_with_fastapi_request(self, monkeypatch):
        """Test that tracing works with FastAPI requests."""
        from httpx import ASGITransport, AsyncClient

        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="test",
                APP_NAME="test-app",
                APP_VERSION="1.0.0",
                TRACING_ENABLED=True,
            ),
        )

        # Configure tracing
        configure_tracing()

        # Create a simple FastAPI app
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # Instrument the app
        instrument_fastapi(app)

        # Make a request
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/test")
            assert response.status_code == 200
            assert response.json() == {"message": "test"}

    def test_tracing_resource_attributes(self, monkeypatch):
        """Test that tracing includes correct resource attributes."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.tracing.get_settings",
            lambda: Settings(
                ENVIRONMENT="production",
                APP_NAME="test-service",
                APP_VERSION="2.0.0",
                TRACING_ENABLED=True,
            ),
        )

        with patch("app.core.tracing.JaegerExporter") as mock_jaeger:
            mock_jaeger.return_value = MagicMock()
            provider = configure_tracing()

            # Check resource attributes
            assert provider is not None
            resource = provider.resource
            assert resource.attributes["service.name"] == "test-service"
            assert resource.attributes["service.version"] == "2.0.0"
            assert resource.attributes["deployment.environment"] == "production"
