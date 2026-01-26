"""
OpenAI client wrapper with retry logic, rate limiting, and error handling.

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
from typing import TYPE_CHECKING, Any

import openai
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError

from app.core.config import get_settings
from app.ai.exceptions import (
    AIConnectionError,
    AIRateLimitError,
    AITimeoutError,
    AIError,
)

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Async OpenAI client with retry logic and rate limiting.
    
    Features:
    - Exponential backoff for rate limits
    - Request timeout handling
    - Usage logging for cost tracking
    - Configurable model and parameters
    
    Example:
        >>> client = OpenAIClient()
        >>> response = await client.complete([
        ...     {"role": "system", "content": "You are a CAD engineer."},
        ...     {"role": "user", "content": "Create a box 100mm x 50mm x 30mm"}
        ... ])
    """
    
    DEFAULT_TIMEOUT = 30.0  # seconds
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
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (default: from settings)
            model: Model to use (default: from settings)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for rate limits
        """
        settings = get_settings()
        
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.MAX_RETRIES
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured - AI features disabled")
            self._client = None
        else:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=0,  # We handle retries ourselves
            )
        
        # Usage tracking
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._request_count = 0
    
    @property
    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return self._client is not None
    
    @property
    def usage_stats(self) -> dict[str, int]:
        """Get cumulative usage statistics."""
        return {
            "prompt_tokens": self._total_prompt_tokens,
            "completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
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
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            response_format: Response format specification (e.g., {"type": "json_object"})
        
        Returns:
            Response content as string
        
        Raises:
            AIConnectionError: Failed to connect to OpenAI
            AIRateLimitError: Rate limit exceeded after retries
            AITimeoutError: Request timed out
            AIError: Other AI-related errors
        """
        if not self._client:
            raise AIConnectionError(
                "OpenAI client not configured - set OPENAI_API_KEY",
                provider="openai",
            )
        
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        
        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        
        # Retry loop with exponential backoff
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.monotonic()
                
                response: ChatCompletion = await self._client.chat.completions.create(
                    **kwargs
                )
                
                elapsed = time.monotonic() - start_time
                
                # Track usage
                if response.usage:
                    self._total_prompt_tokens += response.usage.prompt_tokens
                    self._total_completion_tokens += response.usage.completion_tokens
                self._request_count += 1
                
                # Log successful request
                logger.info(
                    "OpenAI request completed",
                    extra={
                        "model": model,
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "elapsed_seconds": round(elapsed, 2),
                        "attempt": attempt + 1,
                    },
                )
                
                # Extract content
                content = response.choices[0].message.content
                if content is None:
                    raise AIError("Empty response from OpenAI")
                
                return content
                
            except RateLimitError as e:
                last_error = e
                retry_after = self._get_retry_after(e, attempt)
                
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
            
            except APIConnectionError as e:
                raise AIConnectionError(
                    f"Failed to connect to OpenAI: {e}",
                    provider="openai",
                    cause=e,
                )
            
            except APITimeoutError as e:
                raise AITimeoutError(
                    f"OpenAI request timed out after {self.timeout}s",
                    timeout_seconds=self.timeout,
                    cause=e,
                )
            
            except APIError as e:
                raise AIError(
                    f"OpenAI API error: {e}",
                    details={"status_code": e.status_code if hasattr(e, "status_code") else None},
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
        
        Uses OpenAI's JSON mode to ensure valid JSON output.
        
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
    
    def _get_retry_after(self, error: RateLimitError, attempt: int) -> float:
        """Calculate retry delay with exponential backoff."""
        # Try to get retry-after from headers
        if hasattr(error, "response") and error.response:
            headers = error.response.headers
            retry_after = headers.get("retry-after")
            if retry_after:
                try:
                    return min(float(retry_after), self.MAX_DELAY)
                except ValueError:
                    pass
        
        # Exponential backoff: 1s, 2s, 4s, 8s, ...
        delay = self.BASE_DELAY * (2 ** attempt)
        return min(delay, self.MAX_DELAY)


class ProviderClient:
    """
    AI client that wraps the multi-provider abstraction.
    
    Provides the same interface as OpenAIClient but uses whatever
    provider is configured (OpenAI, Ollama, Anthropic, etc.).
    """
    
    def __init__(self):
        from app.ai.providers import get_ai_provider
        self._provider = get_ai_provider()
    
    @property
    def is_configured(self) -> bool:
        """Check if the underlying provider is configured."""
        return self._provider.is_configured
    
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        response_format: dict | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        """
        Send chat completion request.
        
        Args:
            messages: List of message dicts with role and content
            temperature: Sampling temperature (0.0 to 1.0)
            response_format: Response format (e.g. {"type": "json_object"})
            max_tokens: Maximum tokens in response
        
        Returns:
            Response content as string
        """
        return await self._provider.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    
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


_cached_client: ProviderClient | None = None


@lru_cache
def get_ai_client() -> ProviderClient:
    """
    Get cached AI client instance using the configured provider.
    
    Returns:
        ProviderClient that wraps the configured AI provider
    """
    return ProviderClient()


# Re-export provider function for convenience
from app.ai.providers import get_ai_provider, AIProvider

__all__ = ["OpenAIClient", "ProviderClient", "get_ai_client", "get_ai_provider", "AIProvider"]
