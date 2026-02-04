"""
API routes for content reports and moderation.

Handles report submission and admin moderation tools.
"""

from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.rating import (
    ReportCreate,
    ReportResponse,
    ReportDetailResponse,
    ReportResolve,
    ReportListResponse,
    BanCreate,
    BanResponse,
    BanDetailResponse,
    BanListResponse,
    UnbanRequest,
    ModerationStats,
    ModerationQueue,
    ModerationQueueItem,
)
from app.services.rating_service import (
    ReportService,
    BanService,
    ModerationService,
)

router = APIRouter(tags=["reports"])


# =============================================================================
# Report Submission (User)
# =============================================================================


@router.post(
    "/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    """Submit a content report.
    
    Users can report templates, comments, designs, or other users.
    """
    service = ReportService(db)
    
    try:
        report = await service.create_report(current_user.id, data)
        await db.commit()
    except Exception as e:
        # Handle duplicate report
        if "uq_report_user_target" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already reported this content",
            )
        raise
    
    return ReportResponse.model_validate(report)


@router.get(
    "/reports/my",
    response_model=list[ReportResponse],
)
async def get_my_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportResponse]:
    """Get current user's submitted reports."""
    # This would need a service method
    from sqlalchemy import select
    from app.models.rating import ContentReport
    
    stmt = (
        select(ContentReport)
        .where(ContentReport.reporter_id == current_user.id)
        .order_by(ContentReport.created_at.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()
    
    return [ReportResponse.model_validate(r) for r in reports]


# =============================================================================
# Admin Moderation - Reports
# =============================================================================


@router.get(
    "/admin/reports",
    response_model=ReportListResponse,
)
async def get_pending_reports(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportListResponse:
    """Get pending reports for moderation (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    service = ReportService(db)
    offset = (page - 1) * per_page
    reports, total = await service.get_pending_reports(per_page, offset)
    
    items = []
    for report in reports:
        items.append(ReportDetailResponse(
            id=report.id,
            reporter_id=report.reporter_id,
            target_type=report.target_type,
            target_id=report.target_id,
            reason=report.reason,
            description=report.description,
            status=report.status,
            created_at=report.created_at,
            resolved_by_id=report.resolved_by_id,
            resolved_at=report.resolved_at,
            resolution_notes=report.resolution_notes,
            action_taken=report.action_taken,
            reporter_name=report.reporter.display_name if report.reporter else None,
        ))
    
    return ReportListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if per_page > 0 else 0,
    )


@router.get(
    "/admin/reports/{report_id}",
    response_model=ReportDetailResponse,
)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetailResponse:
    """Get a specific report (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    service = ReportService(db)
    report = await service.get_report(report_id)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    return ReportDetailResponse.model_validate(report)


@router.post(
    "/admin/reports/{report_id}/resolve",
    response_model=ReportDetailResponse,
)
async def resolve_report(
    report_id: UUID,
    data: ReportResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetailResponse:
    """Resolve a report with an action (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    service = ReportService(db)
    report = await service.resolve_report(report_id, current_user.id, data)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    await db.commit()
    return ReportDetailResponse.model_validate(report)


@router.post(
    "/admin/reports/{report_id}/dismiss",
    response_model=ReportDetailResponse,
)
async def dismiss_report(
    report_id: UUID,
    notes: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportDetailResponse:
    """Dismiss a report as invalid (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    service = ReportService(db)
    report = await service.dismiss_report(report_id, current_user.id, notes)
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    
    await db.commit()
    return ReportDetailResponse.model_validate(report)


# =============================================================================
# Admin Moderation - Bans
# =============================================================================


@router.post(
    "/admin/bans",
    response_model=BanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ban_user(
    data: BanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BanResponse:
    """Ban a user (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    # Prevent banning yourself
    if data.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ban yourself",
        )
    
    service = BanService(db)
    
    # Check if user is already banned
    existing_ban = await service.get_active_ban(data.user_id)
    if existing_ban:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already banned",
        )
    
    ban = await service.ban_user(current_user.id, data)
    await db.commit()
    
    return BanResponse.model_validate(ban)


@router.get(
    "/admin/bans",
    response_model=BanListResponse,
)
async def get_active_bans(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BanListResponse:
    """Get all active bans (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    service = BanService(db)
    offset = (page - 1) * per_page
    bans, total = await service.get_active_bans(per_page, offset)
    
    items = []
    for ban in bans:
        items.append(BanDetailResponse(
            id=ban.id,
            user_id=ban.user_id,
            reason=ban.reason,
            banned_by_id=ban.banned_by_id,
            is_permanent=ban.is_permanent,
            expires_at=ban.expires_at,
            is_active=ban.is_active,
            created_at=ban.created_at,
            user_email=ban.user.email if ban.user else None,
            user_name=ban.user.display_name if ban.user else None,
        ))
    
    return BanListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=ceil(total / per_page) if per_page > 0 else 0,
    )


@router.post(
    "/admin/bans/{ban_id}/unban",
    response_model=BanResponse,
)
async def unban_user(
    ban_id: UUID,
    data: UnbanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BanResponse:
    """Unban a user (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    service = BanService(db)
    ban = await service.unban_user(ban_id, current_user.id, data.reason)
    
    if not ban:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ban not found",
        )
    
    await db.commit()
    return BanResponse.model_validate(ban)


@router.get(
    "/admin/users/{user_id}/bans",
    response_model=list[BanDetailResponse],
)
async def get_user_ban_history(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BanDetailResponse]:
    """Get ban history for a user (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    service = BanService(db)
    bans = await service.get_user_ban_history(user_id)
    
    return [BanDetailResponse.model_validate(b) for b in bans]


# =============================================================================
# Admin Moderation - Dashboard
# =============================================================================


@router.get(
    "/admin/moderation/stats",
    response_model=ModerationStats,
)
async def get_moderation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModerationStats:
    """Get moderation dashboard statistics (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    service = ModerationService(db)
    return await service.get_moderation_stats()


@router.get(
    "/admin/moderation/queue",
    response_model=ModerationQueue,
)
async def get_moderation_queue(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModerationQueue:
    """Get moderation queue with report details (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    report_service = ReportService(db)
    offset = (page - 1) * per_page
    reports, total = await report_service.get_pending_reports(per_page, offset)
    
    items = []
    for report in reports:
        reporter_history = await report_service.get_user_report_count(report.reporter_id)
        items.append(ModerationQueueItem(
            report=ReportDetailResponse(
                id=report.id,
                reporter_id=report.reporter_id,
                target_type=report.target_type,
                target_id=report.target_id,
                reason=report.reason,
                description=report.description,
                status=report.status,
                created_at=report.created_at,
                resolved_by_id=report.resolved_by_id,
                resolved_at=report.resolved_at,
                resolution_notes=report.resolution_notes,
                action_taken=report.action_taken,
                reporter_name=report.reporter.display_name if report.reporter else None,
            ),
            reporter_history=reporter_history,
        ))
    
    return ModerationQueue(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )
