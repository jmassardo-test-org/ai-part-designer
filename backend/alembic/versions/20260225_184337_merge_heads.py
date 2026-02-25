"""merge heads

Revision ID: 18f5c96f8225
Revises: 028_design_ratings_comments, 006_add_design_id_to_conversations
Create Date: 2026-02-25 18:43:37.834172+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18f5c96f8225'
down_revision: Union[str, None] = ('028_design_ratings_comments', '006_add_design_id_to_conversations')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
