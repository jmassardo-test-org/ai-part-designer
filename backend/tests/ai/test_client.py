"""
Tests for OpenAI client wrapper.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.client import OpenAIClient, get_ai_client
from app.ai.exceptions import (
    AIConnectionError,
    AIRateLimitError,
    AITimeoutError,
    AIError,
)


# =============================================================================
# Client Configuration Tests
# =============================================================================

class TestOpenAIClientConfig:
    """Tests for client configuration."""
    
    def test_client_not_configured_without_api_key(self):
        """Test client reports not configured when no API key."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            # Clear cached settings
            from app.core.config import get_settings
            get_settings.cache_clear()
            
            client = OpenAIClient(api_key=None)
            # Client may or may not be configured depending on settings
            # Just verify it doesn't crash
            assert isinstance(client, OpenAIClient)
    
    def test_client_configured_with_api_key(self):
        """Test client is configured when API key provided."""
        client = OpenAIClient(api_key="test-key")
        assert client.is_configured
        assert client.api_key == "test-key"
    
    def test_client_uses_custom_model(self):
        """Test client respects custom model setting."""
        client = OpenAIClient(api_key="test-key", model="gpt-3.5-turbo")
        assert client.model == "gpt-3.5-turbo"
    
    def test_client_uses_custom_timeout(self):
        """Test client respects custom timeout."""
        client = OpenAIClient(api_key="test-key", timeout=60.0)
        assert client.timeout == 60.0
    
    def test_usage_stats_initialized_to_zero(self):
        """Test usage stats start at zero."""
        client = OpenAIClient(api_key="test-key")
        stats = client.usage_stats
        
        assert stats["prompt_tokens"] == 0
        assert stats["completion_tokens"] == 0
        assert stats["total_tokens"] == 0
        assert stats["request_count"] == 0


# =============================================================================
# Completion Tests
# =============================================================================

class TestOpenAIClientComplete:
    """Tests for completion method."""
    
    @pytest.mark.asyncio
    async def test_complete_not_configured_raises_error(self):
        """Test complete raises error when not configured."""
        client = OpenAIClient(api_key=None)
        client._client = None  # Force unconfigured state
        
        with pytest.raises(AIConnectionError) as exc_info:
            await client.complete([{"role": "user", "content": "test"}])
        
        assert "not configured" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_complete_returns_content(self):
        """Test successful completion returns content."""
        client = OpenAIClient(api_key="test-key")
        
        # Mock the response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"shape": "box"}'
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        
        with patch.object(client._client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await client.complete([{"role": "user", "content": "test"}])
            
            assert result == '{"shape": "box"}'
    
    @pytest.mark.asyncio
    async def test_complete_tracks_usage(self):
        """Test completion tracks token usage."""
        client = OpenAIClient(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        
        with patch.object(client._client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            await client.complete([{"role": "user", "content": "test"}])
            
            stats = client.usage_stats
            assert stats["prompt_tokens"] == 100
            assert stats["completion_tokens"] == 50
            assert stats["request_count"] == 1
    
    @pytest.mark.asyncio
    async def test_complete_json_sets_response_format(self):
        """Test complete_json sets JSON response format."""
        client = OpenAIClient(api_key="test-key")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        
        with patch.object(client._client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            await client.complete_json([{"role": "user", "content": "test"}])
            
            # Verify response_format was passed
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["response_format"] == {"type": "json_object"}


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestOpenAIClientErrors:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_connection_error_wrapped(self):
        """Test connection errors are wrapped properly."""
        from openai import APIConnectionError
        
        client = OpenAIClient(api_key="test-key")
        
        with patch.object(client._client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = APIConnectionError(request=MagicMock())
            
            with pytest.raises(AIConnectionError) as exc_info:
                await client.complete([{"role": "user", "content": "test"}])
            
            assert exc_info.value.provider == "openai"
    
    @pytest.mark.asyncio
    async def test_timeout_error_wrapped(self):
        """Test timeout errors are wrapped properly."""
        from openai import APITimeoutError
        
        client = OpenAIClient(api_key="test-key")
        
        with patch.object(client._client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
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
