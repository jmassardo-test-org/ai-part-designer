"""Add credit balances and transactions tables

Revision ID: 015_credit_balances
Revises: 014_notifications
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '015_credit_balances'
down_revision: Union[str, None] = '014_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create credit_balances table
    op.execute("""
        CREATE TABLE IF NOT EXISTS credit_balances (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            balance INTEGER NOT NULL DEFAULT 0,
            lifetime_earned INTEGER NOT NULL DEFAULT 0,
            lifetime_spent INTEGER NOT NULL DEFAULT 0,
            last_refill_at TIMESTAMP WITH TIME ZONE,
            next_refill_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_credit_balances_user_id ON credit_balances(user_id)")
    
    # Create credit_transactions table
    op.execute("""
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            balance_id UUID NOT NULL REFERENCES credit_balances(id) ON DELETE CASCADE,
            amount INTEGER NOT NULL,
            transaction_type VARCHAR(30) NOT NULL,
            description VARCHAR(255) NOT NULL,
            balance_before INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            reference_type VARCHAR(50),
            reference_id UUID,
            extra_data JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_created ON credit_transactions(user_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON credit_transactions(transaction_type)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS credit_transactions")
    op.execute("DROP TABLE IF EXISTS credit_balances")
