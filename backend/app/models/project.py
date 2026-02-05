"""
Project model for organizing user designs.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.design import Design
    from app.models.organization import Organization
    from app.models.spatial_layout import SpatialLayout
    from app.models.team import ProjectTeam
    from app.models.user import User


class Project(Base, TimestampMixin, SoftDeleteMixin):
    """
    Project model for organizing designs.

    Projects are containers that group related designs together.
    Each user can have multiple projects. Projects can optionally
    be owned by an organization for team collaboration.
    """

    __tablename__ = "projects"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Project info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
        doc="Project status: active, suspended",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="projects",
    )
    organization: Mapped["Organization | None"] = relationship(
        "Organization",
        back_populates="projects",
    )
    designs: Mapped[list["Design"]] = relationship(
        "Design",
        back_populates="project",
        lazy="dynamic",
    )
    layouts: Mapped[list["SpatialLayout"]] = relationship(
        "SpatialLayout",
        back_populates="project",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    team_assignments: Mapped[list["ProjectTeam"]] = relationship(
        "ProjectTeam",
        back_populates="project",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"

    @property
    def design_count(self) -> int:
        """Get count of non-deleted designs in project."""
        # Note: In practice, use a query with filter for deleted_at IS NULL
        return len([d for d in self.designs if not d.is_deleted])

    @property
    def is_organization_owned(self) -> bool:
        """Check if project is owned by an organization."""
        return self.organization_id is not None
