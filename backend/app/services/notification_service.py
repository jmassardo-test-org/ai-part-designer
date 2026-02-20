"""
Notification service for managing user notifications.

Provides functions to create, send, and manage notifications
across different channels (in-app, email, push).
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DEFAULT_PREFERENCES,
    Notification,
    NotificationPreference,
    NotificationPriority,
    NotificationType,
)


class NotificationService:
    """Service for managing notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        action_url: str | None = None,
        action_label: str | None = None,
        actor_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        data: dict[str, Any] | None = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        expires_in_days: int | None = None,
    ) -> Notification | None:
        """
        Create a notification for a user.

        Checks user preferences before creating. Returns None if
        the user has disabled this notification type.

        Extended fields (action_url, action_label, actor_id, entity_type, entity_id,
        priority, expires_in_days) are stored in the data JSONB field.
        """
        # Check user preferences
        if not await self.should_send_in_app(user_id, notification_type):
            return None

        # Build data dict including any extended fields
        notification_data = data.copy() if data else {}
        if action_url:
            notification_data["action_url"] = action_url
        if action_label:
            notification_data["action_label"] = action_label
        if actor_id:
            notification_data["actor_id"] = str(actor_id)
        if entity_type:
            notification_data["entity_type"] = entity_type
        if entity_id:
            notification_data["entity_id"] = str(entity_id)
        if priority != NotificationPriority.NORMAL:
            notification_data["priority"] = priority.value
        if expires_in_days:
            expires_at = datetime.now(tz=UTC) + timedelta(days=expires_in_days)
            notification_data["expires_at"] = expires_at.isoformat()

        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=notification_data if notification_data else None,
        )

        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        # Check if email should be sent
        if await self.should_send_email(user_id, notification_type):
            await self.queue_email_notification(notification)

        return notification

    async def should_send_in_app(
        self,
        user_id: UUID,
        notification_type: NotificationType,
    ) -> bool:
        """Check if in-app notification is enabled for user."""
        pref = await self.get_preference(user_id, notification_type)
        if pref:
            return pref.in_app_enabled
        # Use defaults
        defaults = DEFAULT_PREFERENCES.get(notification_type, {})
        return defaults.get("in_app", True)

    async def should_send_email(
        self,
        user_id: UUID,
        notification_type: NotificationType,
    ) -> bool:
        """Check if email notification is enabled for user."""
        pref = await self.get_preference(user_id, notification_type)
        if pref:
            return pref.email_enabled
        # Use defaults
        defaults = DEFAULT_PREFERENCES.get(notification_type, {})
        return defaults.get("email", False)

    async def get_preference(
        self,
        user_id: UUID,
        notification_type: NotificationType,
    ) -> NotificationPreference | None:
        """Get user preference for a notification type."""
        result = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.notification_type == notification_type,
                )
            )
        )
        return result.scalar_one_or_none()

    async def queue_email_notification(self, notification: Notification) -> None:
        """Queue email notification for sending."""
        # In a real implementation, this would add to a task queue
        # For now, mark as sent immediately (stub)
        notification.email_sent_at = datetime.now(tz=UTC)
        await self.db.commit()

    async def get_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        """Get paginated notifications for a user."""
        conditions = [
            Notification.user_id == user_id,
            Notification.dismissed_at.is_(None),
        ]

        if unread_only:
            conditions.append(Notification.read_at.is_(None))

        # Filter out expired
        conditions.append(
            (Notification.expires_at.is_(None)) | (Notification.expires_at > datetime.now(tz=UTC))
        )

        # Count total
        count_result = await self.db.execute(
            select(func.count(Notification.id)).where(and_(*conditions))
        )
        total = count_result.scalar() or 0

        # Get page
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Notification)
            .where(and_(*conditions))
            .order_by(
                Notification.read_at.is_(None).desc(),  # Unread first
                Notification.created_at.desc(),
            )
            .offset(offset)
            .limit(page_size)
        )
        notifications = list(result.scalars().all())

        return notifications, total

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications."""
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                    Notification.dismissed_at.is_(None),
                    (Notification.expires_at.is_(None))
                    | (Notification.expires_at > datetime.now(tz=UTC)),
                )
            )
        )
        return result.scalar() or 0

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Mark a notification as read."""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
            )
            .values(read_at=datetime.now(tz=UTC))
        )
        await self.db.commit()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
            .values(read_at=datetime.now(tz=UTC))
        )
        await self.db.commit()
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def dismiss(self, notification_id: UUID, user_id: UUID) -> bool:
        """Dismiss a notification."""
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
            )
            .values(dismissed_at=datetime.now(tz=UTC))
        )
        await self.db.commit()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

    async def get_preferences(self, user_id: UUID) -> list[NotificationPreference]:
        """Get all notification preferences for a user."""
        result = await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return list(result.scalars().all())

    async def update_preference(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        in_app_enabled: bool | None = None,
        email_enabled: bool | None = None,
        push_enabled: bool | None = None,
        email_digest: str | None = None,
    ) -> NotificationPreference:
        """Update or create a notification preference."""
        pref = await self.get_preference(user_id, notification_type)

        if not pref:
            # Create with defaults
            defaults = DEFAULT_PREFERENCES.get(notification_type, {})
            pref = NotificationPreference(
                user_id=user_id,
                notification_type=notification_type,
                in_app_enabled=defaults.get("in_app", True),
                email_enabled=defaults.get("email", False),
            )
            self.db.add(pref)

        # Update fields
        if in_app_enabled is not None:
            pref.in_app_enabled = in_app_enabled
        if email_enabled is not None:
            pref.email_enabled = email_enabled
        if push_enabled is not None:
            pref.push_enabled = push_enabled
        if email_digest is not None:
            pref.email_digest = email_digest

        await self.db.commit()
        await self.db.refresh(pref)

        return pref


# --- Notification Helpers ---


async def notify_share_permission_changed(
    db: AsyncSession,
    recipient_id: UUID,
    actor_id: UUID,
    actor_name: str,
    design_id: UUID,
    design_name: str,
    new_permission: str,
) -> Notification | None:
    """Send notification when share permission is updated."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=recipient_id,
        notification_type=NotificationType.SHARE_PERMISSION_CHANGED,
        title="Share permission updated",
        message=f"{actor_name} changed your access to '{design_name}' to {new_permission}",
        action_url=f"/designs/{design_id}",
        action_label="View Design",
        actor_id=actor_id,
        entity_type="design",
        entity_id=design_id,
        data={"permission": new_permission},
    )


async def notify_design_shared(
    db: AsyncSession,
    recipient_id: UUID,
    actor_id: UUID,
    actor_name: str,
    design_id: UUID,
    design_name: str,
    permission: str,
) -> Notification | None:
    """Send notification when a design is shared with a user."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=recipient_id,
        notification_type=NotificationType.DESIGN_SHARED,
        title="Design shared with you",
        message=f"{actor_name} shared '{design_name}' with you ({permission} access)",
        action_url=f"/designs/{design_id}",
        action_label="View Design",
        actor_id=actor_id,
        entity_type="design",
        entity_id=design_id,
        data={"permission": permission},
    )


async def notify_comment_added(
    db: AsyncSession,
    recipient_id: UUID,
    actor_id: UUID,
    actor_name: str,
    design_id: UUID,
    design_name: str,
    comment_preview: str,
) -> Notification | None:
    """Send notification when a comment is added to a design (to design owner)."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=recipient_id,
        notification_type=NotificationType.COMMENT_ADDED,
        title="New comment on your design",
        message=f"{actor_name} commented on '{design_name}': {comment_preview[:100]}{'...' if len(comment_preview) > 100 else ''}",
        action_url=f"/designs/{design_id}",
        action_label="View Comment",
        actor_id=actor_id,
        entity_type="design",
        entity_id=design_id,
    )


async def notify_comment_reply(
    db: AsyncSession,
    recipient_id: UUID,
    actor_id: UUID,
    actor_name: str,
    design_id: UUID,
    design_name: str,
    comment_preview: str,
) -> Notification | None:
    """Send notification when someone replies to a comment thread."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=recipient_id,
        notification_type=NotificationType.COMMENT_REPLY,
        title="New reply to comment",
        message=f"{actor_name} replied to a comment on '{design_name}': {comment_preview[:100]}{'...' if len(comment_preview) > 100 else ''}",
        action_url=f"/designs/{design_id}",
        action_label="View Reply",
        actor_id=actor_id,
        entity_type="design",
        entity_id=design_id,
    )


async def notify_comment_mention(
    db: AsyncSession,
    recipient_id: UUID,
    actor_id: UUID,
    actor_name: str,
    design_id: UUID,
    design_name: str,
    comment_preview: str,
) -> Notification | None:
    """Send notification when a user is mentioned in a comment."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=recipient_id,
        notification_type=NotificationType.COMMENT_MENTION,
        title="You were mentioned",
        message=f"{actor_name} mentioned you in '{design_name}': {comment_preview[:100]}...",
        action_url=f"/designs/{design_id}",
        action_label="View Comment",
        actor_id=actor_id,
        entity_type="design",
        entity_id=design_id,
        priority=NotificationPriority.HIGH,
    )


async def notify_job_completed(
    db: AsyncSession,
    user_id: UUID,
    job_id: UUID,
    job_type: str,
    design_name: str,
) -> Notification | None:
    """Send notification when a job completes."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=user_id,
        notification_type=NotificationType.JOB_COMPLETED,
        title="Job completed",
        message=f"Your {job_type} job for '{design_name}' has completed successfully",
        action_url=f"/jobs/{job_id}",
        action_label="View Result",
        entity_type="job",
        entity_id=job_id,
    )


async def notify_job_failed(
    db: AsyncSession,
    user_id: UUID,
    job_id: UUID,
    job_type: str,
    design_name: str,
    error_message: str,
) -> Notification | None:
    """Send notification when a job fails."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=user_id,
        notification_type=NotificationType.JOB_FAILED,
        title="Job failed",
        message=f"Your {job_type} job for '{design_name}' failed: {error_message}",
        action_url=f"/jobs/{job_id}",
        action_label="View Details",
        entity_type="job",
        entity_id=job_id,
        priority=NotificationPriority.HIGH,
    )


async def notify_subscription_expiring(
    db: AsyncSession,
    user_id: UUID,
    days_remaining: int,
    tier_name: str,
) -> Notification | None:
    """Send notification when subscription is about to expire."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=user_id,
        notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
        title="Subscription expiring soon",
        message=f"Your {tier_name} subscription expires in {days_remaining} days. Renew to keep your benefits.",
        action_url="/settings/billing",
        action_label="Manage Subscription",
        data={"kind": "subscription_expiring", "days_remaining": days_remaining},
    )


async def notify_storage_warning(
    db: AsyncSession,
    user_id: UUID,
    usage_percent: float,
) -> Notification | None:
    """Send notification when storage is near capacity."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=user_id,
        notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
        title="Storage almost full",
        message=f"Your storage is {usage_percent:.0f}% full. Consider freeing up space or upgrading your plan.",
        action_url="/settings",
        action_label="Manage Storage",
        data={"kind": "storage_warning", "usage_percent": usage_percent},
    )


async def notify_design_remixed(
    db: AsyncSession,
    recipient_id: UUID,
    actor_id: UUID,
    actor_name: str,
    design_id: UUID,
    design_name: str,
    remix_name: str,
) -> Notification | None:
    """Send notification when someone remixes your design."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=recipient_id,
        notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
        title="Your design was remixed",
        message=f"{actor_name} created a remix of '{design_name}' called '{remix_name}'",
        action_url=f"/designs/{design_id}",
        action_label="View Design",
        actor_id=actor_id,
        entity_type="design",
        entity_id=design_id,
        data={"kind": "design_remixed", "remix_name": remix_name},
    )


async def notify_org_invite(
    db: AsyncSession,
    recipient_id: UUID,
    actor_id: UUID,
    actor_name: str,
    org_id: UUID,
    org_name: str,
    role: str,
) -> Notification | None:
    """Send notification for organization invite."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=recipient_id,
        notification_type=NotificationType.ORG_INVITE,
        title="Organization invitation",
        message=f"{actor_name} invited you to join '{org_name}' as {role}",
        action_url=f"/organizations/{org_id}/invites",
        action_label="View Invite",
        actor_id=actor_id,
        entity_type="organization",
        entity_id=org_id,
        priority=NotificationPriority.HIGH,
        data={"role": role},
    )
