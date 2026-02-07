"""
User-specific API endpoints.

Provides endpoints for user-specific data including audit logs.
"""

import csv
import io
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.api.deps import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.models.audit import AuditActions, AuditLog
from app.models.user import User

logger = get_logger(__name__)

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


@router.get("/users/me/audit-logs/export/csv")
@rate_limit(category="export")
@audit_log(
    action=AuditActions.EXPORT,
    resource_type="audit_logs",
    context_builder=lambda **kwargs: {
        "format": "csv",
        "filters": {
            "action": kwargs.get("action"),
            "resource_type": kwargs.get("resource_type"),
            "status": kwargs.get("status"),
            "start_date": str(kwargs.get("start_date")) if kwargs.get("start_date") else None,
            "end_date": str(kwargs.get("end_date")) if kwargs.get("end_date") else None,
        },
    },
)
async def export_user_audit_logs_csv(
    _request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    status: str | None = Query(None, description="Filter by status (success, failure, error)"),
    start_date: datetime | None = Query(None, description="Filter logs from this date (inclusive)"),
    end_date: datetime | None = Query(None, description="Filter logs until this date (inclusive)"),
) -> StreamingResponse:
    """
    Export audit logs as CSV file.

    Returns all audit log entries for the current user matching the specified filters.
    The export includes all log details in a comma-separated format suitable for
    analysis in spreadsheet applications or compliance reporting.

    Rate limited based on user tier (export category).

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

    # Apply ordering
    query = query.order_by(AuditLog.created_at.desc())

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    logger.info(
        "audit_logs_export_csv",
        user_id=str(current_user.id),
        count=len(logs),
        filters={
            "action": action,
            "resource_type": resource_type,
            "status": status,
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
        },
    )

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "ID",
            "Timestamp",
            "Action",
            "Resource Type",
            "Resource ID",
            "Actor Type",
            "Status",
            "Error Message",
            "IP Address",
            "User Agent",
            "Context",
        ]
    )

    # Data rows
    for log in logs:
        writer.writerow(
            [
                str(log.id),
                log.created_at.isoformat(),
                log.action,
                log.resource_type,
                str(log.resource_id) if log.resource_id else "",
                log.actor_type,
                log.status,
                log.error_message or "",
                log.ip_address or "",
                log.user_agent or "",
                json.dumps(log.context) if log.context else "{}",
            ]
        )

    output.seek(0)

    # Generate filename with date range if specified
    filename_parts = ["audit_logs"]
    if start_date:
        filename_parts.append(f"from_{start_date.strftime('%Y%m%d')}")
    if end_date:
        filename_parts.append(f"to_{end_date.strftime('%Y%m%d')}")
    filename = "_".join(filename_parts) + ".csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/users/me/audit-logs/export/json")
@rate_limit(category="export")
@audit_log(
    action=AuditActions.EXPORT,
    resource_type="audit_logs",
    context_builder=lambda **kwargs: {
        "format": "json",
        "filters": {
            "action": kwargs.get("action"),
            "resource_type": kwargs.get("resource_type"),
            "status": kwargs.get("status"),
            "start_date": str(kwargs.get("start_date")) if kwargs.get("start_date") else None,
            "end_date": str(kwargs.get("end_date")) if kwargs.get("end_date") else None,
        },
    },
)
async def export_user_audit_logs_json(
    _request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    status: str | None = Query(None, description="Filter by status (success, failure, error)"),
    start_date: datetime | None = Query(None, description="Filter logs from this date (inclusive)"),
    end_date: datetime | None = Query(None, description="Filter logs until this date (inclusive)"),
) -> StreamingResponse:
    """
    Export audit logs as JSON file.

    Returns all audit log entries for the current user matching the specified filters.
    The export includes all log details in JSON format suitable for programmatic
    analysis or integration with other systems.

    Rate limited based on user tier (export category).

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

    # Apply ordering
    query = query.order_by(AuditLog.created_at.desc())

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    logger.info(
        "audit_logs_export_json",
        user_id=str(current_user.id),
        count=len(logs),
        filters={
            "action": action,
            "resource_type": resource_type,
            "status": status,
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
        },
    )

    # Convert logs to JSON-serializable format
    logs_data = []
    for log in logs:
        log_dict = {
            "id": str(log.id),
            "timestamp": log.created_at.isoformat(),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "actor_type": log.actor_type,
            "status": log.status,
            "error_message": log.error_message,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "context": log.context,
        }
        logs_data.append(log_dict)

    # Generate JSON
    json_output = json.dumps(
        {
            "export_metadata": {
                "exported_at": datetime.now(UTC).isoformat(),
                "user_id": str(current_user.id),
                "total_records": len(logs),
                "filters": {
                    "action": action,
                    "resource_type": resource_type,
                    "status": status,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                },
            },
            "audit_logs": logs_data,
        },
        indent=2,
    )

    # Generate filename with date range if specified
    filename_parts = ["audit_logs"]
    if start_date:
        filename_parts.append(f"from_{start_date.strftime('%Y%m%d')}")
    if end_date:
        filename_parts.append(f"to_{end_date.strftime('%Y%m%d')}")
    filename = "_".join(filename_parts) + ".json"

    return StreamingResponse(
        iter([json_output]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
