"""
Tests for request context middleware.

Tests that request_id, user_id, path, and method are properly bound
to structlog context variables during request processing.
"""

from __future__ import annotations

import json
import logging
from io import StringIO
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import AsyncClient

from app.core.logging import configure_structlog, get_logger
from app.middleware.request_context import RequestContextMiddleware

# =============================================================================
# Test Application Setup
# =============================================================================


def create_test_app() -> FastAPI:
    """Create a test FastAPI app with request context middleware."""
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request) -> JSONResponse:
        """Test endpoint that logs and returns request state."""
        logger = get_logger("test.endpoint")
        logger.info("test_request_processed", extra_field="test_value")

        return JSONResponse(
            {
                "request_id": getattr(request.state, "request_id", None),
                "user_id": getattr(request.state, "user_id", None),
            }
        )

    @app.get("/test-with-user")
    async def test_endpoint_with_user(request: Request) -> JSONResponse:
        """Test endpoint with user context."""
        # Simulate user being set by auth middleware
        request.state.user_id = "test-user-123"

        logger = get_logger("test.endpoint")
        logger.info("test_request_with_user")

        return JSONResponse({"status": "ok"})

    return app


# =============================================================================
# Request Context Middleware Tests
# =============================================================================


class TestRequestContextMiddleware:
    """Tests for RequestContextMiddleware."""

    @pytest.mark.asyncio
    async def test_generates_request_id(self):
        """Test middleware generates request_id if not provided."""
        app = create_test_app()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/test")

        assert response.status_code == 200
        data = response.json()

        # Request ID should be generated
        assert data["request_id"] is not None
        assert len(data["request_id"]) > 0

        # Should be in response headers
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] == data["request_id"]

    @pytest.mark.asyncio
    async def test_uses_provided_request_id(self):
        """Test middleware uses X-Request-ID header if provided."""
        app = create_test_app()
        custom_request_id = "custom-request-id-12345"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/test",
                headers={"X-Request-ID": custom_request_id},
            )

        assert response.status_code == 200
        data = response.json()

        # Should use provided request ID
        assert data["request_id"] == custom_request_id
        assert response.headers["X-Request-ID"] == custom_request_id

    @pytest.mark.asyncio
    async def test_binds_request_context_to_logs(self, monkeypatch):
        """Test that request context is bound to structlog."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.logging.get_settings",
            lambda: Settings(ENVIRONMENT="production", APP_NAME="test-app", APP_VERSION="1.0.0"),
        )

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure structlog
        configure_structlog()

        # Replace handler to capture output
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

        # Create app and make request
        app = create_test_app()
        custom_request_id = "test-request-456"

        async with AsyncClient(app=app, base_url="http://test") as client:
            await client.get(
                "/test",
                headers={"X-Request-ID": custom_request_id},
            )

        # Get log output
        log_output = log_stream.getvalue()
        log_lines = [line for line in log_output.strip().split("\n") if line]

        # Find the log entry from our endpoint
        log_data = None
        for line in log_lines:
            try:
                data = json.loads(line)
                if data.get("event") == "test_request_processed":
                    log_data = data
                    break
            except json.JSONDecodeError:
                continue

        assert log_data is not None, "Could not find log entry from endpoint"

        # Verify request context is in logs
        assert log_data["request_id"] == custom_request_id
        assert log_data["path"] == "/test"
        assert log_data["method"] == "GET"
        assert log_data["extra_field"] == "test_value"

    @pytest.mark.asyncio
    async def test_includes_user_id_when_available(self, monkeypatch):
        """Test that user_id is included in logs when user is authenticated."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.logging.get_settings",
            lambda: Settings(ENVIRONMENT="production", APP_NAME="test-app", APP_VERSION="1.0.0"),
        )

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure structlog
        configure_structlog()

        # Replace handler to capture output
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

        # Create app and make request
        app = create_test_app()

        async with AsyncClient(app=app, base_url="http://test") as client:
            await client.get("/test-with-user")

        # Get log output
        log_output = log_stream.getvalue()
        log_lines = [line for line in log_output.strip().split("\n") if line]

        # Find the log entry from our endpoint
        log_data = None
        for line in log_lines:
            try:
                data = json.loads(line)
                if data.get("event") == "test_request_with_user":
                    log_data = data
                    break
            except json.JSONDecodeError:
                continue

        assert log_data is not None, "Could not find log entry from endpoint"

        # Verify user context is in logs
        assert log_data["user_id"] == "test-user-123"

    @pytest.mark.asyncio
    async def test_clears_context_between_requests(self, monkeypatch):
        """Test that context is cleared between requests to prevent leakage."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.logging.get_settings",
            lambda: Settings(ENVIRONMENT="production", APP_NAME="test-app", APP_VERSION="1.0.0"),
        )

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure structlog
        configure_structlog()

        # Replace handler to capture output
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

        # Create app
        app = create_test_app()

        async with AsyncClient(app=app, base_url="http://test") as client:
            # First request with user
            await client.get("/test-with-user")

            # Second request without user
            await client.get("/test")

        # Get all log output
        log_output = log_stream.getvalue()
        log_lines = [line for line in log_output.strip().split("\n") if line]

        # Find both log entries
        first_request_log = None
        second_request_log = None

        for line in log_lines:
            try:
                data = json.loads(line)
                if data.get("event") == "test_request_with_user":
                    first_request_log = data
                elif data.get("event") == "test_request_processed":
                    second_request_log = data
            except json.JSONDecodeError:
                continue

        # Verify both requests logged
        assert first_request_log is not None, "Could not find first request log"
        assert second_request_log is not None, "Could not find second request log"

        # First request should have user_id
        assert first_request_log["user_id"] == "test-user-123"

        # Second request should NOT have user_id (context was cleared)
        assert "user_id" not in second_request_log

    @pytest.mark.asyncio
    async def test_handles_user_object_with_id(self):
        """Test middleware extracts user_id from user object."""
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.get("/test-user-object")
        async def test_with_user_object(request: Request) -> JSONResponse:
            # Simulate user object being set by auth middleware
            mock_user = MagicMock()
            mock_user.id = "user-from-object-789"
            request.state.user = mock_user

            # Trigger middleware context binding by logging
            logger = get_logger("test")
            logger.info("test_user_object")

            return JSONResponse({"status": "ok"})

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/test-user-object")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_middleware_order_with_existing_request_id(self):
        """Test that middleware works with request_id set by other middleware."""
        app = FastAPI()

        # Simulate another middleware setting request_id
        @app.middleware("http")
        async def set_request_id(request: Request, call_next):
            request.state.request_id = "preset-id-999"
            return await call_next(request)

        app.add_middleware(RequestContextMiddleware)

        @app.get("/test")
        async def test_endpoint(request: Request) -> JSONResponse:
            return JSONResponse(
                {"request_id": getattr(request.state, "request_id", None)}
            )

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/test")

        data = response.json()
        # Should use request_id set by other middleware
        assert data["request_id"] == "preset-id-999"
        assert response.headers["X-Request-ID"] == "preset-id-999"
