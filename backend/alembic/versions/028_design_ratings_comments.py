"""Add design ratings and comments tables with avg_rating on designs.

Revision ID: 028_design_ratings_comments
Revises: 027_design_archival_columns
Create Date: 2026-02-25
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "028_design_ratings_comments"
down_revision = "027_design_archival_columns"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists in a table."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def _table_exists(table: str) -> bool:
    """Check if a table already exists."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    return table in inspector.get_table_names()


def upgrade() -> None:
    """Create design_ratings and design_comments tables, add avg_rating to designs."""
    # --- design_ratings table ---
    if not _table_exists("design_ratings"):
        op.create_table(
            "design_ratings",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "design_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("designs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("review", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("design_id", "user_id", name="uq_design_rating_user"),
            sa.CheckConstraint(
                "rating >= 1 AND rating <= 5", name="ck_design_rating_range"
            ),
        )
        op.create_index(
            "idx_design_ratings_design", "design_ratings", ["design_id"]
        )
        op.create_index("idx_design_ratings_user", "design_ratings", ["user_id"])

    # --- design_comments table ---
    if not _table_exists("design_comments"):
        op.create_table(
            "design_comments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "design_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("designs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "parent_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("design_comments.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "is_hidden",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "hidden_by_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("hidden_reason", sa.String(255), nullable=True),
            sa.Column(
                "is_edited",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "idx_design_comments_design", "design_comments", ["design_id"]
        )
        op.create_index(
            "idx_design_comments_user", "design_comments", ["user_id"]
        )
        op.create_index(
            "idx_design_comments_parent", "design_comments", ["parent_id"]
        )
        op.create_index(
            "idx_design_comments_design_created",
            "design_comments",
            ["design_id", "created_at"],
        )

    # --- Add avg_rating and total_ratings to designs ---
    if not _column_exists("designs", "avg_rating"):
        op.add_column("designs", sa.Column("avg_rating", sa.Float(), nullable=True))

    if not _column_exists("designs", "total_ratings"):
        op.add_column(
            "designs",
            sa.Column(
                "total_ratings",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )

    # Marketplace rating sort index
    op.create_index(
        "idx_designs_marketplace_rating",
        "designs",
        ["avg_rating"],
        postgresql_where=(
            "deleted_at IS NULL AND is_public = TRUE AND published_at IS NOT NULL"
        ),
    )


def downgrade() -> None:
    """Remove design ratings and comments tables."""
    op.drop_index("idx_designs_marketplace_rating", "designs")
    op.drop_column("designs", "total_ratings")
    op.drop_column("designs", "avg_rating")
    op.drop_table("design_comments")
    op.drop_table("design_ratings")
