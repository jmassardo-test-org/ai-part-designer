"""
Design domain models: Design, DesignVersion, DesignShare
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.annotation import DesignAnnotation
    from app.models.design_context import DesignContext
    from app.models.job import Job
    from app.models.marketplace import DesignSave
    from app.models.project import Project
    from app.models.rating import DesignComment, DesignRating
    from app.models.template import Template
    from app.models.user import User


class Design(Base, TimestampMixin, SoftDeleteMixin):
    """
    Design model representing a user's CAD design.

    Designs can be created from templates, AI generation, or imports.
    Each design can have multiple versions tracking changes over time.

    Metadata schema example:
    {
        "parameters": {"length": 100, "width": 50},
        "aiPrompt": "Create a box with rounded corners",
        "dimensions": {"x": 100, "y": 50, "z": 30, "unit": "mm"},
        "volume": 150000,
        "surfaceArea": 23000,
        "isPrintable": true,
        "printEstimate": {"time": 3600, "material": 15.5}
    }
    """

    __tablename__ = "designs"

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
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    remixed_from_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Copy tracking (distinct from remix - for user's own copies)
    copied_from_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    current_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Design info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Source tracking
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # template, ai_generated, imported, modified

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        index=True,
    )  # draft, processing, ready, failed, archived

    # Flexible extra data (JSONB) - stores parameters, dimensions, etc.
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Tags for categorization
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    # Visibility
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Analytics
    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Marketplace stats
    save_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    remix_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Marketplace rating aggregates
    avg_rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )
    total_ratings: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Marketplace discoverability
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    featured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Starter design flag
    is_starter: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # Thumbnail for design preview
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Archival tracking
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="When the design was archived to cold storage",
    )
    archive_location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
        doc="Object storage key for the archived design data",
    )

    # Enclosure specification (CAD v2)
    enclosure_spec: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Full-text search vector
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    # License information (Epic 13)
    license_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
        doc="SPDX-like license identifier",
    )
    custom_license_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Custom license terms when license_type is CUSTOM. Max 5000 chars enforced at schema level.",
    )
    custom_allows_remix: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether custom-licensed designs allow remixing.",
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="designs",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="designs",
        lazy="joined",
    )
    template: Mapped["Template | None"] = relationship(
        "Template",
        lazy="joined",
    )
    # Self-referential relationships for copy/remix tracking
    copied_from: Mapped["Design | None"] = relationship(
        "Design",
        foreign_keys=[copied_from_id],
        remote_side="Design.id",
        lazy="joined",
    )
    remixed_from: Mapped["Design | None"] = relationship(
        "Design",
        foreign_keys=[remixed_from_id],
        remote_side="Design.id",
        lazy="joined",
    )
    versions: Mapped[list["DesignVersion"]] = relationship(
        "DesignVersion",
        back_populates="design",
        lazy="dynamic",
        order_by="DesignVersion.version_number.desc()",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="design",
        lazy="dynamic",
    )
    shares: Mapped[list["DesignShare"]] = relationship(
        "DesignShare",
        back_populates="design",
        lazy="dynamic",
    )
    saves: Mapped[list["DesignSave"]] = relationship(
        "DesignSave",
        back_populates="design",
        lazy="dynamic",
    )
    ratings: Mapped[list["DesignRating"]] = relationship(
        "DesignRating",
        back_populates="design",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["DesignComment"]] = relationship(
        "DesignComment",
        back_populates="design",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    annotations: Mapped[list["DesignAnnotation"]] = relationship(
        "DesignAnnotation",
        back_populates="design",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    context: Mapped[Optional["DesignContext"]] = relationship(
        "DesignContext",
        back_populates="design",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_designs_public",
            "is_public",
            "created_at",
            postgresql_where="deleted_at IS NULL AND is_public = TRUE",
        ),
        Index(
            "idx_designs_tags",
            "tags",
            postgresql_using="gin",
            postgresql_where="deleted_at IS NULL",
        ),
        Index("idx_designs_extra_data", "extra_data", postgresql_using="gin"),
        Index("idx_designs_search", "search_vector", postgresql_using="gin"),
        Index(
            "idx_designs_starter",
            "is_starter",
            postgresql_where="deleted_at IS NULL AND is_starter = TRUE",
        ),
        Index(
            "idx_designs_enclosure_spec",
            "enclosure_spec",
            postgresql_using="gin",
            postgresql_where="enclosure_spec IS NOT NULL",
        ),
        Index(
            "idx_designs_archived",
            "archived_at",
            postgresql_where="archived_at IS NOT NULL",
        ),
        Index(
            "idx_designs_marketplace_rating",
            "avg_rating",
            postgresql_where="deleted_at IS NULL AND is_public = TRUE AND published_at IS NOT NULL",
        ),
    )

    def __repr__(self) -> str:
        return f"<Design(id={self.id}, name={self.name})>"

    @property
    def current_version(self) -> "DesignVersion | None":
        """Get the current version of the design."""
        if self.current_version_id:
            for v in self.versions:
                if v.id == self.current_version_id:
                    return v
        return None

    @property
    def parameters(self) -> dict[str, Any]:
        """Get design parameters from extra_data."""
        result: dict[str, Any] = self.extra_data.get("parameters", {})
        return result

    @property
    def dimensions(self) -> dict[str, Any] | None:
        """Get design dimensions from extra_data."""
        result: dict[str, Any] | None = self.extra_data.get("dimensions")
        return result


class DesignVersion(Base):
    """
    Version history for a design.

    Each modification to a design creates a new version,
    preserving the complete history of changes.
    """

    __tablename__ = "design_versions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    design_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Version info
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # File storage
    file_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Available formats (JSONB)
    # Maps format names to S3 URLs (e.g., step, stl, 3mf)
    file_formats: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Parameters used for this version
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Geometry information
    # Contains bounding box dimensions, volume, surface area, triangle count, and manifold status
    geometry_info: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Change tracking
    change_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )

    # Relationships
    design: Mapped["Design"] = relationship(
        "Design",
        back_populates="versions",
    )
    creator: Mapped["User | None"] = relationship(
        "User",
        lazy="joined",
    )

    # Unique constraint
    __table_args__ = (
        Index(
            "idx_design_version_unique",
            "design_id",
            "version_number",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<DesignVersion(id={self.id}, v{self.version_number})>"

    @property
    def bounding_box(self) -> dict[str, Any] | None:
        """Get bounding box from geometry info."""
        result: dict[str, Any] | None = self.geometry_info.get("boundingBox")
        return result

    @property
    def is_manifold(self) -> bool:
        """Check if geometry is manifold (watertight)."""
        result: bool = self.geometry_info.get("isManifold", False)
        return result


class DesignShare(Base, TimestampMixin):
    """
    Design sharing configuration.

    Supports both user-to-user sharing and public link sharing.
    """

    __tablename__ = "design_shares"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    design_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shared_with_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    shared_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Permission level
    permission: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="view",
    )  # view, comment, edit, admin

    # Link sharing
    share_token: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
    )
    is_link_share: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Access tracking
    accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    design: Mapped["Design"] = relationship(
        "Design",
        back_populates="shares",
    )
    shared_with: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[shared_with_user_id],
    )
    shared_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[shared_by_user_id],
    )

    def __repr__(self) -> str:
        return f"<DesignShare(id={self.id}, permission={self.permission})>"

    @property
    def is_expired(self) -> bool:
        """Check if share has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(tz=UTC) > self.expires_at

    def record_access(self) -> None:
        """Record an access to this share."""
        self.accessed_at = datetime.now(tz=UTC)
        self.access_count += 1
