"""
Tests for usage/billing API endpoints.

Tests subscription tiers, credit balance, and usage tracking.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Subscription Tiers Tests
# =============================================================================

class TestSubscriptionTiers:
    """Tests for subscription tier endpoints."""

    async def test_list_tiers_success(
        self, client: AsyncClient, auth_headers: dict, subscription_tiers
    ):
        """Should return list of subscription tiers."""
        response = await client.get(
            "/api/v1/usage/tiers",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Should have at least the seeded tiers

    async def test_list_tiers_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/usage/tiers")
        assert response.status_code == 401

    async def test_get_tier_by_slug(
        self, client: AsyncClient, auth_headers: dict, subscription_tiers
    ):
        """Should return tier details by slug."""
        response = await client.get(
            "/api/v1/usage/tiers/free",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "free"

    async def test_get_tier_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent tier."""
        response = await client.get(
            "/api/v1/usage/tiers/nonexistent-tier-slug",
            headers=auth_headers
        )
        
        assert response.status_code == 404


# =============================================================================
# Credit Balance Tests
# =============================================================================

class TestCreditBalance:
    """Tests for credit balance endpoints."""

    async def test_get_balance_success(
        self, client: AsyncClient, auth_headers: dict, subscription_tiers
    ):
        """Should return user's credit balance."""
        response = await client.get(
            "/api/v1/usage/credits/balance",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data

    async def test_get_balance_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/usage/credits/balance")
        assert response.status_code == 401


# =============================================================================
# Transaction History Tests
# =============================================================================

class TestTransactionHistory:
    """Tests for credit transaction history."""

    async def test_get_transactions_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return user's transaction history."""
        response = await client.get(
            "/api/v1/usage/credits/transactions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# =============================================================================
# Usage Summary Tests
# =============================================================================

class TestUsageSummary:
    """Tests for usage summary endpoints."""

    async def test_get_usage_success(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return usage summary."""
        response = await client.get(
            "/api/v1/usage/credits/usage",
            headers=auth_headers
        )
        
        assert response.status_code == 200


# =============================================================================
# Quota Tests
# =============================================================================

class TestQuota:
    """Tests for quota endpoints."""

    async def test_get_quota_success(
        self, client: AsyncClient, auth_headers: dict, subscription_tiers
    ):
        """Should return quota usage."""
        response = await client.get(
            "/api/v1/usage/quota",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_get_quota_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/usage/quota")
        assert response.status_code == 401


# =============================================================================
# Dashboard Tests
# =============================================================================

class TestUsageDashboard:
    """Tests for usage dashboard endpoint."""

    async def test_get_dashboard_success(
        self, client: AsyncClient, auth_headers: dict, subscription_tiers
    ):
        """Should return usage dashboard data."""
        response = await client.get(
            "/api/v1/usage/dashboard",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    async def test_get_dashboard_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/usage/dashboard")
        assert response.status_code == 401
