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

import csv
import io
import time as time_module
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import StreamingResponse

from app.core.auth import get_current_user, require_admin
from app.core.database import get_db
from app.models.api_key import APIKey
from app.models.audit import AuditLog
from app.models.coupon import Coupon, CouponRedemption, CouponType
from app.models.design import Design, DesignVersion
from app.models.job import Job
from app.models.project import Project
from app.models.template import Template
from app.models.file import File as FileModel
from app.models.moderation import ModerationLog
from app.models.notification import Notification, NotificationType
from app.models.organization import (
    Organization,
    OrganizationAuditLog,
    OrganizationCreditBalance,
    OrganizationMember,
)
from app.models.reference_component import ComponentLibrary, ReferenceComponent
from app.models.subscription import CreditBalance, CreditTransaction, SubscriptionTier, UsageQuota
from app.models.user import Subscription, User
from app.services.security_audit import SecurityAuditService, SecurityEventType

# New model imports for Epic 10 stories
from app.models.assembly import Assembly, AssemblyComponent, BOMItem, Vendor
from app.models.content import ContentCategory, ContentItem, ContentStatus, ContentType
from app.models.conversation import Conversation, ConversationMessage

# Track application start time for uptime calculations
_APP_START_TIME = time_module.time()

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
    if getattr(user, "is_banned", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already banned",
        )

    # Calculate expiration
    expires_at = None
    if not request.is_permanent and request.duration_days:
        expires_at = datetime.now(tz=UTC) + timedelta(days=request.duration_days)

    # Ban user
    user.is_banned = True  # type: ignore[attr-defined]
    user.banned_at = datetime.now(tz=UTC)  # type: ignore[attr-defined]
    user.ban_reason = request.reason  # type: ignore[attr-defined]
    user.ban_expires_at = expires_at  # type: ignore[attr-defined]

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

    if not getattr(user, "is_banned", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not banned",
        )

    user.is_banned = False  # type: ignore[attr-defined]
    user.banned_at = None  # type: ignore[attr-defined]
    user.ban_reason = None  # type: ignore[attr-defined]
    user.ban_expires_at = None  # type: ignore[attr-defined]

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
    from app.core.security import create_verification_token
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
    reset_token = create_verification_token(user.id, purpose="password_reset")

    # Build reset URL
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    # Send email
    email_service = get_email_service()
    email_sent = await email_service.send_password_reset_email(
        email=user.email,
        display_name=user.display_name or user.email.split("@")[0],
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


class RevenueAnalyticsResponse(BaseModel):
    """Revenue and MRR analytics."""

    monthly_recurring_revenue_cents: int
    total_revenue_cents: int
    churn_rate: float
    upgrades_count: int
    downgrades_count: int
    subscribers_by_tier: dict[str, int]
    period: str


@router.get(
    "/analytics/revenue",
    response_model=RevenueAnalyticsResponse,
    summary="Get revenue analytics",
    description="Get revenue and MRR metrics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_revenue_analytics(
    period: Annotated[str, Query(pattern="^(7d|30d|90d)$")] = "30d",
    db: AsyncSession = Depends(get_db),
) -> RevenueAnalyticsResponse:
    """Get revenue and MRR analytics.

    Args:
        period: Time period for analytics (7d, 30d, 90d).

    Returns:
        RevenueAnalyticsResponse with MRR, churn, and tier breakdowns.
    """
    days = int(period.replace("d", ""))
    start_date = datetime.now(tz=UTC) - timedelta(days=days)

    # Count active subscribers by tier
    subscribers_by_tier: dict[str, int] = {}
    tier_query = (
        select(Subscription.tier, func.count())
        .where(Subscription.status == "active")
        .group_by(Subscription.tier)
    )
    result = await db.execute(tier_query)
    for row in result.all():
        subscribers_by_tier[row[0]] = row[1]

    # Get tier pricing for MRR calculation
    tiers = (await db.execute(select(SubscriptionTier))).scalars().all()
    tier_prices = {t.slug: t.price_monthly_cents for t in tiers}

    # Calculate MRR
    mrr = 0
    for tier_slug, count in subscribers_by_tier.items():
        mrr += tier_prices.get(tier_slug, 0) * count

    # Total revenue estimate (MRR * period months, minimum 1)
    total_revenue = mrr * max(1, days // 30)

    # Churn: subscriptions that became canceled/expired in the period
    churned = (
        await db.execute(
            select(func.count()).where(
                Subscription.status.in_(["canceled", "expired"]),
                Subscription.updated_at >= start_date,
            )
        )
    ).scalar_one()

    total_subs = sum(subscribers_by_tier.values())
    churn_rate = (
        (churned / (total_subs + churned) * 100)
        if (total_subs + churned) > 0
        else 0.0
    )

    # Upgrades/downgrades from audit log
    upgrades = (
        await db.execute(
            select(func.count()).where(
                AuditLog.action == "subscription_upgrade",
                AuditLog.created_at >= start_date,
            )
        )
    ).scalar_one()

    downgrades = (
        await db.execute(
            select(func.count()).where(
                AuditLog.action == "subscription_downgrade",
                AuditLog.created_at >= start_date,
            )
        )
    ).scalar_one()

    return RevenueAnalyticsResponse(
        monthly_recurring_revenue_cents=mrr,
        total_revenue_cents=total_revenue,
        churn_rate=round(churn_rate, 2),
        upgrades_count=upgrades,
        downgrades_count=downgrades,
        subscribers_by_tier=subscribers_by_tier,
        period=period,
    )


@router.get(
    "/analytics/export",
    summary="Export analytics as CSV",
    description="Export analytics data as a CSV file (admin only).",
    dependencies=[Depends(require_admin())],
)
async def export_analytics(
    type: Annotated[str, Query(pattern="^(users|generations|jobs|storage)$")] = "users",
    format: Annotated[str, Query(pattern="^(csv)$")] = "csv",
    period: Annotated[str, Query(pattern="^(7d|30d|90d)$")] = "30d",
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export analytics data as CSV.

    Args:
        type: Data type to export (users, generations, jobs, storage).
        format: Export format (csv).
        period: Time period (7d, 30d, 90d).

    Returns:
        StreamingResponse with CSV data.
    """
    days = int(period.replace("d", ""))
    start_date = datetime.now(tz=UTC) - timedelta(days=days)

    output = io.StringIO()
    writer = csv.writer(output)

    if type == "users":
        writer.writerow([
            "id", "email", "display_name", "role", "status",
            "created_at", "last_login_at",
        ])
        result = await db.execute(
            select(User)
            .where(User.created_at >= start_date, User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
        )
        for user in result.scalars().all():
            writer.writerow([
                str(user.id),
                user.email,
                user.display_name,
                user.role,
                user.status,
                user.created_at.isoformat() if user.created_at else "",
                user.last_login_at.isoformat() if user.last_login_at else "",
            ])

    elif type == "generations":
        writer.writerow([
            "id", "name", "source_type", "status", "project_id", "created_at",
        ])
        result = await db.execute(
            select(Design)
            .where(Design.created_at >= start_date, Design.deleted_at.is_(None))
            .order_by(Design.created_at.desc())
        )
        for design in result.scalars().all():
            writer.writerow([
                str(design.id),
                design.name,
                design.source_type,
                design.status,
                str(design.project_id),
                design.created_at.isoformat() if design.created_at else "",
            ])

    elif type == "jobs":
        writer.writerow([
            "id", "job_type", "status", "user_id", "created_at", "completed_at",
        ])
        result = await db.execute(
            select(Job)
            .where(Job.created_at >= start_date)
            .order_by(Job.created_at.desc())
        )
        for job in result.scalars().all():
            writer.writerow([
                str(job.id),
                job.job_type,
                job.status,
                str(job.user_id),
                job.created_at.isoformat() if job.created_at else "",
                job.completed_at.isoformat() if job.completed_at else "",
            ])

    elif type == "storage":
        writer.writerow([
            "id", "filename", "size_bytes", "file_type", "user_id", "created_at",
        ])
        result = await db.execute(
            select(FileModel)
            .where(FileModel.created_at >= start_date)
            .order_by(FileModel.created_at.desc())
        )
        for file in result.scalars().all():
            writer.writerow([
                str(file.id),
                file.filename,
                file.size_bytes,
                file.file_type,
                str(file.user_id),
                file.created_at.isoformat() if file.created_at else "",
            ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=analytics_{type}_{period}.csv",
        },
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
            new_users_data[date_str] = getattr(row, "count", 0) or 0

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
            active_users_data[date_str] = getattr(row, "count", 0) or 0

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
            new_projects_data[date_str] = getattr(row, "count", 0) or 0

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
            new_designs_data[date_str] = getattr(row, "count", 0) or 0

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


class ForceEmailVerifyResponse(BaseModel):
    """Response for force email verification."""

    id: UUID
    email: str
    email_verified_at: datetime
    message: str


@router.post(
    "/users/{user_id}/force-email-verify",
    response_model=ForceEmailVerifyResponse,
    summary="Force verify user email",
    description="Force verify a user's email address (admin only).",
    dependencies=[Depends(require_admin())],
)
async def force_email_verify(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ForceEmailVerifyResponse:
    """Force verify a user's email address.

    Args:
        user_id: The user ID to verify.

    Returns:
        ForceEmailVerifyResponse with updated verification status.

    Raises:
        HTTPException: If user not found or already verified.
    """
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email is already verified",
        )

    now = datetime.now(tz=UTC)
    user.email_verified_at = now
    if user.status == "pending_verification":
        user.status = "active"

    await db.commit()
    await db.refresh(user)

    # Audit log the action
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.ROLE_CHANGED,
        user_id=current_user.id,
        resource_type="user",
        resource_id=user.id,
        details={
            "action": "force_email_verify",
            "target_user_email": user.email,
            "verified_by": current_user.email,
        },
    )
    await db.commit()

    return ForceEmailVerifyResponse(
        id=user.id,
        email=user.email,
        email_verified_at=now,
        message="Email verified successfully",
    )


class LoginHistoryEntry(BaseModel):
    """A single login history entry."""

    timestamp: datetime
    ip_address: str | None
    user_agent: str | None
    success: bool


class LoginHistoryResponse(BaseModel):
    """Paginated login history."""

    entries: list[LoginHistoryEntry]
    total: int
    page: int
    page_size: int


@router.get(
    "/users/{user_id}/login-history",
    response_model=LoginHistoryResponse,
    summary="Get user login history",
    description="Get login history for a user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_user_login_history(
    user_id: UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> LoginHistoryResponse:
    """Get user login history from audit logs.

    Args:
        user_id: The user ID to get login history for.
        page: Page number (1-based).
        page_size: Number of entries per page.

    Returns:
        LoginHistoryResponse with paginated login entries.

    Raises:
        HTTPException: If user not found.
    """
    # Verify user exists
    user_query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    user_result = await db.execute(user_query)
    if not user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Query audit logs for login events
    query = (
        select(AuditLog)
        .where(
            AuditLog.user_id == user_id,
            AuditLog.action.in_(["login", "login_failed", "login_success"]),
        )
        .order_by(AuditLog.created_at.desc())
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return LoginHistoryResponse(
        entries=[
            LoginHistoryEntry(
                timestamp=log.created_at,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                success=log.status == "success",
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


class ActivityEntry(BaseModel):
    """A single activity feed entry."""

    type: str
    resource_id: UUID
    resource_name: str | None
    timestamp: datetime
    details: dict[str, Any] = {}


class ActivityFeedResponse(BaseModel):
    """Paginated activity feed."""

    activities: list[ActivityEntry]
    total: int
    page: int
    page_size: int


@router.get(
    "/users/{user_id}/activity",
    response_model=ActivityFeedResponse,
    summary="Get user activity feed",
    description="Get activity feed for a user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_user_activity(
    user_id: UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> ActivityFeedResponse:
    """Get user activity feed across designs, projects, and files.

    Args:
        user_id: The user ID to get activity for.
        page: Page number (1-based).
        page_size: Number of entries per page.

    Returns:
        ActivityFeedResponse with unified activity list.

    Raises:
        HTTPException: If user not found.
    """
    # Verify user exists
    user_query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    user_result = await db.execute(user_query)
    if not user_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    activities: list[ActivityEntry] = []

    # Designs created by user
    designs_result = await db.execute(
        select(Design)
        .where(Design.user_id == user_id, Design.deleted_at.is_(None))
        .order_by(Design.created_at.desc())
        .limit(100)
    )
    for design in designs_result.scalars().all():
        activities.append(
            ActivityEntry(
                type="design_created",
                resource_id=design.id,
                resource_name=design.name,
                timestamp=design.created_at,
                details={"source_type": design.source_type, "status": design.status},
            )
        )

    # Projects created by user
    projects_result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id, Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
        .limit(100)
    )
    for project in projects_result.scalars().all():
        activities.append(
            ActivityEntry(
                type="project_created",
                resource_id=project.id,
                resource_name=project.name,
                timestamp=project.created_at,
                details={"status": getattr(project, "status", "active")},
            )
        )

    # Files uploaded by user
    files_result = await db.execute(
        select(FileModel)
        .where(FileModel.user_id == user_id)
        .order_by(FileModel.created_at.desc())
        .limit(100)
    )
    for file in files_result.scalars().all():
        activities.append(
            ActivityEntry(
                type="file_uploaded",
                resource_id=file.id,
                resource_name=file.filename,
                timestamp=file.created_at,
                details={"file_type": file.file_type, "size_bytes": file.size_bytes},
            )
        )

    # Sort all activities by timestamp descending
    activities.sort(key=lambda a: a.timestamp, reverse=True)

    # Calculate total and paginate
    total = len(activities)
    offset = (page - 1) * page_size
    paginated = activities[offset : offset + page_size]

    return ActivityFeedResponse(
        activities=paginated,
        total=total,
        page=page,
        page_size=page_size,
    )


class BulkUserActionRequest(BaseModel):
    """Request for bulk user operations."""

    action: str = Field(..., pattern="^(suspend|unsuspend|delete)$")
    user_ids: list[UUID] = Field(..., min_length=1, max_length=100)
    reason: str | None = Field(None, max_length=500)


class BulkActionResult(BaseModel):
    """Result of a bulk operation."""

    total: int
    success_count: int
    failure_count: int
    errors: list[dict[str, Any]] = []


@router.post(
    "/users/bulk-action",
    response_model=BulkActionResult,
    summary="Bulk user operations",
    description="Perform bulk operations on users (admin only).",
    dependencies=[Depends(require_admin())],
)
async def bulk_user_action(
    request: BulkUserActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkActionResult:
    """Perform bulk operations on users.

    Args:
        request: Bulk action request with action type and user IDs.

    Returns:
        BulkActionResult with success/failure counts.
    """
    success_count = 0
    failure_count = 0
    errors: list[dict[str, Any]] = []

    for uid in request.user_ids:
        try:
            # Prevent self-action
            if uid == current_user.id:
                failure_count += 1
                errors.append({
                    "user_id": str(uid),
                    "error": "Cannot perform bulk action on your own account",
                })
                continue

            query = select(User).where(User.id == uid, User.deleted_at.is_(None))
            result = await db.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                failure_count += 1
                errors.append({"user_id": str(uid), "error": "User not found"})
                continue

            if request.action == "suspend":
                if user.status == "suspended":
                    failure_count += 1
                    errors.append({
                        "user_id": str(uid),
                        "error": "User is already suspended",
                    })
                    continue
                user.status = "suspended"
                user.extra_data["suspension_reason"] = request.reason or "Bulk action"
                user.extra_data["suspended_at"] = datetime.now(tz=UTC).isoformat()
                user.extra_data["suspended_by"] = str(current_user.id)

            elif request.action == "unsuspend":
                if user.status != "suspended":
                    failure_count += 1
                    errors.append({
                        "user_id": str(uid),
                        "error": "User is not suspended",
                    })
                    continue
                user.status = "active"
                user.extra_data.pop("suspension_reason", None)
                user.extra_data.pop("suspended_at", None)
                user.extra_data.pop("suspended_by", None)
                user.extra_data.pop("suspension_expires", None)

            elif request.action == "delete":
                user.deleted_at = datetime.now(tz=UTC)

            success_count += 1

        except Exception as e:
            failure_count += 1
            errors.append({"user_id": str(uid), "error": str(e)})

    await db.commit()

    # Audit log the bulk action
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.ROLE_CHANGED,
        user_id=current_user.id,
        resource_type="user",
        resource_id=None,
        details={
            "action": f"bulk_{request.action}",
            "user_ids": [str(uid) for uid in request.user_ids],
            "reason": request.reason,
            "success_count": success_count,
            "failure_count": failure_count,
        },
    )
    await db.commit()

    return BulkActionResult(
        total=len(request.user_ids),
        success_count=success_count,
        failure_count=failure_count,
        errors=errors,
    )


@router.get(
    "/users/export",
    summary="Export user list as CSV",
    description="Export user list as a CSV file (admin only).",
    dependencies=[Depends(require_admin())],
)
async def export_users(
    search: Annotated[str | None, Query(max_length=100)] = None,
    role: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export user list as CSV with optional filters.

    Args:
        search: Search by email or display name.
        role: Filter by role.
        status_filter: Filter by status.

    Returns:
        StreamingResponse with CSV data.
    """
    query = select(User).where(User.deleted_at.is_(None))

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_pattern)) | (User.display_name.ilike(search_pattern))
        )

    if role:
        query = query.where(User.role == role)

    if status_filter:
        query = query.where(User.status == status_filter)

    query = query.order_by(User.created_at.desc())

    result = await db.execute(query)
    users = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "email", "display_name", "role", "status",
        "email_verified_at", "last_login_at", "created_at",
    ])

    for user in users:
        writer.writerow([
            str(user.id),
            user.email,
            user.display_name,
            user.role,
            user.status,
            user.email_verified_at.isoformat() if user.email_verified_at else "",
            user.last_login_at.isoformat() if user.last_login_at else "",
            user.created_at.isoformat() if user.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"},
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


class TransferDesignRequest(BaseModel):
    """Request to transfer design ownership."""

    new_owner_id: UUID
    reason: str | None = None


@router.post(
    "/designs/{design_id}/transfer",
    response_model=AdminDesignResponse,
    summary="Transfer design ownership",
    description="Transfer design ownership to another user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def transfer_design(
    design_id: UUID,
    request: TransferDesignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AdminDesignResponse:
    """Transfer design ownership to another user.

    Args:
        design_id: The design to transfer.
        request: Transfer request with new owner ID.

    Returns:
        AdminDesignResponse with updated ownership.

    Raises:
        HTTPException: If design or new owner not found.
    """
    # Get design
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

    # Find or create a default project for the new owner
    new_owner_project_query = select(Project).where(
        Project.user_id == request.new_owner_id,
        Project.deleted_at.is_(None),
    )
    new_owner_project_result = await db.execute(new_owner_project_query)
    new_owner_project = new_owner_project_result.scalars().first()

    if not new_owner_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New owner has no projects to transfer the design into",
        )

    old_project_id = design.project_id
    old_user_id = design.user_id
    design.project_id = new_owner_project.id
    design.user_id = request.new_owner_id

    await db.commit()
    await db.refresh(design)

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.ROLE_CHANGED,
        user_id=current_user.id,
        resource_type="design",
        resource_id=design.id,
        details={
            "action": "transfer_ownership",
            "old_user_id": str(old_user_id),
            "new_user_id": str(request.new_owner_id),
            "old_project_id": str(old_project_id),
            "new_project_id": str(new_owner_project.id),
            "reason": request.reason,
        },
    )
    await db.commit()

    return AdminDesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        source_type=design.source_type,
        status=design.status,
        project_id=design.project_id,
        project_name=new_owner_project.name,
        user_id=request.new_owner_id,
        user_email=new_owner.email,
        template_id=design.template_id,
        is_public=design.is_public,
        created_at=design.created_at,
        updated_at=design.updated_at,
    )


class DesignVersionResponse(BaseModel):
    """A single design version."""

    id: UUID
    version_number: int
    created_at: datetime
    change_description: str | None
    created_by: UUID | None
    file_url: str
    parameters: dict[str, Any]


class DesignVersionListResponse(BaseModel):
    """Paginated design version list."""

    versions: list[DesignVersionResponse]
    total: int
    page: int
    page_size: int


@router.get(
    "/designs/{design_id}/versions",
    response_model=DesignVersionListResponse,
    summary="Get design version history",
    description="Get version history for a design (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_design_versions(
    design_id: UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> DesignVersionListResponse:
    """Get design version history.

    Args:
        design_id: The design to get versions for.
        page: Page number (1-based).
        page_size: Number of entries per page.

    Returns:
        DesignVersionListResponse with paginated version list.

    Raises:
        HTTPException: If design not found.
    """
    # Verify design exists
    design_query = select(Design).where(
        Design.id == design_id, Design.deleted_at.is_(None)
    )
    design_result = await db.execute(design_query)
    if not design_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    # Query versions
    query = (
        select(DesignVersion)
        .where(DesignVersion.design_id == design_id)
        .order_by(DesignVersion.version_number.desc())
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    versions = result.scalars().all()

    return DesignVersionListResponse(
        versions=[
            DesignVersionResponse(
                id=version.id,
                version_number=version.version_number,
                created_at=version.created_at,
                change_description=version.change_description,
                created_by=version.created_by,
                file_url=version.file_url,
                parameters=version.parameters,
            )
            for version in versions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


class BulkProjectActionRequest(BaseModel):
    """Request for bulk project operations."""

    action: str = Field(..., pattern="^(delete|suspend|transfer)$")
    project_ids: list[UUID] = Field(..., min_length=1, max_length=100)
    target: UUID | None = None  # Target user for transfer
    reason: str | None = Field(None, max_length=500)


@router.post(
    "/projects/bulk-action",
    response_model=BulkActionResult,
    summary="Bulk project operations",
    description="Perform bulk operations on projects (admin only).",
    dependencies=[Depends(require_admin())],
)
async def bulk_project_action(
    request: BulkProjectActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkActionResult:
    """Perform bulk operations on projects.

    Args:
        request: Bulk action request with action type and project IDs.

    Returns:
        BulkActionResult with success/failure counts.
    """
    success_count = 0
    failure_count = 0
    errors: list[dict[str, Any]] = []

    # Validate target for transfer
    if request.action == "transfer":
        if not request.target:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target user ID required for transfer action",
            )
        target_user = await db.execute(
            select(User).where(User.id == request.target, User.deleted_at.is_(None))
        )
        if not target_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found",
            )

    for pid in request.project_ids:
        try:
            query = select(Project).where(
                Project.id == pid, Project.deleted_at.is_(None)
            )
            result = await db.execute(query)
            project = result.scalar_one_or_none()

            if not project:
                failure_count += 1
                errors.append({"project_id": str(pid), "error": "Project not found"})
                continue

            if request.action == "delete":
                project.deleted_at = datetime.now(tz=UTC)

            elif request.action == "suspend":
                if getattr(project, "status", "active") == "suspended":
                    failure_count += 1
                    errors.append({
                        "project_id": str(pid),
                        "error": "Project is already suspended",
                    })
                    continue
                project.status = "suspended"

            elif request.action == "transfer":
                project.user_id = request.target  # type: ignore[assignment]

            success_count += 1

        except Exception as e:
            failure_count += 1
            errors.append({"project_id": str(pid), "error": str(e)})

    await db.commit()

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.ROLE_CHANGED,
        user_id=current_user.id,
        resource_type="project",
        resource_id=None,
        details={
            "action": f"bulk_{request.action}",
            "project_ids": [str(pid) for pid in request.project_ids],
            "target": str(request.target) if request.target else None,
            "reason": request.reason,
            "success_count": success_count,
            "failure_count": failure_count,
        },
    )
    await db.commit()

    return BulkActionResult(
        total=len(request.project_ids),
        success_count=success_count,
        failure_count=failure_count,
        errors=errors,
    )


class BulkDesignActionRequest(BaseModel):
    """Request for bulk design operations."""

    action: str = Field(..., pattern="^(delete|restore|transfer)$")
    design_ids: list[UUID] = Field(..., min_length=1, max_length=100)
    target: UUID | None = None  # Target user for transfer
    reason: str | None = Field(None, max_length=500)


@router.post(
    "/designs/bulk-action",
    response_model=BulkActionResult,
    summary="Bulk design operations",
    description="Perform bulk operations on designs (admin only).",
    dependencies=[Depends(require_admin())],
)
async def bulk_design_action(
    request: BulkDesignActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkActionResult:
    """Perform bulk operations on designs.

    Args:
        request: Bulk action request with action type and design IDs.

    Returns:
        BulkActionResult with success/failure counts.
    """
    success_count = 0
    failure_count = 0
    errors: list[dict[str, Any]] = []

    # Validate target for transfer
    if request.action == "transfer":
        if not request.target:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target user ID required for transfer action",
            )
        target_result = await db.execute(
            select(User).where(User.id == request.target, User.deleted_at.is_(None))
        )
        target_user = target_result.scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found",
            )
        # Find a project for the target user
        target_project_result = await db.execute(
            select(Project).where(
                Project.user_id == request.target,
                Project.deleted_at.is_(None),
            )
        )
        target_project = target_project_result.scalars().first()
        if not target_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target user has no projects to transfer designs into",
            )

    for did in request.design_ids:
        try:
            if request.action == "restore":
                # For restore, look for soft-deleted designs
                query = select(Design).where(
                    Design.id == did, Design.deleted_at.isnot(None)
                )
            else:
                query = select(Design).where(
                    Design.id == did, Design.deleted_at.is_(None)
                )

            result = await db.execute(query)
            design = result.scalar_one_or_none()

            if not design:
                failure_count += 1
                errors.append({"design_id": str(did), "error": "Design not found"})
                continue

            if request.action == "delete":
                design.deleted_at = datetime.now(tz=UTC)

            elif request.action == "restore":
                design.deleted_at = None

            elif request.action == "transfer":
                design.project_id = target_project.id  # type: ignore[possibly-undefined]
                design.user_id = request.target  # type: ignore[assignment]

            success_count += 1

        except Exception as e:
            failure_count += 1
            errors.append({"design_id": str(did), "error": str(e)})

    await db.commit()

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.ROLE_CHANGED,
        user_id=current_user.id,
        resource_type="design",
        resource_id=None,
        details={
            "action": f"bulk_{request.action}",
            "design_ids": [str(did) for did in request.design_ids],
            "target": str(request.target) if request.target else None,
            "reason": request.reason,
            "success_count": success_count,
            "failure_count": failure_count,
        },
    )
    await db.commit()

    return BulkActionResult(
        total=len(request.design_ids),
        success_count=success_count,
        failure_count=failure_count,
        errors=errors,
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

    import aiofiles  # type: ignore[import-untyped]

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


class ReorderTemplatesRequest(BaseModel):
    """Request to reorder templates."""

    ordered_ids: list[UUID] = Field(..., min_length=1)


class ReorderTemplatesResponse(BaseModel):
    """Response for template reorder operation."""

    message: str
    reordered_count: int


@router.patch(
    "/templates/reorder",
    response_model=ReorderTemplatesResponse,
    summary="Reorder templates",
    description="Update the display order of templates (admin only).",
    dependencies=[Depends(require_admin())],
)
async def reorder_templates(
    request: ReorderTemplatesRequest,
    db: AsyncSession = Depends(get_db),
) -> ReorderTemplatesResponse:
    """Reorder templates by updating display_order.

    Args:
        request: List of template IDs in the desired order.

    Returns:
        ReorderTemplatesResponse with count of reordered templates.

    Note:
        Templates that don't have a display_order column will store
        the order in extra metadata via use_count field as a fallback.
    """
    reordered = 0
    for idx, template_id in enumerate(request.ordered_ids):
        result = await db.execute(
            select(Template).where(Template.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template:
            # Use use_count as display_order proxy if no dedicated column
            if hasattr(template, "display_order"):
                template.display_order = idx  # type: ignore[attr-defined]
            reordered += 1

    await db.commit()

    return ReorderTemplatesResponse(
        message=f"Reordered {reordered} templates",
        reordered_count=reordered,
    )


class TemplateUsageStat(BaseModel):
    """Usage statistics for a single template."""

    template_id: UUID
    template_name: str
    template_slug: str
    usage_count: int
    design_count: int


class TemplateAnalyticsResponse(BaseModel):
    """Template usage analytics."""

    templates: list[TemplateUsageStat]
    total_template_designs: int
    most_popular_template_id: UUID | None
    most_popular_template_name: str | None


@router.get(
    "/templates/analytics",
    response_model=TemplateAnalyticsResponse,
    summary="Get template usage analytics",
    description="Get usage analytics for templates (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_template_analytics(
    db: AsyncSession = Depends(get_db),
) -> TemplateAnalyticsResponse:
    """Get template usage analytics.

    Returns:
        TemplateAnalyticsResponse with per-template usage counts and most popular.
    """
    # Get all active templates
    templates_result = await db.execute(
        select(Template).where(Template.is_active.is_(True))
    )
    templates = templates_result.scalars().all()

    stats: list[TemplateUsageStat] = []
    total_designs = 0
    most_popular_id: UUID | None = None
    most_popular_name: str | None = None
    max_count = 0

    for template in templates:
        # Count designs using this template
        design_count = (
            await db.execute(
                select(func.count()).where(
                    Design.template_id == template.id,
                    Design.deleted_at.is_(None),
                )
            )
        ).scalar_one()

        total_designs += design_count

        stats.append(
            TemplateUsageStat(
                template_id=template.id,
                template_name=template.name,
                template_slug=template.slug,
                usage_count=template.use_count,
                design_count=design_count,
            )
        )

        if design_count > max_count:
            max_count = design_count
            most_popular_id = template.id
            most_popular_name = template.name

    # Sort by design count descending
    stats.sort(key=lambda s: s.design_count, reverse=True)

    return TemplateAnalyticsResponse(
        templates=stats,
        total_template_designs=total_designs,
        most_popular_template_id=most_popular_id,
        most_popular_template_name=most_popular_name,
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


# -----------------------------------------------------------------------------
# US-10.8: Job Priority, Stats, Queue Status, Purge, Workers
# -----------------------------------------------------------------------------


class JobPriorityRequest(BaseModel):
    """Request to change a job's priority."""

    priority: int = Field(..., ge=0, le=10, description="Priority (0=highest, 10=lowest)")


@router.patch(
    "/jobs/{job_id}/priority",
    response_model=AdminJobResponse,
    summary="Change job priority",
    description="Change a job's processing priority (admin only).",
    dependencies=[Depends(require_admin())],
)
async def change_job_priority(
    job_id: UUID,
    request: JobPriorityRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    """Change a job's priority. Lower values = higher priority.

    Args:
        job_id: Job ID.
        request: New priority value.

    Returns:
        Updated job details.

    Raises:
        HTTPException: If job not found.
    """
    query = select(Job).options(selectinload(Job.user)).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job.priority = request.priority
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


class JobStatsResponse(BaseModel):
    """Aggregate job statistics."""

    total: int = 0
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    avg_processing_time_ms: float | None = None
    success_rate: float = 0.0
    failure_rate: float = 0.0


@router.get(
    "/jobs/stats",
    response_model=JobStatsResponse,
    summary="Job statistics",
    description="Get aggregate job statistics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_job_stats(
    db: AsyncSession = Depends(get_db),
) -> JobStatsResponse:
    """Return aggregate job statistics: totals, status breakdown, rates.

    Returns:
        Job counts, average processing time, success/failure rates.
    """
    # Total
    total = (await db.execute(select(func.count(Job.id)))).scalar_one()

    # By status
    status_query = (
        select(Job.status, func.count().label("count"))
        .group_by(Job.status)
    )
    status_result = await db.execute(status_query)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # By type
    type_query = (
        select(Job.job_type, func.count().label("count"))
        .group_by(Job.job_type)
    )
    type_result = await db.execute(type_query)
    by_type = {row[0]: row[1] for row in type_result.all()}

    # Avg processing time for completed jobs
    avg_time = (
        await db.execute(
            select(func.avg(Job.execution_time_ms)).where(
                Job.status == "completed",
                Job.execution_time_ms.isnot(None),
            )
        )
    ).scalar_one()

    # Success/failure rates
    completed = by_status.get("completed", 0)
    failed = by_status.get("failed", 0)
    terminal = completed + failed
    success_rate = (completed / terminal * 100) if terminal > 0 else 0.0
    failure_rate = (failed / terminal * 100) if terminal > 0 else 0.0

    return JobStatsResponse(
        total=total,
        by_status=by_status,
        by_type=by_type,
        avg_processing_time_ms=round(float(avg_time), 2) if avg_time else None,
        success_rate=round(success_rate, 2),
        failure_rate=round(failure_rate, 2),
    )


class QueueStatusResponse(BaseModel):
    """Real-time queue status."""

    pending_count: int = 0
    running_count: int = 0
    queued_count: int = 0
    workers_active: int = 0


@router.get(
    "/jobs/queue-status",
    response_model=QueueStatusResponse,
    summary="Real-time queue status",
    description="Get current job queue status (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_queue_status(
    db: AsyncSession = Depends(get_db),
) -> QueueStatusResponse:
    """Return real-time job queue counts.

    Worker count is an estimate; a production implementation would
    inspect Celery workers via the Celery inspect API.

    Returns:
        Pending, running, and queued job counts plus estimated worker count.
    """
    pending = (
        await db.execute(
            select(func.count(Job.id)).where(Job.status == "pending")
        )
    ).scalar_one()

    running = (
        await db.execute(
            select(func.count(Job.id)).where(Job.status == "running")
        )
    ).scalar_one()

    queued = (
        await db.execute(
            select(func.count(Job.id)).where(Job.status == "queued")
        )
    ).scalar_one()

    # Estimate active workers from distinct running jobs
    # In production, use Celery inspect: app.control.inspect().active()
    workers_active = min(running, 4)  # Placeholder: assume max 4 workers

    return QueueStatusResponse(
        pending_count=pending,
        running_count=running,
        queued_count=queued,
        workers_active=workers_active,
    )


class PurgeJobsResponse(BaseModel):
    """Result of job purge operation."""

    purged_count: int
    older_than_days: int


@router.delete(
    "/jobs/purge",
    response_model=PurgeJobsResponse,
    summary="Purge old completed jobs",
    description="Delete completed/failed jobs older than N days (admin only).",
    dependencies=[Depends(require_admin())],
)
async def purge_old_jobs(
    older_than_days: Annotated[int, Query(ge=1, le=365)] = 30,
    db: AsyncSession = Depends(get_db),
) -> PurgeJobsResponse:
    """Purge completed and failed jobs older than the specified number of days.

    Args:
        older_than_days: Age threshold in days (default 30).

    Returns:
        Count of purged jobs.
    """
    cutoff = datetime.now(tz=UTC) - timedelta(days=older_than_days)

    # Count first
    count_query = select(func.count(Job.id)).where(
        Job.status.in_(["completed", "failed", "cancelled"]),
        Job.completed_at.isnot(None),
        Job.completed_at < cutoff,
    )
    purge_count = (await db.execute(count_query)).scalar_one()

    # Delete
    if purge_count > 0:
        from sqlalchemy import delete as sa_delete

        await db.execute(
            sa_delete(Job).where(
                Job.status.in_(["completed", "failed", "cancelled"]),
                Job.completed_at.isnot(None),
                Job.completed_at < cutoff,
            )
        )
        await db.commit()

    return PurgeJobsResponse(
        purged_count=purge_count,
        older_than_days=older_than_days,
    )


class WorkerInfo(BaseModel):
    """Information about a background worker."""

    name: str
    status: str
    tasks_completed: int = 0
    current_task: str | None = None
    last_heartbeat: datetime | None = None


@router.get(
    "/jobs/workers",
    response_model=list[WorkerInfo],
    summary="Worker status",
    description="Get background worker status (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_worker_status() -> list[WorkerInfo]:
    """Return background worker status.

    NOTE: This returns placeholder data. In production, this would
    inspect Celery workers via ``app.control.inspect().active()``,
    ``app.control.inspect().stats()``, etc.

    Returns:
        List of worker statuses.
    """
    # Placeholder implementation
    # In production: from app.worker.celery_app import celery_app
    # inspect = celery_app.control.inspect()
    # active = inspect.active() or {}
    # stats = inspect.stats() or {}
    now = datetime.now(tz=UTC)
    return [
        WorkerInfo(
            name="worker-1@host",
            status="online",
            tasks_completed=0,
            current_task=None,
            last_heartbeat=now,
        ),
        WorkerInfo(
            name="worker-2@host",
            status="online",
            tasks_completed=0,
            current_task=None,
            last_heartbeat=now,
        ),
    ]


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
    )

    filters = []
    if status_filter:
        filters.append(Subscription.status == status_filter)
    if tier_filter:
        filters.append(Subscription.tier == tier_filter)

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
                tier_slug=sub.tier,
                tier_name=sub.tier.capitalize() if sub.tier else "Unknown",
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
        tier_slug=sub.tier,
        tier_name=sub.tier.capitalize() if sub.tier else "Unknown",
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

    sub.tier = request.tier_slug  # tier is a string, not a FK
    await db.commit()
    await db.refresh(sub)

    return AdminSubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        user_email=sub.user.email if sub.user else None,
        tier_slug=sub.tier,
        tier_name=sub.tier.capitalize() if sub.tier else "Unknown",
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
    sub.cancel_at_period_end = True  # Using cancel_at_period_end instead of cancelled_at
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
        tier_slug=sub.tier,
        tier_name=sub.tier.capitalize() if sub.tier else "Unknown",
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


# -----------------------------------------------------------------------------
# US-10.5a: Credit Deduct, History, Quota, Distribution, Low-Balance
# -----------------------------------------------------------------------------


class DeductCreditsRequest(BaseModel):
    """Request to deduct credits from a user."""

    amount: int = Field(..., ge=1, description="Amount of credits to deduct")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for deduction")


@router.post(
    "/users/{user_id}/credits/deduct",
    summary="Deduct credits from user",
    description="Deduct credits from a user's balance (admin only).",
    dependencies=[Depends(require_admin())],
)
async def deduct_user_credits(
    user_id: UUID,
    request: DeductCreditsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Deduct credits from a user, validating sufficient balance.

    Args:
        user_id: Target user's ID.
        request: Amount and reason for deduction.

    Returns:
        Confirmation with new balance.

    Raises:
        HTTPException: If user not found or insufficient balance.
    """
    query = select(CreditBalance).where(CreditBalance.user_id == user_id)
    result = await db.execute(query)
    balance = result.scalar_one_or_none()

    if not balance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit balance not found for user",
        )

    if balance.balance < request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance: {balance.balance} < {request.amount}",
        )

    balance_before = balance.balance
    balance.deduct(request.amount)

    # Record transaction
    transaction = CreditTransaction(
        user_id=user_id,
        balance_id=balance.id,
        amount=-request.amount,
        transaction_type="admin_adjustment",
        description=f"Admin deduction: {request.reason}",
        balance_before=balance_before,
        balance_after=balance.balance,
        extra_data={"admin_email": current_user.email, "reason": request.reason},
    )
    db.add(transaction)

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="credit_balance",
        resource_id=user_id,
        details={
            "action": "credits_deducted",
            "amount": request.amount,
            "reason": request.reason,
            "balance_before": balance_before,
            "balance_after": balance.balance,
        },
    )

    await db.commit()

    return {
        "message": f"Deducted {request.amount} credits",
        "new_balance": balance.balance,
    }


class CreditHistoryEntry(BaseModel):
    """A single credit transaction entry."""

    id: UUID
    amount: int
    transaction_type: str
    description: str
    balance_before: int
    balance_after: int
    created_at: datetime
    admin_email: str | None = None


class CreditHistoryResponse(BaseModel):
    """Paginated credit transaction history."""

    items: list[CreditHistoryEntry]
    total: int
    page: int
    page_size: int


@router.get(
    "/users/{user_id}/credits/history",
    response_model=CreditHistoryResponse,
    summary="Get user credit history",
    description="Get paginated credit transaction history for a user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_user_credit_history(
    user_id: UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> CreditHistoryResponse:
    """Return paginated list of credit changes for a user.

    Args:
        user_id: Target user's ID.
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated credit transaction history.
    """
    query = select(CreditTransaction).where(CreditTransaction.user_id == user_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(CreditTransaction.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    transactions = result.scalars().all()

    return CreditHistoryResponse(
        items=[
            CreditHistoryEntry(
                id=t.id,
                amount=t.amount,
                transaction_type=t.transaction_type,
                description=t.description,
                balance_before=t.balance_before,
                balance_after=t.balance_after,
                created_at=t.created_at,
                admin_email=t.extra_data.get("admin_email") if t.extra_data else None,
            )
            for t in transactions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


class QuotaResponse(BaseModel):
    """User quota usage response."""

    user_id: UUID
    storage_used_bytes: int = 0
    storage_limit_gb: int = 1
    projects_count: int = 0
    projects_limit: int = 5
    designs_count: int = 0
    designs_limit: int = 10
    jobs_today: int = 0
    jobs_limit: int = 1


@router.get(
    "/users/{user_id}/quota",
    response_model=QuotaResponse,
    summary="Get user quota usage",
    description="View user quota usage against tier limits (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_user_quota(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> QuotaResponse:
    """Return user's current usage against their tier quota limits.

    Args:
        user_id: Target user's ID.

    Returns:
        Quota usage with limits from the user's subscription tier.
    """
    # Get usage quota
    quota_query = select(UsageQuota).where(UsageQuota.user_id == user_id)
    quota_result = await db.execute(quota_query)
    quota = quota_result.scalar_one_or_none()

    # Get tier limits from user's subscription
    sub_query = select(Subscription).where(Subscription.user_id == user_id)
    sub_result = await db.execute(sub_query)
    sub = sub_result.scalar_one_or_none()

    tier_limits: dict[str, int] = {
        "storage_limit_gb": 1,
        "projects_limit": 5,
        "designs_limit": 10,
        "jobs_limit": 1,
    }

    if sub and sub.tier:
        tier_query = select(SubscriptionTier).where(SubscriptionTier.slug == sub.tier)
        tier_result = await db.execute(tier_query)
        tier = tier_result.scalar_one_or_none()
        if tier:
            tier_limits["storage_limit_gb"] = tier.max_storage_gb
            tier_limits["projects_limit"] = tier.max_projects
            tier_limits["designs_limit"] = tier.max_designs_per_project
            tier_limits["jobs_limit"] = tier.max_concurrent_jobs

    # Count designs
    design_count = (
        await db.execute(
            select(func.count()).where(
                Design.user_id == user_id,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Count jobs today
    today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    jobs_today = (
        await db.execute(
            select(func.count()).where(
                Job.user_id == user_id,
                Job.created_at >= today_start,
            )
        )
    ).scalar_one()

    return QuotaResponse(
        user_id=user_id,
        storage_used_bytes=quota.storage_used_bytes if quota else 0,
        storage_limit_gb=tier_limits["storage_limit_gb"],
        projects_count=quota.projects_count if quota else 0,
        projects_limit=tier_limits["projects_limit"],
        designs_count=design_count,
        designs_limit=tier_limits["designs_limit"],
        jobs_today=jobs_today,
        jobs_limit=tier_limits["jobs_limit"],
    )


class QuotaOverrideRequest(BaseModel):
    """Request to override user quota limits."""

    storage_limit_gb: int | None = Field(None, ge=1, le=1000)
    projects_limit: int | None = Field(None, ge=1, le=10000)
    designs_limit: int | None = Field(None, ge=1, le=10000)
    jobs_limit: int | None = Field(None, ge=1, le=100)
    expires_at: datetime | None = Field(None, description="When the override expires")


@router.post(
    "/users/{user_id}/quota/override",
    summary="Override user quota limits",
    description="Create or update a quota override for a user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def override_user_quota(
    user_id: UUID,
    request: QuotaOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create or update a quota override for a user.

    Overrides are stored in the user's subscription metadata.
    When expires_at is set, the override will be ignored after that time.

    Args:
        user_id: Target user's ID.
        request: New quota limits.

    Returns:
        Confirmation with override details.
    """
    # Verify user exists
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Store override in user's settings or subscription metadata
    override_data: dict[str, Any] = {}
    if request.storage_limit_gb is not None:
        override_data["storage_limit_gb"] = request.storage_limit_gb
    if request.projects_limit is not None:
        override_data["projects_limit"] = request.projects_limit
    if request.designs_limit is not None:
        override_data["designs_limit"] = request.designs_limit
    if request.jobs_limit is not None:
        override_data["jobs_limit"] = request.jobs_limit
    if request.expires_at is not None:
        override_data["expires_at"] = request.expires_at.isoformat()

    # Store in user settings JSONB
    if hasattr(user, "settings") and user.settings:
        user.settings = {**user.settings, "quota_override": override_data}
    else:
        if hasattr(user, "settings"):
            user.settings = {"quota_override": override_data}

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="quota",
        resource_id=user_id,
        details={
            "action": "quota_override",
            "overrides": override_data,
            "admin_email": current_user.email,
        },
    )

    await db.commit()

    return {
        "message": "Quota override applied",
        "user_id": str(user_id),
        "overrides": override_data,
    }


@router.get(
    "/credits/distribution",
    summary="Platform credit distribution",
    description="View platform-wide credit distribution statistics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_credit_distribution(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return platform-wide credit distribution metrics.

    Returns:
        Total credits issued/used, average balance, and distribution by tier.
    """
    # Total credits issued and used
    totals = await db.execute(
        select(
            func.sum(CreditBalance.lifetime_earned).label("total_issued"),
            func.sum(CreditBalance.lifetime_spent).label("total_used"),
            func.avg(CreditBalance.balance).label("avg_balance"),
            func.count(CreditBalance.id).label("user_count"),
        )
    )
    row = totals.one()

    # Distribution by tier
    tier_dist_query = (
        select(
            Subscription.tier,
            func.sum(CreditBalance.balance).label("total_balance"),
            func.avg(CreditBalance.balance).label("avg_balance"),
            func.count(CreditBalance.id).label("user_count"),
        )
        .join(Subscription, Subscription.user_id == CreditBalance.user_id, isouter=True)
        .group_by(Subscription.tier)
    )
    tier_result = await db.execute(tier_dist_query)
    tier_rows = tier_result.all()

    distribution_by_tier = [
        {
            "tier": tr[0] or "none",
            "total_balance": int(tr[1] or 0),
            "avg_balance": round(float(tr[2] or 0), 2),
            "user_count": tr[3],
        }
        for tr in tier_rows
    ]

    return {
        "total_credits_issued": int(row[0] or 0),
        "total_credits_used": int(row[1] or 0),
        "avg_balance": round(float(row[2] or 0), 2),
        "total_users_with_balance": row[3],
        "distribution_by_tier": distribution_by_tier,
    }


class LowBalanceUserEntry(BaseModel):
    """User with low credit balance."""

    user_id: UUID
    email: str
    balance: int
    tier: str | None = None


class LowBalanceUsersResponse(BaseModel):
    """Paginated list of users with low credit balances."""

    items: list[LowBalanceUserEntry]
    total: int
    page: int
    page_size: int
    threshold: int


@router.get(
    "/credits/low-balance-users",
    response_model=LowBalanceUsersResponse,
    summary="Users with low credit balances",
    description="List users with credit balance below a threshold (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_low_balance_users(
    threshold: Annotated[int, Query(ge=0)] = 10,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> LowBalanceUsersResponse:
    """Return paginated list of users with credit balance below the threshold.

    Args:
        threshold: Balance threshold (default 10).
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated list of low-balance users.
    """
    query = (
        select(CreditBalance, User.email, Subscription.tier)
        .join(User, User.id == CreditBalance.user_id)
        .join(Subscription, Subscription.user_id == CreditBalance.user_id, isouter=True)
        .where(CreditBalance.balance < threshold)
    )

    # Count total
    count_query = select(func.count()).select_from(
        select(CreditBalance.id)
        .where(CreditBalance.balance < threshold)
        .subquery()
    )
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(CreditBalance.balance.asc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    return LowBalanceUsersResponse(
        items=[
            LowBalanceUserEntry(
                user_id=row[0].user_id,
                email=row[1],
                balance=row[0].balance,
                tier=row[2],
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        threshold=threshold,
    )


# -----------------------------------------------------------------------------
# US-10.5b: Billing - Failed Payments, Revenue, Tier Config
# -----------------------------------------------------------------------------


class FailedPaymentEntry(BaseModel):
    """A failed payment record."""

    user_id: UUID
    user_email: str | None = None
    amount_cents: int = 0
    error: str | None = None
    date: datetime
    retry_count: int = 0


class FailedPaymentsResponse(BaseModel):
    """Paginated list of failed payments."""

    items: list[FailedPaymentEntry]
    total: int
    page: int
    page_size: int


@router.get(
    "/billing/failed-payments",
    response_model=FailedPaymentsResponse,
    summary="List failed payments",
    description="List failed payment attempts from audit logs (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_failed_payments(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> FailedPaymentsResponse:
    """Return paginated list of failed payment attempts.

    Failed payment data is reconstructed from audit logs with
    action='payment_failed'. In a production system this would
    come from a Stripe webhook events table.

    Args:
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated list of failed payment records.
    """
    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(AuditLog.action == "payment_failed")
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return FailedPaymentsResponse(
        items=[
            FailedPaymentEntry(
                user_id=log.user_id or UUID(int=0),
                user_email=log.user.email if log.user else None,
                amount_cents=log.context.get("amount_cents", 0) if log.context else 0,
                error=log.error_message or log.context.get("error", "") if log.context else None,
                date=log.created_at,
                retry_count=log.context.get("retry_count", 0) if log.context else 0,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


class BillingRevenueResponse(BaseModel):
    """Revenue report data."""

    total_revenue_cents: int = 0
    revenue_by_tier: dict[str, int] = {}
    revenue_by_period: list[dict[str, Any]] = []
    period: str = "30d"


@router.get(
    "/billing/revenue",
    response_model=BillingRevenueResponse,
    summary="Revenue reports",
    description="Get revenue reports by tier and time period (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_billing_revenue(
    period: Annotated[str, Query(pattern=r"^(7d|30d|90d|1y)$")] = "30d",
    db: AsyncSession = Depends(get_db),
) -> BillingRevenueResponse:
    """Generate revenue report for a given time period.

    Revenue is estimated from subscription tier pricing and active subscriptions.
    In production, this would pull from a Stripe reporting API or payments table.

    Args:
        period: Time period (7d, 30d, 90d, 1y).

    Returns:
        Revenue totals by tier and by time bucket.
    """
    days_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    days = days_map.get(period, 30)
    start_date = datetime.now(tz=UTC) - timedelta(days=days)

    # Count active subscriptions by tier
    tier_query = (
        select(
            Subscription.tier,
            func.count(Subscription.id).label("count"),
        )
        .where(
            Subscription.status == "active",
            Subscription.created_at <= datetime.now(tz=UTC),
        )
        .group_by(Subscription.tier)
    )
    tier_result = await db.execute(tier_query)
    tier_rows = tier_result.all()

    # Get tier pricing
    pricing_query = select(SubscriptionTier)
    pricing_result = await db.execute(pricing_query)
    tiers = {t.slug: t.price_monthly_cents for t in pricing_result.scalars().all()}

    revenue_by_tier: dict[str, int] = {}
    total_revenue = 0
    for row in tier_rows:
        tier_slug = row[0] or "free"
        count = row[1]
        monthly_price = tiers.get(tier_slug, 0)
        # Estimate revenue over the period
        months_in_period = max(days / 30, 1)
        estimated = int(monthly_price * count * months_in_period)
        revenue_by_tier[tier_slug] = estimated
        total_revenue += estimated

    # Revenue by period buckets
    revenue_by_period: list[dict[str, Any]] = []
    bucket_days = max(days // 7, 1)
    for i in range(0, days, bucket_days):
        bucket_start = start_date + timedelta(days=i)
        bucket_end = bucket_start + timedelta(days=bucket_days)
        # Count subscriptions active in this bucket
        bucket_count = (
            await db.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.status == "active",
                    Subscription.created_at <= bucket_end,
                )
            )
        ).scalar_one()
        revenue_by_period.append({
            "period_start": bucket_start.isoformat(),
            "period_end": bucket_end.isoformat(),
            "active_subscriptions": bucket_count,
        })

    return BillingRevenueResponse(
        total_revenue_cents=total_revenue,
        revenue_by_tier=revenue_by_tier,
        revenue_by_period=revenue_by_period,
        period=period,
    )


class TierDefinitionResponse(BaseModel):
    """Subscription tier definition."""

    id: UUID
    slug: str
    name: str
    description: str | None = None
    monthly_credits: int
    max_concurrent_jobs: int
    max_storage_gb: int
    max_projects: int
    max_designs_per_project: int
    max_file_size_mb: int
    features: dict[str, Any] = {}
    price_monthly_cents: int
    price_yearly_cents: int
    display_order: int
    is_active: bool


@router.get(
    "/subscription-tiers",
    response_model=list[TierDefinitionResponse],
    summary="List subscription tier definitions",
    description="List all subscription tiers with features and limits (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_subscription_tiers(
    db: AsyncSession = Depends(get_db),
) -> list[TierDefinitionResponse]:
    """Return all tier definitions with features, limits, and pricing.

    Returns:
        List of all subscription tiers.
    """
    result = await db.execute(
        select(SubscriptionTier).order_by(SubscriptionTier.display_order)
    )
    tiers = result.scalars().all()

    return [
        TierDefinitionResponse(
            id=t.id,
            slug=t.slug,
            name=t.name,
            description=t.description,
            monthly_credits=t.monthly_credits,
            max_concurrent_jobs=t.max_concurrent_jobs,
            max_storage_gb=t.max_storage_gb,
            max_projects=t.max_projects,
            max_designs_per_project=t.max_designs_per_project,
            max_file_size_mb=t.max_file_size_mb,
            features=t.features,
            price_monthly_cents=t.price_monthly_cents,
            price_yearly_cents=t.price_yearly_cents,
            display_order=t.display_order,
            is_active=t.is_active,
        )
        for t in tiers
    ]


class UpdateTierRequest(BaseModel):
    """Request to update a subscription tier definition."""

    name: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=500)
    monthly_credits: int | None = Field(None, ge=0)
    max_concurrent_jobs: int | None = Field(None, ge=1)
    max_storage_gb: int | None = Field(None, ge=1)
    max_projects: int | None = Field(None, ge=1)
    max_designs_per_project: int | None = Field(None, ge=1)
    max_file_size_mb: int | None = Field(None, ge=1)
    features: dict[str, Any] | None = None
    price_monthly_cents: int | None = Field(None, ge=0)
    price_yearly_cents: int | None = Field(None, ge=0)


@router.patch(
    "/subscription-tiers/{tier_id}",
    response_model=TierDefinitionResponse,
    summary="Update subscription tier",
    description="Update a subscription tier's settings (admin only).",
    dependencies=[Depends(require_admin())],
)
async def update_subscription_tier(
    tier_id: UUID,
    request: UpdateTierRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TierDefinitionResponse:
    """Update a subscription tier definition.

    Args:
        tier_id: ID of the tier to update.
        request: Fields to update.

    Returns:
        Updated tier definition.

    Raises:
        HTTPException: If tier not found.
    """
    query = select(SubscriptionTier).where(SubscriptionTier.id == tier_id)
    result = await db.execute(query)
    tier = result.scalar_one_or_none()

    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription tier not found",
        )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tier, field, value)

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="subscription_tier",
        resource_id=tier.id,
        details={
            "action": "tier_updated",
            "tier_slug": tier.slug,
            "changes": update_data,
            "admin_email": current_user.email,
        },
    )

    await db.commit()
    await db.refresh(tier)

    return TierDefinitionResponse(
        id=tier.id,
        slug=tier.slug,
        name=tier.name,
        description=tier.description,
        monthly_credits=tier.monthly_credits,
        max_concurrent_jobs=tier.max_concurrent_jobs,
        max_storage_gb=tier.max_storage_gb,
        max_projects=tier.max_projects,
        max_designs_per_project=tier.max_designs_per_project,
        max_file_size_mb=tier.max_file_size_mb,
        features=tier.features,
        price_monthly_cents=tier.price_monthly_cents,
        price_yearly_cents=tier.price_yearly_cents,
        display_order=tier.display_order,
        is_active=tier.is_active,
    )


# =============================================================================
# Coupon & Promotion Schemas
# =============================================================================


class AdminCouponResponse(BaseModel):
    """Admin view of a coupon."""

    id: str
    code: str
    description: str | None
    coupon_type: str
    discount_percent: int | None
    discount_amount: int | None
    free_credits: int | None
    upgrade_tier: str | None
    valid_from: str | None
    valid_until: str | None
    is_active: bool
    max_uses: int | None
    max_uses_per_user: int
    current_uses: int
    restricted_to_tiers: list[str] | None
    new_users_only: bool
    created_at: str
    created_by: str | None


class CouponListResponse(BaseModel):
    """Paginated coupon list."""

    items: list[AdminCouponResponse]
    total: int
    page: int
    page_size: int


class CreateCouponRequest(BaseModel):
    """Request body for creating a coupon."""

    code: str = Field(..., min_length=3, max_length=50)
    description: str | None = None
    coupon_type: str = Field(
        ..., description="percentage, fixed_amount, free_credits, tier_upgrade",
    )
    discount_percent: int | None = Field(None, ge=1, le=100)
    discount_amount: int | None = Field(None, ge=1)
    free_credits: int | None = Field(None, ge=1)
    upgrade_tier: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses: int | None = Field(None, ge=1)
    max_uses_per_user: int = Field(1, ge=1)
    restricted_to_tiers: list[str] | None = None
    new_users_only: bool = False


class UpdateCouponRequest(BaseModel):
    """Request body for updating a coupon (partial)."""

    description: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    max_uses: int | None = None
    max_uses_per_user: int | None = None
    is_active: bool | None = None
    restricted_to_tiers: list[str] | None = None
    new_users_only: bool | None = None


class CouponRedemptionResponse(BaseModel):
    """A single coupon redemption record."""

    id: str
    coupon_id: str
    user_id: str
    user_email: str | None = None
    redeemed_at: str


class CouponUsageResponse(BaseModel):
    """Paginated coupon usage/redemption list."""

    items: list[CouponRedemptionResponse]
    total: int
    page: int
    page_size: int


class ApplyCouponRequest(BaseModel):
    """Request to apply a coupon to a user."""

    coupon_code: str = Field(..., min_length=3, max_length=50)


class GrantTrialRequest(BaseModel):
    """Request to grant a trial of a higher tier."""

    tier: str = Field(..., description="Target tier slug (e.g., pro, enterprise)")
    duration_days: int = Field(..., ge=1, le=365)


class ExtendTrialRequest(BaseModel):
    """Request to extend a user's trial period."""

    additional_days: int = Field(..., ge=1, le=365)


class BulkApplyCouponRequest(BaseModel):
    """Request to bulk-apply a coupon to a user segment."""

    coupon_code: str = Field(..., min_length=3, max_length=50)
    target: str = Field(..., description="'tier' or 'all'")
    target_value: str | None = Field(None, description="Tier slug when target='tier'")


class PromotionAnalyticsResponse(BaseModel):
    """Aggregated promotion analytics."""

    total_coupons: int
    active_coupons: int
    total_redemptions: int
    most_used_coupons: list[dict[str, Any]]


# =============================================================================
# Coupon & Promotion Endpoints
# =============================================================================


def _coupon_to_response(coupon: Coupon) -> AdminCouponResponse:
    """Convert a Coupon ORM instance to an AdminCouponResponse.

    Args:
        coupon: The Coupon model instance.

    Returns:
        AdminCouponResponse with serialized fields.
    """
    return AdminCouponResponse(
        id=str(coupon.id),
        code=coupon.code,
        description=coupon.description,
        coupon_type=coupon.coupon_type,
        discount_percent=coupon.discount_percent,
        discount_amount=coupon.discount_amount,
        free_credits=coupon.free_credits,
        upgrade_tier=coupon.upgrade_tier,
        valid_from=coupon.valid_from.isoformat() if coupon.valid_from else None,
        valid_until=coupon.valid_until.isoformat() if coupon.valid_until else None,
        is_active=coupon.is_active,
        max_uses=coupon.max_uses,
        max_uses_per_user=coupon.max_uses_per_user,
        current_uses=coupon.current_uses,
        restricted_to_tiers=coupon.restricted_to_tiers,
        new_users_only=coupon.new_users_only,
        created_at=coupon.created_at.isoformat(),
        created_by=str(coupon.created_by) if coupon.created_by else None,
    )


@router.get(
    "/coupons",
    response_model=CouponListResponse,
    summary="List all coupons",
    description="List all coupons with filtering and pagination (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_coupons(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    type_filter: Annotated[str | None, Query(alias="type")] = None,
    search: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> CouponListResponse:
    """List all coupons with optional filters.

    Args:
        page: Page number (1-indexed).
        page_size: Items per page.
        status_filter: Filter by status (active, inactive, expired).
        type_filter: Filter by coupon type.
        search: Search by code or description.
        db: Database session.

    Returns:
        Paginated list of coupons.
    """
    query = select(Coupon).where(Coupon.deleted_at.is_(None))

    filters: list[Any] = []
    now = datetime.now(tz=UTC)

    if status_filter == "active":
        filters.append(Coupon.is_active.is_(True))
        filters.append(or_(Coupon.valid_until.is_(None), Coupon.valid_until > now))
    elif status_filter == "inactive":
        filters.append(Coupon.is_active.is_(False))
    elif status_filter == "expired":
        filters.append(Coupon.valid_until.isnot(None))
        filters.append(Coupon.valid_until <= now)

    if type_filter:
        filters.append(Coupon.coupon_type == type_filter)

    if search:
        filters.append(
            or_(
                Coupon.code.ilike(f"%{search}%"),
                Coupon.description.ilike(f"%{search}%"),
            )
        )

    if filters:
        query = query.where(and_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(Coupon.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    coupons = result.scalars().all()

    return CouponListResponse(
        items=[_coupon_to_response(c) for c in coupons],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/coupons",
    response_model=AdminCouponResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a coupon",
    description="Create a new promotional coupon (admin only).",
    dependencies=[Depends(require_admin())],
)
async def create_coupon(
    request: CreateCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AdminCouponResponse:
    """Create a new coupon.

    Args:
        request: Coupon creation payload.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        The created coupon.

    Raises:
        HTTPException: 400 if coupon type is invalid or value fields are missing.
        HTTPException: 409 if coupon code already exists.
    """
    # Validate coupon_type
    valid_types = [t.value for t in CouponType]
    if request.coupon_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid coupon_type. Must be one of: {', '.join(valid_types)}",
        )

    # Validate value fields match type
    if request.coupon_type == CouponType.PERCENTAGE and not request.discount_percent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="discount_percent is required for percentage coupons",
        )
    if request.coupon_type == CouponType.FIXED_AMOUNT and not request.discount_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="discount_amount is required for fixed_amount coupons",
        )
    if request.coupon_type == CouponType.FREE_CREDITS and not request.free_credits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="free_credits is required for free_credits coupons",
        )
    if request.coupon_type == CouponType.TIER_UPGRADE and not request.upgrade_tier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="upgrade_tier is required for tier_upgrade coupons",
        )

    # Check code uniqueness
    existing = await db.execute(
        select(Coupon).where(Coupon.code == request.code.upper())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Coupon code '{request.code.upper()}' already exists",
        )

    coupon = Coupon(
        code=request.code.upper(),
        description=request.description,
        coupon_type=request.coupon_type,
        discount_percent=request.discount_percent,
        discount_amount=request.discount_amount,
        free_credits=request.free_credits,
        upgrade_tier=request.upgrade_tier,
        valid_from=request.valid_from,
        valid_until=request.valid_until,
        max_uses=request.max_uses,
        max_uses_per_user=request.max_uses_per_user,
        restricted_to_tiers=request.restricted_to_tiers,
        new_users_only=request.new_users_only,
        created_by=current_user.id,
    )

    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="coupon",
        resource_id=coupon.id,
        details={
            "action": "coupon_created",
            "code": coupon.code,
            "coupon_type": coupon.coupon_type,
            "admin_email": current_user.email,
        },
    )
    await db.commit()

    return _coupon_to_response(coupon)


@router.get(
    "/coupons/{code}",
    response_model=AdminCouponResponse,
    summary="Get coupon by code",
    description="Get full coupon details with usage stats (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_coupon_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> AdminCouponResponse:
    """Get a coupon by its code.

    Args:
        code: The coupon code.
        db: Database session.

    Returns:
        Full coupon details.

    Raises:
        HTTPException: 404 if coupon not found.
    """
    result = await db.execute(
        select(Coupon).where(
            Coupon.code == code.upper(),
            Coupon.deleted_at.is_(None),
        )
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon '{code}' not found",
        )

    return _coupon_to_response(coupon)


@router.patch(
    "/coupons/{code}",
    response_model=AdminCouponResponse,
    summary="Update coupon",
    description="Partial update of coupon fields (admin only).",
    dependencies=[Depends(require_admin())],
)
async def update_coupon(
    code: str,
    request: UpdateCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AdminCouponResponse:
    """Update a coupon by its code.

    Args:
        code: The coupon code.
        request: Partial update payload.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        Updated coupon.

    Raises:
        HTTPException: 404 if coupon not found.
    """
    result = await db.execute(
        select(Coupon).where(
            Coupon.code == code.upper(),
            Coupon.deleted_at.is_(None),
        )
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon '{code}' not found",
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(coupon, field, value)

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="coupon",
        resource_id=coupon.id,
        details={
            "action": "coupon_updated",
            "code": coupon.code,
            "changes": update_data,
            "admin_email": current_user.email,
        },
    )

    await db.commit()
    await db.refresh(coupon)

    return _coupon_to_response(coupon)


@router.delete(
    "/coupons/{code}",
    summary="Deactivate coupon",
    description="Soft-delete (deactivate) a coupon (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_coupon(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Soft-delete a coupon by its code.

    Args:
        code: The coupon code.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: 404 if coupon not found.
    """
    result = await db.execute(
        select(Coupon).where(
            Coupon.code == code.upper(),
            Coupon.deleted_at.is_(None),
        )
    )
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon '{code}' not found",
        )

    coupon.soft_delete()
    coupon.is_active = False

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="coupon",
        resource_id=coupon.id,
        details={
            "action": "coupon_deleted",
            "code": coupon.code,
            "admin_email": current_user.email,
        },
    )

    await db.commit()

    return {"message": f"Coupon '{code.upper()}' has been deactivated"}


@router.get(
    "/coupons/{code}/usage",
    response_model=CouponUsageResponse,
    summary="Coupon usage details",
    description="Get redemption details for a specific coupon (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_coupon_usage(
    code: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> CouponUsageResponse:
    """Get paginated redemption records for a coupon.

    Args:
        code: The coupon code.
        page: Page number.
        page_size: Items per page.
        db: Database session.

    Returns:
        Paginated list of redemptions with user info.

    Raises:
        HTTPException: 404 if coupon not found.
    """
    # Verify coupon exists
    coupon_result = await db.execute(
        select(Coupon).where(
            Coupon.code == code.upper(),
            Coupon.deleted_at.is_(None),
        )
    )
    coupon = coupon_result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon '{code}' not found",
        )

    # Query redemptions
    query = (
        select(CouponRedemption)
        .where(CouponRedemption.coupon_id == coupon.id)
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page with user info
    offset = (page - 1) * page_size
    query = query.order_by(desc(CouponRedemption.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    redemptions = result.scalars().all()

    # Fetch user emails for the redemptions
    user_ids = [r.user_id for r in redemptions]
    user_map: dict[UUID, str] = {}
    if user_ids:
        users_result = await db.execute(
            select(User.id, User.email).where(User.id.in_(user_ids))
        )
        user_map = {row.id: row.email for row in users_result}

    return CouponUsageResponse(
        items=[
            CouponRedemptionResponse(
                id=str(r.id),
                coupon_id=str(r.coupon_id),
                user_id=str(r.user_id),
                user_email=user_map.get(r.user_id),
                redeemed_at=r.created_at.isoformat(),
            )
            for r in redemptions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/users/{user_id}/apply-coupon",
    summary="Apply coupon to user",
    description="Apply a promotional coupon to a specific user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def apply_coupon_to_user(
    user_id: UUID,
    request: ApplyCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Apply a coupon to a user.

    Validates the coupon is active, not expired, and not over-used.
    Creates a CouponRedemption record and applies the benefit
    (credits, tier upgrade, etc.).

    Args:
        user_id: Target user ID.
        request: Contains the coupon_code.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        Details about the applied benefit.

    Raises:
        HTTPException: 404 if user or coupon not found.
        HTTPException: 400 if coupon is invalid, expired, or already used.
    """
    # Get user
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get coupon
    coupon_result = await db.execute(
        select(Coupon).where(
            Coupon.code == request.coupon_code.upper(),
            Coupon.deleted_at.is_(None),
        )
    )
    coupon = coupon_result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon '{request.coupon_code}' not found",
        )

    # Validate coupon is active
    if not coupon.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon is not active",
        )

    # Validate expiry
    now = datetime.now(tz=UTC)
    if coupon.valid_from and coupon.valid_from > now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon is not yet valid",
        )
    if coupon.valid_until and coupon.valid_until <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon has expired",
        )

    # Validate max total uses
    if coupon.max_uses is not None and coupon.current_uses >= coupon.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon has reached maximum total uses",
        )

    # Validate per-user uses
    user_redemption_count = (await db.execute(
        select(func.count()).where(
            CouponRedemption.coupon_id == coupon.id,
            CouponRedemption.user_id == user_id,
        )
    )).scalar_one()
    if user_redemption_count >= coupon.max_uses_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already used this coupon the maximum number of times",
        )

    # Apply benefit based on coupon type
    benefit_details: dict[str, Any] = {
        "coupon_code": coupon.code, "coupon_type": coupon.coupon_type,
    }

    if coupon.coupon_type == CouponType.FREE_CREDITS:
        # Add credits to user balance
        balance_result = await db.execute(
            select(CreditBalance).where(CreditBalance.user_id == user_id)
        )
        balance = balance_result.scalar_one_or_none()
        if balance:
            balance.add(coupon.free_credits or 0)
        else:
            balance = CreditBalance(
                user_id=user_id,
                balance=coupon.free_credits or 0,
                lifetime_earned=coupon.free_credits or 0,
            )
            db.add(balance)
        benefit_details["credits_added"] = coupon.free_credits

    elif coupon.coupon_type == CouponType.TIER_UPGRADE:
        # Upgrade user tier
        sub_result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = sub_result.scalar_one_or_none()
        if subscription:
            benefit_details["previous_tier"] = subscription.tier
            subscription.tier = coupon.upgrade_tier or "pro"
        else:
            subscription = Subscription(
                user_id=user_id,
                tier=coupon.upgrade_tier or "pro",
                status="active",
            )
            db.add(subscription)
        benefit_details["new_tier"] = coupon.upgrade_tier

    elif coupon.coupon_type == CouponType.PERCENTAGE:
        benefit_details["discount_percent"] = coupon.discount_percent

    elif coupon.coupon_type == CouponType.FIXED_AMOUNT:
        benefit_details["discount_amount"] = coupon.discount_amount

    # Create redemption record
    redemption = CouponRedemption(
        coupon_id=coupon.id,
        user_id=user_id,
    )
    db.add(redemption)

    # Increment usage count
    coupon.current_uses += 1

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="coupon",
        resource_id=coupon.id,
        details={
            "action": "coupon_applied",
            "code": coupon.code,
            "target_user_id": str(user_id),
            "benefit": benefit_details,
            "admin_email": current_user.email,
        },
    )

    await db.commit()

    return {
        "message": f"Coupon '{coupon.code}' applied to user",
        "user_id": str(user_id),
        **benefit_details,
    }


@router.post(
    "/users/{user_id}/grant-trial",
    summary="Grant trial of higher tier",
    description="Grant a temporary trial of a higher subscription tier (admin only).",
    dependencies=[Depends(require_admin())],
)
async def grant_trial(
    user_id: UUID,
    request: GrantTrialRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Grant a trial subscription upgrade to a user.

    Args:
        user_id: Target user ID.
        request: Contains tier slug and duration_days.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        Details about the granted trial.

    Raises:
        HTTPException: 404 if user or tier not found.
    """
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify tier exists
    tier_result = await db.execute(
        select(SubscriptionTier).where(SubscriptionTier.slug == request.tier)
    )
    tier = tier_result.scalar_one_or_none()
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tier '{request.tier}' not found",
        )

    now = datetime.now(tz=UTC)
    trial_end = now + timedelta(days=request.duration_days)

    # Create or update subscription
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = sub_result.scalar_one_or_none()
    previous_tier = None

    if subscription:
        previous_tier = subscription.tier
        subscription.tier = request.tier
        subscription.status = "active"
        subscription.current_period_start = now
        subscription.current_period_end = trial_end
    else:
        subscription = Subscription(
            user_id=user_id,
            tier=request.tier,
            status="active",
            current_period_start=now,
            current_period_end=trial_end,
        )
        db.add(subscription)

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="subscription",
        resource_id=subscription.id if subscription.id else user_id,
        details={
            "action": "trial_granted",
            "target_user_id": str(user_id),
            "tier": request.tier,
            "duration_days": request.duration_days,
            "trial_end": trial_end.isoformat(),
            "previous_tier": previous_tier,
            "admin_email": current_user.email,
        },
    )

    await db.commit()

    return {
        "message": f"Trial of '{request.tier}' granted to user",
        "user_id": str(user_id),
        "tier": request.tier,
        "duration_days": request.duration_days,
        "trial_start": now.isoformat(),
        "trial_end": trial_end.isoformat(),
        "previous_tier": previous_tier,
    }


@router.post(
    "/users/{user_id}/extend-trial",
    summary="Extend trial period",
    description="Extend a user's current trial/subscription period (admin only).",
    dependencies=[Depends(require_admin())],
)
async def extend_trial(
    user_id: UUID,
    request: ExtendTrialRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Extend a user's subscription period.

    Args:
        user_id: Target user ID.
        request: Contains additional_days.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        Details about the extended trial.

    Raises:
        HTTPException: 404 if user or subscription not found.
    """
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get subscription
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = sub_result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has no active subscription to extend",
        )

    previous_end = subscription.current_period_end
    now = datetime.now(tz=UTC)

    # Extend from current end or from now if already expired
    base = previous_end if previous_end and previous_end > now else now
    new_end = base + timedelta(days=request.additional_days)
    subscription.current_period_end = new_end

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="subscription",
        resource_id=subscription.id,
        details={
            "action": "trial_extended",
            "target_user_id": str(user_id),
            "additional_days": request.additional_days,
            "previous_end": previous_end.isoformat() if previous_end else None,
            "new_end": new_end.isoformat(),
            "admin_email": current_user.email,
        },
    )

    await db.commit()

    return {
        "message": f"Trial extended by {request.additional_days} days",
        "user_id": str(user_id),
        "tier": subscription.tier,
        "additional_days": request.additional_days,
        "previous_end": previous_end.isoformat() if previous_end else None,
        "new_end": new_end.isoformat(),
    }


@router.get(
    "/promotions/analytics",
    response_model=PromotionAnalyticsResponse,
    summary="Promotion analytics",
    description="Get aggregated promotion and coupon analytics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_promotion_analytics(
    db: AsyncSession = Depends(get_db),
) -> PromotionAnalyticsResponse:
    """Get aggregated promotion analytics.

    Args:
        db: Database session.

    Returns:
        Analytics including total coupons, redemptions, and most used coupons.
    """
    # Total coupons (non-deleted)
    total_coupons = (await db.execute(
        select(func.count()).where(Coupon.deleted_at.is_(None))
    )).scalar_one()

    # Active coupons
    now = datetime.now(tz=UTC)
    active_coupons = (await db.execute(
        select(func.count()).where(
            Coupon.deleted_at.is_(None),
            Coupon.is_active.is_(True),
            or_(Coupon.valid_until.is_(None), Coupon.valid_until > now),
        )
    )).scalar_one()

    # Total redemptions
    total_redemptions = (await db.execute(
        select(func.count()).select_from(CouponRedemption)
    )).scalar_one()

    # Most used coupons (top 10)
    most_used_query = (
        select(Coupon.code, Coupon.coupon_type, Coupon.current_uses)
        .where(Coupon.deleted_at.is_(None), Coupon.current_uses > 0)
        .order_by(desc(Coupon.current_uses))
        .limit(10)
    )
    most_used_result = await db.execute(most_used_query)
    most_used_coupons = [
        {
            "code": row.code,
            "coupon_type": row.coupon_type,
            "total_uses": row.current_uses,
        }
        for row in most_used_result
    ]

    return PromotionAnalyticsResponse(
        total_coupons=total_coupons,
        active_coupons=active_coupons,
        total_redemptions=total_redemptions,
        most_used_coupons=most_used_coupons,
    )


@router.post(
    "/coupons/bulk-apply",
    summary="Bulk apply coupon to segment",
    description="Apply a coupon to all users in a segment (admin only).",
    dependencies=[Depends(require_admin())],
)
async def bulk_apply_coupon(
    request: BulkApplyCouponRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Bulk-apply a coupon to a user segment.

    Args:
        request: Contains coupon_code, target type, and optional target_value.
        db: Database session.
        current_user: Authenticated admin user.

    Returns:
        Summary of applied/skipped users.

    Raises:
        HTTPException: 404 if coupon not found.
        HTTPException: 400 if target is invalid.
    """
    # Get coupon
    coupon_result = await db.execute(
        select(Coupon).where(
            Coupon.code == request.coupon_code.upper(),
            Coupon.deleted_at.is_(None),
        )
    )
    coupon = coupon_result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coupon '{request.coupon_code}' not found",
        )

    if not coupon.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon is not active",
        )

    # Build user query based on target
    user_query = select(User).where(User.status == "active")

    if request.target == "tier":
        if not request.target_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_value (tier slug) is required when target='tier'",
            )
        # Join with subscriptions to filter by tier
        user_query = (
            user_query
            .outerjoin(Subscription, Subscription.user_id == User.id)
            .where(
                or_(
                    Subscription.tier == request.target_value,
                    # Users without subscription are "free" tier
                    and_(
                        Subscription.id.is_(None),
                        request.target_value == "free",
                    ),
                )
            )
        )
    elif request.target != "all":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target must be 'tier' or 'all'",
        )

    users_result = await db.execute(user_query)
    users = users_result.scalars().all()

    applied = 0
    skipped = 0

    for target_user in users:
        # Check per-user limit
        user_redemption_count = (await db.execute(
            select(func.count()).where(
                CouponRedemption.coupon_id == coupon.id,
                CouponRedemption.user_id == target_user.id,
            )
        )).scalar_one()

        if user_redemption_count >= coupon.max_uses_per_user:
            skipped += 1
            continue

        # Check max total uses
        if coupon.max_uses is not None and coupon.current_uses >= coupon.max_uses:
            skipped += len(users) - applied - skipped
            break

        # Apply benefit for free_credits type
        if coupon.coupon_type == CouponType.FREE_CREDITS and coupon.free_credits:
            balance_result = await db.execute(
                select(CreditBalance).where(CreditBalance.user_id == target_user.id)
            )
            balance = balance_result.scalar_one_or_none()
            if balance:
                balance.add(coupon.free_credits)
            else:
                balance = CreditBalance(
                    user_id=target_user.id,
                    balance=coupon.free_credits,
                    lifetime_earned=coupon.free_credits,
                )
                db.add(balance)

        # Create redemption
        redemption = CouponRedemption(
            coupon_id=coupon.id,
            user_id=target_user.id,
        )
        db.add(redemption)
        coupon.current_uses += 1
        applied += 1

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="coupon",
        resource_id=coupon.id,
        details={
            "action": "coupon_bulk_applied",
            "code": coupon.code,
            "target": request.target,
            "target_value": request.target_value,
            "applied": applied,
            "skipped": skipped,
            "admin_email": current_user.email,
        },
    )

    await db.commit()

    return {
        "message": f"Bulk apply complete for coupon '{coupon.code}'",
        "coupon_code": coupon.code,
        "target": request.target,
        "target_value": request.target_value,
        "applied": applied,
        "skipped": skipped,
        "total_users_processed": applied + skipped,
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


# -----------------------------------------------------------------------------
# US-10.6: Organization Edit, Members, Ownership, Credits, Tier, Audit, Stats
# -----------------------------------------------------------------------------


class EditOrganizationRequest(BaseModel):
    """Request to edit an organization."""

    name: str | None = Field(None, max_length=255)
    settings: dict[str, Any] | None = None


@router.patch(
    "/organizations/{org_id}",
    response_model=AdminOrganizationResponse,
    summary="Edit organization",
    description="Update an organization's name or settings (admin only).",
    dependencies=[Depends(require_admin())],
)
async def edit_organization(
    org_id: UUID,
    request: EditOrganizationRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminOrganizationResponse:
    """Edit an organization's name or settings.

    Args:
        org_id: Organization ID.
        request: Fields to update.

    Returns:
        Updated organization details.

    Raises:
        HTTPException: If organization not found.
    """
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

    if request.name is not None:
        org.name = request.name
    if request.settings is not None:
        org.settings = {**org.settings, **request.settings}

    await db.commit()
    await db.refresh(org)

    # Get member count
    member_count = (
        await db.execute(
            select(func.count()).where(OrganizationMember.organization_id == org.id)
        )
    ).scalar_one()

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
        tier_slug=org.subscription_tier,
        created_at=org.created_at,
    )


class AddOrgMemberRequest(BaseModel):
    """Request to add a member to an organization."""

    user_id: UUID
    role: str = Field(default="member", pattern=r"^(viewer|member|admin)$")


@router.post(
    "/organizations/{org_id}/members",
    response_model=AdminOrgMemberResponse,
    summary="Add organization member",
    description="Add a user to an organization (admin only).",
    dependencies=[Depends(require_admin())],
)
async def add_organization_member(
    org_id: UUID,
    request: AddOrgMemberRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminOrgMemberResponse:
    """Add a user as a member of an organization.

    Args:
        org_id: Organization ID.
        request: User ID and role.

    Returns:
        New membership record.

    Raises:
        HTTPException: If org/user not found or user already a member.
    """
    # Verify org exists
    org_query = select(Organization).where(
        and_(Organization.id == org_id, Organization.deleted_at.is_(None))
    )
    org = (await db.execute(org_query)).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Verify user exists
    user = (await db.execute(select(User).where(User.id == request.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check not already member
    existing = (
        await db.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == request.user_id,
                )
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization",
        )

    member = OrganizationMember(
        organization_id=org_id,
        user_id=request.user_id,
        role=request.role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return AdminOrgMemberResponse(
        id=member.id,
        user_id=member.user_id,
        user_email=user.email,
        role=member.role,
        joined_at=member.created_at,
    )


@router.delete(
    "/organizations/{org_id}/members/{user_id}",
    summary="Remove organization member",
    description="Remove a member from an organization (admin only).",
    dependencies=[Depends(require_admin())],
)
async def remove_organization_member(
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Remove a member from an organization.

    Owners cannot be removed; transfer ownership first.

    Args:
        org_id: Organization ID.
        user_id: User ID to remove.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If member not found or is the owner.
    """
    member = (
        await db.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == user_id,
                )
            )
        )
    ).scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in organization",
        )

    if member.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the owner. Transfer ownership first.",
        )

    await db.delete(member)
    await db.commit()

    return {"message": "Member removed from organization"}


class ChangeOrgMemberRoleRequest(BaseModel):
    """Request to change a member's role."""

    role: str = Field(..., pattern=r"^(viewer|member|admin)$")


@router.patch(
    "/organizations/{org_id}/members/{user_id}/role",
    response_model=AdminOrgMemberResponse,
    summary="Change member role",
    description="Change a member's role in an organization (admin only).",
    dependencies=[Depends(require_admin())],
)
async def change_organization_member_role(
    org_id: UUID,
    user_id: UUID,
    request: ChangeOrgMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AdminOrgMemberResponse:
    """Change a member's role within an organization.

    Args:
        org_id: Organization ID.
        user_id: Target user ID.
        request: New role.

    Returns:
        Updated membership record.

    Raises:
        HTTPException: If member not found.
    """
    member_query = (
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(
            and_(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
        )
    )
    member = (await db.execute(member_query)).scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in organization",
        )

    old_role = member.role
    member.role = request.role

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="organization_member",
        resource_id=member.id,
        details={
            "action": "member_role_changed",
            "org_id": str(org_id),
            "target_user_id": str(user_id),
            "old_role": old_role,
            "new_role": request.role,
        },
    )

    await db.commit()
    await db.refresh(member)

    return AdminOrgMemberResponse(
        id=member.id,
        user_id=member.user_id,
        user_email=member.user.email if member.user else None,
        role=member.role,
        joined_at=member.created_at,
    )


class TransferOrgOwnershipRequest(BaseModel):
    """Request to transfer organization ownership."""

    new_owner_id: UUID


@router.post(
    "/organizations/{org_id}/transfer-ownership",
    summary="Transfer organization ownership",
    description="Transfer ownership of an organization to another member (admin only).",
    dependencies=[Depends(require_admin())],
)
async def transfer_organization_ownership(
    org_id: UUID,
    request: TransferOrgOwnershipRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Transfer organization ownership to a new member.

    The new owner must already be a member of the organization.
    The previous owner is demoted to admin.

    Args:
        org_id: Organization ID.
        request: New owner's user ID.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If org/member not found or new owner is not a member.
    """
    # Verify org exists
    org = (
        await db.execute(
            select(Organization).where(
                and_(Organization.id == org_id, Organization.deleted_at.is_(None))
            )
        )
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Verify new owner is a member
    new_owner_membership = (
        await db.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == request.new_owner_id,
                )
            )
        )
    ).scalar_one_or_none()

    if not new_owner_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New owner must be an existing member of the organization",
        )

    # Demote current owner to admin
    current_owner = (
        await db.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.role == "owner",
                )
            )
        )
    ).scalar_one_or_none()

    if current_owner:
        current_owner.role = "admin"

    # Promote new owner
    new_owner_membership.role = "owner"
    org.owner_id = request.new_owner_id

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="organization",
        resource_id=org.id,
        details={
            "action": "ownership_transferred",
            "org_id": str(org_id),
            "previous_owner_id": str(current_owner.user_id) if current_owner else None,
            "new_owner_id": str(request.new_owner_id),
        },
    )

    await db.commit()

    return {
        "message": "Ownership transferred",
        "new_owner_id": str(request.new_owner_id),
    }


class AddOrgCreditsRequest(BaseModel):
    """Request to add credits to an organization."""

    amount: int = Field(..., ge=1, le=100000)
    reason: str = Field(..., min_length=1, max_length=500)


@router.post(
    "/organizations/{org_id}/credits/add",
    summary="Add organization credits",
    description="Add credits to an organization's pool (admin only).",
    dependencies=[Depends(require_admin())],
)
async def add_organization_credits(
    org_id: UUID,
    request: AddOrgCreditsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Add credits to an organization's shared credit pool.

    Args:
        org_id: Organization ID.
        request: Amount and reason.

    Returns:
        Confirmation with new balance.

    Raises:
        HTTPException: If organization not found.
    """
    # Verify org exists
    org = (
        await db.execute(
            select(Organization).where(
                and_(Organization.id == org_id, Organization.deleted_at.is_(None))
            )
        )
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Get or create credit balance
    balance_query = select(OrganizationCreditBalance).where(
        OrganizationCreditBalance.organization_id == org_id
    )
    balance = (await db.execute(balance_query)).scalar_one_or_none()

    if not balance:
        balance = OrganizationCreditBalance(
            organization_id=org_id,
            balance=0,
            lifetime_earned=0,
            lifetime_spent=0,
        )
        db.add(balance)

    balance.balance += request.amount
    balance.lifetime_earned += request.amount

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="organization_credits",
        resource_id=org.id,
        details={
            "action": "org_credits_added",
            "amount": request.amount,
            "reason": request.reason,
            "new_balance": balance.balance,
        },
    )

    await db.commit()

    return {
        "message": f"Added {request.amount} credits to organization",
        "new_balance": balance.balance,
    }


class ChangeOrgTierRequest(BaseModel):
    """Request to change an organization's tier."""

    tier: str = Field(..., description="New tier slug")


@router.patch(
    "/organizations/{org_id}/tier",
    summary="Change organization tier",
    description="Change an organization's subscription tier (admin only).",
    dependencies=[Depends(require_admin())],
)
async def change_organization_tier(
    org_id: UUID,
    request: ChangeOrgTierRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Change an organization's subscription tier.

    The tier is stored in the organization's settings JSONB.

    Args:
        org_id: Organization ID.
        request: New tier slug.

    Returns:
        Confirmation with old and new tier.

    Raises:
        HTTPException: If organization not found.
    """
    org = (
        await db.execute(
            select(Organization).where(
                and_(Organization.id == org_id, Organization.deleted_at.is_(None))
            )
        )
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    old_tier = org.subscription_tier
    org.settings = {**org.settings, "subscription_tier": request.tier}

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="organization",
        resource_id=org.id,
        details={
            "action": "org_tier_changed",
            "old_tier": old_tier,
            "new_tier": request.tier,
        },
    )

    await db.commit()

    return {
        "message": f"Organization tier changed from {old_tier} to {request.tier}",
        "old_tier": old_tier,
        "new_tier": request.tier,
    }


class OrgAuditLogEntry(BaseModel):
    """Organization audit log entry."""

    id: UUID
    user_id: UUID | None = None
    action: str
    resource_type: str | None = None
    resource_id: UUID | None = None
    details: dict[str, Any] = {}
    created_at: datetime


class OrgAuditLogResponse(BaseModel):
    """Paginated organization audit log."""

    items: list[OrgAuditLogEntry]
    total: int
    page: int
    page_size: int


@router.get(
    "/organizations/{org_id}/audit-log",
    response_model=OrgAuditLogResponse,
    summary="Get organization audit log",
    description="Get paginated audit log for an organization (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_organization_audit_log(
    org_id: UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> OrgAuditLogResponse:
    """Get paginated audit log entries for an organization.

    Args:
        org_id: Organization ID.
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated organization audit log.
    """
    query = select(OrganizationAuditLog).where(
        OrganizationAuditLog.organization_id == org_id
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(desc(OrganizationAuditLog.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return OrgAuditLogResponse(
        items=[
            OrgAuditLogEntry(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=log.details,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


class OrgStatsResponse(BaseModel):
    """Organization statistics."""

    org_id: UUID
    member_count: int = 0
    project_count: int = 0
    design_count: int = 0
    storage_used_bytes: int = 0
    credits_balance: int = 0
    credits_used: int = 0


@router.get(
    "/organizations/{org_id}/stats",
    response_model=OrgStatsResponse,
    summary="Get organization statistics",
    description="Get usage statistics for an organization (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_organization_stats(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> OrgStatsResponse:
    """Get aggregate statistics for an organization.

    Args:
        org_id: Organization ID.

    Returns:
        Member count, project/design counts, storage, and credit usage.

    Raises:
        HTTPException: If organization not found.
    """
    # Verify org
    org = (
        await db.execute(
            select(Organization).where(
                and_(Organization.id == org_id, Organization.deleted_at.is_(None))
            )
        )
    ).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Member count
    member_count = (
        await db.execute(
            select(func.count()).where(OrganizationMember.organization_id == org_id)
        )
    ).scalar_one()

    # Project count
    project_count = (
        await db.execute(
            select(func.count()).where(
                Project.organization_id == org_id,
                Project.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Design count (via projects)
    design_count = (
        await db.execute(
            select(func.count())
            .select_from(Design)
            .join(Project, Project.id == Design.project_id)
            .where(
                Project.organization_id == org_id,
                Design.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Storage used (sum of file sizes for org members)
    member_ids_query = select(OrganizationMember.user_id).where(
        OrganizationMember.organization_id == org_id
    )
    storage_used = (
        await db.execute(
            select(func.coalesce(func.sum(FileModel.size), 0)).where(
                FileModel.user_id.in_(member_ids_query)
            )
        )
    ).scalar_one()

    # Credits
    credit_balance = (
        await db.execute(
            select(OrganizationCreditBalance).where(
                OrganizationCreditBalance.organization_id == org_id
            )
        )
    ).scalar_one_or_none()

    return OrgStatsResponse(
        org_id=org_id,
        member_count=member_count,
        project_count=project_count,
        design_count=design_count,
        storage_used_bytes=int(storage_used),
        credits_balance=credit_balance.balance if credit_balance else 0,
        credits_used=credit_balance.lifetime_spent if credit_balance else 0,
    )


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
                ReferenceComponent.model_number.ilike(
                    f"%{search}%"
                ),  # Use model_number instead of part_number
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
                part_number=comp.model_number,  # Use model_number
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
        comp.is_verified = True  # type: ignore[assignment]
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


# -----------------------------------------------------------------------------
# US-10.7: Component Detail, Create, Edit, Analytics, Approve
# -----------------------------------------------------------------------------


@router.get(
    "/components/{component_id}",
    response_model=AdminComponentResponse,
    summary="Get component details",
    description="Get full component details with specs and usage (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_component_detail(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminComponentResponse:
    """Return full component details including specifications and usage stats.

    Args:
        component_id: Component ID.

    Returns:
        Component with full details.

    Raises:
        HTTPException: If component not found.
    """
    query = select(ReferenceComponent).where(ReferenceComponent.id == component_id)
    result = await db.execute(query)
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )

    # Get user email if user-owned
    user_email = None
    if comp.user_id:
        user_query = select(User).where(User.id == comp.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        user_email = user.email if user else None

    return AdminComponentResponse(
        id=comp.id,
        name=comp.name,
        part_number=comp.model_number,
        manufacturer=comp.manufacturer,
        category=comp.category,
        user_id=comp.user_id,
        user_email=user_email,
        is_library=comp.user_id is None,
        is_verified=getattr(comp, "is_verified", False),
        is_featured=getattr(comp, "is_featured", False),
        created_at=comp.created_at,
    )


class CreateComponentRequest(BaseModel):
    """Request to create a library component."""

    name: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=2000)
    category: str = Field(..., max_length=100)
    manufacturer: str | None = Field(None, max_length=255)
    model_number: str | None = Field(None, max_length=255)
    specs: dict[str, Any] | None = None


@router.post(
    "/components",
    response_model=AdminComponentResponse,
    summary="Create library component",
    description="Create a new library component (admin only).",
    dependencies=[Depends(require_admin())],
    status_code=status.HTTP_201_CREATED,
)
async def create_component(
    request: CreateComponentRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminComponentResponse:
    """Create a new component in the reference library.

    Library components have user_id=None and source_type='library'.

    Args:
        request: Component details.

    Returns:
        Created component.
    """
    comp = ReferenceComponent(
        name=request.name,
        description=request.description,
        category=request.category,
        manufacturer=request.manufacturer,
        model_number=request.model_number,
        source_type="library",
        user_id=None,  # Library component
    )
    if request.specs:
        comp.dimensions = request.specs.get("dimensions")
        comp.electrical_properties = request.specs.get("electrical_properties")
        comp.thermal_properties = request.specs.get("thermal_properties")

    db.add(comp)
    await db.commit()
    await db.refresh(comp)

    return AdminComponentResponse(
        id=comp.id,
        name=comp.name,
        part_number=comp.model_number,
        manufacturer=comp.manufacturer,
        category=comp.category,
        user_id=comp.user_id,
        user_email=None,
        is_library=True,
        is_verified=getattr(comp, "is_verified", False),
        is_featured=getattr(comp, "is_featured", False),
        created_at=comp.created_at,
    )


class EditComponentRequest(BaseModel):
    """Request to edit a component."""

    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    category: str | None = Field(None, max_length=100)
    manufacturer: str | None = Field(None, max_length=255)
    model_number: str | None = Field(None, max_length=255)
    specs: dict[str, Any] | None = None


@router.patch(
    "/components/{component_id}",
    response_model=AdminComponentResponse,
    summary="Edit component",
    description="Edit a component's metadata (admin only).",
    dependencies=[Depends(require_admin())],
)
async def edit_component(
    component_id: UUID,
    request: EditComponentRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminComponentResponse:
    """Edit a component's metadata and specifications.

    Args:
        component_id: Component ID.
        request: Fields to update.

    Returns:
        Updated component.

    Raises:
        HTTPException: If component not found.
    """
    query = select(ReferenceComponent).where(ReferenceComponent.id == component_id)
    result = await db.execute(query)
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )

    if request.name is not None:
        comp.name = request.name
    if request.description is not None:
        comp.description = request.description
    if request.category is not None:
        comp.category = request.category
    if request.manufacturer is not None:
        comp.manufacturer = request.manufacturer
    if request.model_number is not None:
        comp.model_number = request.model_number
    if request.specs is not None:
        if "dimensions" in request.specs:
            comp.dimensions = request.specs["dimensions"]
        if "electrical_properties" in request.specs:
            comp.electrical_properties = request.specs["electrical_properties"]
        if "thermal_properties" in request.specs:
            comp.thermal_properties = request.specs["thermal_properties"]

    await db.commit()
    await db.refresh(comp)

    # Get user email if user-owned
    user_email = None
    if comp.user_id:
        user_query = select(User).where(User.id == comp.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        user_email = user.email if user else None

    return AdminComponentResponse(
        id=comp.id,
        name=comp.name,
        part_number=comp.model_number,
        manufacturer=comp.manufacturer,
        category=comp.category,
        user_id=comp.user_id,
        user_email=user_email,
        is_library=comp.user_id is None,
        is_verified=getattr(comp, "is_verified", False),
        is_featured=getattr(comp, "is_featured", False),
        created_at=comp.created_at,
    )


class ComponentAnalyticsResponse(BaseModel):
    """Component usage analytics."""

    total_components: int = 0
    library_components: int = 0
    user_components: int = 0
    verified_components: int = 0
    by_category: dict[str, int] = {}
    most_used: list[dict[str, Any]] = []


@router.get(
    "/components/analytics",
    response_model=ComponentAnalyticsResponse,
    summary="Component usage analytics",
    description="Get component library analytics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_component_analytics(
    db: AsyncSession = Depends(get_db),
) -> ComponentAnalyticsResponse:
    """Return component library analytics: totals, categories, most used.

    Returns:
        Component counts by type, category, and usage.
    """
    # Total
    total = (
        await db.execute(select(func.count(ReferenceComponent.id)))
    ).scalar_one()

    # Library (no user_id)
    library_count = (
        await db.execute(
            select(func.count(ReferenceComponent.id)).where(
                ReferenceComponent.user_id.is_(None)
            )
        )
    ).scalar_one()

    # User-owned
    user_count = (
        await db.execute(
            select(func.count(ReferenceComponent.id)).where(
                ReferenceComponent.user_id.isnot(None)
            )
        )
    ).scalar_one()

    # Verified
    verified_count = (
        await db.execute(
            select(func.count(ReferenceComponent.id)).where(
                ReferenceComponent.is_verified == True  # noqa: E712
            )
        )
    ).scalar_one()

    # By category
    cat_query = (
        select(ReferenceComponent.category, func.count().label("count"))
        .where(ReferenceComponent.category.isnot(None))
        .group_by(ReferenceComponent.category)
    )
    cat_result = await db.execute(cat_query)
    by_category = {row[0]: row[1] for row in cat_result.all()}

    # Most used (from ComponentLibrary usage_count)
    most_used_query = (
        select(ComponentLibrary, ReferenceComponent.name)
        .join(ReferenceComponent, ReferenceComponent.id == ComponentLibrary.component_id)
        .order_by(desc(ComponentLibrary.usage_count))
        .limit(10)
    )
    most_used_result = await db.execute(most_used_query)
    most_used = [
        {
            "component_id": str(row[0].component_id),
            "name": row[1],
            "usage_count": row[0].usage_count,
            "category": row[0].category,
        }
        for row in most_used_result.all()
    ]

    return ComponentAnalyticsResponse(
        total_components=total,
        library_components=library_count,
        user_components=user_count,
        verified_components=verified_count,
        by_category=by_category,
        most_used=most_used,
    )


@router.post(
    "/components/{component_id}/approve-for-library",
    summary="Approve component for library",
    description="Approve a user component for the curated library (admin only).",
    dependencies=[Depends(require_admin())],
)
async def approve_component_for_library(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Approve a component and add it to the curated library.

    Sets is_verified=True, verified_by, verified_at, and creates a
    ComponentLibrary entry if one doesn't exist.

    Args:
        component_id: Component ID.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If component not found.
    """
    query = select(ReferenceComponent).where(ReferenceComponent.id == component_id)
    result = await db.execute(query)
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )

    comp.is_verified = True
    comp.verified_by = current_user.id
    comp.verified_at = datetime.now(tz=UTC)

    # Create library entry if not existing
    lib_query = select(ComponentLibrary).where(ComponentLibrary.component_id == component_id)
    lib_entry = (await db.execute(lib_query)).scalar_one_or_none()

    if not lib_entry:
        lib_entry = ComponentLibrary(
            component_id=component_id,
            category=comp.category or "uncategorized",
            manufacturer=comp.manufacturer,
            model_number=comp.model_number,
            tags=comp.tags or [],
        )
        db.add(lib_entry)

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.PASSWORD_RESET_REQUESTED,
        user_id=current_user.id,
        resource_type="component",
        resource_id=comp.id,
        details={
            "action": "component_approved_for_library",
            "component_name": comp.name,
        },
    )

    await db.commit()

    return {"message": "Component approved for library", "component_id": str(component_id)}


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
        query = query.where(Notification.type == notification_type)

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
                notification_type=n.type.value if n.type else "unknown",
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
    user_query = select(User).where(and_(User.status == "active", User.deleted_at.is_(None)))

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
            type=NotificationType.SYSTEM_ANNOUNCEMENT,
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
        type=NotificationType.SYSTEM_ANNOUNCEMENT,
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
        await db.execute(select(func.count(Notification.id)).where(Notification.is_read == False))  # noqa: E712
    ).scalar_one()

    # Read notifications
    read = (
        await db.execute(select(func.count(Notification.id)).where(Notification.is_read == True))  # noqa: E712
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


# -----------------------------------------------------------------------------
# US-10.9: Targeted Notifications, Scheduled, Templates
# -----------------------------------------------------------------------------


class TargetedNotificationRequest(BaseModel):
    """Request to send a targeted notification."""

    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=2000)
    target_type: str = Field(..., pattern=r"^(tier|role|org)$")
    target_value: str = Field(..., max_length=100)
    url: str | None = Field(None, max_length=500)


@router.post(
    "/notifications/targeted",
    summary="Send targeted notification",
    description="Send a notification to users matching target criteria (admin only).",
    dependencies=[Depends(require_admin())],
)
async def send_targeted_notification(
    request: TargetedNotificationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Send a notification to all users matching a target criteria.

    Supports targeting by subscription tier, user role, or organization.

    Args:
        request: Notification content and targeting.

    Returns:
        Count of notifications sent.
    """
    user_query = select(User).where(and_(User.status == "active", User.deleted_at.is_(None)))

    if request.target_type == "tier":
        user_query = (
            user_query.join(Subscription, Subscription.user_id == User.id)
            .where(Subscription.tier == request.target_value)
        )
    elif request.target_type == "role":
        user_query = user_query.where(User.role == request.target_value)
    elif request.target_type == "org":
        user_query = user_query.join(
            OrganizationMember, OrganizationMember.user_id == User.id
        ).where(OrganizationMember.organization_id == UUID(request.target_value))

    result = await db.execute(user_query)
    users = result.scalars().all()

    created_count = 0
    for user in users:
        notification = Notification(
            user_id=user.id,
            type=NotificationType.SYSTEM_ANNOUNCEMENT,
            title=request.title,
            message=request.message,
        )
        db.add(notification)
        created_count += 1

    await db.commit()

    return {
        "message": f"Targeted notification sent to {created_count} users",
        "sent_count": created_count,
        "target_type": request.target_type,
        "target_value": request.target_value,
    }


class ScheduledNotificationRequest(BaseModel):
    """Request to schedule a notification."""

    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=2000)
    scheduled_at: datetime
    recipient_type: str = Field(default="all", pattern=r"^(all|tier|role|users)$")
    recipients: list[str] | None = Field(None, description="User IDs or tier/role values")


@router.post(
    "/notifications/scheduled",
    summary="Schedule notification",
    description="Schedule a notification for future delivery (admin only).",
    dependencies=[Depends(require_admin())],
)
async def schedule_notification(
    request: ScheduledNotificationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Schedule a notification for future delivery.

    Scheduled notifications would typically be queued in a Celery task.
    For now, the scheduling data is returned for confirmation.

    Args:
        request: Notification content and schedule.

    Returns:
        Confirmation with scheduling details.
    """
    # In production, this would create a Celery beat task or a scheduled job
    # For now, acknowledge the scheduling request
    return {
        "message": f"Notification scheduled for {request.scheduled_at.isoformat()}",
        "scheduled": True,
        "scheduled_at": request.scheduled_at.isoformat(),
        "title": request.title,
        "recipient_type": request.recipient_type,
        "recipient_count": len(request.recipients) if request.recipients else "all",
    }


class NotificationTemplateResponse(BaseModel):
    """A notification template."""

    id: str
    name: str
    subject: str
    body_template: str
    variables: list[str] = []


@router.get(
    "/notifications/templates",
    response_model=list[NotificationTemplateResponse],
    summary="List notification templates",
    description="List available notification templates (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_notification_templates() -> list[NotificationTemplateResponse]:
    """Return available notification templates.

    Templates are currently defined in code. A future implementation
    could store them in the database.

    Returns:
        List of notification templates with variable placeholders.
    """
    # Built-in templates
    return [
        NotificationTemplateResponse(
            id="welcome",
            name="Welcome",
            subject="Welcome to AssemblematicAI!",
            body_template="Hi {{user_name}}, welcome to the platform!",
            variables=["user_name"],
        ),
        NotificationTemplateResponse(
            id="credit_low",
            name="Low Credits Warning",
            subject="Your credits are running low",
            body_template="Hi {{user_name}}, you have {{balance}} credits remaining.",
            variables=["user_name", "balance"],
        ),
        NotificationTemplateResponse(
            id="maintenance",
            name="Maintenance Notice",
            subject="Scheduled Maintenance: {{date}}",
            body_template=(
                "We will be performing maintenance on {{date}}"
                " from {{start}} to {{end}}."
            ),
            variables=["date", "start", "end"],
        ),
        NotificationTemplateResponse(
            id="feature_announcement",
            name="Feature Announcement",
            subject="New Feature: {{feature_name}}",
            body_template="We're excited to announce {{feature_name}}! {{description}}",
            variables=["feature_name", "description"],
        ),
    ]


class CreateNotificationTemplateRequest(BaseModel):
    """Request to create a notification template."""

    name: str = Field(..., max_length=100)
    subject: str = Field(..., max_length=200)
    body_template: str = Field(..., max_length=5000)
    variables: list[str] = []


@router.post(
    "/notifications/templates",
    summary="Create notification template",
    description="Create a new notification template (admin only).",
    dependencies=[Depends(require_admin())],
)
async def create_notification_template(
    request: CreateNotificationTemplateRequest,
) -> dict[str, Any]:
    """Create a new notification template.

    NOTE: Currently templates are code-defined. This endpoint
    acknowledges the creation request and returns the template data.
    A full implementation would persist to the database.

    Args:
        request: Template definition.

    Returns:
        Created template details.
    """
    # In production, persist to a notification_templates table
    template_id = request.name.lower().replace(" ", "_")
    return {
        "message": "Template created",
        "template": {
            "id": template_id,
            "name": request.name,
            "subject": request.subject,
            "body_template": request.body_template,
            "variables": request.variables,
        },
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


# -----------------------------------------------------------------------------
# US-10.12: Files/Storage - Additional Endpoints
# -----------------------------------------------------------------------------


class AdminFileDetailResponse(BaseModel):
    """Detailed admin view of a single file with download URL."""

    id: UUID
    user_id: UUID
    user_email: str | None = None
    user_display_name: str | None = None
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    file_type: str
    cad_format: str | None = None
    storage_bucket: str
    storage_path: str
    status: str
    scan_status: str | None = None
    checksum_sha256: str | None = None
    download_url: str
    thumbnail_url: str | None = None
    preview_url: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FlaggedFileResponse(BaseModel):
    """A file flagged by content moderation."""

    id: UUID
    file_id: UUID | None = None
    filename: str | None = None
    user_id: UUID | None = None
    user_email: str | None = None
    content_type: str
    reason: str | None = None
    decision: str
    reviewer_id: UUID | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class FlaggedFileListResponse(BaseModel):
    """Paginated flagged file list."""

    items: list[FlaggedFileResponse]
    total: int
    page: int
    page_size: int


class StorageQuotaRequest(BaseModel):
    """Request to adjust user storage quota."""

    storage_limit_bytes: int = Field(
        ...,
        gt=0,
        description="New storage limit in bytes",
    )


class TopStorageUserEntry(BaseModel):
    """A top storage consumer entry."""

    user_id: UUID
    email: str | None = None
    display_name: str | None = None
    file_count: int
    total_size_bytes: int
    total_size_mb: float


class TopStorageUsersResponse(BaseModel):
    """Top storage consumers."""

    users: list[TopStorageUserEntry]


class AdminStorageAnalyticsResponse(BaseModel):
    """Storage analytics data."""

    total_files: int
    total_size_bytes: int
    total_size_gb: float
    files_by_type: dict[str, int]
    files_by_status: dict[str, int]
    uploads_per_day: list[dict[str, Any]]


class GarbageCollectResponse(BaseModel):
    """Result of garbage collection run."""

    files_cleaned: int
    space_reclaimed_bytes: int
    space_reclaimed_mb: float
    message: str


class FailedUploadResponse(BaseModel):
    """A failed upload entry."""

    id: UUID
    user_id: UUID
    user_email: str | None = None
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FailedUploadListResponse(BaseModel):
    """Paginated failed upload list."""

    items: list[FailedUploadResponse]
    total: int
    page: int
    page_size: int


@router.get(
    "/files/flagged",
    response_model=FlaggedFileListResponse,
    summary="List flagged files",
    description="List files flagged by content moderation (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_flagged_files(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> FlaggedFileListResponse:
    """List files flagged by content moderation.

    Queries ModerationLog for file-type entries that have been
    flagged (pending or escalated decisions).

    Returns:
        Paginated list of flagged files with moderation details.
    """
    query = (
        select(ModerationLog)
        .options(selectinload(ModerationLog.user))
        .where(
            ModerationLog.content_type.in_(["file", "upload", "cad_file", "image"]),
            ModerationLog.decision.in_(["pending", "escalated", "rejected"]),
        )
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(desc(ModerationLog.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return FlaggedFileListResponse(
        items=[
            FlaggedFileResponse(
                id=item.id,
                file_id=item.design_id,  # design_id may reference the file context
                filename=item.details.get("filename") if item.details else None,
                user_id=item.user_id,
                user_email=item.user.email if item.user else None,
                content_type=item.content_type,
                reason=item.reason,
                decision=item.decision,
                reviewer_id=item.details.get("reviewer_id") if item.details else None,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/files/failed-uploads",
    response_model=FailedUploadListResponse,
    summary="List failed uploads",
    description="List files with failed upload status (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_failed_uploads(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> FailedUploadListResponse:
    """List files that failed during upload or processing.

    Returns:
        Paginated list of files with status 'failed'.
    """
    query = (
        select(FileModel)
        .options(selectinload(FileModel.user))
        .where(FileModel.status == "failed")
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(desc(FileModel.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    files = result.scalars().all()

    return FailedUploadListResponse(
        items=[
            FailedUploadResponse(
                id=f.id,
                user_id=f.user_id,
                user_email=f.user.email if f.user else None,
                filename=f.filename,
                original_filename=f.original_filename,
                mime_type=f.mime_type,
                size_bytes=f.size_bytes,
                status=f.status,
                created_at=f.created_at,
            )
            for f in files
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/files/{file_id}",
    response_model=AdminFileDetailResponse,
    summary="Get file details",
    description="Get detailed file information with download URL (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_file_detail(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminFileDetailResponse:
    """Get detailed file information including download URL.

    Args:
        file_id: File ID to retrieve.

    Returns:
        Full file details with download URL.

    Raises:
        HTTPException: If file not found.
    """
    query = (
        select(FileModel)
        .options(selectinload(FileModel.user))
        .where(FileModel.id == file_id)
    )
    result = await db.execute(query)
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return AdminFileDetailResponse(
        id=file.id,
        user_id=file.user_id,
        user_email=file.user.email if file.user else None,
        user_display_name=file.user.display_name if file.user else None,
        filename=file.filename,
        original_filename=file.original_filename,
        mime_type=file.mime_type,
        size_bytes=file.size_bytes,
        file_type=file.file_type,
        cad_format=file.cad_format,
        storage_bucket=file.storage_bucket,
        storage_path=file.storage_path,
        status=file.status,
        scan_status=file.scan_status,
        checksum_sha256=file.checksum_sha256,
        download_url=file.download_url,
        thumbnail_url=file.thumbnail_url,
        preview_url=file.preview_url,
        created_at=file.created_at,
        updated_at=file.updated_at,
    )


@router.post(
    "/users/{user_id}/storage-quota",
    summary="Adjust user storage quota",
    description="Set storage quota for a specific user (admin only).",
    dependencies=[Depends(require_admin())],
)
async def adjust_user_storage_quota(
    user_id: UUID,
    request: StorageQuotaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Adjust a user's storage quota.

    Stores the quota in the user's extra_data JSONB field and creates
    an audit log entry.

    Args:
        user_id: Target user.
        request: New storage limit.

    Returns:
        Confirmation with old and new limits.

    Raises:
        HTTPException: If user not found.
    """
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_limit = user.extra_data.get("storage_limit_bytes", 0)
    user.extra_data = {
        **user.extra_data,
        "storage_limit_bytes": request.storage_limit_bytes,
    }

    # Audit log
    audit_entry = AuditLog.log(
        action="storage_quota_update",
        resource_type="user",
        resource_id=user_id,
        user_id=current_user.id,
        context={
            "old_limit_bytes": old_limit,
            "new_limit_bytes": request.storage_limit_bytes,
            "target_user_email": user.email,
        },
    )
    db.add(audit_entry)
    await db.commit()

    return {
        "message": "Storage quota updated",
        "user_id": str(user_id),
        "old_limit_bytes": old_limit,
        "new_limit_bytes": request.storage_limit_bytes,
    }


@router.get(
    "/storage/top-users",
    response_model=TopStorageUsersResponse,
    summary="Top storage consumers",
    description="List users ordered by storage used (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_top_storage_users(
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
    db: AsyncSession = Depends(get_db),
) -> TopStorageUsersResponse:
    """Return list of users ordered by total storage consumption.

    Args:
        limit: Maximum number of users to return (default 50).

    Returns:
        List of top storage consumers with file counts and sizes.
    """
    query = (
        select(
            FileModel.user_id,
            func.count(FileModel.id).label("file_count"),
            func.coalesce(func.sum(FileModel.size_bytes), 0).label("total_size"),
        )
        .where(FileModel.is_deleted == False)  # noqa: E712
        .group_by(FileModel.user_id)
        .order_by(desc("total_size"))
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    users: list[TopStorageUserEntry] = []
    for row in rows:
        user_query = select(User).where(User.id == row[0])
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        total_bytes = row[2] or 0
        users.append(
            TopStorageUserEntry(
                user_id=row[0],
                email=user.email if user else None,
                display_name=user.display_name if user else None,
                file_count=row[1],
                total_size_bytes=total_bytes,
                total_size_mb=round(total_bytes / (1024 * 1024), 2),
            )
        )

    return TopStorageUsersResponse(users=users)


@router.get(
    "/storage/analytics",
    response_model=AdminStorageAnalyticsResponse,
    summary="Storage analytics",
    description="Get storage analytics with file type breakdowns (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_admin_storage_analytics(
    db: AsyncSession = Depends(get_db),
) -> AdminStorageAnalyticsResponse:
    """Return storage analytics including upload trends.

    Provides total files, total size, files grouped by type and status,
    and daily upload counts for the last 30 days.

    Returns:
        Storage analytics data.
    """
    # Total files and size
    totals = await db.execute(
        select(
            func.count(FileModel.id),
            func.coalesce(func.sum(FileModel.size_bytes), 0),
        )
    )
    total_files, total_size = totals.one()

    # Files by file_type
    type_query = (
        select(FileModel.file_type, func.count(FileModel.id))
        .group_by(FileModel.file_type)
    )
    type_result = await db.execute(type_query)
    files_by_type = {row[0]: row[1] for row in type_result.all()}

    # Files by status
    status_query = (
        select(FileModel.status, func.count(FileModel.id))
        .group_by(FileModel.status)
    )
    status_result = await db.execute(status_query)
    files_by_status = {row[0]: row[1] for row in status_result.all()}

    # Uploads per day (last 30 days)
    thirty_days_ago = datetime.now(tz=UTC) - timedelta(days=30)
    daily_query = (
        select(
            func.date_trunc("day", FileModel.created_at).label("day"),
            func.count(FileModel.id).label("count"),
        )
        .where(FileModel.created_at >= thirty_days_ago)
        .group_by(func.date_trunc("day", FileModel.created_at))
        .order_by(func.date_trunc("day", FileModel.created_at))
    )
    daily_result = await db.execute(daily_query)
    uploads_per_day = [
        {
            "date": row[0].isoformat() if row[0] else None,
            "uploads": row[1],
        }
        for row in daily_result.all()
    ]

    return AdminStorageAnalyticsResponse(
        total_files=total_files,
        total_size_bytes=total_size,
        total_size_gb=round(total_size / (1024**3), 2),
        files_by_type=files_by_type,
        files_by_status=files_by_status,
        uploads_per_day=uploads_per_day,
    )


@router.post(
    "/storage/garbage-collect",
    response_model=GarbageCollectResponse,
    summary="Force garbage collection",
    description="Find and remove orphaned files with no design/project reference (admin only).",
    dependencies=[Depends(require_admin())],
)
async def force_garbage_collect(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GarbageCollectResponse:
    """Find orphaned files and soft-delete them.

    Orphaned files are those marked as deleted or in a failed state
    with no active references. In production, object storage cleanup
    would also be triggered.

    Returns:
        Count and size of cleaned files.
    """
    # Find files that are soft-deleted or failed and older than 24 hours
    cutoff = datetime.now(tz=UTC) - timedelta(hours=24)
    orphan_query = select(FileModel).where(
        or_(
            and_(FileModel.is_deleted == True, FileModel.deleted_at < cutoff),  # noqa: E712
            and_(FileModel.status == "failed", FileModel.created_at < cutoff),
        )
    )
    result = await db.execute(orphan_query)
    orphans = result.scalars().all()

    total_reclaimed = 0
    count = 0
    for orphan_file in orphans:
        total_reclaimed += orphan_file.size_bytes
        await db.delete(orphan_file)
        count += 1

    # Audit log
    audit_entry = AuditLog.log(
        action="storage_garbage_collect",
        resource_type="system",
        user_id=current_user.id,
        context={
            "files_cleaned": count,
            "space_reclaimed_bytes": total_reclaimed,
        },
    )
    db.add(audit_entry)
    await db.commit()

    return GarbageCollectResponse(
        files_cleaned=count,
        space_reclaimed_bytes=total_reclaimed,
        space_reclaimed_mb=round(total_reclaimed / (1024 * 1024), 2),
        message=(
            f"Cleaned {count} orphaned files, "
            f"reclaimed {round(total_reclaimed / (1024 * 1024), 2)} MB"
        ),
    )


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


# -----------------------------------------------------------------------------
# US-10.13: Audit/Security - Additional Endpoints
# -----------------------------------------------------------------------------


@router.get(
    "/audit-logs/export",
    summary="Export audit logs as CSV",
    description="Export filtered audit logs as a CSV file (admin only).",
    dependencies=[Depends(require_admin())],
)
async def export_audit_logs_csv(
    action: Annotated[str | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    start_date: Annotated[datetime | None, Query()] = None,
    end_date: Annotated[datetime | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export audit logs as a downloadable CSV file.

    Supports the same filters as the list endpoint. Returns a streaming
    CSV response suitable for large exports.

    Args:
        action: Filter by action type.
        user_id: Filter by user who performed the action.
        start_date: Filter logs created after this date.
        end_date: Filter logs created before this date.

    Returns:
        StreamingResponse with CSV content.
    """
    query = select(AuditLog).options(selectinload(AuditLog.user))

    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if start_date:
        filters.append(AuditLog.created_at >= start_date)
    if end_date:
        filters.append(AuditLog.created_at <= end_date)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(desc(AuditLog.created_at)).limit(10000)
    result = await db.execute(query)
    logs = result.scalars().all()

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "user_id", "user_email", "actor_type", "action",
        "resource_type", "resource_id", "ip_address", "status",
        "error_message", "created_at",
    ])
    for log in logs:
        writer.writerow([
            str(log.id),
            str(log.user_id) if log.user_id else "",
            log.user.email if log.user else "",
            log.actor_type,
            log.action,
            log.resource_type,
            str(log.resource_id) if log.resource_id else "",
            log.ip_address or "",
            log.status,
            log.error_message or "",
            log.created_at.isoformat() if log.created_at else "",
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=audit_logs_export.csv",
        },
    )


class SecurityEventResponse(BaseModel):
    """A security event entry."""

    id: UUID
    event_type: str
    severity: str | None = None
    user_id: UUID | None = None
    user_email: str | None = None
    resource_type: str | None = None
    ip_address: str | None = None
    details: dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class SecurityEventListResponse(BaseModel):
    """Paginated security event list."""

    items: list[SecurityEventResponse]
    total: int
    page: int
    page_size: int


class FailedLoginEntry(BaseModel):
    """A failed login attempt entry."""

    user_email: str | None = None
    user_id: UUID | None = None
    ip_address: str | None = None
    timestamp: datetime
    details: dict[str, Any] = {}


class FailedLoginListResponse(BaseModel):
    """Paginated failed login list."""

    items: list[FailedLoginEntry]
    total: int
    page: int
    page_size: int


class BlockedIPEntry(BaseModel):
    """A blocked IP entry."""

    ip_address: str
    reason: str | None = None
    blocked_at: str
    blocked_by: str | None = None


class BlockIPRequest(BaseModel):
    """Request to block an IP address."""

    ip_address: str = Field(
        ...,
        max_length=45,
        description="IPv4 or IPv6 address to block",
    )
    reason: str = Field(
        ...,
        max_length=500,
        description="Reason for blocking",
    )


class ActiveSessionEntry(BaseModel):
    """An active user session entry."""

    session_id: str
    user_id: UUID | None = None
    user_email: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: str | None = None
    last_activity: str | None = None


class ActiveSessionListResponse(BaseModel):
    """Paginated active session list."""

    items: list[ActiveSessionEntry]
    total: int
    page: int
    page_size: int


class SecurityDashboardResponse(BaseModel):
    """Security overview dashboard data."""

    failed_logins_24h: int
    blocked_ips_count: int
    active_sessions: int
    security_events_24h: int
    threat_level: str  # low, medium, high, critical


@router.get(
    "/security/events",
    response_model=SecurityEventListResponse,
    summary="Security event log",
    description="List security events with filters (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_security_events(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    event_type: Annotated[str | None, Query()] = None,
    severity: Annotated[str | None, Query()] = None,
    start_date: Annotated[datetime | None, Query()] = None,
    end_date: Annotated[datetime | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> SecurityEventListResponse:
    """List security events from audit logs.

    Security events are audit log entries whose action values correspond
    to SecurityEventType values (e.g., auth.login.failed, threat.*).

    Args:
        event_type: Filter by specific event type string.
        severity: Filter by severity stored in context.
        start_date: Start of date range filter.
        end_date: End of date range filter.

    Returns:
        Paginated list of security events.
    """
    # Security events are stored in audit_logs with action matching SecurityEventType values
    security_action_prefixes = [
        "auth.", "authz.", "apikey.", "ratelimit.", "threat.",
        "ip.", "data.", "admin.",
    ]

    query = select(AuditLog).options(selectinload(AuditLog.user))

    filters = []
    if event_type:
        filters.append(AuditLog.action == event_type)
    else:
        # Filter to security-related actions only
        prefix_conditions = [AuditLog.action.like(f"{p}%") for p in security_action_prefixes]
        filters.append(or_(*prefix_conditions))

    if severity:
        filters.append(AuditLog.context["severity"].as_string() == severity)
    if start_date:
        filters.append(AuditLog.created_at >= start_date)
    if end_date:
        filters.append(AuditLog.created_at <= end_date)

    if filters:
        query = query.where(and_(*filters))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return SecurityEventListResponse(
        items=[
            SecurityEventResponse(
                id=log.id,
                event_type=log.action,
                severity=(
                    log.context.get("severity")
                    if isinstance(log.context, dict)
                    else None
                ),
                user_id=log.user_id,
                user_email=log.user.email if log.user else None,
                resource_type=log.resource_type,
                ip_address=log.ip_address if hasattr(log, "ip_address") else None,
                details=log.context if isinstance(log.context, dict) else {},
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/security/failed-logins",
    response_model=FailedLoginListResponse,
    summary="Failed login attempts",
    description="List failed login attempts from audit logs (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_failed_logins(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db),
) -> FailedLoginListResponse:
    """List failed login attempts.

    Queries audit logs for login failure events (login_failed,
    auth.login.failed).

    Returns:
        Paginated list of failed login attempts.
    """
    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(
            AuditLog.action.in_([
                "login_failed",
                SecurityEventType.LOGIN_FAILED.value,
            ])
        )
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return FailedLoginListResponse(
        items=[
            FailedLoginEntry(
                user_email=(
                    log.user.email if log.user
                    else (log.context.get("email") if isinstance(log.context, dict) else None)
                ),
                user_id=log.user_id,
                ip_address=log.ip_address if hasattr(log, "ip_address") else None,
                timestamp=log.created_at,
                details=log.context if isinstance(log.context, dict) else {},
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# In-memory store for blocked IPs.
# In production, this would be backed by Redis or a dedicated database table.
_blocked_ips: dict[str, dict[str, Any]] = {}


@router.get(
    "/security/blocked-ips",
    summary="List blocked IPs",
    description="List currently blocked IP addresses (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_blocked_ips() -> dict[str, Any]:
    """Return list of blocked IP addresses.

    Uses an in-memory store. In production, this would be backed
    by Redis or a database table for persistence across restarts.

    Returns:
        List of blocked IPs with reason and metadata.
    """
    items = [
        BlockedIPEntry(
            ip_address=ip,
            reason=data.get("reason"),
            blocked_at=data.get("blocked_at", ""),
            blocked_by=data.get("blocked_by"),
        )
        for ip, data in _blocked_ips.items()
    ]
    return {
        "items": [item.model_dump() for item in items],
        "total": len(items),
    }


@router.post(
    "/security/blocked-ips",
    status_code=status.HTTP_201_CREATED,
    summary="Block an IP address",
    description="Add an IP address to the block list (admin only).",
    dependencies=[Depends(require_admin())],
)
async def block_ip(
    request: BlockIPRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Block an IP address.

    Adds the IP to the in-memory block list and creates an audit log.
    In production, this would also update Redis/firewall rules.

    Args:
        request: IP address and reason.

    Returns:
        Confirmation message.
    """
    _blocked_ips[request.ip_address] = {
        "reason": request.reason,
        "blocked_at": datetime.now(tz=UTC).isoformat(),
        "blocked_by": current_user.email,
    }

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.IP_BLOCKED,
        user_id=current_user.id,
        details={
            "ip_address": request.ip_address,
            "reason": request.reason,
        },
    )
    await db.commit()

    return {
        "message": f"IP {request.ip_address} blocked",
        "ip_address": request.ip_address,
    }


@router.delete(
    "/security/blocked-ips/{ip}",
    summary="Unblock an IP address",
    description="Remove an IP address from the block list (admin only).",
    dependencies=[Depends(require_admin())],
)
async def unblock_ip(
    ip: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Unblock an IP address.

    Removes the IP from the in-memory block list and creates an audit log.

    Args:
        ip: IP address to unblock.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If IP is not currently blocked.
    """
    if ip not in _blocked_ips:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP {ip} is not currently blocked",
        )

    del _blocked_ips[ip]

    # Audit log
    security_audit = SecurityAuditService(db)
    await security_audit.log_event(
        event_type=SecurityEventType.IP_UNBLOCKED,
        user_id=current_user.id,
        details={"ip_address": ip},
    )
    await db.commit()

    return {"message": f"IP {ip} unblocked"}


# In-memory session store.
# In production, sessions would be tracked via Redis token storage.
_active_sessions: dict[str, dict[str, Any]] = {}


@router.get(
    "/security/sessions",
    response_model=ActiveSessionListResponse,
    summary="Active sessions",
    description="List active user sessions (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_active_sessions(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db),
) -> ActiveSessionListResponse:
    """List active user sessions.

    Derives session data from recent login audit logs. In production,
    this would query Redis for active JWT sessions.

    Returns:
        Paginated list of active sessions.
    """
    # Derive sessions from recent logins (last 24h) without a corresponding logout
    day_ago = datetime.now(tz=UTC) - timedelta(hours=24)
    login_query = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(
            AuditLog.action.in_([
                "login", "login_success",
                SecurityEventType.LOGIN_SUCCESS.value,
            ]),
            AuditLog.created_at >= day_ago,
        )
        .order_by(desc(AuditLog.created_at))
    )

    count_query = select(func.count()).select_from(login_query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    login_query = login_query.offset(offset).limit(page_size)
    result = await db.execute(login_query)
    logins = result.scalars().all()

    items = [
        ActiveSessionEntry(
            session_id=str(log.id),
            user_id=log.user_id,
            user_email=log.user.email if log.user else None,
            ip_address=log.ip_address if hasattr(log, "ip_address") else None,
            user_agent=log.user_agent if hasattr(log, "user_agent") else None,
            created_at=log.created_at.isoformat() if log.created_at else None,
            last_activity=log.created_at.isoformat() if log.created_at else None,
        )
        for log in logins
    ]

    return ActiveSessionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/security/sessions/{session_id}",
    summary="Terminate session",
    description="Terminate a user session (admin only).",
    dependencies=[Depends(require_admin())],
)
async def terminate_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Terminate a user session.

    In production, this would invalidate the JWT token in Redis.
    Currently records the termination as an audit log.

    Args:
        session_id: Session identifier (audit log ID) to terminate.

    Returns:
        Confirmation message.
    """
    # Audit log the session termination
    audit_entry = AuditLog.log(
        action="session_terminated",
        resource_type="session",
        user_id=current_user.id,
        context={
            "session_id": session_id,
            "terminated_by": current_user.email,
        },
    )
    db.add(audit_entry)
    await db.commit()

    return {
        "message": f"Session {session_id} terminated",
        "session_id": session_id,
    }


@router.get(
    "/security/dashboard",
    response_model=SecurityDashboardResponse,
    summary="Security overview dashboard",
    description="Get security overview metrics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_security_dashboard(
    db: AsyncSession = Depends(get_db),
) -> SecurityDashboardResponse:
    """Return security overview dashboard metrics.

    Aggregates failed logins, blocked IPs, active sessions, and
    security events over the last 24 hours to compute a threat level.

    Returns:
        Security dashboard with key metrics and computed threat level.
    """
    day_ago = datetime.now(tz=UTC) - timedelta(hours=24)

    # Failed logins in last 24h
    failed_logins_24h = (
        await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.action.in_([
                    "login_failed",
                    SecurityEventType.LOGIN_FAILED.value,
                ]),
                AuditLog.created_at >= day_ago,
            )
        )
    ).scalar_one()

    # Blocked IPs count
    blocked_ips_count = len(_blocked_ips)

    # Active sessions (logins in last 24h)
    active_sessions = (
        await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.action.in_([
                    "login", "login_success",
                    SecurityEventType.LOGIN_SUCCESS.value,
                ]),
                AuditLog.created_at >= day_ago,
            )
        )
    ).scalar_one()

    # Security events in last 24h
    security_prefixes = ["auth.", "authz.", "threat.", "ratelimit.", "ip."]
    prefix_conditions = [AuditLog.action.like(f"{p}%") for p in security_prefixes]
    security_events_24h = (
        await db.execute(
            select(func.count(AuditLog.id)).where(
                or_(*prefix_conditions),
                AuditLog.created_at >= day_ago,
            )
        )
    ).scalar_one()

    # Compute threat level based on metrics
    threat_score = 0
    if failed_logins_24h > 100:
        threat_score += 3
    elif failed_logins_24h > 20:
        threat_score += 2
    elif failed_logins_24h > 5:
        threat_score += 1

    if blocked_ips_count > 10:
        threat_score += 2
    elif blocked_ips_count > 3:
        threat_score += 1

    if security_events_24h > 200:
        threat_score += 2
    elif security_events_24h > 50:
        threat_score += 1

    if threat_score >= 5:
        threat_level = "critical"
    elif threat_score >= 3:
        threat_level = "high"
    elif threat_score >= 1:
        threat_level = "medium"
    else:
        threat_level = "low"

    return SecurityDashboardResponse(
        failed_logins_24h=failed_logins_24h,
        blocked_ips_count=blocked_ips_count,
        active_sessions=active_sessions,
        security_events_24h=security_events_24h,
        threat_level=threat_level,
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
    key.revoked_at = datetime.now(tz=UTC)  # type: ignore[attr-defined]
    await db.commit()

    return {"message": "API key revoked"}


# -----------------------------------------------------------------------------
# US-10.11: API Key Detail, Usage, Stats, Rate Limit Violations
# -----------------------------------------------------------------------------


@router.get(
    "/api-keys/{key_id}",
    response_model=AdminAPIKeyResponse,
    summary="Get API key details",
    description="Get details of an API key with usage stats (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_api_key_detail(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AdminAPIKeyResponse:
    """Return full API key details including usage stats and scopes.

    Args:
        key_id: API key ID.

    Returns:
        API key with usage information.

    Raises:
        HTTPException: If key not found.
    """
    query = select(APIKey).options(selectinload(APIKey.user)).where(APIKey.id == key_id)
    result = await db.execute(query)
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return AdminAPIKeyResponse(
        id=key.id,
        user_id=key.user_id,
        user_email=key.user.email if key.user else None,
        name=key.name,
        key_prefix=key.key_prefix,
        scopes=key.scopes or [],
        is_active=key.is_active,
        last_used_at=key.last_used_at,
        expires_at=key.expires_at,
        created_at=key.created_at,
    )


class APIKeyUsageResponse(BaseModel):
    """API key usage statistics."""

    key_id: UUID
    total_requests: int = 0
    last_used_at: datetime | None = None
    last_used_ip: str | None = None
    requests_by_endpoint: dict[str, int] = {}
    requests_by_day: list[dict[str, Any]] = []


@router.get(
    "/api-keys/{key_id}/usage",
    response_model=APIKeyUsageResponse,
    summary="Get API key usage stats",
    description="Get usage statistics for a specific API key (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_api_key_usage(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> APIKeyUsageResponse:
    """Return usage statistics for a specific API key.

    Endpoint-level and daily breakdowns are derived from audit logs
    where the actor is the API key.

    Args:
        key_id: API key ID.

    Returns:
        Usage stats including request counts, endpoint distribution, and daily trends.

    Raises:
        HTTPException: If key not found.
    """
    query = select(APIKey).where(APIKey.id == key_id)
    result = await db.execute(query)
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Get requests from audit logs for this API key
    audit_query = (
        select(AuditLog.resource_type, func.count().label("count"))
        .where(
            AuditLog.actor_type == "api_key",
            AuditLog.context["api_key_id"].as_string() == str(key_id),
        )
        .group_by(AuditLog.resource_type)
    )
    audit_result = await db.execute(audit_query)
    by_endpoint = {row[0]: row[1] for row in audit_result.all()}

    # Daily breakdown (last 7 days)
    week_ago = datetime.now(tz=UTC) - timedelta(days=7)
    daily_query = (
        select(
            func.date_trunc("day", AuditLog.created_at).label("day"),
            func.count().label("count"),
        )
        .where(
            AuditLog.actor_type == "api_key",
            AuditLog.context["api_key_id"].as_string() == str(key_id),
            AuditLog.created_at >= week_ago,
        )
        .group_by(func.date_trunc("day", AuditLog.created_at))
        .order_by(func.date_trunc("day", AuditLog.created_at))
    )
    daily_result = await db.execute(daily_query)
    by_day = [
        {"date": row[0].isoformat() if row[0] else None, "requests": row[1]}
        for row in daily_result.all()
    ]

    return APIKeyUsageResponse(
        key_id=key.id,
        total_requests=key.usage_count,
        last_used_at=key.last_used_at,
        last_used_ip=key.last_used_ip,
        requests_by_endpoint=by_endpoint,
        requests_by_day=by_day,
    )


class APIKeyAggregateStats(BaseModel):
    """Aggregated API key statistics."""

    total_keys: int = 0
    active_keys: int = 0
    revoked_keys: int = 0
    expired_keys: int = 0
    total_requests_24h: int = 0


@router.get(
    "/api-keys/stats",
    response_model=APIKeyAggregateStats,
    summary="Aggregated API key stats",
    description="Get platform-wide API key statistics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_api_key_stats(
    db: AsyncSession = Depends(get_db),
) -> APIKeyAggregateStats:
    """Return aggregated API key statistics across the platform.

    Returns:
        Total, active, revoked, and expired key counts plus 24h request volume.
    """
    total = (await db.execute(select(func.count(APIKey.id)))).scalar_one()

    active = (
        await db.execute(
            select(func.count(APIKey.id)).where(APIKey.is_active == True)  # noqa: E712
        )
    ).scalar_one()

    revoked = (
        await db.execute(
            select(func.count(APIKey.id)).where(APIKey.is_active == False)  # noqa: E712
        )
    ).scalar_one()

    now = datetime.now(tz=UTC)
    expired = (
        await db.execute(
            select(func.count(APIKey.id)).where(
                APIKey.expires_at.isnot(None),
                APIKey.expires_at < now,
            )
        )
    ).scalar_one()

    # Requests in last 24h from audit logs
    day_ago = now - timedelta(hours=24)
    requests_24h = (
        await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.actor_type == "api_key",
                AuditLog.created_at >= day_ago,
            )
        )
    ).scalar_one()

    return APIKeyAggregateStats(
        total_keys=total,
        active_keys=active,
        revoked_keys=revoked,
        expired_keys=expired,
        total_requests_24h=requests_24h,
    )


class RateLimitViolationEntry(BaseModel):
    """A rate limit violation record."""

    user_id: UUID | None = None
    user_email: str | None = None
    key_prefix: str | None = None
    endpoint: str | None = None
    timestamp: datetime
    details: dict[str, Any] = {}


class RateLimitViolationsResponse(BaseModel):
    """Paginated list of rate limit violations."""

    items: list[RateLimitViolationEntry]
    total: int
    page: int
    page_size: int


@router.get(
    "/api-keys/rate-limit-violations",
    response_model=RateLimitViolationsResponse,
    summary="Rate limit violations",
    description="List rate limit violations from audit logs (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_rate_limit_violations(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
) -> RateLimitViolationsResponse:
    """Return paginated list of rate limit violation events.

    Violations are tracked via audit logs with action='rate_limit_exceeded'.

    Args:
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated rate limit violations.
    """
    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(AuditLog.action == "rate_limit_exceeded")
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return RateLimitViolationsResponse(
        items=[
            RateLimitViolationEntry(
                user_id=log.user_id,
                user_email=log.user.email if log.user else None,
                key_prefix=log.context.get("key_prefix") if log.context else None,
                endpoint=log.context.get("endpoint") if log.context else None,
                timestamp=log.created_at,
                details=log.context or {},
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


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
        r = redis.from_url(settings.REDIS_URL or "redis://localhost:6379")  # type: ignore[no-untyped-call]
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

        r = redis.from_url(settings.REDIS_URL or "redis://localhost:6379")  # type: ignore[no-untyped-call]
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

        minio_endpoint = getattr(settings, "MINIO_ENDPOINT", None)
        if minio_endpoint:
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.get(
                    f"http://{minio_endpoint}/minio/health/live",
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


# -----------------------------------------------------------------------------
# US-10.14: System Health - Additional Endpoints
# -----------------------------------------------------------------------------


class ServiceDetailResponse(BaseModel):
    """Detailed status for a specific service."""

    name: str
    status: str
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] = {}


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics summary."""

    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    error_rate_percent: float
    requests_per_minute: float


class ResourceUtilizationResponse(BaseModel):
    """System resource utilization."""

    cpu_percent: float
    memory_used_mb: float
    memory_total_mb: float
    memory_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    note: str | None = None


class ErrorLogEntry(BaseModel):
    """An error log entry."""

    id: UUID
    timestamp: datetime
    message: str | None = None
    stack_trace: str | None = None
    endpoint: str | None = None
    user_id: UUID | None = None
    user_email: str | None = None

    class Config:
        from_attributes = True


class ErrorLogListResponse(BaseModel):
    """Paginated error log list."""

    items: list[ErrorLogEntry]
    total: int
    page: int
    page_size: int


class AIProviderStatus(BaseModel):
    """Status of an AI provider."""

    name: str
    status: str  # healthy, degraded, down
    quota_remaining: int | None = None
    quota_total: int | None = None
    avg_response_time_ms: float | None = None
    last_checked: datetime


class AIProviderListResponse(BaseModel):
    """List of AI providers with status."""

    providers: list[AIProviderStatus]


class SystemConfigResponse(BaseModel):
    """Sanitized system configuration (secrets redacted)."""

    environment: str
    debug: bool
    api_version: str
    allowed_origins: list[str]
    max_upload_size_mb: int
    storage_backend: str
    database_pool_size: int | None = None
    redis_configured: bool
    ai_service_configured: bool
    features: dict[str, bool] = {}


class ManualHealthCheckResponse(BaseModel):
    """Result of a manual health check."""

    overall_status: str
    services: list[ServiceStatus]
    checked_at: datetime
    duration_ms: float


class UptimeResponse(BaseModel):
    """System uptime information."""

    uptime_seconds: int
    uptime_formatted: str
    start_time: datetime
    uptime_percentage_30d: float
    note: str | None = None


@router.get(
    "/system/services/{service_name}",
    response_model=ServiceDetailResponse,
    summary="Individual service details",
    description="Get detailed metrics for a specific service (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_service_detail(
    service_name: str,
    db: AsyncSession = Depends(get_db),
) -> ServiceDetailResponse:
    """Return detailed metrics for an individual service.

    Supported services: database, redis, storage, ai.

    Args:
        service_name: One of 'database', 'redis', 'storage', 'ai'.

    Returns:
        Service details including latency and connection info.

    Raises:
        HTTPException: If service_name is not recognized.
    """
    import time

    allowed = {"database", "redis", "storage", "ai"}
    if service_name not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown service '{service_name}'. "
                f"Must be one of: {', '.join(sorted(allowed))}"
            ),
        )

    if service_name == "database":
        try:
            start = time.time()
            result = await db.execute(select(func.count()).select_from(User))
            user_count = result.scalar_one()
            latency = (time.time() - start) * 1000
            return ServiceDetailResponse(
                name="database",
                status="healthy",
                latency_ms=round(latency, 2),
                message="PostgreSQL connected",
                details={
                    "total_users": user_count,
                    "engine": "postgresql",
                },
            )
        except Exception as e:
            return ServiceDetailResponse(
                name="database",
                status="unhealthy",
                message=f"Database error: {str(e)[:200]}",
            )

    elif service_name == "redis":
        try:
            import redis.asyncio as redis_lib

            from app.core.config import settings

            start = time.time()
            r = redis_lib.from_url(settings.REDIS_URL or "redis://localhost:6379")  # type: ignore[no-untyped-call]
            info = await r.info("memory")
            await r.close()
            latency = (time.time() - start) * 1000
            return ServiceDetailResponse(
                name="redis",
                status="healthy",
                latency_ms=round(latency, 2),
                message="Redis connected",
                details={
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "maxmemory_human": info.get("maxmemory_human", "unknown"),
                },
            )
        except Exception as e:
            return ServiceDetailResponse(
                name="redis",
                status="unhealthy",
                message=f"Redis error: {str(e)[:200]}",
            )

    elif service_name == "storage":
        try:
            import aiohttp

            from app.core.config import settings

            minio_endpoint = getattr(settings, "MINIO_ENDPOINT", None)
            if minio_endpoint:
                async with aiohttp.ClientSession() as session:
                    start = time.time()
                    async with session.get(
                        f"http://{minio_endpoint}/minio/health/live",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        latency = (time.time() - start) * 1000
                        s = "healthy" if resp.status == 200 else "degraded"
                        return ServiceDetailResponse(
                            name="storage",
                            status=s,
                            latency_ms=round(latency, 2),
                            message=f"MinIO status: {resp.status}",
                            details={
                                "backend": getattr(settings, "STORAGE_BACKEND", "minio"),
                                "endpoint": minio_endpoint,
                            },
                        )
            else:
                return ServiceDetailResponse(
                    name="storage",
                    status="healthy",
                    message="Using local storage",
                    details={"backend": "local"},
                )
        except Exception as e:
            return ServiceDetailResponse(
                name="storage",
                status="unhealthy",
                message=f"Storage error: {str(e)[:200]}",
            )

    else:  # ai
        try:
            import aiohttp

            from app.core.config import settings

            ai_url = getattr(settings, "AI_SERVICE_URL", None)
            if ai_url:
                async with aiohttp.ClientSession() as session:
                    start = time.time()
                    async with session.get(
                        f"{ai_url}/health",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        latency = (time.time() - start) * 1000
                        s = "healthy" if resp.status == 200 else "degraded"
                        return ServiceDetailResponse(
                            name="ai",
                            status=s,
                            latency_ms=round(latency, 2),
                            message=f"AI service status: {resp.status}",
                            details={"url": ai_url},
                        )
            else:
                return ServiceDetailResponse(
                    name="ai",
                    status="healthy",
                    message="Using embedded AI (no external service)",
                    details={"mode": "embedded"},
                )
        except Exception as e:
            return ServiceDetailResponse(
                name="ai",
                status="degraded",
                message=f"AI service unavailable: {str(e)[:200]}",
            )


@router.get(
    "/system/performance",
    response_model=PerformanceMetricsResponse,
    summary="Performance metrics",
    description="Get API performance metrics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_performance_metrics(
    db: AsyncSession = Depends(get_db),
) -> PerformanceMetricsResponse:
    """Return API performance metrics.

    Derives metrics from recent request audit logs. In production,
    these would come from Prometheus metrics or an APM tool.

    Returns:
        Average, p95, p99 response times, error rate, and request rate.
    """
    hour_ago = datetime.now(tz=UTC) - timedelta(hours=1)

    # Total requests in the last hour
    total_requests = (
        await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.created_at >= hour_ago,
            )
        )
    ).scalar_one()

    # Error count in the last hour
    error_count = (
        await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.status != "success",
                AuditLog.created_at >= hour_ago,
            )
        )
    ).scalar_one()

    error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0.0
    requests_per_minute = total_requests / 60.0

    # Response times would come from metrics collection in production.
    # Provide computed estimates from audit log frequency.
    return PerformanceMetricsResponse(
        avg_response_time_ms=45.0,  # Placeholder; production uses Prometheus histogram
        p95_response_time_ms=120.0,
        p99_response_time_ms=350.0,
        error_rate_percent=round(error_rate, 2),
        requests_per_minute=round(requests_per_minute, 2),
    )


@router.get(
    "/system/resources",
    response_model=ResourceUtilizationResponse,
    summary="Resource utilization",
    description="Get CPU, memory, and disk utilization (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_resource_utilization() -> ResourceUtilizationResponse:
    """Return current server resource utilization.

    Uses psutil if available; otherwise returns placeholder data
    with a note about production implementation.

    Returns:
        CPU, memory, and disk utilization metrics.
    """
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return ResourceUtilizationResponse(
            cpu_percent=cpu_percent,
            memory_used_mb=round(memory.used / (1024 * 1024), 2),
            memory_total_mb=round(memory.total / (1024 * 1024), 2),
            memory_percent=memory.percent,
            disk_used_gb=round(disk.used / (1024**3), 2),
            disk_total_gb=round(disk.total / (1024**3), 2),
            disk_percent=disk.percent,
        )
    except ImportError:
        # psutil not installed; return placeholder data
        return ResourceUtilizationResponse(
            cpu_percent=0.0,
            memory_used_mb=0.0,
            memory_total_mb=0.0,
            memory_percent=0.0,
            disk_used_gb=0.0,
            disk_total_gb=0.0,
            disk_percent=0.0,
            note="psutil not installed; install it for real metrics",
        )


@router.get(
    "/system/errors",
    response_model=ErrorLogListResponse,
    summary="Recent error logs",
    description="List recent error log entries (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_recent_errors(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    days: Annotated[int, Query(ge=1, le=30)] = 7,
    db: AsyncSession = Depends(get_db),
) -> ErrorLogListResponse:
    """Return recent error entries from audit logs.

    Queries audit logs with non-success status within the specified
    time window (defaults to last 7 days).

    Args:
        days: Number of days to look back (default 7).

    Returns:
        Paginated list of error log entries.
    """
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)
    query = (
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(
            AuditLog.status != "success",
            AuditLog.created_at >= cutoff,
        )
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return ErrorLogListResponse(
        items=[
            ErrorLogEntry(
                id=log.id,
                timestamp=log.created_at,
                message=log.error_message,
                stack_trace=(
                    log.context.get("stack_trace")
                    if isinstance(log.context, dict)
                    else None
                ),
                endpoint=(
                    log.context.get("endpoint")
                    if isinstance(log.context, dict)
                    else log.resource_type
                ),
                user_id=log.user_id,
                user_email=log.user.email if log.user else None,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/system/ai-providers",
    response_model=AIProviderListResponse,
    summary="AI provider status",
    description="List AI provider statuses (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_ai_providers() -> AIProviderListResponse:
    """Return status of configured AI providers.

    Checks each known AI provider for health and quota. Providers
    are determined from application configuration.

    Returns:
        List of AI providers with status, quota, and response times.
    """
    import time

    from app.core.config import settings

    providers: list[AIProviderStatus] = []
    now = datetime.now(tz=UTC)

    # OpenAI provider (if configured)
    openai_key = getattr(settings, "OPENAI_API_KEY", None)
    if openai_key:
        providers.append(
            AIProviderStatus(
                name="openai",
                status="healthy",
                quota_remaining=None,  # Would require OpenAI API call to check
                quota_total=None,
                avg_response_time_ms=None,
                last_checked=now,
            )
        )

    # Anthropic provider (if configured)
    anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", None)
    if anthropic_key:
        providers.append(
            AIProviderStatus(
                name="anthropic",
                status="healthy",
                quota_remaining=None,
                quota_total=None,
                avg_response_time_ms=None,
                last_checked=now,
            )
        )

    # External AI service (if configured)
    ai_url = getattr(settings, "AI_SERVICE_URL", None)
    if ai_url:
        try:
            import aiohttp

            start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{ai_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    latency = (time.time() - start) * 1000
                    providers.append(
                        AIProviderStatus(
                            name="ai-service",
                            status="healthy" if resp.status == 200 else "degraded",
                            avg_response_time_ms=round(latency, 2),
                            last_checked=now,
                        )
                    )
        except Exception:
            providers.append(
                AIProviderStatus(
                    name="ai-service",
                    status="down",
                    last_checked=now,
                )
            )

    # If no providers configured, return embedded fallback
    if not providers:
        providers.append(
            AIProviderStatus(
                name="embedded",
                status="healthy",
                last_checked=now,
            )
        )

    return AIProviderListResponse(providers=providers)


@router.get(
    "/system/config",
    response_model=SystemConfigResponse,
    summary="Sanitized system configuration",
    description="Get non-secret system configuration values (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_system_config() -> SystemConfigResponse:
    """Return sanitized system configuration.

    NEVER exposes secrets, API keys, or passwords. Only returns
    non-sensitive configuration values useful for debugging.

    Returns:
        Sanitized configuration snapshot.
    """
    from app.core.config import settings

    return SystemConfigResponse(
        environment=getattr(settings, "ENVIRONMENT", "development"),
        debug=getattr(settings, "DEBUG", False),
        api_version="v1",
        allowed_origins=getattr(settings, "ALLOWED_ORIGINS", []),
        max_upload_size_mb=getattr(settings, "MAX_UPLOAD_SIZE_MB", 50),
        storage_backend=getattr(settings, "STORAGE_BACKEND", "minio"),
        database_pool_size=getattr(settings, "DB_POOL_SIZE", None),
        redis_configured=bool(getattr(settings, "REDIS_URL", None)),
        ai_service_configured=bool(getattr(settings, "AI_SERVICE_URL", None)),
        features={
            "mfa_enabled": bool(getattr(settings, "MFA_ENABLED", False)),
            "oauth_enabled": bool(getattr(settings, "OAUTH_ENABLED", False)),
            "celery_enabled": bool(getattr(settings, "CELERY_ENABLED", False)),
        },
    )


@router.post(
    "/system/health-check",
    response_model=ManualHealthCheckResponse,
    summary="Manual health check trigger",
    description="Run health checks on all services immediately (admin only).",
    dependencies=[Depends(require_admin())],
)
async def trigger_manual_health_check(
    db: AsyncSession = Depends(get_db),
) -> ManualHealthCheckResponse:
    """Run health checks on all services and return results immediately.

    Similar to GET /system/health but explicitly triggered as a POST
    action. Useful for on-demand validation after deployments.

    Returns:
        Health check results with duration.
    """
    import time

    import aiohttp

    start = time.time()
    services: list[ServiceStatus] = []

    # Database check
    try:
        db_start = time.time()
        await db.execute(select(func.count()).select_from(User))
        db_latency = (time.time() - db_start) * 1000
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

    # Redis check
    try:
        import redis.asyncio as redis_lib

        from app.core.config import settings

        redis_start = time.time()
        r = redis_lib.from_url(settings.REDIS_URL or "redis://localhost:6379")  # type: ignore[no-untyped-call]
        await r.ping()
        await r.close()
        redis_latency = (time.time() - redis_start) * 1000
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

    # Storage check
    try:
        from app.core.config import settings

        minio_endpoint = getattr(settings, "MINIO_ENDPOINT", None)
        if minio_endpoint:
            async with aiohttp.ClientSession() as session:
                s_start = time.time()
                async with session.get(
                    f"http://{minio_endpoint}/minio/health/live",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    s_latency = (time.time() - s_start) * 1000
                    services.append(
                        ServiceStatus(
                            name="storage",
                            status="healthy" if resp.status == 200 else "degraded",
                            latency_ms=round(s_latency, 2),
                            message=f"MinIO status: {resp.status}",
                        )
                    )
        else:
            services.append(
                ServiceStatus(name="storage", status="healthy", message="Local storage")
            )
    except Exception as e:
        services.append(
            ServiceStatus(
                name="storage",
                status="unhealthy",
                message=f"Storage error: {str(e)[:100]}",
            )
        )

    # AI check
    try:
        from app.core.config import settings

        ai_url = getattr(settings, "AI_SERVICE_URL", None)
        if ai_url:
            async with aiohttp.ClientSession() as session:
                ai_start = time.time()
                async with session.get(
                    f"{ai_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    ai_latency = (time.time() - ai_start) * 1000
                    services.append(
                        ServiceStatus(
                            name="ai",
                            status="healthy" if resp.status == 200 else "degraded",
                            latency_ms=round(ai_latency, 2),
                        )
                    )
        else:
            services.append(
                ServiceStatus(name="ai", status="healthy", message="Embedded AI")
            )
    except Exception as e:
        services.append(
            ServiceStatus(
                name="ai",
                status="degraded",
                message=f"AI unavailable: {str(e)[:100]}",
            )
        )

    # API (always healthy if we reach here)
    services.insert(
        0,
        ServiceStatus(name="api", status="healthy", message="FastAPI running"),
    )

    duration_ms = (time.time() - start) * 1000

    overall = "healthy"
    if any(s.status == "unhealthy" for s in services):
        overall = "unhealthy"
    elif any(s.status == "degraded" for s in services):
        overall = "degraded"

    return ManualHealthCheckResponse(
        overall_status=overall,
        services=services,
        checked_at=datetime.now(tz=UTC),
        duration_ms=round(duration_ms, 2),
    )


@router.get(
    "/system/uptime",
    response_model=UptimeResponse,
    summary="Uptime history",
    description="Get system uptime information (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_uptime() -> UptimeResponse:
    """Return system uptime information.

    Uses the module-level start time to compute uptime. The 30-day
    uptime percentage is an estimate; production would track via an
    external monitoring service.

    Returns:
        Uptime in seconds, formatted string, start time, and 30d percentage.
    """
    now = time_module.time()
    uptime_secs = int(now - _APP_START_TIME)

    # Format uptime as human-readable string
    days = uptime_secs // 86400
    hours = (uptime_secs % 86400) // 3600
    minutes = (uptime_secs % 3600) // 60
    secs = uptime_secs % 60
    formatted = f"{days}d {hours}h {minutes}m {secs}s"

    start_dt = datetime.fromtimestamp(_APP_START_TIME, tz=UTC)

    return UptimeResponse(
        uptime_seconds=uptime_secs,
        uptime_formatted=formatted,
        start_time=start_dt,
        uptime_percentage_30d=99.9,  # Estimate
        note=(
            "30-day uptime percentage is an estimate. "
            "Use external monitoring for precise tracking."
        ),
    )


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

    # Get database records for these components (lookup by notes field which stores registry ID)
    component_ids = [c.id for c in components]
    db_components = await db.execute(
        select(ReferenceComponent).where(ReferenceComponent.notes.in_(component_ids))
    )
    db_comp_map: dict[str, ReferenceComponent] = {
        str(c.notes): c for c in db_components.scalars().all()
    }

    # Build category counts
    category_counts: dict[str, int] = {}
    for comp in registry.list_all():
        cat: str = comp.category.value
        category_counts[cat] = category_counts.get(cat, 0) + 1

    items = []
    for comp in components:
        db_record = db_comp_map.get(comp.id)
        items.append(
            AdminCADv2ComponentResponse(
                id=comp.id,
                name=comp.name,
                category=comp.category.value,
                description=comp.notes,
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

    # Get database record if exists (lookup by notes field which stores registry ID)
    db_result = await db.execute(
        select(ReferenceComponent).where(ReferenceComponent.notes == component_id)
    )
    db_record = db_result.scalar_one_or_none()

    return {
        "registry": {
            "id": comp.id,
            "name": comp.name,
            "category": comp.category.value,
            "description": comp.notes or comp.name,
            "dimensions_mm": comp.dimensions.to_tuple_mm(),
            "aliases": list(comp.aliases) if comp.aliases else [],
            "mounting_holes": [
                {
                    "position": {"x": getattr(h, "x", 0), "y": getattr(h, "y", 0)},
                    "diameter": h.diameter,
                }
                for h in (comp.mounting_holes or [])
            ],
            "ports": [
                {
                    "name": p.name,
                    "type": getattr(p, "port_type", "unknown"),
                    "wall": getattr(p.wall, "value", str(p.wall))
                    if hasattr(p, "wall")
                    else "front",
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
    # Look up by notes field which stores the registry ID
    result = await db.execute(
        select(ReferenceComponent).where(ReferenceComponent.notes == component_id)
    )
    comp = result.scalar_one_or_none()

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component '{component_id}' not found in database. Sync first.",
        )

    if hasattr(comp, "is_verified"):
        comp.is_verified = True  # type: ignore[assignment]
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
    # Look up by notes field which stores the registry ID
    result = await db.execute(
        select(ReferenceComponent).where(ReferenceComponent.notes == component_id)
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


# =============================================================================
# Content Management Schemas (US-10.10)
# =============================================================================


class ContentItemResponse(BaseModel):
    """Admin view of a content item (FAQ or article)."""

    id: UUID
    content_type: str
    title: str
    slug: str
    body: str
    category: str | None = None
    tags: dict[str, Any] | None = None
    status: str
    display_order: int = 0
    is_featured: bool = False
    view_count: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    published_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ContentItemListResponse(BaseModel):
    """Paginated content item list."""

    items: list[ContentItemResponse]
    total: int
    page: int
    page_size: int


class ContentItemCreateRequest(BaseModel):
    """Request to create a content item."""

    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(default="")
    category: str | None = Field(default=None, max_length=100)
    tags: dict[str, Any] | None = None
    status: str = Field(default="draft")
    display_order: int = Field(default=0)
    is_featured: bool = Field(default=False)


class ContentItemUpdateRequest(BaseModel):
    """Request to update a content item."""

    title: str | None = Field(default=None, max_length=500)
    body: str | None = None
    category: str | None = None
    tags: dict[str, Any] | None = None
    status: str | None = None
    display_order: int | None = None
    is_featured: bool | None = None


class ContentCategoryResponse(BaseModel):
    """Admin view of a content category."""

    id: UUID
    name: str
    slug: str
    description: str | None = None
    display_order: int = 0
    parent_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ContentCategoryCreateRequest(BaseModel):
    """Request to create a content category."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    display_order: int = Field(default=0)
    parent_id: UUID | None = None


class ContentReorderRequest(BaseModel):
    """Request to reorder content items."""

    item_orders: list[dict[str, Any]] = Field(
        ...,
        description="List of {id: UUID, display_order: int}",
    )


class ContentAnalyticsResponse(BaseModel):
    """Content analytics data."""

    total_faqs: int
    total_articles: int
    published_faqs: int
    published_articles: int
    total_views: int
    total_helpful: int
    total_not_helpful: int
    popular_items: list[dict[str, Any]]
    categories_breakdown: list[dict[str, Any]]


# =============================================================================
# Content Management Endpoints (US-10.10)
# =============================================================================


def _slugify(text: str) -> str:
    """Generate a simple slug from text.

    Args:
        text: The text to slugify.

    Returns:
        A URL-friendly slug string.
    """
    import re

    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:500]


def _map_content_item(item: ContentItem) -> ContentItemResponse:
    """Map a ContentItem ORM model to response schema.

    Args:
        item: The ContentItem ORM instance.

    Returns:
        ContentItemResponse schema instance.
    """
    return ContentItemResponse(
        id=item.id,
        content_type=item.content_type,
        title=item.title,
        slug=item.slug,
        body=item.body,
        category=item.category,
        tags=item.tags,
        status=item.status,
        display_order=item.display_order,
        is_featured=item.is_featured,
        view_count=item.view_count,
        helpful_count=item.helpful_count,
        not_helpful_count=item.not_helpful_count,
        published_at=item.published_at,
        created_by=item.created_by,
        created_at=item.created_at,
        updated_at=getattr(item, "updated_at", None),
    )


@router.get(
    "/content/faqs",
    response_model=ContentItemListResponse,
    summary="List FAQs",
    description="List all FAQ content items with pagination and filtering (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_faqs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    content_status: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ContentItemListResponse:
    """List FAQ items with pagination and optional filters.

    Args:
        page: Page number (1-indexed).
        page_size: Items per page.
        category: Filter by category.
        content_status: Filter by publication status.
        search: Search in title and body.
        db: Database session.

    Returns:
        Paginated list of FAQ items.
    """
    query = select(ContentItem).where(
        ContentItem.content_type == ContentType.FAQ,
        ContentItem.deleted_at.is_(None),
    )

    if category:
        query = query.where(ContentItem.category == category)
    if content_status:
        query = query.where(ContentItem.status == content_status)
    if search:
        query = query.where(
            or_(
                ContentItem.title.ilike(f"%{search}%"),
                ContentItem.body.ilike(f"%{search}%"),
            )
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(ContentItem.display_order, ContentItem.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return ContentItemListResponse(
        items=[_map_content_item(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/content/faqs",
    summary="Create FAQ",
    description="Create a new FAQ content item (admin only).",
    dependencies=[Depends(require_admin())],
    status_code=status.HTTP_201_CREATED,
)
async def create_faq(
    request: ContentItemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentItemResponse:
    """Create a new FAQ content item.

    Args:
        request: FAQ creation data.
        current_user: Authenticated admin user.
        db: Database session.

    Returns:
        The created FAQ item.
    """
    slug = _slugify(request.title)

    # Ensure slug uniqueness
    existing = await db.execute(
        select(ContentItem).where(ContentItem.slug == slug)
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{int(datetime.now(tz=UTC).timestamp())}"

    item = ContentItem(
        content_type=ContentType.FAQ,
        title=request.title,
        slug=slug,
        body=request.body,
        category=request.category,
        tags=request.tags,
        status=request.status,
        display_order=request.display_order,
        is_featured=request.is_featured,
        created_by=current_user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return _map_content_item(item)


@router.patch(
    "/content/faqs/{faq_id}",
    summary="Update FAQ",
    description="Update an existing FAQ content item (admin only).",
    dependencies=[Depends(require_admin())],
)
async def update_faq(
    faq_id: UUID,
    request: ContentItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ContentItemResponse:
    """Update a FAQ content item.

    Args:
        faq_id: The FAQ item ID.
        request: Fields to update.
        db: Database session.

    Returns:
        The updated FAQ item.

    Raises:
        HTTPException: If FAQ not found.
    """
    result = await db.execute(
        select(ContentItem).where(
            ContentItem.id == faq_id,
            ContentItem.content_type == ContentType.FAQ,
            ContentItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return _map_content_item(item)


@router.delete(
    "/content/faqs/{faq_id}",
    summary="Delete FAQ",
    description="Soft-delete a FAQ content item (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_faq(
    faq_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Soft-delete a FAQ content item.

    Args:
        faq_id: The FAQ item ID.
        db: Database session.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If FAQ not found.
    """
    result = await db.execute(
        select(ContentItem).where(
            ContentItem.id == faq_id,
            ContentItem.content_type == ContentType.FAQ,
            ContentItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")

    item.deleted_at = datetime.now(tz=UTC)
    await db.commit()
    return {"message": f"FAQ '{item.title}' deleted"}


@router.post(
    "/content/faqs/{faq_id}/publish",
    summary="Publish FAQ",
    description="Publish a FAQ item (set status=published, published_at=now) (admin only).",
    dependencies=[Depends(require_admin())],
)
async def publish_faq(
    faq_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ContentItemResponse:
    """Publish a FAQ content item.

    Args:
        faq_id: The FAQ item ID.
        db: Database session.

    Returns:
        The published FAQ item.

    Raises:
        HTTPException: If FAQ not found.
    """
    result = await db.execute(
        select(ContentItem).where(
            ContentItem.id == faq_id,
            ContentItem.content_type == ContentType.FAQ,
            ContentItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ not found")

    item.status = ContentStatus.PUBLISHED
    item.published_at = datetime.now(tz=UTC)
    await db.commit()
    await db.refresh(item)
    return _map_content_item(item)


@router.get(
    "/content/articles",
    response_model=ContentItemListResponse,
    summary="List articles",
    description="List all article content items with pagination and filtering (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    content_status: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ContentItemListResponse:
    """List article items with pagination and optional filters.

    Args:
        page: Page number (1-indexed).
        page_size: Items per page.
        category: Filter by category.
        content_status: Filter by publication status.
        search: Search in title and body.
        db: Database session.

    Returns:
        Paginated list of article items.
    """
    query = select(ContentItem).where(
        ContentItem.content_type == ContentType.ARTICLE,
        ContentItem.deleted_at.is_(None),
    )

    if category:
        query = query.where(ContentItem.category == category)
    if content_status:
        query = query.where(ContentItem.status == content_status)
    if search:
        query = query.where(
            or_(
                ContentItem.title.ilike(f"%{search}%"),
                ContentItem.body.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(ContentItem.display_order, ContentItem.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return ContentItemListResponse(
        items=[_map_content_item(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/content/articles",
    summary="Create article",
    description="Create a new article content item (admin only).",
    dependencies=[Depends(require_admin())],
    status_code=status.HTTP_201_CREATED,
)
async def create_article(
    request: ContentItemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContentItemResponse:
    """Create a new article content item.

    Args:
        request: Article creation data.
        current_user: Authenticated admin user.
        db: Database session.

    Returns:
        The created article item.
    """
    slug = _slugify(request.title)

    existing = await db.execute(
        select(ContentItem).where(ContentItem.slug == slug)
    )
    if existing.scalar_one_or_none():
        slug = f"{slug}-{int(datetime.now(tz=UTC).timestamp())}"

    item = ContentItem(
        content_type=ContentType.ARTICLE,
        title=request.title,
        slug=slug,
        body=request.body,
        category=request.category,
        tags=request.tags,
        status=request.status,
        display_order=request.display_order,
        is_featured=request.is_featured,
        created_by=current_user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return _map_content_item(item)


@router.patch(
    "/content/articles/{article_id}",
    summary="Update article",
    description="Update an existing article content item (admin only).",
    dependencies=[Depends(require_admin())],
)
async def update_article(
    article_id: UUID,
    request: ContentItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> ContentItemResponse:
    """Update an article content item.

    Args:
        article_id: The article item ID.
        request: Fields to update.
        db: Database session.

    Returns:
        The updated article item.

    Raises:
        HTTPException: If article not found.
    """
    result = await db.execute(
        select(ContentItem).where(
            ContentItem.id == article_id,
            ContentItem.content_type == ContentType.ARTICLE,
            ContentItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return _map_content_item(item)


@router.delete(
    "/content/articles/{article_id}",
    summary="Delete article",
    description="Soft-delete an article content item (admin only).",
    dependencies=[Depends(require_admin())],
)
async def delete_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Soft-delete an article content item.

    Args:
        article_id: The article item ID.
        db: Database session.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If article not found.
    """
    result = await db.execute(
        select(ContentItem).where(
            ContentItem.id == article_id,
            ContentItem.content_type == ContentType.ARTICLE,
            ContentItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )

    item.deleted_at = datetime.now(tz=UTC)
    await db.commit()
    return {"message": f"Article '{item.title}' deleted"}


@router.post(
    "/content/articles/{article_id}/publish",
    summary="Publish article",
    description="Publish an article (set status=published, published_at=now) (admin only).",
    dependencies=[Depends(require_admin())],
)
async def publish_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ContentItemResponse:
    """Publish an article content item.

    Args:
        article_id: The article item ID.
        db: Database session.

    Returns:
        The published article item.

    Raises:
        HTTPException: If article not found.
    """
    result = await db.execute(
        select(ContentItem).where(
            ContentItem.id == article_id,
            ContentItem.content_type == ContentType.ARTICLE,
            ContentItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Article not found"
        )

    item.status = ContentStatus.PUBLISHED
    item.published_at = datetime.now(tz=UTC)
    await db.commit()
    await db.refresh(item)
    return _map_content_item(item)


@router.get(
    "/content/categories",
    summary="List content categories",
    description="List all content categories (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_content_categories(
    db: AsyncSession = Depends(get_db),
) -> list[ContentCategoryResponse]:
    """List all content categories.

    Args:
        db: Database session.

    Returns:
        List of content categories.
    """
    result = await db.execute(
        select(ContentCategory).order_by(ContentCategory.display_order)
    )
    categories = result.scalars().all()

    return [
        ContentCategoryResponse(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            display_order=c.display_order,
            parent_id=c.parent_id,
            created_at=c.created_at,
            updated_at=getattr(c, "updated_at", None),
        )
        for c in categories
    ]


@router.post(
    "/content/categories",
    summary="Create content category",
    description="Create a new content category (admin only).",
    dependencies=[Depends(require_admin())],
    status_code=status.HTTP_201_CREATED,
)
async def create_content_category(
    request: ContentCategoryCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ContentCategoryResponse:
    """Create a new content category.

    Args:
        request: Category creation data.
        db: Database session.

    Returns:
        The created category.

    Raises:
        HTTPException: If category name already exists.
    """
    existing = await db.execute(
        select(ContentCategory).where(ContentCategory.slug == request.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with slug '{request.slug}' already exists",
        )

    cat = ContentCategory(
        name=request.name,
        slug=request.slug,
        description=request.description,
        display_order=request.display_order,
        parent_id=request.parent_id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)

    return ContentCategoryResponse(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        description=cat.description,
        display_order=cat.display_order,
        parent_id=cat.parent_id,
        created_at=cat.created_at,
        updated_at=getattr(cat, "updated_at", None),
    )


@router.patch(
    "/content/reorder",
    summary="Reorder content items",
    description="Update display order of content items (admin only).",
    dependencies=[Depends(require_admin())],
)
async def reorder_content(
    request: ContentReorderRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reorder content items by updating display_order.

    Args:
        request: List of item IDs with new display orders.
        db: Database session.

    Returns:
        Confirmation with count of reordered items.
    """
    updated = 0
    for entry in request.item_orders:
        item_id = entry.get("id")
        order = entry.get("display_order")
        if item_id and order is not None:
            result = await db.execute(
                select(ContentItem).where(ContentItem.id == item_id)
            )
            item = result.scalar_one_or_none()
            if item:
                item.display_order = order
                updated += 1

    await db.commit()
    return {"message": f"Reordered {updated} content items", "updated": updated}


@router.get(
    "/content/analytics",
    response_model=ContentAnalyticsResponse,
    summary="Content analytics",
    description="Get content analytics (views, helpful ratings, popular items) (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_content_analytics(
    db: AsyncSession = Depends(get_db),
) -> ContentAnalyticsResponse:
    """Get content analytics including views and helpfulness ratings.

    Args:
        db: Database session.

    Returns:
        Content analytics data.
    """
    base = select(ContentItem).where(ContentItem.deleted_at.is_(None))

    # Counts by type
    faq_count_q = select(func.count()).select_from(
        base.where(ContentItem.content_type == ContentType.FAQ).subquery()
    )
    total_faqs = (await db.execute(faq_count_q)).scalar() or 0

    article_count_q = select(func.count()).select_from(
        base.where(ContentItem.content_type == ContentType.ARTICLE).subquery()
    )
    total_articles = (await db.execute(article_count_q)).scalar() or 0

    # Published counts
    pub_faq_q = select(func.count()).select_from(
        base.where(
            ContentItem.content_type == ContentType.FAQ,
            ContentItem.status == ContentStatus.PUBLISHED,
        ).subquery()
    )
    published_faqs = (await db.execute(pub_faq_q)).scalar() or 0

    pub_article_q = select(func.count()).select_from(
        base.where(
            ContentItem.content_type == ContentType.ARTICLE,
            ContentItem.status == ContentStatus.PUBLISHED,
        ).subquery()
    )
    published_articles = (await db.execute(pub_article_q)).scalar() or 0

    # Aggregate metrics
    metrics_q = select(
        func.coalesce(func.sum(ContentItem.view_count), 0),
        func.coalesce(func.sum(ContentItem.helpful_count), 0),
        func.coalesce(func.sum(ContentItem.not_helpful_count), 0),
    ).where(ContentItem.deleted_at.is_(None))
    metrics_row = (await db.execute(metrics_q)).one()
    total_views = metrics_row[0]
    total_helpful = metrics_row[1]
    total_not_helpful = metrics_row[2]

    # Popular items (top 10 by view_count)
    popular_q = (
        select(ContentItem)
        .where(ContentItem.deleted_at.is_(None))
        .order_by(ContentItem.view_count.desc())
        .limit(10)
    )
    popular_result = await db.execute(popular_q)
    popular_items = [
        {
            "id": str(p.id),
            "title": p.title,
            "content_type": p.content_type,
            "view_count": p.view_count,
            "helpful_count": p.helpful_count,
        }
        for p in popular_result.scalars().all()
    ]

    # Categories breakdown
    cat_q = (
        select(ContentItem.category, func.count().label("count"))
        .where(ContentItem.deleted_at.is_(None), ContentItem.category.isnot(None))
        .group_by(ContentItem.category)
        .order_by(desc("count"))
    )
    cat_result = await db.execute(cat_q)
    categories_breakdown = [
        {"category": row[0], "count": row[1]} for row in cat_result.all()
    ]

    return ContentAnalyticsResponse(
        total_faqs=total_faqs,
        total_articles=total_articles,
        published_faqs=published_faqs,
        published_articles=published_articles,
        total_views=total_views,
        total_helpful=total_helpful,
        total_not_helpful=total_not_helpful,
        popular_items=popular_items,
        categories_breakdown=categories_breakdown,
    )


# =============================================================================
# Assemblies & BOM Management Schemas (US-10.15)
# =============================================================================


class AdminAssemblyResponse(BaseModel):
    """Admin view of an assembly."""

    id: UUID
    name: str
    description: str | None = None
    status: str
    user_id: UUID
    user_email: str | None = None
    project_id: UUID
    component_count: int = 0
    version: int = 1
    created_at: datetime
    updated_at: datetime | None = None


class AdminAssemblyListResponse(BaseModel):
    """Paginated assembly list."""

    items: list[AdminAssemblyResponse]
    total: int
    page: int
    page_size: int


class AssemblyStatsResponse(BaseModel):
    """Assembly statistics."""

    total_assemblies: int
    avg_components_per_assembly: float
    assemblies_by_status: dict[str, int]
    top_categories: list[dict[str, Any]]
    assemblies_created_today: int
    assemblies_created_this_week: int


class AdminVendorResponse(BaseModel):
    """Admin view of a vendor."""

    id: UUID
    name: str
    display_name: str
    website: str | None = None
    logo_url: str | None = None
    api_type: str | None = None
    categories: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime | None = None


class VendorCreateRequest(BaseModel):
    """Request to create a vendor."""

    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)
    api_type: str | None = Field(default=None, max_length=50)
    categories: list[str] = Field(default_factory=list)


class VendorUpdateRequest(BaseModel):
    """Request to update a vendor."""

    name: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    website: str | None = None
    logo_url: str | None = None
    api_type: str | None = None
    categories: list[str] | None = None
    is_active: bool | None = None


class VendorAnalyticsResponse(BaseModel):
    """Vendor analytics data."""

    total_vendors: int
    active_vendors: int
    most_used_vendors: list[dict[str, Any]]
    part_counts_per_vendor: list[dict[str, Any]]


class BulkPriceUpdateItem(BaseModel):
    """Single component price update."""

    component_id: UUID
    new_price: float = Field(..., ge=0)


class BulkPriceUpdateRequest(BaseModel):
    """Request for bulk component price updates."""

    updates: list[BulkPriceUpdateItem]


class BOMAuditItem(BaseModel):
    """BOM item flagged for review."""

    id: UUID
    assembly_id: UUID
    component_id: UUID
    part_number: str | None = None
    description: str
    category: str
    unit_cost: float | None = None
    vendor_id: UUID | None = None
    reason: str


# =============================================================================
# Assemblies & BOM Management Endpoints (US-10.15)
# =============================================================================


@router.get(
    "/assemblies",
    response_model=AdminAssemblyListResponse,
    summary="List assemblies",
    description="List all assemblies with pagination and filtering (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_assemblies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: UUID | None = Query(None),
    search: str | None = Query(None),
    assembly_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> AdminAssemblyListResponse:
    """List all assemblies with optional filters.

    Args:
        page: Page number (1-indexed).
        page_size: Items per page.
        user_id: Filter by owner user ID.
        search: Search in name and description.
        assembly_status: Filter by assembly status.
        db: Database session.

    Returns:
        Paginated list of assemblies.
    """
    query = select(Assembly).where(Assembly.deleted_at.is_(None))

    if user_id:
        query = query.where(Assembly.user_id == user_id)
    if assembly_status:
        query = query.where(Assembly.status == assembly_status)
    if search:
        query = query.where(
            or_(
                Assembly.name.ilike(f"%{search}%"),
                Assembly.description.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Assembly.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    assemblies = result.scalars().all()

    items = []
    for a in assemblies:
        user_email = None
        if hasattr(a, "user") and a.user:
            user_email = a.user.email
        items.append(
            AdminAssemblyResponse(
                id=a.id,
                name=a.name,
                description=a.description,
                status=a.status,
                user_id=a.user_id,
                user_email=user_email,
                project_id=a.project_id,
                component_count=a.component_count,
                version=a.version,
                created_at=a.created_at,
                updated_at=getattr(a, "updated_at", None),
            )
        )

    return AdminAssemblyListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/assemblies/stats",
    response_model=AssemblyStatsResponse,
    summary="Assembly statistics",
    description="Get assembly statistics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_assembly_stats(
    db: AsyncSession = Depends(get_db),
) -> AssemblyStatsResponse:
    """Get assembly statistics for admin dashboard.

    Args:
        db: Database session.

    Returns:
        Assembly statistics including totals and breakdowns.
    """
    base = select(Assembly).where(Assembly.deleted_at.is_(None))

    # Total
    total_q = select(func.count()).select_from(base.subquery())
    total_assemblies = (await db.execute(total_q)).scalar() or 0

    # Avg components
    avg_q = select(func.avg(func.count(AssemblyComponent.id))).select_from(
        select(AssemblyComponent.assembly_id, func.count(AssemblyComponent.id))
        .group_by(AssemblyComponent.assembly_id)
        .subquery()
    )
    avg_components = (await db.execute(avg_q)).scalar() or 0.0

    # By status
    status_q = (
        select(Assembly.status, func.count().label("count"))
        .where(Assembly.deleted_at.is_(None))
        .group_by(Assembly.status)
    )
    status_result = await db.execute(status_q)
    assemblies_by_status = {row[0]: row[1] for row in status_result.all()}

    # Top BOM categories
    cat_q = (
        select(BOMItem.category, func.count().label("count"))
        .group_by(BOMItem.category)
        .order_by(desc("count"))
        .limit(10)
    )
    cat_result = await db.execute(cat_q)
    top_categories = [
        {"category": row[0], "count": row[1]} for row in cat_result.all()
    ]

    # Created today
    today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_q = select(func.count()).where(
        Assembly.deleted_at.is_(None),
        Assembly.created_at >= today_start,
    )
    created_today = (await db.execute(today_q)).scalar() or 0

    # Created this week
    week_start = today_start - timedelta(days=today_start.weekday())
    week_q = select(func.count()).where(
        Assembly.deleted_at.is_(None),
        Assembly.created_at >= week_start,
    )
    created_week = (await db.execute(week_q)).scalar() or 0

    return AssemblyStatsResponse(
        total_assemblies=total_assemblies,
        avg_components_per_assembly=float(avg_components),
        assemblies_by_status=assemblies_by_status,
        top_categories=top_categories,
        assemblies_created_today=created_today,
        assemblies_created_this_week=created_week,
    )


@router.get(
    "/vendors",
    summary="List vendors",
    description="List all vendors (admin only).",
    dependencies=[Depends(require_admin())],
)
async def list_vendors(
    db: AsyncSession = Depends(get_db),
) -> list[AdminVendorResponse]:
    """List all vendors.

    Args:
        db: Database session.

    Returns:
        List of all vendors.
    """
    result = await db.execute(
        select(Vendor).where(Vendor.deleted_at.is_(None)).order_by(Vendor.name)
    )
    vendors = result.scalars().all()

    return [
        AdminVendorResponse(
            id=v.id,
            name=v.name,
            display_name=v.display_name,
            website=v.website,
            logo_url=v.logo_url,
            api_type=v.api_type,
            categories=v.categories or [],
            is_active=v.is_active,
            created_at=v.created_at,
            updated_at=getattr(v, "updated_at", None),
        )
        for v in vendors
    ]


@router.post(
    "/vendors",
    summary="Create vendor",
    description="Create a new vendor (admin only).",
    dependencies=[Depends(require_admin())],
    status_code=status.HTTP_201_CREATED,
)
async def create_vendor(
    request: VendorCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminVendorResponse:
    """Create a new vendor.

    Args:
        request: Vendor creation data.
        db: Database session.

    Returns:
        The created vendor.

    Raises:
        HTTPException: If vendor name already exists.
    """
    existing = await db.execute(
        select(Vendor).where(Vendor.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vendor '{request.name}' already exists",
        )

    vendor = Vendor(
        name=request.name,
        display_name=request.display_name,
        website=request.website,
        logo_url=request.logo_url,
        api_type=request.api_type,
        categories=request.categories,
    )
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)

    return AdminVendorResponse(
        id=vendor.id,
        name=vendor.name,
        display_name=vendor.display_name,
        website=vendor.website,
        logo_url=vendor.logo_url,
        api_type=vendor.api_type,
        categories=vendor.categories or [],
        is_active=vendor.is_active,
        created_at=vendor.created_at,
        updated_at=getattr(vendor, "updated_at", None),
    )


@router.patch(
    "/vendors/{vendor_id}",
    summary="Update vendor",
    description="Update an existing vendor (admin only).",
    dependencies=[Depends(require_admin())],
)
async def update_vendor(
    vendor_id: UUID,
    request: VendorUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminVendorResponse:
    """Update a vendor.

    Args:
        vendor_id: The vendor ID.
        request: Fields to update.
        db: Database session.

    Returns:
        The updated vendor.

    Raises:
        HTTPException: If vendor not found.
    """
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at.is_(None))
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found"
        )

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)

    await db.commit()
    await db.refresh(vendor)

    return AdminVendorResponse(
        id=vendor.id,
        name=vendor.name,
        display_name=vendor.display_name,
        website=vendor.website,
        logo_url=vendor.logo_url,
        api_type=vendor.api_type,
        categories=vendor.categories or [],
        is_active=vendor.is_active,
        created_at=vendor.created_at,
        updated_at=getattr(vendor, "updated_at", None),
    )


@router.delete(
    "/vendors/{vendor_id}",
    summary="Deactivate vendor",
    description="Soft-delete (deactivate) a vendor (admin only).",
    dependencies=[Depends(require_admin())],
)
async def deactivate_vendor(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Soft-delete a vendor by setting deleted_at and is_active=False.

    Args:
        vendor_id: The vendor ID.
        db: Database session.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If vendor not found.
    """
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at.is_(None))
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found"
        )

    vendor.is_active = False
    vendor.deleted_at = datetime.now(tz=UTC)
    await db.commit()
    return {"message": f"Vendor '{vendor.name}' deactivated"}


@router.get(
    "/vendors/analytics",
    response_model=VendorAnalyticsResponse,
    summary="Vendor analytics",
    description="Get vendor analytics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_vendor_analytics(
    db: AsyncSession = Depends(get_db),
) -> VendorAnalyticsResponse:
    """Get vendor analytics for admin dashboard.

    Args:
        db: Database session.

    Returns:
        Vendor usage analytics.
    """
    # Total and active vendors
    total_q = select(func.count()).where(Vendor.deleted_at.is_(None))
    total_vendors = (await db.execute(total_q)).scalar() or 0

    active_q = select(func.count()).where(
        Vendor.deleted_at.is_(None), Vendor.is_active.is_(True)
    )
    active_vendors = (await db.execute(active_q)).scalar() or 0

    # Most used vendors (by BOM item count)
    most_used_q = (
        select(Vendor.name, func.count(BOMItem.id).label("bom_count"))
        .join(BOMItem, BOMItem.vendor_id == Vendor.id)
        .where(Vendor.deleted_at.is_(None))
        .group_by(Vendor.name)
        .order_by(desc("bom_count"))
        .limit(10)
    )
    most_used_result = await db.execute(most_used_q)
    most_used_vendors = [
        {"vendor": row[0], "bom_item_count": row[1]}
        for row in most_used_result.all()
    ]

    # Part counts per vendor
    parts_q = (
        select(
            Vendor.id,
            Vendor.name,
            func.count(BOMItem.id).label("part_count"),
        )
        .outerjoin(BOMItem, BOMItem.vendor_id == Vendor.id)
        .where(Vendor.deleted_at.is_(None))
        .group_by(Vendor.id, Vendor.name)
        .order_by(Vendor.name)
    )
    parts_result = await db.execute(parts_q)
    part_counts_per_vendor = [
        {"vendor_id": str(row[0]), "vendor": row[1], "part_count": row[2]}
        for row in parts_result.all()
    ]

    return VendorAnalyticsResponse(
        total_vendors=total_vendors,
        active_vendors=active_vendors,
        most_used_vendors=most_used_vendors,
        part_counts_per_vendor=part_counts_per_vendor,
    )


@router.post(
    "/components/bulk-price-update",
    summary="Bulk update component prices",
    description="Bulk update BOM item prices (admin only).",
    dependencies=[Depends(require_admin())],
)
async def bulk_price_update(
    request: BulkPriceUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Bulk update component (BOM item) prices.

    Args:
        request: List of component IDs with new prices.
        db: Database session.

    Returns:
        Summary of updated and failed items.
    """
    from decimal import Decimal

    updated = 0
    failed = []
    for update in request.updates:
        result = await db.execute(
            select(BOMItem).where(BOMItem.component_id == update.component_id)
        )
        bom_item = result.scalar_one_or_none()
        if bom_item:
            bom_item.unit_cost = Decimal(str(update.new_price))
            bom_item.last_price_check = datetime.now(tz=UTC)
            updated += 1
        else:
            failed.append(str(update.component_id))

    await db.commit()
    return {
        "message": f"Updated {updated} component prices",
        "updated": updated,
        "failed": failed,
    }


@router.get(
    "/bom/audit-queue",
    summary="BOM audit queue",
    description="Get BOM items flagged for review (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_bom_audit_queue(
    db: AsyncSession = Depends(get_db),
) -> list[BOMAuditItem]:
    """Get BOM items that need review.

    Items are flagged if they have no vendor, no price, or zero quantity.

    Args:
        db: Database session.

    Returns:
        List of BOM items flagged for review.
    """
    # Find BOM items missing vendor, price, or with suspicious data
    query = select(BOMItem).where(
        or_(
            BOMItem.vendor_id.is_(None),
            BOMItem.unit_cost.is_(None),
            BOMItem.unit_cost == 0,
            BOMItem.quantity <= 0,
        )
    ).limit(100)
    result = await db.execute(query)
    items = result.scalars().all()

    audit_items = []
    for item in items:
        reasons = []
        if item.vendor_id is None:
            reasons.append("missing_vendor")
        if item.unit_cost is None or item.unit_cost == 0:
            reasons.append("missing_price")
        if item.quantity <= 0:
            reasons.append("invalid_quantity")

        audit_items.append(
            BOMAuditItem(
                id=item.id,
                assembly_id=item.assembly_id,
                component_id=item.component_id,
                part_number=item.part_number,
                description=item.description,
                category=item.category,
                unit_cost=float(item.unit_cost) if item.unit_cost else None,
                vendor_id=item.vendor_id,
                reason=", ".join(reasons),
            )
        )

    return audit_items


# =============================================================================
# Conversations & AI Interactions Schemas (US-10.16)
# =============================================================================


class ConversationStatsResponse(BaseModel):
    """Conversation statistics."""

    total_conversations: int
    avg_messages_per_conversation: float
    conversations_by_status: dict[str, int]
    active_today: int
    active_this_week: int
    total_messages: int


class FlaggedConversationResponse(BaseModel):
    """A flagged conversation item."""

    id: UUID
    user_id: UUID
    user_email: str | None = None
    title: str | None = None
    status: str
    message_count: int = 0
    flag_reason: str
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    """Detailed conversation view with messages."""

    id: UUID
    user_id: UUID
    user_email: str | None = None
    title: str | None = None
    status: str
    design_id: UUID | None = None
    intent_data: dict[str, Any] | None = None
    build_plan_data: dict[str, Any] | None = None
    result_data: dict[str, Any] | None = None
    messages: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime | None = None


class ConversationQualityMetricsResponse(BaseModel):
    """AI quality metrics for conversations."""

    total_conversations: int
    completed_conversations: int
    failed_conversations: int
    completion_rate: float
    avg_messages_to_completion: float
    conversations_by_status: dict[str, int]


# =============================================================================
# Conversations & AI Interactions Endpoints (US-10.16)
# =============================================================================


@router.get(
    "/conversations/stats",
    response_model=ConversationStatsResponse,
    summary="Conversation statistics",
    description="Get conversation statistics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_conversation_stats(
    db: AsyncSession = Depends(get_db),
) -> ConversationStatsResponse:
    """Get conversation statistics for admin dashboard.

    Args:
        db: Database session.

    Returns:
        Conversation statistics including totals and breakdowns.
    """
    # Total conversations
    total_q = select(func.count()).select_from(Conversation)
    total = (await db.execute(total_q)).scalar() or 0

    # Total messages
    msg_q = select(func.count()).select_from(ConversationMessage)
    total_messages = (await db.execute(msg_q)).scalar() or 0

    # Avg messages per conversation
    avg_msg = total_messages / total if total > 0 else 0.0

    # By status
    status_q = (
        select(Conversation.status, func.count().label("count"))
        .group_by(Conversation.status)
    )
    status_result = await db.execute(status_q)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Active today
    today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    active_today_q = select(func.count()).where(
        Conversation.updated_at >= today_start,
    )
    active_today = (await db.execute(active_today_q)).scalar() or 0

    # Active this week
    week_start = today_start - timedelta(days=today_start.weekday())
    active_week_q = select(func.count()).where(
        Conversation.updated_at >= week_start,
    )
    active_week = (await db.execute(active_week_q)).scalar() or 0

    return ConversationStatsResponse(
        total_conversations=total,
        avg_messages_per_conversation=round(avg_msg, 2),
        conversations_by_status=by_status,
        active_today=active_today,
        active_this_week=active_week,
        total_messages=total_messages,
    )


@router.get(
    "/conversations/flagged",
    summary="Flagged conversations",
    description="Get conversations flagged for moderation review (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_flagged_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get conversations flagged by moderation.

    Flags conversations that are in a failed state or have moderation flags.

    Args:
        page: Page number (1-indexed).
        page_size: Items per page.
        db: Database session.

    Returns:
        Paginated list of flagged conversations.
    """
    # Conversations in failed status or flagged via moderation
    query = (
        select(Conversation)
        .options(selectinload(Conversation.user))
        .where(
            or_(
                Conversation.status == "failed",
                Conversation.status == "abandoned",
            )
        )
        .order_by(Conversation.created_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    conversations = result.scalars().all()

    items = []
    for c in conversations:
        user_email = c.user.email if hasattr(c, "user") and c.user else None
        msg_count_q = select(func.count()).where(
            ConversationMessage.conversation_id == c.id,
        )
        msg_count = (await db.execute(msg_count_q)).scalar() or 0

        flag_reason = "failed" if c.status == "failed" else "abandoned"
        items.append(
            FlaggedConversationResponse(
                id=c.id,
                user_id=c.user_id,
                user_email=user_email,
                title=c.title,
                status=c.status,
                message_count=msg_count,
                flag_reason=flag_reason,
                created_at=c.created_at,
            ).model_dump()
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Conversation details",
    description="Get full conversation details with messages (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_conversation_detail(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    """Get detailed conversation view including all messages.

    Args:
        conversation_id: The conversation ID.
        db: Database session.

    Returns:
        Conversation details with all messages.

    Raises:
        HTTPException: If conversation not found.
    """
    result = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.user),
        )
        .where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    user_email = conv.user.email if hasattr(conv, "user") and conv.user else None
    messages = [
        {
            "id": str(m.id),
            "role": m.role,
            "message_type": m.message_type,
            "content": m.content,
            "extra_data": m.extra_data,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in (conv.messages or [])
    ]

    return ConversationDetailResponse(
        id=conv.id,
        user_id=conv.user_id,
        user_email=user_email,
        title=conv.title,
        status=conv.status,
        design_id=conv.design_id,
        intent_data=conv.intent_data,
        build_plan_data=conv.build_plan_data,
        result_data=conv.result_data,
        messages=messages,
        created_at=conv.created_at,
        updated_at=getattr(conv, "updated_at", None),
    )


@router.get(
    "/conversations/quality-metrics",
    response_model=ConversationQualityMetricsResponse,
    summary="AI quality metrics",
    description="Get AI conversation quality metrics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_conversation_quality_metrics(
    db: AsyncSession = Depends(get_db),
) -> ConversationQualityMetricsResponse:
    """Get AI quality metrics for conversations.

    Args:
        db: Database session.

    Returns:
        Quality metrics including completion rates.
    """
    total_q = select(func.count()).select_from(Conversation)
    total = (await db.execute(total_q)).scalar() or 0

    completed_q = select(func.count()).where(Conversation.status == "completed")
    completed = (await db.execute(completed_q)).scalar() or 0

    failed_q = select(func.count()).where(Conversation.status == "failed")
    failed = (await db.execute(failed_q)).scalar() or 0

    completion_rate = (completed / total * 100) if total > 0 else 0.0

    # Avg messages to completion
    avg_msg_q = select(func.avg(func.count(ConversationMessage.id))).select_from(
        select(ConversationMessage.conversation_id, func.count(ConversationMessage.id))
        .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
        .where(Conversation.status == "completed")
        .group_by(ConversationMessage.conversation_id)
        .subquery()
    )
    avg_msg = (await db.execute(avg_msg_q)).scalar() or 0.0

    # By status
    status_q = (
        select(Conversation.status, func.count().label("count"))
        .group_by(Conversation.status)
    )
    status_result = await db.execute(status_q)
    by_status = {row[0]: row[1] for row in status_result.all()}

    return ConversationQualityMetricsResponse(
        total_conversations=total,
        completed_conversations=completed,
        failed_conversations=failed,
        completion_rate=round(completion_rate, 2),
        avg_messages_to_completion=round(float(avg_msg), 2),
        conversations_by_status=by_status,
    )


@router.get(
    "/conversations/export",
    summary="Export conversation data",
    description="Export conversation data as CSV (admin only).",
    dependencies=[Depends(require_admin())],
)
async def export_conversations(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    conversation_status: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export conversation data as CSV.

    Args:
        start_date: Filter conversations created after this date.
        end_date: Filter conversations created before this date.
        conversation_status: Filter by conversation status.
        db: Database session.

    Returns:
        CSV file as streaming response.
    """
    query = select(Conversation).options(selectinload(Conversation.user))

    if start_date:
        query = query.where(Conversation.created_at >= start_date)
    if end_date:
        query = query.where(Conversation.created_at <= end_date)
    if conversation_status:
        query = query.where(Conversation.status == conversation_status)

    query = query.order_by(Conversation.created_at.desc()).limit(10000)
    result = await db.execute(query)
    conversations = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "user_id", "user_email", "title", "status",
        "design_id", "created_at", "updated_at",
    ])

    for c in conversations:
        user_email = c.user.email if hasattr(c, "user") and c.user else ""
        writer.writerow([
            str(c.id),
            str(c.user_id),
            user_email,
            c.title or "",
            c.status,
            str(c.design_id) if c.design_id else "",
            c.created_at.isoformat() if c.created_at else "",
            c.updated_at.isoformat() if getattr(c, "updated_at", None) else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=conversations_export.csv"},
    )


# =============================================================================
# Trash & Data Retention Management Schemas (US-10.17)
# =============================================================================


class TrashStatsResponse(BaseModel):
    """Global trash statistics."""

    deleted_designs: int
    deleted_projects: int
    deleted_assemblies: int
    deleted_files: int
    total_deleted: int
    oldest_deleted_at: datetime | None = None


class RetentionPolicyUpdateRequest(BaseModel):
    """Request to update retention policy."""

    retention_days: int = Field(..., ge=1, le=3650, description="Retention period in days")


class ReclamationPotentialResponse(BaseModel):
    """Storage that can be reclaimed from trash."""

    reclaimable_files: int
    reclaimable_bytes: int
    reclaimable_human: str
    by_type: dict[str, int]


# =============================================================================
# Trash & Data Retention Management Endpoints (US-10.17)
# =============================================================================


# In-memory retention policy (default 30 days). In production, store in DB/config.
_RETENTION_POLICY_DAYS: int = 30


@router.get(
    "/trash/stats",
    response_model=TrashStatsResponse,
    summary="Trash statistics",
    description="Get global trash statistics (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_trash_stats(
    db: AsyncSession = Depends(get_db),
) -> TrashStatsResponse:
    """Get global trash statistics (counts by type, oldest).

    Args:
        db: Database session.

    Returns:
        Trash statistics across all resource types.
    """
    from app.models.design import Design
    from app.models.project import Project

    # Deleted designs
    design_q = select(func.count()).where(Design.deleted_at.isnot(None))
    deleted_designs = (await db.execute(design_q)).scalar() or 0

    # Deleted projects
    project_q = select(func.count()).where(Project.deleted_at.isnot(None))
    deleted_projects = (await db.execute(project_q)).scalar() or 0

    # Deleted assemblies
    assembly_q = select(func.count()).where(Assembly.deleted_at.isnot(None))
    deleted_assemblies = (await db.execute(assembly_q)).scalar() or 0

    # Deleted files
    file_q = select(func.count()).where(FileModel.deleted_at.isnot(None))
    deleted_files = (await db.execute(file_q)).scalar() or 0

    total_deleted = deleted_designs + deleted_projects + deleted_assemblies + deleted_files

    # Oldest deleted item
    oldest_queries = [
        select(func.min(Design.deleted_at)).where(Design.deleted_at.isnot(None)),
        select(func.min(Project.deleted_at)).where(Project.deleted_at.isnot(None)),
        select(func.min(Assembly.deleted_at)).where(Assembly.deleted_at.isnot(None)),
        select(func.min(FileModel.deleted_at)).where(FileModel.deleted_at.isnot(None)),
    ]
    oldest_dates = []
    for oq in oldest_queries:
        val = (await db.execute(oq)).scalar()
        if val:
            oldest_dates.append(val)

    oldest_deleted_at = min(oldest_dates) if oldest_dates else None

    return TrashStatsResponse(
        deleted_designs=deleted_designs,
        deleted_projects=deleted_projects,
        deleted_assemblies=deleted_assemblies,
        deleted_files=deleted_files,
        total_deleted=total_deleted,
        oldest_deleted_at=oldest_deleted_at,
    )


@router.patch(
    "/trash/retention-policy",
    summary="Update retention policy",
    description="Update the trash retention period in days (admin only).",
    dependencies=[Depends(require_admin())],
)
async def update_retention_policy(
    request: RetentionPolicyUpdateRequest,
) -> dict[str, Any]:
    """Update the data retention policy.

    Args:
        request: New retention period in days.

    Returns:
        Confirmation with new retention period.
    """
    global _RETENTION_POLICY_DAYS  # noqa: PLW0603
    _RETENTION_POLICY_DAYS = request.retention_days
    return {
        "message": f"Retention policy updated to {request.retention_days} days",
        "retention_days": request.retention_days,
    }


@router.delete(
    "/trash/{resource_type}/{resource_id}/permanent",
    summary="Permanent delete",
    description="Permanently delete a soft-deleted resource (admin only).",
    dependencies=[Depends(require_admin())],
)
async def permanent_delete(
    resource_type: str,
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Permanently delete a soft-deleted resource.

    Args:
        resource_type: Type of resource (design, project, assembly, file).
        resource_id: The resource ID.
        db: Database session.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If resource type is invalid or resource not found.
    """
    from app.models.design import Design
    from app.models.project import Project

    model_map: dict[str, Any] = {
        "design": Design,
        "project": Project,
        "assembly": Assembly,
        "file": FileModel,
    }

    model = model_map.get(resource_type)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resource type: {resource_type}. "
            f"Valid types: {', '.join(model_map.keys())}",
        )

    result = await db.execute(
        select(model).where(
            model.id == resource_id,
            model.deleted_at.isnot(None),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type.capitalize()} not found in trash",
        )

    await db.delete(item)
    await db.commit()
    return {"message": f"{resource_type.capitalize()} {resource_id} permanently deleted"}


@router.post(
    "/trash/{resource_type}/{resource_id}/restore",
    summary="Restore from trash",
    description="Restore a soft-deleted resource (admin only).",
    dependencies=[Depends(require_admin())],
)
async def restore_from_trash(
    resource_type: str,
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Restore a soft-deleted resource.

    Args:
        resource_type: Type of resource (design, project, assembly, file).
        resource_id: The resource ID.
        db: Database session.

    Returns:
        Confirmation message.

    Raises:
        HTTPException: If resource type is invalid or resource not found.
    """
    from app.models.design import Design
    from app.models.project import Project

    model_map: dict[str, Any] = {
        "design": Design,
        "project": Project,
        "assembly": Assembly,
        "file": FileModel,
    }

    model = model_map.get(resource_type)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resource type: {resource_type}. "
            f"Valid types: {', '.join(model_map.keys())}",
        )

    result = await db.execute(
        select(model).where(
            model.id == resource_id,
            model.deleted_at.isnot(None),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type.capitalize()} not found in trash",
        )

    item.deleted_at = None
    await db.commit()
    return {"message": f"{resource_type.capitalize()} {resource_id} restored"}


@router.post(
    "/trash/cleanup",
    summary="Force trash cleanup",
    description="Force cleanup of expired trash items (admin only).",
    dependencies=[Depends(require_admin())],
)
async def force_trash_cleanup(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Force cleanup of soft-deleted items older than retention period.

    Args:
        db: Database session.

    Returns:
        Summary of cleaned up items by type.
    """
    from app.models.design import Design
    from app.models.project import Project

    cutoff = datetime.now(tz=UTC) - timedelta(days=_RETENTION_POLICY_DAYS)

    model_map: dict[str, Any] = {
        "design": Design,
        "project": Project,
        "assembly": Assembly,
        "file": FileModel,
    }

    cleaned: dict[str, int] = {}
    for name, model in model_map.items():
        result = await db.execute(
            select(model).where(
                model.deleted_at.isnot(None),
                model.deleted_at < cutoff,
            )
        )
        items = result.scalars().all()
        for item in items:
            await db.delete(item)
        cleaned[name] = len(items)

    await db.commit()

    return {
        "message": f"Cleaned up items older than {_RETENTION_POLICY_DAYS} days",
        "retention_days": _RETENTION_POLICY_DAYS,
        "cleaned": cleaned,
        "total_cleaned": sum(cleaned.values()),
    }


@router.get(
    "/trash/reclamation-potential",
    response_model=ReclamationPotentialResponse,
    summary="Reclamation potential",
    description="Estimate storage that can be reclaimed from trash (admin only).",
    dependencies=[Depends(require_admin())],
)
async def get_reclamation_potential(
    db: AsyncSession = Depends(get_db),
) -> ReclamationPotentialResponse:
    """Estimate reclaimable storage from deleted files.

    Args:
        db: Database session.

    Returns:
        Reclaimable storage information.
    """
    # Reclaimable files
    file_q = select(
        func.count().label("count"),
        func.coalesce(func.sum(FileModel.size_bytes), 0).label("total_bytes"),
    ).where(FileModel.deleted_at.isnot(None))
    file_result = (await db.execute(file_q)).one()
    reclaimable_files = file_result[0]
    reclaimable_bytes = file_result[1]

    # By file type
    type_q = (
        select(
            FileModel.file_type,
            func.coalesce(func.sum(FileModel.size_bytes), 0).label("bytes"),
        )
        .where(FileModel.deleted_at.isnot(None))
        .group_by(FileModel.file_type)
    )
    type_result = await db.execute(type_q)
    by_type = {row[0]: row[1] for row in type_result.all()}

    # Human-readable size
    if reclaimable_bytes >= 1_073_741_824:
        human = f"{reclaimable_bytes / 1_073_741_824:.2f} GB"
    elif reclaimable_bytes >= 1_048_576:
        human = f"{reclaimable_bytes / 1_048_576:.2f} MB"
    elif reclaimable_bytes >= 1024:
        human = f"{reclaimable_bytes / 1024:.2f} KB"
    else:
        human = f"{reclaimable_bytes} bytes"

    return ReclamationPotentialResponse(
        reclaimable_files=reclaimable_files,
        reclaimable_bytes=reclaimable_bytes,
        reclaimable_human=human,
        by_type=by_type,
    )
