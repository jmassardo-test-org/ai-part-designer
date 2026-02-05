"""
Content moderation model.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.design import Design
    from app.models.user import User


class ModerationLog(Base):
    """
    Content moderation tracking for AI-generated designs.

    Records moderation decisions (automated and manual) for
    designs to ensure compliance with content policies.

    Details schema example:
    {
        "categories": {
            "violence": {"score": 0.02, "flagged": false},
            "adult": {"score": 0.01, "flagged": false},
            "weapons": {"score": 0.95, "flagged": true}
        },
        "originalPrompt": "Create a custom gun grip",
        "sanitizedPrompt": null,
        "moderationModel": "claude-content-moderation"
    }
    """

    __tablename__ = "moderation_logs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    design_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Content info
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # prompt, design, comment, profile

    content_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Moderation type
    moderation_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="automated",
    )  # automated, manual, appeal

    # Decision
    decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # approved, rejected, pending_review, escalated

    # Rejection reason
    reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # violence, weapons, adult, hate_speech, ip_violation, other

    # Confidence score (0-1) for automated moderation
    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Detailed moderation info (JSONB)
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Appeal handling
    is_appealed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    appeal_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    appeal_decision: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # upheld, overturned, null
    appealed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    design: Mapped["Design | None"] = relationship("Design")
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    reviewer: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[reviewer_id],
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_moderation_pending",
            "decision",
            "created_at",
            postgresql_where="decision = 'pending_review'",
        ),
        Index(
            "idx_moderation_rejected",
            "reason",
            "created_at",
            postgresql_where="decision = 'rejected'",
        ),
    )

    def __repr__(self) -> str:
        return f"<ModerationLog(id={self.id}, decision={self.decision})>"

    @property
    def is_flagged(self) -> bool:
        """Check if content was flagged (rejected or escalated)."""
        return self.decision in ("rejected", "escalated", "pending_review")

    @property
    def needs_review(self) -> bool:
        """Check if manual review is needed."""
        return self.decision in ("pending_review", "escalated")

    @property
    def category_scores(self) -> dict:
        """Get category scores from details."""
        return self.details.get("categories", {})

    def file_appeal(self, reason: str) -> None:
        """File an appeal for this moderation decision."""
        self.is_appealed = True
        self.appeal_reason = reason
        self.appealed_at = datetime.utcnow()

    def resolve_appeal(self, decision: str, reviewer_id: UUID) -> None:
        """Resolve the appeal with a decision."""
        self.appeal_decision = decision
        self.reviewer_id = reviewer_id
        self.reviewed_at = datetime.utcnow()

        if decision == "overturned":
            self.decision = "approved"
