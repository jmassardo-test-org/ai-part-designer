"""
User-specific API endpoints.

Provides endpoints for user-specific data including audit logs.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================


class AuditLogResponse(BaseModel):
    """Response schema for an audit log entry."""

    id: UUID = Field(description="Audit log entry ID")
    action: str = Field(description="Action performed (e.g., create, update, delete, login)")
    resource_type: str = Field(description="Type of resource acted upon")
    resource_id: UUID | None = Field(description="ID of the resource, if applicable")
    actor_type: str = Field(description="Type of actor (user, system, api_key, etc.)")
    status: str = Field(description="Action status (success, failure, error)")
    error_message: str | None = Field(description="Error message, if status is failure or error")
    context: dict[str, Any] = Field(description="Additional context information")
    ip_address: str | None = Field(description="IP address of the request")
    user_agent: str | None = Field(description="User agent string of the request")
    created_at: datetime = Field(description="When the action occurred")

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Response schema for listing audit logs."""

    logs: list[AuditLogResponse] = Field(description="List of audit log entries")
    total: int = Field(description="Total number of audit logs matching the filters")
    skip: int = Field(description="Number of entries skipped")
    limit: int = Field(description="Maximum number of entries returned")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/users/me/audit-logs", response_model=AuditLogListResponse)
async def get_user_audit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of entries to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of entries to return"),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    status: str | None = Query(None, description="Filter by status (success, failure, error)"),
    start_date: datetime | None = Query(None, description="Filter logs from this date (inclusive)"),
    end_date: datetime | None = Query(None, description="Filter logs until this date (inclusive)"),
) -> AuditLogListResponse:
    """
    Get audit logs for the current user.

    Returns a paginated list of audit log entries showing all actions
    performed by or affecting the current user's account.

    Supports filtering by:
    - action: Type of action (e.g., 'create', 'update', 'delete', 'login')
    - resource_type: Type of resource (e.g., 'design', 'project', 'user')
    - status: Action status ('success', 'failure', 'error')
    - start_date/end_date: Date range for the logs
    """
    # Build the base query
    query = select(AuditLog).where(AuditLog.user_id == current_user.id)

    # Apply filters
    if action:
        query = query.where(AuditLog.action == action)

    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    if status:
        query = query.where(AuditLog.status == status)

    if start_date:
        query = query.where(AuditLog.created_at >= start_date)

    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    # Get total count
    from sqlalchemy import func

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        skip=skip,
        limit=limit,
    )
