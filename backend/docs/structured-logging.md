# Structured Logging Guide

This document explains how to use structured logging with `structlog` in the AI Part Designer application.

## Overview

Structured logging provides:
- **JSON output in production** for log aggregation tools (ELK, Splunk, etc.)
- **Human-readable console output in development** with colors
- **Automatic request correlation** with request_id, user_id, path, and method
- **Consistent log structure** across the application

## Basic Usage

### Getting a Logger

Replace standard library logging with structlog:

```python
# ❌ Old way (standard library logging)
import logging
logger = logging.getLogger(__name__)

# ✅ New way (structured logging)
from app.core.logging import get_logger
logger = get_logger(__name__)
```

### Logging with Context

Use keyword arguments instead of string formatting:

```python
# ❌ Old way (string formatting)
logger.info(f"User {user_id} created design {design_id}")
logger.warning(f"Attempt {attempt} failed: {error}")

# ✅ New way (structured logging)
logger.info("user_created_design", user_id=user_id, design_id=design_id)
logger.warning("operation_failed", attempt=attempt, error=str(error), error_type=type(error).__name__)
```

### Event Naming Convention

Use descriptive, snake_case event names that describe what happened:

```python
# Good event names
logger.info("database_connection_established", host=db_host, port=db_port)
logger.info("user_logged_in", user_id=user.id, username=user.username)
logger.warning("rate_limit_exceeded", user_id=user.id, limit=limit, current=current)
logger.error("payment_processing_failed", order_id=order_id, error=str(e))

# Avoid generic names
logger.info("success")  # ❌ Too vague
logger.info("error")    # ❌ Too vague
```

## Automatic Request Context

The `RequestContextMiddleware` automatically binds the following context to all logs during request processing:

- `request_id`: Unique identifier for request tracing
- `user_id`: Authenticated user ID (if available)
- `path`: Request path
- `method`: HTTP method

You don't need to manually add these fields - they're automatically included!

```python
# This log entry will automatically include request_id, user_id, path, method
logger.info("design_created", design_id=design.id, template_id=template.id)

# Output in production (JSON):
{
  "event": "design_created",
  "design_id": "123e4567-e89b-12d3-a456-426614174000",
  "template_id": "template-abc",
  "request_id": "XyZ789AbC123",
  "user_id": "user-456",
  "path": "/api/v1/designs",
  "method": "POST",
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "info",
  "logger": "app.services.design"
}
```

## Log Levels

Use appropriate log levels:

- **DEBUG**: Detailed diagnostic information (disabled in production)
- **INFO**: General informational messages about application flow
- **WARNING**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for serious problems
- **EXCEPTION**: Like ERROR but includes exception traceback

```python
logger.debug("cache_lookup", key=cache_key, hit=cache_hit)
logger.info("task_completed", task_id=task_id, duration_ms=duration)
logger.warning("deprecated_api_usage", endpoint=endpoint, user_id=user_id)
logger.error("external_service_error", service="stripe", error=str(e))
logger.exception("unhandled_exception", operation="process_payment")  # Includes traceback
```

## Examples

### Before and After

**Old Style:**
```python
import logging

logger = logging.getLogger(__name__)

async def generate_design(description: str, max_retries: int = 3) -> Design:
    logger.info(f"Generating design for: {description[:100]}...")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}")
            result = await ai_service.generate(description)
            logger.info(f"Generation succeeded in {result.time}ms")
            return result
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
    
    logger.error(f"All {max_retries} attempts failed")
    raise GenerationError("Failed to generate design")
```

**New Style:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

async def generate_design(description: str, max_retries: int = 3) -> Design:
    logger.info(
        "design_generation_started",
        description_preview=description[:100],
        max_retries=max_retries,
    )
    
    for attempt in range(max_retries):
        try:
            logger.info("generation_attempt", attempt=attempt + 1)
            result = await ai_service.generate(description)
            logger.info(
                "generation_succeeded",
                attempt=attempt + 1,
                duration_ms=result.time,
            )
            return result
        except Exception as e:
            logger.warning(
                "generation_attempt_failed",
                attempt=attempt + 1,
                error=str(e),
                error_type=type(e).__name__,
            )
    
    logger.error("all_generation_attempts_failed", max_retries=max_retries)
    raise GenerationError("Failed to generate design")
```

## Migration Checklist

When updating existing code:

1. ✅ Replace `import logging` with `from app.core.logging import get_logger`
2. ✅ Replace `logging.getLogger(__name__)` with `get_logger(__name__)`
3. ✅ Convert f-strings and % formatting to keyword arguments
4. ✅ Use descriptive event names instead of generic messages
5. ✅ Add relevant context (IDs, types, durations, etc.)
6. ✅ Use appropriate log levels
7. ✅ Include error types when logging exceptions

## Production Log Format

In production (ENVIRONMENT=production), logs are output as JSON:

```json
{
  "event": "design_generation_started",
  "description_preview": "Create a mounting bracket for...",
  "max_retries": 3,
  "request_id": "XyZ789AbC123",
  "user_id": "user-456",
  "path": "/api/v1/designs/generate",
  "method": "POST",
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "info",
  "logger": "app.ai.direct_generation",
  "app_name": "ai-part-designer",
  "environment": "production"
}
```

## Development Log Format

In development, logs are formatted for human readability with colors:

```
2024-01-15T10:30:45.123456Z [info     ] design_generation_started  description_preview=Create a mounting bracket for... max_retries=3 request_id=XyZ789AbC123 user_id=user-456 path=/api/v1/designs/generate method=POST
```

## Best Practices

1. **Be specific**: Use descriptive event names that explain what happened
2. **Add context**: Include relevant IDs, types, and metrics
3. **Avoid sensitive data**: Don't log passwords, tokens, or PII
4. **Use keyword arguments**: This creates structured data, not unstructured strings
5. **Log exceptions properly**: Use `logger.exception()` or include `exc_info=True`
6. **Measure performance**: Include duration/timing information when relevant
7. **Think queryability**: Structure your logs so they can be filtered and aggregated

## See Also

- [structlog documentation](https://www.structlog.org/)
- `app/core/logging.py` - Logging configuration
- `app/middleware/request_context.py` - Request context middleware
