"""
Conversation models for chat-based CAD generation.

Stores chat sessions with message history for iterative part design.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ConversationStatus(str, enum.Enum):
    """Status of a conversation."""
    
    ACTIVE = "active"  # Ongoing conversation
    CLARIFYING = "clarifying"  # Waiting for user response to clarification
    READY = "ready"  # Has enough info to generate
    GENERATING = "generating"  # CAD generation in progress
    COMPLETED = "completed"  # Successfully generated
    FAILED = "failed"  # Generation failed
    ABANDONED = "abandoned"  # User left without completing


class MessageRole(str, enum.Enum):
    """Role of a message sender."""
    
    USER = "user"  # User input
    ASSISTANT = "assistant"  # AI response
    SYSTEM = "system"  # System messages (errors, status updates)


class MessageType(str, enum.Enum):
    """Type of message content."""
    
    TEXT = "text"  # Plain text
    CLARIFICATION = "clarification"  # AI asking for clarification
    CONFIRMATION = "confirmation"  # AI confirming understanding
    PLAN = "plan"  # Build plan preview
    PROGRESS = "progress"  # Generation progress update
    RESULT = "result"  # Final result with downloads
    ERROR = "error"  # Error message


class Conversation(Base, TimestampMixin):
    """A chat conversation for CAD generation."""
    
    __tablename__ = "conversations"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Conversation metadata
    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    # Using String instead of Enum to avoid PostgreSQL enum creation issues
    status: Mapped[str] = mapped_column(
        String(50),
        default=ConversationStatus.ACTIVE.value,
        nullable=False,
    )
    
    # Accumulated understanding (updated as conversation progresses)
    intent_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    build_plan_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    
    # Result data (populated on completion)
    result_job_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    result_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation",
        order_by="ConversationMessage.created_at",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, status={self.status})>"


class ConversationMessage(Base, TimestampMixin):
    """A single message in a conversation."""
    
    __tablename__ = "conversation_messages"
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Message content
    # Using String instead of Enum to avoid PostgreSQL enum creation issues
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    message_type: Mapped[str] = mapped_column(
        String(20),
        default=MessageType.TEXT.value,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # Structured data (for clarifications, plans, results)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    
    # Relationship
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role}, type={self.message_type})>"
