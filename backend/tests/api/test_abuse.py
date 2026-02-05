"""
Tests for abuse reporting API endpoints.

Tests content abuse/flagging and moderation functionality.
"""

from httpx import AsyncClient

# =============================================================================
# Abuse Dashboard Tests
# =============================================================================


class TestAbuseDashboard:
    """Tests for abuse dashboard."""

    async def test_dashboard_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/admin/abuse/dashboard")
        assert response.status_code == 401

    async def test_dashboard_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Should return 403 for non-admin users."""
        response = await client.get("/api/v1/admin/abuse/dashboard", headers=auth_headers)
        assert response.status_code == 403

    async def test_dashboard_admin(self, client: AsyncClient, admin_headers: dict):
        """Should return dashboard stats for admin users."""
        response = await client.get("/api/v1/admin/abuse/dashboard", headers=admin_headers)
        assert response.status_code == 200


# =============================================================================
# Abuse Reports Tests
# =============================================================================


class TestAbuseReports:
    """Tests for abuse reports."""

    async def test_list_reports_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/admin/abuse/reports")
        assert response.status_code == 401

    async def test_list_reports_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Should return 403 for non-admin users."""
        response = await client.get("/api/v1/admin/abuse/reports", headers=auth_headers)
        assert response.status_code == 403

    async def test_list_reports_admin(self, client: AsyncClient, admin_headers: dict):
        """Should return reports list for admin."""
        response = await client.get("/api/v1/admin/abuse/reports", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# =============================================================================
# Ban Management Tests
# =============================================================================


class TestBanManagement:
    """Tests for user ban management."""

    async def test_list_bans_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/admin/abuse/bans")
        assert response.status_code == 401

    async def test_list_bans_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Should return 403 for non-admin users."""
        response = await client.get("/api/v1/admin/abuse/bans", headers=auth_headers)
        assert response.status_code == 403

    async def test_list_bans_admin(self, client: AsyncClient, admin_headers: dict):
        """Should return bans list for admin."""
        response = await client.get("/api/v1/admin/abuse/bans", headers=admin_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# =============================================================================
# Moderation Queue Tests
# =============================================================================


class TestModerationQueue:
    """Tests for moderation queue."""

    async def test_queue_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/admin/abuse/moderation-queue")
        assert response.status_code == 401

    async def test_queue_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Should return 403 for non-admin users."""
        response = await client.get("/api/v1/admin/abuse/moderation-queue", headers=auth_headers)
        assert response.status_code == 403

    async def test_queue_admin(self, client: AsyncClient, admin_headers: dict):
        """Should return moderation queue for admin."""
        response = await client.get("/api/v1/admin/abuse/moderation-queue", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # Response is paginated, so check for items key
        assert "items" in data or isinstance(data, list)
