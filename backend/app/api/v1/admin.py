"""
Admin API.

Provides endpoints for:
- Viewing moderation queue
- Approving/rejecting flagged content
- Managing user warnings and bans
- Moderation statistics
- Subscription management
- Organization management
- Component library management
- Notification/announcement management
- File/storage management
- Audit logs and security
- System health monitoring
- CAD v2 component registry management
- Starter design management
- Marketplace administration
"""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user, require_admin
from app.core.database import get_db
from app.models.api_key import APIKey
from app.models.audit import AuditLog
from app.models.file import File as FileModel
from app.models.moderation import ModerationLog
from app.models.notification import Notification
from app.models.organization import Organization, OrganizationMember
from app.models.reference_component import ReferenceComponent
from app.models.subscription import CreditBalance, SubscriptionTier
from app.models.user import Subscription, User
from app.services.security_audit import SecurityAuditService, SecurityEventType

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class ModerationItemResponse(BaseModel):
    """A moderation queue item."""

    id: UUID
    design_id: UUID | None
    user_id: UUID
    user_email: str | None = None
    content_type: str
    content_text: str | None = None
    decision: str
    reason: str | None = None
    confidence_score: float | None = None
    details: dict[str, Any] = Field(default_factory=dict[str, Any])
    is_appealed: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class ModerationQueueResponse(BaseModel):
    """Paginated moderation queue."""

    items: list[ModerationItemResponse]
    total: int
    page: int
    page_size: int
    pending_count: int
    escalated_count: int


class ModerationDecisionRequest(BaseModel):
    """Request to approve or reject content."""

    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional review notes",
    )


class RejectContentRequest(BaseModel):
    """Request to reject content with reason."""

    reason: str = Field(
        ...,
        max_length=100,
        description="Rejection reason category",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Additional notes",
    )
    warn_user: bool = Field(
        default=False,
        description="Also issue a warning to the user",
    )


class ModerationDecisionResponse(BaseModel):
    """Response after moderation decision."""

    id: UUID
    decision: str
    reviewed_by: UUID
    reviewed_at: datetime
    message: str


class UserWarningRequest(BaseModel):
    """Request to issue a user warning."""

    category: str = Field(
        ...,
        description="Warning category",
    )
    severity: str = Field(
        default="low",
        description="Warning severity (low, medium, high)",
    )
    message: str = Field(
        ...,
        max_length=1000,
        description="Warning message to user",
    )
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Days until warning expires (null = permanent)",
    )


class UserWarningResponse(BaseModel):
    """User warning details."""

    id: UUID
    user_id: UUID
    category: str
    severity: str
    message: str
    acknowledged: bool
    created_at: datetime
    expires_at: datetime | None


class UserBanRequest(BaseModel):
    """Request to ban a user."""

    reason: str = Field(
        ...,
        max_length=1000,
        description="Ban reason",
    )
    is_permanent: bool = Field(
        default=False,
        description="Whether ban is permanent",
    )
    duration_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Ban duration in days (if not permanent)",
    )


class UserBanResponse(BaseModel):
    """User ban details."""

    id: UUID
    user_id: UUID
    reason: str
    is_permanent: bool
    expires_at: datetime | None
    created_at: datetime


class ModerationStatsResponse(BaseModel):
    """Moderation statistics."""

    pending_count: int
    escalated_count: int
    approved_today: int
    rejected_today: int
    appeals_pending: int
    avg_review_time_hours: float | None


# =============================================================================
# Helper Functions
# =============================================================================


async def get_moderation_item_or_404(
    item_id: UUID,
    db: AsyncSession,
) -> ModerationLog:
    """Get moderation item by ID."""
    query = (
        select(ModerationLog)
        .options(selectinload(ModerationLog.user))
        .where(ModerationLog.id == item_id)
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moderation item not found",
        )

    return item


# =============================================================================
# Moderation Queue Endpoints
# =============================================================================


@router.get(
    "/moderation/queue",
    response_model=ModerationQueueResponse,
    summary="Get moderation queue",
    description="List items pending moderation review (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_moderation_queue(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query()] = None,
    _severity_filter: Annotated[str | None, Query()] = None,  # TODO: Implement severity filtering
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ModerationQueueResponse:
    """Get paginated moderation queue."""

    # Base query
    base_query = select(ModerationLog).options(selectinload(ModerationLog.user))

    # Apply filters
    filters = []
    if status_filter:
        filters.append(ModerationLog.decision == status_filter)
    else:
        # Default: show pending and escalated
        filters.append(ModerationLog.decision.in_(["pending_review", "escalated"]))

    if filters:
        base_query = base_query.where(and_(*filters))

    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Count pending and escalated
    pending_count = (
        await db.execute(select(func.count()).where(ModerationLog.decision == "pending_review"))
    ).scalar_one()

    escalated_count = (
        await db.execute(select(func.count()).where(ModerationLog.decision == "escalated"))
    ).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = base_query.order_by(ModerationLog.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return ModerationQueueResponse(
        items=[
            ModerationItemResponse(
                id=item.id,
                design_id=item.design_id,
                user_id=item.user_id,
                user_email=item.user.email if item.user else None,
                content_type=item.content_type,
                content_text=item.content_text,
                decision=item.decision,
                reason=item.reason,
                confidence_score=item.confidence_score,
                details=item.details,
                is_appealed=item.is_appealed,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        pending_count=pending_count,
        escalated_count=escalated_count,
    )


@router.get(
    "/moderation/stats",
    response_model=ModerationStatsResponse,
    summary="Get moderation stats",
    description="Get moderation statistics.",
    dependencies=[Depends(require_admin())],
)
async def get_moderation_stats(
    db: AsyncSession = Depends(get_db),
) -> ModerationStatsResponse:
    """Get moderation statistics."""
    today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    # Count pending
    pending_count = (
        await db.execute(select(func.count()).where(ModerationLog.decision == "pending_review"))
    ).scalar_one()

    # Count escalated
    escalated_count = (
        await db.execute(select(func.count()).where(ModerationLog.decision == "escalated"))
    ).scalar_one()

    # Count approved today
    approved_today = (
        await db.execute(
            select(func.count()).where(
                ModerationLog.decision == "approved",
                ModerationLog.reviewed_at >= today_start,
            )
        )
    ).scalar_one()

    # Count rejected today
    rejected_today = (
        await db.execute(
            select(func.count()).where(
                ModerationLog.decision == "rejected",
                ModerationLog.reviewed_at >= today_start,
            )
        )
    ).scalar_one()

    # Count pending appeals
    appeals_pending = (
        await db.execute(
            select(func.count()).where(
                ModerationLog.is_appealed,
                ModerationLog.appeal_decision.is_(None),
            )
        )
    ).scalar_one()

    return ModerationStatsResponse(
        pending_count=pending_count,
        escalated_count=escalated_count,
        approved_today=approved_today,
        rejected_today=rejected_today,
        appeals_pending=appeals_pending,
        avg_review_time_hours=None,  # Would calculate from reviewed_at - created_at
    )


@router.get(
    "/moderation/{item_id}",
    response_model=ModerationItemResponse,
    summary="Get moderation item",
    description="Get details of a specific moderation item.",
    dependencies=[Depends(require_admin())],
)
async def get_moderation_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ModerationItemResponse:
    """Get moderation item details."""
    item = await get_moderation_item_or_404(item_id, db)

    return ModerationItemResponse(
        id=item.id,
        design_id=item.design_id,
        user_id=item.user_id,
        user_email=item.user.email if item.user else None,
        content_type=item.content_type,
        content_text=item.content_text,
        decision=item.decision,
        reason=item.reason,
        confidence_score=item.confidence_score,
        details=item.details,
        is_appealed=item.is_appealed,
        created_at=item.created_at,
    )


@router.post(
    "/moderation/{item_id}/approve",
    response_model=ModerationDecisionResponse,
    summary="Approve content",
    description="Approve flagged content after review.",
    dependencies=[Depends(require_admin())],
)
async def approve_content(
    item_id: UUID,
    request: ModerationDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModerationDecisionResponse:
    """Approve content after review."""
    item = await get_moderation_item_or_404(item_id, db)

    if item.decision == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content already approved",
        )

    # Update item
    item.decision = "approved"
    item.reviewer_id = current_user.id
    item.reviewed_at = datetime.now(tz=UTC)

    if request.notes:
        item.details["review_notes"] = request.notes

    await db.commit()

    return ModerationDecisionResponse(
        id=item.id,
        decision="approved",
        reviewed_by=current_user.id,
        reviewed_at=item.reviewed_at,
        message="Content approved successfully",
    )


@router.post(
    "/moderation/{item_id}/reject",
    response_model=ModerationDecisionResponse,
    summary="Reject content",
    description="Reject flagged content with reason.",
    dependencies=[Depends(require_admin())],
)
async def reject_content(
    item_id: UUID,
    request: RejectContentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModerationDecisionResponse:
    """Reject content after review."""
    item = await get_moderation_item_or_404(item_id, db)

    if item.decision == "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content already rejected",
        )

    # Update item
    item.decision = "rejected"
    item.reason = request.reason
    item.reviewer_id = current_user.id
    item.reviewed_at = datetime.now(tz=UTC)

    if request.notes:
        item.details["review_notes"] = request.notes

    # Optionally issue warning
    if request.warn_user:
        # Create warning (simplified - would use UserWarning model)
        item.details["warning_issued"] = True

    await db.commit()

    return ModerationDecisionResponse(
        id=item.id,
        decision="rejected",
        reviewed_by=current_user.id,
        reviewed_at=item.reviewed_at,
        message=f"Content rejected: {request.reason}",
    )


@router.post(
    "/moderation/{item_id}/escalate",
    response_model=ModerationDecisionResponse,
    summary="Escalate for review",
    description="Escalate item for senior review.",
    dependencies=[Depends(require_admin())],
)
async def escalate_content(
    item_id: UUID,
    request: ModerationDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModerationDecisionResponse:
    """Escalate content for senior review."""
    item = await get_moderation_item_or_404(item_id, db)

    item.decision = "escalated"
    item.details["escalated_by"] = str(current_user.id)
    item.details["escalated_at"] = datetime.now(tz=UTC).isoformat()

    if request.notes:
        item.details["escalation_notes"] = request.notes

    await db.commit()

    return ModerationDecisionResponse(
        id=item.id,
        decision="escalated",
        reviewed_by=current_user.id,
        reviewed_at=datetime.now(tz=UTC),
        message="Content escalated for senior review",
    )


# =============================================================================
# User Management Endpoints
# =============================================================================


@router.post(
    "/users/{user_id}/warn",
    response_model=UserWarningResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue warning",
    description="Issue a warning to a user.",
    dependencies=[Depends(require_admin())],
)
async def warn_user(
    user_id: UUID,
    request: UserWarningRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserWarningResponse:
    """Issue a warning to a user."""
    # Verify user exists
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(tz=UTC) + timedelta(days=request.expires_in_days)

    # Store warning in user's extra_data (simplified)
    # In production, use dedicated UserWarning model
    warnings = user.extra_data.get("warnings", [])
    warning_id = str(uuid4())
    warnings.append(
        {
            "id": warning_id,
            "category": request.category,
            "severity": request.severity,
            "message": request.message,
            "issued_by": str(current_user.id),
            "created_at": datetime.now(tz=UTC).isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "acknowledged": False,
        }
    )
    user.extra_data["warnings"] = warnings

    await db.commit()

    from uuid import UUID as UUID_type

    return UserWarningResponse(
        id=UUID_type(warning_id),
        user_id=user_id,
        category=request.category,
        severity=request.severity,
        message=request.message,
        acknowledged=False,
        created_at=datetime.now(tz=UTC),
        expires_at=expires_at,
    )


@router.post(
    "/users/{user_id}/ban",
    response_model=UserBanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ban user",
    description="Ban a user from the platform.",
    dependencies=[Depends(require_admin())],
)
async def ban_user(
    user_id: UUID,
    request: UserBanRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> UserBanResponse:
    """Ban a user from the platform."""
    # Verify user exists
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if already banned
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already banned",
        )

    # Calculate expiration
    expires_at = None
    if not request.is_permanent and request.duration_days:
        expires_at = datetime.now(tz=UTC) + timedelta(days=request.duration_days)

    # Ban user
    user.is_banned = True
    user.banned_at = datetime.now(tz=UTC)
    user.ban_reason = request.reason
    user.ban_expires_at = expires_at

    await db.commit()

    return UserBanResponse(
        id=user.id,  # Using user ID as ban ID (simplified)
        user_id=user_id,
        reason=request.reason,
        is_permanent=request.is_permanent,
        expires_at=expires_at,
        created_at=datetime.now(tz=UTC),
    )


@router.delete(
    "/users/{user_id}/ban",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unban user",
    description="Remove ban from a user.",
    dependencies=[Depends(require_admin())],
)
async def unban_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove ban from a user."""
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not banned",
        )

    user.is_banned = False
    user.banned_at = None
    user.ban_reason = None
    user.ban_expires_at = None

    await db.commit()


class PasswordResetResponse(BaseModel):
    """Response for admin-initiated password reset."""

    message: str
    email_sent: bool


@router.post(
    "/users/{user_id}/reset-password",
    response_model=PasswordResetResponse,
    summary="Reset user password",
    description="Send password reset email to user.",
    dependencies=[Depends(require_admin())],
)
async def admin_reset_password(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PasswordResetResponse:
    """Admin-initiated password reset for a user."""
    from app.core.config import get_settings
    from app.core.security import create_password_reset_token
    from app.services.email import get_email_service

    settings = get_settings()

    # Verify user exists
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate reset token
    reset_token = create_password_reset_token(user.email)

    # Build reset URL
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    # Send email
    email_service = get_email_service()
    email_sent = await email_service.send_password_reset_email(
        email=user.email,
        display_name=user.full_name or user.email.split("@")[0],
        reset_url=reset_url,
    )

    # Log password reset request to audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="user",
        resource_id=user.id,
        details={
            "target_user_email": user.email,
            "initiated_by": current_user.email,
            "email_sent": email_sent,
        },
    )
    await db.commit()

    return PasswordResetResponse(
        message=f"Password reset email sent to {user.email}"
        if email_sent
        else "Failed to send email",
        email_sent=email_sent,
    )


# Need uuid4 import
from uuid import uuid4

from app.models.design import Design
from app.models.job import Job
from app.models.project import Project
from app.models.template import Template

# =============================================================================
# Analytics Schemas
# =============================================================================


class AnalyticsOverviewResponse(BaseModel):
    """Platform analytics overview."""

    total_users: int
    active_users_daily: int
    active_users_weekly: int
    active_users_monthly: int
    new_signups_today: int
    new_signups_week: int
    total_projects: int
    total_designs: int
    total_generations_today: int
    total_generations_week: int
    total_storage_bytes: int
    pending_jobs: int
    failed_jobs_today: int


class UserAnalyticsResponse(BaseModel):
    """User analytics for a period."""

    period: str
    total_users: int
    new_users: int
    active_users: int
    churned_users: int
    users_by_tier: dict[str, int]


class GenerationAnalyticsResponse(BaseModel):
    """Generation analytics for a period."""

    period: str
    total_generations: int
    ai_generations: int
    template_generations: int
    import_count: int
    success_rate: float
    avg_generation_time_ms: int | None


class JobAnalyticsResponse(BaseModel):
    """Job queue analytics."""

    period: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    success_rate: float
    avg_processing_time_ms: int | None
    jobs_by_type: dict[str, int]


class StorageAnalyticsResponse(BaseModel):
    """Storage usage analytics."""

    total_storage_bytes: int
    used_storage_bytes: int
    storage_by_type: dict[str, int]
    largest_users: list[dict[str, Any]]


# =============================================================================
# User Management Schemas
# =============================================================================


class AdminUserResponse(BaseModel):
    """Admin view of a user."""

    id: UUID
    email: str
    display_name: str
    role: str
    status: str
    email_verified_at: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    project_count: int = 0
    design_count: int = 0
    subscription_tier: str | None = None


class AdminUserListResponse(BaseModel):
    """Paginated user list for admins."""

    users: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class AdminUserUpdateRequest(BaseModel):
    """Request to update a user."""

    display_name: str | None = None
    role: str | None = Field(None, pattern="^(user|moderator|admin)$")
    status: str | None = Field(None, pattern="^(active|suspended|pending_verification)$")


class SuspendUserRequest(BaseModel):
    """Request to suspend a user."""

    reason: str = Field(..., max_length=500)
    duration_days: int | None = Field(None, ge=1, le=365)


class ImpersonateResponse(BaseModel):
    """Response for user impersonation."""

    access_token: str
    user_id: UUID
    user_email: str
    expires_at: datetime
    audit_id: UUID


# =============================================================================
# Project/Design Admin Schemas
# =============================================================================


class AdminProjectResponse(BaseModel):
    """Admin view of a project."""

    id: UUID
    name: str
    description: str | None
    user_id: UUID
    user_email: str | None
    design_count: int
    status: str = "active"
    created_at: datetime
    updated_at: datetime | None


class SuspendProjectRequest(BaseModel):
    """Request to suspend a project."""

    reason: str = Field(..., min_length=1, max_length=500)


class AdminProjectListResponse(BaseModel):
    """Paginated project list."""

    projects: list[AdminProjectResponse]
    total: int
    page: int
    page_size: int


class AdminDesignResponse(BaseModel):
    """Admin view of a design."""

    id: UUID
    name: str
    description: str | None
    source_type: str
    status: str
    project_id: UUID
    project_name: str | None = None
    user_id: UUID | None = None
    user_email: str | None = None
    template_id: UUID | None
    is_public: bool
    created_at: datetime
    updated_at: datetime | None


class AdminDesignListResponse(BaseModel):
    """Paginated design list."""

    designs: list[AdminDesignResponse]
    total: int
    page: int
    page_size: int


class TransferOwnershipRequest(BaseModel):
    """Request to transfer ownership."""

    new_owner_id: UUID
    reason: str | None = None


class VisibilityChangeRequest(BaseModel):
    """Request to change design visibility."""

    is_public: bool


# =============================================================================
# Template Admin Schemas
# =============================================================================


class AdminTemplateResponse(BaseModel):
    """Admin view of a template."""

    id: UUID
    name: str
    slug: str
    description: str | None
    category: str
    is_active: bool
    is_featured: bool
    min_tier: str
    use_count: int
    created_at: datetime
    updated_at: datetime | None
    preview_url: str | None = None


class AdminTemplateListResponse(BaseModel):
    """Paginated template list."""

    templates: list[AdminTemplateResponse]
    total: int
    page: int
    page_size: int


class AdminTemplateCreateRequest(BaseModel):
    """Request to create a template."""

    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100)
    description: str | None = None
    category: str = Field(..., max_length=50)
    subcategory: str | None = None
    parameters: dict[str, Any]
    default_values: dict[str, Any]
    cadquery_script: str
    min_tier: str = "free"
    is_active: bool = True


class AdminTemplateUpdateRequest(BaseModel):
    """Request to update a template."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    parameters: dict[str, Any] | None = None
    default_values: dict[str, Any] | None = None
    cadquery_script: str | None = None
    min_tier: str | None = None
    is_active: bool | None = None
    is_featured: bool | None = None


# =============================================================================
# Job Admin Schemas
# =============================================================================


class AdminJobResponse(BaseModel):
    """Admin view of a job."""

    id: UUID
    job_type: str
    status: str
    user_id: UUID
    user_email: str | None = None
    design_id: UUID | None
    progress: int
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    processing_time_ms: int | None = None


class AdminJobListResponse(BaseModel):
    """Paginated job list."""

    jobs: list[AdminJobResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Analytics Endpoints
# =============================================================================


@router.get(
    "/analytics/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get analytics overview",
    description="Get platform-wide analytics overview (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_analytics_overview(
    organization_id: Annotated[UUID | None, Query()] = None,
    plan: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """Get platform analytics overview.

    Args:
        organization_id: Filter by organization
        plan: Filter by subscription plan (free, starter, pro, enterprise)
    """
    now = datetime.now(tz=UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Build user filter conditions
    user_conditions = [User.deleted_at.is_(None)]

    if organization_id:
        # Get users in organization
        org_user_ids = select(OrganizationMember.user_id).where(
            OrganizationMember.organization_id == organization_id
        )
        user_conditions.append(User.id.in_(org_user_ids))

    if plan:
        # Get users with specific plan
        plan_user_ids = select(Subscription.user_id).where(
            Subscription.tier == plan,
            Subscription.status == "active",
        )
        user_conditions.append(User.id.in_(plan_user_ids))

    # User counts
    total_users = (await db.execute(select(func.count()).where(*user_conditions))).scalar_one()

    # Active users (by last_login_at) - with filters
    active_daily = (
        await db.execute(
            select(func.count()).where(
                User.last_login_at >= today_start,
                *user_conditions,
            )
        )
    ).scalar_one()

    active_weekly = (
        await db.execute(
            select(func.count()).where(
                User.last_login_at >= week_ago,
                *user_conditions,
            )
        )
    ).scalar_one()

    active_monthly = (
        await db.execute(
            select(func.count()).where(
                User.last_login_at >= month_ago,
                *user_conditions,
            )
        )
    ).scalar_one()

    # New signups - with filters
    new_today = (
        await db.execute(
            select(func.count()).where(
                User.created_at >= today_start,
                *user_conditions,
            )
        )
    ).scalar_one()

    new_week = (
        await db.execute(
            select(func.count()).where(
                User.created_at >= week_ago,
                *user_conditions,
            )
        )
    ).scalar_one()

    # Build project/design filters based on user filters
    filtered_user_ids = None
    if organization_id or plan:
        filtered_user_ids = select(User.id).where(*user_conditions)

    # Projects and designs
    project_conditions = [Project.deleted_at.is_(None)]
    design_conditions = [Design.deleted_at.is_(None)]

    if filtered_user_ids is not None:
        project_conditions.append(Project.user_id.in_(filtered_user_ids))
        design_conditions.append(Design.user_id.in_(filtered_user_ids))

    total_projects = (
        await db.execute(select(func.count()).where(*project_conditions))
    ).scalar_one()

    total_designs = (await db.execute(select(func.count()).where(*design_conditions))).scalar_one()

    # Generations (designs created)
    generations_today = (
        await db.execute(
            select(func.count()).where(
                Design.created_at >= today_start,
                *design_conditions,
            )
        )
    ).scalar_one()

    generations_week = (
        await db.execute(
            select(func.count()).where(
                Design.created_at >= week_ago,
                *design_conditions,
            )
        )
    ).scalar_one()

    # Jobs
    pending_jobs = (
        await db.execute(
            select(func.count()).where(
                Job.status.in_(["pending", "processing"]),
            )
        )
    ).scalar_one()

    failed_today = (
        await db.execute(
            select(func.count()).where(
                Job.status == "failed",
                Job.created_at >= today_start,
            )
        )
    ).scalar_one()

    return AnalyticsOverviewResponse(
        total_users=total_users,
        active_users_daily=active_daily,
        active_users_weekly=active_weekly,
        active_users_monthly=active_monthly,
        new_signups_today=new_today,
        new_signups_week=new_week,
        total_projects=total_projects,
        total_designs=total_designs,
        total_generations_today=generations_today,
        total_generations_week=generations_week,
        total_storage_bytes=0,  # Would calculate from files table
        pending_jobs=pending_jobs,
        failed_jobs_today=failed_today,
    )


@router.get(
    "/analytics/users",
    response_model=UserAnalyticsResponse,
    summary="Get user analytics",
    description="Get user analytics for a period.",
    dependencies=[Depends(require_admin())],
)
async def get_user_analytics(
    period: Annotated[str, Query(pattern="^(7d|30d|90d|365d)$")] = "30d",
    db: AsyncSession = Depends(get_db),
) -> UserAnalyticsResponse:
    """Get user analytics for a period."""
    days = int(period.replace("d", ""))
    start_date = datetime.now(tz=UTC) - timedelta(days=days)

    total_users = (
        await db.execute(select(func.count()).where(User.deleted_at.is_(None)))
    ).scalar_one()

    new_users = (
        await db.execute(
            select(func.count()).where(
                User.created_at >= start_date,
                User.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    active_users = (
        await db.execute(
            select(func.count()).where(
                User.last_login_at >= start_date,
                User.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Churned = not logged in during period but were active before
    churned_users = 0  # Simplified - would need more complex query

    return UserAnalyticsResponse(
        period=period,
        total_users=total_users,
        new_users=new_users,
        active_users=active_users,
        churned_users=churned_users,
        users_by_tier={"free": total_users},  # Simplified
    )


@router.get(
    "/analytics/generations",
    response_model=GenerationAnalyticsResponse,
    summary="Get generation analytics",
    description="Get design generation analytics for a period.",
    dependencies=[Depends(require_admin())],
)
async def get_generation_analytics(
    period: Annotated[str, Query(pattern="^(7d|30d|90d|365d)$")] = "30d",
    db: AsyncSession = Depends(get_db),
) -> GenerationAnalyticsResponse:
    """Get generation analytics for a period."""
    days = int(period.replace("d", ""))
    start_date = datetime.now(tz=UTC) - timedelta(days=days)

    total = (
        await db.execute(
            select(func.count()).where(
                Design.created_at >= start_date,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    ai_generated = (
        await db.execute(
            select(func.count()).where(
                Design.created_at >= start_date,
                Design.source_type == "ai_generated",
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    template_generated = (
        await db.execute(
            select(func.count()).where(
                Design.created_at >= start_date,
                Design.source_type == "template",
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    imported = (
        await db.execute(
            select(func.count()).where(
                Design.created_at >= start_date,
                Design.source_type == "imported",
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Success rate based on status
    successful = (
        await db.execute(
            select(func.count()).where(
                Design.created_at >= start_date,
                Design.status == "ready",
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    success_rate = (successful / total * 100) if total > 0 else 0.0

    return GenerationAnalyticsResponse(
        period=period,
        total_generations=total,
        ai_generations=ai_generated,
        template_generations=template_generated,
        import_count=imported,
        success_rate=round(success_rate, 2),
        avg_generation_time_ms=None,  # Would calculate from jobs
    )


@router.get(
    "/analytics/jobs",
    response_model=JobAnalyticsResponse,
    summary="Get job analytics",
    description="Get background job analytics for a period.",
    dependencies=[Depends(require_admin())],
)
async def get_job_analytics(
    period: Annotated[str, Query(pattern="^(7d|30d|90d|365d)$")] = "30d",
    db: AsyncSession = Depends(get_db),
) -> JobAnalyticsResponse:
    """Get job queue analytics."""
    days = int(period.replace("d", ""))
    start_date = datetime.now(tz=UTC) - timedelta(days=days)

    total = (
        await db.execute(select(func.count()).where(Job.created_at >= start_date))
    ).scalar_one()

    completed = (
        await db.execute(
            select(func.count()).where(
                Job.created_at >= start_date,
                Job.status == "completed",
            )
        )
    ).scalar_one()

    failed = (
        await db.execute(
            select(func.count()).where(
                Job.created_at >= start_date,
                Job.status == "failed",
            )
        )
    ).scalar_one()

    pending = (
        await db.execute(
            select(func.count()).where(
                Job.status.in_(["pending", "processing"]),
            )
        )
    ).scalar_one()

    success_rate = (completed / total * 100) if total > 0 else 0.0

    return JobAnalyticsResponse(
        period=period,
        total_jobs=total,
        completed_jobs=completed,
        failed_jobs=failed,
        pending_jobs=pending,
        success_rate=round(success_rate, 2),
        avg_processing_time_ms=None,  # Would calculate from started/completed times
        jobs_by_type={},  # Would group by job_type
    )


@router.get(
    "/analytics/storage",
    response_model=StorageAnalyticsResponse,
    summary="Get storage analytics",
    description="Get storage usage analytics.",
    dependencies=[Depends(require_admin())],
)
async def get_storage_analytics(
    _db: AsyncSession = Depends(get_db),
) -> StorageAnalyticsResponse:
    """Get storage usage analytics."""
    # Simplified - would calculate from files table
    return StorageAnalyticsResponse(
        total_storage_bytes=0,
        used_storage_bytes=0,
        storage_by_type={},
        largest_users=[],
    )


class TimeSeriesDataPoint(BaseModel):
    """A single data point in a time series."""

    date: str
    value: int


class TimeSeriesAnalyticsResponse(BaseModel):
    """Time-series analytics data for charts."""

    new_users: list[TimeSeriesDataPoint]
    active_users: list[TimeSeriesDataPoint]
    new_projects: list[TimeSeriesDataPoint]
    new_designs: list[TimeSeriesDataPoint]
    jobs_completed: list[TimeSeriesDataPoint]


@router.get(
    "/analytics/time-series",
    response_model=TimeSeriesAnalyticsResponse,
    summary="Get time-series analytics",
    description="Get time-series analytics data for charts.",
    dependencies=[Depends(require_admin())],
)
async def get_time_series_analytics(
    days: Annotated[int, Query(ge=7, le=365)] = 30,
    db: AsyncSession = Depends(get_db),
) -> TimeSeriesAnalyticsResponse:
    """Get time-series analytics for charting."""
    now = datetime.now(tz=UTC)
    start_date = now - timedelta(days=days)

    # Generate date range
    date_range = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        date_range.append(date.strftime("%Y-%m-%d"))

    # Initialize data with zeros
    new_users_data = dict.fromkeys(date_range, 0)
    active_users_data = dict.fromkeys(date_range, 0)
    new_projects_data = dict.fromkeys(date_range, 0)
    new_designs_data = dict.fromkeys(date_range, 0)
    jobs_completed_data = dict.fromkeys(date_range, 0)

    # Query new users per day
    new_users_query = (
        select(
            func.date(User.created_at).label("date"),
            func.count().label("count"),
        )
        .where(
            User.created_at >= start_date,
            User.deleted_at.is_(None),
        )
        .group_by(func.date(User.created_at))
    )
    result = await db.execute(new_users_query)
    for row in result.all():
        date_str = row.date.strftime("%Y-%m-%d") if hasattr(row.date, "strftime") else str(row.date)
        if date_str in new_users_data:
            new_users_data[date_str] = row.count

    # Query active users per day (by last_login_at)
    active_users_query = (
        select(
            func.date(User.last_login_at).label("date"),
            func.count(func.distinct(User.id)).label("count"),
        )
        .where(
            User.last_login_at >= start_date,
            User.deleted_at.is_(None),
        )
        .group_by(func.date(User.last_login_at))
    )
    result = await db.execute(active_users_query)
    for row in result.all():
        date_str = row.date.strftime("%Y-%m-%d") if hasattr(row.date, "strftime") else str(row.date)
        if date_str in active_users_data:
            active_users_data[date_str] = row.count

    # Query new projects per day
    new_projects_query = (
        select(
            func.date(Project.created_at).label("date"),
            func.count().label("count"),
        )
        .where(
            Project.created_at >= start_date,
            Project.deleted_at.is_(None),
        )
        .group_by(func.date(Project.created_at))
    )
    result = await db.execute(new_projects_query)
    for row in result.all():
        date_str = row.date.strftime("%Y-%m-%d") if hasattr(row.date, "strftime") else str(row.date)
        if date_str in new_projects_data:
            new_projects_data[date_str] = row.count

    # Query new designs per day
    new_designs_query = (
        select(
            func.date(Design.created_at).label("date"),
            func.count().label("count"),
        )
        .where(
            Design.created_at >= start_date,
            Design.deleted_at.is_(None),
        )
        .group_by(func.date(Design.created_at))
    )
    result = await db.execute(new_designs_query)
    for row in result.all():
        date_str = row.date.strftime("%Y-%m-%d") if hasattr(row.date, "strftime") else str(row.date)
        if date_str in new_designs_data:
            new_designs_data[date_str] = row.count

    # Convert to response format
    return TimeSeriesAnalyticsResponse(
        new_users=[TimeSeriesDataPoint(date=d, value=v) for d, v in new_users_data.items()],
        active_users=[TimeSeriesDataPoint(date=d, value=v) for d, v in active_users_data.items()],
        new_projects=[TimeSeriesDataPoint(date=d, value=v) for d, v in new_projects_data.items()],
        new_designs=[TimeSeriesDataPoint(date=d, value=v) for d, v in new_designs_data.items()],
        jobs_completed=[
            TimeSeriesDataPoint(date=d, value=v) for d, v in jobs_completed_data.items()
        ],
    )


# =============================================================================
# User Management Endpoints
# =============================================================================


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List all users",
    description="List all users with filters (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
    role: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    db: AsyncSession = Depends(get_db),
) -> AdminUserListResponse:
    """List all users with pagination and filters."""
    query = select(User).where(User.deleted_at.is_(None))

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_pattern)) | (User.display_name.ilike(search_pattern))
        )

    if role:
        query = query.where(User.role == role)

    if status_filter:
        query = query.where(User.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    return AdminUserListResponse(
        users=[
            AdminUserResponse(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                role=user.role,
                status=user.status,
                email_verified_at=user.email_verified_at,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
            )
            for user in users
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Get user details",
    description="Get complete user details (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_user_details(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Get complete user details."""
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Count projects and designs
    project_count = (
        await db.execute(
            select(func.count()).where(
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    design_count = (
        await db.execute(
            select(func.count())
            .select_from(Design)
            .join(Project, Design.project_id == Project.id)
            .where(
                Project.user_id == user_id,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        email_verified_at=user.email_verified_at,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        project_count=project_count,
        design_count=design_count,
    )


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Update user",
    description="Update user profile (admin only).",
    dependencies=[Depends(require_admin())],
)
async def update_user(
    user_id: UUID,
    request: AdminUserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AdminUserResponse:
    """Update user profile."""
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-demotion
    if user_id == current_user.id and request.role and request.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote your own admin role",
        )

    # Track original role for audit
    old_role = user.role

    # Apply updates
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.role is not None:
        user.role = request.role
    if request.status is not None:
        user.status = request.status

    await db.commit()
    await db.refresh(user)

    # Log role change to audit log
    if request.role is not None and request.role != old_role:
        security_audit = SecurityAuditService(db)
        await security_audit.log_event(
            event_type=SecurityEventType.ROLE_CHANGED,
            user_id=current_user.id,
            resource_type="user",
            resource_id=user.id,
            details={
                "target_user_email": user.email,
                "old_role": old_role,
                "new_role": request.role,
                "changed_by": current_user.email,
            },
        )
        await db.commit()

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        email_verified_at=user.email_verified_at,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.post(
    "/users/{user_id}/suspend",
    response_model=AdminUserResponse,
    summary="Suspend user",
    description="Suspend a user account (admin only).",
    dependencies=[Depends(require_admin())],
)
async def suspend_user(
    user_id: UUID,
    request: SuspendUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AdminUserResponse:
    """Suspend a user account."""
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend your own account",
        )

    if user.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already suspended",
        )

    user.status = "suspended"
    user.extra_data["suspension_reason"] = request.reason
    user.extra_data["suspended_at"] = datetime.now(tz=UTC).isoformat()
    user.extra_data["suspended_by"] = str(current_user.id)
    if request.duration_days:
        user.extra_data["suspension_expires"] = (
            datetime.now(tz=UTC) + timedelta(days=request.duration_days)
        ).isoformat()

    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        email_verified_at=user.email_verified_at,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.post(
    "/users/{user_id}/unsuspend",
    response_model=AdminUserResponse,
    summary="Unsuspend user",
    description="Remove suspension from a user account (admin only).",
    dependencies=[Depends(require_admin())],
)
async def unsuspend_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    """Remove suspension from a user account."""
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.status != "suspended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not suspended",
        )

    user.status = "active"
    user.extra_data.pop("suspension_reason", None)
    user.extra_data.pop("suspended_at", None)
    user.extra_data.pop("suspended_by", None)
    user.extra_data.pop("suspension_expires", None)

    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        email_verified_at=user.email_verified_at,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Soft-delete a user account (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-delete a user account."""
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user.deleted_at = datetime.now(tz=UTC)
    await db.commit()


@router.post(
    "/users/{user_id}/impersonate",
    response_model=ImpersonateResponse,
    summary="Impersonate user",
    description="Create temporary session as a user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def impersonate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImpersonateResponse:
    """Create temporary session as a user for debugging."""
    from app.core.security import create_access_token

    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot impersonate admin users",
        )

    # Create short-lived token (1 hour)
    expires_at = datetime.now(tz=UTC) + timedelta(hours=1)
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        expires_delta=timedelta(hours=1),
        additional_claims={"impersonated_by": str(current_user.id)},
    )

    # Store audit record
    audit_id = uuid4()
    user.extra_data.setdefault("impersonation_log", []).append(
        {
            "id": str(audit_id),
            "by": str(current_user.id),
            "at": datetime.now(tz=UTC).isoformat(),
        }
    )
    await db.commit()

    return ImpersonateResponse(
        access_token=token,
        user_id=user.id,
        user_email=user.email,
        expires_at=expires_at,
        audit_id=audit_id,
    )


# =============================================================================
# Project Management Endpoints
# =============================================================================


@router.get(
    "/projects",
    response_model=AdminProjectListResponse,
    summary="List all projects",
    description="List all projects (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_projects(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    db: AsyncSession = Depends(get_db),
) -> AdminProjectListResponse:
    """List all projects with pagination."""
    query = select(Project).options(selectinload(Project.user)).where(Project.deleted_at.is_(None))

    if user_id:
        query = query.where(Project.user_id == user_id)

    if status_filter:
        query = query.where(Project.status == status_filter)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(Project.name.ilike(search_pattern))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    projects = result.scalars().all()

    return AdminProjectListResponse(
        projects=[
            AdminProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                user_id=project.user_id,
                user_email=project.user.email if project.user else None,
                design_count=0,  # Would count from relationship
                status=getattr(project, "status", "active"),
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            for project in projects
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/projects/{project_id}",
    response_model=AdminProjectResponse,
    summary="Get project details",
    description="Get project details (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_project_details(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminProjectResponse:
    """Get project details."""
    query = (
        select(Project)
        .options(selectinload(Project.user))
        .where(Project.id == project_id, Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Count designs
    design_count = (
        await db.execute(
            select(func.count()).where(
                Design.project_id == project_id,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    return AdminProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        user_id=project.user_id,
        user_email=project.user.email if project.user else None,
        design_count=design_count,
        status=getattr(project, "status", "active"),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Soft-delete a project (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a project."""
    query = select(Project).where(Project.id == project_id, Project.deleted_at.is_(None))
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    project.deleted_at = datetime.now(tz=UTC)
    await db.commit()


@router.post(
    "/projects/{project_id}/transfer",
    response_model=AdminProjectResponse,
    summary="Transfer project",
    description="Transfer project ownership (admin only).",
    dependencies=[Depends(require_admin())],
)
async def transfer_project(
    project_id: UUID,
    request: TransferOwnershipRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminProjectResponse:
    """Transfer project ownership to another user."""
    # Get project
    query = (
        select(Project)
        .options(selectinload(Project.user))
        .where(Project.id == project_id, Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Verify new owner exists
    new_owner_query = select(User).where(
        User.id == request.new_owner_id,
        User.deleted_at.is_(None),
    )
    new_owner_result = await db.execute(new_owner_query)
    new_owner = new_owner_result.scalar_one_or_none()

    if not new_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New owner not found",
        )

    project.user_id = request.new_owner_id
    await db.commit()

    # Refresh to get new owner
    await db.refresh(project)

    return AdminProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        user_id=project.user_id,
        user_email=new_owner.email,
        design_count=0,
        status=getattr(project, "status", "active"),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post(
    "/projects/{project_id}/suspend",
    response_model=AdminProjectResponse,
    summary="Suspend project",
    description="Suspend a project (admin only).",
    dependencies=[Depends(require_admin())],
)
async def suspend_project(
    project_id: UUID,
    _request: SuspendProjectRequest,  # TODO: Use request.reason for audit log
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> AdminProjectResponse:
    """Suspend a project."""
    query = (
        select(Project)
        .options(selectinload(Project.user))
        .where(Project.id == project_id, Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if getattr(project, "status", "active") == "suspended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is already suspended",
        )

    project.status = "suspended"
    await db.commit()
    await db.refresh(project)

    # Count designs
    design_count = (
        await db.execute(
            select(func.count()).where(
                Design.project_id == project_id,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    return AdminProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        user_id=project.user_id,
        user_email=project.user.email if project.user else None,
        design_count=design_count,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post(
    "/projects/{project_id}/unsuspend",
    response_model=AdminProjectResponse,
    summary="Unsuspend project",
    description="Unsuspend a project (admin only).",
    dependencies=[Depends(require_admin())],
)
async def unsuspend_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminProjectResponse:
    """Unsuspend a project."""
    query = (
        select(Project)
        .options(selectinload(Project.user))
        .where(Project.id == project_id, Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if getattr(project, "status", "active") != "suspended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not suspended",
        )

    project.status = "active"
    await db.commit()
    await db.refresh(project)

    # Count designs
    design_count = (
        await db.execute(
            select(func.count()).where(
                Design.project_id == project_id,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    return AdminProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        user_id=project.user_id,
        user_email=project.user.email if project.user else None,
        design_count=design_count,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


# =============================================================================
# Design Management Endpoints
# =============================================================================


@router.get(
    "/designs",
    response_model=AdminDesignListResponse,
    summary="List all designs",
    description="List all designs (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_designs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    source_type: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    db: AsyncSession = Depends(get_db),
) -> AdminDesignListResponse:
    """List all designs with pagination."""
    query = (
        select(Design)
        .join(Project, Design.project_id == Project.id)
        .options(selectinload(Design.project).selectinload(Project.user))
        .where(Design.deleted_at.is_(None))
    )

    if source_type:
        query = query.where(Design.source_type == source_type)

    if status_filter:
        query = query.where(Design.status == status_filter)

    if user_id:
        query = query.where(Project.user_id == user_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(Design.name.ilike(search_pattern))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Design.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    designs = result.scalars().all()

    return AdminDesignListResponse(
        designs=[
            AdminDesignResponse(
                id=design.id,
                name=design.name,
                description=design.description,
                source_type=design.source_type,
                status=design.status,
                project_id=design.project_id,
                project_name=design.project.name if design.project else None,
                user_id=design.project.user_id if design.project else None,
                user_email=design.project.user.email
                if design.project and design.project.user
                else None,
                template_id=design.template_id,
                is_public=design.is_public,
                created_at=design.created_at,
                updated_at=design.updated_at,
            )
            for design in designs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/designs/{design_id}",
    response_model=AdminDesignResponse,
    summary="Get design details",
    description="Get design details (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_design_details(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminDesignResponse:
    """Get design details."""
    query = (
        select(Design)
        .options(selectinload(Design.project).selectinload(Project.user))
        .where(Design.id == design_id, Design.deleted_at.is_(None))
    )
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    return AdminDesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        source_type=design.source_type,
        status=design.status,
        project_id=design.project_id,
        project_name=design.project.name if design.project else None,
        user_id=design.project.user_id if design.project else None,
        user_email=design.project.user.email if design.project and design.project.user else None,
        template_id=design.template_id,
        is_public=design.is_public,
        created_at=design.created_at,
        updated_at=design.updated_at,
    )


@router.delete(
    "/designs/{design_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete design",
    description="Soft-delete a design (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_design(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a design."""
    query = select(Design).where(Design.id == design_id, Design.deleted_at.is_(None))
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    design.deleted_at = datetime.now(tz=UTC)
    await db.commit()


@router.post(
    "/designs/{design_id}/restore",
    response_model=AdminDesignResponse,
    summary="Restore design",
    description="Restore a soft-deleted design (admin only).",
    dependencies=[Depends(require_admin())],
)
async def restore_design(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminDesignResponse:
    """Restore a soft-deleted design."""
    query = (
        select(Design)
        .options(selectinload(Design.project).selectinload(Project.user))
        .where(Design.id == design_id, Design.deleted_at.isnot(None))
    )
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted design not found",
        )

    design.deleted_at = None
    await db.commit()
    await db.refresh(design)

    return AdminDesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        source_type=design.source_type,
        status=design.status,
        project_id=design.project_id,
        project_name=design.project.name if design.project else None,
        user_id=design.project.user_id if design.project else None,
        user_email=design.project.user.email if design.project and design.project.user else None,
        template_id=design.template_id,
        is_public=design.is_public,
        created_at=design.created_at,
        updated_at=design.updated_at,
    )


@router.patch(
    "/designs/{design_id}/visibility",
    response_model=AdminDesignResponse,
    summary="Change design visibility",
    description="Change design visibility (admin only).",
    dependencies=[Depends(require_admin())],
)
async def change_design_visibility(
    design_id: UUID,
    request: VisibilityChangeRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminDesignResponse:
    """Change design visibility."""
    query = (
        select(Design)
        .options(selectinload(Design.project).selectinload(Project.user))
        .where(Design.id == design_id, Design.deleted_at.is_(None))
    )
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    design.is_public = request.is_public
    await db.commit()
    await db.refresh(design)

    return AdminDesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        source_type=design.source_type,
        status=design.status,
        project_id=design.project_id,
        project_name=design.project.name if design.project else None,
        user_id=design.project.user_id if design.project else None,
        user_email=design.project.user.email if design.project and design.project.user else None,
        template_id=design.template_id,
        is_public=design.is_public,
        created_at=design.created_at,
        updated_at=design.updated_at,
    )


# =============================================================================
# Template Management Endpoints
# =============================================================================


@router.get(
    "/templates",
    response_model=AdminTemplateListResponse,
    summary="List all templates",
    description="List all templates (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_templates(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateListResponse:
    """List all templates with pagination."""
    query = select(Template)

    if category:
        query = query.where(Template.category == category)

    if is_active is not None:
        query = query.where(Template.is_active == is_active)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Template.name.ilike(search_pattern)) | (Template.slug.ilike(search_pattern))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Template.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    templates = result.scalars().all()

    return AdminTemplateListResponse(
        templates=[
            AdminTemplateResponse(
                id=template.id,
                name=template.name,
                slug=template.slug,
                description=template.description,
                category=template.category,
                is_active=template.is_active,
                is_featured=template.is_featured,
                min_tier=template.min_tier,
                use_count=template.use_count,
                created_at=template.created_at,
                updated_at=template.updated_at,
            )
            for template in templates
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/templates/{template_id}",
    response_model=AdminTemplateResponse,
    summary="Get template details",
    description="Get template details (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_template_details(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateResponse:
    """Get template details."""
    query = select(Template).where(Template.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return AdminTemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        is_featured=template.is_featured,
        min_tier=template.min_tier,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post(
    "/templates",
    response_model=AdminTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create template",
    description="Create a new template (admin only).",
    dependencies=[Depends(require_admin())],
)
async def create_template(
    request: AdminTemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateResponse:
    """Create a new template."""
    # Check slug uniqueness
    existing = await db.execute(select(Template).where(Template.slug == request.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this slug already exists",
        )

    template = Template(
        name=request.name,
        slug=request.slug,
        description=request.description,
        category=request.category,
        subcategory=request.subcategory,
        parameters=request.parameters,
        default_values=request.default_values,
        cadquery_script=request.cadquery_script,
        min_tier=request.min_tier,
        is_active=request.is_active,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return AdminTemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        is_featured=template.is_featured,
        min_tier=template.min_tier,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.patch(
    "/templates/{template_id}",
    response_model=AdminTemplateResponse,
    summary="Update template",
    description="Update a template (admin only).",
    dependencies=[Depends(require_admin())],
)
async def update_template(
    template_id: UUID,
    request: AdminTemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateResponse:
    """Update a template."""
    query = select(Template).where(Template.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Apply updates
    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.category is not None:
        template.category = request.category
    if request.subcategory is not None:
        template.subcategory = request.subcategory
    if request.parameters is not None:
        template.parameters = request.parameters
    if request.default_values is not None:
        template.default_values = request.default_values
    if request.cadquery_script is not None:
        template.cadquery_script = request.cadquery_script
    if request.min_tier is not None:
        template.min_tier = request.min_tier
    if request.is_active is not None:
        template.is_active = request.is_active
    if request.is_featured is not None:
        template.is_featured = request.is_featured

    await db.commit()
    await db.refresh(template)

    return AdminTemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        is_featured=template.is_featured,
        min_tier=template.min_tier,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete template",
    description="Delete a template (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a template."""
    query = select(Template).where(Template.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    await db.delete(template)
    await db.commit()


@router.post(
    "/templates/{template_id}/enable",
    response_model=AdminTemplateResponse,
    summary="Enable template",
    description="Enable a template (admin only).",
    dependencies=[Depends(require_admin())],
)
async def enable_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateResponse:
    """Enable a template."""
    query = select(Template).where(Template.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    template.is_active = True
    await db.commit()
    await db.refresh(template)

    return AdminTemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        is_featured=template.is_featured,
        min_tier=template.min_tier,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post(
    "/templates/{template_id}/disable",
    response_model=AdminTemplateResponse,
    summary="Disable template",
    description="Disable a template (admin only).",
    dependencies=[Depends(require_admin())],
)
async def disable_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateResponse:
    """Disable a template."""
    query = select(Template).where(Template.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    template.is_active = False
    await db.commit()
    await db.refresh(template)

    return AdminTemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        is_featured=template.is_featured,
        min_tier=template.min_tier,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post(
    "/templates/{template_id}/feature",
    response_model=AdminTemplateResponse,
    summary="Feature template",
    description="Mark template as featured (admin only).",
    dependencies=[Depends(require_admin())],
)
async def feature_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateResponse:
    """Mark a template as featured."""
    query = select(Template).where(Template.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    template.is_featured = True
    await db.commit()
    await db.refresh(template)

    return AdminTemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        is_featured=template.is_featured,
        min_tier=template.min_tier,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post(
    "/templates/{template_id}/unfeature",
    response_model=AdminTemplateResponse,
    summary="Unfeature template",
    description="Remove featured status from template (admin only).",
    dependencies=[Depends(require_admin())],
)
async def unfeature_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateResponse:
    """Remove featured status from a template."""
    query = select(Template).where(Template.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    template.is_featured = False
    await db.commit()
    await db.refresh(template)

    return AdminTemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        is_featured=template.is_featured,
        min_tier=template.min_tier,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post(
    "/templates/{template_id}/clone",
    response_model=AdminTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone template",
    description="Clone a template (admin only).",
    dependencies=[Depends(require_admin())],
)
async def clone_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateResponse:
    """Clone a template."""
    query = select(Template).where(Template.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Create clone with unique slug
    new_slug = f"{template.slug}-copy-{uuid4().hex[:8]}"

    clone = Template(
        name=f"{template.name} (Copy)",
        slug=new_slug,
        description=template.description,
        category=template.category,
        subcategory=template.subcategory,
        parameters=template.parameters,
        default_values=template.default_values,
        cadquery_script=template.cadquery_script,
        min_tier=template.min_tier,
        is_active=False,  # Clone starts inactive
        is_featured=False,
    )

    db.add(clone)
    await db.commit()
    await db.refresh(clone)

    return AdminTemplateResponse(
        id=clone.id,
        name=clone.name,
        slug=clone.slug,
        description=clone.description,
        category=clone.category,
        is_active=clone.is_active,
        is_featured=clone.is_featured,
        min_tier=clone.min_tier,
        use_count=clone.use_count,
        created_at=clone.created_at,
        updated_at=clone.updated_at,
    )


@router.post(
    "/templates/{template_id}/preview-image",
    response_model=AdminTemplateResponse,
    summary="Upload template preview image",
    description="Upload a preview image for a template (admin only).",
    dependencies=[Depends(require_admin())],
)
async def upload_template_preview_image(
    template_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> AdminTemplateResponse:
    """Upload preview image for a template."""
    from pathlib import Path

    import aiofiles

    from app.core.config import get_settings

    settings = get_settings()

    # Validate file type
    allowed_types = {"image/png", "image/jpeg", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}",
        )

    # Validate file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB.",
        )

    # Get template
    query = select(Template).where(Template.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Save file
    file_ext = file.filename.split(".")[-1] if file.filename else "png"
    filename = f"template-{template_id}.{file_ext}"
    upload_dir = Path(settings.UPLOAD_DIR) / "templates"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    async with aiofiles.open(str(file_path), "wb") as f:
        await f.write(content)

    # Update template with preview URL
    template.preview_url = f"/uploads/templates/{filename}"
    await db.commit()
    await db.refresh(template)

    return AdminTemplateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        description=template.description,
        category=template.category,
        is_active=template.is_active,
        is_featured=template.is_featured,
        min_tier=template.min_tier,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
        preview_url=template.preview_url,
    )


# =============================================================================
# Job Management Endpoints
# =============================================================================


@router.get(
    "/jobs",
    response_model=AdminJobListResponse,
    summary="List all jobs",
    description="List all background jobs (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_jobs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    job_type: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> AdminJobListResponse:
    """List all jobs with pagination."""
    query = select(Job).options(selectinload(Job.user))

    if job_type:
        query = query.where(Job.job_type == job_type)

    if status_filter:
        query = query.where(Job.status == status_filter)

    if user_id:
        query = query.where(Job.user_id == user_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Job.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return AdminJobListResponse(
        jobs=[
            AdminJobResponse(
                id=job.id,
                job_type=job.job_type,
                status=job.status,
                user_id=job.user_id,
                user_email=job.user.email if job.user else None,
                design_id=job.design_id,
                progress=job.progress,
                error_message=job.error_message,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
            for job in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=AdminJobResponse,
    summary="Get job details",
    description="Get job details (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_job_details(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Get job details."""
    query = select(Job).options(selectinload(Job.user)).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return AdminJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        user_id=job.user_id,
        user_email=job.user.email if job.user else None,
        design_id=job.design_id,
        progress=job.progress,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=AdminJobResponse,
    summary="Cancel job",
    description="Cancel a pending or running job (admin only).",
    dependencies=[Depends(require_admin())],
)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Cancel a job."""
    query = select(Job).options(selectinload(Job.user)).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status not in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}",
        )

    job.status = "cancelled"
    job.completed_at = datetime.now(tz=UTC)
    await db.commit()
    await db.refresh(job)

    return AdminJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        user_id=job.user_id,
        user_email=job.user.email if job.user else None,
        design_id=job.design_id,
        progress=job.progress,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=AdminJobResponse,
    summary="Retry failed job",
    description="Retry a failed job (admin only).",
    dependencies=[Depends(require_admin())],
)
async def retry_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Retry a failed job."""
    query = select(Job).options(selectinload(Job.user)).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed jobs can be retried",
        )

    # Reset job for retry
    job.status = "pending"
    job.progress = 0
    job.error = {}
    job.started_at = None
    job.completed_at = None
    job.retry_count = (job.retry_count or 0) + 1

    await db.commit()
    await db.refresh(job)

    return AdminJobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        user_id=job.user_id,
        user_email=job.user.email if job.user else None,
        design_id=job.design_id,
        progress=job.progress,
        error_message=None,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


# =============================================================================
# Subscription Management Schemas
# =============================================================================


class AdminSubscriptionResponse(BaseModel):
    """Admin view of a subscription."""

    id: UUID
    user_id: UUID
    user_email: str | None = None
    tier_slug: str
    tier_name: str
    status: str
    stripe_subscription_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Paginated subscription list."""

    items: list[AdminSubscriptionResponse]
    total: int
    page: int
    page_size: int


class ChangeTierRequest(BaseModel):
    """Request to change a user's tier."""

    tier_slug: str = Field(..., description="New tier slug")
    reason: str | None = Field(None, max_length=500)


class ExtendSubscriptionRequest(BaseModel):
    """Request to extend a subscription."""

    days: int = Field(..., ge=1, le=365)
    reason: str | None = Field(None, max_length=500)


# =============================================================================
# Subscription Management Endpoints
# =============================================================================


@router.get(
    "/subscriptions",
    response_model=SubscriptionListResponse,
    summary="List all subscriptions",
    description="List all subscriptions with filtering (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_subscriptions(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query()] = None,
    tier_filter: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionListResponse:
    """List all subscriptions."""
    query = select(Subscription).options(
        selectinload(Subscription.user),
        selectinload(Subscription.tier),
    )

    filters = []
    if status_filter:
        filters.append(Subscription.status == status_filter)
    if tier_filter:
        filters.append(Subscription.tier.has(slug=tier_filter))

    if filters:
        query = query.where(and_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(Subscription.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return SubscriptionListResponse(
        items=[
            AdminSubscriptionResponse(
                id=sub.id,
                user_id=sub.user_id,
                user_email=sub.user.email if sub.user else None,
                tier_slug=sub.tier.slug if sub.tier else "unknown",
                tier_name=sub.tier.name if sub.tier else "Unknown",
                status=sub.status,
                stripe_subscription_id=sub.stripe_subscription_id,
                current_period_start=sub.current_period_start,
                current_period_end=sub.current_period_end,
                cancel_at_period_end=sub.cancel_at_period_end,
                created_at=sub.created_at,
            )
            for sub in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=AdminSubscriptionResponse,
    summary="Get subscription details",
    description="Get details of a specific subscription (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminSubscriptionResponse:
    """Get subscription by ID."""
    query = (
        select(Subscription)
        .options(
            selectinload(Subscription.user),
            selectinload(Subscription.tier),
        )
        .where(Subscription.id == subscription_id)
    )

    result = await db.execute(query)
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    return AdminSubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        user_email=sub.user.email if sub.user else None,
        tier_slug=sub.tier.slug if sub.tier else "unknown",
        tier_name=sub.tier.name if sub.tier else "Unknown",
        status=sub.status,
        stripe_subscription_id=sub.stripe_subscription_id,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        created_at=sub.created_at,
    )


@router.patch(
    "/subscriptions/{subscription_id}/tier",
    response_model=AdminSubscriptionResponse,
    summary="Change subscription tier",
    description="Change a subscription's tier (admin only).",
    dependencies=[Depends(require_admin())],
)
async def change_subscription_tier(
    subscription_id: UUID,
    request: ChangeTierRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminSubscriptionResponse:
    """Change subscription tier."""
    # Get subscription
    query = (
        select(Subscription)
        .options(
            selectinload(Subscription.user),
            selectinload(Subscription.tier),
        )
        .where(Subscription.id == subscription_id)
    )

    result = await db.execute(query)
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    # Get new tier
    tier_query = select(SubscriptionTier).where(SubscriptionTier.slug == request.tier_slug)
    tier_result = await db.execute(tier_query)
    new_tier = tier_result.scalar_one_or_none()

    if not new_tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tier '{request.tier_slug}' not found",
        )

    sub.tier_id = new_tier.id
    await db.commit()
    await db.refresh(sub)

    return AdminSubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        user_email=sub.user.email if sub.user else None,
        tier_slug=new_tier.slug,
        tier_name=new_tier.name,
        status=sub.status,
        stripe_subscription_id=sub.stripe_subscription_id,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        created_at=sub.created_at,
    )


@router.post(
    "/subscriptions/{subscription_id}/cancel",
    summary="Cancel subscription",
    description="Cancel a subscription immediately (admin only).",
    dependencies=[Depends(require_admin())],
)
async def cancel_subscription_admin(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Cancel subscription."""
    query = select(Subscription).where(Subscription.id == subscription_id)
    result = await db.execute(query)
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    sub.status = "cancelled"
    sub.cancelled_at = datetime.now(tz=UTC)
    await db.commit()

    return {"message": "Subscription cancelled"}


@router.post(
    "/subscriptions/{subscription_id}/extend",
    response_model=AdminSubscriptionResponse,
    summary="Extend subscription",
    description="Extend a subscription's end date (admin only).",
    dependencies=[Depends(require_admin())],
)
async def extend_subscription(
    subscription_id: UUID,
    request: ExtendSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminSubscriptionResponse:
    """Extend subscription end date."""
    query = (
        select(Subscription)
        .options(
            selectinload(Subscription.user),
            selectinload(Subscription.tier),
        )
        .where(Subscription.id == subscription_id)
    )

    result = await db.execute(query)
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    if sub.current_period_end:
        sub.current_period_end = sub.current_period_end + timedelta(days=request.days)
    else:
        sub.current_period_end = datetime.now(tz=UTC) + timedelta(days=request.days)

    await db.commit()
    await db.refresh(sub)

    return AdminSubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        user_email=sub.user.email if sub.user else None,
        tier_slug=sub.tier.slug if sub.tier else "unknown",
        tier_name=sub.tier.name if sub.tier else "Unknown",
        status=sub.status,
        stripe_subscription_id=sub.stripe_subscription_id,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        created_at=sub.created_at,
    )


@router.get(
    "/users/{user_id}/credits",
    summary="Get user credits",
    description="Get credit balance for a user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_user_credits(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get user credit balance."""
    query = select(CreditBalance).where(CreditBalance.user_id == user_id)
    result = await db.execute(query)
    balance = result.scalar_one_or_none()

    if not balance:
        return {"user_id": str(user_id), "balance": 0, "lifetime_earned": 0, "lifetime_spent": 0}

    return {
        "user_id": str(user_id),
        "balance": balance.balance,
        "lifetime_earned": balance.lifetime_earned,
        "lifetime_spent": balance.lifetime_spent,
    }


@router.post(
    "/users/{user_id}/credits/add",
    summary="Add credits to user",
    description="Add credits to a user's balance (admin only).",
    dependencies=[Depends(require_admin())],
)
async def add_user_credits(
    user_id: UUID,
    amount: Annotated[int, Query(ge=1, le=10000)],
    _reason: Annotated[str | None, Query(max_length=500)] = None,  # TODO: Store reason in audit log
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add credits to user."""
    query = select(CreditBalance).where(CreditBalance.user_id == user_id)
    result = await db.execute(query)
    balance = result.scalar_one_or_none()

    if not balance:
        balance = CreditBalance(user_id=user_id, balance=0, lifetime_earned=0, lifetime_spent=0)
        db.add(balance)

    balance.balance += amount
    balance.lifetime_earned += amount

    await db.commit()

    return {
        "message": f"Added {amount} credits",
        "new_balance": balance.balance,
    }


# =============================================================================
# Organization Management Schemas
# =============================================================================


class AdminOrganizationResponse(BaseModel):
    """Admin view of an organization."""

    id: UUID
    name: str
    slug: str
    description: str | None = None
    member_count: int = 0
    owner_id: UUID | None = None
    owner_email: str | None = None
    tier_slug: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    """Paginated organization list."""

    items: list[AdminOrganizationResponse]
    total: int
    page: int
    page_size: int


class AdminOrgMemberResponse(BaseModel):
    """Admin view of an organization member."""

    id: UUID
    user_id: UUID
    user_email: str | None = None
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Organization Management Endpoints
# =============================================================================


@router.get(
    "/organizations",
    response_model=OrganizationListResponse,
    summary="List all organizations",
    description="List all organizations (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_organizations(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> OrganizationListResponse:
    """List all organizations."""
    query = select(Organization).where(Organization.deleted_at.is_(None))

    if search:
        query = query.where(
            or_(
                Organization.name.ilike(f"%{search}%"),
                Organization.slug.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(Organization.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    orgs = result.scalars().all()

    items = []
    for org in orgs:
        # Get member count
        member_count_query = select(func.count()).where(
            OrganizationMember.organization_id == org.id
        )
        member_count = (await db.execute(member_count_query)).scalar_one()

        # Get owner
        owner_query = (
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user))
            .where(
                and_(
                    OrganizationMember.organization_id == org.id,
                    OrganizationMember.role == "owner",
                )
            )
        )
        owner_result = await db.execute(owner_query)
        owner_membership = owner_result.scalar_one_or_none()

        items.append(
            AdminOrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                description=org.description,
                member_count=member_count,
                owner_id=owner_membership.user_id if owner_membership else None,
                owner_email=owner_membership.user.email
                if owner_membership and owner_membership.user
                else None,
                tier_slug=org.tier_slug if hasattr(org, "tier_slug") else None,
                created_at=org.created_at,
            )
        )

    return OrganizationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/organizations/{org_id}",
    response_model=AdminOrganizationResponse,
    summary="Get organization details",
    description="Get details of an organization (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminOrganizationResponse:
    """Get organization by ID."""
    query = select(Organization).where(
        and_(Organization.id == org_id, Organization.deleted_at.is_(None))
    )
    result = await db.execute(query)
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Get member count
    member_count_query = select(func.count()).where(OrganizationMember.organization_id == org.id)
    member_count = (await db.execute(member_count_query)).scalar_one()

    # Get owner
    owner_query = (
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(
            and_(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.role == "owner",
            )
        )
    )
    owner_result = await db.execute(owner_query)
    owner_membership = owner_result.scalar_one_or_none()

    return AdminOrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        member_count=member_count,
        owner_id=owner_membership.user_id if owner_membership else None,
        owner_email=owner_membership.user.email
        if owner_membership and owner_membership.user
        else None,
        tier_slug=org.tier_slug if hasattr(org, "tier_slug") else None,
        created_at=org.created_at,
    )


@router.get(
    "/organizations/{org_id}/members",
    summary="Get organization members",
    description="Get members of an organization (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_organization_members(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AdminOrgMemberResponse]:
    """Get organization members."""
    query = (
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(OrganizationMember.organization_id == org_id)
    )

    result = await db.execute(query)
    members = result.scalars().all()

    return [
        AdminOrgMemberResponse(
            id=m.id,
            user_id=m.user_id,
            user_email=m.user.email if m.user else None,
            role=m.role,
            joined_at=m.created_at,
        )
        for m in members
    ]


@router.delete(
    "/organizations/{org_id}",
    summary="Delete organization",
    description="Soft delete an organization (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete organization."""
    query = select(Organization).where(
        and_(Organization.id == org_id, Organization.deleted_at.is_(None))
    )
    result = await db.execute(query)
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    org.deleted_at = datetime.now(tz=UTC)
    await db.commit()

    return {"message": "Organization deleted"}


# =============================================================================
# Component Library Management Schemas
# =============================================================================


class AdminComponentResponse(BaseModel):
    """Admin view of a component."""

    id: UUID
    name: str
    part_number: str | None = None
    manufacturer: str | None = None
    category: str | None = None
    user_id: UUID | None = None
    user_email: str | None = None
    is_library: bool = False
    is_verified: bool = False
    is_featured: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class ComponentListResponse(BaseModel):
    """Paginated component list."""

    items: list[AdminComponentResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Component Library Management Endpoints
# =============================================================================


@router.get(
    "/components",
    response_model=ComponentListResponse,
    summary="List all components",
    description="List all components (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_components(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query()] = None,
    library_only: Annotated[bool, Query()] = False,
    db: AsyncSession = Depends(get_db),
) -> ComponentListResponse:
    """List all components."""
    query = select(ReferenceComponent)

    filters = []
    if search:
        filters.append(
            or_(
                ReferenceComponent.name.ilike(f"%{search}%"),
                ReferenceComponent.part_number.ilike(f"%{search}%"),
                ReferenceComponent.manufacturer.ilike(f"%{search}%"),
            )
        )
    if library_only:
        filters.append(ReferenceComponent.user_id.is_(None))

    if filters:
        query = query.where(and_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(ReferenceComponent.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    components = result.scalars().all()

    items = []
    for comp in components:
        # Get user email if user-owned
        user_email = None
        if comp.user_id:
            user_query = select(User).where(User.id == comp.user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            user_email = user.email if user else None

        items.append(
            AdminComponentResponse(
                id=comp.id,
                name=comp.name,
                part_number=comp.part_number,
                manufacturer=comp.manufacturer,
                category=comp.category,
                user_id=comp.user_id,
                user_email=user_email,
                is_library=comp.user_id is None,
                is_verified=getattr(comp, "is_verified", False),
                is_featured=getattr(comp, "is_featured", False),
                created_at=comp.created_at,
            )
        )

    return ComponentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/components/{component_id}/verify",
    summary="Verify component",
    description="Mark a component as verified (admin only).",
    dependencies=[Depends(require_admin())],
)
async def verify_component(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Verify a component."""
    query = select(ReferenceComponent).where(ReferenceComponent.id == component_id)
    result = await db.execute(query)
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )

    if hasattr(comp, "is_verified"):
        comp.is_verified = True
        await db.commit()

    return {"message": "Component verified"}


@router.post(
    "/components/{component_id}/feature",
    summary="Feature component",
    description="Mark a component as featured (admin only).",
    dependencies=[Depends(require_admin())],
)
async def feature_component(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Feature a component."""
    query = select(ReferenceComponent).where(ReferenceComponent.id == component_id)
    result = await db.execute(query)
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )

    if hasattr(comp, "is_featured"):
        comp.is_featured = True
        await db.commit()

    return {"message": "Component featured"}


@router.delete(
    "/components/{component_id}",
    summary="Delete component",
    description="Delete a component (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_component(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a component."""
    query = select(ReferenceComponent).where(ReferenceComponent.id == component_id)
    result = await db.execute(query)
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )

    await db.delete(comp)
    await db.commit()

    return {"message": "Component deleted"}


# =============================================================================
# Notification Management Schemas
# =============================================================================


class AdminNotificationResponse(BaseModel):
    """Admin view of a notification."""

    id: UUID
    user_id: UUID
    user_email: str | None = None
    notification_type: str
    title: str
    message: str | None = None
    is_read: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated notification list."""

    items: list[AdminNotificationResponse]
    total: int
    page: int
    page_size: int


class RecipientType(StrEnum):
    """Recipient targeting type for notifications."""

    ALL = "all"
    TIER = "tier"
    ORGANIZATION = "organization"
    USERS = "users"


class CreateAnnouncementRequest(BaseModel):
    """Request to create a system announcement."""

    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=2000)
    recipient_type: RecipientType = Field(
        default=RecipientType.ALL, description="Target audience type"
    )
    target_tier: str | None = Field(
        None, description="Target specific tier (if recipient_type=tier)"
    )
    target_organization_id: str | None = Field(
        None, description="Target org ID (if recipient_type=organization)"
    )
    target_user_ids: list[str] | None = Field(
        None, description="Target user IDs (if recipient_type=users)"
    )
    scheduled_at: datetime | None = Field(None, description="When to send (None for immediate)")
    expires_at: datetime | None = Field(None, description="When notification expires")


# =============================================================================
# Notification Management Endpoints
# =============================================================================


@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    summary="List notifications",
    description="List all notifications (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_notifications_admin(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    notification_type: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """List all notifications."""
    query = select(Notification).options(selectinload(Notification.user))

    if notification_type:
        query = query.where(Notification.notification_type == notification_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(Notification.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return NotificationListResponse(
        items=[
            AdminNotificationResponse(
                id=n.id,
                user_id=n.user_id,
                user_email=n.user.email if n.user else None,
                notification_type=n.notification_type,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in notifications
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/notifications/announcement",
    summary="Create announcement",
    description="Send a system announcement with flexible targeting (admin only).",
    dependencies=[Depends(require_admin())],
)
async def create_announcement(
    request: CreateAnnouncementRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a system announcement with various targeting options.

    Supports:
    - All users
    - Specific subscription tier users
    - Specific organization members
    - Specific user IDs
    - Scheduled notifications (future delivery)
    - Expiration dates
    """
    # TODO: If scheduled_at is in the future, store in a job queue
    # For now, we send immediately
    if request.scheduled_at and request.scheduled_at > datetime.now(
        request.scheduled_at.tzinfo or None
    ):
        # Return scheduled info but don't send yet
        # This would typically go to a Celery task
        return {
            "message": f"Announcement scheduled for {request.scheduled_at.isoformat()}",
            "scheduled": True,
            "scheduled_at": request.scheduled_at.isoformat(),
        }

    # Build user query based on recipient_type
    user_query = select(User).where(User.is_active)

    if request.recipient_type == RecipientType.TIER:
        if not request.target_tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_tier is required when recipient_type is 'tier'",
            )
        user_query = (
            user_query.join(Subscription)
            .join(SubscriptionTier)
            .where(SubscriptionTier.slug == request.target_tier)
        )
    elif request.recipient_type == RecipientType.ORGANIZATION:
        if not request.target_organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_organization_id is required when recipient_type is 'organization'",
            )
        user_query = user_query.join(OrganizationMember).where(
            OrganizationMember.organization_id == UUID(request.target_organization_id)
        )
    elif request.recipient_type == RecipientType.USERS:
        if not request.target_user_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_user_ids is required when recipient_type is 'users'",
            )
        user_ids = [UUID(uid) for uid in request.target_user_ids]
        user_query = user_query.where(User.id.in_(user_ids))
    # RecipientType.ALL uses the base query without additional filters

    result = await db.execute(user_query)
    users = result.scalars().all()

    # Create notification for each user
    created_count = 0
    for user in users:
        notification = Notification(
            user_id=user.id,
            notification_type="system_announcement",
            title=request.title,
            message=request.message,
            expires_at=request.expires_at,
        )
        db.add(notification)
        created_count += 1

    await db.commit()

    return {
        "message": f"Announcement sent to {created_count} users",
        "sent_count": created_count,
        "recipient_type": request.recipient_type.value,
        "expires_at": request.expires_at.isoformat() if request.expires_at else None,
    }


@router.post(
    "/users/{user_id}/send-notification",
    summary="Send notification to user",
    description="Send a notification to a specific user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def send_user_notification(
    user_id: UUID,
    title: str = Query(..., max_length=200),
    message: str = Query(..., max_length=2000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Send notification to a specific user."""
    # Verify user exists
    user_query = select(User).where(User.id == user_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    notification = Notification(
        user_id=user_id,
        notification_type="admin_message",
        title=title,
        message=message,
    )
    db.add(notification)
    await db.commit()

    return {"message": "Notification sent"}


@router.delete(
    "/notifications/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification",
    description="Delete a notification by ID (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_notification_admin(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a notification."""
    query = select(Notification).where(Notification.id == notification_id)
    result = await db.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    await db.delete(notification)
    await db.commit()


@router.get(
    "/notifications/stats",
    summary="Get notification stats",
    description="Get notification delivery and read statistics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_notification_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get notification statistics."""
    now = datetime.now(tz=UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # Total notifications
    total = (await db.execute(select(func.count(Notification.id)))).scalar_one()

    # Unread notifications
    unread = (
        await db.execute(select(func.count(Notification.id)).where(not Notification.is_read))
    ).scalar_one()

    # Read notifications
    read = (
        await db.execute(select(func.count(Notification.id)).where(Notification.is_read))
    ).scalar_one()

    # Notifications sent today
    sent_today = (
        await db.execute(
            select(func.count(Notification.id)).where(Notification.created_at >= today_start)
        )
    ).scalar_one()

    # Notifications sent this week
    sent_week = (
        await db.execute(
            select(func.count(Notification.id)).where(Notification.created_at >= week_ago)
        )
    ).scalar_one()

    # Expired notifications
    expired = (
        await db.execute(
            select(func.count(Notification.id)).where(
                Notification.expires_at.isnot(None),
                Notification.expires_at < now,
            )
        )
    ).scalar_one()

    # Calculate read rate
    read_rate = (read / total * 100) if total > 0 else 0

    return {
        "total": total,
        "unread": unread,
        "read": read,
        "read_rate_percent": round(read_rate, 1),
        "sent_today": sent_today,
        "sent_this_week": sent_week,
        "expired": expired,
    }


# =============================================================================
# File/Storage Management Schemas
# =============================================================================


class AdminFileResponse(BaseModel):
    """Admin view of a file."""

    id: UUID
    user_id: UUID
    user_email: str | None = None
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_bucket: str
    created_at: datetime

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """Paginated file list."""

    items: list[AdminFileResponse]
    total: int
    page: int
    page_size: int


class StorageStatsResponse(BaseModel):
    """Storage statistics."""

    total_files: int
    total_size_bytes: int
    total_size_gb: float
    files_by_type: dict[str, int]
    top_users: list[dict[str, Any]]


# =============================================================================
# File/Storage Management Endpoints
# =============================================================================


@router.get(
    "/storage/stats",
    response_model=StorageStatsResponse,
    summary="Get storage statistics",
    description="Get platform-wide storage statistics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_storage_stats(
    db: AsyncSession = Depends(get_db),
) -> StorageStatsResponse:
    """Get storage statistics."""
    # Total files and size
    total_query = select(
        func.count(FileModel.id),
        func.coalesce(func.sum(FileModel.size_bytes), 0),
    )
    total_result = await db.execute(total_query)
    total_files, total_size = total_result.one()

    # Files by MIME type
    type_query = select(
        FileModel.mime_type,
        func.count(FileModel.id),
    ).group_by(FileModel.mime_type)
    type_result = await db.execute(type_query)
    files_by_type = {row[0]: row[1] for row in type_result.all()}

    # Top users by storage
    top_query = (
        select(
            FileModel.user_id,
            func.count(FileModel.id).label("file_count"),
            func.sum(FileModel.size_bytes).label("total_size"),
        )
        .group_by(FileModel.user_id)
        .order_by(desc("total_size"))
        .limit(10)
    )
    top_result = await db.execute(top_query)

    top_users = []
    for row in top_result.all():
        user_query = select(User).where(User.id == row[0])
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        top_users.append(
            {
                "user_id": str(row[0]),
                "email": user.email if user else None,
                "file_count": row[1],
                "total_size_bytes": row[2] or 0,
            }
        )

    return StorageStatsResponse(
        total_files=total_files,
        total_size_bytes=total_size,
        total_size_gb=round(total_size / (1024**3), 2),
        files_by_type=files_by_type,
        top_users=top_users,
    )


@router.get(
    "/files",
    response_model=FileListResponse,
    summary="List all files",
    description="List all files (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_files_admin(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: Annotated[UUID | None, Query()] = None,
    mime_type: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> FileListResponse:
    """List all files."""
    query = select(FileModel).options(selectinload(FileModel.user))

    filters = []
    if user_id:
        filters.append(FileModel.user_id == user_id)
    if mime_type:
        filters.append(FileModel.mime_type.ilike(f"%{mime_type}%"))

    if filters:
        query = query.where(and_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(FileModel.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    files = result.scalars().all()

    return FileListResponse(
        items=[
            AdminFileResponse(
                id=f.id,
                user_id=f.user_id,
                user_email=f.user.email if f.user else None,
                filename=f.filename,
                original_filename=f.original_filename,
                mime_type=f.mime_type,
                size_bytes=f.size_bytes,
                storage_bucket=f.storage_bucket,
                created_at=f.created_at,
            )
            for f in files
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/files/{file_id}",
    summary="Delete file",
    description="Delete a file (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_file_admin(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a file."""
    query = select(FileModel).where(FileModel.id == file_id)
    result = await db.execute(query)
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    await db.delete(file)
    await db.commit()

    return {"message": "File deleted"}


# =============================================================================
# Audit Log Schemas
# =============================================================================


class AdminAuditLogResponse(BaseModel):
    """Admin view of an audit log entry."""

    id: UUID
    user_id: UUID | None = None
    user_email: str | None = None
    actor_type: str
    action: str
    resource_type: str
    resource_id: str | None = None
    ip_address: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list."""

    items: list[AdminAuditLogResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Audit Log Endpoints
# =============================================================================


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    summary="Get audit logs",
    description="Get system audit logs (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_audit_logs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    user_id: Annotated[UUID | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    resource_type: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """Get paginated audit logs."""
    query = select(AuditLog).options(selectinload(AuditLog.user))

    filters = []
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if action:
        filters.append(AuditLog.action == action)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)

    if filters:
        query = query.where(and_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        items=[
            AdminAuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_email=log.user.email if log.user else None,
                actor_type=log.actor_type,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=str(log.resource_id)
                if hasattr(log, "resource_id") and log.resource_id
                else None,
                ip_address=log.ip_address if hasattr(log, "ip_address") else None,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# API Key Management Schemas
# =============================================================================


class AdminAPIKeyResponse(BaseModel):
    """Admin view of an API key (masked)."""

    id: UUID
    user_id: UUID
    user_email: str | None = None
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool = True
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """Paginated API key list."""

    items: list[AdminAPIKeyResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# API Key Management Endpoints
# =============================================================================


@router.get(
    "/api-keys",
    response_model=APIKeyListResponse,
    summary="List all API keys",
    description="List all API keys (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_api_keys(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: Annotated[UUID | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> APIKeyListResponse:
    """List all API keys."""
    query = select(APIKey).options(selectinload(APIKey.user))

    if user_id:
        query = query.where(APIKey.user_id == user_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(APIKey.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    keys = result.scalars().all()

    return APIKeyListResponse(
        items=[
            AdminAPIKeyResponse(
                id=k.id,
                user_id=k.user_id,
                user_email=k.user.email if k.user else None,
                name=k.name,
                key_prefix=k.key_prefix,
                scopes=k.scopes or [],
                is_active=k.is_active,
                last_used_at=k.last_used_at,
                expires_at=k.expires_at,
                created_at=k.created_at,
            )
            for k in keys
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/api-keys/{key_id}/revoke",
    summary="Revoke API key",
    description="Revoke an API key (admin only).",
    dependencies=[Depends(require_admin())],
)
async def revoke_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Revoke an API key."""
    query = select(APIKey).where(APIKey.id == key_id)
    result = await db.execute(query)
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    key.is_active = False
    key.revoked_at = datetime.now(tz=UTC)
    await db.commit()

    return {"message": "API key revoked"}


# =============================================================================
# System Health Schemas
# =============================================================================


class ServiceStatus(BaseModel):
    """Status of a service."""

    name: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float | None = None
    message: str | None = None


class SystemHealthResponse(BaseModel):
    """System health overview."""

    overall_status: str
    services: list[ServiceStatus]
    version: str
    uptime_seconds: int
    last_check: datetime


# =============================================================================
# System Health Endpoints
# =============================================================================


@router.get(
    "/system/health",
    response_model=SystemHealthResponse,
    summary="Get system health",
    description="Get overall system health status (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_system_health(
    db: AsyncSession = Depends(get_db),
) -> SystemHealthResponse:
    """Get system health status for all services."""
    import time

    import aiohttp

    services = []

    # Check database
    try:
        start = time.time()
        await db.execute(select(func.count()).select_from(User))
        db_latency = (time.time() - start) * 1000
        services.append(
            ServiceStatus(
                name="database",
                status="healthy",
                latency_ms=round(db_latency, 2),
                message="PostgreSQL connected",
            )
        )
    except Exception as e:
        services.append(
            ServiceStatus(
                name="database",
                status="unhealthy",
                message=f"Database error: {str(e)[:100]}",
            )
        )

    # Check Redis
    try:
        import redis.asyncio as redis

        from app.core.config import settings

        start = time.time()
        r = redis.from_url(settings.REDIS_URL or "redis://localhost:6379")
        await r.ping()
        await r.close()
        redis_latency = (time.time() - start) * 1000
        services.append(
            ServiceStatus(
                name="redis",
                status="healthy",
                latency_ms=round(redis_latency, 2),
                message="Redis connected",
            )
        )
    except Exception as e:
        services.append(
            ServiceStatus(
                name="redis",
                status="unhealthy",
                message=f"Redis error: {str(e)[:100]}",
            )
        )

    # Check Celery (by checking if Redis has celery keys)
    try:
        import redis.asyncio as redis

        from app.core.config import settings

        r = redis.from_url(settings.REDIS_URL or "redis://localhost:6379")
        # Check for celery-related keys
        celery_keys = await r.keys("celery*")
        await r.close()
        services.append(
            ServiceStatus(
                name="celery",
                status="healthy" if celery_keys else "degraded",
                message="Celery queue active" if celery_keys else "No active workers detected",
            )
        )
    except Exception as e:
        services.append(
            ServiceStatus(
                name="celery",
                status="unhealthy",
                message=f"Celery check failed: {str(e)[:100]}",
            )
        )

    # Check MinIO/S3
    try:
        from app.core.config import settings

        if settings.MINIO_ENDPOINT:
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.get(
                    f"http://{settings.MINIO_ENDPOINT}/minio/health/live",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    minio_latency = (time.time() - start) * 1000
                    if resp.status == 200:
                        services.append(
                            ServiceStatus(
                                name="storage",
                                status="healthy",
                                latency_ms=round(minio_latency, 2),
                                message="MinIO connected",
                            )
                        )
                    else:
                        services.append(
                            ServiceStatus(
                                name="storage",
                                status="degraded",
                                latency_ms=round(minio_latency, 2),
                                message=f"MinIO returned status {resp.status}",
                            )
                        )
        else:
            services.append(
                ServiceStatus(
                    name="storage",
                    status="healthy",
                    message="Using local storage",
                )
            )
    except Exception as e:
        services.append(
            ServiceStatus(
                name="storage",
                status="unhealthy",
                message=f"Storage error: {str(e)[:100]}",
            )
        )

    # Check AI Service (if configured)
    try:
        from app.core.config import settings

        if hasattr(settings, "AI_SERVICE_URL") and settings.AI_SERVICE_URL:
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.get(
                    f"{settings.AI_SERVICE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    ai_latency = (time.time() - start) * 1000
                    if resp.status == 200:
                        services.append(
                            ServiceStatus(
                                name="ai",
                                status="healthy",
                                latency_ms=round(ai_latency, 2),
                                message="AI service connected",
                            )
                        )
                    else:
                        services.append(
                            ServiceStatus(
                                name="ai",
                                status="degraded",
                                message=f"AI service returned status {resp.status}",
                            )
                        )
        else:
            services.append(
                ServiceStatus(
                    name="ai",
                    status="healthy",
                    message="Using embedded AI (no external service)",
                )
            )
    except Exception as e:
        services.append(
            ServiceStatus(
                name="ai",
                status="degraded",
                message=f"AI service unavailable: {str(e)[:50]}",
            )
        )

    # API status (always healthy if we got this far)
    services.insert(
        0,
        ServiceStatus(
            name="api",
            status="healthy",
            message="FastAPI running",
        ),
    )

    # Overall status
    overall = "healthy"
    if any(s.status == "unhealthy" for s in services):
        overall = "unhealthy"
    elif any(s.status == "degraded" for s in services):
        overall = "degraded"

    return SystemHealthResponse(
        overall_status=overall,
        services=services,
        version="1.0.0",
        uptime_seconds=0,  # Would need app start time tracking
        last_check=datetime.now(tz=UTC),
    )


@router.get(
    "/system/version",
    summary="Get system version",
    description="Get system version info (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_system_version() -> dict[str, Any]:
    """Get system version."""
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "python_version": "3.11",
        "environment": "development",
    }


# =============================================================================
# CAD v2 Admin Schemas
# =============================================================================


class AdminCADv2ComponentResponse(BaseModel):
    """Admin view of a CAD v2 component from the registry."""

    id: str
    name: str
    category: str
    description: str | None = None
    dimensions_mm: tuple[float, float, float]
    aliases: list[str] = Field(default_factory=list)
    mounting_hole_count: int = 0
    port_count: int = 0
    is_in_database: bool = False
    database_id: UUID | None = None
    is_verified: bool = False
    is_featured: bool = False


class CADv2ComponentListResponse(BaseModel):
    """Paginated CAD v2 component list."""

    items: list[AdminCADv2ComponentResponse]
    total: int
    categories: dict[str, int]


class AdminStarterResponse(BaseModel):
    """Admin view of a starter design."""

    id: UUID
    name: str
    description: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_starter: bool = True
    is_public: bool = True
    is_featured: bool = False
    remix_count: int = 0
    view_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class StarterListResponse(BaseModel):
    """Paginated starter list."""

    items: list[AdminStarterResponse]
    total: int
    page: int
    page_size: int
    categories: list[str]


class StarterUpdateRequest(BaseModel):
    """Request to update a starter design."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    is_featured: bool | None = None
    is_public: bool | None = None


class AdminMarketplaceStatsResponse(BaseModel):
    """Marketplace statistics for admin dashboard."""

    total_starters: int
    total_public_designs: int
    total_remixes_today: int
    total_remixes_week: int
    most_remixed: list[dict[str, Any]]
    starters_by_category: dict[str, int]


class CADv2RegistrySyncResponse(BaseModel):
    """Response from syncing CAD v2 registry to database."""

    created: int
    updated: int
    total_in_registry: int
    message: str


# =============================================================================
# CAD v2 Admin Endpoints
# =============================================================================


@router.get(
    "/cad-v2/components",
    response_model=CADv2ComponentListResponse,
    summary="List CAD v2 components",
    description="List all components from the CAD v2 registry (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_cad_v2_components(
    category: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    db: AsyncSession = Depends(get_db),
) -> CADv2ComponentListResponse:
    """List all CAD v2 components from the registry.

    Shows components from the in-memory registry and indicates
    which have corresponding database records.
    """
    from app.cad_v2.components import get_registry

    registry = get_registry()

    # Get all components from registry
    if category:
        from app.cad_v2.schemas.components import ComponentCategory

        try:
            cat_enum = ComponentCategory(category)
            components = registry.list_category(cat_enum)
        except ValueError:
            components = []
    else:
        components = registry.list_all()

    # Filter by search if provided
    if search:
        search_lower = search.lower()
        components = [
            c
            for c in components
            if search_lower in c.id.lower()
            or search_lower in c.name.lower()
            or any(search_lower in alias.lower() for alias in c.aliases)
        ]

    # Get database records for these components
    slugs = [c.id for c in components]
    db_components = await db.execute(
        select(ReferenceComponent).where(ReferenceComponent.slug.in_(slugs))
    )
    db_comp_map = {c.slug: c for c in db_components.scalars().all()}

    # Build category counts
    category_counts: dict[str, int] = {}
    for comp in registry.list_all():
        cat = comp.category.value
        category_counts[cat] = category_counts.get(cat, 0) + 1

    items = []
    for comp in components:
        db_record = db_comp_map.get(comp.id)
        items.append(
            AdminCADv2ComponentResponse(
                id=comp.id,
                name=comp.name,
                category=comp.category.value,
                description=comp.description,
                dimensions_mm=comp.dimensions.to_tuple_mm(),
                aliases=list(comp.aliases) if comp.aliases else [],
                mounting_hole_count=len(comp.mounting_holes) if comp.mounting_holes else 0,
                port_count=len(comp.ports) if comp.ports else 0,
                is_in_database=db_record is not None,
                database_id=db_record.id if db_record else None,
                is_verified=getattr(db_record, "is_verified", False) if db_record else False,
                is_featured=getattr(db_record, "is_featured", False) if db_record else False,
            )
        )

    return CADv2ComponentListResponse(
        items=items,
        total=len(items),
        categories=category_counts,
    )


@router.get(
    "/cad-v2/components/{component_id}",
    summary="Get CAD v2 component details",
    description="Get detailed info for a CAD v2 component (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_cad_v2_component(
    component_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get detailed CAD v2 component info."""
    from app.cad_v2.components import get_registry

    registry = get_registry()
    comp = registry.get(component_id)

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component '{component_id}' not found in registry",
        )

    # Get database record if exists
    db_result = await db.execute(
        select(ReferenceComponent).where(ReferenceComponent.slug == component_id)
    )
    db_record = db_result.scalar_one_or_none()

    return {
        "registry": {
            "id": comp.id,
            "name": comp.name,
            "category": comp.category.value,
            "description": comp.description,
            "dimensions_mm": comp.dimensions.to_tuple_mm(),
            "aliases": list(comp.aliases) if comp.aliases else [],
            "mounting_holes": [
                {
                    "position": {"x": h.position.x, "y": h.position.y},
                    "diameter": h.diameter,
                }
                for h in (comp.mounting_holes or [])
            ],
            "ports": [
                {
                    "name": p.name,
                    "type": p.type,
                    "wall": p.wall.value if hasattr(p.wall, "value") else str(p.wall),
                    "width": p.width,
                    "height": p.height,
                }
                for p in (comp.ports or [])
            ],
        },
        "database": {
            "exists": db_record is not None,
            "id": str(db_record.id) if db_record else None,
            "is_verified": getattr(db_record, "is_verified", False) if db_record else False,
            "is_featured": getattr(db_record, "is_featured", False) if db_record else False,
            "created_at": db_record.created_at.isoformat() if db_record else None,
        },
    }


@router.post(
    "/cad-v2/sync",
    response_model=CADv2RegistrySyncResponse,
    summary="Sync CAD v2 registry to database",
    description="Sync all CAD v2 components from registry to database (admin only).",
    dependencies=[Depends(require_admin())],
)
async def sync_cad_v2_registry(
    db: AsyncSession = Depends(get_db),
) -> CADv2RegistrySyncResponse:
    """Sync CAD v2 component registry with database.

    Creates or updates ReferenceComponent records for all
    components in the in-memory registry.
    """
    from app.cad_v2.components import get_registry
    from app.seeds.components_v2 import seed_components_v2

    registry = get_registry()
    created, updated = await seed_components_v2(db)

    return CADv2RegistrySyncResponse(
        created=created,
        updated=updated,
        total_in_registry=registry.count,
        message=f"Synced {created + updated} components ({created} created, {updated} updated)",
    )


@router.post(
    "/cad-v2/components/{component_id}/verify",
    summary="Verify CAD v2 component",
    description="Mark a CAD v2 component as verified (admin only).",
    dependencies=[Depends(require_admin())],
)
async def verify_cad_v2_component(
    component_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark a CAD v2 component as verified."""
    result = await db.execute(
        select(ReferenceComponent).where(ReferenceComponent.slug == component_id)
    )
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component '{component_id}' not found in database. Sync first.",
        )

    if hasattr(comp, "is_verified"):
        comp.is_verified = True
        await db.commit()

    return {"message": f"Component '{component_id}' verified"}


@router.post(
    "/cad-v2/components/{component_id}/feature",
    summary="Feature CAD v2 component",
    description="Mark a CAD v2 component as featured (admin only).",
    dependencies=[Depends(require_admin())],
)
async def feature_cad_v2_component(
    component_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mark a CAD v2 component as featured."""
    result = await db.execute(
        select(ReferenceComponent).where(ReferenceComponent.slug == component_id)
    )
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component '{component_id}' not found in database. Sync first.",
        )

    if hasattr(comp, "is_featured"):
        comp.is_featured = True
        await db.commit()

    return {"message": f"Component '{component_id}' featured"}


# =============================================================================
# Starter Design Admin Endpoints
# =============================================================================


@router.get(
    "/starters",
    response_model=StarterListResponse,
    summary="List starter designs",
    description="List all starter designs (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_starters(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    db: AsyncSession = Depends(get_db),
) -> StarterListResponse:
    """List all starter designs with pagination."""
    from app.models.design import Design

    query = select(Design).where(
        Design.source_type == "starter",
        Design.deleted_at.is_(None),
    )

    if category:
        query = query.where(Design.category == category)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Design.name.ilike(search_pattern),
                Design.description.ilike(search_pattern),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Get unique categories
    cat_query = (
        select(Design.category)
        .where(
            Design.source_type == "starter",
            Design.deleted_at.is_(None),
            Design.category.isnot(None),
        )
        .distinct()
    )
    cat_result = await db.execute(cat_query)
    categories = [row[0] for row in cat_result.all() if row[0]]

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(Design.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    starters = result.scalars().all()

    return StarterListResponse(
        items=[
            AdminStarterResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                category=s.category,
                tags=s.tags or [],
                is_starter=s.extra_data.get("is_starter", True),
                is_public=s.is_public,
                is_featured=s.extra_data.get("is_featured", False),
                remix_count=getattr(s, "remix_count", 0),
                view_count=getattr(s, "view_count", 0),
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in starters
        ],
        total=total,
        page=page,
        page_size=page_size,
        categories=categories,
    )


@router.get(
    "/starters/{starter_id}",
    response_model=AdminStarterResponse,
    summary="Get starter details",
    description="Get starter design details (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_starter(
    starter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminStarterResponse:
    """Get starter design details."""
    from app.models.design import Design

    result = await db.execute(
        select(Design).where(
            Design.id == starter_id,
            Design.source_type == "starter",
            Design.deleted_at.is_(None),
        )
    )
    starter = result.scalar_one_or_none()

    if not starter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Starter design not found",
        )

    return AdminStarterResponse(
        id=starter.id,
        name=starter.name,
        description=starter.description,
        category=starter.category,
        tags=starter.tags or [],
        is_starter=starter.extra_data.get("is_starter", True),
        is_public=starter.is_public,
        is_featured=starter.extra_data.get("is_featured", False),
        remix_count=getattr(starter, "remix_count", 0),
        view_count=getattr(starter, "view_count", 0),
        created_at=starter.created_at,
        updated_at=starter.updated_at,
    )


@router.patch(
    "/starters/{starter_id}",
    response_model=AdminStarterResponse,
    summary="Update starter",
    description="Update a starter design (admin only).",
    dependencies=[Depends(require_admin())],
)
async def update_starter(
    starter_id: UUID,
    request: StarterUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminStarterResponse:
    """Update a starter design."""
    from app.models.design import Design

    result = await db.execute(
        select(Design).where(
            Design.id == starter_id,
            Design.source_type == "starter",
            Design.deleted_at.is_(None),
        )
    )
    starter = result.scalar_one_or_none()

    if not starter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Starter design not found",
        )

    # Apply updates
    if request.name is not None:
        starter.name = request.name
    if request.description is not None:
        starter.description = request.description
    if request.category is not None:
        starter.category = request.category
    if request.tags is not None:
        starter.tags = request.tags
    if request.is_featured is not None:
        starter.extra_data["is_featured"] = request.is_featured
    if request.is_public is not None:
        starter.is_public = request.is_public

    starter.updated_at = datetime.now(tz=UTC)

    await db.commit()
    await db.refresh(starter)

    return AdminStarterResponse(
        id=starter.id,
        name=starter.name,
        description=starter.description,
        category=starter.category,
        tags=starter.tags or [],
        is_starter=starter.extra_data.get("is_starter", True),
        is_public=starter.is_public,
        is_featured=starter.extra_data.get("is_featured", False),
        remix_count=getattr(starter, "remix_count", 0),
        view_count=getattr(starter, "view_count", 0),
        created_at=starter.created_at,
        updated_at=starter.updated_at,
    )


@router.post(
    "/starters/{starter_id}/feature",
    summary="Feature starter",
    description="Mark a starter as featured (admin only).",
    dependencies=[Depends(require_admin())],
)
async def feature_starter(
    starter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Feature a starter design."""
    from app.models.design import Design

    result = await db.execute(
        select(Design).where(
            Design.id == starter_id,
            Design.source_type == "starter",
        )
    )
    starter = result.scalar_one_or_none()

    if not starter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Starter design not found",
        )

    starter.extra_data["is_featured"] = True
    await db.commit()

    return {"message": "Starter featured"}


@router.post(
    "/starters/{starter_id}/unfeature",
    summary="Unfeature starter",
    description="Remove featured status from a starter (admin only).",
    dependencies=[Depends(require_admin())],
)
async def unfeature_starter(
    starter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Remove featured status from a starter design."""
    from app.models.design import Design

    result = await db.execute(
        select(Design).where(
            Design.id == starter_id,
            Design.source_type == "starter",
        )
    )
    starter = result.scalar_one_or_none()

    if not starter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Starter design not found",
        )

    starter.extra_data["is_featured"] = False
    await db.commit()

    return {"message": "Starter unfeatured"}


@router.delete(
    "/starters/{starter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete starter",
    description="Soft-delete a starter design (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_starter(
    starter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a starter design."""
    from app.models.design import Design

    result = await db.execute(
        select(Design).where(
            Design.id == starter_id,
            Design.source_type == "starter",
            Design.deleted_at.is_(None),
        )
    )
    starter = result.scalar_one_or_none()

    if not starter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Starter design not found",
        )

    starter.deleted_at = datetime.now(tz=UTC)
    await db.commit()


@router.post(
    "/starters/reseed",
    summary="Reseed starters",
    description="Re-run the starter seeding process (admin only).",
    dependencies=[Depends(require_admin())],
)
async def reseed_starters(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Re-run starter seeding."""
    from app.seeds.starters import seed_starters

    created, updated = await seed_starters(db)

    return {
        "message": f"Reseeded starters: {created} created, {updated} updated",
        "created": created,
        "updated": updated,
    }


# =============================================================================
# Marketplace Admin Endpoints
# =============================================================================


@router.get(
    "/marketplace/stats",
    response_model=AdminMarketplaceStatsResponse,
    summary="Get marketplace statistics",
    description="Get marketplace analytics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_marketplace_stats(
    db: AsyncSession = Depends(get_db),
) -> AdminMarketplaceStatsResponse:
    """Get marketplace statistics for admin dashboard."""
    from app.models.design import Design

    today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.now(tz=UTC) - timedelta(days=7)

    # Total starters
    total_starters = (
        await db.execute(
            select(func.count()).where(
                Design.source_type == "starter",
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Total public designs
    total_public = (
        await db.execute(
            select(func.count()).where(
                Design.is_public,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Remixes today (designs with source_type='remix' created today)
    remixes_today = (
        await db.execute(
            select(func.count()).where(
                Design.source_type == "remix",
                Design.created_at >= today_start,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Remixes this week
    remixes_week = (
        await db.execute(
            select(func.count()).where(
                Design.source_type == "remix",
                Design.created_at >= week_ago,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Starters by category
    cat_query = (
        select(
            Design.category,
            func.count().label("count"),
        )
        .where(
            Design.source_type == "starter",
            Design.deleted_at.is_(None),
            Design.category.isnot(None),
        )
        .group_by(Design.category)
    )
    cat_result = await db.execute(cat_query)
    starters_by_category = {row[0]: row[1] for row in cat_result.all()}

    # Most remixed (would need remix tracking, simplified here)
    most_remixed: list[dict[str, Any]] = []

    return AdminMarketplaceStatsResponse(
        total_starters=total_starters,
        total_public_designs=total_public,
        total_remixes_today=remixes_today,
        total_remixes_week=remixes_week,
        most_remixed=most_remixed,
        starters_by_category=starters_by_category,
    )


@router.get(
    "/marketplace/featured",
    summary="Get featured marketplace items",
    description="Get featured starters and designs (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_featured_items(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get featured marketplace items."""
    from app.models.design import Design

    # Get featured starters
    featured_query = select(Design).where(
        Design.source_type == "starter",
        Design.deleted_at.is_(None),
    )

    # Filter by is_featured in extra_data using JSON extraction
    featured_query = featured_query.where(Design.extra_data["is_featured"].as_boolean())

    result = await db.execute(featured_query.limit(20))
    featured = result.scalars().all()

    return {
        "featured_starters": [
            {
                "id": str(d.id),
                "name": d.name,
                "category": d.category,
                "description": d.description,
            }
            for d in featured
        ],
        "total": len(featured),
    }


@router.post(
    "/marketplace/reorder-featured",
    summary="Reorder featured items",
    description="Update the display order of featured items (admin only).",
    dependencies=[Depends(require_admin())],
)
async def reorder_featured(
    item_ids: list[UUID],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reorder featured marketplace items.

    Args:
        item_ids: List of design IDs in desired order.
    """
    from app.models.design import Design

    # Update display_order for each item
    for idx, item_id in enumerate(item_ids):
        result = await db.execute(select(Design).where(Design.id == item_id))
        design = result.scalar_one_or_none()
        if design and hasattr(design, "display_order"):
            design.display_order = idx

    await db.commit()

    return {
        "message": f"Reordered {len(item_ids)} items",
        "order": [str(id) for id in item_ids],
    }
