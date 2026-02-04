"""Add marketplace models: design_lists, design_list_items, design_saves.

Also adds marketplace fields to designs table.

Revision ID: 023_marketplace_models
Revises: 022_mfa_columns
Create Date: 2025-02-01 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "023_marketplace_models"
down_revision = "022_mfa_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create marketplace tables and add marketplace fields to designs."""
    
    # Add marketplace fields to designs table
    op.add_column(
        "designs",
        sa.Column("save_count", sa.Integer, server_default="0", nullable=False),
    )
    op.add_column(
        "designs",
        sa.Column("remix_count", sa.Integer, server_default="0", nullable=False),
    )
    op.add_column(
        "designs",
        sa.Column("category", sa.String(50), nullable=True),
    )
    op.add_column(
        "designs",
        sa.Column("featured_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "designs",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create index for marketplace queries
    op.create_index(
        "idx_designs_published",
        "designs",
        ["published_at"],
        postgresql_where=sa.text("published_at IS NOT NULL"),
    )
    op.create_index(
        "idx_designs_featured",
        "designs",
        ["featured_at"],
        postgresql_where=sa.text("featured_at IS NOT NULL"),
    )
    op.create_index("idx_designs_category", "designs", ["category"])
    op.create_index("idx_designs_save_count", "designs", ["save_count"])
    
    # Design lists table (user-created collections)
    op.create_table(
        "design_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(50), server_default="folder", nullable=False),
        sa.Column("color", sa.String(20), server_default="#6366f1", nullable=False),
        sa.Column("is_public", sa.Boolean, server_default="false", nullable=False),
        sa.Column("position", sa.Integer, server_default="0", nullable=False),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_design_lists_user",
        "design_lists",
        ["user_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    
    # Design list items table (junction table)
    op.create_table(
        "design_list_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("design_lists.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "design_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("designs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("position", sa.Integer, server_default="0", nullable=False),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("list_id", "design_id", name="uq_list_design"),
    )
    
    # Design saves table (tracking save actions)
    op.create_table(
        "design_saves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "design_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("designs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "design_id", name="uq_user_design_save"),
    )
    op.create_index("idx_design_saves_design", "design_saves", ["design_id"])


def downgrade() -> None:
    """Remove marketplace tables and fields."""
    
    # Drop tables
    op.drop_table("design_saves")
    op.drop_table("design_list_items")
    op.drop_table("design_lists")
    
    # Drop indexes
    op.drop_index("idx_designs_save_count", "designs")
    op.drop_index("idx_designs_category", "designs")
    op.drop_index("idx_designs_featured", "designs")
    op.drop_index("idx_designs_published", "designs")
    
    # Drop columns
    op.drop_column("designs", "published_at")
    op.drop_column("designs", "featured_at")
    op.drop_column("designs", "category")
    op.drop_column("designs", "remix_count")
    op.drop_column("designs", "save_count")
