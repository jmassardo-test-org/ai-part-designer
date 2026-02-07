"""Add copied_from_id to designs for copy tracking.

Revision ID: 026_design_copy_tracking
Revises: 025_design_remix_tracking
Create Date: 2026-02-04 19:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "026_design_copy_tracking"
down_revision = "025_design_remix_tracking"
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
    """Add copied_from_id column for tracking design copies.

    This is distinct from remixed_from_id:
    - copied_from_id: Direct copy of design (same user, within projects)
    - remixed_from_id: Remix from marketplace (different user, attribution)

    This migration is idempotent.
    """
    # Add copied_from_id column (if not exists)
    if not _column_exists("designs", "copied_from_id"):
        op.add_column(
            "designs",
            sa.Column(
                "copied_from_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )

    # Add foreign key constraint (if not exists)
    if not _fk_exists("designs", "fk_designs_copied_from_id"):
        op.create_foreign_key(
            "fk_designs_copied_from_id",
            "designs",
            "designs",
            ["copied_from_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Add index for copied_from_id (if not exists)
    if not _index_exists("designs", "idx_designs_copied_from_id"):
        op.create_index(
            "idx_designs_copied_from_id",
            "designs",
            ["copied_from_id"],
        )


def downgrade() -> None:
    """Remove copied_from_id column."""
    # Drop index
    op.drop_index("idx_designs_copied_from_id", table_name="designs")

    # Drop foreign key
    op.drop_constraint("fk_designs_copied_from_id", "designs", type_="foreignkey")

    # Drop column
    op.drop_column("designs", "copied_from_id")
