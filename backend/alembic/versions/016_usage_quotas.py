"""Add usage_quotas table

Revision ID: 016_usage_quotas
Revises: 015_credit_balances
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '016_usage_quotas'
down_revision: Union[str, None] = '015_credit_balances'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create usage_quotas table
    op.execute("""
        CREATE TABLE IF NOT EXISTS usage_quotas (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            storage_used_bytes INTEGER NOT NULL DEFAULT 0,
            active_jobs_count INTEGER NOT NULL DEFAULT 0,
            projects_count INTEGER NOT NULL DEFAULT 0,
            period_start TIMESTAMP WITH TIME ZONE,
            period_generations INTEGER NOT NULL DEFAULT 0,
            period_refinements INTEGER NOT NULL DEFAULT 0,
            period_exports INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_usage_quotas_user_id ON usage_quotas(user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS usage_quotas")
