"""Add OAuth connections table

Revision ID: 011_oauth_connections
Revises: 010_payment_history
Create Date: 2025-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "011_oauth_connections"
down_revision: Union[str, None] = "010_payment_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create oauth_connections table."""
    op.create_table(
        "oauth_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(255), nullable=True),
        sa.Column("provider_username", sa.String(255), nullable=True),
        sa.Column("access_token", sa.String(2000), nullable=True),
        sa.Column("refresh_token", sa.String(2000), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "profile_data",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),
        sa.UniqueConstraint(
            "provider", "provider_user_id", name="uq_oauth_provider_user_id"
        ),
    )

    # Create indexes
    op.create_index(
        "idx_oauth_connections_user_id",
        "oauth_connections",
        ["user_id"],
    )
    op.create_index(
        "idx_oauth_provider_user",
        "oauth_connections",
        ["provider", "provider_user_id"],
    )


def downgrade() -> None:
    """Drop oauth_connections table."""
    op.drop_index("idx_oauth_provider_user", table_name="oauth_connections")
    op.drop_index("idx_oauth_connections_user_id", table_name="oauth_connections")
    op.drop_table("oauth_connections")
