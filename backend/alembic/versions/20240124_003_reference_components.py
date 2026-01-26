"""Reference components tables

Revision ID: 003_reference_components
Revises: 002_assemblies
Create Date: 2024-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '003_reference_components'
down_revision: Union[str, None] = '002_assemblies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reference Components table
    op.create_table(
        'reference_components',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('subcategory', sa.String(100), nullable=True),
        sa.Column('manufacturer', sa.String(255), nullable=True),
        sa.Column('model_number', sa.String(255), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False, server_default='uploaded'),
        sa.Column('datasheet_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('cad_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('dimensions', postgresql.JSONB(), nullable=True,
                  comment='Overall dimensions: {length, width, height, unit}'),
        sa.Column('mounting_holes', postgresql.JSONB(), nullable=True,
                  comment='Array of mounting holes'),
        sa.Column('connectors', postgresql.JSONB(), nullable=True,
                  comment='Array of connectors'),
        sa.Column('clearance_zones', postgresql.JSONB(), nullable=True,
                  comment='Array of clearance zones'),
        sa.Column('thermal_properties', postgresql.JSONB(), nullable=True,
                  comment='Thermal specs'),
        sa.Column('electrical_properties', postgresql.JSONB(), nullable=True,
                  comment='Electrical specs'),
        sa.Column('extraction_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('extraction_error', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True,
                  comment='AI extraction confidence 0.0-1.0'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false',
                  comment='Admin-verified specifications'),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['datasheet_file_id'], ['files.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cad_file_id'], ['files.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reference_components_user_id', 'reference_components', ['user_id'])
    op.create_index('ix_reference_components_category', 'reference_components', ['category'])
    op.create_index('ix_reference_components_source_type', 'reference_components', ['source_type'])
    op.create_index('ix_ref_components_category_subcategory', 'reference_components',
                    ['category', 'subcategory'])
    op.create_index('ix_ref_components_manufacturer_model', 'reference_components',
                    ['manufacturer', 'model_number'])
    op.create_index('ix_ref_components_source_verified', 'reference_components',
                    ['source_type', 'is_verified'])
    
    # Component Library table
    op.create_table(
        'component_library',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('component_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('subcategory', sa.String(100), nullable=True),
        sa.Column('manufacturer', sa.String(255), nullable=True),
        sa.Column('model_number', sa.String(255), nullable=True),
        sa.Column('popularity_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),
        sa.Column('display_order', sa.Integer(), server_default='0'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['component_id'], ['reference_components.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('component_id')
    )
    op.create_index('ix_component_library_category', 'component_library', ['category'])
    op.create_index('ix_component_library_subcategory', 'component_library', ['subcategory'])
    op.create_index('ix_component_library_manufacturer', 'component_library', ['manufacturer'])
    op.create_index('ix_component_library_popularity', 'component_library',
                    ['popularity_score', 'usage_count'])
    op.create_index('ix_library_category_featured', 'component_library',
                    ['category', 'is_featured'])
    
    # Component Extraction Jobs table
    op.create_table(
        'component_extraction_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('component_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), server_default='0'),
        sa.Column('current_step', sa.String(255), nullable=True),
        sa.Column('extracted_data', postgresql.JSONB(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['component_id'], ['reference_components.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_extraction_jobs_component_id', 'component_extraction_jobs', ['component_id'])
    op.create_index('ix_extraction_jobs_status', 'component_extraction_jobs', ['status'])
    
    # User Components table
    op.create_table(
        'user_components',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_component_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('custom_name', sa.String(255), nullable=True),
        sa.Column('custom_notes', sa.Text(), nullable=True),
        sa.Column('custom_dimensions', postgresql.JSONB(), nullable=True),
        sa.Column('custom_mounting_holes', postgresql.JSONB(), nullable=True),
        sa.Column('custom_connectors', postgresql.JSONB(), nullable=True),
        sa.Column('custom_clearance_zones', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_component_id'], ['reference_components.id'],
                                ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_components_user_id', 'user_components', ['user_id'])
    op.create_index('ix_user_components_project_id', 'user_components', ['project_id'])


def downgrade() -> None:
    op.drop_table('user_components')
    op.drop_table('component_extraction_jobs')
    op.drop_table('component_library')
    op.drop_table('reference_components')
