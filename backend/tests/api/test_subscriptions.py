"""
Subscriptions API Tests.

Tests for subscription management, checkout, billing portal,
and usage endpoints.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient


class TestGetPlans:
    """Tests for GET /api/v1/subscriptions/plans"""

    async def test_get_plans_success(self, client: AsyncClient, db_session):
        """Test getting subscription plans."""
        # Create mock plans in database
        from app.models.subscription import SubscriptionTier

        plan = SubscriptionTier(
            slug="free",
            name="Free",
            description="Get started",
            monthly_credits=10,
            max_concurrent_jobs=1,
            max_storage_gb=1,
            max_projects=3,
            max_designs_per_project=10,
            max_file_size_mb=10,
            features={"ai_generation": True},
            price_monthly_cents=0,
            price_yearly_cents=0,
        )
        db_session.add(plan)
        await db_session.commit()

        response = await client.get("/api/v1/subscriptions/plans")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Check plan structure
        plan_data = data[0]
        assert "slug" in plan_data
        assert "name" in plan_data
        assert "price_monthly" in plan_data
        assert "features" in plan_data

    async def test_get_plans_public_endpoint(self, client: AsyncClient):
        """Test that plans endpoint is public (no auth required)."""
        response = await client.get("/api/v1/subscriptions/plans")

        # Should not return 401/403
        assert response.status_code in [200, 404]  # 404 if no plans seeded


class TestGetCurrentSubscription:
    """Tests for GET /api/v1/subscriptions/current"""

    async def test_get_current_subscription_unauthorized(self, client: AsyncClient):
        """Test getting subscription without auth."""
        response = await client.get("/api/v1/subscriptions/current")
        assert response.status_code == 401

    async def test_get_current_subscription_success(self, auth_client: AsyncClient, test_user):
        """Test getting current subscription for authenticated user."""
        response = await auth_client.get("/api/v1/subscriptions/current")

        assert response.status_code == 200
        data = response.json()
        assert "tier" in data
        assert "status" in data
        assert "is_active" in data
        assert "is_premium" in data

    async def test_get_current_subscription_free_tier(self, auth_client: AsyncClient, test_user):
        """Test that new user shows free tier."""
        response = await auth_client.get("/api/v1/subscriptions/current")

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "free"
        assert not data["is_premium"]


class TestCheckout:
    """Tests for POST /api/v1/subscriptions/checkout"""

    async def test_checkout_unauthorized(self, client: AsyncClient):
        """Test checkout without auth."""
        response = await client.post(
            "/api/v1/subscriptions/checkout",
            json={"plan_slug": "pro", "billing_interval": "monthly"},
        )
        assert response.status_code == 401

    @patch("app.services.payment.PaymentService.create_checkout_session")
    async def test_checkout_success(
        self,
        mock_checkout: AsyncMock,
        auth_client: AsyncClient,
        test_user,
    ):
        """Test successful checkout session creation."""
        mock_checkout.return_value = {
            "checkout_url": "https://checkout.stripe.com/cs_test_123",
            "session_id": "cs_test_123",
        }

        response = await auth_client.post(
            "/api/v1/subscriptions/checkout",
            json={"plan_slug": "pro", "billing_interval": "monthly"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "checkout_url" in data
        assert "session_id" in data
        assert data["checkout_url"].startswith("https://checkout.stripe.com")

    @patch("app.services.payment.PaymentService.create_checkout_session")
    async def test_checkout_yearly_billing(
        self,
        mock_checkout: AsyncMock,
        auth_client: AsyncClient,
        test_user,
    ):
        """Test checkout with yearly billing."""
        mock_checkout.return_value = {
            "checkout_url": "https://checkout.stripe.com/cs_test_456",
            "session_id": "cs_test_456",
        }

        response = await auth_client.post(
            "/api/v1/subscriptions/checkout",
            json={"plan_slug": "pro", "billing_interval": "yearly"},
        )

        assert response.status_code == 200
        mock_checkout.assert_called_once()
        call_kwargs = mock_checkout.call_args.kwargs
        assert call_kwargs.get("billing_interval") == "yearly"

    async def test_checkout_invalid_plan(self, auth_client: AsyncClient, test_user):
        """Test checkout with invalid plan slug."""
        response = await auth_client.post(
            "/api/v1/subscriptions/checkout",
            json={"plan_slug": "nonexistent", "billing_interval": "monthly"},
        )

        assert response.status_code == 400


class TestBillingPortal:
    """Tests for POST /api/v1/subscriptions/portal"""

    async def test_portal_unauthorized(self, client: AsyncClient):
        """Test billing portal without auth."""
        response = await client.post("/api/v1/subscriptions/portal")
        assert response.status_code == 401

    @patch("app.services.payment.PaymentService.create_billing_portal_session")
    async def test_portal_success(
        self,
        mock_portal: AsyncMock,
        auth_client: AsyncClient,
        test_user,
    ):
        """Test successful billing portal session creation."""
        mock_portal.return_value = {
            "portal_url": "https://billing.stripe.com/session/test_123",
        }

        response = await auth_client.post("/api/v1/subscriptions/portal")

        assert response.status_code == 200
        data = response.json()
        assert "portal_url" in data


class TestCancelSubscription:
    """Tests for POST /api/v1/subscriptions/cancel"""

    async def test_cancel_unauthorized(self, client: AsyncClient):
        """Test cancel without auth."""
        response = await client.post("/api/v1/subscriptions/cancel")
        assert response.status_code == 401

    @patch("app.services.payment.PaymentService.cancel_subscription")
    async def test_cancel_at_period_end(
        self,
        mock_cancel: AsyncMock,
        auth_client: AsyncClient,
        test_user,
    ):
        """Test canceling subscription at period end."""
        mock_cancel.return_value = {
            "tier": "pro",
            "status": "active",
            "is_active": True,
            "is_premium": True,
            "cancel_at_period_end": True,
            "current_period_end": (datetime.now(tz=datetime.UTC) + timedelta(days=30)).isoformat(),
        }

        response = await auth_client.post("/api/v1/subscriptions/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["cancel_at_period_end"]

    @patch("app.services.payment.PaymentService.cancel_subscription")
    async def test_cancel_immediately(
        self,
        mock_cancel: AsyncMock,
        auth_client: AsyncClient,
        test_user,
    ):
        """Test canceling subscription immediately."""
        mock_cancel.return_value = {
            "tier": "free",
            "status": "canceled",
            "is_active": False,
            "is_premium": False,
            "cancel_at_period_end": False,
        }

        response = await auth_client.post(
            "/api/v1/subscriptions/cancel",
            params={"immediately": True},
        )

        assert response.status_code == 200
        mock_cancel.assert_called_once()
        call_kwargs = mock_cancel.call_args.kwargs
        assert call_kwargs.get("immediately")


class TestResumeSubscription:
    """Tests for POST /api/v1/subscriptions/resume"""

    async def test_resume_unauthorized(self, client: AsyncClient):
        """Test resume without auth."""
        response = await client.post("/api/v1/subscriptions/resume")
        assert response.status_code == 401

    @patch("app.services.payment.PaymentService.resume_subscription")
    async def test_resume_success(
        self,
        mock_resume: AsyncMock,
        auth_client: AsyncClient,
        test_user,
    ):
        """Test resuming a canceled subscription."""
        mock_resume.return_value = {
            "tier": "pro",
            "status": "active",
            "is_active": True,
            "is_premium": True,
            "cancel_at_period_end": False,
        }

        response = await auth_client.post("/api/v1/subscriptions/resume")

        assert response.status_code == 200
        data = response.json()
        assert not data["cancel_at_period_end"]
        assert data["is_active"]


class TestUsage:
    """Tests for GET /api/v1/subscriptions/usage"""

    async def test_usage_unauthorized(self, client: AsyncClient):
        """Test usage without auth."""
        response = await client.get("/api/v1/subscriptions/usage")
        assert response.status_code == 401

    async def test_usage_success(self, auth_client: AsyncClient, test_user):
        """Test getting usage statistics."""
        response = await auth_client.get("/api/v1/subscriptions/usage")

        assert response.status_code == 200
        data = response.json()
        assert "tier" in data
        assert "credits_used" in data
        assert "credits_remaining" in data
        assert "storage_used_gb" in data
        assert "generations_this_period" in data


class TestPaymentHistory:
    """Tests for GET /api/v1/subscriptions/payments"""

    async def test_payments_unauthorized(self, client: AsyncClient):
        """Test payments without auth."""
        response = await client.get("/api/v1/subscriptions/payments")
        assert response.status_code == 401

    async def test_payments_empty(self, auth_client: AsyncClient, test_user):
        """Test getting empty payment history."""
        response = await auth_client.get("/api/v1/subscriptions/payments")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_payments_pagination(self, auth_client: AsyncClient, test_user):
        """Test payment history pagination."""
        response = await auth_client.get(
            "/api/v1/subscriptions/payments",
            params={"limit": 5, "offset": 0},
        )

        assert response.status_code == 200


class TestStripeConfig:
    """Tests for GET /api/v1/subscriptions/config"""

    async def test_get_stripe_config(self, client: AsyncClient):
        """Test getting Stripe publishable key."""
        with patch("app.api.v1.subscriptions.get_stripe_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_publishable_key.return_value = "pk_test_123456"
            mock_get_client.return_value = mock_client

            response = await client.get("/api/v1/subscriptions/config")

            assert response.status_code == 200
            data = response.json()
            assert "publishable_key" in data
            assert data["publishable_key"] == "pk_test_123456"
