"""
OAuth connection model.

Tracks linked OAuth provider accounts for users.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class OAuthConnection(Base, TimestampMixin):
    """
    OAuth provider connection for a user.

    Allows users to link multiple OAuth providers (Google, GitHub)
    to their account for authentication.
    """

    __tablename__ = "oauth_connections"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # OAuth provider info
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # 'google', 'github'

    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )  # User ID from the provider

    provider_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )  # Email from provider (may differ from account email)

    provider_username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )  # Username from provider (e.g., GitHub username)

    # Token storage (encrypted in production)
    access_token: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )
    refresh_token: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Provider profile data
    profile_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )  # Full profile response from provider

    # Last used for login
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="oauth_connections",
    )

    # Unique constraint: one connection per provider per user
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user_id"),
        Index("idx_oauth_provider_user", "provider", "provider_user_id"),
    )

    def __repr__(self) -> str:
        return f"<OAuthConnection(id={self.id}, provider={self.provider}, user_id={self.user_id})>"

    def update_tokens(
        self,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        """Update OAuth tokens."""
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        if expires_at:
            self.token_expires_at = expires_at
        self.last_used_at = datetime.now(tz=UTC)
