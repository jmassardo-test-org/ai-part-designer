"""
Tests for assemblies API endpoints.

Tests assembly CRUD and component operations.
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
async def test_project_for_assembly(db_session: AsyncSession, test_user):
    """Create a test project for assembly tests."""
    project = Project(
        id=uuid4(),
        user_id=test_user.id,
        name="Assembly Test Project",
        description="Project for assembly tests",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    yield project

    # Cleanup
    try:
        await db_session.delete(project)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_assembly(db_session: AsyncSession, test_user, test_project_for_assembly):
    """Create a test assembly."""
    assembly = Assembly(
        id=uuid4(),
        user_id=test_user.id,
        project_id=test_project_for_assembly.id,
        name="Test Assembly",
        description="A test assembly",
        status="draft",
    )
    db_session.add(assembly)
    await db_session.commit()
    await db_session.refresh(assembly)

    yield assembly

    # Cleanup
    try:
        await db_session.delete(assembly)
        await db_session.commit()
    except Exception:
        pass


# =============================================================================
# List Assemblies Tests
# =============================================================================


class TestListAssemblies:
    """Tests for GET /api/v1/assemblies."""

    async def test_list_assemblies_success(
        self, client: AsyncClient, auth_headers: dict, test_assembly
    ):
        """Should return list of user's assemblies."""
        response = await client.get("/api/v1/assemblies", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "assemblies" in data or isinstance(data, list)

    async def test_list_assemblies_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/assemblies")
        assert response.status_code == 401

    async def test_list_assemblies_filter_by_project(
        self, client: AsyncClient, auth_headers: dict, test_assembly, test_project_for_assembly
    ):
        """Should filter assemblies by project."""
        response = await client.get(
            f"/api/v1/assemblies?project_id={test_project_for_assembly.id}", headers=auth_headers
        )

        assert response.status_code == 200


# =============================================================================
# Create Assembly Tests
# =============================================================================


class TestCreateAssembly:
    """Tests for POST /api/v1/assemblies."""

    async def test_create_assembly_success(
        self, client: AsyncClient, auth_headers: dict, test_project_for_assembly
    ):
        """Should create a new assembly."""
        response = await client.post(
            "/api/v1/assemblies",
            headers=auth_headers,
            json={
                "name": "New Assembly",
                "project_id": str(test_project_for_assembly.id),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Assembly"

        # Cleanup
        assembly_id = data["id"]
        await client.delete(f"/api/v1/assemblies/{assembly_id}", headers=auth_headers)

    async def test_create_assembly_missing_project(self, client: AsyncClient, auth_headers: dict):
        """Should reject assembly without project_id."""
        response = await client.post(
            "/api/v1/assemblies",
            headers=auth_headers,
            json={
                "name": "No Project Assembly",
            },
        )

        assert response.status_code == 422

    async def test_create_assembly_invalid_project(self, client: AsyncClient, auth_headers: dict):
        """Should reject assembly with non-existent project."""
        response = await client.post(
            "/api/v1/assemblies",
            headers=auth_headers,
            json={
                "name": "Bad Project Assembly",
                "project_id": "00000000-0000-0000-0000-000000000000",
            },
        )

        assert response.status_code in [400, 404, 422]


# =============================================================================
# Get Assembly Tests
# =============================================================================


class TestGetAssembly:
    """Tests for GET /api/v1/assemblies/{assembly_id}."""

    async def test_get_assembly_success(
        self, client: AsyncClient, auth_headers: dict, test_assembly
    ):
        """Should return assembly details."""
        response = await client.get(f"/api/v1/assemblies/{test_assembly.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_assembly.id)
        assert data["name"] == test_assembly.name

    async def test_get_assembly_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent assembly."""
        response = await client.get(
            "/api/v1/assemblies/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )

        assert response.status_code == 404


# =============================================================================
# Update Assembly Tests
# =============================================================================


class TestUpdateAssembly:
    """Tests for PUT /api/v1/assemblies/{assembly_id}."""

    async def test_update_assembly_success(
        self, client: AsyncClient, auth_headers: dict, test_assembly
    ):
        """Should update assembly."""
        response = await client.put(
            f"/api/v1/assemblies/{test_assembly.id}",
            headers=auth_headers,
            json={"name": "Updated Assembly Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Assembly Name"

    async def test_update_assembly_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent assembly."""
        response = await client.put(
            "/api/v1/assemblies/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
            json={"name": "Does Not Exist"},
        )

        assert response.status_code == 404


# =============================================================================
# Delete Assembly Tests
# =============================================================================


class TestDeleteAssembly:
    """Tests for DELETE /api/v1/assemblies/{assembly_id}."""

    async def test_delete_assembly_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user,
        test_project_for_assembly,
    ):
        """Should delete assembly."""
        # Create an assembly to delete
        assembly = Assembly(
            id=uuid4(),
            user_id=test_user.id,
            project_id=test_project_for_assembly.id,
            name="To Delete",
            status="draft",
        )
        db_session.add(assembly)
        await db_session.commit()

        response = await client.delete(f"/api/v1/assemblies/{assembly.id}", headers=auth_headers)

        assert response.status_code == 204

    async def test_delete_assembly_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent assembly."""
        response = await client.delete(
            "/api/v1/assemblies/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )

        assert response.status_code == 404
