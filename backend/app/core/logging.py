"""
Structured logging configuration using structlog.

Provides JSON logging for production and human-readable console logging
for development. Includes context binding for request correlation.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

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
        _logger: The logger instance (unused).
        _method_name: The method name (unused).
        event_dict: The event dictionary to modify.

    Returns:
        Modified event dictionary with app context.
    """
    settings = get_settings()
    event_dict["app_name"] = settings.APP_NAME
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def configure_structlog() -> None:
    """
    Configure structlog for structured logging.

    Sets up processors based on environment:
    - Production: JSON output for log aggregation
    - Development: Console output with colors for readability

    All logs include:
    - timestamp: ISO 8601 format with UTC timezone
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name (module path)
    - event: Log message
    - Additional context from context binding
    """
    settings = get_settings()

    # Shared processors for all environments
    shared_processors: list[Processor] = [
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add logger name to event dict
        structlog.stdlib.add_logger_name,
        # Add timestamp in ISO 8601 format
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add application context
        add_app_context,
        # Format stack info if present
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.format_exc_info,
        # Decode unicode
        structlog.processors.UnicodeDecoder(),
    ]

    # Environment-specific processors
    if settings.ENVIRONMENT == "production":
        # JSON output for production (for log aggregation systems)
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        # Console output with colors for development
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.rich_traceback,
        )

    # Configure structlog
    structlog.configure(
        processors=[
            # Filter by log level
            structlog.stdlib.filter_by_level,
            # Merge context vars
            structlog.contextvars.merge_contextvars,
            *shared_processors,
            # Must be before the renderer
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # Use standard library logger factory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger instances for performance
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to work with structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            # Remove _record and _from_structlog added by wrap_for_formatter
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    # Set up handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG)

    # Set log level for noisy third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> Any:
    """
    Get a structlog logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.
              If None, returns the root logger.

    Returns:
        Configured structlog logger.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_logged_in", user_id=123, username="alice")
    """
    return structlog.get_logger(name)
