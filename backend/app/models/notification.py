"""
Notification models for in-app and email notifications.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class NotificationType(enum.StrEnum):
    """Types of notifications."""

    # Sharing
    DESIGN_SHARED = "design_shared"
    SHARE_PERMISSION_CHANGED = "share_permission_changed"
    SHARE_REVOKED = "share_revoked"

    # Comments
    COMMENT_ADDED = "comment_added"
    COMMENT_REPLY = "comment_reply"
    COMMENT_MENTION = "comment_mention"

    # Annotations
    ANNOTATION_ADDED = "annotation_added"
    ANNOTATION_RESOLVED = "annotation_resolved"

    # Jobs
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"

    # Organization
    ORG_INVITE = "org_invite"
    ORG_ROLE_CHANGED = "org_role_changed"
    ORG_MEMBER_JOINED = "org_member_joined"

    # System
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class NotificationPriority(enum.StrEnum):
    """Priority levels for notifications."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """
    User notification model.

    Stores in-app notifications for users with support for
    various types.
    """

    __tablename__ = "notifications"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # Recipient
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification content - use native PostgreSQL enum that already exists
    type: Mapped[NotificationType] = mapped_column(
        "notification_type",
        Enum(
            NotificationType,
            name="notificationtype",
            create_type=False,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Extra data
    data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional notification data",
    )

    # Status - database has both is_read boolean AND read_at timestamp
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Auto-dismiss after this time",
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="notifications",
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_notifications_user_unread",
            "user_id",
            "is_read",
            postgresql_where="is_read = false",
        ),
        Index("idx_notifications_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification {self.id} type={self.type.value}>"

    @property
    def is_dismissed(self) -> bool:
        """Check if notification has been dismissed."""
        return self.dismissed_at is not None

    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if not self.expires_at:
            return False
        return datetime.now(tz=datetime.UTC) > self.expires_at

    def mark_read(self) -> None:
        """Mark notification as read."""
        self.is_read = True
        self.read_at = datetime.now(tz=datetime.UTC)

    def dismiss(self) -> None:
        """Dismiss the notification."""
        self.dismissed_at = datetime.now(tz=datetime.UTC)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class NotificationPreference(Base):
    """
    User notification preferences.

    Controls which notifications are enabled for each channel.
    """

    __tablename__ = "notification_preferences"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # User
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification type
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType),
        nullable=False,
    )

    # Channel preferences
    in_app_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    push_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Digest settings
    email_digest: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="instant, hourly, daily, weekly",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        back_populates="notification_preferences",
    )

    # Unique constraint
    __table_args__ = (
        Index("idx_notification_prefs_user_type", "user_id", "notification_type", unique=True),
    )

    def __repr__(self) -> str:
        return f"<NotificationPreference {self.user_id} {self.notification_type.value}>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "notification_type": self.notification_type.value,
            "in_app_enabled": self.in_app_enabled,
            "email_enabled": self.email_enabled,
            "push_enabled": self.push_enabled,
            "email_digest": self.email_digest,
        }


# Default preferences for each notification type
DEFAULT_PREFERENCES = {
    # High priority - all enabled
    NotificationType.DESIGN_SHARED: {"in_app": True, "email": True},
    NotificationType.COMMENT_MENTION: {"in_app": True, "email": True},
    NotificationType.ORG_INVITE: {"in_app": True, "email": True},
    NotificationType.JOB_COMPLETED: {"in_app": True, "email": False},
    NotificationType.JOB_FAILED: {"in_app": True, "email": True},
    # Medium priority
    NotificationType.COMMENT_REPLY: {"in_app": True, "email": False},
    NotificationType.ANNOTATION_ADDED: {"in_app": True, "email": False},
    NotificationType.ANNOTATION_RESOLVED: {"in_app": True, "email": False},
    NotificationType.SHARE_PERMISSION_CHANGED: {"in_app": True, "email": False},
    # Low priority
    NotificationType.COMMENT_ADDED: {"in_app": True, "email": False},
    NotificationType.ORG_MEMBER_JOINED: {"in_app": True, "email": False},
    # System
    NotificationType.SYSTEM_ANNOUNCEMENT: {"in_app": True, "email": True},
}
