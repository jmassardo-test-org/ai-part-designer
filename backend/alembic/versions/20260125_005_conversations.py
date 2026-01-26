"""Add conversations table

Revision ID: 005_conversations
Revises: 20240124_004_abuse_protection
Create Date: 2026-01-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_conversations'
down_revision = '004_abuse_protection'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create conversations table using VARCHAR for status to avoid enum issues
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('intent_data', postgresql.JSONB, nullable=True),
        sa.Column('build_plan_data', postgresql.JSONB, nullable=True),
        sa.Column('result_job_id', sa.String(100), nullable=True),
        sa.Column('result_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_status', 'conversations', ['status'])
    op.create_index('ix_conversations_created_at', 'conversations', ['created_at'])
    
    # Create conversation_messages table using VARCHAR for role/type
    op.create_table(
        'conversation_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('message_type', sa.String(20), nullable=False, server_default='text'),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('extra_data', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_conversation_messages_conversation_id', 'conversation_messages', ['conversation_id'])
    op.create_index('ix_conversation_messages_created_at', 'conversation_messages', ['created_at'])


def downgrade() -> None:
    # Drop tables
    op.drop_table('conversation_messages')
    op.drop_table('conversations')
