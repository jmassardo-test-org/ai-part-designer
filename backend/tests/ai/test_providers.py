"""
Tests for AI provider abstraction layer.

Tests the Anthropic (Claude) provider - the only supported AI provider.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.exceptions import AIConnectionError
from app.ai.providers import (
    _PROVIDERS,
    AIProvider,
    AnthropicProvider,
    get_ai_provider,
    reset_provider,
)

# =============================================================================
# Provider Base Class Tests
# =============================================================================


class TestAIProviderInterface:
    """Test that all providers implement the required interface."""

    def test_anthropic_provider_in_registry(self):
        """Verify Anthropic provider is registered."""
        assert "anthropic" in _PROVIDERS

    def test_anthropic_provider_inherits_from_base(self):
        """Anthropic provider should inherit from AIProvider."""
        assert issubclass(AnthropicProvider, AIProvider)


# =============================================================================
# Anthropic Provider Tests
# =============================================================================


class TestAnthropicProvider:
    """Tests for Anthropic (Claude) provider."""

    def test_anthropic_provider_name(self):
        """Provider name should be 'anthropic'."""
        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ANTHROPIC_API_KEY=None,
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )
            provider = AnthropicProvider()
            assert provider.name == "anthropic"

    def test_anthropic_provider_not_configured_without_key(self):
        """Provider should not be configured without API key."""
        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ANTHROPIC_API_KEY=None,
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )
            provider = AnthropicProvider()
            assert provider.is_configured is False

    def test_anthropic_provider_configured_with_key(self):
        """Provider should be configured with API key."""
        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ANTHROPIC_API_KEY="sk-ant-test-key",
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )
            provider = AnthropicProvider()
            assert provider.is_configured is True

    @pytest.mark.asyncio
    async def test_anthropic_provider_complete_not_configured(self):
        """Complete should raise error when not configured."""
        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ANTHROPIC_API_KEY=None,
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )
            provider = AnthropicProvider()

            with pytest.raises(AIConnectionError) as exc_info:
                await provider.complete([{"role": "user", "content": "test"}])

            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_anthropic_provider_complete_success(self):
        """Complete should return content on success."""
        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ANTHROPIC_API_KEY="sk-ant-test-key",
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )
            provider = AnthropicProvider()

            # Mock the response
            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = "Generated CAD code"

            with patch.object(
                provider._client.messages, "create", new_callable=AsyncMock
            ) as mock_create:
                mock_create.return_value = mock_response

                result = await provider.complete([{"role": "user", "content": "Create a box"}])

                assert result == "Generated CAD code"

    @pytest.mark.asyncio
    async def test_anthropic_provider_separates_system_message(self):
        """Complete should properly separate system message."""
        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ANTHROPIC_API_KEY="sk-ant-test-key",
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )
            provider = AnthropicProvider()

            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = "response"

            with patch.object(
                provider._client.messages, "create", new_callable=AsyncMock
            ) as mock_create:
                mock_create.return_value = mock_response

                await provider.complete(
                    [
                        {"role": "system", "content": "You are a CAD engineer."},
                        {"role": "user", "content": "Create a box."},
                    ]
                )

                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["system"] == "You are a CAD engineer."
                assert len(call_kwargs["messages"]) == 1

    @pytest.mark.asyncio
    async def test_anthropic_provider_json_mode(self):
        """Complete should add JSON hint when response_format specified."""
        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ANTHROPIC_API_KEY="sk-ant-test-key",
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )
            provider = AnthropicProvider()

            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = '{"key": "value"}'

            with patch.object(
                provider._client.messages, "create", new_callable=AsyncMock
            ) as mock_create:
                mock_create.return_value = mock_response

                await provider.complete(
                    [{"role": "user", "content": "test"}],
                    response_format={"type": "json_object"},
                )

                call_kwargs = mock_create.call_args[1]
                assert "valid JSON only" in call_kwargs["system"]

    @pytest.mark.asyncio
    async def test_anthropic_provider_complete_with_vision(self):
        """Complete with vision should work with image content."""
        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                ANTHROPIC_API_KEY="sk-ant-test-key",
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )
            provider = AnthropicProvider()

            mock_response = MagicMock()
            mock_response.content = [MagicMock()]
            mock_response.content[0].text = "I see a mechanical drawing."

            with patch.object(
                provider._client.messages, "create", new_callable=AsyncMock
            ) as mock_create:
                mock_create.return_value = mock_response

                result = await provider.complete_with_vision(
                    [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "What is this?"},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": "base64data",
                                    },
                                },
                            ],
                        }
                    ]
                )

                assert result == "I see a mechanical drawing."


# =============================================================================
# Provider Factory Tests
# =============================================================================


class TestGetAIProvider:
    """Tests for get_ai_provider factory function."""

    def test_get_ai_provider_returns_singleton(self):
        """get_ai_provider should return same instance."""
        reset_provider()

        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                AI_PROVIDER="anthropic",
                ANTHROPIC_API_KEY="test-key",
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )

            provider1 = get_ai_provider()
            provider2 = get_ai_provider()

            assert provider1 is provider2

    def test_get_ai_provider_returns_anthropic(self):
        """get_ai_provider should return Anthropic provider."""
        reset_provider()

        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                AI_PROVIDER="anthropic",
                ANTHROPIC_API_KEY="test-key",
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )

            provider = get_ai_provider()

            assert isinstance(provider, AnthropicProvider)
            assert provider.name == "anthropic"

    def test_get_ai_provider_defaults_to_anthropic_for_unknown(self):
        """get_ai_provider should default to anthropic for unknown provider."""
        reset_provider()

        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                AI_PROVIDER="unknown-provider",
                ANTHROPIC_API_KEY="test-key",
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )

            provider = get_ai_provider()

            assert isinstance(provider, AnthropicProvider)


class TestResetProvider:
    """Tests for reset_provider function."""

    def test_reset_provider_clears_instance(self):
        """reset_provider should clear cached instance."""
        reset_provider()

        with patch("app.ai.providers.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                AI_PROVIDER="anthropic",
                ANTHROPIC_API_KEY="test-key",
                ANTHROPIC_MODEL="claude-sonnet-4-20250514",
                AI_MAX_TOKENS=4096,
            )

            provider1 = get_ai_provider()
            reset_provider()
            provider2 = get_ai_provider()

            # Should be different instances after reset
            assert provider1 is not provider2
