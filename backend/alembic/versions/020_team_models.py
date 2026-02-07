"""add team models

Revision ID: 020_team_models
Revises: 019_project_status
Create Date: 2024-02-01

Creates tables for Organization Teams feature:
- teams: Team groupings within organizations
- team_members: User membership in teams
- project_teams: Project-Team access assignments
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '020_team_models'
down_revision = '019b_notif_dismissed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('settings', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('organization_id', 'slug', name='uq_team_org_slug'),
    )
    op.create_index('idx_teams_org', 'teams', ['organization_id'])
    op.create_index('idx_teams_slug', 'teams', ['slug'])
    op.create_index('idx_teams_active', 'teams', ['is_active'])

    # Create team_members table
    op.create_table(
        'team_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('team_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('teams.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('role', sa.String(20), nullable=False, default='member'),
        sa.Column('added_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_member'),
    )
    op.create_index('idx_team_members_team', 'team_members', ['team_id'])
    op.create_index('idx_team_members_user', 'team_members', ['user_id'])

    # Create project_teams table
    op.create_table(
        'project_teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('team_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('teams.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('permission_level', sa.String(20), nullable=False, default='viewer'),
        sa.Column('assigned_by_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('project_id', 'team_id', name='uq_project_team'),
    )
    op.create_index('idx_project_teams_project', 'project_teams', ['project_id'])
    op.create_index('idx_project_teams_team', 'project_teams', ['team_id'])


def downgrade() -> None:
    op.drop_table('project_teams')
    op.drop_table('team_members')
    op.drop_table('teams')
