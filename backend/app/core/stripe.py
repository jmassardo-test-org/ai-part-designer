"""
Stripe integration module.

Provides a client wrapper for Stripe API operations including
subscription management, checkout sessions, and webhook handling.
"""

import stripe
from stripe import StripeError, SignatureVerificationError

from app.core.config import settings


# Configure Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY if hasattr(settings, 'STRIPE_SECRET_KEY') else None


class StripeClient:
    """
    Stripe API client wrapper.
    
    Provides typed methods for common Stripe operations.
    """
    
    def __init__(self):
        """Initialize Stripe client with configuration."""
        if not stripe.api_key:
            raise ValueError("STRIPE_SECRET_KEY is not configured")
    
    @staticmethod
    def get_publishable_key() -> str:
        """Get the publishable key for frontend."""
        return getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '')
    
    # =====================
    # Customer Operations
    # =====================
    
    def create_customer(
        self,
        email: str,
        name: str | None = None,
        metadata: dict | None = None,
    ) -> stripe.Customer:
        """
        Create a new Stripe customer.
        
        Args:
            email: Customer's email address
            name: Customer's display name
            metadata: Additional metadata to store
            
        Returns:
            Created Stripe Customer object
        """
        return stripe.Customer.create(
            email=email,
            name=name,
            metadata=metadata or {},
        )
    
    def get_customer(self, customer_id: str) -> stripe.Customer:
        """Retrieve a Stripe customer by ID."""
        return stripe.Customer.retrieve(customer_id)
    
    def update_customer(
        self,
        customer_id: str,
        email: str | None = None,
        name: str | None = None,
        metadata: dict | None = None,
    ) -> stripe.Customer:
        """Update a Stripe customer's details."""
        update_data = {}
        if email:
            update_data["email"] = email
        if name:
            update_data["name"] = name
        if metadata:
            update_data["metadata"] = metadata
        
        return stripe.Customer.modify(customer_id, **update_data)
    
    # =====================
    # Subscription Operations
    # =====================
    
    def get_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Retrieve a subscription by ID."""
        return stripe.Subscription.retrieve(subscription_id)
    
    def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = True,
    ) -> stripe.Subscription:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: The Stripe subscription ID
            cancel_at_period_end: If True, cancels at the end of the billing period.
                                  If False, cancels immediately.
        
        Returns:
            Updated Stripe Subscription object
        """
        if cancel_at_period_end:
            return stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True,
            )
        else:
            return stripe.Subscription.cancel(subscription_id)
    
    def resume_subscription(self, subscription_id: str) -> stripe.Subscription:
        """
        Resume a subscription that was set to cancel at period end.
        
        Args:
            subscription_id: The Stripe subscription ID
            
        Returns:
            Updated Stripe Subscription object
        """
        return stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False,
        )
    
    def update_subscription(
        self,
        subscription_id: str,
        price_id: str,
        proration_behavior: str = "create_prorations",
    ) -> stripe.Subscription:
        """
        Update a subscription to a different price/plan.
        
        Args:
            subscription_id: The Stripe subscription ID
            price_id: The new Stripe Price ID to switch to
            proration_behavior: How to handle prorations
            
        Returns:
            Updated Stripe Subscription object
        """
        subscription = stripe.Subscription.retrieve(subscription_id)
        return stripe.Subscription.modify(
            subscription_id,
            items=[{
                "id": subscription["items"]["data"][0]["id"],
                "price": price_id,
            }],
            proration_behavior=proration_behavior,
        )
    
    # =====================
    # Checkout Operations
    # =====================
    
    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        mode: str = "subscription",
        allow_promotion_codes: bool = True,
        metadata: dict | None = None,
    ) -> stripe.checkout.Session:
        """
        Create a Stripe Checkout session.
        
        Args:
            customer_id: The Stripe customer ID
            price_id: The Stripe Price ID for the subscription
            success_url: URL to redirect to on successful payment
            cancel_url: URL to redirect to if checkout is canceled
            mode: "subscription" or "payment"
            allow_promotion_codes: Whether to allow promo codes
            metadata: Additional metadata
            
        Returns:
            Checkout Session object with URL
        """
        return stripe.checkout.Session.create(
            customer=customer_id,
            mode=mode,
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=allow_promotion_codes,
            metadata=metadata or {},
        )
    
    # =====================
    # Billing Portal
    # =====================
    
    def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> stripe.billing_portal.Session:
        """
        Create a Stripe Billing Portal session.
        
        Allows customers to manage their subscription, payment methods,
        and view invoice history.
        
        Args:
            customer_id: The Stripe customer ID
            return_url: URL to return to after leaving the portal
            
        Returns:
            Billing Portal Session object with URL
        """
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
    
    # =====================
    # Product/Price Operations
    # =====================
    
    def list_prices(
        self,
        product_id: str | None = None,
        active: bool = True,
    ) -> list:
        """List prices, optionally filtered by product."""
        params: dict = {"active": active}
        if product_id:
            params["product"] = product_id
        
        return list(stripe.Price.list(**params))
    
    def get_price(self, price_id: str) -> stripe.Price:
        """Retrieve a price by ID."""
        return stripe.Price.retrieve(price_id)
    
    # =====================
    # Webhook Operations
    # =====================
    
    @staticmethod
    def construct_webhook_event(
        payload: bytes,
        signature: str,
        webhook_secret: str | None = None,
    ) -> stripe.Event:
        """
        Construct and verify a webhook event.
        
        Args:
            payload: Raw request body bytes
            signature: Stripe-Signature header value
            webhook_secret: Webhook endpoint secret (uses env if not provided)
            
        Returns:
            Verified Stripe Event object
            
        Raises:
            SignatureVerificationError: If signature is invalid
        """
        secret = webhook_secret or getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        if not secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET is not configured")
        
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=secret,
        )


# Singleton instance
_stripe_client: StripeClient | None = None


def get_stripe_client() -> StripeClient:
    """
    Get the Stripe client singleton.
    
    Returns:
        StripeClient instance
        
    Raises:
        ValueError: If Stripe is not configured
    """
    global _stripe_client
    
    if _stripe_client is None:
        _stripe_client = StripeClient()
    
    return _stripe_client


# Re-export stripe errors for convenience
__all__ = [
    "StripeClient",
    "get_stripe_client",
    "StripeError",
    "SignatureVerificationError",
    "stripe",
]
