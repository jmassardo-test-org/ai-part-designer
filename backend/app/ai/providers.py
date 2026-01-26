"""
AI Provider abstraction for multi-provider support.

Supports:
- OpenAI (GPT-4, GPT-3.5)
- Ollama (local models like Llama, CodeLlama, Mistral)
- Anthropic (Claude)
- Azure OpenAI

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

import httpx

from app.core.config import get_settings
from app.ai.exceptions import (
    AIConnectionError,
    AIRateLimitError,
    AITimeoutError,
    AIError,
)

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass
    
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass
    
    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        """Send chat completion request."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is reachable."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""
    
    def __init__(self):
        from openai import AsyncOpenAI
        
        settings = get_settings()
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        
        if self.api_key:
            self._client = AsyncOpenAI(api_key=self.api_key, timeout=30.0)
        else:
            self._client = None
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def is_configured(self) -> bool:
        return self._client is not None
    
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        if not self._client:
            raise AIConnectionError("OpenAI not configured - set OPENAI_API_KEY", provider="openai")
        
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        try:
            response = await self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise AIError(f"OpenAI request failed: {e}", details={"provider": "openai"}) from e
    
    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False


class OllamaProvider(AIProvider):
    """
    Ollama provider for local LLM development.
    
    Ollama provides an OpenAI-compatible API, making it easy to test locally.
    
    Setup:
        1. Install Ollama: https://ollama.ai
        2. Pull a model: `ollama pull llama3.2` or `ollama pull codellama`
        3. Set AI_PROVIDER=ollama in .env
    
    Recommended models for CAD generation:
        - codellama:13b - Good code/structured output
        - llama3.2 - General purpose, fast
        - mistral - Good reasoning
        - mixtral - Best quality, slower
    """
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.max_tokens = settings.AI_MAX_TOKENS
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
    
    @property
    def name(self) -> str:
        return "ollama"
    
    @property
    def is_configured(self) -> bool:
        # Ollama is always "configured" - we just need to check if it's running
        return True
    
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        """
        Send completion request to Ollama.
        
        Ollama supports OpenAI-compatible chat API at /api/chat
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or self.max_tokens,
            }
        }
        
        # Ollama supports JSON mode
        if response_format and response_format.get("type") == "json_object":
            payload["format"] = "json"
        
        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except httpx.ConnectError as e:
            raise AIConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is Ollama running? Start it with: ollama serve",
                provider="ollama",
            ) from e
        except httpx.TimeoutException as e:
            raise AITimeoutError("Ollama request timed out", provider="ollama") from e
        except Exception as e:
            raise AIError(f"Ollama request failed: {e}", details={"provider": "ollama"}) from e
    
    async def health_check(self) -> bool:
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.AI_MAX_TOKENS
        
        if self.api_key:
            # Anthropic SDK
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
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
        response_format: dict | None = None,
    ) -> str:
        if not self._client:
            raise AIConnectionError("Anthropic not configured - set ANTHROPIC_API_KEY", provider="anthropic")
        
        # Convert messages to Anthropic format (separate system message)
        system_message = None
        chat_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)
        
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                system=system_message or "You are a helpful CAD engineering assistant.",
                messages=chat_messages,
            )
            return response.content[0].text
        except Exception as e:
            raise AIError(f"Anthropic request failed: {e}", details={"provider": "anthropic"}) from e
    
    async def health_check(self) -> bool:
        # Anthropic doesn't have a free health endpoint
        return self._client is not None


class AzureOpenAIProvider(AIProvider):
    """Azure OpenAI provider."""
    
    def __init__(self):
        from openai import AsyncAzureOpenAI
        
        settings = get_settings()
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT
        self.api_version = settings.AZURE_OPENAI_API_VERSION
        self.max_tokens = settings.AI_MAX_TOKENS
        
        if self.api_key and self.endpoint and self.deployment:
            self._client = AsyncAzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.endpoint,
            )
        else:
            self._client = None
    
    @property
    def name(self) -> str:
        return "azure"
    
    @property
    def is_configured(self) -> bool:
        return self._client is not None
    
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        if not self._client:
            raise AIConnectionError(
                "Azure OpenAI not configured - set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT",
                provider="azure",
            )
        
        kwargs: dict[str, Any] = {
            "model": self.deployment,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        try:
            response = await self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise AIError(f"Azure OpenAI request failed: {e}", details={"provider": "azure"}) from e
    
    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            # Azure doesn't have a simple models list endpoint
            return True
        except Exception:
            return False


# Provider registry
_PROVIDERS: dict[str, type[AIProvider]] = {
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
    "azure": AzureOpenAIProvider,
}

_provider_instance: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    """
    Get the configured AI provider instance.
    
    Uses singleton pattern - provider is created once and reused.
    
    Returns:
        Configured AIProvider instance
        
    Example:
        >>> provider = get_ai_provider()
        >>> response = await provider.complete([...])
    """
    global _provider_instance
    
    if _provider_instance is None:
        settings = get_settings()
        provider_name = settings.AI_PROVIDER
        
        if provider_name not in _PROVIDERS:
            raise ValueError(f"Unknown AI provider: {provider_name}. Choose from: {list(_PROVIDERS.keys())}")
        
        provider_class = _PROVIDERS[provider_name]
        _provider_instance = provider_class()
        
        logger.info(f"Initialized AI provider: {provider_name} (model: {getattr(_provider_instance, 'model', 'N/A')})")
    
    return _provider_instance


def reset_provider() -> None:
    """Reset provider instance (useful for testing)."""
    global _provider_instance
    _provider_instance = None
