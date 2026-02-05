"""
Audit log model for tracking all system actions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    """
    Comprehensive audit logging for security and compliance.

    Records all significant actions in the system for:
    - Security auditing
    - Compliance requirements
    - Debugging and support
    - Analytics and usage patterns

    Context schema example:
    {
        "resourceId": "uuid",
        "resourceType": "design",
        "changes": {
            "name": {"old": "Draft", "new": "Final Design"},
            "status": {"old": "draft", "new": "ready"}
        },
        "requestId": "req_abc123",
        "sessionId": "sess_xyz789"
    }
    """

    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Actor (who performed the action)
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
    )  # user, system, api_key, webhook

    # Action classification
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    # Actions: create, read, update, delete, export, share, login,
    #          logout, password_change, api_key_create, etc.

    # Resource being acted upon
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # user, design, project, template, job, api_key, etc.

    resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Detailed context (JSONB)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Request metadata
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Result
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
    )  # success, failure, error

    error_message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User | None"] = relationship("User")

    # Indexes for common query patterns
    __table_args__ = (
        Index(
            "idx_audit_resource",
            "resource_type",
            "resource_id",
            "created_at",
        ),
        Index(
            "idx_audit_user_actions",
            "user_id",
            "action",
            "created_at",
        ),
        Index(
            "idx_audit_context",
            "context",
            postgresql_using="gin",
        ),
        # Partial index for failed actions (security focus)
        Index(
            "idx_audit_failures",
            "status",
            "created_at",
            postgresql_where="status != 'success'",
        ),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type})>"

    @classmethod
    def log(
        cls,
        action: str,
        resource_type: str,
        resource_id: UUID | None = None,
        user_id: UUID | None = None,
        actor_type: str = "user",
        context: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> "AuditLog":
        """
        Create an audit log entry.

        This is a convenience method for creating audit logs.
        The caller is responsible for adding to session and committing.

        Example:
            log = AuditLog.log(
                action="create",
                resource_type="design",
                resource_id=design.id,
                user_id=current_user.id,
                context={"name": design.name},
            )
            db.add(log)
        """
        return cls(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            actor_type=actor_type,
            context=context or {},
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
        )

    @classmethod
    def log_success(
        cls,
        action: str,
        resource_type: str,
        **kwargs: Any,
    ) -> "AuditLog":
        """Create a successful audit log entry."""
        return cls.log(
            action=action,
            resource_type=resource_type,
            status="success",
            **kwargs,
        )

    @classmethod
    def log_failure(
        cls,
        action: str,
        resource_type: str,
        error_message: str,
        **kwargs: Any,
    ) -> "AuditLog":
        """Create a failed audit log entry."""
        return cls.log(
            action=action,
            resource_type=resource_type,
            status="failure",
            error_message=error_message,
            **kwargs,
        )


# Common audit action constants
class AuditActions:
    """Constants for common audit actions."""

    # CRUD
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"

    # Sharing
    SHARE = "share"
    UNSHARE = "unshare"

    # Export
    EXPORT = "export"
    DOWNLOAD = "download"

    # API Keys
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"

    # Moderation
    MODERATE = "moderate"
    APPEAL = "appeal"

    # Admin
    ADMIN_ACTION = "admin_action"
    IMPERSONATE = "impersonate"
