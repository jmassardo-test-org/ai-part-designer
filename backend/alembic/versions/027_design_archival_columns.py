"""Add archival columns to designs for cold storage.

Revision ID: 027_design_archival_columns
Revises: 026_design_copy_tracking
Create Date: 2026-02-24 10:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = "027_design_archival_columns"
down_revision = "026_design_copy_tracking"
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


def upgrade() -> None:
    """Add archived_at and archive_location columns for design archival.

    These columns support archiving inactive designs to cold storage:
    - archived_at: Timestamp when the design was archived
    - archive_location: Object storage key for the archived data

    A partial index on archived_at enables efficient querying of archived designs.

    This migration is idempotent.
    """
    # Add archived_at column (if not exists)
    if not _column_exists("designs", "archived_at"):
        op.add_column(
            "designs",
            sa.Column(
                "archived_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    # Add archive_location column (if not exists)
    if not _column_exists("designs", "archive_location"):
        op.add_column(
            "designs",
            sa.Column(
                "archive_location",
                sa.String(500),
                nullable=True,
            ),
        )

    # Create partial index on archived_at WHERE archived_at IS NOT NULL
    if not _index_exists("designs", "idx_designs_archived"):
        op.create_index(
            "idx_designs_archived",
            "designs",
            ["archived_at"],
            postgresql_where=sa.text("archived_at IS NOT NULL"),
        )


def downgrade() -> None:
    """Remove archival columns from designs."""
    # Drop index
    if _index_exists("designs", "idx_designs_archived"):
        op.drop_index("idx_designs_archived", table_name="designs")

    # Drop columns
    if _column_exists("designs", "archive_location"):
        op.drop_column("designs", "archive_location")

    if _column_exists("designs", "archived_at"):
        op.drop_column("designs", "archived_at")
