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
    from app.models.design import Design
    from app.models.job import Job
    from app.models.api_key import APIKey
    from app.models.conversation import Conversation
    from app.models.subscription import CreditBalance, UsageQuota
    from app.models.organization import OrganizationMember
    from app.models.team import TeamMember
    from app.models.annotation import DesignAnnotation
    from app.models.notification import Notification, NotificationPreference
    from app.models.payment import PaymentHistory
    from app.models.oauth import OAuthConnection
    from app.models.rating import (
        TemplateRating,
        TemplateFeedback,
        TemplateComment,
        ContentReport,
        UserBan,
    )
    from app.models.marketplace import DesignList


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

    # Onboarding tracking
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    onboarding_step: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )  # Track progress through onboarding steps

    # MFA (Multi-Factor Authentication)
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    mfa_secret: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )  # TOTP secret (encrypted)
    mfa_backup_codes: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # Hashed backup codes
    mfa_enabled_at: Mapped[datetime | None] = mapped_column(
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
    credit_balance: Mapped["CreditBalance"] = relationship(
        "CreditBalance",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    usage_quota: Mapped["UsageQuota"] = relationship(
        "UsageQuota",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="user",
        lazy="dynamic",
    )
    designs: Mapped[list["Design"]] = relationship(
        "Design",
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
    organization_memberships: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="user",
        lazy="dynamic",
        foreign_keys="OrganizationMember.user_id",
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="user",
        lazy="dynamic",
        foreign_keys="TeamMember.user_id",
    )
    design_annotations: Mapped[list["DesignAnnotation"]] = relationship(
        "DesignAnnotation",
        back_populates="user",
        lazy="dynamic",
        foreign_keys="DesignAnnotation.user_id",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        lazy="dynamic",
        foreign_keys="Notification.user_id",
    )
    notification_preferences: Mapped[list["NotificationPreference"]] = relationship(
        "NotificationPreference",
        back_populates="user",
        lazy="selectin",
    )
    payment_history: Mapped[list["PaymentHistory"]] = relationship(
        "PaymentHistory",
        back_populates="user",
        lazy="dynamic",
    )
    oauth_connections: Mapped[list["OAuthConnection"]] = relationship(
        "OAuthConnection",
        back_populates="user",
        lazy="selectin",
    )
    
    # Marketplace lists
    design_lists: Mapped[list["DesignList"]] = relationship(
        "DesignList",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    
    # Rating and feedback relationships
    template_ratings: Mapped[list["TemplateRating"]] = relationship(
        "TemplateRating",
        back_populates="user",
        lazy="dynamic",
    )
    template_feedback: Mapped[list["TemplateFeedback"]] = relationship(
        "TemplateFeedback",
        back_populates="user",
        lazy="dynamic",
    )
    template_comments: Mapped[list["TemplateComment"]] = relationship(
        "TemplateComment",
        back_populates="user",
        lazy="dynamic",
        foreign_keys="TemplateComment.user_id",
    )
    reports_filed: Mapped[list["ContentReport"]] = relationship(
        "ContentReport",
        back_populates="reporter",
        lazy="dynamic",
        foreign_keys="ContentReport.reporter_id",
    )
    bans: Mapped[list["UserBan"]] = relationship(
        "UserBan",
        back_populates="user",
        lazy="dynamic",
        foreign_keys="UserBan.user_id",
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

    @property
    def has_mfa(self) -> bool:
        """Check if MFA is enabled for this user."""
        return self.mfa_enabled and self.mfa_secret is not None

    @property
    def mfa_backup_codes_remaining(self) -> int:
        """Get count of remaining unused backup codes."""
        if not self.mfa_backup_codes:
            return 0
        return len([c for c in self.mfa_backup_codes if not c.get("used", False)])


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
