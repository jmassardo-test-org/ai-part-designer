"""
Admin License Management API endpoints (Epic 13).

Provides endpoints for admin-only license enforcement:
- Design takedown for license violations
- License violation report listing and management
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 — FastAPI needs UUID at runtime for path params

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select

from app.api.deps import get_current_admin_user
from app.core.auth import AuthContext  # noqa: TC001 — FastAPI needs this at runtime for Depends()
from app.core.database import get_db
from app.models.rating import ContentReport, ReportStatus, ReportTargetType
from app.schemas.license import (
    TakedownRequest,
    TakedownResponse,
)
from app.services.license_service import LicenseService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Admin Takedown
# =============================================================================


@router.post(
    "/designs/{design_id}/takedown",
    response_model=TakedownResponse,
    status_code=status.HTTP_200_OK,
)
async def admin_takedown_design(
    design_id: UUID,
    data: TakedownRequest,
    db: AsyncSession = Depends(get_db),
    auth_ctx: AuthContext = Depends(get_current_admin_user),
) -> TakedownResponse:
    """Admin takedown of a design for licensing violations.

    Unpublishes the design, records an audit trail, and optionally
    resolves the linked violation report.

    Requires admin role.
    """
    service = LicenseService(db)
    try:
        return await service.admin_takedown(
            design_id=design_id,
            admin_user=auth_ctx.user,
            reason=data.reason,
            violation_report_id=data.violation_report_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# =============================================================================
# Admin License Violation Reports
# =============================================================================


@router.get(
    "/license-violations",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def list_license_violations(
    report_status: str | None = Query(
        None,
        description="Filter by status: pending, reviewing, resolved, dismissed",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    _admin_user: AuthContext = Depends(get_current_admin_user),
) -> dict:
    """List license violation reports for admin review.

    Returns a paginated list of license violation reports,
    optionally filtered by status. Requires admin role.
    """
    # Validate status filter if provided
    valid_statuses = {s.value for s in ReportStatus}
    if report_status and report_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    # Base query: only LICENSE_VIOLATION reports
    base_filter = ContentReport.target_type == ReportTargetType.LICENSE_VIOLATION

    # Optional status filter
    if report_status:
        base_filter = base_filter & (ContentReport.status == report_status)

    # Count query
    count_stmt = select(func.count()).select_from(ContentReport).where(base_filter)
    total = (await db.execute(count_stmt)).scalar_one()

    total_pages = max(1, (total + page_size - 1) // page_size)

    # Data query with ordering (newest first)
    offset = (page - 1) * page_size
    stmt = (
        select(ContentReport)
        .where(base_filter)
        .order_by(desc(ContentReport.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()

    items = [
        {
            "id": str(report.id),
            "design_id": str(report.target_id),
            "violation_type": report.reason,
            "status": report.status if isinstance(report.status, str) else report.status.value,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "reporter_id": str(report.reporter_id),
            "description": report.description,
            "evidence_url": report.evidence_url,
            "resolved_by_id": str(report.resolved_by_id) if report.resolved_by_id else None,
            "resolved_at": report.resolved_at.isoformat() if report.resolved_at else None,
            "resolution_notes": report.resolution_notes,
            "action_taken": report.action_taken,
        }
        for report in reports
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
