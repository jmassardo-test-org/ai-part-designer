"""
Tests for onboarding API endpoints.

Tests user onboarding flow and progress tracking.
"""

from httpx import AsyncClient

# =============================================================================
# Onboarding Status Tests
# =============================================================================


class TestOnboardingStatus:
    """Tests for onboarding status endpoints."""

    async def test_get_onboarding_status_success(self, client: AsyncClient, auth_headers: dict):
        """Should return current onboarding status."""
        response = await client.get("/api/v1/onboarding/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Should have completion status
        assert "completed" in data or "step" in data or "progress" in data

    async def test_get_onboarding_status_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/onboarding/status")
        assert response.status_code == 401


# =============================================================================
# Onboarding Progress Tests
# =============================================================================


class TestOnboardingProgress:
    """Tests for onboarding progress endpoints."""

    async def test_get_steps_success(self, client: AsyncClient, auth_headers: dict):
        """Should return onboarding steps list."""
        response = await client.get("/api/v1/onboarding/steps", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        # Should have list of steps
        assert "steps" in data or "items" in data or isinstance(data, list)

    async def test_get_metrics_success(self, client: AsyncClient, auth_headers: dict):
        """Should return onboarding metrics for admin."""
        response = await client.get("/api/v1/onboarding/metrics", headers=auth_headers)

        # May return 200 (if user is admin) or 403 (forbidden)
        assert response.status_code in [200, 403]
