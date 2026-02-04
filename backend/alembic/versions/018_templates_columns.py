"""Add missing columns to templates table

Revision ID: 018_templates_columns
Revises: 017_missing_tables
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '018_templates_columns'
down_revision: Union[str, None] = '017_missing_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to templates table
    op.execute("""
        ALTER TABLE templates 
        ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT false
    """)
    op.execute("""
        ALTER TABLE templates 
        ADD COLUMN IF NOT EXISTS created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL
    """)
    op.execute("""
        ALTER TABLE templates 
        ADD COLUMN IF NOT EXISTS source_design_id UUID REFERENCES designs(id) ON DELETE SET NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE templates DROP COLUMN IF EXISTS source_design_id")
    op.execute("ALTER TABLE templates DROP COLUMN IF EXISTS created_by_user_id")
    op.execute("ALTER TABLE templates DROP COLUMN IF EXISTS is_public")
