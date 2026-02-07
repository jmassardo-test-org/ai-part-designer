"""Add community rating and moderation models.

Revision ID: 021_rating_models
Revises: 020_team_models
Create Date: 2025-01-15 12:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "021_rating_models"
down_revision = "020_team_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create rating, feedback, comment, report, and ban tables."""

    # Template ratings table (1-5 stars)
    op.create_table(
        "template_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("templates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("review", sa.Text, nullable=True),
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
        sa.UniqueConstraint("template_id", "user_id", name="uq_template_rating_user"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
    )
    op.create_index(
        "idx_template_ratings_template",
        "template_ratings",
        ["template_id"],
    )
    op.create_index(
        "idx_template_ratings_user",
        "template_ratings",
        ["user_id"],
    )

    # Template feedback table (thumbs up/down)
    op.create_table(
        "template_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("templates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("feedback_type", sa.String(20), nullable=False),
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
        sa.UniqueConstraint("template_id", "user_id", name="uq_template_feedback_user"),
    )
    op.create_index(
        "idx_template_feedback_template",
        "template_feedback",
        ["template_id"],
    )
    op.create_index(
        "idx_template_feedback_user",
        "template_feedback",
        ["user_id"],
    )

    # Template comments table with threading
    op.create_table(
        "template_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("templates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("template_comments.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_hidden", sa.Boolean, nullable=False, default=False),
        sa.Column(
            "hidden_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hidden_reason", sa.String(255), nullable=True),
        sa.Column("is_edited", sa.Boolean, nullable=False, default=False),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_template_comments_template",
        "template_comments",
        ["template_id"],
    )
    op.create_index(
        "idx_template_comments_user",
        "template_comments",
        ["user_id"],
    )
    op.create_index(
        "idx_template_comments_parent",
        "template_comments",
        ["parent_id"],
    )

    # Content reports table
    op.create_table(
        "content_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reporter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column(
            "resolved_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("action_taken", sa.String(50), nullable=True),
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
        sa.UniqueConstraint(
            "reporter_id", "target_type", "target_id", name="uq_report_user_target"
        ),
    )
    op.create_index(
        "idx_reports_reporter",
        "content_reports",
        ["reporter_id"],
    )
    op.create_index(
        "idx_reports_target",
        "content_reports",
        ["target_type", "target_id"],
    )
    op.create_index(
        "idx_reports_status",
        "content_reports",
        ["status"],
    )

    # User bans table - add missing columns to existing table from 004_abuse_protection
    # The table already exists with different schema, so we add the new columns
    from sqlalchemy.engine import reflection

    bind = op.get_bind()
    inspector = reflection.Inspector.from_engine(bind)

    if 'user_bans' not in inspector.get_table_names():
        # Create table if it doesn't exist (shouldn't happen with proper migration order)
        op.create_table(
            "user_bans",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("reason", sa.Text, nullable=False),
            sa.Column(
                "banned_by_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("is_permanent", sa.Boolean, nullable=False, default=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, default=True),
            sa.Column(
                "unbanned_by_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("unbanned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("unban_reason", sa.Text, nullable=True),
            sa.Column(
                "related_report_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("content_reports.id", ondelete="SET NULL"),
                nullable=True,
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
        )
        op.create_index(
            "idx_bans_user",
            "user_bans",
            ["user_id"],
        )
        op.create_index(
            "idx_bans_active",
            "user_bans",
            ["is_active"],
        )
    else:
        # Table exists, add missing columns if not present
        columns = [c['name'] for c in inspector.get_columns('user_bans')]
        if 'unbanned_by_id' not in columns:
            op.add_column('user_bans', sa.Column('unbanned_by_id', postgresql.UUID(as_uuid=True), nullable=True))
        if 'unbanned_at' not in columns:
            op.add_column('user_bans', sa.Column('unbanned_at', sa.DateTime(timezone=True), nullable=True))
        if 'unban_reason' not in columns:
            op.add_column('user_bans', sa.Column('unban_reason', sa.Text, nullable=True))
        if 'related_report_id' not in columns:
            op.add_column('user_bans', sa.Column('related_report_id', postgresql.UUID(as_uuid=True), nullable=True))
        if 'is_permanent' not in columns:
            op.add_column('user_bans', sa.Column('is_permanent', sa.Boolean, nullable=False, server_default='false'))
        if 'banned_by_id' not in columns:
            op.add_column('user_bans', sa.Column('banned_by_id', postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    """Drop rating, feedback, comment, report tables and added columns."""
    # Don't drop user_bans table - it's created in 004_abuse_protection
    # Just drop the columns we added
    from sqlalchemy.engine import reflection
    bind = op.get_bind()
    inspector = reflection.Inspector.from_engine(bind)
    columns = [c['name'] for c in inspector.get_columns('user_bans')]

    if 'related_report_id' in columns:
        op.drop_column('user_bans', 'related_report_id')
    if 'unban_reason' in columns:
        op.drop_column('user_bans', 'unban_reason')
    if 'unbanned_at' in columns:
        op.drop_column('user_bans', 'unbanned_at')
    if 'unbanned_by_id' in columns:
        op.drop_column('user_bans', 'unbanned_by_id')

    op.drop_table("content_reports")
    op.drop_table("template_comments")
    op.drop_table("template_feedback")
    op.drop_table("template_ratings")
