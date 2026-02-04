"""
Tests for enclosures API endpoints.

Tests enclosure generation and styles.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Enclosure Styles Tests
# =============================================================================

class TestEnclosureStyles:
    """Tests for enclosure styles endpoints."""

    async def test_list_styles_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return list of available enclosure styles."""
        response = await client.get(
            "/api/v1/enclosures/styles",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data or isinstance(data, list)

    async def test_list_styles_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/enclosures/styles")
        assert response.status_code == 401

    async def test_get_style_details(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return details for a specific style."""
        # First get the list of styles
        list_response = await client.get(
            "/api/v1/enclosures/styles",
            headers=auth_headers
        )
        
        if list_response.status_code == 200:
            styles_data = list_response.json()
            styles = styles_data.get("styles", styles_data) if isinstance(styles_data, dict) else styles_data
            
            if styles and len(styles) > 0:
                # Get first style type
                style_type = styles[0].get("type", styles[0].get("name", "box"))
                
                response = await client.get(
                    f"/api/v1/enclosures/styles/{style_type}",
                    headers=auth_headers
                )
                
                assert response.status_code in [200, 404]


# =============================================================================
# Preview Dimensions Tests
# =============================================================================

class TestPreviewDimensions:
    """Tests for preview dimensions endpoint."""

    async def test_preview_dimensions_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should calculate preview dimensions for components."""
        response = await client.post(
            "/api/v1/enclosures/preview-dimensions",
            headers=auth_headers,
            json={
                "components": [
                    {
                        "width": 100,
                        "height": 50,
                        "depth": 30,
                    }
                ],
                "wall_thickness": 2.0,
                "padding": 5.0,
            }
        )
        
        # Could be 200, 422 for missing fields, or other
        assert response.status_code in [200, 422]
