"""Add status column to projects table

Revision ID: 019_project_status
Revises: 018_templates_columns
Create Date: 2026-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '019_project_status'
down_revision: Union[str, None] = '018_templates_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status column to projects table."""
    op.execute("""
        ALTER TABLE projects 
        ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_projects_status ON projects(status)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_projects_status")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS status")
