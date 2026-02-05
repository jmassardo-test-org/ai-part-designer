"""
Tests for Rate Limiter.

Tests the rate limiting dependency for FastAPI endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
    expensive_operation_limit,
    get_client_ip,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = MagicMock()
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.url.path = "/api/v1/test"
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    with patch("app.core.rate_limiter.redis_client") as mock:
        mock.check_rate_limit = AsyncMock(return_value=(True, 9))
        mock.ttl = AsyncMock(return_value=60)
        yield mock


# =============================================================================
# get_client_ip Tests
# =============================================================================


class TestGetClientIP:
    """Tests for extracting client IP."""

    def test_direct_connection(self, mock_request):
        """Test IP extraction from direct connection."""
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.100"

        assert get_client_ip(mock_request) == "192.168.1.100"

    def test_x_forwarded_for_single(self, mock_request):
        """Test IP extraction from X-Forwarded-For header."""
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1"}

        assert get_client_ip(mock_request) == "10.0.0.1"

    def test_x_forwarded_for_multiple(self, mock_request):
        """Test IP extraction with multiple proxies."""
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1, 172.16.0.1"}

        # Should return the first (client) IP
        assert get_client_ip(mock_request) == "10.0.0.1"

    def test_no_client(self, mock_request):
        """Test IP extraction when client is None."""
        mock_request.headers = {}
        mock_request.client = None

        assert get_client_ip(mock_request) == "unknown"


# =============================================================================
# RateLimiter Tests
# =============================================================================


class TestRateLimiter:
    """Tests for the RateLimiter dependency."""

    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self, mock_request, mock_redis):
        """Test that requests under the limit are allowed."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        # Should not raise
        await limiter(mock_request)

        mock_redis.check_rate_limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_blocks_request_over_limit(self, mock_request, mock_redis):
        """Test that requests over the limit are blocked."""
        mock_redis.check_rate_limit = AsyncMock(return_value=(False, 0))
        mock_redis.ttl = AsyncMock(return_value=30)

        limiter = RateLimiter(max_requests=10, window_seconds=60)

        with pytest.raises(RateLimitExceeded) as exc_info:
            await limiter(mock_request)

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers is not None
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_uses_user_id_when_authenticated(self, mock_request, mock_redis):
        """Test that user ID is used for authenticated requests."""
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_request.state.user = mock_user

        limiter = RateLimiter(max_requests=10, window_seconds=60, use_user_id=True)

        await limiter(mock_request)

        # Check that the key includes user ID
        call_args = mock_redis.check_rate_limit.call_args
        assert f"user:{mock_user.id}" in call_args.kwargs["key"]

    @pytest.mark.asyncio
    async def test_uses_ip_when_unauthenticated(self, mock_request, mock_redis):
        """Test that IP is used for unauthenticated requests."""
        mock_request.state.user = None
        limiter = RateLimiter(max_requests=10, window_seconds=60, use_user_id=True)

        await limiter(mock_request)

        # Check that the key includes IP
        call_args = mock_redis.check_rate_limit.call_args
        assert "ip:127.0.0.1" in call_args.kwargs["key"]

    @pytest.mark.asyncio
    async def test_custom_key_func(self, mock_request, mock_redis):
        """Test custom key generation function."""

        def custom_key(r, u):
            return "custom:test"

        limiter = RateLimiter(
            max_requests=10,
            window_seconds=60,
            key_func=custom_key,
        )

        await limiter(mock_request)

        call_args = mock_redis.check_rate_limit.call_args
        assert "custom:test" in call_args.kwargs["key"]

    @pytest.mark.asyncio
    async def test_fails_open_on_redis_error(self, mock_request, mock_redis):
        """Test that requests are allowed if Redis is unavailable."""
        mock_redis.check_rate_limit.side_effect = Exception("Redis connection error")

        limiter = RateLimiter(max_requests=10, window_seconds=60)

        # Should not raise - fail open
        await limiter(mock_request)

    @pytest.mark.asyncio
    async def test_sets_rate_limit_headers_in_state(self, mock_request, mock_redis):
        """Test that rate limit info is stored in request state."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)

        await limiter(mock_request)

        assert mock_request.state.rate_limit_remaining == 9
        assert mock_request.state.rate_limit_limit == 10
        assert mock_request.state.rate_limit_reset == 60


# =============================================================================
# Pre-configured Limiters Tests
# =============================================================================


class TestPreconfiguredLimiters:
    """Tests for pre-configured rate limiters."""

    def test_expensive_operation_limit_config(self):
        """Test expensive operation limiter configuration."""
        assert expensive_operation_limit.max_requests == 10
        assert expensive_operation_limit.window_seconds == 60

    def test_rate_limit_exceeded_includes_retry_after(self):
        """Test that RateLimitExceeded includes Retry-After header."""
        exc = RateLimitExceeded(retry_after=30)

        assert exc.status_code == 429
        assert exc.headers is not None
        assert exc.headers["Retry-After"] == "30"
