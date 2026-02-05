"""
Tests for shares API endpoints.

Tests design sharing functionality.
"""

from uuid import uuid4

from httpx import AsyncClient

# =============================================================================
# List Shares Tests
# =============================================================================


class TestListShares:
    """Tests for GET /api/v1/shares/designs/{design_id}."""

    async def test_list_shares_for_nonexistent_design(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent design."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/shares/designs/{fake_id}", headers=auth_headers)

        # Should return 404 for non-existent design
        assert response.status_code == 404

    async def test_list_shares_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/shares/designs/{fake_id}")

        assert response.status_code == 401


# =============================================================================
# Shared With Me Tests
# =============================================================================


class TestSharedWithMe:
    """Tests for GET /api/v1/shares/shared-with-me."""

    async def test_shared_with_me_success(self, client: AsyncClient, auth_headers: dict):
        """Should return designs shared with current user."""
        response = await client.get("/api/v1/shares/shared-with-me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
