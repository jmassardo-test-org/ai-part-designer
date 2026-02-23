"""Add design_id to conversations

Revision ID: 006_add_design_id_to_conversations
Revises: 019b_notif_dismissed
Create Date: 2026-02-11
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '006_add_design_id_to_conversations'
down_revision = '019b_notif_dismissed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add design_id column to conversations table."""
    op.add_column(
        'conversations',
        sa.Column(
            'design_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('designs.id', ondelete='SET NULL'),
            nullable=True
        )
    )
    op.create_index('ix_conversations_design_id', 'conversations', ['design_id'])


def downgrade() -> None:
    """Remove design_id column from conversations table."""
    op.drop_index('ix_conversations_design_id', table_name='conversations')
    op.drop_column('conversations', 'design_id')
