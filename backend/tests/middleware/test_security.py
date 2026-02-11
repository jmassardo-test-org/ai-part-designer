"""
Tests for security middleware.

Tests security headers, request logging, 401/403 tracking, and rate limiting.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import AsyncClient

from app.middleware.security import (
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    SecurityLoggingMiddleware,
)

# =============================================================================
# Test Application Setup
# =============================================================================


def create_test_app() -> FastAPI:
    """Create a test FastAPI app with security middleware."""
    app = FastAPI()

    # Add middleware in reverse order (they execute in reverse)
    app.add_middleware(SecurityLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test/ok")
    async def test_ok(request: Request) -> JSONResponse:
        """Test endpoint that returns 200."""
        return JSONResponse({"status": "ok"})

    @app.get("/test/unauthorized")
    async def test_unauthorized(request: Request) -> JSONResponse:
        """Test endpoint that returns 401."""
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    @app.get("/test/forbidden")
    async def test_forbidden(request: Request) -> JSONResponse:
        """Test endpoint that returns 403."""
        return JSONResponse({"detail": "Forbidden"}, status_code=403)

    @app.get("/test/forbidden-with-user")
    async def test_forbidden_with_user(request: Request) -> JSONResponse:
        """Test endpoint that returns 403 with user context."""
        # Simulate authenticated user
        request.state.user_id = "test-user-123"
        return JSONResponse({"detail": "Forbidden"}, status_code=403)

    @app.get("/test/server-error")
    async def test_server_error(request: Request) -> JSONResponse:
        """Test endpoint that returns 500."""
        return JSONResponse({"detail": "Internal Server Error"}, status_code=500)

    return app


# =============================================================================
# Security Headers Middleware Tests
# =============================================================================


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        """Test that security headers are added to responses."""
        app = create_test_app()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/test/ok")

        assert response.status_code == 200

        # Check security headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_cache_control_on_api_routes(self):
        """Test that cache control headers are added to API routes."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/api/v1/test")
        async def api_test() -> JSONResponse:
            return JSONResponse({"data": "test"})

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/test")

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"
        assert response.headers["Pragma"] == "no-cache"


# =============================================================================
# Request ID Middleware Tests
# =============================================================================


class TestRequestIdMiddleware:
    """Tests for RequestIdMiddleware."""

    @pytest.mark.asyncio
    async def test_generates_request_id(self):
        """Test that request ID is generated if not provided."""
        app = create_test_app()

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/test/ok")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    @pytest.mark.asyncio
    async def test_uses_provided_request_id(self):
        """Test that provided X-Request-ID is used."""
        app = create_test_app()
        custom_id = "custom-request-123"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/test/ok",
                headers={"X-Request-ID": custom_id},
            )

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == custom_id


# =============================================================================
# Security Logging Middleware Tests
# =============================================================================


class TestSecurityLoggingMiddleware:
    """Tests for SecurityLoggingMiddleware."""

    @pytest.mark.asyncio
    async def test_logs_request(self, caplog):
        """Test that requests are logged."""
        app = create_test_app()

        with caplog.at_level(logging.INFO, logger="security"):
            async with AsyncClient(app=app, base_url="http://test") as client:
                await client.get("/test/ok")

        # Check that request was logged
        assert len(caplog.records) > 0
        log_record = caplog.records[0]
        assert log_record.levelname == "INFO"
        assert "Request completed" in log_record.message

    @pytest.mark.asyncio
    async def test_tracks_401_failed_auth(self, caplog):
        """Test that 401 responses trigger failed auth tracking."""
        app = create_test_app()

        # Mock redis_client.increment_counter
        with patch("app.middleware.security.redis_client") as mock_redis:
            mock_redis.increment_counter = AsyncMock(return_value=1)

            with caplog.at_level(logging.WARNING, logger="security"):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    await client.get("/test/unauthorized")

            # Verify increment_counter was called
            mock_redis.increment_counter.assert_called_once()
            call_args = mock_redis.increment_counter.call_args
            assert call_args[0][0].startswith("security:failed_auth:")
            assert call_args[1]["window_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_tracks_401_logs_warning_at_threshold(self, caplog):
        """Test that warning is logged when 401 threshold is exceeded."""
        app = create_test_app()

        with patch("app.middleware.security.redis_client") as mock_redis:
            mock_redis.increment_counter = AsyncMock(return_value=11)

            with caplog.at_level(logging.WARNING, logger="security"):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    await client.get("/test/unauthorized")

            # Check for warning log
            warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
            assert len(warning_logs) >= 1
            assert any("Multiple failed auth attempts" in r.message for r in warning_logs)

    @pytest.mark.asyncio
    async def test_tracks_403_forbidden_by_ip(self, caplog):
        """Test that 403 responses trigger failed authorization tracking by IP."""
        app = create_test_app()

        with patch("app.middleware.security.redis_client") as mock_redis:
            mock_redis.increment_counter = AsyncMock(return_value=1)

            with caplog.at_level(logging.WARNING, logger="security"):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    await client.get("/test/forbidden")

            # Verify increment_counter was called at least once (for IP)
            assert mock_redis.increment_counter.call_count >= 1

            # Check that IP tracking key was used
            call_args_list = mock_redis.increment_counter.call_args_list
            ip_calls = [
                call for call in call_args_list if "security:failed_authz:ip:" in call[0][0]
            ]
            assert len(ip_calls) == 1
            assert call_args_list[0][1]["window_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_tracks_403_forbidden_by_user(self, caplog):
        """Test that 403 responses with user_id track by both IP and user."""
        app = create_test_app()

        with patch("app.middleware.security.redis_client") as mock_redis:
            mock_redis.increment_counter = AsyncMock(return_value=1)

            with caplog.at_level(logging.WARNING, logger="security"):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    await client.get("/test/forbidden-with-user")

            # Should be called twice: once for IP, once for user
            assert mock_redis.increment_counter.call_count == 2

            call_args_list = mock_redis.increment_counter.call_args_list
            ip_calls = [
                call for call in call_args_list if "security:failed_authz:ip:" in call[0][0]
            ]
            user_calls = [
                call for call in call_args_list if "security:failed_authz:user:" in call[0][0]
            ]

            assert len(ip_calls) == 1
            assert len(user_calls) == 1
            assert "test-user-123" in user_calls[0][0][0]

    @pytest.mark.asyncio
    async def test_403_logs_warning_at_10_attempts(self, caplog):
        """Test that warning is logged at 10 forbidden attempts."""
        app = create_test_app()

        with patch("app.middleware.security.redis_client") as mock_redis:
            mock_redis.increment_counter = AsyncMock(return_value=10)

            with caplog.at_level(logging.WARNING, logger="security"):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    await client.get("/test/forbidden")

            # Check for warning log
            warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
            assert len(warning_logs) >= 1
            assert any("Multiple forbidden access attempts" in r.message for r in warning_logs)

    @pytest.mark.asyncio
    async def test_403_logs_error_at_20_attempts(self, caplog):
        """Test that error is logged at 20 forbidden attempts."""
        app = create_test_app()

        with patch("app.middleware.security.redis_client") as mock_redis:
            mock_redis.increment_counter = AsyncMock(return_value=20)

            with caplog.at_level(logging.ERROR, logger="security"):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    await client.get("/test/forbidden")

            # Check for error log
            error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
            assert len(error_logs) >= 1
            assert any("High volume of forbidden access attempts" in r.message for r in error_logs)
            assert any("enumeration attack" in r.message for r in error_logs)

    @pytest.mark.asyncio
    async def test_403_user_logs_error_at_20_attempts(self, caplog):
        """Test that error is logged at 20 user-based forbidden attempts."""
        app = create_test_app()

        with patch("app.middleware.security.redis_client") as mock_redis:
            # Return 5 for IP, 20 for user
            mock_redis.increment_counter = AsyncMock(side_effect=[5, 20])

            with caplog.at_level(logging.ERROR, logger="security"):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    await client.get("/test/forbidden-with-user")

            # Check for error log mentioning privilege escalation
            error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
            assert len(error_logs) >= 1
            assert any("privilege escalation" in r.message for r in error_logs)

    @pytest.mark.asyncio
    async def test_403_no_alert_under_threshold(self, caplog):
        """Test that no alert is logged for legitimate 403s under threshold."""
        app = create_test_app()

        with patch("app.middleware.security.redis_client") as mock_redis:
            mock_redis.increment_counter = AsyncMock(return_value=1)

            with caplog.at_level(logging.WARNING, logger="security"):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    await client.get("/test/forbidden")

            # Should log the request but not trigger security alerts
            warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
            security_alerts = [
                r for r in warning_logs if "Multiple forbidden access attempts" in r.message
            ]
            assert len(security_alerts) == 0

    @pytest.mark.asyncio
    async def test_excludes_health_check_paths(self, caplog):
        """Test that health check paths are not logged."""
        app = FastAPI()
        app.add_middleware(SecurityLoggingMiddleware)

        @app.get("/health")
        async def health() -> JSONResponse:
            return JSONResponse({"status": "healthy"})

        with caplog.at_level(logging.INFO, logger="security"):
            async with AsyncClient(app=app, base_url="http://test") as client:
                await client.get("/health")

        # Should not log health check requests
        assert len(caplog.records) == 0

    @pytest.mark.asyncio
    async def test_detects_suspicious_patterns(self, caplog):
        """Test detection of suspicious request patterns."""
        app = create_test_app()

        suspicious_paths = [
            "/test/../etc/passwd",
            "/test/wp-admin",
            "/test/<script>alert('xss')</script>",
        ]

        with caplog.at_level(logging.WARNING, logger="security"):
            async with AsyncClient(app=app, base_url="http://test") as client:
                for path in suspicious_paths:
                    await client.get(path)

        # Should have logged suspicious requests
        warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warning_logs) >= len(suspicious_paths)

    @pytest.mark.asyncio
    async def test_extracts_client_ip_from_x_forwarded_for(self):
        """Test that client IP is extracted from X-Forwarded-For header."""
        app = FastAPI()
        middleware = SecurityLoggingMiddleware(app)

        @app.get("/test-ip")
        async def test_ip(request: Request) -> JSONResponse:
            client_ip = middleware._get_client_ip(request)
            return JSONResponse({"client_ip": client_ip})

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/test-ip",
                headers={"X-Forwarded-For": "203.0.113.1, 198.51.100.1"},
            )

        assert response.status_code == 200
        data = response.json()
        # Should extract the first IP (original client)
        assert data["client_ip"] == "203.0.113.1"

    @pytest.mark.asyncio
    async def test_extracts_client_ip_from_x_real_ip(self):
        """Test that client IP is extracted from X-Real-IP header."""
        app = FastAPI()
        middleware = SecurityLoggingMiddleware(app)

        @app.get("/test-ip")
        async def test_ip(request: Request) -> JSONResponse:
            client_ip = middleware._get_client_ip(request)
            return JSONResponse({"client_ip": client_ip})

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/test-ip",
                headers={"X-Real-IP": "203.0.113.5"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["client_ip"] == "203.0.113.5"
