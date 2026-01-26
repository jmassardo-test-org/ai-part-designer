"""Initial database schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-15

This migration creates all initial tables for the AI Part Designer platform.
Tables are created in dependency order to handle foreign key constraints.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===========================================
    # USERS TABLE
    # ===========================================
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, default="user"),
        sa.Column("status", sa.String(20), nullable=False, default="pending_verification"),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index("idx_users_status", "users", ["status"])

    # ===========================================
    # USER SETTINGS TABLE
    # ===========================================
    op.create_table(
        "user_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default='{"defaultUnits": "mm", "defaultExportFormat": "stl", "theme": "system", "language": "en"}'),
        sa.Column("notifications", postgresql.JSONB(), nullable=False, server_default='{"email": {"jobComplete": true, "weeklyDigest": true, "marketing": false}, "push": {"jobComplete": true}}'),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_user_settings_user", "user_settings", ["user_id"], unique=True)

    # ===========================================
    # SUBSCRIPTIONS TABLE
    # ===========================================
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("tier", sa.String(20), nullable=False, default="free"),
        sa.Column("status", sa.String(20), nullable=False, default="active"),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_subscriptions_user", "subscriptions", ["user_id"], unique=True)
    op.create_index("idx_subscriptions_stripe_customer", "subscriptions", ["stripe_customer_id"])

    # ===========================================
    # FILES TABLE
    # ===========================================
    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_bucket", sa.String(63), nullable=False, default="uploads"),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("cad_format", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="uploading"),
        sa.Column("thumbnail_url", sa.String(1024), nullable=True),
        sa.Column("preview_url", sa.String(1024), nullable=True),
        sa.Column("geometry_info", postgresql.JSONB(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("scan_status", sa.String(20), nullable=True),
        sa.Column("scan_result", postgresql.JSONB(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_files_user", "files", ["user_id"])
    op.create_index("idx_files_mime_type", "files", ["mime_type"])
    op.create_index("idx_files_file_type", "files", ["file_type"])
    op.create_index("idx_files_cad_format", "files", ["cad_format"])
    op.create_index("idx_files_status", "files", ["status"])
    op.create_index("idx_files_user_active", "files", ["user_id", "created_at"], postgresql_where=sa.text("is_deleted = false"))

    # ===========================================
    # PROJECTS TABLE
    # ===========================================
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_projects_user", "projects", ["user_id"])

    # ===========================================
    # TEMPLATES TABLE
    # ===========================================
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("subcategory", sa.String(50), nullable=True),
        sa.Column("parameters", postgresql.JSONB(), nullable=False),
        sa.Column("default_values", postgresql.JSONB(), nullable=False, default=dict),
        sa.Column("cadquery_script", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("preview_url", sa.String(500), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, default=list),
        sa.Column("min_tier", sa.String(20), nullable=False, default="free"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("use_count", sa.Integer(), nullable=False, default=0),
        sa.Column("avg_rating", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_templates_category", "templates", ["category", "subcategory"])
    op.create_index("idx_templates_slug", "templates", ["slug"], unique=True)
    op.create_index("idx_templates_featured", "templates", ["is_featured", "category"], postgresql_where=sa.text("is_active = TRUE AND is_featured = TRUE"))
    op.create_index("idx_templates_tags", "templates", ["tags"], postgresql_using="gin")

    # ===========================================
    # DESIGNS TABLE
    # ===========================================
    op.create_table(
        "designs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="draft"),
        sa.Column("extra_data", postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column("is_public", sa.Boolean(), nullable=False, default=False),
        sa.Column("view_count", sa.Integer(), nullable=False, default=0),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_designs_project", "designs", ["project_id"])
    op.create_index("idx_designs_template", "designs", ["template_id"])
    op.create_index("idx_designs_status", "designs", ["status"])
    op.create_index("idx_designs_public", "designs", ["is_public", "created_at"], postgresql_where=sa.text("deleted_at IS NULL AND is_public = TRUE"))
    op.create_index("idx_designs_tags", "designs", ["tags"], postgresql_using="gin", postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("idx_designs_extra_data", "designs", ["extra_data"], postgresql_using="gin")
    op.create_index("idx_designs_search", "designs", ["search_vector"], postgresql_using="gin")

    # ===========================================
    # DESIGN VERSIONS TABLE
    # ===========================================
    op.create_table(
        "design_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("file_formats", postgresql.JSONB(), nullable=False, default=dict),
        sa.Column("parameters", postgresql.JSONB(), nullable=False, default=dict),
        sa.Column("geometry_info", postgresql.JSONB(), nullable=False, default=dict),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_design_versions_design", "design_versions", ["design_id"])
    op.create_index("idx_design_version_unique", "design_versions", ["design_id", "version_number"], unique=True)

    # ===========================================
    # DESIGN SHARES TABLE
    # ===========================================
    op.create_table(
        "design_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shared_with_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("shared_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission", sa.String(20), nullable=False, default="view"),
        sa.Column("share_token", sa.String(64), unique=True, nullable=True),
        sa.Column("is_link_share", sa.Boolean(), nullable=False, default=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_design_shares_design", "design_shares", ["design_id"])
    op.create_index("idx_design_shares_user", "design_shares", ["shared_with_user_id"])
    op.create_index("idx_design_shares_token", "design_shares", ["share_token"])

    # ===========================================
    # JOBS TABLE
    # ===========================================
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("priority", sa.Integer(), nullable=False, default=5),
        sa.Column("progress", sa.Integer(), nullable=False, default=0),
        sa.Column("progress_message", sa.String(255), nullable=True),
        sa.Column("input_params", postgresql.JSONB(), nullable=False, default=dict),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, default=0),
        sa.Column("max_retries", sa.Integer(), nullable=False, default=3),
        sa.Column("celery_task_id", sa.String(255), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("cpu_time_seconds", sa.Float(), nullable=True),
        sa.Column("memory_mb", sa.Float(), nullable=True),
    )
    op.create_index("idx_jobs_user", "jobs", ["user_id"])
    op.create_index("idx_jobs_design", "jobs", ["design_id"])
    op.create_index("idx_jobs_type", "jobs", ["job_type"])
    op.create_index("idx_jobs_status", "jobs", ["status"])
    op.create_index("idx_jobs_celery", "jobs", ["celery_task_id"])
    op.create_index("idx_jobs_pending", "jobs", ["status", "priority", "created_at"], postgresql_where=sa.text("status IN ('pending', 'queued')"))
    op.create_index("idx_jobs_user_recent", "jobs", ["user_id", "created_at"])

    # ===========================================
    # MODERATION LOGS TABLE
    # ===========================================
    op.create_table(
        "moderation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("moderation_type", sa.String(20), nullable=False, default="automated"),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False, default=dict),
        sa.Column("is_appealed", sa.Boolean(), nullable=False, default=False),
        sa.Column("appeal_reason", sa.Text(), nullable=True),
        sa.Column("appeal_decision", sa.String(20), nullable=True),
        sa.Column("appealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_moderation_design", "moderation_logs", ["design_id"])
    op.create_index("idx_moderation_user", "moderation_logs", ["user_id"])
    op.create_index("idx_moderation_decision", "moderation_logs", ["decision"])
    op.create_index("idx_moderation_pending", "moderation_logs", ["decision", "created_at"], postgresql_where=sa.text("decision = 'pending_review'"))
    op.create_index("idx_moderation_rejected", "moderation_logs", ["reason", "created_at"], postgresql_where=sa.text("decision = 'rejected'"))

    # ===========================================
    # API KEYS TABLE
    # ===========================================
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("key_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.String()), nullable=False, default=list),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.String(45), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, default=0),
        sa.Column("rate_limit", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_api_keys_user", "api_keys", ["user_id"])
    op.create_index("idx_api_keys_prefix", "api_keys", ["key_prefix"])
    op.create_index("idx_api_keys_active", "api_keys", ["user_id", "is_active"], postgresql_where=sa.text("is_active = TRUE"))

    # ===========================================
    # AUDIT LOGS TABLE
    # ===========================================
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_type", sa.String(20), nullable=False, default="user"),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=False, default=dict),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="success"),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_audit_user", "audit_logs", ["user_id"])
    op.create_index("idx_audit_action", "audit_logs", ["action"])
    op.create_index("idx_audit_resource_type", "audit_logs", ["resource_type"])
    op.create_index("idx_audit_resource", "audit_logs", ["resource_type", "resource_id", "created_at"])
    op.create_index("idx_audit_user_actions", "audit_logs", ["user_id", "action", "created_at"])
    op.create_index("idx_audit_created", "audit_logs", ["created_at"])
    op.create_index("idx_audit_context", "audit_logs", ["context"], postgresql_using="gin")
    op.create_index("idx_audit_failures", "audit_logs", ["status", "created_at"], postgresql_where=sa.text("status != 'success'"))


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("audit_logs")
    op.drop_table("api_keys")
    op.drop_table("moderation_logs")
    op.drop_table("jobs")
    op.drop_table("design_shares")
    op.drop_table("design_versions")
    op.drop_table("designs")
    op.drop_table("templates")
    op.drop_table("projects")
    op.drop_table("files")
    op.drop_table("subscriptions")
    op.drop_table("user_settings")
    op.drop_table("users")
