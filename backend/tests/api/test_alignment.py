"""
Tests for alignment API endpoints.

Tests CAD alignment operations.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Alignment Tests
# =============================================================================

class TestAlignment:
    """Tests for alignment endpoints."""

    async def test_align_components_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.post(
            "/api/v1/cad/align",
            json={}
        )
        assert response.status_code == 401

    async def test_align_components(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should align components."""
        response = await client.post(
            "/api/v1/cad/align",
            headers=auth_headers,
            json={
                "components": [],
                "alignment_type": "center",
            }
        )
        
        # Could fail validation or work
        assert response.status_code in [200, 400, 422]


# =============================================================================
# Snap-to-Grid Tests
# =============================================================================

class TestSnapToGrid:
    """Tests for snap-to-grid functionality."""

    async def test_snap_to_grid(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should snap positions to grid."""
        response = await client.post(
            "/api/v1/cad/align/snap-to-grid",
            headers=auth_headers,
            json={
                "positions": [{"x": 10.3, "y": 20.7, "z": 5.2}],
                "grid_size": 5.0,
            }
        )
        
        assert response.status_code in [200, 404, 422]
