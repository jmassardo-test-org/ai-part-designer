"""Abuse protection tables

Revision ID: 004_abuse_protection
Revises: 003_reference_components
Create Date: 2024-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '004_abuse_protection'
down_revision: Union[str, None] = '003_reference_components'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Usage Records table
    op.create_table(
        'usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_usage_records_user_id', 'usage_records', ['user_id'])
    op.create_index('ix_usage_records_resource_type', 'usage_records', ['resource_type'])
    op.create_index('ix_usage_records_period_start', 'usage_records', ['period_start'])
    op.create_index(
        'ix_usage_user_resource_period',
        'usage_records',
        ['user_id', 'resource_type', 'period_type', 'period_start'],
        unique=True,
    )
    
    # Concurrent Operations table
    op.create_table(
        'concurrent_operations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_concurrent_user_type', 'concurrent_operations',
                    ['user_id', 'operation_type'])
    
    # User Bans table
    op.create_table(
        'user_bans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('ban_type', sa.String(50), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('banned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('lifted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lifted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('violation_count', sa.Integer(), server_default='1'),
        sa.Column('violation_history', postgresql.JSONB(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_bans_user_id', 'user_bans', ['user_id'])
    op.create_index('ix_user_bans_ip_address', 'user_bans', ['ip_address'])
    op.create_index('ix_user_bans_is_active', 'user_bans', ['is_active'])
    
    # Abuse Reports table
    op.create_table(
        'abuse_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence', postgresql.JSONB(), server_default='{}'),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default="'pending'"),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_taken', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_abuse_reports_user_id', 'abuse_reports', ['user_id'])
    op.create_index('ix_abuse_reports_status', 'abuse_reports', ['status'])
    op.create_index('ix_abuse_reports_severity', 'abuse_reports', ['severity'])
    op.create_index('ix_abuse_reports_created_at', 'abuse_reports', ['created_at'])
    op.create_index('ix_abuse_reports_trigger_type', 'abuse_reports', ['trigger_type'])


def downgrade() -> None:
    op.drop_table('abuse_reports')
    op.drop_table('user_bans')
    op.drop_table('concurrent_operations')
    op.drop_table('usage_records')
