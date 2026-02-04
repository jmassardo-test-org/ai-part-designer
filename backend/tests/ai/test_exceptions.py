"""
Tests for AI Exception Classes.

Tests exception hierarchy, message formatting, details handling,
and specific exception types.
"""

import pytest

from app.ai.exceptions import (
    AIError,
    AIConnectionError,
    AIRateLimitError,
    AIParseError,
    AITimeoutError,
    AIValidationError,
    AIGenerationError,
)


# =============================================================================
# AIError Base Class Tests
# =============================================================================

class TestAIError:
    """Tests for base AIError class."""

    def test_basic_error(self):
        """Test creating basic AI error."""
        error = AIError("Something went wrong")
        
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with details dict."""
        error = AIError(
            "Failed operation",
            details={"code": "E001", "context": "test"},
        )
        
        assert error.details["code"] == "E001"
        assert "details:" in str(error)

    def test_error_with_cause(self):
        """Test error with underlying cause."""
        original = ValueError("Original error")
        error = AIError("Wrapped error", cause=original)
        
        assert error.cause is original

    def test_error_inheritance(self):
        """Test that AIError inherits from Exception."""
        error = AIError("test")
        assert isinstance(error, Exception)


# =============================================================================
# AIConnectionError Tests
# =============================================================================

class TestAIConnectionError:
    """Tests for AI connection errors."""

    def test_default_message(self):
        """Test default connection error message."""
        error = AIConnectionError()
        
        assert "connect" in error.message.lower()

    def test_custom_message(self):
        """Test custom connection error message."""
        error = AIConnectionError("Cannot reach API")
        
        assert error.message == "Cannot reach API"

    def test_provider_attribute(self):
        """Test provider is stored."""
        error = AIConnectionError(provider="anthropic")
        
        assert error.provider == "anthropic"
        assert error.details["provider"] == "anthropic"

    def test_default_provider(self):
        """Test default provider is anthropic."""
        error = AIConnectionError()
        
        assert error.provider == "anthropic"

    def test_inheritance(self):
        """Test inheritance from AIError."""
        error = AIConnectionError()
        assert isinstance(error, AIError)


# =============================================================================
# AIRateLimitError Tests
# =============================================================================

class TestAIRateLimitError:
    """Tests for rate limit errors."""

    def test_default_message(self):
        """Test default rate limit message."""
        error = AIRateLimitError()
        
        assert "rate limit" in error.message.lower()

    def test_retry_after(self):
        """Test retry_after attribute."""
        error = AIRateLimitError(retry_after=60.0)
        
        assert error.retry_after == 60.0
        assert error.details["retry_after_seconds"] == 60.0

    def test_no_retry_after(self):
        """Test when retry_after is None."""
        error = AIRateLimitError()
        
        assert error.retry_after is None

    def test_inheritance(self):
        """Test inheritance from AIError."""
        error = AIRateLimitError()
        assert isinstance(error, AIError)


# =============================================================================
# AIParseError Tests
# =============================================================================

class TestAIParseError:
    """Tests for parse errors."""

    def test_default_message(self):
        """Test default parse error message."""
        error = AIParseError()
        
        assert "parse" in error.message.lower()

    def test_raw_response(self):
        """Test raw response storage."""
        error = AIParseError(raw_response='{"invalid": json}')
        
        assert error.raw_response == '{"invalid": json}'
        assert "raw_response" in error.details

    def test_raw_response_truncation(self):
        """Test long responses are truncated in details."""
        long_response = "x" * 1000
        error = AIParseError(raw_response=long_response)
        
        assert len(error.details["raw_response"]) == 500
        assert error.raw_response == long_response  # Full value preserved

    def test_inheritance(self):
        """Test inheritance from AIError."""
        error = AIParseError()
        assert isinstance(error, AIError)


# =============================================================================
# AITimeoutError Tests
# =============================================================================

class TestAITimeoutError:
    """Tests for timeout errors."""

    def test_default_message(self):
        """Test default timeout message."""
        error = AITimeoutError()
        
        assert "timed out" in error.message.lower()

    def test_timeout_seconds(self):
        """Test timeout_seconds attribute."""
        error = AITimeoutError(timeout_seconds=30.0)
        
        assert error.timeout_seconds == 30.0
        assert error.details["timeout_seconds"] == 30.0

    def test_no_timeout(self):
        """Test when timeout is None."""
        error = AITimeoutError()
        
        assert error.timeout_seconds is None

    def test_inheritance(self):
        """Test inheritance from AIError."""
        error = AITimeoutError()
        assert isinstance(error, AIError)


# =============================================================================
# AIValidationError Tests
# =============================================================================

class TestAIValidationError:
    """Tests for validation errors."""

    def test_default_message(self):
        """Test default validation error message."""
        error = AIValidationError()
        
        assert "validation" in error.message.lower()

    def test_validation_errors_list(self):
        """Test validation errors list."""
        errors_list = ["Missing field 'x'", "Invalid type for 'y'"]
        error = AIValidationError(validation_errors=errors_list)
        
        assert error.validation_errors == errors_list
        assert error.details["validation_errors"] == errors_list

    def test_empty_validation_errors(self):
        """Test with no validation errors."""
        error = AIValidationError()
        
        assert error.validation_errors == []

    def test_inheritance(self):
        """Test inheritance from AIError."""
        error = AIValidationError()
        assert isinstance(error, AIError)


# =============================================================================
# AIGenerationError Tests
# =============================================================================

class TestAIGenerationError:
    """Tests for generation errors."""

    def test_default_message(self):
        """Test default generation error message."""
        error = AIGenerationError()
        
        assert "generation" in error.message.lower()

    def test_prompt_storage(self):
        """Test prompt is stored."""
        error = AIGenerationError(prompt="Create a box")
        
        assert error.prompt == "Create a box"
        assert error.details["prompt"] == "Create a box"

    def test_prompt_truncation(self):
        """Test long prompts are truncated in details."""
        long_prompt = "Create " + "x" * 1000
        error = AIGenerationError(prompt=long_prompt)
        
        assert len(error.details["prompt"]) == 500
        assert error.prompt == long_prompt  # Full value preserved

    def test_inheritance(self):
        """Test inheritance from AIError."""
        error = AIGenerationError()
        assert isinstance(error, AIError)


# =============================================================================
# Exception Hierarchy Tests
# =============================================================================

class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_all_inherit_from_ai_error(self):
        """Test all specific exceptions inherit from AIError."""
        exceptions = [
            AIConnectionError(),
            AIRateLimitError(),
            AIParseError(),
            AITimeoutError(),
            AIValidationError(),
            AIGenerationError(),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, AIError)

    def test_all_are_exceptions(self):
        """Test all can be raised and caught."""
        exceptions = [
            AIError("test"),
            AIConnectionError(),
            AIRateLimitError(),
            AIParseError(),
            AITimeoutError(),
            AIValidationError(),
            AIGenerationError(),
        ]
        
        for exc in exceptions:
            with pytest.raises(AIError):
                raise exc

    def test_catch_specific_exception(self):
        """Test catching specific exception type."""
        with pytest.raises(AIRateLimitError):
            raise AIRateLimitError("Too many requests", retry_after=30)
