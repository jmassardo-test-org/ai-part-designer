"""add_notifications_dismissed_at

Revision ID: 019b_notif_dismissed
Revises: 019_project_status
Create Date: 2026-01-26 22:03:02.913884+00:00

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '019b_notif_dismissed'
down_revision: Union[str, None] = '019_project_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add dismissed_at column to notifications table (if not exists)
    if not _column_exists("notifications", "dismissed_at"):
        op.add_column(
            'notifications',
            sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True)
        )
    # Add email_sent_at column to notifications table (if not exists)
    if not _column_exists("notifications", "email_sent_at"):
        op.add_column(
            'notifications',
            sa.Column('email_sent_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    op.drop_column('notifications', 'email_sent_at')
    op.drop_column('notifications', 'dismissed_at')
