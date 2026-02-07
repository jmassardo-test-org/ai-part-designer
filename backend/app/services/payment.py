"""
Payment Service.

Handles subscription management, checkout sessions, billing portal,
and payment processing via Stripe.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.stripe import StripeClient, StripeError, get_stripe_client
from app.models.payment import PaymentHistory, PaymentStatus, PaymentType
from app.models.subscription import SubscriptionTier, TierSlug
from app.models.user import Subscription, User

if TYPE_CHECKING:
    from stripe import Invoice
    from stripe import Subscription as StripeSubscription
    from stripe.checkout import Session as CheckoutSession


logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Payment-related error."""


class PaymentService:
    """
    Payment service for handling subscriptions and billing.

    Integrates with Stripe for payment processing and manages
    subscription lifecycle within the application.
    """

    def __init__(self, db: AsyncSession):
        """Initialize payment service with database session."""
        self.db = db
        self._stripe: StripeClient | None = None

    @property
    def stripe(self) -> Any:
        """Lazy-load Stripe client."""
        if self._stripe is None:
            self._stripe = get_stripe_client()
        return self._stripe

    # =============================
    # Customer Management
    # =============================

    async def get_or_create_stripe_customer(self, user: User) -> str:
        """
        Get or create a Stripe customer for a user.

        Args:
            user: The user to get/create customer for

        Returns:
            Stripe customer ID
        """
        # Check if user already has a Stripe customer
        if user.subscription and user.subscription.stripe_customer_id:
            return user.subscription.stripe_customer_id

        # Create new Stripe customer
        try:
            customer = self.stripe.create_customer(
                email=user.email,
                name=user.display_name or user.email,
                metadata={
                    "user_id": str(user.id),
                    "environment": settings.ENVIRONMENT,
                },
            )

            # Update user's subscription record
            if user.subscription:
                user.subscription.stripe_customer_id = customer.id
                await self.db.commit()

            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return cast("str", customer.id)

        except StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise PaymentError(f"Failed to create payment profile: {e}")

    # =============================
    # Subscription Plans
    # =============================

    async def get_subscription_plans(self) -> list[SubscriptionTier]:
        """
        Get all active subscription plans.

        Returns:
            List of subscription tiers ordered by display_order
        """
        result = await self.db.execute(
            select(SubscriptionTier)
            .where(SubscriptionTier.is_active)
            .order_by(SubscriptionTier.display_order)
        )
        return list(result.scalars().all())

    async def get_plan_by_slug(self, slug: str) -> SubscriptionTier | None:
        """Get a subscription plan by its slug."""
        result = await self.db.execute(
            select(SubscriptionTier)
            .where(SubscriptionTier.slug == slug)
            .where(SubscriptionTier.is_active)
        )
        return result.scalar_one_or_none()

    # =============================
    # Checkout
    # =============================

    async def create_checkout_session(
        self,
        user: User,
        plan_slug: str,
        billing_interval: str = "monthly",
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription.

        Args:
            user: The user upgrading
            plan_slug: The plan to subscribe to (pro, enterprise)
            billing_interval: "monthly" or "yearly"
            success_url: Override success redirect URL
            cancel_url: Override cancel redirect URL

        Returns:
            Dict with checkout_url and session_id
        """
        # Get the plan
        plan = await self.get_plan_by_slug(plan_slug)
        if not plan:
            raise PaymentError(f"Plan '{plan_slug}' not found")

        if plan_slug == TierSlug.FREE:
            raise PaymentError("Cannot checkout for free plan")

        # Get the correct price ID
        if billing_interval == "yearly":
            price_id = plan.stripe_price_id_yearly
        else:
            price_id = plan.stripe_price_id_monthly

        if not price_id:
            raise PaymentError(f"No Stripe price configured for {plan_slug} {billing_interval}")

        # Get or create Stripe customer
        customer_id = await self.get_or_create_stripe_customer(user)

        # Build URLs
        base_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"
        success = success_url or f"{base_url}/settings/billing?success=true"
        cancel = cancel_url or f"{base_url}/pricing?canceled=true"

        try:
            session = self.stripe.create_checkout_session(
                customer_id=customer_id,
                price_id=price_id,
                success_url=success,
                cancel_url=cancel,
                metadata={
                    "user_id": str(user.id),
                    "plan_slug": plan_slug,
                    "billing_interval": billing_interval,
                },
            )

            logger.info(f"Created checkout session {session.id} for user {user.id}")

            return {
                "checkout_url": session.url,
                "session_id": session.id,
            }

        except StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise PaymentError(f"Failed to start checkout: {e}")

    # =============================
    # Billing Portal
    # =============================

    async def create_billing_portal_session(
        self,
        user: User,
        return_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a Stripe Billing Portal session.

        Allows the user to manage payment methods, view invoices,
        and manage their subscription.

        Args:
            user: The user accessing the portal
            return_url: URL to return to after portal

        Returns:
            Dict with portal_url
        """
        if not user.subscription or not user.subscription.stripe_customer_id:
            raise PaymentError("No payment profile found")

        # Build return URL
        base_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"
        return_to = return_url or f"{base_url}/settings/billing"

        try:
            session = self.stripe.create_billing_portal_session(
                customer_id=user.subscription.stripe_customer_id,
                return_url=return_to,
            )

            logger.info(f"Created portal session for user {user.id}")

            return {
                "portal_url": session.url,
            }

        except StripeError as e:
            logger.error(f"Failed to create billing portal: {e}")
            raise PaymentError(f"Failed to access billing portal: {e}")

    # =============================
    # Subscription Management
    # =============================

    async def get_subscription_status(self, user: User) -> dict[str, Any]:
        """
        Get the user's current subscription status.

        Returns:
            Dict with subscription details
        """
        sub = user.subscription
        if not sub:
            return {
                "tier": TierSlug.FREE,
                "status": "active",
                "is_active": True,
                "is_premium": False,
            }

        return {
            "tier": sub.tier,
            "status": sub.status,
            "is_active": sub.is_active,
            "is_premium": sub.is_premium,
            "stripe_subscription_id": sub.stripe_subscription_id,
            "stripe_customer_id": sub.stripe_customer_id,
            "current_period_start": sub.current_period_start.isoformat()
            if sub.current_period_start
            else None,
            "current_period_end": sub.current_period_end.isoformat()
            if sub.current_period_end
            else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }

    async def cancel_subscription(
        self,
        user: User,
        immediately: bool = False,
    ) -> dict[str, Any]:
        """
        Cancel user's subscription.

        Args:
            user: The user canceling
            immediately: If True, cancel now. If False, cancel at period end.

        Returns:
            Dict with updated subscription status
        """
        if not user.subscription or not user.subscription.stripe_subscription_id:
            raise PaymentError("No active subscription to cancel")

        try:
            self.stripe.cancel_subscription(
                subscription_id=user.subscription.stripe_subscription_id,
                cancel_at_period_end=not immediately,
            )

            # Update local record
            if immediately:
                user.subscription.status = "canceled"
                user.subscription.tier = TierSlug.FREE
            else:
                user.subscription.cancel_at_period_end = True

            await self.db.commit()

            logger.info(f"Canceled subscription for user {user.id}, immediate={immediately}")

            return await self.get_subscription_status(user)

        except StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise PaymentError(f"Failed to cancel subscription: {e}")

    async def resume_subscription(self, user: User) -> dict[str, Any]:
        """
        Resume a subscription that was set to cancel at period end.

        Args:
            user: The user resuming

        Returns:
            Dict with updated subscription status
        """
        if not user.subscription or not user.subscription.stripe_subscription_id:
            raise PaymentError("No subscription found")

        if not user.subscription.cancel_at_period_end:
            raise PaymentError("Subscription is not set to cancel")

        try:
            self.stripe.resume_subscription(
                subscription_id=user.subscription.stripe_subscription_id,
            )

            # Update local record
            user.subscription.cancel_at_period_end = False
            await self.db.commit()

            logger.info(f"Resumed subscription for user {user.id}")

            return await self.get_subscription_status(user)

        except StripeError as e:
            logger.error(f"Failed to resume subscription: {e}")
            raise PaymentError(f"Failed to resume subscription: {e}")

    # =============================
    # Webhook Handlers
    # =============================

    async def handle_checkout_completed(
        self,
        session: "CheckoutSession",
    ) -> None:
        """
        Handle checkout.session.completed webhook event.

        Creates or updates the user's subscription.
        """
        user_id = (session.metadata or {}).get("user_id")
        if not user_id:
            logger.warning("Checkout session missing user_id metadata")
            return

        # Get user
        result = await self.db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            logger.error(f"User {user_id} not found for checkout completion")
            return

        # Get subscription details from Stripe
        stripe_sub = self.stripe.get_subscription(session.subscription)
        plan_slug = (session.metadata or {}).get("plan_slug", "pro")

        # Update subscription
        if user.subscription:
            user.subscription.tier = plan_slug
            user.subscription.status = "active"
            user.subscription.stripe_subscription_id = str(session.subscription) if session.subscription else None
            user.subscription.stripe_customer_id = str(session.customer) if session.customer else None
            user.subscription.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start, tz=UTC
            )
            user.subscription.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=UTC
            )
            user.subscription.cancel_at_period_end = False

        await self.db.commit()

        logger.info(f"Activated {plan_slug} subscription for user {user_id}")

    async def handle_subscription_updated(
        self,
        subscription: "StripeSubscription",
    ) -> None:
        """Handle customer.subscription.updated webhook event."""
        # Find user by subscription ID
        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription.id)
        )
        sub = result.scalar_one_or_none()

        if not sub:
            logger.warning(f"No local subscription for Stripe sub {subscription.id}")
            return

        # Update period dates
        sub.current_period_start = datetime.fromtimestamp(subscription.current_period_start, tz=UTC)  # type: ignore[attr-defined]
        sub.current_period_end = datetime.fromtimestamp(subscription.current_period_end, tz=UTC)  # type: ignore[attr-defined]
        sub.cancel_at_period_end = subscription.cancel_at_period_end

        # Update status
        if subscription.status == "active":
            sub.status = "active"
        elif subscription.status == "past_due":
            sub.status = "past_due"
        elif subscription.status in ("canceled", "unpaid"):
            sub.status = "canceled"
            sub.tier = TierSlug.FREE

        await self.db.commit()

        logger.info(f"Updated subscription {subscription.id}")

    async def handle_subscription_deleted(
        self,
        subscription: "StripeSubscription",
    ) -> None:
        """Handle customer.subscription.deleted webhook event."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == subscription.id)
        )
        sub = result.scalar_one_or_none()

        if not sub:
            return

        # Downgrade to free
        sub.tier = TierSlug.FREE
        sub.status = "canceled"
        sub.stripe_subscription_id = None
        sub.cancel_at_period_end = False

        await self.db.commit()

        logger.info(f"Subscription {subscription.id} deleted, user downgraded to free")

    async def handle_invoice_paid(
        self,
        invoice: "Invoice",
    ) -> None:
        """Handle invoice.paid webhook event."""
        # Find user by customer ID
        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == invoice.customer)
        )
        sub = result.scalar_one_or_none()

        if not sub:
            logger.warning(f"No subscription for customer {invoice.customer}")
            return

        # Record payment
        payment = PaymentHistory(
            user_id=sub.user_id,
            stripe_invoice_id=invoice.id,
            stripe_subscription_id=getattr(invoice, "subscription", None),
            stripe_charge_id=getattr(invoice, "charge", None),
            payment_type=PaymentType.SUBSCRIPTION.value,
            status=PaymentStatus.SUCCEEDED.value,
            amount_cents=invoice.amount_paid,
            currency=invoice.currency,
            description=f"Subscription payment - {sub.tier}",
            paid_at=datetime.fromtimestamp(invoice.status_transitions.paid_at, tz=UTC)
            if invoice.status_transitions.paid_at
            else datetime.now(UTC),
            period_start=datetime.fromtimestamp(invoice.lines.data[0].period.start, tz=UTC)
            if invoice.lines.data
            else None,
            period_end=datetime.fromtimestamp(invoice.lines.data[0].period.end, tz=UTC)
            if invoice.lines.data
            else None,
            invoice_url=invoice.hosted_invoice_url,
            invoice_pdf_url=invoice.invoice_pdf,
        )

        self.db.add(payment)
        await self.db.commit()

        logger.info(f"Recorded payment {payment.id} for invoice {invoice.id}")

    async def handle_invoice_payment_failed(
        self,
        invoice: "Invoice",
    ) -> None:
        """Handle invoice.payment_failed webhook event."""
        # Find subscription
        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == invoice.customer)
        )
        sub = result.scalar_one_or_none()

        if sub:
            sub.status = "past_due"
            await self.db.commit()

        # Record failed payment
        if sub:
            payment = PaymentHistory(
                user_id=sub.user_id,
                stripe_invoice_id=invoice.id,
                stripe_subscription_id=getattr(invoice, "subscription", None),
                payment_type=PaymentType.SUBSCRIPTION.value,
                status=PaymentStatus.FAILED.value,
                amount_cents=invoice.amount_due,
                currency=invoice.currency,
                description=f"Failed payment - {sub.tier}",
                failure_code=invoice.last_finalization_error.code
                if invoice.last_finalization_error
                else None,
                failure_message=invoice.last_finalization_error.message
                if invoice.last_finalization_error
                else None,
            )

            self.db.add(payment)
            await self.db.commit()

        logger.warning(f"Payment failed for invoice {invoice.id}")

    # =============================
    # Payment History
    # =============================

    async def get_payment_history(
        self,
        user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PaymentHistory]:
        """Get user's payment history."""
        result = await self.db.execute(
            select(PaymentHistory)
            .where(PaymentHistory.user_id == user.id)
            .order_by(PaymentHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


# Factory function for dependency injection
async def get_payment_service(db: AsyncSession) -> PaymentService:
    """Get payment service instance."""
    return PaymentService(db)
