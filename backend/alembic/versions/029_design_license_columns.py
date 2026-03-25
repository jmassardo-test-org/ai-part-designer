"""Add license columns to designs table (Epic 13).

Revision ID: 029_design_license_columns
Revises: 18f5c96f8225
Create Date: 2026-02-25
"""

import sqlalchemy as sa

from alembic import op

revision = "029_design_license_columns"
down_revision = "18f5c96f8225"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists in a table."""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    """Add license_type, custom_license_text, and custom_allows_remix to designs."""
    if not _column_exists("designs", "license_type"):
        op.add_column(
            "designs",
            sa.Column("license_type", sa.String(30), nullable=True),
        )
        op.create_index(
            "idx_designs_license_type",
            "designs",
            ["license_type"],
            postgresql_where="license_type IS NOT NULL",
        )

    if not _column_exists("designs", "custom_license_text"):
        op.add_column(
            "designs",
            sa.Column("custom_license_text", sa.Text(), nullable=True),
        )

    if not _column_exists("designs", "custom_allows_remix"):
        op.add_column(
            "designs",
            sa.Column(
                "custom_allows_remix",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    """Remove license columns from designs."""
    op.drop_index("idx_designs_license_type", table_name="designs")
    op.drop_column("designs", "custom_allows_remix")
    op.drop_column("designs", "custom_license_text")
    op.drop_column("designs", "license_type")
