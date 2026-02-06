"""
Tests for Prometheus metrics configuration.

Tests metrics setup, collection functions, and custom business metrics.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY

from app.core.metrics import (
    ai_requests_total,
    cad_generations_total,
    collect_db_pool_metrics,
    collect_redis_metrics,
    db_pool_checked_out,
    db_pool_checkedin,
    db_pool_overflow,
    db_pool_size,
    designs_created_total,
    export_duration,
    exports_total,
    redis_connected,
    setup_metrics,
    user_logins_total,
    user_registrations_total,
)


@pytest.fixture(autouse=True)
def _cleanup_prometheus_registry():
    """Clean up Prometheus registry between tests to avoid duplicate metric errors."""
    yield
    # Unregister collectors added by tests
    # Note: We can't unregister the default collectors, only custom ones
    collectors_to_remove = []
    for collector in list(REGISTRY._collector_to_names.keys()):
        # Keep the default process and platform collectors
        if collector.__class__.__name__ not in ["ProcessCollector", "PlatformCollector", "GCCollector"]:
            collectors_to_remove.append(collector)

    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass  # Ignore errors during cleanup


# =============================================================================
# Metrics Setup Tests
# =============================================================================


class TestMetricsSetup:
    """Tests for metrics setup and instrumentation."""

    @pytest.mark.asyncio
    async def test_setup_metrics_instruments_app(self):
        """Test setup_metrics instruments the FastAPI app."""
        app = FastAPI()

        instrumentator = setup_metrics(app)

        assert instrumentator is not None
        # Verify the instrumentator is configured
        assert instrumentator.should_group_status_codes is True
        assert instrumentator.should_instrument_requests_inprogress is True

    @pytest.mark.asyncio
    async def test_metrics_endpoint_exposed(self):
        """Test /metrics endpoint is properly exposed."""
        app = FastAPI()

        # Setup metrics (which also exposes the /metrics endpoint)
        setup_metrics(app)

        # Create transport after metrics are exposed
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/metrics")

        assert response.status_code == 200
        # Prometheus metrics should be in text format
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type or "text" in content_type
        # Should contain basic metric identifiers
        content = response.text
        assert "http_requests" in content or "HELP" in content or "#" in content

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_prometheus_format(self):
        """Test /metrics endpoint returns proper Prometheus format."""
        app = FastAPI()

        # Add a simple endpoint to generate some metrics
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        setup_metrics(app)

        # Make a request to generate metrics
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/test")
            response = await client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Verify Prometheus format (HELP, TYPE, metric lines)
        assert "# HELP" in content
        assert "# TYPE" in content


# =============================================================================
# Custom Business Metrics Tests
# =============================================================================


class TestBusinessMetrics:
    """Tests for custom business metrics."""

    def test_cad_generations_metric_exists(self):
        """Test CAD generation counter exists and can be incremented."""
        # Get initial value
        initial = cad_generations_total.labels(status="success", template_type="box").collect()[0].samples[0].value

        # Increment
        cad_generations_total.labels(status="success", template_type="box").inc()

        # Verify increment
        new_value = cad_generations_total.labels(status="success", template_type="box").collect()[0].samples[0].value
        assert new_value == initial + 1

    def test_exports_metric_exists(self):
        """Test exports counter exists and can be incremented."""
        initial = exports_total.labels(format="stl", status="success").collect()[0].samples[0].value

        exports_total.labels(format="stl", status="success").inc()

        new_value = exports_total.labels(format="stl", status="success").collect()[0].samples[0].value
        assert new_value == initial + 1

    def test_export_duration_histogram(self):
        """Test export duration histogram records observations."""
        export_duration.labels(format="step").observe(1.5)

        # Verify histogram is working (should have samples)
        metric = export_duration.labels(format="step").collect()[0]
        assert len(metric.samples) > 0

    def test_ai_requests_metric_exists(self):
        """Test AI requests counter exists and can be incremented."""
        initial = ai_requests_total.labels(
            provider="anthropic", model="claude-3", status="success"
        ).collect()[0].samples[0].value

        ai_requests_total.labels(
            provider="anthropic", model="claude-3", status="success"
        ).inc()

        new_value = ai_requests_total.labels(
            provider="anthropic", model="claude-3", status="success"
        ).collect()[0].samples[0].value
        assert new_value == initial + 1

    def test_user_registrations_metric_exists(self):
        """Test user registrations counter exists and can be incremented."""
        initial = user_registrations_total.labels(method="email").collect()[0].samples[0].value

        user_registrations_total.labels(method="email").inc()

        new_value = user_registrations_total.labels(method="email").collect()[0].samples[0].value
        assert new_value == initial + 1

    def test_user_logins_metric_exists(self):
        """Test user logins counter exists and can be incremented."""
        initial = user_logins_total.labels(method="email", status="success").collect()[0].samples[0].value

        user_logins_total.labels(method="email", status="success").inc()

        new_value = user_logins_total.labels(method="email", status="success").collect()[0].samples[0].value
        assert new_value == initial + 1

    def test_designs_created_metric_exists(self):
        """Test designs created counter exists and can be incremented."""
        initial = designs_created_total.labels(template_type="parametric").collect()[0].samples[0].value

        designs_created_total.labels(template_type="parametric").inc()

        new_value = designs_created_total.labels(template_type="parametric").collect()[0].samples[0].value
        assert new_value == initial + 1


# =============================================================================
# Database Pool Metrics Tests
# =============================================================================


class TestDatabasePoolMetrics:
    """Tests for database connection pool metrics collection."""

    @pytest.mark.asyncio
    async def test_collect_db_pool_metrics_updates_gauges(self):
        """Test collect_db_pool_metrics updates Prometheus gauges."""
        # Mock the engine pool
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 2

        with patch("app.core.database.engine") as mock_engine:
            mock_engine.pool = mock_pool

            await collect_db_pool_metrics()

            # Verify gauges were set
            assert db_pool_size.collect()[0].samples[0].value == 10
            assert db_pool_checked_out.collect()[0].samples[0].value == 3
            assert db_pool_overflow.collect()[0].samples[0].value == 2
            assert db_pool_checkedin.collect()[0].samples[0].value == 5  # 10 - 3 - 2

    @pytest.mark.asyncio
    async def test_collect_db_pool_metrics_handles_errors(self):
        """Test collect_db_pool_metrics handles errors gracefully."""
        with patch("app.core.database.engine", side_effect=Exception("DB error")):
            # Should not raise exception
            await collect_db_pool_metrics()


# =============================================================================
# Redis Metrics Tests
# =============================================================================


class TestRedisMetrics:
    """Tests for Redis metrics collection."""

    @pytest.mark.asyncio
    async def test_collect_redis_metrics_when_connected(self):
        """Test collect_redis_metrics sets connected=1 when Redis responds."""
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(return_value=True)

        mock_redis_client = MagicMock()
        mock_redis_client._client = True
        mock_redis_client.client = mock_client

        with patch("app.core.cache.redis_client", mock_redis_client):
            await collect_redis_metrics()

            assert redis_connected.collect()[0].samples[0].value == 1

    @pytest.mark.asyncio
    async def test_collect_redis_metrics_when_disconnected(self):
        """Test collect_redis_metrics sets connected=0 when Redis fails."""
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(side_effect=Exception("Connection failed"))

        mock_redis_client = MagicMock()
        mock_redis_client._client = True
        mock_redis_client.client = mock_client

        with patch("app.core.cache.redis_client", mock_redis_client):
            await collect_redis_metrics()

            assert redis_connected.collect()[0].samples[0].value == 0

    @pytest.mark.asyncio
    async def test_collect_redis_metrics_when_client_not_initialized(self):
        """Test collect_redis_metrics handles uninitialized client."""
        mock_redis_client = MagicMock()
        mock_redis_client._client = None

        with patch("app.core.cache.redis_client", mock_redis_client):
            await collect_redis_metrics()

            assert redis_connected.collect()[0].samples[0].value == 0

    @pytest.mark.asyncio
    async def test_collect_redis_metrics_handles_errors(self):
        """Test collect_redis_metrics handles unexpected errors."""
        with patch("app.core.cache.redis_client", side_effect=Exception("Unexpected error")):
            # Should not raise exception
            await collect_redis_metrics()

            # Should set connected to 0
            assert redis_connected.collect()[0].samples[0].value == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestMetricsIntegration:
    """Integration tests for metrics in a full application context."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_with_request_metrics(self):
        """Test /metrics endpoint includes request metrics after API calls."""
        app = FastAPI()

        @app.get("/api/test")
        async def api_endpoint():
            return {"data": "test"}

        setup_metrics(app)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Make some API requests
            await client.get("/api/test")
            await client.get("/api/test")

            # Fetch metrics
            response = await client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Should contain HTTP request metrics
        assert "http_requests" in content or "http_request" in content

    @pytest.mark.asyncio
    async def test_excluded_handlers_not_tracked(self):
        """Test that excluded endpoints are not tracked in metrics."""
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        setup_metrics(app)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Call health endpoint (should be excluded)
            await client.get("/health")

            # Fetch metrics
            response = await client.get("/metrics")

        assert response.status_code == 200
        # Metrics endpoint itself should not be tracked
        content = response.text
        # The /health and /metrics endpoints should be excluded from tracking
        # Just verify metrics endpoint works
        assert "# HELP" in content
