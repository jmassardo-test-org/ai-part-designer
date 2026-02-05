"""
Anthropic Claude client wrapper with retry logic, rate limiting, and error handling.

Example:
    >>> from app.ai.client import get_ai_client
    >>> client = get_ai_client()
    >>> response = await client.complete([
    ...     {"role": "user", "content": "Create a box 100x50x30mm"}
    ... ])
"""

from __future__ import annotations

import asyncio
import logging
import time
from functools import lru_cache
from typing import Any

from app.ai.exceptions import (
    AIConnectionError,
    AIError,
    AIRateLimitError,
    AITimeoutError,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """
    Async Anthropic Claude client with retry logic and rate limiting.

    Features:
    - Exponential backoff for rate limits
    - Request timeout handling
    - Usage logging for cost tracking
    - Configurable model and parameters

    Example:
        >>> client = ClaudeClient()
        >>> response = await client.complete([
        ...     {"role": "system", "content": "You are a CAD engineer."},
        ...     {"role": "user", "content": "Create a box 100mm x 50mm x 30mm"}
        ... ])
    """

    DEFAULT_TIMEOUT = 60.0  # seconds
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    MAX_DELAY = 60.0  # seconds

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key (default: from settings)
            model: Model to use (default: from settings)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for rate limits
        """
        settings = get_settings()

        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.max_tokens = settings.AI_MAX_TOKENS
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.MAX_RETRIES

        if not self.api_key:
            logger.warning("Anthropic API key not configured - AI features disabled")
            self._client = None
        else:
            try:
                from anthropic import AsyncAnthropic

                self._client = AsyncAnthropic(
                    api_key=self.api_key,
                    timeout=self.timeout,
                )
            except ImportError:
                logger.error("anthropic package not installed - run: pip install anthropic")
                self._client = None

        # Usage tracking
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._request_count = 0

    @property
    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return self._client is not None

    @property
    def usage_stats(self) -> dict[str, int]:
        """Get cumulative usage statistics."""
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "request_count": self._request_count,
        }

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        """
        Send chat completion request with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Override default model
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            response_format: Response format specification (used for JSON mode hint)

        Returns:
            Response content as string

        Raises:
            AIConnectionError: Failed to connect to Anthropic
            AIRateLimitError: Rate limit exceeded after retries
            AITimeoutError: Request timed out
            AIError: Other AI-related errors
        """
        if not self._client:
            raise AIConnectionError(
                "Claude client not configured - set ANTHROPIC_API_KEY",
                provider="anthropic",
            )

        model = model or self.model
        max_tokens = max_tokens or self.max_tokens

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

        # Ensure we have at least a default system message
        if system_message is None:
            system_message = "You are a helpful CAD engineering assistant."

        # Anthropic API requires at least one user message
        # If we only have a system message (no chat_messages), create a user message
        if not chat_messages:
            chat_messages = [
                {
                    "role": "user",
                    "content": "Please process the request described in the system instructions.",
                }
            ]

        # Retry loop with exponential backoff
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                from anthropic import APIConnectionError, APIError, APITimeoutError, RateLimitError

                start_time = time.monotonic()

                response = await self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_message,
                    messages=chat_messages,
                    temperature=temperature,
                )

                elapsed = time.monotonic() - start_time

                # Track usage
                if hasattr(response, "usage"):
                    self._total_input_tokens += response.usage.input_tokens
                    self._total_output_tokens += response.usage.output_tokens
                self._request_count += 1

                # Log successful request
                logger.info(
                    "Claude request completed",
                    extra={
                        "model": model,
                        "input_tokens": response.usage.input_tokens
                        if hasattr(response, "usage")
                        else 0,
                        "output_tokens": response.usage.output_tokens
                        if hasattr(response, "usage")
                        else 0,
                        "elapsed_seconds": round(elapsed, 2),
                        "attempt": attempt + 1,
                    },
                )

                # Extract content
                content = response.content[0].text
                if content is None:
                    raise AIError("Empty response from Claude")

                return content

            except RateLimitError as e:
                last_error = e
                retry_after = self._get_retry_after(attempt)

                if attempt < self.max_retries:
                    logger.warning(
                        f"Rate limited, retrying in {retry_after:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(retry_after)
                else:
                    raise AIRateLimitError(
                        "Rate limit exceeded after max retries",
                        retry_after=retry_after,
                        cause=e,
                    )

            except APITimeoutError as e:
                raise AITimeoutError(
                    f"Claude request timed out after {self.timeout}s",
                    timeout_seconds=self.timeout,
                    cause=e,
                )

            except APIConnectionError as e:
                raise AIConnectionError(
                    f"Failed to connect to Anthropic: {e}",
                    provider="anthropic",
                    cause=e,
                )

            except APIError as e:
                raise AIError(
                    f"Anthropic API error: {e}",
                    details={"status_code": getattr(e, "status_code", None)},
                    cause=e,
                )

            except Exception as e:
                raise AIError(
                    f"Unexpected error calling Claude: {e}",
                    cause=e,
                )

        # Should not reach here, but just in case
        raise AIError("Unexpected error in retry loop", cause=last_error)

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        **kwargs,
    ) -> str:
        """
        Send chat completion request expecting JSON response.

        Args:
            messages: List of message dicts
            **kwargs: Additional arguments for complete()

        Returns:
            JSON response as string
        """
        return await self.complete(
            messages,
            response_format={"type": "json_object"},
            **kwargs,
        )

    async def complete_with_vision(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        """
        Send chat completion request with image content.

        Claude supports vision natively with base64 images or URLs.

        Args:
            messages: List of message dicts (can include image content)
            model: Override default model
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            Response content as string
        """
        if not self._client:
            raise AIConnectionError(
                "Claude client not configured - set ANTHROPIC_API_KEY",
                provider="anthropic",
            )

        model = model or self.model
        max_tokens = max_tokens or self.max_tokens

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
                model=model,
                max_tokens=max_tokens,
                system=system_message,
                messages=chat_messages,
                temperature=temperature,
            )

            self._request_count += 1
            if hasattr(response, "usage"):
                self._total_input_tokens += response.usage.input_tokens
                self._total_output_tokens += response.usage.output_tokens

            return response.content[0].text

        except Exception as e:
            raise AIError(f"Claude vision request failed: {e}", cause=e)

    def _get_retry_after(self, attempt: int) -> float:
        """Calculate retry delay with exponential backoff."""
        # Exponential backoff: 1s, 2s, 4s, 8s, ...
        delay = self.BASE_DELAY * (2**attempt)
        return min(delay, self.MAX_DELAY)

    async def health_check(self) -> bool:
        """Check if the Claude API is reachable."""
        if not self._client:
            return False
        try:
            # Simple test message
            await self._client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except Exception:
            return False


# Singleton client instance
_cached_client: ClaudeClient | None = None


@lru_cache
def get_ai_client() -> ClaudeClient:
    """
    Get cached AI client instance.

    Returns:
        ClaudeClient instance
    """
    return ClaudeClient()


def reset_client() -> None:
    """Reset client instance (useful for testing)."""
    global _cached_client
    _cached_client = None
    get_ai_client.cache_clear()


__all__ = [
    "ClaudeClient",
    "get_ai_client",
    "reset_client",
]
