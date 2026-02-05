"""
Design Context model for AI-powered design iteration.

Tracks conversation history and parameters for iterative design refinement.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.design import Design
    from app.models.user import User


class DesignContext(Base):
    """
    Stores conversation context for iterative design refinement.

    Enables AI to understand the history of changes and user intent
    when refining a design with follow-up instructions.
    """

    __tablename__ = "design_contexts"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    design_id: Mapped[UUID] = mapped_column(
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Conversation history - list of messages
    # [{"role": "user", "content": "...", "timestamp": "..."}, ...]
    messages: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Current parameters - flattened parameter state
    # {"length": 100, "width": 50, "height": 30, ...}
    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Parameter history - track changes over iterations
    # [{"version": 1, "parameters": {...}, "instruction": "..."}, ...]
    parameter_history: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Iteration tracking
    iteration_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Last instruction for quick reference
    last_instruction: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # AI model context (for advanced use)
    ai_context: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Cached AI embeddings or context for faster inference",
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
        back_populates="context",
    )

    def __repr__(self) -> str:
        return f"<DesignContext {self.id} iterations={self.iteration_count}>"

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        message = {
            "role": "user",
            "content": content,
            "timestamp": datetime.now(tz=datetime.UTC).isoformat(),
        }
        self.messages = [*self.messages, message]
        self.last_instruction = content

    def add_assistant_message(self, content: str, parameters: dict | None = None) -> None:
        """Add an assistant message to the conversation."""
        message = {
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now(tz=datetime.UTC).isoformat(),
        }
        if parameters:
            message["parameters"] = parameters
        self.messages = [*self.messages, message]

    def add_system_message(self, content: str) -> None:
        """Add a system message to the conversation."""
        message = {
            "role": "system",
            "content": content,
            "timestamp": datetime.now(tz=datetime.UTC).isoformat(),
        }
        self.messages = [*self.messages, message]

    def increment_iteration(self, instruction: str, new_parameters: dict) -> None:
        """Record a new iteration with parameter changes."""
        self.iteration_count += 1

        # Record parameter history
        history_entry = {
            "version": self.iteration_count,
            "parameters": new_parameters.copy(),
            "instruction": instruction,
            "timestamp": datetime.now(tz=datetime.UTC).isoformat(),
        }
        self.parameter_history = [*self.parameter_history, history_entry]

        # Update current parameters
        self.parameters = new_parameters.copy()
        self.last_instruction = instruction

    def get_conversation_for_ai(self) -> list[dict]:
        """
        Get conversation formatted for AI API.

        Returns a list of messages suitable for chat completion APIs.
        """
        ai_messages = []

        # Add system context
        ai_messages.append(
            {
                "role": "system",
                "content": self._get_system_prompt(),
            }
        )

        # Add conversation history (limit to last N messages)
        recent_messages = self.messages[-20:]  # Keep last 20 messages
        for msg in recent_messages:
            ai_messages.append(
                {
                    "role": msg["role"],
                    "content": msg["content"],
                }
            )

        return ai_messages

    def _get_system_prompt(self) -> str:
        """Generate system prompt with current context."""
        param_str = ", ".join([f"{k}={v}" for k, v in self.parameters.items()])

        return f"""You are an AI assistant helping to refine a 3D CAD design.

Current design parameters:
{param_str or "No parameters set yet"}

Iteration count: {self.iteration_count}

When the user asks to modify the design:
1. Understand their intent
2. Identify which parameters should change
3. Calculate new parameter values
4. Respond with the changes you'll make

Be concise and specific about what changes you'll make."""

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "design_id": str(self.design_id),
            "messages": self.messages,
            "parameters": self.parameters,
            "iteration_count": self.iteration_count,
            "last_instruction": self.last_instruction,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class DesignRefinementJob(Base):
    """
    Tracks async refinement jobs for designs.

    Used when design refinement requires background processing.
    """

    __tablename__ = "design_refinement_jobs"

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

    # Job details
    instruction: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, processing, completed, failed

    # Results
    result_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("design_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Parameter changes
    old_parameters: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    new_parameters: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # AI response
    ai_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    design: Mapped[Design] = relationship("Design")
    user: Mapped[User] = relationship("User")

    def __repr__(self) -> str:
        return f"<DesignRefinementJob {self.id} status={self.status}>"

    def start(self) -> None:
        """Mark job as started."""
        self.status = "processing"
        self.started_at = datetime.now(tz=datetime.UTC)

    def complete(self, version_id: UUID, new_params: dict, ai_response: str) -> None:
        """Mark job as completed."""
        self.status = "completed"
        self.completed_at = datetime.now(tz=datetime.UTC)
        self.result_version_id = version_id
        self.new_parameters = new_params
        self.ai_response = ai_response

    def fail(self, error: str) -> None:
        """Mark job as failed."""
        self.status = "failed"
        self.completed_at = datetime.now(tz=datetime.UTC)
        self.error_message = error

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "design_id": str(self.design_id),
            "instruction": self.instruction,
            "status": self.status,
            "old_parameters": self.old_parameters,
            "new_parameters": self.new_parameters,
            "ai_response": self.ai_response,
            "result_version_id": str(self.result_version_id) if self.result_version_id else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
