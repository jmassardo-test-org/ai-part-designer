"""
Tests for CAD v2 admin API endpoints.

Tests administrative functionality for:
- CAD v2 component registry management
- Starter design management
- Marketplace administration
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    Counter,
    DesignFactory,
    ProjectFactory,
    UserFactory,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_counters():
    """Reset factory counters before each test."""
    Counter.reset()


@pytest.fixture
async def starter_design(db_session: AsyncSession):
    """Create a starter design for testing."""
    user = await UserFactory.create(
        db_session,
        email="vendor@test.com",
        role="system",
    )
    project = await ProjectFactory.create(
        db_session,
        user=user,
        name="Starters Project",
    )
    return await DesignFactory.create(
        db_session,
        project=project,
        name="Test Starter Design",
        description="A test starter design",
        source_type="starter",
        is_public=True,
        category="raspberry-pi",
        tags=["test", "raspberry-pi"],
        extra_data={
            "is_starter": True,
            "enclosure_spec": {
                "exterior": {
                    "width": {"value": 100},
                    "depth": {"value": 80},
                    "height": {"value": 40},
                },
                "walls": {"thickness": {"value": 2.5}},
            },
        },
    )


# =============================================================================
# CAD v2 Component Registry Tests
# =============================================================================


class TestCADv2ComponentAdmin:
    """Tests for CAD v2 component admin endpoints."""

    async def test_list_cad_v2_components(self, client: AsyncClient, admin_headers: dict):
        """Admin can list CAD v2 components from registry."""
        response = await client.get("/api/v1/admin/cad-v2/components", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "categories" in data
        # Should have some components from the registry
        assert data["total"] >= 0
        assert isinstance(data["categories"], dict)

    async def test_list_cad_v2_components_with_category_filter(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Admin can filter CAD v2 components by category."""
        response = await client.get(
            "/api/v1/admin/cad-v2/components?category=board", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        # All items should be in 'board' category
        for item in data["items"]:
            assert item["category"] == "board"

    async def test_list_cad_v2_components_with_search(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Admin can search CAD v2 components."""
        response = await client.get(
            "/api/v1/admin/cad-v2/components?search=raspberry", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Results should match search query
        for item in data["items"]:
            name_lower = item["name"].lower()
            id_lower = item["id"].lower()
            assert "raspberry" in name_lower or "raspberry" in id_lower

    async def test_get_cad_v2_component_details(self, client: AsyncClient, admin_headers: dict):
        """Admin can get detailed component info."""
        # First get list to find a component ID
        list_response = await client.get("/api/v1/admin/cad-v2/components", headers=admin_headers)

        if list_response.json()["total"] == 0:
            pytest.skip("No components in registry")

        component_id = list_response.json()["items"][0]["id"]

        response = await client.get(
            f"/api/v1/admin/cad-v2/components/{component_id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "registry" in data
        assert "database" in data
        assert data["registry"]["id"] == component_id

    async def test_get_cad_v2_component_not_found(self, client: AsyncClient, admin_headers: dict):
        """Getting non-existent component returns 404."""
        response = await client.get(
            "/api/v1/admin/cad-v2/components/non-existent-component", headers=admin_headers
        )

        assert response.status_code == 404
        assert "not found in registry" in response.json()["detail"]

    async def test_sync_cad_v2_registry(self, client: AsyncClient, admin_headers: dict):
        """Admin can sync CAD v2 registry to database."""
        response = await client.post("/api/v1/admin/cad-v2/sync", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "created" in data
        assert "updated" in data
        assert "total_in_registry" in data
        assert "message" in data

    async def test_verify_cad_v2_component_requires_sync(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Verifying a component not in database returns 404."""
        response = await client.post(
            "/api/v1/admin/cad-v2/components/non-synced-component/verify", headers=admin_headers
        )

        assert response.status_code == 404
        assert "Sync first" in response.json()["detail"]

    async def test_feature_cad_v2_component_requires_sync(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Featuring a component not in database returns 404."""
        response = await client.post(
            "/api/v1/admin/cad-v2/components/non-synced-component/feature", headers=admin_headers
        )

        assert response.status_code == 404
        assert "Sync first" in response.json()["detail"]


class TestCADv2ComponentAdminWithSync:
    """Tests for CAD v2 component admin with synced data."""

    @pytest.fixture(autouse=True)
    async def sync_registry(self, client: AsyncClient, admin_headers: dict):
        """Sync the registry before each test in this class."""
        await client.post("/api/v1/admin/cad-v2/sync", headers=admin_headers)

    async def test_verify_cad_v2_component_after_sync(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Admin can verify a component after sync."""
        # Get a component ID
        list_response = await client.get("/api/v1/admin/cad-v2/components", headers=admin_headers)

        if list_response.json()["total"] == 0:
            pytest.skip("No components in registry")

        component_id = list_response.json()["items"][0]["id"]

        response = await client.post(
            f"/api/v1/admin/cad-v2/components/{component_id}/verify", headers=admin_headers
        )

        assert response.status_code == 200
        assert "verified" in response.json()["message"]

    async def test_feature_cad_v2_component_after_sync(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Admin can feature a component after sync."""
        # Get a component ID
        list_response = await client.get("/api/v1/admin/cad-v2/components", headers=admin_headers)

        if list_response.json()["total"] == 0:
            pytest.skip("No components in registry")

        component_id = list_response.json()["items"][0]["id"]

        response = await client.post(
            f"/api/v1/admin/cad-v2/components/{component_id}/feature", headers=admin_headers
        )

        assert response.status_code == 200
        assert "featured" in response.json()["message"]


# =============================================================================
# Starter Design Admin Tests
# =============================================================================


class TestStarterAdmin:
    """Tests for starter design admin endpoints."""

    async def test_list_starters_empty(self, client: AsyncClient, admin_headers: dict):
        """Admin can list starters (empty list)."""
        response = await client.get("/api/v1/admin/starters", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "categories" in data

    async def test_list_starters_with_data(
        self, client: AsyncClient, admin_headers: dict, starter_design
    ):
        """Admin can list starters with data."""
        response = await client.get("/api/v1/admin/starters", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(item["id"] == str(starter_design.id) for item in data["items"])

    async def test_list_starters_with_category_filter(
        self, client: AsyncClient, admin_headers: dict, starter_design
    ):
        """Admin can filter starters by category."""
        response = await client.get(
            "/api/v1/admin/starters?category=raspberry-pi", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["category"] == "raspberry-pi"

    async def test_list_starters_with_search(
        self, client: AsyncClient, admin_headers: dict, starter_design
    ):
        """Admin can search starters."""
        response = await client.get("/api/v1/admin/starters?search=Test", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_list_starters_pagination(
        self, client: AsyncClient, admin_headers: dict, starter_design
    ):
        """Admin can paginate starters."""
        response = await client.get(
            "/api/v1/admin/starters?page=1&page_size=5", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    async def test_get_starter_details(
        self, client: AsyncClient, admin_headers: dict, starter_design
    ):
        """Admin can get starter details."""
        response = await client.get(
            f"/api/v1/admin/starters/{starter_design.id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(starter_design.id)
        assert data["name"] == starter_design.name
        assert data["is_starter"] is True

    async def test_get_starter_not_found(self, client: AsyncClient, admin_headers: dict):
        """Getting non-existent starter returns 404."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/admin/starters/{fake_id}", headers=admin_headers)

        assert response.status_code == 404

    async def test_update_starter(self, client: AsyncClient, admin_headers: dict, starter_design):
        """Admin can update a starter."""
        response = await client.patch(
            f"/api/v1/admin/starters/{starter_design.id}",
            headers=admin_headers,
            json={
                "name": "Updated Starter Name",
                "description": "Updated description",
                "tags": ["updated", "test"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Starter Name"
        assert data["description"] == "Updated description"
        assert "updated" in data["tags"]

    async def test_update_starter_category(
        self, client: AsyncClient, admin_headers: dict, starter_design
    ):
        """Admin can change starter category."""
        response = await client.patch(
            f"/api/v1/admin/starters/{starter_design.id}",
            headers=admin_headers,
            json={"category": "arduino"},
        )

        assert response.status_code == 200
        assert response.json()["category"] == "arduino"

    async def test_feature_starter(self, client: AsyncClient, admin_headers: dict, starter_design):
        """Admin can feature a starter."""
        response = await client.post(
            f"/api/v1/admin/starters/{starter_design.id}/feature", headers=admin_headers
        )

        assert response.status_code == 200
        assert "featured" in response.json()["message"]

    async def test_unfeature_starter(
        self, client: AsyncClient, admin_headers: dict, starter_design
    ):
        """Admin can unfeature a starter."""
        # First feature it
        await client.post(
            f"/api/v1/admin/starters/{starter_design.id}/feature", headers=admin_headers
        )

        # Then unfeature
        response = await client.post(
            f"/api/v1/admin/starters/{starter_design.id}/unfeature", headers=admin_headers
        )

        assert response.status_code == 200
        assert "unfeatured" in response.json()["message"]

    async def test_delete_starter(self, client: AsyncClient, admin_headers: dict, starter_design):
        """Admin can soft-delete a starter."""
        response = await client.delete(
            f"/api/v1/admin/starters/{starter_design.id}", headers=admin_headers
        )

        assert response.status_code == 204

        # Verify it's no longer visible
        get_response = await client.get(
            f"/api/v1/admin/starters/{starter_design.id}", headers=admin_headers
        )
        assert get_response.status_code == 404

    async def test_reseed_starters(self, client: AsyncClient, admin_headers: dict):
        """Admin can reseed starters."""
        response = await client.post("/api/v1/admin/starters/reseed", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "created" in data
        assert "updated" in data
        assert "message" in data


# =============================================================================
# Marketplace Admin Tests
# =============================================================================


class TestMarketplaceAdmin:
    """Tests for marketplace admin endpoints."""

    async def test_get_marketplace_stats(self, client: AsyncClient, admin_headers: dict):
        """Admin can get marketplace statistics."""
        response = await client.get("/api/v1/admin/marketplace/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_starters" in data
        assert "total_public_designs" in data
        assert "total_remixes_today" in data
        assert "total_remixes_week" in data
        assert "starters_by_category" in data

    async def test_get_marketplace_stats_with_starters(
        self, client: AsyncClient, admin_headers: dict, starter_design
    ):
        """Marketplace stats include starter counts."""
        response = await client.get("/api/v1/admin/marketplace/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_starters"] >= 1
        assert "raspberry-pi" in data["starters_by_category"]

    async def test_get_featured_items(self, client: AsyncClient, admin_headers: dict):
        """Admin can get featured marketplace items."""
        response = await client.get("/api/v1/admin/marketplace/featured", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "featured_starters" in data
        assert "total" in data

    async def test_reorder_featured(self, client: AsyncClient, admin_headers: dict, starter_design):
        """Admin can reorder featured items."""
        response = await client.post(
            "/api/v1/admin/marketplace/reorder-featured",
            headers=admin_headers,
            json=[str(starter_design.id)],
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "order" in data


# =============================================================================
# Access Control Tests
# =============================================================================


class TestCADv2AdminAccess:
    """Tests for CAD v2 admin access control."""

    async def test_cad_v2_components_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot access CAD v2 admin."""
        response = await client.get("/api/v1/admin/cad-v2/components", headers=auth_headers)
        assert response.status_code == 403

    async def test_starters_forbidden_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Non-admin users cannot access starters admin."""
        response = await client.get("/api/v1/admin/starters", headers=auth_headers)
        assert response.status_code == 403

    async def test_marketplace_stats_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot access marketplace stats."""
        response = await client.get("/api/v1/admin/marketplace/stats", headers=auth_headers)
        assert response.status_code == 403

    async def test_sync_registry_forbidden_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Non-admin users cannot sync the registry."""
        response = await client.post("/api/v1/admin/cad-v2/sync", headers=auth_headers)
        assert response.status_code == 403

    async def test_reseed_starters_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot reseed starters."""
        response = await client.post("/api/v1/admin/starters/reseed", headers=auth_headers)
        assert response.status_code == 403

    async def test_cad_v2_components_unauthenticated(self, client: AsyncClient):
        """Unauthenticated requests are rejected."""
        response = await client.get("/api/v1/admin/cad-v2/components")
        assert response.status_code == 401

    async def test_starters_unauthenticated(self, client: AsyncClient):
        """Unauthenticated requests are rejected."""
        response = await client.get("/api/v1/admin/starters")
        assert response.status_code == 401
