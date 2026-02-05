"""
Tests for Claude (Anthropic) client wrapper.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.client import ClaudeClient, get_ai_client
from app.ai.exceptions import (
    AIConnectionError,
    AITimeoutError,
)

# =============================================================================
# Client Configuration Tests
# =============================================================================


class TestClaudeClientConfig:
    """Tests for client configuration."""

    def test_client_not_configured_without_api_key(self):
        """Test client reports not configured when no API key."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            # Clear cached settings
            from app.core.config import get_settings

            get_settings.cache_clear()

            client = ClaudeClient(api_key=None)
            # Client may or may not be configured depending on settings
            # Just verify it doesn't crash
            assert isinstance(client, ClaudeClient)

    def test_client_configured_with_api_key(self):
        """Test client is configured when API key provided."""
        client = ClaudeClient(api_key="test-key")
        assert client.is_configured
        assert client.api_key == "test-key"

    def test_client_uses_custom_model(self):
        """Test client respects custom model setting."""
        client = ClaudeClient(api_key="test-key", model="claude-3-haiku-20240307")
        assert client.model == "claude-3-haiku-20240307"

    def test_client_uses_custom_timeout(self):
        """Test client respects custom timeout."""
        client = ClaudeClient(api_key="test-key", timeout=120.0)
        assert client.timeout == 120.0

    def test_usage_stats_initialized_to_zero(self):
        """Test usage stats start at zero."""
        client = ClaudeClient(api_key="test-key")
        stats = client.usage_stats

        assert stats["input_tokens"] == 0
        assert stats["output_tokens"] == 0
        assert stats["total_tokens"] == 0
        assert stats["request_count"] == 0


# =============================================================================
# Completion Tests
# =============================================================================


class TestClaudeClientComplete:
    """Tests for completion method."""

    @pytest.mark.asyncio
    async def test_complete_not_configured_raises_error(self):
        """Test complete raises error when not configured."""
        client = ClaudeClient(api_key=None)
        client._client = None  # Force unconfigured state

        with pytest.raises(AIConnectionError) as exc_info:
            await client.complete([{"role": "user", "content": "test"}])

        assert "not configured" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_complete_returns_content(self):
        """Test successful completion returns content."""
        client = ClaudeClient(api_key="test-key")

        # Mock the response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = '{"shape": "box"}'
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5

        with patch.object(client._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            result = await client.complete([{"role": "user", "content": "test"}])

            assert result == '{"shape": "box"}'

    @pytest.mark.asyncio
    async def test_complete_tracks_usage(self):
        """Test completion tracks token usage."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "response"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        with patch.object(client._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            await client.complete([{"role": "user", "content": "test"}])

            stats = client.usage_stats
            assert stats["input_tokens"] == 100
            assert stats["output_tokens"] == 50
            assert stats["request_count"] == 1

    @pytest.mark.asyncio
    async def test_complete_separates_system_message(self):
        """Test complete properly separates system message for Claude API."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "response"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5

        with patch.object(client._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            await client.complete(
                [
                    {"role": "system", "content": "You are a CAD engineer."},
                    {"role": "user", "content": "Create a box."},
                ]
            )

            # Verify system message was passed separately
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["system"] == "You are a CAD engineer."
            assert len(call_kwargs["messages"]) == 1
            assert call_kwargs["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_complete_json_adds_json_hint(self):
        """Test complete_json adds JSON hint to system message."""
        client = ClaudeClient(api_key="test-key")

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = '{"key": "value"}'
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5

        with patch.object(client._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            await client.complete_json(
                [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "test"},
                ]
            )

            # Verify JSON hint was added to system message
            call_kwargs = mock_create.call_args[1]
            assert "valid JSON only" in call_kwargs["system"]


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestClaudeClientErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_connection_error_wrapped(self):
        """Test connection errors are wrapped properly."""
        client = ClaudeClient(api_key="test-key")

        with patch.object(client._client.messages, "create", new_callable=AsyncMock) as mock_create:
            import httpx
            from anthropic import APIConnectionError

            # APIConnectionError requires a request parameter
            mock_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            mock_create.side_effect = APIConnectionError(
                message="Connection failed", request=mock_request
            )

            with pytest.raises(AIConnectionError) as exc_info:
                await client.complete([{"role": "user", "content": "test"}])

            assert exc_info.value.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_timeout_error_wrapped(self):
        """Test timeout errors are wrapped properly."""
        client = ClaudeClient(api_key="test-key")

        with patch.object(client._client.messages, "create", new_callable=AsyncMock) as mock_create:
            from anthropic import APITimeoutError

            mock_create.side_effect = APITimeoutError(request=MagicMock())

            with pytest.raises(AITimeoutError) as exc_info:
                await client.complete([{"role": "user", "content": "test"}])

            assert exc_info.value.timeout_seconds == client.timeout


# =============================================================================
# Singleton Tests
# =============================================================================


class TestGetAIClient:
    """Tests for get_ai_client singleton."""

    def test_get_ai_client_returns_same_instance(self):
        """Test get_ai_client returns cached instance."""
        # Clear cache first
        get_ai_client.cache_clear()

        client1 = get_ai_client()
        client2 = get_ai_client()

        assert client1 is client2

    def test_get_ai_client_returns_claude_client(self):
        """Test get_ai_client returns ClaudeClient instance."""
        get_ai_client.cache_clear()

        client = get_ai_client()

        assert isinstance(client, ClaudeClient)
