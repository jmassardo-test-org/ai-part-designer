"""
User domain models: User, UserSettings, Subscription
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.job import Job
    from app.models.api_key import APIKey
    from app.models.conversation import Conversation


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    User account model.
    
    Represents registered users of the platform with authentication
    credentials and account status.
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Profile
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Authorization
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
    )  # user, admin, moderator

    # Account status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending_verification",
    )  # pending_verification, active, suspended, deleted

    # Verification
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Activity tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Extra data for flexible storage (JSONB)
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    subscription: Mapped["Subscription"] = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        lazy="joined",
    )
    settings: Mapped["UserSettings"] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="user",
        lazy="dynamic",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="user",
        lazy="dynamic",
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        lazy="dynamic",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"

    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == "active" and not self.is_deleted

    @property
    def is_verified(self) -> bool:
        """Check if email is verified."""
        return self.email_verified_at is not None

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"

    @property
    def tier(self) -> str:
        """Get user's subscription tier."""
        if self.subscription:
            return self.subscription.tier
        return "free"


class Subscription(Base, TimestampMixin):
    """
    User subscription model.
    
    Tracks the subscription tier and billing status for a user.
    One-to-one relationship with User.
    """

    __tablename__ = "subscriptions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Subscription details
    tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="free",
    )  # free, pro, enterprise

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )  # active, past_due, canceled, expired

    # Stripe integration
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Billing period
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="subscription",
    )

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, tier={self.tier})>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status == "active"

    @property
    def is_premium(self) -> bool:
        """Check if subscription is a paid tier."""
        return self.tier in ("pro", "enterprise")


class UserSettings(Base, TimestampMixin):
    """
    User preferences and notification settings.
    
    Stores user-configurable settings as JSONB for flexibility.
    One-to-one relationship with User.
    """

    __tablename__ = "user_settings"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Settings as JSONB
    preferences: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "defaultUnits": "mm",
            "defaultExportFormat": "stl",
            "theme": "system",
            "language": "en",
        },
    )

    notifications: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "email": {
                "jobComplete": True,
                "weeklyDigest": True,
                "marketing": False,
            },
            "push": {
                "jobComplete": True,
            },
        },
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="settings",
    )

    def __repr__(self) -> str:
        return f"<UserSettings(id={self.id}, user_id={self.user_id})>"
