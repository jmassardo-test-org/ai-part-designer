"""Add assembly, BOM, and vendor tables

Revision ID: 002_assemblies
Revises: 001_initial_schema
Create Date: 2024-01-20

This migration adds tables for assemblies, assembly components,
component relationships, vendors, and bill of materials items.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_assemblies"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===========================================
    # VENDORS TABLE
    # ===========================================
    op.create_table(
        "vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("api_type", sa.String(50), nullable=True),
        sa.Column("api_base_url", sa.String(500), nullable=True),
        sa.Column("api_credentials", postgresql.JSONB(), nullable=True),
        sa.Column("categories", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ===========================================
    # ASSEMBLIES TABLE
    # ===========================================
    op.create_table(
        "assemblies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("root_design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="draft"),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_assemblies_project", "assemblies", ["project_id", "created_at"])
    op.create_index("idx_assemblies_user", "assemblies", ["user_id", "updated_at"])

    # ===========================================
    # ASSEMBLY COMPONENTS TABLE
    # ===========================================
    op.create_table(
        "assembly_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assembly_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assemblies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("design_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("designs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, default=1),
        sa.Column("position", postgresql.JSONB(), nullable=False, server_default='{"x": 0, "y": 0, "z": 0}'),
        sa.Column("rotation", postgresql.JSONB(), nullable=False, server_default='{"rx": 0, "ry": 0, "rz": 0}'),
        sa.Column("scale", postgresql.JSONB(), nullable=False, server_default='{"sx": 1, "sy": 1, "sz": 1}'),
        sa.Column("is_cots", sa.Boolean(), nullable=False, default=False),
        sa.Column("part_number", sa.String(100), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_components_assembly", "assembly_components", ["assembly_id"])
    op.create_index("idx_components_design", "assembly_components", ["design_id"])

    # ===========================================
    # COMPONENT RELATIONSHIPS TABLE
    # ===========================================
    op.create_table(
        "component_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assembly_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assemblies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_component_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assembly_components.id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_component_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assembly_components.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("constraint_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("assembly_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_relationships_assembly", "component_relationships", ["assembly_id"])
    op.create_index("idx_relationships_parent", "component_relationships", ["parent_component_id"])
    op.create_index("idx_relationships_child", "component_relationships", ["child_component_id"])

    # ===========================================
    # BOM ITEMS TABLE
    # ===========================================
    op.create_table(
        "bom_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assembly_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assemblies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assembly_components.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("part_number", sa.String(100), nullable=True),
        sa.Column("vendor_part_number", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, default="custom"),
        sa.Column("quantity", sa.Integer(), nullable=False, default=1),
        sa.Column("unit_cost", sa.Numeric(10, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, default="USD"),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("minimum_order_quantity", sa.Integer(), nullable=False, default=1),
        sa.Column("in_stock", sa.Boolean(), nullable=True),
        sa.Column("last_price_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_bom_assembly", "bom_items", ["assembly_id"])
    op.create_index("idx_bom_category", "bom_items", ["category"])
    op.create_index("idx_bom_vendor", "bom_items", ["vendor_id"])

    # ===========================================
    # SEED DEFAULT VENDORS
    # ===========================================
    op.execute("""
        INSERT INTO vendors (id, name, display_name, website, api_type, categories, is_active, created_at, updated_at)
        VALUES 
            (gen_random_uuid(), 'mcmaster', 'McMaster-Carr', 'https://www.mcmaster.com', 'mcmaster', '["fasteners", "bearings", "linear_motion", "hardware"]', true, now(), now()),
            (gen_random_uuid(), 'misumi', 'MISUMI', 'https://us.misumi-ec.com', 'misumi', '["extrusion", "linear_motion", "fasteners", "automation"]', true, now(), now()),
            (gen_random_uuid(), 'digikey', 'DigiKey', 'https://www.digikey.com', 'digikey', '["electronics", "connectors", "sensors"]', true, now(), now()),
            (gen_random_uuid(), 'amazon', 'Amazon', 'https://www.amazon.com', null, '["general", "electronics", "hardware"]', true, now(), now()),
            (gen_random_uuid(), 'custom', 'Custom/In-House', null, null, '["custom", "printed", "machined"]', true, now(), now())
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table("bom_items")
    op.drop_table("component_relationships")
    op.drop_table("assembly_components")
    op.drop_table("assemblies")
    op.drop_table("vendors")
