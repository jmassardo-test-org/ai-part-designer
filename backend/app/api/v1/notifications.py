"""
Notifications API endpoints.

Handles notification listing, status updates, and preferences.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import (
    DEFAULT_PREFERENCES,
    Notification,
    NotificationType,
    User,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


# --- Schemas ---


class NotificationActorResponse(BaseModel):
    """Actor info for notification."""

    id: UUID
    display_name: str


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: UUID
    type: str
    title: str
    message: str
    data: dict | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated notification list."""

    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
    has_more: bool


class NotificationPreferenceResponse(BaseModel):
    """Notification preference response."""

    notification_type: str
    in_app_enabled: bool
    email_enabled: bool
    push_enabled: bool
    email_digest: str | None


class NotificationPreferencesResponse(BaseModel):
    """All notification preferences."""

    preferences: list[NotificationPreferenceResponse]


class UpdatePreferenceRequest(BaseModel):
    """Update notification preference."""

    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    push_enabled: bool | None = None
    email_digest: str | None = Field(
        None,
        pattern="^(instant|hourly|daily|weekly)$",
    )


class MarkReadRequest(BaseModel):
    """Mark notifications as read."""

    notification_ids: list[UUID] | None = None  # If None, mark all


class UnreadCountResponse(BaseModel):
    """Unread notification count."""

    count: int


# --- Helper Functions ---


def notification_to_response(notification: Notification) -> NotificationResponse:
    """Convert notification to response schema."""
    return NotificationResponse(
        id=notification.id,
        type=notification.type.value if hasattr(notification.type, "value") else notification.type,
        title=notification.title,
        message=notification.message,
        data=notification.data,
        is_read=notification.is_read,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


# --- Endpoints ---


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated notifications for the current user."""
    service = NotificationService(db)

    notifications, total = await service.get_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )

    unread_count = await service.get_unread_count(current_user.id)

    return NotificationListResponse(
        items=[notification_to_response(n) for n in notifications],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get count of unread notifications."""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return UnreadCountResponse(count=count)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific notification."""
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return notification_to_response(notification)


@router.post("/mark-read")
async def mark_notifications_read(
    request: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark notifications as read."""
    service = NotificationService(db)

    if request.notification_ids is None:
        # Mark all as read
        count = await service.mark_all_as_read(current_user.id)
        return {"marked_read": count}
    # Mark specific notifications
    marked = 0
    for notification_id in request.notification_ids:
        if await service.mark_as_read(notification_id, current_user.id):
            marked += 1
    return {"marked_read": marked}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a single notification as read."""
    service = NotificationService(db)

    if not await service.mark_as_read(notification_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return {"success": True}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss a notification."""
    service = NotificationService(db)

    if not await service.dismiss(notification_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


# --- Preferences ---


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all notification preferences for current user."""
    service = NotificationService(db)
    prefs = await service.get_preferences(current_user.id)

    # Build complete list with defaults for missing types
    pref_map = {p.notification_type: p for p in prefs}
    all_prefs = []

    for notification_type in NotificationType:
        if notification_type in pref_map:
            p = pref_map[notification_type]
            all_prefs.append(
                NotificationPreferenceResponse(
                    notification_type=notification_type.value,
                    in_app_enabled=p.in_app_enabled,
                    email_enabled=p.email_enabled,
                    push_enabled=p.push_enabled,
                    email_digest=p.email_digest,
                )
            )
        else:
            # Use defaults
            defaults = DEFAULT_PREFERENCES.get(notification_type, {})
            all_prefs.append(
                NotificationPreferenceResponse(
                    notification_type=notification_type.value,
                    in_app_enabled=defaults.get("in_app", True),
                    email_enabled=defaults.get("email", False),
                    push_enabled=False,
                    email_digest=None,
                )
            )

    return NotificationPreferencesResponse(preferences=all_prefs)


@router.patch("/preferences/{notification_type}", response_model=NotificationPreferenceResponse)
async def update_notification_preference(
    notification_type: str,
    request: UpdatePreferenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update notification preference for a specific type."""
    # Validate notification type
    try:
        ntype = NotificationType(notification_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification type: {notification_type}",
        )

    service = NotificationService(db)
    pref = await service.update_preference(
        user_id=current_user.id,
        notification_type=ntype,
        in_app_enabled=request.in_app_enabled,
        email_enabled=request.email_enabled,
        push_enabled=request.push_enabled,
        email_digest=request.email_digest,
    )

    return NotificationPreferenceResponse(
        notification_type=pref.notification_type.value,
        in_app_enabled=pref.in_app_enabled,
        email_enabled=pref.email_enabled,
        push_enabled=pref.push_enabled,
        email_digest=pref.email_digest,
    )
