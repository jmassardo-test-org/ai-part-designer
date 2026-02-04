"""
Tests for Payment Service.

Tests subscription management, checkout sessions, billing portal,
and payment processing functionality.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.payment import PaymentService, PaymentError
from app.models.subscription import SubscriptionTier, TierSlug
from app.models.user import User, Subscription


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_stripe():
    """Mock Stripe client."""
    with patch("app.services.payment.get_stripe_client") as mock:
        stripe_client = MagicMock()
        mock.return_value = stripe_client
        yield stripe_client


@pytest.fixture
def payment_service(db_session):
    """Create payment service with database session."""
    return PaymentService(db_session)


# =============================================================================
# Customer Management Tests
# =============================================================================

class TestCustomerManagement:
    """Tests for Stripe customer management."""

    @pytest.mark.asyncio
    async def test_get_existing_stripe_customer(
        self,
        payment_service: PaymentService,
        db_session,
        test_user,
    ):
        """Test returning existing Stripe customer ID."""
        # Setup: User already has a Stripe customer ID
        test_user.subscription = Subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_existing123",
            tier="free",
        )
        db_session.add(test_user.subscription)
        await db_session.commit()

        result = await payment_service.get_or_create_stripe_customer(test_user)

        assert result == "cus_existing123"

    @pytest.mark.asyncio
    async def test_create_new_stripe_customer(
        self,
        payment_service: PaymentService,
        db_session,
        test_user,
        mock_stripe,
    ):
        """Test creating new Stripe customer when none exists."""
        # Setup: User has subscription but no Stripe ID
        test_user.subscription = Subscription(
            user_id=test_user.id,
            stripe_customer_id=None,
            tier="free",
        )
        db_session.add(test_user.subscription)
        await db_session.commit()

        # Mock Stripe response
        mock_stripe.create_customer.return_value = MagicMock(id="cus_new456")

        result = await payment_service.get_or_create_stripe_customer(test_user)

        assert result == "cus_new456"
        mock_stripe.create_customer.assert_called_once()
        # Verify customer ID was saved
        await db_session.refresh(test_user.subscription)
        assert test_user.subscription.stripe_customer_id == "cus_new456"

    @pytest.mark.asyncio
    async def test_create_customer_stripe_error(
        self,
        payment_service: PaymentService,
        db_session,
        test_user,
        mock_stripe,
    ):
        """Test handling Stripe errors during customer creation."""
        from app.core.stripe import StripeError

        test_user.subscription = Subscription(
            user_id=test_user.id,
            stripe_customer_id=None,
            tier="free",
        )
        db_session.add(test_user.subscription)
        await db_session.commit()

        mock_stripe.create_customer.side_effect = StripeError("API error")

        with pytest.raises(PaymentError) as exc:
            await payment_service.get_or_create_stripe_customer(test_user)

        assert "Failed to create payment profile" in str(exc.value)


# =============================================================================
# Subscription Plans Tests
# =============================================================================

class TestSubscriptionPlans:
    """Tests for subscription plan retrieval."""

    @pytest.mark.asyncio
    async def test_get_subscription_plans(
        self,
        payment_service: PaymentService,
        db_session,
    ):
        """Test retrieving all active subscription plans."""
        # Create test plans
        free_plan = SubscriptionTier(
            slug=TierSlug.FREE,
            name="Free",
            display_order=1,
            is_active=True,
            monthly_credits=100,
            price_monthly_cents=0,
            price_yearly_cents=0,
        )
        pro_plan = SubscriptionTier(
            slug=TierSlug.PRO,
            name="Pro",
            display_order=2,
            is_active=True,
            monthly_credits=1000,
            price_monthly_cents=2900,
            price_yearly_cents=29000,
        )
        inactive_plan = SubscriptionTier(
            slug="inactive",
            name="Inactive Plan",
            display_order=99,
            is_active=False,
            monthly_credits=0,
            price_monthly_cents=0,
            price_yearly_cents=0,
        )
        
        db_session.add_all([free_plan, pro_plan, inactive_plan])
        await db_session.commit()

        result = await payment_service.get_subscription_plans()

        # Should only return active plans, ordered by display_order
        assert len(result) == 2
        assert result[0].slug == TierSlug.FREE
        assert result[1].slug == TierSlug.PRO

    @pytest.mark.asyncio
    async def test_get_plan_by_slug_found(
        self,
        payment_service: PaymentService,
        db_session,
    ):
        """Test finding a plan by slug."""
        plan = SubscriptionTier(
            slug=TierSlug.PRO,
            name="Pro",
            display_order=1,
            is_active=True,
            monthly_credits=1000,
            price_monthly_cents=2900,
            price_yearly_cents=29000,
        )
        db_session.add(plan)
        await db_session.commit()

        result = await payment_service.get_plan_by_slug(TierSlug.PRO)

        assert result is not None
        assert result.slug == TierSlug.PRO
        assert result.name == "Pro"

    @pytest.mark.asyncio
    async def test_get_plan_by_slug_not_found(
        self,
        payment_service: PaymentService,
    ):
        """Test returning None for non-existent plan."""
        result = await payment_service.get_plan_by_slug("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_plan_by_slug_inactive(
        self,
        payment_service: PaymentService,
        db_session,
    ):
        """Test that inactive plans are not returned."""
        plan = SubscriptionTier(
            slug="inactive",
            name="Inactive",
            display_order=1,
            is_active=False,
            monthly_credits=0,
            price_monthly_cents=0,
            price_yearly_cents=0,
        )
        db_session.add(plan)
        await db_session.commit()

        result = await payment_service.get_plan_by_slug("inactive")

        assert result is None


# =============================================================================
# Checkout Tests
# =============================================================================

class TestCheckout:
    """Tests for checkout session creation."""

    @pytest.mark.asyncio
    async def test_create_checkout_session_monthly(
        self,
        payment_service: PaymentService,
        db_session,
        test_user,
        mock_stripe,
    ):
        """Test creating monthly checkout session."""
        # Setup plan
        plan = SubscriptionTier(
            slug=TierSlug.PRO,
            name="Pro",
            display_order=1,
            is_active=True,
            monthly_credits=1000,
            price_monthly_cents=2900,
            price_yearly_cents=29000,
            stripe_price_id_monthly="price_monthly_123",
            stripe_price_id_yearly="price_yearly_456",
        )
        db_session.add(plan)

        # Setup user with Stripe customer
        test_user.subscription = Subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            tier="free",
        )
        db_session.add(test_user.subscription)
        await db_session.commit()

        # Mock checkout session
        mock_stripe.create_checkout_session.return_value = MagicMock(
            id="cs_test123",
            url="https://checkout.stripe.com/session123",
        )

        result = await payment_service.create_checkout_session(
            user=test_user,
            plan_slug=TierSlug.PRO,
            billing_interval="monthly",
        )

        assert result["session_id"] == "cs_test123"
        assert result["checkout_url"] == "https://checkout.stripe.com/session123"
        mock_stripe.create_checkout_session.assert_called_once()
        call_kwargs = mock_stripe.create_checkout_session.call_args.kwargs
        assert call_kwargs["price_id"] == "price_monthly_123"

    @pytest.mark.asyncio
    async def test_create_checkout_session_yearly(
        self,
        payment_service: PaymentService,
        db_session,
        test_user,
        mock_stripe,
    ):
        """Test creating yearly checkout session."""
        plan = SubscriptionTier(
            slug=TierSlug.PRO,
            name="Pro",
            display_order=1,
            is_active=True,
            monthly_credits=1000,
            price_monthly_cents=2900,
            price_yearly_cents=29000,
            stripe_price_id_monthly="price_monthly_123",
            stripe_price_id_yearly="price_yearly_456",
        )
        db_session.add(plan)

        test_user.subscription = Subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            tier="free",
        )
        db_session.add(test_user.subscription)
        await db_session.commit()

        mock_stripe.create_checkout_session.return_value = MagicMock(
            id="cs_yearly123",
            url="https://checkout.stripe.com/yearly",
        )

        result = await payment_service.create_checkout_session(
            user=test_user,
            plan_slug=TierSlug.PRO,
            billing_interval="yearly",
        )

        call_kwargs = mock_stripe.create_checkout_session.call_args.kwargs
        assert call_kwargs["price_id"] == "price_yearly_456"

    @pytest.mark.asyncio
    async def test_create_checkout_session_plan_not_found(
        self,
        payment_service: PaymentService,
        test_user,
    ):
        """Test error when plan doesn't exist."""
        with pytest.raises(PaymentError) as exc:
            await payment_service.create_checkout_session(
                user=test_user,
                plan_slug="nonexistent",
            )

        assert "not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_checkout_session_free_plan_error(
        self,
        payment_service: PaymentService,
        db_session,
        test_user,
    ):
        """Test error when trying to checkout for free plan."""
        plan = SubscriptionTier(
            slug=TierSlug.FREE,
            name="Free",
            display_order=1,
            is_active=True,
            monthly_credits=100,
            price_monthly_cents=0,
            price_yearly_cents=0,
        )
        db_session.add(plan)
        await db_session.commit()

        with pytest.raises(PaymentError) as exc:
            await payment_service.create_checkout_session(
                user=test_user,
                plan_slug=TierSlug.FREE,
            )

        assert "Cannot checkout for free plan" in str(exc.value)


# =============================================================================
# Billing Portal Tests
# =============================================================================

class TestBillingPortal:
    """Tests for billing portal access."""

    @pytest.mark.asyncio
    async def test_create_billing_portal_session(
        self,
        payment_service: PaymentService,
        db_session,
        test_user,
        mock_stripe,
    ):
        """Test creating billing portal session."""
        test_user.subscription = Subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            tier="pro",
        )
        db_session.add(test_user.subscription)
        await db_session.commit()

        mock_stripe.create_billing_portal_session.return_value = MagicMock(
            url="https://billing.stripe.com/portal123",
        )

        result = await payment_service.create_billing_portal_session(user=test_user)

        assert result["portal_url"] == "https://billing.stripe.com/portal123"

    @pytest.mark.asyncio
    async def test_create_billing_portal_no_customer(
        self,
        payment_service: PaymentService,
        test_user,
    ):
        """Test error when user has no Stripe customer."""
        test_user.subscription = None

        with pytest.raises(PaymentError) as exc:
            await payment_service.create_billing_portal_session(user=test_user)

        assert "No payment profile found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_create_billing_portal_stripe_error(
        self,
        payment_service: PaymentService,
        db_session,
        test_user,
        mock_stripe,
    ):
        """Test handling Stripe errors for portal."""
        from app.core.stripe import StripeError

        test_user.subscription = Subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_test123",
            tier="pro",
        )
        db_session.add(test_user.subscription)
        await db_session.commit()

        mock_stripe.create_billing_portal_session.side_effect = StripeError("Portal error")

        with pytest.raises(PaymentError) as exc:
            await payment_service.create_billing_portal_session(user=test_user)

        assert "Failed to access billing portal" in str(exc.value)
