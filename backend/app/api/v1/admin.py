"""
Admin Moderation API.

Provides endpoints for:
- Viewing moderation queue
- Approving/rejecting flagged content
- Managing user warnings and bans
- Moderation statistics
"""

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user, require_admin
from app.core.database import get_db
from app.models.moderation import ModerationLog
from app.models.user import User
from app.services.moderation import (
    ContentModerator,
    ModerationResult,
    ModerationStatus,
    FlagSeverity,
)

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
    details: dict = Field(default_factory=dict)
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
    dependencies=[Depends(require_admin)],
)
async def get_moderation_queue(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query()] = None,
    severity_filter: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModerationQueueResponse:
    """Get paginated moderation queue."""
    
    # Base query
    base_query = select(ModerationLog).options(
        selectinload(ModerationLog.user)
    )
    
    # Apply filters
    filters = []
    if status_filter:
        filters.append(ModerationLog.decision == status_filter)
    else:
        # Default: show pending and escalated
        filters.append(
            ModerationLog.decision.in_(["pending_review", "escalated"])
        )
    
    if filters:
        base_query = base_query.where(and_(*filters))
    
    # Count total
    count_query = select(func.count()).select_from(
        base_query.subquery()
    )
    total = (await db.execute(count_query)).scalar_one()
    
    # Count pending and escalated
    pending_count = (await db.execute(
        select(func.count())
        .where(ModerationLog.decision == "pending_review")
    )).scalar_one()
    
    escalated_count = (await db.execute(
        select(func.count())
        .where(ModerationLog.decision == "escalated")
    )).scalar_one()
    
    # Fetch page
    offset = (page - 1) * page_size
    query = (
        base_query
        .order_by(ModerationLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
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
    "/moderation/{item_id}",
    response_model=ModerationItemResponse,
    summary="Get moderation item",
    description="Get details of a specific moderation item.",
    dependencies=[Depends(require_admin)],
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
    dependencies=[Depends(require_admin)],
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
    item.reviewed_at = datetime.utcnow()
    
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
    dependencies=[Depends(require_admin)],
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
    item.reviewed_at = datetime.utcnow()
    
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
    dependencies=[Depends(require_admin)],
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
    item.details["escalated_at"] = datetime.utcnow().isoformat()
    
    if request.notes:
        item.details["escalation_notes"] = request.notes
    
    await db.commit()
    
    return ModerationDecisionResponse(
        id=item.id,
        decision="escalated",
        reviewed_by=current_user.id,
        reviewed_at=datetime.utcnow(),
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
    dependencies=[Depends(require_admin)],
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
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    # Store warning in user's extra_data (simplified)
    # In production, use dedicated UserWarning model
    warnings = user.extra_data.get("warnings", [])
    warning_id = str(uuid4())
    warnings.append({
        "id": warning_id,
        "category": request.category,
        "severity": request.severity,
        "message": request.message,
        "issued_by": str(current_user.id),
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "acknowledged": False,
    })
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
        created_at=datetime.utcnow(),
        expires_at=expires_at,
    )


@router.post(
    "/users/{user_id}/ban",
    response_model=UserBanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ban user",
    description="Ban a user from the platform.",
    dependencies=[Depends(require_admin)],
)
async def ban_user(
    user_id: UUID,
    request: UserBanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        expires_at = datetime.utcnow() + timedelta(days=request.duration_days)
    
    # Ban user
    user.is_banned = True
    user.banned_at = datetime.utcnow()
    user.ban_reason = request.reason
    user.ban_expires_at = expires_at
    
    await db.commit()
    
    return UserBanResponse(
        id=user.id,  # Using user ID as ban ID (simplified)
        user_id=user_id,
        reason=request.reason,
        is_permanent=request.is_permanent,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
    )


@router.delete(
    "/users/{user_id}/ban",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unban user",
    description="Remove ban from a user.",
    dependencies=[Depends(require_admin)],
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


# =============================================================================
# Statistics Endpoints
# =============================================================================


@router.get(
    "/moderation/stats",
    response_model=ModerationStatsResponse,
    summary="Get moderation stats",
    description="Get moderation statistics.",
    dependencies=[Depends(require_admin)],
)
async def get_moderation_stats(
    db: AsyncSession = Depends(get_db),
) -> ModerationStatsResponse:
    """Get moderation statistics."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Count pending
    pending_count = (await db.execute(
        select(func.count())
        .where(ModerationLog.decision == "pending_review")
    )).scalar_one()
    
    # Count escalated
    escalated_count = (await db.execute(
        select(func.count())
        .where(ModerationLog.decision == "escalated")
    )).scalar_one()
    
    # Count approved today
    approved_today = (await db.execute(
        select(func.count())
        .where(
            ModerationLog.decision == "approved",
            ModerationLog.reviewed_at >= today_start,
        )
    )).scalar_one()
    
    # Count rejected today
    rejected_today = (await db.execute(
        select(func.count())
        .where(
            ModerationLog.decision == "rejected",
            ModerationLog.reviewed_at >= today_start,
        )
    )).scalar_one()
    
    # Count pending appeals
    appeals_pending = (await db.execute(
        select(func.count())
        .where(
            ModerationLog.is_appealed == True,
            ModerationLog.appeal_decision.is_(None),
        )
    )).scalar_one()
    
    return ModerationStatsResponse(
        pending_count=pending_count,
        escalated_count=escalated_count,
        approved_today=approved_today,
        rejected_today=rejected_today,
        appeals_pending=appeals_pending,
        avg_review_time_hours=None,  # Would calculate from reviewed_at - created_at
    )


# Need uuid4 import
from uuid import uuid4
