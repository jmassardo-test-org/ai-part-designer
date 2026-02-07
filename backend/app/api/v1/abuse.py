"""
Admin Abuse Dashboard API

Provides endpoints for monitoring and managing:
- Active bans
- Abuse reports
- Usage patterns
- Content moderation queues
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_db
from app.core.usage_limits import AbuseReport, UsageRecord
from app.models.rating import UserBan
from app.models.user import User
from app.services.abuse_detection import AbuseDetectionService

router = APIRouter(prefix="/admin/abuse", tags=["admin-abuse"])


# =============================================================================
# Response Schemas
# =============================================================================


class BanResponse(BaseModel):
    """Ban information."""

    id: UUID
    user_id: UUID | None
    ip_address: str | None
    reason: str
    ban_type: str
    expires_at: datetime | None
    is_active: bool
    violation_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AbuseReportResponse(BaseModel):
    """Abuse report information."""

    id: UUID
    user_id: UUID | None
    ip_address: str | None
    trigger_type: str
    severity: str
    description: str
    status: str
    action_taken: str | None
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class UsageStatsResponse(BaseModel):
    """Usage statistics."""

    period: str
    total_generations: int
    total_modifications: int
    total_exports: int
    unique_users: int
    average_per_user: float


class ModerationQueueItem(BaseModel):
    """Item in moderation queue."""

    id: UUID
    user_id: UUID
    user_email: str | None
    content_type: str
    description: str
    severity: str
    created_at: datetime
    status: str


class DashboardStats(BaseModel):
    """Overview statistics for dashboard."""

    active_bans: int
    pending_reports: int
    reports_today: int
    generations_today: int
    flagged_content_today: int
    top_violation_types: list[dict[str, Any]]


# =============================================================================
# Dashboard Overview
# =============================================================================


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> DashboardStats:
    """Get overview statistics for abuse dashboard."""
    now = datetime.now(tz=UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Count active bans
    active_bans_query = select(func.count(UserBan.id)).where(
        and_(
            UserBan.is_active,
            or_(
                UserBan.expires_at.is_(None),
                UserBan.expires_at > now,
            ),
        )
    )
    active_bans = await db.scalar(active_bans_query) or 0

    # Count pending reports
    pending_query = select(func.count(AbuseReport.id)).where(AbuseReport.status == "pending")
    pending_reports = await db.scalar(pending_query) or 0

    # Reports today
    reports_today_query = select(func.count(AbuseReport.id)).where(
        AbuseReport.created_at >= today_start
    )
    reports_today = await db.scalar(reports_today_query) or 0

    # Generations today
    generations_query = select(func.sum(UsageRecord.count)).where(
        and_(
            UsageRecord.resource_type == "generation",
            UsageRecord.period_type == "day",
            UsageRecord.period_start >= today_start,
        )
    )
    generations_today = await db.scalar(generations_query) or 0

    # Flagged content today
    flagged_query = select(func.count(AbuseReport.id)).where(
        and_(
            AbuseReport.created_at >= today_start,
            AbuseReport.trigger_type == "content_moderation",
        )
    )
    flagged_content_today = await db.scalar(flagged_query) or 0

    # Top violation types (last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    violation_query = (
        select(
            AbuseReport.trigger_type,
            func.count(AbuseReport.id).label("count"),
        )
        .where(AbuseReport.created_at >= thirty_days_ago)
        .group_by(AbuseReport.trigger_type)
        .order_by(desc("count"))
        .limit(5)
    )
    violation_result = await db.execute(violation_query)
    top_violations = [
        {"type": row.trigger_type, "count": row.count} for row in violation_result.all()
    ]

    return DashboardStats(
        active_bans=active_bans,
        pending_reports=pending_reports,
        reports_today=reports_today,
        generations_today=generations_today,
        flagged_content_today=flagged_content_today,
        top_violation_types=top_violations,
    )


# =============================================================================
# Ban Management
# =============================================================================


@router.get("/bans", response_model=list[BanResponse])
async def list_bans(
    active_only: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> list[BanResponse]:
    """List all bans with pagination."""
    now = datetime.now(tz=UTC)

    query = select(UserBan)

    if active_only:
        query = query.where(
            and_(
                UserBan.is_active,
                or_(
                    UserBan.expires_at.is_(None),
                    UserBan.expires_at > now,
                ),
            )
        )

    query = query.order_by(desc(UserBan.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    return list(result.scalars().all())  # type: ignore[arg-type]  # FastAPI converts ORM→Pydantic


@router.get("/bans/{ban_id}", response_model=BanResponse)
async def get_ban(
    ban_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> BanResponse:
    """Get ban details."""
    query = select(UserBan).where(UserBan.id == ban_id)
    result = await db.execute(query)
    ban = result.scalar_one_or_none()

    if not ban:
        raise HTTPException(status_code=404, detail="Ban not found")

    return ban  # type: ignore[return-value]  # FastAPI converts ORM→Pydantic


@router.post("/bans/{ban_id}/lift")
async def lift_ban(
    ban_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> dict[str, Any]:
    """Lift a ban manually."""
    service = AbuseDetectionService(db)
    success = await service.lift_ban(ban_id, admin.id)

    if not success:
        raise HTTPException(status_code=404, detail="Ban not found")

    return {"message": "Ban lifted successfully", "ban_id": str(ban_id)}


class CreateBanRequest(BaseModel):
    user_id: UUID | None = None
    ip_address: str | None = None
    reason: str
    ban_type: str = "temporary"  # "temporary", "permanent"
    duration_hours: int | None = 24


@router.post("/bans", response_model=BanResponse, status_code=201)
async def create_ban(
    data: CreateBanRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> BanResponse:
    """Create a manual ban."""
    if not data.user_id and not data.ip_address:
        raise HTTPException(
            status_code=400,
            detail="Must provide user_id or ip_address",
        )

    expires_at = None
    if data.ban_type == "temporary" and data.duration_hours:
        expires_at = datetime.now(tz=UTC) + timedelta(hours=data.duration_hours)

    ban = UserBan(
        user_id=data.user_id,
        ip_address=data.ip_address,
        reason=data.reason,
        ban_type=data.ban_type,
        expires_at=expires_at,
        banned_by=admin.id,
    )

    db.add(ban)
    await db.commit()
    await db.refresh(ban)

    return ban  # type: ignore[return-value]  # FastAPI converts ORM→Pydantic


# =============================================================================
# Abuse Reports
# =============================================================================


@router.get("/reports", response_model=list[AbuseReportResponse])
async def list_reports(
    status: str | None = None,
    severity: str | None = None,
    trigger_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> list[AbuseReportResponse]:
    """List abuse reports with filtering."""
    query = select(AbuseReport)

    conditions = []
    if status:
        conditions.append(AbuseReport.status == status)
    if severity:
        conditions.append(AbuseReport.severity == severity)
    if trigger_type:
        conditions.append(AbuseReport.trigger_type == trigger_type)

    if conditions:
        query = query.where(and_(*conditions))

    query = (
        query.order_by(desc(AbuseReport.created_at)).offset((page - 1) * page_size).limit(page_size)
    )

    result = await db.execute(query)
    return list(result.scalars().all())  # type: ignore[arg-type]  # FastAPI converts ORM→Pydantic


@router.get("/reports/{report_id}", response_model=AbuseReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> AbuseReportResponse:
    """Get abuse report details."""
    query = select(AbuseReport).where(AbuseReport.id == report_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report  # type: ignore[return-value]  # FastAPI converts ORM→Pydantic


class ResolveReportRequest(BaseModel):
    resolution: str
    action_taken: str  # "none", "warning", "temp_ban", "perm_ban", "content_removed"


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: UUID,
    data: ResolveReportRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
) -> dict[str, Any]:
    """Resolve an abuse report."""
    query = select(AbuseReport).where(AbuseReport.id == report_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = "resolved"  # type: ignore[assignment]
    report.resolution = data.resolution  # type: ignore[assignment]
    report.action_taken = data.action_taken  # type: ignore[assignment]
    report.resolved_by = admin.id  # type: ignore[assignment]
    report.resolved_at = datetime.now(tz=UTC)  # type: ignore[assignment]

    await db.commit()

    return {"message": "Report resolved", "report_id": str(report_id)}


# =============================================================================
# Usage Statistics
# =============================================================================


@router.get("/usage/stats")
async def get_usage_stats(
    period: str = Query("day", regex="^(hour|day|week|month)$"),
    resource_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> dict[str, Any]:
    """Get usage statistics."""
    now = datetime.now(tz=UTC)

    period_starts = {
        "hour": now - timedelta(hours=1),
        "day": now - timedelta(days=1),
        "week": now - timedelta(weeks=1),
        "month": now - timedelta(days=30),
    }
    period_start = period_starts.get(period, now - timedelta(days=1))

    conditions = [UsageRecord.created_at >= period_start]
    if resource_type:
        conditions.append(UsageRecord.resource_type == resource_type)

    # Total counts
    total_query = (
        select(
            UsageRecord.resource_type,
            func.sum(UsageRecord.count).label("total"),
            func.count(func.distinct(UsageRecord.user_id)).label("unique_users"),
        )
        .where(and_(*conditions))
        .group_by(UsageRecord.resource_type)
    )

    result = await db.execute(total_query)
    stats = {}

    for row in result.all():
        stats[row.resource_type] = {
            "total": row.total or 0,
            "unique_users": row.unique_users or 0,
            "average_per_user": ((row.total or 0) / max(1, row.unique_users or 1)),
        }

    return {
        "period": period,
        "period_start": period_start.isoformat(),
        "stats": stats,
    }


@router.get("/usage/top-users")
async def get_top_users(
    resource_type: str = "generation",
    period: str = Query("day", regex="^(day|week|month)$"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> dict[str, Any]:
    """Get top users by usage."""
    now = datetime.now(tz=UTC)

    period_starts = {
        "day": now - timedelta(days=1),
        "week": now - timedelta(weeks=1),
        "month": now - timedelta(days=30),
    }
    period_start = period_starts.get(period, now - timedelta(days=1))

    query = (
        select(
            UsageRecord.user_id,
            func.sum(UsageRecord.count).label("total"),
        )
        .where(
            and_(
                UsageRecord.resource_type == resource_type,
                UsageRecord.created_at >= period_start,
            )
        )
        .group_by(UsageRecord.user_id)
        .order_by(desc("total"))
        .limit(limit)
    )

    result = await db.execute(query)

    top_users = []
    for row in result.all():
        # Get user info
        user_query = select(User).where(User.id == row.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        top_users.append(
            {
                "user_id": str(row.user_id),
                "email": user.email if user else "Unknown",
                "total": row.total,
            }
        )

    return {
        "period": period,
        "resource_type": resource_type,
        "top_users": top_users,
    }


# =============================================================================
# Moderation Queue
# =============================================================================


@router.get("/moderation-queue")
async def get_moderation_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> dict[str, Any]:
    """Get items pending moderation review."""
    query = (
        select(AbuseReport)
        .where(AbuseReport.status == "pending")
        .order_by(
            # Critical first, then by date
            desc(AbuseReport.severity == "critical"),
            desc(AbuseReport.severity == "high"),
            AbuseReport.created_at,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    reports = result.scalars().all()

    queue_items = []
    for report in reports:
        # Get user email if available
        user_email = None
        if report.user_id:
            user_query = select(User.email).where(User.id == report.user_id)
            user_result = await db.execute(user_query)
            user_email = user_result.scalar_one_or_none()

        queue_items.append(
            {
                "id": str(report.id),
                "user_id": str(report.user_id) if report.user_id else None,
                "user_email": user_email,
                "content_type": report.trigger_type,
                "description": report.description[:200],  # Truncate
                "severity": report.severity,
                "created_at": report.created_at.isoformat(),
                "status": report.status,
                "prompt": report.prompt[:100] if report.prompt else None,
            }
        )

    # Get total count
    count_query = select(func.count(AbuseReport.id)).where(AbuseReport.status == "pending")
    total = await db.scalar(count_query) or 0

    return {
        "items": queue_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
