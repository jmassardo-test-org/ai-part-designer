"""Add remixed_from_id to designs for tracking remix relationships.

Revision ID: 025_design_remix_tracking
Revises: 024_design_marketplace_fields
Create Date: 2026-02-02 11:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "025_design_remix_tracking"
down_revision = "024_design_marketplace_fields"
branch_labels = None
depends_on = None


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


def _fk_exists(table_name: str, constraint_name: str) -> bool:
    """Check if a foreign key constraint exists on the given table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    fks = [fk["name"] for fk in inspector.get_foreign_keys(table_name)]
    return constraint_name in fks


def upgrade() -> None:
    """Add remixed_from_id column for tracking remix relationships.

    This migration is idempotent - it checks for existing schema objects
    before attempting to create them.
    """

    # Add remixed_from_id column (if not exists)
    if not _column_exists("designs", "remixed_from_id"):
        op.add_column(
            "designs",
            sa.Column(
                "remixed_from_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )

    # Add foreign key constraint for remix tracking (if not exists)
    if not _fk_exists("designs", "fk_designs_remixed_from_id"):
        op.create_foreign_key(
            "fk_designs_remixed_from_id",
            "designs",
            "designs",
            ["remixed_from_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Add index for remixed_from_id (if not exists)
    if not _index_exists("designs", "idx_designs_remixed_from_id"):
        op.create_index("idx_designs_remixed_from_id", "designs", ["remixed_from_id"])


def downgrade() -> None:
    """Remove remixed_from_id column."""

    # Drop index
    op.drop_index("idx_designs_remixed_from_id", table_name="designs")

    # Drop foreign key
    op.drop_constraint("fk_designs_remixed_from_id", "designs", type_="foreignkey")

    # Drop column
    op.drop_column("designs", "remixed_from_id")
