"""Add onboarding fields to users

Revision ID: 012_onboarding_fields
Revises: 011_oauth_connections
Create Date: 2025-01-22

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "012_onboarding_fields"
down_revision: Union[str, None] = "011_oauth_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add onboarding tracking fields to users table."""
    if not _column_exists("users", "onboarding_completed"):
        op.add_column(
            "users",
            sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false"),
        )
    if not _column_exists("users", "onboarding_completed_at"):
        op.add_column(
            "users",
            sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _column_exists("users", "onboarding_step"):
        op.add_column(
            "users",
            sa.Column("onboarding_step", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    """Remove onboarding fields from users table."""
    op.drop_column("users", "onboarding_step")
    op.drop_column("users", "onboarding_completed_at")
    op.drop_column("users", "onboarding_completed")
