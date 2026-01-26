"""
API Key model for programmatic access.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
import secrets
import hashlib

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Index,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class APIKey(Base, TimestampMixin):
    """
    API key for programmatic access to the platform.
    
    Keys are stored as SHA-256 hashes. The actual key is only
    shown once at creation time and cannot be recovered.
    
    Scopes define granular permissions:
    - designs:read - Read designs
    - designs:write - Create/modify designs
    - templates:read - Read templates
    - projects:read - Read projects
    - projects:write - Create/modify projects
    - exports:write - Export designs
    - jobs:read - Read job status
    """

    __tablename__ = "api_keys"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Key info
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Key storage (hashed)
    key_prefix: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
    )  # First 8 chars for identification
    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    # Permissions
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_used_ip: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Rate limiting
    rate_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # Requests per minute, null = default

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="api_keys",
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_api_keys_active",
            "user_id",
            "is_active",
            postgresql_where="is_active = TRUE",
        ),
    )

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, prefix={self.key_prefix}...)>"

    @classmethod
    def generate_key(cls) -> tuple[str, str, str]:
        """
        Generate a new API key.
        
        Returns:
            Tuple of (full_key, key_prefix, key_hash)
        """
        # Generate a secure random key
        # Format: apd_{32 random chars} (36 chars total)
        random_part = secrets.token_urlsafe(24)[:32]
        full_key = f"apd_{random_part}"
        
        # Extract prefix for identification
        key_prefix = full_key[:8]
        
        # Hash the full key for storage
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        return full_key, key_prefix, key_hash

    @classmethod
    def hash_key(cls, key: str) -> str:
        """Hash an API key for comparison."""
        return hashlib.sha256(key.encode()).hexdigest()

    @classmethod
    def create_with_key(
        cls,
        user_id: UUID,
        name: str,
        scopes: list[str],
        description: str | None = None,
        expires_at: datetime | None = None,
        rate_limit: int | None = None,
    ) -> tuple["APIKey", str]:
        """
        Create a new API key instance with a generated key.
        
        Returns:
            Tuple of (APIKey instance, raw_key)
            
        Note: The raw_key should be shown to the user once and never stored.
        """
        full_key, key_prefix, key_hash = cls.generate_key()
        
        api_key = cls(
            user_id=user_id,
            name=name,
            description=description,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes,
            expires_at=expires_at,
            rate_limit=rate_limit,
        )
        
        return api_key, full_key

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def has_scope(self, scope: str) -> bool:
        """Check if the key has a specific scope."""
        # Check for wildcard scope
        if "*" in self.scopes:
            return True
        
        # Check exact match
        if scope in self.scopes:
            return True
        
        # Check partial match (e.g., "designs:*" matches "designs:read")
        scope_parts = scope.split(":")
        if len(scope_parts) == 2:
            wildcard_scope = f"{scope_parts[0]}:*"
            if wildcard_scope in self.scopes:
                return True
        
        return False

    def record_usage(self, ip_address: str | None = None) -> None:
        """Record API key usage."""
        self.last_used_at = datetime.utcnow()
        self.last_used_ip = ip_address
        self.usage_count += 1

    def revoke(self) -> None:
        """Revoke the API key."""
        self.is_active = False
