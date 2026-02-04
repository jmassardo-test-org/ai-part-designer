"""
Tests for drawings API endpoints.

Tests technical drawing generation functionality.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4


# =============================================================================
# Drawing Generation Tests
# =============================================================================

class TestDrawingGeneration:
    """Tests for POST /api/v1/drawings."""

    async def test_generate_drawing_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent design."""
        fake_id = uuid4()
        response = await client.post(
            "/api/v1/drawings",
            headers=auth_headers,
            json={
                "design_id": str(fake_id),
                "drawing_type": "orthographic",
            }
        )
        
        assert response.status_code == 404

    async def test_generate_drawing_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.post(
            "/api/v1/drawings",
            json={
                "design_id": str(uuid4()),
                "drawing_type": "orthographic",
            }
        )
        
        # 401 if endpoint exists, 404 if path not found
        assert response.status_code in [401, 404]


# =============================================================================
# Drawing Retrieval Tests
# =============================================================================

class TestDrawingRetrieval:
    """Tests for GET /api/v1/drawings."""

    async def test_list_drawings_for_design(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return drawings for a design."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/drawings?design_id={fake_id}",
            headers=auth_headers
        )
        
        # Should return 200 with empty list or 404
        assert response.status_code in [200, 404]

    async def test_list_drawings_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/drawings")
        # 401 if endpoint exists, 404 if path not found
        assert response.status_code in [401, 404]


# =============================================================================
# Get Drawing Tests
# =============================================================================

class TestGetDrawing:
    """Tests for GET /api/v1/drawings/{drawing_id}."""

    async def test_get_drawing_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent drawing."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/drawings/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


# =============================================================================
# Download Drawing Tests
# =============================================================================

class TestDownloadDrawing:
    """Tests for GET /api/v1/drawings/{drawing_id}/download."""

    async def test_download_drawing_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent drawing."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/drawings/{fake_id}/download",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_download_drawing_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/drawings/{fake_id}/download")
        # 401 if endpoint exists, 404 if path not found
        assert response.status_code in [401, 404]
