"""
Tests for webhooks API endpoints.

Tests webhook configuration and delivery.
"""

from httpx import AsyncClient

# =============================================================================
# Stripe Webhook Tests
# =============================================================================


class TestStripeWebhooks:
    """Tests for Stripe webhook handling."""

    async def test_stripe_webhook_without_signature(self, client: AsyncClient):
        """Should reject webhook without signature."""
        response = await client.post(
            "/api/v1/webhooks/stripe",
            json={"type": "test"},
        )

        # Should reject without proper signature
        assert response.status_code in [400, 401, 403, 422]

    async def test_stripe_webhook_invalid_payload(self, client: AsyncClient):
        """Should reject invalid webhook payload."""
        response = await client.post(
            "/api/v1/webhooks/stripe",
            content="invalid-json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code in [400, 422]
