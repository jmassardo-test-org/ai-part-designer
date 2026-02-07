"""Add marketplace fields to designs: user_id, is_starter, thumbnail_url, enclosure_spec, remixed_from_id.

Revision ID: 024_design_marketplace_fields
Revises: 023_marketplace_models
Create Date: 2026-02-02 10:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "024_design_marketplace_fields"
down_revision = "023_marketplace_models"
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
    """Add marketplace fields to designs table.

    This migration is idempotent - it checks for existing schema objects
    before attempting to create them.
    """

    # Add user_id column with foreign key to users table (if not exists)
    if not _column_exists("designs", "user_id"):
        op.add_column(
            "designs",
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
        )

        # Backfill user_id from the related project
        op.execute("""
            UPDATE designs d
            SET user_id = p.user_id
            FROM projects p
            WHERE d.project_id = p.id
            AND d.user_id IS NULL
        """)

        # Make user_id non-nullable after backfill
        op.alter_column("designs", "user_id", nullable=False)

        # Add foreign key constraint
        op.create_foreign_key(
            "fk_designs_user_id",
            "designs",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Add index for user_id (if not exists)
    if not _index_exists("designs", "idx_designs_user_id"):
        op.create_index("idx_designs_user_id", "designs", ["user_id"])

    # Add is_starter boolean column (if not exists)
    if not _column_exists("designs", "is_starter"):
        op.add_column(
            "designs",
            sa.Column(
                "is_starter",
                sa.Boolean,
                server_default="false",
                nullable=False,
            ),
        )

    # Add index for starter designs (if not exists)
    if not _index_exists("designs", "idx_designs_starter"):
        op.create_index(
            "idx_designs_starter",
            "designs",
            ["is_starter"],
            postgresql_where=sa.text("deleted_at IS NULL AND is_starter = TRUE"),
        )

    # Add thumbnail_url column (if not exists)
    if not _column_exists("designs", "thumbnail_url"):
        op.add_column(
            "designs",
            sa.Column(
                "thumbnail_url",
                sa.String(500),
                nullable=True,
            ),
        )

    # Add enclosure_spec JSONB column for CAD v2 specs (if not exists)
    if not _column_exists("designs", "enclosure_spec"):
        op.add_column(
            "designs",
            sa.Column(
                "enclosure_spec",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )

    # Add GIN index for enclosure_spec (if not exists)
    if not _index_exists("designs", "idx_designs_enclosure_spec"):
        op.create_index(
            "idx_designs_enclosure_spec",
            "designs",
            ["enclosure_spec"],
            postgresql_using="gin",
            postgresql_where=sa.text("enclosure_spec IS NOT NULL"),
        )

    # Add remixed_from_id column for tracking remix relationships (if not exists)
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
    """Remove marketplace fields from designs table."""

    # Drop indexes
    op.drop_index("idx_designs_remixed_from_id", table_name="designs")
    op.drop_index("idx_designs_enclosure_spec", table_name="designs")
    op.drop_index("idx_designs_starter", table_name="designs")
    op.drop_index("idx_designs_user_id", table_name="designs")

    # Drop foreign keys
    op.drop_constraint("fk_designs_remixed_from_id", "designs", type_="foreignkey")
    op.drop_constraint("fk_designs_user_id", "designs", type_="foreignkey")

    # Drop columns
    op.drop_column("designs", "remixed_from_id")
    op.drop_column("designs", "enclosure_spec")
    op.drop_column("designs", "thumbnail_url")
    op.drop_column("designs", "is_starter")
    op.drop_column("designs", "user_id")
