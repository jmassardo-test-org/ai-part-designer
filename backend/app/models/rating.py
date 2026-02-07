"""
Rating and feedback models for community features.

Handles template ratings, thumbs up/down, and user feedback.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.template import Template
    from app.models.user import User


class FeedbackType(StrEnum):
    """Type of feedback."""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class TemplateRating(Base, TimestampMixin):
    """
    Template star rating (1-5).

    Users can rate templates to help others find quality content.
    Each user can only rate a template once (can update rating).
    """

    __tablename__ = "template_ratings"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    template_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rating (1-5 stars)
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Optional review text
    review: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    template: Mapped["Template"] = relationship(
        "Template",
        back_populates="ratings",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="template_ratings",
    )

    # Constraints
    __table_args__ = (
        # One rating per user per template
        UniqueConstraint("template_id", "user_id", name="uq_template_rating_user"),
        # Rating must be 1-5
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
        Index("idx_template_ratings_template", "template_id"),
        Index("idx_template_ratings_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<TemplateRating(template_id={self.template_id}, user_id={self.user_id}, rating={self.rating})>"


class TemplateFeedback(Base, TimestampMixin):
    """
    Template thumbs up/down feedback.

    Quick feedback mechanism for templates.
    Each user can only have one feedback per template.
    """

    __tablename__ = "template_feedback"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    template_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Feedback type
    feedback_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Relationships
    template: Mapped["Template"] = relationship(
        "Template",
        back_populates="feedback",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="template_feedback",
    )

    # Constraints
    __table_args__ = (
        # One feedback per user per template
        UniqueConstraint("template_id", "user_id", name="uq_template_feedback_user"),
        Index("idx_template_feedback_template", "template_id"),
        Index("idx_template_feedback_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<TemplateFeedback(template_id={self.template_id}, type={self.feedback_type})>"


class TemplateComment(Base, TimestampMixin):
    """
    Template comments with threading support.

    Users can leave comments and feedback on templates.
    Supports threaded replies via parent_id.
    """

    __tablename__ = "template_comments"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    template_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("template_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Comment content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Moderation status
    is_hidden: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    hidden_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    hidden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    hidden_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Edit tracking
    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    template: Mapped["Template"] = relationship(
        "Template",
        back_populates="comments",
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="template_comments",
    )
    parent: Mapped["TemplateComment | None"] = relationship(
        "TemplateComment",
        remote_side=[id],
        back_populates="replies",
    )
    replies: Mapped[list["TemplateComment"]] = relationship(
        "TemplateComment",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    hidden_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[hidden_by_id],
    )

    # Constraints
    __table_args__ = (
        Index("idx_template_comments_template", "template_id"),
        Index("idx_template_comments_user", "user_id"),
        Index("idx_template_comments_parent", "parent_id"),
    )

    def __repr__(self) -> str:
        return f"<TemplateComment(id={self.id}, template_id={self.template_id})>"


class ReportReason(StrEnum):
    """Reason categories for reports."""

    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    COPYRIGHT = "copyright"
    MISLEADING = "misleading"
    OFFENSIVE = "offensive"
    OTHER = "other"


class ReportStatus(StrEnum):
    """Status of a report."""

    PENDING = "pending"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ReportTargetType(StrEnum):
    """Type of content being reported."""

    TEMPLATE = "template"
    COMMENT = "comment"
    DESIGN = "design"
    USER = "user"


class ContentReport(Base, TimestampMixin):
    """
    Content report for moderation.

    Users can report inappropriate templates, comments, or designs.
    """

    __tablename__ = "content_reports"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Reporter
    reporter_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Target content
    target_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    target_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Report details
    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReportStatus.PENDING.value,
    )

    # Resolution
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    action_taken: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relationships
    reporter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[reporter_id],
        back_populates="reports_filed",
    )
    resolved_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[resolved_by_id],
    )

    # Constraints
    __table_args__ = (
        # Prevent duplicate reports from same user for same content
        UniqueConstraint("reporter_id", "target_type", "target_id", name="uq_report_user_target"),
        Index("idx_reports_reporter", "reporter_id"),
        Index("idx_reports_target", "target_type", "target_id"),
        Index("idx_reports_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ContentReport(id={self.id}, target={self.target_type}:{self.target_id}, status={self.status})>"


class UserBan(Base, TimestampMixin):
    """
    User ban for moderation.

    Tracks when and why users are banned from the platform.
    """

    __tablename__ = "user_bans"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Banned user
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Ban details
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    banned_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Duration
    is_permanent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Unban info
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    unbanned_by_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    unbanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    unban_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Related report
    related_report_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("content_reports.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="bans",
    )
    banned_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[banned_by_id],
    )
    unbanned_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[unbanned_by_id],
    )
    related_report: Mapped["ContentReport | None"] = relationship(
        "ContentReport",
    )

    # Constraints
    __table_args__ = (
        Index("idx_bans_user", "user_id"),
        Index("idx_bans_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<UserBan(user_id={self.user_id}, active={self.is_active})>"

    @property
    def is_expired(self) -> bool:
        """Check if ban has expired."""
        if self.is_permanent:
            return False
        if self.expires_at is None:
            return False
        return datetime.now(tz=UTC) > self.expires_at
