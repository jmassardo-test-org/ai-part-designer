"""
Organization domain models.

Handles multi-user organizations, team membership,
roles, and invitations.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
import secrets

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project
    from app.models.team import Team


class OrganizationRole(str, Enum):
    """Organization member roles with increasing permissions."""
    
    VIEWER = "viewer"  # Read-only access
    MEMBER = "member"  # Create and edit own resources
    ADMIN = "admin"    # Manage members and settings
    OWNER = "owner"    # Full control, can delete org


class InviteStatus(str, Enum):
    """Invitation status."""
    
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    """
    Organization model.
    
    Represents a team or company that can have multiple members
    and own shared resources like projects and designs.
    """

    __tablename__ = "organizations"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Owner (creator) - nullable in DB
    owner_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Settings (JSONB for flexibility)
    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "allow_member_invites": False,
            "default_project_visibility": "private",
            "require_2fa": False,
            "allowed_domains": [],
        },
    )

    # Virtual properties from settings (not actual columns)
    @property
    def description(self) -> str | None:
        """Get description from settings."""
        return self.settings.get("description")
    
    @description.setter
    def description(self, value: str | None) -> None:
        """Set description in settings."""
        if self.settings is None:
            self.settings = {}
        self.settings = {**self.settings, "description": value}
    
    @property
    def logo_url(self) -> str | None:
        """Get logo URL from settings."""
        return self.settings.get("logo_url")
    
    @property
    def subscription_tier(self) -> str:
        """Get subscription tier from settings."""
        return self.settings.get("subscription_tier", "free")
    
    @property
    def max_members(self) -> int:
        """Get max members from settings."""
        return self.settings.get("max_members", 5)
    
    @property
    def max_projects(self) -> int:
        """Get max projects from settings."""
        return self.settings.get("max_projects", 10)

    # Stripe customer ID - stored in settings JSONB since column doesn't exist
    @property
    def stripe_customer_id(self) -> str | None:
        """Get Stripe customer ID from settings."""
        return self.settings.get("stripe_customer_id")

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
        lazy="joined",
    )
    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    invites: Mapped[list["OrganizationInvite"]] = relationship(
        "OrganizationInvite",
        back_populates="organization",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="organization",
        lazy="dynamic",
    )
    teams: Mapped[list["Team"]] = relationship(
        "Team",
        back_populates="organization",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    credit_balance: Mapped["OrganizationCreditBalance | None"] = relationship(
        "OrganizationCreditBalance",
        back_populates="organization",
        uselist=False,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, slug={self.slug})>"

    @property
    def member_count(self) -> int:
        """Count of active members."""
        return self.members.count()


class OrganizationMember(Base, TimestampMixin):
    """
    Organization membership.
    
    Links users to organizations with role-based access control.
    """

    __tablename__ = "organization_members"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=OrganizationRole.MEMBER.value,
    )

    # Invitation tracking
    invited_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    invited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="organization_memberships",
    )
    invited_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[invited_by_id],
    )

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        Index("idx_org_members_org", "organization_id"),
        Index("idx_org_members_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember(org_id={self.organization_id}, user_id={self.user_id}, role={self.role})>"

    def has_permission(self, required_role: OrganizationRole) -> bool:
        """Check if member has at least the required role."""
        role_hierarchy = {
            OrganizationRole.VIEWER: 0,
            OrganizationRole.MEMBER: 1,
            OrganizationRole.ADMIN: 2,
            OrganizationRole.OWNER: 3,
        }
        member_level = role_hierarchy.get(OrganizationRole(self.role), 0)
        required_level = role_hierarchy.get(required_role, 0)
        return member_level >= required_level


class OrganizationInvite(Base, TimestampMixin):
    """
    Organization invitation.
    
    Tracks pending invitations sent to email addresses.
    """

    __tablename__ = "organization_invites"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Invitation details
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=OrganizationRole.MEMBER.value,
    )

    # Token for accepting invite
    token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: secrets.token_urlsafe(32),
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InviteStatus.PENDING.value,
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(days=7),
    )

    # Response tracking
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    accepted_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="invites",
    )
    invited_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[invited_by_id],
    )
    accepted_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[accepted_by_id],
    )

    # Indexes
    __table_args__ = (
        Index("idx_org_invites_org", "organization_id"),
        Index("idx_org_invites_email", "email"),
        Index("idx_org_invites_token", "token"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationInvite(org_id={self.organization_id}, email={self.email}, status={self.status})>"

    @property
    def is_valid(self) -> bool:
        """Check if invite is still valid."""
        return (
            self.status == InviteStatus.PENDING.value
            and self.expires_at > datetime.utcnow()
        )

    def accept(self, user: "User") -> None:
        """Mark invite as accepted."""
        self.status = InviteStatus.ACCEPTED.value
        self.accepted_at = datetime.utcnow()
        self.accepted_by_id = user.id

    def decline(self) -> None:
        """Mark invite as declined."""
        self.status = InviteStatus.DECLINED.value

    def revoke(self) -> None:
        """Revoke the invitation."""
        self.status = InviteStatus.REVOKED.value


class OrganizationCreditBalance(Base, TimestampMixin):
    """
    Organization credit pool.
    
    Shared credits for all organization members.
    """

    __tablename__ = "organization_credit_balances"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Balance
    balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Lifetime tracking
    lifetime_earned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    lifetime_spent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Refill tracking
    last_refill_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_refill_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="credit_balance",
    )

    def __repr__(self) -> str:
        return f"<OrganizationCreditBalance(org_id={self.organization_id}, balance={self.balance})>"


class OrganizationAuditLog(Base, TimestampMixin):
    """
    Organization audit log.
    
    Tracks all organization actions for compliance.
    """

    __tablename__ = "organization_audit_logs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Action details
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # member_added, member_removed, role_changed, settings_updated, etc.
    
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # member, invite, project, settings
    
    resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Details
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # IP and user agent
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_org_audit_org_created", "organization_id", "created_at"),
        Index("idx_org_audit_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationAuditLog(org_id={self.organization_id}, action={self.action})>"
