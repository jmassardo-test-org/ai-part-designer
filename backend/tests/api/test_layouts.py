"""
Tests for layouts API endpoints.

Tests spatial layout functionality for component placement.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4


# =============================================================================
# Layout Create Tests
# =============================================================================

class TestCreateLayout:
    """Tests for POST /api/v1/layouts."""

    async def test_create_layout_project_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent project."""
        fake_id = uuid4()
        response = await client.post(
            "/api/v1/layouts",
            headers=auth_headers,
            json={
                "project_id": str(fake_id),
                "name": "Test Layout",
                "enclosure_length": 100,
                "enclosure_width": 100,
                "enclosure_height": 50,
            }
        )
        
        assert response.status_code == 404

    async def test_create_layout_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.post(
            "/api/v1/layouts",
            json={
                "project_id": str(uuid4()),
                "name": "Test Layout",
            }
        )
        assert response.status_code == 401


# =============================================================================
# Layout List Tests
# =============================================================================

class TestListLayouts:
    """Tests for GET /api/v1/layouts."""

    async def test_list_layouts_project_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent project."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/layouts?project_id={fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_list_layouts_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/layouts")
        assert response.status_code == 401


# =============================================================================
# Get Layout Tests
# =============================================================================

class TestGetLayout:
    """Tests for GET /api/v1/layouts/{layout_id}."""

    async def test_get_layout_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent layout."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/layouts/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_get_layout_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/layouts/{fake_id}")
        assert response.status_code == 401


# =============================================================================
# Update Layout Tests
# =============================================================================

class TestUpdateLayout:
    """Tests for PATCH /api/v1/layouts/{layout_id}."""

    async def test_update_layout_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent layout."""
        fake_id = uuid4()
        response = await client.patch(
            f"/api/v1/layouts/{fake_id}",
            headers=auth_headers,
            json={"name": "Updated Layout"}
        )
        
        assert response.status_code == 404


# =============================================================================
# Delete Layout Tests
# =============================================================================

class TestDeleteLayout:
    """Tests for DELETE /api/v1/layouts/{layout_id}."""

    async def test_delete_layout_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent layout."""
        fake_id = uuid4()
        response = await client.delete(
            f"/api/v1/layouts/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


# =============================================================================
# Layout Component Tests
# =============================================================================

class TestLayoutComponents:
    """Tests for layout component management."""

    async def test_add_component_layout_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent layout."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/layouts/{fake_id}/components",
            headers=auth_headers,
            json={
                "component_id": str(uuid4()),
                "position_x": 10,
                "position_y": 10,
            }
        )
        
        assert response.status_code == 404

    async def test_auto_place_layout_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent layout."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/layouts/{fake_id}/auto-place",
            headers=auth_headers
        )
        
        assert response.status_code == 404
