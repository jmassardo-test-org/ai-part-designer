"""
Design Annotation model for 3D annotations.

Stores annotations pinned to 3D coordinates on CAD models.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.design import Design
    from app.models.user import User


class AnnotationType(enum.StrEnum):
    """Types of annotations."""

    NOTE = "note"
    QUESTION = "question"
    ISSUE = "issue"
    APPROVAL = "approval"
    SUGGESTION = "suggestion"
    DIMENSION = "dimension"


class AnnotationStatus(enum.StrEnum):
    """Status of an annotation."""

    OPEN = "open"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"
    DEFERRED = "deferred"


class DesignAnnotation(Base):
    """
    Annotation pinned to a 3D position on a design.

    Annotations can be threaded (replies) and have different types
    for categorization and filtering.
    """

    __tablename__ = "design_annotations"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    design_id: Mapped[UUID] = mapped_column(
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("design_annotations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 3D position and orientation
    position: Mapped[dict[str, float]] = mapped_column(
        JSONB,
        nullable=False,
        comment="3D position {x, y, z}",
    )
    normal: Mapped[dict[str, float] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Surface normal for orientation {x, y, z}",
    )
    camera_position: Mapped[dict[str, float] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Camera position when annotation was created {x, y, z}",
    )
    camera_target: Mapped[dict[str, float] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Camera target when annotation was created {x, y, z}",
    )

    # Content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Type and status
    annotation_type: Mapped[AnnotationType] = mapped_column(
        Enum(AnnotationType),
        default=AnnotationType.NOTE,
        nullable=False,
        index=True,
    )
    status: Mapped[AnnotationStatus] = mapped_column(
        Enum(AnnotationStatus),
        default=AnnotationStatus.OPEN,
        nullable=False,
        index=True,
    )

    # Resolution
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Version tracking
    version_number: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Version of the design this annotation was created on",
    )

    # Reply tracking
    reply_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Number of replies to this annotation",
    )

    # Mentions
    mentioned_users: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="UUIDs of users mentioned in this annotation",
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
    design: Mapped[Design] = relationship(
        "Design",
        back_populates="annotations",
    )
    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="design_annotations",
    )
    resolved_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[resolved_by_id],
    )
    parent: Mapped[DesignAnnotation | None] = relationship(
        "DesignAnnotation",
        remote_side=[id],
        back_populates="replies",
    )
    replies: Mapped[list[DesignAnnotation]] = relationship(
        "DesignAnnotation",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DesignAnnotation {self.id} type={self.annotation_type.value}>"

    @property
    def is_resolved(self) -> bool:
        """Check if annotation is resolved."""
        return self.status == AnnotationStatus.RESOLVED

    @property
    def is_reply(self) -> bool:
        """Check if this is a reply to another annotation."""
        return self.parent_id is not None

    def get_reply_count(self) -> int:
        """Get the actual count of replies from the relationship.

        Note: Use reply_count column for cached count, this method
        for live count from loaded relationship.
        """
        return len(self.replies) if self.replies else 0

    @property
    def position_tuple(self) -> tuple[float, float, float]:
        """Get position as a tuple."""
        return (
            self.position.get("x", 0),
            self.position.get("y", 0),
            self.position.get("z", 0),
        )

    def resolve(
        self,
        user_id: UUID,
        note: str | None = None,
        status: AnnotationStatus = AnnotationStatus.RESOLVED,
    ) -> None:
        """Mark annotation as resolved."""
        self.status = status
        self.resolved_by_id = user_id
        self.resolved_at = datetime.now(tz=datetime.UTC)
        self.resolution_note = note

    def reopen(self) -> None:
        """Reopen a resolved annotation."""
        self.status = AnnotationStatus.OPEN
        self.resolved_by_id = None
        self.resolved_at = None
        self.resolution_note = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "design_id": str(self.design_id),
            "user_id": str(self.user_id),
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "position": self.position,
            "normal": self.normal,
            "camera_position": self.camera_position,
            "camera_target": self.camera_target,
            "content": self.content,
            "annotation_type": self.annotation_type.value,
            "status": self.status.value,
            "priority": self.priority,
            "tags": self.tags or [],
            "resolved_by_id": str(self.resolved_by_id) if self.resolved_by_id else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_note": self.resolution_note,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "reply_count": self.reply_count,
            "is_resolved": self.is_resolved,
        }
