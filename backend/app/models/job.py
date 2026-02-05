"""
Job model for async task tracking.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
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


class Job(Base):
    """
    Async job tracking for CAD operations.

    Tracks status, progress, and results of long-running operations like:
    - AI generation
    - CAD model processing
    - Format conversion/export
    - Batch operations

    Result schema example:
    {
        "fileUrl": "s3://bucket/path/to/file.step",
        "thumbnailUrl": "s3://bucket/path/to/thumb.png",
        "formats": ["step", "stl", "3mf"],
        "geometryInfo": {...}
    }

    Error schema example:
    {
        "code": "GENERATION_FAILED",
        "message": "AI generation failed due to invalid prompt",
        "details": {"step": "validation", "reason": "..."}
    }
    """

    __tablename__ = "jobs"

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
    design_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Job type
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    # Types: ai_generation, cad_modification, format_conversion,
    #        export, batch_export, validation, repair

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )  # pending, queued, running, completed, failed, cancelled

    # Priority (lower = higher priority)
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )

    # Progress tracking (0-100)
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    progress_message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Input parameters (JSONB)
    input_params: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Result (JSONB) - populated on completion
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Error info (JSONB) - populated on failure
    error: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    # Celery task tracking
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Execution stats
    execution_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Resource usage tracking
    cpu_time_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    memory_mb: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        lazy="joined",
    )
    design: Mapped["Design | None"] = relationship(
        "Design",
        back_populates="jobs",
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_jobs_pending",
            "status",
            "priority",
            "created_at",
            postgresql_where="status IN ('pending', 'queued')",
        ),
        Index(
            "idx_jobs_user_recent",
            "user_id",
            "created_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, type={self.job_type}, status={self.status})>"

    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in ("completed", "failed", "cancelled")

    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == "running"

    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.status == "failed" and self.retry_count < self.max_retries

    @property
    def duration_ms(self) -> int | None:
        """Calculate job duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None

    def start(self) -> None:
        """Mark job as started."""
        self.status = "running"
        self.started_at = datetime.now(tz=datetime.UTC)
        self.progress = 0

    def complete(self, result: dict[str, Any]) -> None:
        """Mark job as completed with result."""
        self.status = "completed"
        self.completed_at = datetime.now(tz=datetime.UTC)
        self.result = result
        self.progress = 100

        if self.started_at:
            delta = self.completed_at - self.started_at
            self.execution_time_ms = int(delta.total_seconds() * 1000)

    def fail(self, error_message: str, error_details: dict[str, Any] | None = None) -> None:
        """Mark job as failed with error info."""
        self.status = "failed"
        self.completed_at = datetime.now(tz=datetime.UTC)
        self.error_message = error_message
        self.error = error_details or {"message": error_message}

        if self.started_at:
            delta = self.completed_at - self.started_at
            self.execution_time_ms = int(delta.total_seconds() * 1000)

    def cancel(self) -> None:
        """Mark job as cancelled."""
        self.status = "cancelled"
        self.completed_at = datetime.now(tz=datetime.UTC)

    def update_progress(self, progress: int, message: str | None = None) -> None:
        """Update job progress."""
        self.progress = min(max(progress, 0), 100)
        if message:
            self.progress_message = message
