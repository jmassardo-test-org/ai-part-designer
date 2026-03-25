"""Add evidence_url to content_reports table (Epic 13).

Revision ID: 030_content_report_evidence_url
Revises: 029_design_license_columns
Create Date: 2026-02-25
"""

import sqlalchemy as sa

from alembic import op

revision = "030_content_report_evidence_url"
down_revision = "029_design_license_columns"
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
    """Add evidence_url column to content_reports table."""
    if not _column_exists("content_reports", "evidence_url"):
        op.add_column(
            "content_reports",
            sa.Column("evidence_url", sa.String(2048), nullable=True),
        )


def downgrade() -> None:
    """Remove evidence_url column from content_reports."""
    op.drop_column("content_reports", "evidence_url")
