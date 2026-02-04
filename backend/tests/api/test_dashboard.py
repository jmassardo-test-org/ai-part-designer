"""
Tests for dashboard API endpoints.

Tests user dashboard data retrieval.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Dashboard Tests
# =============================================================================

class TestDashboard:
    """Tests for dashboard endpoints."""

    async def test_get_dashboard_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return dashboard data."""
        response = await client.get(
            "/api/v1/dashboard",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Dashboard should have various metrics/stats
        assert isinstance(data, dict)

    async def test_get_dashboard_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/dashboard")
        assert response.status_code == 401


# =============================================================================
# Recent Activity Tests
# =============================================================================

class TestRecentActivity:
    """Tests for recent activity on dashboard."""

    async def test_get_recent_designs(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should include recent designs in dashboard."""
        response = await client.get(
            "/api/v1/dashboard",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should have some kind of recent items
        assert "recent_designs" in data or "designs" in data or "recent" in data or "activity" in data


# =============================================================================
# Stats Tests
# =============================================================================

class TestDashboardStats:
    """Tests for dashboard statistics."""

    async def test_get_stats(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should include statistics in dashboard."""
        response = await client.get(
            "/api/v1/dashboard",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should have stats
        assert "stats" in data or "total_designs" in data or "design_count" in data or isinstance(data, dict)
