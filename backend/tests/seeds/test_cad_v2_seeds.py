"""
Tests for CAD v2 seeding modules.

Tests for:
- Component v2 seeding
- Starter design seeding
"""

from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reference_component import ReferenceComponent
from app.models.design import Design
from app.models.project import Project
from app.models.user import User


# =============================================================================
# Component V2 Seeding Tests
# =============================================================================


class TestComponentV2Seeding:
    """Tests for CAD v2 component seeding."""

    async def test_seed_components_v2_creates_records(
        self, db_session: AsyncSession
    ):
        """Seeding creates component records in database."""
        from app.seeds.components_v2 import seed_components_v2
        from app.cad_v2.components import get_registry
        
        registry = get_registry()
        initial_registry_count = registry.count
        
        if initial_registry_count == 0:
            pytest.skip("No components in registry")
        
        created, updated = await seed_components_v2(db_session)
        
        # Should have created records
        assert created + updated == initial_registry_count

    async def test_seed_components_v2_is_idempotent(
        self, db_session: AsyncSession
    ):
        """Running seed twice doesn't duplicate records."""
        from app.seeds.components_v2 import seed_components_v2
        from app.cad_v2.components import get_registry
        
        registry = get_registry()
        if registry.count == 0:
            pytest.skip("No components in registry")
        
        # First run
        created1, updated1 = await seed_components_v2(db_session)
        
        # Second run
        created2, updated2 = await seed_components_v2(db_session)
        
        # Second run should only update, not create
        assert created2 == 0
        assert updated2 == created1 + updated1

    async def test_seed_components_v2_sets_library_source(
        self, db_session: AsyncSession
    ):
        """Seeded components have source_type='library'."""
        from app.seeds.components_v2 import seed_components_v2
        
        await seed_components_v2(db_session)
        
        result = await db_session.execute(
            select(ReferenceComponent).where(
                ReferenceComponent.source_type == "library"
            )
        )
        components = result.scalars().all()
        
        # All library components should have user_id=None
        for comp in components:
            assert comp.user_id is None

    async def test_seed_components_v2_includes_dimensions(
        self, db_session: AsyncSession
    ):
        """Seeded components have dimensions data."""
        from app.seeds.components_v2 import seed_components_v2
        
        await seed_components_v2(db_session)
        
        result = await db_session.execute(
            select(ReferenceComponent).limit(5)
        )
        components = result.scalars().all()
        
        for comp in components:
            if comp.dimensions is not None:
                assert "width" in comp.dimensions
                assert "depth" in comp.dimensions
                assert "height" in comp.dimensions

    async def test_component_to_dict_conversion(self):
        """component_to_dict correctly converts ComponentDefinition."""
        from app.seeds.components_v2 import component_to_dict
        from app.cad_v2.components import get_registry
        
        registry = get_registry()
        components = registry.list_all()
        
        if not components:
            pytest.skip("No components in registry")
        
        comp = components[0]
        result = component_to_dict(comp)
        
        assert result["name"] == comp.name
        assert result["category"] == comp.category.value
        assert result["source_type"] == "library"
        assert isinstance(result["dimensions"], dict)


# =============================================================================
# Starter Seeding Tests
# =============================================================================


class TestStarterSeeding:
    """Tests for starter design seeding."""

    async def test_seed_starters_creates_vendor_user(
        self, db_session: AsyncSession
    ):
        """Seeding creates the vendor user."""
        from app.seeds.starters import seed_starters, VENDOR_USER_ID
        
        await seed_starters(db_session)
        
        result = await db_session.execute(
            select(User).where(User.id == VENDOR_USER_ID)
        )
        vendor = result.scalar_one_or_none()
        
        assert vendor is not None
        assert vendor.role == "system"

    async def test_seed_starters_creates_project(
        self, db_session: AsyncSession
    ):
        """Seeding creates the starters project."""
        from app.seeds.starters import seed_starters, STARTERS_PROJECT_ID
        
        await seed_starters(db_session)
        
        result = await db_session.execute(
            select(Project).where(Project.id == STARTERS_PROJECT_ID)
        )
        project = result.scalar_one_or_none()
        
        assert project is not None
        assert project.name == "Starter Designs"

    async def test_seed_starters_creates_designs(
        self, db_session: AsyncSession
    ):
        """Seeding creates starter designs."""
        from app.seeds.starters import seed_starters, STARTER_DESIGNS
        
        created, updated = await seed_starters(db_session)
        
        assert created + updated == len(STARTER_DESIGNS)

    async def test_seed_starters_is_idempotent(
        self, db_session: AsyncSession
    ):
        """Running seed twice doesn't duplicate records."""
        from app.seeds.starters import seed_starters, STARTER_DESIGNS
        
        # First run
        created1, updated1 = await seed_starters(db_session)
        
        # Second run
        created2, updated2 = await seed_starters(db_session)
        
        # Second run should only update, not create
        assert created2 == 0
        assert updated2 == len(STARTER_DESIGNS)

    async def test_seeded_starters_are_marked_correctly(
        self, db_session: AsyncSession
    ):
        """Seeded starters have correct flags."""
        from app.seeds.starters import seed_starters
        
        await seed_starters(db_session)
        
        result = await db_session.execute(
            select(Design).where(Design.source_type == "starter")
        )
        starters = result.scalars().all()
        
        for starter in starters:
            assert starter.source_type == "starter"
            assert starter.is_public is True
            # is_starter stored in extra_data
            assert starter.extra_data.get("is_starter", False) is True

    async def test_seeded_starters_have_enclosure_spec(
        self, db_session: AsyncSession
    ):
        """Seeded starters have enclosure_spec in extra_data."""
        from app.seeds.starters import seed_starters
        
        await seed_starters(db_session)
        
        result = await db_session.execute(
            select(Design).where(Design.source_type == "starter")
        )
        starters = result.scalars().all()
        
        for starter in starters:
            enclosure_spec = starter.extra_data.get("enclosure_spec")
            assert enclosure_spec is not None
            assert "exterior" in enclosure_spec

    async def test_seeded_starters_have_categories_and_tags(
        self, db_session: AsyncSession
    ):
        """Seeded starters have categories and tags."""
        from app.seeds.starters import seed_starters
        
        await seed_starters(db_session)
        
        result = await db_session.execute(
            select(Design).where(Design.source_type == "starter")
        )
        starters = result.scalars().all()
        
        for starter in starters:
            assert starter.category is not None
            assert starter.tags is not None
            assert len(starter.tags) > 0

    async def test_starter_designs_data_structure(self):
        """STARTER_DESIGNS has correct structure."""
        from app.seeds.starters import STARTER_DESIGNS
        
        assert len(STARTER_DESIGNS) > 0
        
        for starter in STARTER_DESIGNS:
            assert "id" in starter
            assert "name" in starter
            assert "description" in starter
            assert "category" in starter
            assert "tags" in starter
            assert "is_starter" in starter
            assert "enclosure_spec" in starter
            assert isinstance(starter["id"], UUID)
            assert isinstance(starter["tags"], list)


# =============================================================================
# Integration Tests
# =============================================================================


class TestSeedingIntegration:
    """Integration tests for seeding modules."""

    async def test_full_seeding_workflow(
        self, db_session: AsyncSession
    ):
        """Test complete seeding workflow."""
        from app.seeds.components_v2 import seed_components_v2
        from app.seeds.starters import seed_starters
        
        # Seed components
        comp_created, comp_updated = await seed_components_v2(db_session)
        
        # Seed starters
        start_created, start_updated = await seed_starters(db_session)
        
        # Verify both worked
        assert comp_created >= 0
        assert start_created >= 0
        
        # Verify data is accessible
        components = await db_session.execute(
            select(ReferenceComponent).where(
                ReferenceComponent.source_type == "library"
            )
        )
        starters = await db_session.execute(
            select(Design).where(Design.source_type == "starter")
        )
        
        assert components.scalars().first() is not None or comp_created == 0
        assert starters.scalars().first() is not None
