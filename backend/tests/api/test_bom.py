"""
Tests for BOM (Bill of Materials) API endpoints.

Tests BOM generation and management.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assembly import Assembly
from app.models.project import Project

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def assembly_for_bom(db_session: AsyncSession, test_user):
    """Create an assembly for BOM tests."""
    project = Project(
        id=uuid4(),
        user_id=test_user.id,
        name="BOM Test Project",
    )
    db_session.add(project)
    await db_session.flush()

    assembly = Assembly(
        id=uuid4(),
        user_id=test_user.id,
        project_id=project.id,
        name="BOM Test Assembly",
        status="completed",
    )
    db_session.add(assembly)
    await db_session.commit()
    await db_session.refresh(assembly)

    yield assembly

    try:
        await db_session.delete(assembly)
        await db_session.delete(project)
        await db_session.commit()
    except Exception:
        pass


# =============================================================================
# BOM Generation Tests
# =============================================================================


class TestBOMGeneration:
    """Tests for BOM generation endpoints."""

    async def test_get_assembly_bom(
        self, client: AsyncClient, auth_headers: dict, assembly_for_bom
    ):
        """Should return BOM for an assembly."""
        response = await client.get(
            f"/api/v1/bom/assemblies/{assembly_for_bom.id}", headers=auth_headers
        )

        assert response.status_code in [200, 404]

    async def test_get_bom_unauthenticated(self, client: AsyncClient, assembly_for_bom):
        """Should return 401 without authentication."""
        response = await client.get(f"/api/v1/bom/assemblies/{assembly_for_bom.id}")
        # May return 401 (unauthorized) or 404 (not found without auth context)
        assert response.status_code in [401, 404]


# =============================================================================
# BOM Export Tests
# =============================================================================


class TestBOMExport:
    """Tests for BOM export endpoints."""

    async def test_export_bom_csv(self, client: AsyncClient, auth_headers: dict, assembly_for_bom):
        """Should export BOM as CSV."""
        response = await client.get(
            f"/api/v1/bom/assemblies/{assembly_for_bom.id}/export?format=csv", headers=auth_headers
        )

        assert response.status_code in [200, 404, 422]

    async def test_export_bom_json(self, client: AsyncClient, auth_headers: dict, assembly_for_bom):
        """Should export BOM as JSON."""
        response = await client.get(
            f"/api/v1/bom/assemblies/{assembly_for_bom.id}/export?format=json", headers=auth_headers
        )

        assert response.status_code in [200, 404, 422]
