"""Add all remaining missing tables

Revision ID: 017_missing_tables
Revises: 016_usage_quotas
Create Date: 2026-01-26

This migration adds all tables that exist in models but were missing from the database:
- subscription_tiers
- organization_members
- organization_invites
- organization_credit_balances
- organization_audit_logs
- spatial_layouts
- component_placements
- design_annotations
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '017_missing_tables'
down_revision: Union[str, None] = '016_usage_quotas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. subscription_tiers
    # =========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS subscription_tiers (
            id UUID PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            slug VARCHAR(20) NOT NULL UNIQUE,
            description TEXT,
            monthly_credits INTEGER NOT NULL DEFAULT 10,
            credit_rollover BOOLEAN NOT NULL DEFAULT false,
            max_concurrent_jobs INTEGER NOT NULL DEFAULT 1,
            max_storage_gb INTEGER NOT NULL DEFAULT 1,
            max_projects INTEGER NOT NULL DEFAULT 5,
            max_designs_per_project INTEGER NOT NULL DEFAULT 10,
            max_file_size_mb INTEGER NOT NULL DEFAULT 25,
            features JSONB NOT NULL DEFAULT '{}',
            price_monthly_cents INTEGER NOT NULL DEFAULT 0,
            price_yearly_cents INTEGER NOT NULL DEFAULT 0,
            stripe_price_id_monthly VARCHAR(100),
            stripe_price_id_yearly VARCHAR(100),
            display_order INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscription_tiers_slug ON subscription_tiers(slug)")
    
    # =========================================================================
    # 2. organization_members
    # =========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS organization_members (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL DEFAULT 'member',
            invited_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            invited_at TIMESTAMP WITH TIME ZONE,
            joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            UNIQUE(organization_id, user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id)")
    
    # =========================================================================
    # 3. organization_invites
    # =========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS organization_invites (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            invited_by_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'member',
            token VARCHAR(64) NOT NULL UNIQUE,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            message TEXT,
            accepted_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_invites_org ON organization_invites(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_invites_email ON organization_invites(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_invites_token ON organization_invites(token)")
    
    # =========================================================================
    # 4. organization_credit_balances
    # =========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS organization_credit_balances (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
            balance INTEGER NOT NULL DEFAULT 0,
            lifetime_earned INTEGER NOT NULL DEFAULT 0,
            lifetime_spent INTEGER NOT NULL DEFAULT 0,
            last_refill_at TIMESTAMP WITH TIME ZONE,
            next_refill_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_credit_balances_org ON organization_credit_balances(organization_id)")
    
    # =========================================================================
    # 5. organization_audit_logs
    # =========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS organization_audit_logs (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(50),
            resource_id UUID,
            details JSONB NOT NULL DEFAULT '{}',
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_audit_logs_org ON organization_audit_logs(organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_audit_logs_user ON organization_audit_logs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_audit_logs_created ON organization_audit_logs(organization_id, created_at)")
    
    # =========================================================================
    # 6. spatial_layouts
    # =========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS spatial_layouts (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            enclosure_length FLOAT NOT NULL DEFAULT 100.0,
            enclosure_width FLOAT NOT NULL DEFAULT 100.0,
            enclosure_height FLOAT NOT NULL DEFAULT 50.0,
            auto_arrange BOOLEAN NOT NULL DEFAULT true,
            min_spacing_x FLOAT NOT NULL DEFAULT 5.0,
            min_spacing_y FLOAT NOT NULL DEFAULT 5.0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_spatial_layouts_project ON spatial_layouts(project_id)")
    
    # =========================================================================
    # 7. component_placements
    # =========================================================================
    op.execute("""
        CREATE TABLE IF NOT EXISTS component_placements (
            id UUID PRIMARY KEY,
            layout_id UUID NOT NULL REFERENCES spatial_layouts(id) ON DELETE CASCADE,
            component_id UUID NOT NULL REFERENCES reference_components(id) ON DELETE CASCADE,
            position_x FLOAT NOT NULL DEFAULT 0.0,
            position_y FLOAT NOT NULL DEFAULT 0.0,
            position_z FLOAT NOT NULL DEFAULT 0.0,
            rotation FLOAT NOT NULL DEFAULT 0.0,
            rotation_axis VARCHAR(10),
            custom_dimensions JSONB,
            notes TEXT,
            face_direction VARCHAR(20) NOT NULL DEFAULT 'front',
            is_locked BOOLEAN NOT NULL DEFAULT false,
            mounting_requirements JSONB,
            clearance_requirements JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_component_placements_layout ON component_placements(layout_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_component_placements_component ON component_placements(component_id)")
    
    # =========================================================================
    # 8. design_annotations (with enum types)
    # =========================================================================
    # Create enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE annotationtype AS ENUM ('note', 'question', 'issue', 'approval', 'suggestion', 'dimension');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE annotationstatus AS ENUM ('open', 'resolved', 'wont_fix', 'deferred');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS design_annotations (
            id UUID PRIMARY KEY,
            design_id UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            parent_id UUID REFERENCES design_annotations(id) ON DELETE CASCADE,
            position JSONB NOT NULL,
            normal JSONB,
            camera_position JSONB,
            camera_target JSONB,
            content TEXT NOT NULL,
            annotation_type annotationtype NOT NULL DEFAULT 'note',
            status annotationstatus NOT NULL DEFAULT 'open',
            resolved_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            resolved_at TIMESTAMP WITH TIME ZONE,
            version_number INTEGER,
            reply_count INTEGER NOT NULL DEFAULT 0,
            mentioned_users UUID[],
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_design_annotations_design ON design_annotations(design_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_design_annotations_user ON design_annotations(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_design_annotations_parent ON design_annotations(parent_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_design_annotations_type ON design_annotations(annotation_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_design_annotations_status ON design_annotations(status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS design_annotations")
    op.execute("DROP TABLE IF EXISTS component_placements")
    op.execute("DROP TABLE IF EXISTS spatial_layouts")
    op.execute("DROP TABLE IF EXISTS organization_audit_logs")
    op.execute("DROP TABLE IF EXISTS organization_credit_balances")
    op.execute("DROP TABLE IF EXISTS organization_invites")
    op.execute("DROP TABLE IF EXISTS organization_members")
    op.execute("DROP TABLE IF EXISTS subscription_tiers")
    op.execute("DROP TYPE IF EXISTS annotationstatus")
    op.execute("DROP TYPE IF EXISTS annotationtype")
