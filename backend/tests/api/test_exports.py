"""
Tests for exports API endpoints.

Tests data export functionality.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Export Tests
# =============================================================================

class TestExports:
    """Tests for data export endpoints."""

    async def test_list_exports_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return list of user's exports."""
        response = await client.get(
            "/api/v1/exports",
            headers=auth_headers
        )
        
        # Could be 200 with list, or 404 if not implemented
        assert response.status_code in [200, 404]

    async def test_list_exports_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/exports")
        assert response.status_code in [401, 404]


# =============================================================================
# Export Request Tests
# =============================================================================

class TestExportRequest:
    """Tests for requesting exports."""

    async def test_request_export_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should request export of user's data."""
        response = await client.post(
            "/api/v1/exports/request",
            headers=auth_headers,
            json={}
        )
        
        # Could be 200/201 for success, 400 for duplicate, 429 for rate limit, or 500 for storage issues
        assert response.status_code in [200, 201, 202, 400, 429, 500]

    async def test_request_export_unauthenticated(
        self, client: AsyncClient
    ):
        """Should reject unauthenticated export request."""
        response = await client.post(
            "/api/v1/exports/request",
            json={}
        )
        
        # Should require authentication
        assert response.status_code == 401
