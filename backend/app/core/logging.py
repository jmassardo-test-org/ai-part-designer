"""
Structured logging configuration using structlog.

Provides JSON-formatted logs with consistent context including:
- Timestamps
- Log levels
- Logger names
- Request IDs
- User IDs
- Additional context fields
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog

from app.core.config import get_settings

if TYPE_CHECKING:
    from structlog.types import EventDict, Processor


def add_app_context(
    _logger: logging.Logger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add application-level context to log entries.

    Args:
        _logger: The logger instance (required by structlog signature)
        _method_name: The logging method name (required by structlog signature)
        event_dict: The event dictionary

    Returns:
        Updated event dictionary with app context
    """
    settings = get_settings()
    event_dict["app"] = settings.APP_NAME
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def configure_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up structlog with JSON formatting for production and
    human-readable output for development. Configures both
    structlog and standard library logging to work together.
    """
    settings = get_settings()

    # Determine log level
    log_level_str = getattr(settings, "LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Determine processors based on environment
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_app_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.ENVIRONMENT == "production":
        # Production: JSON output for log aggregation
        processors = [*shared_processors, structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
    else:
        # Development: Human-readable output with colors
        processors = [*shared_processors, structlog.processors.ExceptionRenderer(), structlog.dev.ConsoleRenderer(colors=True)]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured structlog logger.

    Args:
        name: Optional logger name. If not provided, uses the calling module's name.

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)
