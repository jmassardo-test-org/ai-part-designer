"""
Team models for organization sub-teams.

Teams allow organizations to group members for better resource
organization and access control within an organization.
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.project import Project
    from app.models.user import User


class TeamRole(StrEnum):
    """
    Role within a team.

    Defines permission levels for team members:
    - MEMBER: Can view team resources and participate
    - LEAD: Can manage team members and some settings
    - ADMIN: Full team administration rights
    """

    MEMBER = "member"
    LEAD = "lead"
    ADMIN = "admin"


class Team(Base, TimestampMixin, SoftDeleteMixin):
    """
    Team within an organization.

    Teams are sub-groups within organizations that allow for
    better resource organization and granular access control.
    """

    __tablename__ = "teams"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Organization reference
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Team details
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Team settings (JSONB for flexibility)
    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Creator tracking
    created_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Team status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="teams",
        lazy="joined",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="joined",
    )
    members: Mapped[list["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="team",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    project_assignments: Mapped[list["ProjectTeam"]] = relationship(
        "ProjectTeam",
        back_populates="team",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # Constraints
    __table_args__ = (
        # Slug must be unique within organization
        UniqueConstraint("organization_id", "slug", name="uq_team_org_slug"),
        Index("idx_teams_org", "organization_id"),
        Index("idx_teams_slug", "slug"),
        Index("idx_teams_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name}, org_id={self.organization_id})>"

    @property
    def member_count(self) -> int:
        """Count of active team members."""
        return self.members.filter(TeamMember.is_active).count()

    @property
    def color(self) -> str | None:
        """Get team color from settings."""
        return self.settings.get("color")

    @property
    def icon(self) -> str | None:
        """Get team icon from settings."""
        return self.settings.get("icon")


class TeamMember(Base, TimestampMixin):
    """
    Team membership.

    Links users to teams with role-based access control.
    """

    __tablename__ = "team_members"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
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
        default=TeamRole.MEMBER.value,
    )

    # Added by tracking
    added_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
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
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="team_memberships",
    )
    added_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[added_by_id],
    )

    # Constraints
    __table_args__ = (
        # User can only be in a team once
        UniqueConstraint("team_id", "user_id", name="uq_team_member"),
        Index("idx_team_members_team", "team_id"),
        Index("idx_team_members_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<TeamMember(team_id={self.team_id}, user_id={self.user_id}, role={self.role})>"

    def has_permission(self, required_role: TeamRole) -> bool:
        """Check if member has at least the required role."""
        role_hierarchy = {
            TeamRole.MEMBER: 0,
            TeamRole.LEAD: 1,
            TeamRole.ADMIN: 2,
        }
        member_level = role_hierarchy.get(TeamRole(self.role), 0)
        required_level = role_hierarchy.get(required_role, 0)
        return member_level >= required_level


class ProjectTeam(Base, TimestampMixin):
    """
    Project-Team assignment.

    Links projects to teams for access control.
    When a team is assigned to a project, all team members
    gain access based on the assigned permission level.
    """

    __tablename__ = "project_teams"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Permission level for the team on this project
    permission_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="viewer",  # viewer, editor, admin
    )

    # Assignment tracking
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="team_assignments",
    )
    team: Mapped["Team"] = relationship(
        "Team",
        back_populates="project_assignments",
    )
    assigned_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_by_id],
    )

    # Constraints
    __table_args__ = (
        # Team can only be assigned to a project once
        UniqueConstraint("project_id", "team_id", name="uq_project_team"),
        Index("idx_project_teams_project", "project_id"),
        Index("idx_project_teams_team", "team_id"),
    )

    def __repr__(self) -> str:
        return f"<ProjectTeam(project_id={self.project_id}, team_id={self.team_id}, permission={self.permission_level})>"
