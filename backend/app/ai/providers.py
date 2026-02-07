"""
AI Provider abstraction - Claude (Anthropic) only.

This module provides a simplified provider interface using Claude as the sole AI provider.

Example:
    >>> from app.ai.providers import get_ai_provider
    >>> provider = get_ai_provider()
    >>> response = await provider.complete([
    ...     {"role": "user", "content": "Create a box 100x50x30mm"}
    ... ])
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.ai.exceptions import (
    AIConnectionError,
    AIError,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Send chat completion request."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is reachable."""


class AnthropicProvider(AIProvider):
    """
    Anthropic Claude provider - the primary and only supported AI provider.

    Claude provides excellent reasoning capabilities for CAD generation tasks.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.AI_MAX_TOKENS

        if self.api_key:
            try:
                from anthropic import AsyncAnthropic

                self._client = AsyncAnthropic(api_key=self.api_key, timeout=60.0)
            except ImportError:
                logger.warning("anthropic package not installed - run: pip install anthropic")
                self._client = None
        else:
            self._client = None

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """
        Send completion request to Claude.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            response_format: Response format specification

        Returns:
            Response content as string
        """
        if not self._client:
            raise AIConnectionError(
                "Anthropic not configured - set ANTHROPIC_API_KEY",
                provider="anthropic",
            )

        # Convert messages to Anthropic format (separate system message)
        system_message = None
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                    }
                )

        # If JSON format requested, add hint to system message
        if response_format and response_format.get("type") == "json_object":
            json_hint = "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no explanations."
            if system_message:
                system_message = system_message + json_hint
            else:
                system_message = "You are a helpful assistant." + json_hint

        if system_message is None:
            system_message = "You are a helpful CAD engineering assistant."

        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                system=system_message,
                messages=chat_messages,
                temperature=temperature,
            )
            content: str = response.content[0].text
            return content
        except Exception as e:
            raise AIError(
                f"Anthropic request failed: {e}", details={"provider": "anthropic"}
            ) from e

    async def complete_with_vision(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        """
        Send completion request with image content.

        Claude supports vision natively.

        Args:
            messages: List of message dicts (can include image content)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            Response content as string
        """
        if not self._client:
            raise AIConnectionError(
                "Anthropic not configured - set ANTHROPIC_API_KEY",
                provider="anthropic",
            )

        # Convert messages to Anthropic format
        system_message = None
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        if system_message is None:
            system_message = "You are a helpful CAD engineering assistant with vision capabilities."

        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                system=system_message,
                messages=chat_messages,
                temperature=temperature,
            )
            content: str = response.content[0].text
            return content
        except Exception as e:
            raise AIError(
                f"Anthropic vision request failed: {e}", details={"provider": "anthropic"}
            ) from e

    async def health_check(self) -> bool:
        """Check if Claude API is reachable."""
        if not self._client:
            return False
        try:
            await self._client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except Exception:
            return False


# Provider registry - Claude only
_PROVIDERS: dict[str, type[AIProvider]] = {
    "anthropic": AnthropicProvider,
}

_provider_instance: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    """
    Get the configured AI provider instance (Claude).

    Uses singleton pattern - provider is created once and reused.

    Returns:
        Configured AIProvider instance (AnthropicProvider)

    Example:
        >>> provider = get_ai_provider()
        >>> response = await provider.complete([...])
    """
    global _provider_instance

    if _provider_instance is None:
        settings = get_settings()
        provider_name = settings.AI_PROVIDER

        if provider_name not in _PROVIDERS:
            # Default to anthropic if invalid provider specified
            logger.warning(f"Unknown AI provider: {provider_name}. Defaulting to anthropic.")
            provider_name = "anthropic"

        provider_class = _PROVIDERS[provider_name]
        _provider_instance = provider_class()

        logger.info(
            f"Initialized AI provider: {provider_name} (model: {getattr(_provider_instance, 'model', 'N/A')})"
        )

    return _provider_instance


def reset_provider() -> None:
    """Reset provider instance (useful for testing)."""
    global _provider_instance
    _provider_instance = None


__all__ = [
    "AIProvider",
    "AnthropicProvider",
    "get_ai_provider",
    "reset_provider",
]
