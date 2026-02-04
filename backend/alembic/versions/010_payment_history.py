"""Add payment history table

Revision ID: 010_payment_history
Revises: 009_design_context
Create Date: 2026-01-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '010_payment_history'
down_revision: Union[str, None] = '009_design_context'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create payment_history table
    op.create_table(
        'payment_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Stripe identifiers
        sa.Column('stripe_payment_intent_id', sa.String(255), nullable=True),
        sa.Column('stripe_invoice_id', sa.String(255), nullable=True),
        sa.Column('stripe_charge_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        
        # Payment details
        sa.Column('payment_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='usd'),
        sa.Column('description', sa.String(500), nullable=False),
        
        # Payment method info
        sa.Column('payment_method_type', sa.String(50), nullable=True),
        sa.Column('payment_method_last4', sa.String(4), nullable=True),
        
        # Timestamps
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        
        # Invoice/Receipt URLs
        sa.Column('invoice_url', sa.Text(), nullable=True),
        sa.Column('invoice_pdf_url', sa.Text(), nullable=True),
        sa.Column('receipt_url', sa.Text(), nullable=True),
        
        # Failure details
        sa.Column('failure_code', sa.String(100), nullable=True),
        sa.Column('failure_message', sa.Text(), nullable=True),
        
        # Extra data (JSONB for flexibility)
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        
        # Timestamps from base
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('idx_payment_history_user_id', 'payment_history', ['user_id'])
    op.create_index('idx_payment_history_user_created', 'payment_history', ['user_id', 'created_at'])
    op.create_index('idx_payment_history_status', 'payment_history', ['status'])
    op.create_index('idx_payment_history_type', 'payment_history', ['payment_type'])
    op.create_index('idx_payment_history_stripe_payment_intent', 'payment_history', ['stripe_payment_intent_id'])
    op.create_index('idx_payment_history_stripe_invoice', 'payment_history', ['stripe_invoice_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_payment_history_stripe_invoice', table_name='payment_history')
    op.drop_index('idx_payment_history_stripe_payment_intent', table_name='payment_history')
    op.drop_index('idx_payment_history_type', table_name='payment_history')
    op.drop_index('idx_payment_history_status', table_name='payment_history')
    op.drop_index('idx_payment_history_user_created', table_name='payment_history')
    op.drop_index('idx_payment_history_user_id', table_name='payment_history')
    
    # Drop table
    op.drop_table('payment_history')
