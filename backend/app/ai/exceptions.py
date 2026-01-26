"""
AI-specific exceptions.

Provides a hierarchy of exceptions for AI-related errors including
connection issues, rate limits, parsing failures, and timeouts.
"""

from __future__ import annotations

from typing import Any


class AIError(Exception):
    """Base exception for all AI-related errors."""
    
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


class AIConnectionError(AIError):
    """Failed to connect to AI provider."""
    
    def __init__(
        self,
        message: str = "Failed to connect to AI provider",
        *,
        provider: str = "openai",
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.provider = provider
        self.details["provider"] = provider


class AIRateLimitError(AIError):
    """Rate limit exceeded on AI provider."""
    
    def __init__(
        self,
        message: str = "AI rate limit exceeded",
        *,
        retry_after: float | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after_seconds"] = retry_after


class AIParseError(AIError):
    """Failed to parse AI response."""
    
    def __init__(
        self,
        message: str = "Failed to parse AI response",
        *,
        raw_response: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.raw_response = raw_response
        if raw_response:
            # Truncate for logging
            self.details["raw_response"] = raw_response[:500]


class AITimeoutError(AIError):
    """AI request timed out."""
    
    def __init__(
        self,
        message: str = "AI request timed out",
        *,
        timeout_seconds: float | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            self.details["timeout_seconds"] = timeout_seconds


class AIValidationError(AIError):
    """AI response failed validation."""
    
    def __init__(
        self,
        message: str = "AI response validation failed",
        *,
        validation_errors: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []
        if self.validation_errors:
            self.details["validation_errors"] = self.validation_errors


class AIGenerationError(AIError):
    """AI code generation failed."""
    
    def __init__(
        self,
        message: str = "AI code generation failed",
        *,
        prompt: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.prompt = prompt
        if prompt:
            # Truncate for logging
            self.details["prompt"] = prompt[:500]
