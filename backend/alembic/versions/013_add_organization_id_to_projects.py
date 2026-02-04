"""Add organization_id to projects table

Revision ID: 013_add_org_to_projects
Revises: 012_onboarding_fields
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '013_add_org_to_projects'
down_revision: Union[str, None] = '012_onboarding_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def _index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on the given table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    # Check if organizations table exists, if not create it first
    op.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id UUID PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
            settings JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            deleted_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    # Add organization_id column to projects (if not exists)
    if not _column_exists("projects", "organization_id"):
        op.add_column(
            'projects',
            sa.Column(
                'organization_id',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('organizations.id', ondelete='SET NULL'),
                nullable=True,
            )
        )
    
    # Create index on organization_id (if not exists)
    if not _index_exists("projects", "idx_projects_organization"):
        op.create_index(
            'idx_projects_organization',
            'projects',
            ['organization_id']
        )


def downgrade() -> None:
    op.drop_index('idx_projects_organization', 'projects')
    op.drop_column('projects', 'organization_id')
