"""add design context and refinement jobs

Revision ID: 009_design_context
Revises: 005_conversations
Create Date: 2024-01-18 12:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '009_design_context'
down_revision = '005_conversations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create design_contexts table
    op.create_table(
        'design_contexts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('design_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('designs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('messages', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('parameters', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('parameter_history', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('iteration_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_instruction', sa.Text(), nullable=True),
        sa.Column('ai_context', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('ix_design_contexts_design_id', 'design_contexts', ['design_id'])

    # Create design_refinement_jobs table
    op.create_table(
        'design_refinement_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('design_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('designs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('instruction', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('result_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('design_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('old_parameters', postgresql.JSONB(), nullable=True),
        sa.Column('new_parameters', postgresql.JSONB(), nullable=True),
        sa.Column('ai_response', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index('ix_design_refinement_jobs_design_id', 'design_refinement_jobs', ['design_id'])
    op.create_index('ix_design_refinement_jobs_user_id', 'design_refinement_jobs', ['user_id'])
    op.create_index('ix_design_refinement_jobs_status', 'design_refinement_jobs', ['status'])


def downgrade() -> None:
    op.drop_index('ix_design_refinement_jobs_status')
    op.drop_index('ix_design_refinement_jobs_user_id')
    op.drop_index('ix_design_refinement_jobs_design_id')
    op.drop_table('design_refinement_jobs')

    op.drop_index('ix_design_contexts_design_id')
    op.drop_table('design_contexts')
