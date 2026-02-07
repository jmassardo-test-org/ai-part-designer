"""
Audit logging decorators and utilities.

Provides decorators for easy application of audit logging to API endpoints.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from fastapi import Request
from structlog import get_logger

from app.models.audit import AuditLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = get_logger(__name__)

# Type variable for generic function signatures
F = TypeVar("F", bound=Callable[..., Any])


def audit_log(
    action: str,
    resource_type: str,
    resource_id_param: str | None = None,
    context_builder: Callable[..., dict[str, Any]] | None = None,
) -> Callable[[F], F]:
    """
    Decorator to add audit logging to API endpoints.

    This decorator automatically logs sensitive actions to the audit log,
    capturing user, resource, request metadata, and custom context.

    Args:
        action: The action being performed (e.g., "create", "update", "delete")
                Use AuditActions constants for common actions.
        resource_type: The type of resource being acted upon (e.g., "design", "share")
        resource_id_param: Optional parameter name to extract resource ID from.
                          Can be a path parameter, kwarg, or response attribute.
                          Examples: "design_id", "id", "response.id"
        context_builder: Optional function to build custom context dict.
                        Receives all endpoint args/kwargs and should return dict.

    Returns:
        Decorated function that logs audit trail.

    Example:
        >>> @audit_log(
        ...     action=AuditActions.CREATE,
        ...     resource_type="design",
        ...     resource_id_param="response.id",
        ...     context_builder=lambda **kwargs: {
        ...         "name": kwargs["request"].name
        ...     }
        ... )
        >>> async def create_design(
        ...     request: DesignCreate,
        ...     current_user: User = Depends(get_current_user),
        ...     db: AsyncSession = Depends(get_db),
        ... ) -> DesignResponse:
        ...     ...

    Context is automatically enriched with:
        - Request ID from request state
        - IP address from request
        - User agent from request headers
        - Resource ID if extractable
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract common dependencies from kwargs
            current_user: User | None = kwargs.get("current_user")
            db: AsyncSession | None = kwargs.get("db")

            # Try to find Request object - look in args and kwargs
            request: Request | None = None

            # Check kwargs first (most likely from FastAPI dependency injection)
            for value in kwargs.values():
                if isinstance(value, Request):
                    request = value
                    break

            # Check args if not found in kwargs
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            # Execute the endpoint
            result = await func(*args, **kwargs)

            # Only log if we have database session
            if db is None:
                logger.warning(
                    "audit_log_skipped_no_db",
                    action=action,
                    resource_type=resource_type,
                )
                return result

            # Extract resource ID
            resource_id: UUID | None = None
            if resource_id_param:
                resource_id = _extract_resource_id(
                    resource_id_param,
                    result,
                    kwargs,
                )

            # Build context
            context: dict[str, Any] = {}
            if context_builder:
                try:
                    context = context_builder(result=result, **kwargs)
                except Exception as e:
                    logger.warning(
                        "audit_context_builder_failed",
                        error=str(e),
                        action=action,
                    )

            # Extract request metadata
            ip_address: str | None = None
            user_agent: str | None = None
            request_id: str | None = None

            if request:
                # Get client IP (handle proxies)
                ip_address = request.headers.get("X-Forwarded-For")
                if ip_address:
                    # Take first IP if multiple (client, proxy1, proxy2, ...)
                    ip_address = ip_address.split(",")[0].strip()
                else:
                    ip_address = request.client.host if request.client else None

                user_agent = request.headers.get("User-Agent")
                request_id = getattr(request.state, "request_id", None)

            # Add request metadata to context
            if request_id:
                context["request_id"] = request_id

            # Create audit log entry
            try:
                audit_entry = AuditLog.log_success(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    user_id=current_user.id if current_user else None,
                    context=context,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                db.add(audit_entry)
                await db.flush()

                logger.info(
                    "audit_logged",
                    action=action,
                    resource_type=resource_type,
                    resource_id=str(resource_id) if resource_id else None,
                    user_id=str(current_user.id) if current_user else None,
                )
            except Exception as e:
                # Don't fail the request if audit logging fails
                logger.error(
                    "audit_log_failed",
                    action=action,
                    resource_type=resource_type,
                    error=str(e),
                )

            return result

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # For synchronous functions, we can't log to DB
            # Just log a warning and continue
            logger.warning(
                "audit_log_unsupported_sync",
                action=action,
                resource_type=resource_type,
            )
            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _extract_resource_id(
    param_path: str,
    result: Any,
    kwargs: dict[str, Any],
) -> UUID | None:
    """
    Extract resource ID from parameters or result.

    Args:
        param_path: Dot-separated path to the ID (e.g., "design_id", "response.id")
        result: The endpoint result
        kwargs: The endpoint kwargs

    Returns:
        Extracted UUID or None if not found
    """
    parts = param_path.split(".")

    # Special case: "response.something" means look in result
    if parts[0] == "response":
        obj = result
        parts = parts[1:]
    else:
        # Look in kwargs first
        if parts[0] in kwargs:
            obj = kwargs[parts[0]]
            parts = parts[1:]
        else:
            return None

    # Navigate the path
    for part in parts:
        if hasattr(obj, part):
            obj = getattr(obj, part)
        elif isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return None

    # Convert to UUID if needed
    if isinstance(obj, UUID):
        return obj
    if isinstance(obj, str):
        try:
            return UUID(obj)
        except ValueError:
            return None

    return None


def audit_failure(
    action: str,
    resource_type: str,
    error_message: str,
    user: User | None,
    db: AsyncSession,
    resource_id: UUID | None = None,
    context: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """
    Log a failed action to the audit log.

    Use this in exception handlers to log failed attempts.

    Args:
        action: The action that failed
        resource_type: The type of resource
        error_message: Error message describing the failure
        user: The user who attempted the action (if authenticated)
        db: Database session
        resource_id: Optional resource ID
        context: Optional additional context
        request: Optional request object for metadata

    Example:
        >>> try:
        ...     await delete_design(design_id, user, db)
        ... except HTTPException as e:
        ...     await audit_failure(
        ...         action=AuditActions.DELETE,
        ...         resource_type="design",
        ...         error_message=str(e.detail),
        ...         user=current_user,
        ...         db=db,
        ...         resource_id=design_id,
        ...     )
        ...     raise
    """
    # Extract request metadata
    ip_address: str | None = None
    user_agent: str | None = None

    if request:
        ip_address = request.headers.get("X-Forwarded-For")
        if ip_address:
            ip_address = ip_address.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

    # Create failure audit log
    audit_entry = AuditLog.log_failure(
        action=action,
        resource_type=resource_type,
        error_message=error_message,
        resource_id=resource_id,
        user_id=user.id if user else None,
        context=context or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    db.add(audit_entry)
    # Note: Caller should commit/flush as appropriate

    logger.warning(
        "audit_failure_logged",
        action=action,
        resource_type=resource_type,
        error=error_message,
        user_id=str(user.id) if user else None,
    )
