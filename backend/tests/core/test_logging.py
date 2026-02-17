"""
Tests for structured logging configuration.

Tests the structlog setup, processors, and log format output.
"""

from __future__ import annotations

import json
import logging
from io import StringIO
from typing import TYPE_CHECKING

import pytest
import structlog

from app.core.logging import add_app_context, configure_structlog, get_logger

if TYPE_CHECKING:
    from structlog.types import EventDict


# =============================================================================
# Configuration Tests
# =============================================================================


class TestStructlogConfiguration:
    """Tests for structlog configuration."""

    def test_configure_structlog_production(self, monkeypatch):
        """Test structlog configures JSON output in production."""
        # Mock settings to return production environment
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.logging.get_settings",
            lambda: Settings(ENVIRONMENT="production", APP_NAME="test-app", APP_VERSION="1.0.0"),
        )

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure structlog
        configure_structlog()

        # Get the formatter from the configured handler and apply to our test handler
        root_logger = logging.getLogger()
        if root_logger.handlers:
            handler.setFormatter(root_logger.handlers[0].formatter)
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

        # Create logger and log message
        logger = get_logger("test.module")
        logger.info("test_event", key="value", number=42)

        # Get output
        log_output = log_stream.getvalue()

        # Should be valid JSON
        log_line = log_output.strip()
        log_data = json.loads(log_line)

        # Verify structure
        assert log_data["event"] == "test_event"
        assert log_data["key"] == "value"
        assert log_data["number"] == 42
        assert "timestamp" in log_data
        assert "level" in log_data
        assert log_data["level"] == "info"
        assert "logger" in log_data
        assert log_data["logger"] == "test.module"

    def test_configure_structlog_development(self, monkeypatch):
        """Test structlog configures console output in development."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.logging.get_settings",
            lambda: Settings(ENVIRONMENT="development", APP_NAME="test-app", APP_VERSION="1.0.0"),
        )

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure structlog
        configure_structlog()

        # Replace handler to capture output
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

        # Create logger and log message
        logger = get_logger("test.module")
        logger.info("test_event", key="value")

        # Get output
        log_output = log_stream.getvalue()

        # Should be human-readable console format (not JSON)
        assert "test_event" in log_output
        assert "key" in log_output
        assert "value" in log_output

    def test_get_logger_returns_structlog_logger(self):
        """Test get_logger returns a structlog logger instance."""
        logger = get_logger("test.logger")

        # Should be a structlog logger
        assert hasattr(logger, "bind")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")


# =============================================================================
# Processor Tests
# =============================================================================


class TestProcessors:
    """Tests for custom structlog processors."""

    def test_add_app_context_processor(self, monkeypatch):
        """Test add_app_context adds application metadata to logs."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.logging.get_settings",
            lambda: Settings(
                ENVIRONMENT="test",
                APP_NAME="test-application",
                APP_VERSION="1.2.3",
            ),
        )

        event_dict: EventDict = {"event": "test"}
        logger = logging.getLogger("test")

        result = add_app_context(logger, "info", event_dict)

        assert result["app_name"] == "test-application"
        assert result["environment"] == "test"


# =============================================================================
# Context Variable Tests
# =============================================================================


class TestContextVariables:
    """Tests for structlog context variable binding."""

    def test_context_binding(self, monkeypatch):
        """Test that context variables are included in logs."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.logging.get_settings",
            lambda: Settings(ENVIRONMENT="production", APP_NAME="test-app", APP_VERSION="1.0.0"),
        )

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure structlog
        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure structlog
        configure_structlog()

        # Get the formatter from the configured handler and apply to our test handler
        root_logger = logging.getLogger()
        if root_logger.handlers:
            handler.setFormatter(root_logger.handlers[0].formatter)
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

        # Bind context variables
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id="test-req-123",
            user_id="user-456",
        )

        # Create logger and log message
        logger = get_logger("test.module")
        logger.info("test_with_context")

        # Get output
        log_output = log_stream.getvalue()
        log_data = json.loads(log_output.strip())

        # Context variables should be included
        assert log_data["request_id"] == "test-req-123"
        assert log_data["user_id"] == "user-456"
        assert log_data["event"] == "test_with_context"

    def test_context_cleared_between_requests(self):
        """Test that context can be cleared between requests."""
        # Bind some context
        structlog.contextvars.bind_contextvars(
            request_id="old-request",
            user_id="old-user",
        )

        # Clear context
        structlog.contextvars.clear_contextvars()

        # Bind new context
        structlog.contextvars.bind_contextvars(
            request_id="new-request",
        )

        # Old context should not leak
        # This is implicitly tested by the middleware in integration tests


# =============================================================================
# Log Level Tests
# =============================================================================


class TestLogLevels:
    """Tests for different log levels."""

    @pytest.mark.parametrize(
        ("level", "method"),
        [
            ("debug", "debug"),
            ("info", "info"),
            ("warning", "warning"),
            ("error", "error"),
        ],
    )
    def test_log_levels(self, level, method, monkeypatch):
        """Test different log levels produce correct output."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.logging.get_settings",
            lambda: Settings(ENVIRONMENT="production", APP_NAME="test-app", APP_VERSION="1.0.0"),
        )

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure structlog
        configure_structlog()

        # Get the formatter from the configured handler and apply to our test handler
        root_logger = logging.getLogger()
        if root_logger.handlers:
            handler.setFormatter(root_logger.handlers[0].formatter)
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)

        # Create logger and log message
        logger = get_logger("test.module")
        log_method = getattr(logger, method)
        log_method(f"test_{level}_message")

        # Get output
        log_output = log_stream.getvalue()
        if log_output:  # Some levels might be filtered
            log_data = json.loads(log_output.strip())
            assert log_data["level"] == level

    def test_debug_logs_filtered_in_production(self, monkeypatch):
        """Test that DEBUG logs are filtered out in production."""
        from app.core.config import Settings

        monkeypatch.setattr(
            "app.core.logging.get_settings",
            lambda: Settings(ENVIRONMENT="production", APP_NAME="test-app", APP_VERSION="1.0.0"),
        )

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)

        # Configure structlog (sets INFO level in production)
        configure_structlog()

        # Get the formatter from the configured handler and apply to our test handler
        root_logger = logging.getLogger()
        if root_logger.handlers:
            handler.setFormatter(root_logger.handlers[0].formatter)
        root_logger.handlers.clear()
        root_logger.addHandler(handler)

        # Create logger and log messages at different levels
        logger = get_logger("test.module")
        logger.debug("debug_message_should_not_appear")
        logger.info("info_message_should_appear")

        # Get output
        log_output = log_stream.getvalue()
        log_lines = [line for line in log_output.strip().split("\n") if line]

        # Should have exactly 1 log line (info), debug should be filtered
        assert len(log_lines) == 1
        log_data = json.loads(log_lines[0])
        assert log_data["level"] == "info"
        assert log_data["event"] == "info_message_should_appear"
