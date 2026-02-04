"""Add MFA columns to users table.

Revision ID: 022
Revises: 021_rating_models
Create Date: 2026-01-28

"""

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "022_mfa_columns"
down_revision = "021_rating_models"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add MFA-related columns to users table."""
    # Add MFA columns (if not exist)
    if not _column_exists("users", "mfa_enabled"):
        op.add_column(
            "users",
            sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
        )
    if not _column_exists("users", "mfa_secret"):
        op.add_column(
            "users",
            sa.Column("mfa_secret", sa.String(64), nullable=True),
        )
    if not _column_exists("users", "mfa_backup_codes"):
        op.add_column(
            "users",
            sa.Column("mfa_backup_codes", JSONB, nullable=True),
        )
    if not _column_exists("users", "mfa_enabled_at"):
        op.add_column(
            "users",
            sa.Column("mfa_enabled_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Remove MFA-related columns from users table."""
    op.drop_column("users", "mfa_enabled_at")
    op.drop_column("users", "mfa_backup_codes")
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "mfa_enabled")
