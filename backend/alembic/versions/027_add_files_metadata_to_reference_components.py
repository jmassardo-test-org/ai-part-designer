"""Add files_metadata to reference_components.

Revision ID: 027_files_metadata
Revises: 026_design_copy_tracking
Create Date: 2026-02-20

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "027_files_metadata"
down_revision: Union[str, None] = "026_design_copy_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reference_components",
        sa.Column(
            "files_metadata",
            postgresql.JSONB(),
            nullable=True,
            comment="File metadata: {cad_file: {...}, datasheet: {...}, thumbnail: {...}}",
        ),
    )


def downgrade() -> None:
    op.drop_column("reference_components", "files_metadata")
