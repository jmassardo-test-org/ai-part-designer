"""
Subscription API endpoints.

Handles subscription plans, checkout, billing portal, and subscription management.
"""

import logging
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.stripe import get_stripe_client
from app.models.user import User
from app.services.payment import PaymentError, PaymentService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
logger = logging.getLogger(__name__)


# =============================
# Schemas
# =============================


class FeatureSet(BaseModel):
    """Feature flags for a plan."""

    ai_generation: bool = True
    export_2d: bool = False
    hardware_library: bool = True
    collaboration: bool = False
    api_access: bool = False
    priority_queue: bool = False
    white_label: bool = False


class PlanResponse(BaseModel):
    """Subscription plan response."""

    slug: str
    name: str
    description: str | None

    # Limits
    monthly_credits: int
    max_concurrent_jobs: int
    max_storage_gb: int
    max_projects: int
    max_designs_per_project: int
    max_file_size_mb: int

    # Features
    features: dict[str, Any]

    # Pricing
    price_monthly: float
    price_yearly: float

    # Stripe (for checkout)
    stripe_price_id_monthly: str | None = None
    stripe_price_id_yearly: str | None = None

    class Config:
        from_attributes = True


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    plan_slug: str = Field(..., description="Plan to subscribe to: 'pro' or 'enterprise'")
    billing_interval: Literal["monthly", "yearly"] = Field(
        default="monthly", description="Billing frequency"
    )
    success_url: str | None = Field(None, description="Override success redirect URL")
    cancel_url: str | None = Field(None, description="Override cancel redirect URL")


class CheckoutResponse(BaseModel):
    """Checkout session response."""

    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    """Billing portal session response."""

    portal_url: str


class SubscriptionResponse(BaseModel):
    """Current subscription status."""

    tier: str
    status: str
    is_active: bool
    is_premium: bool
    stripe_subscription_id: str | None = None
    stripe_customer_id: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool = False


class PaymentHistoryItem(BaseModel):
    """Payment history entry."""

    id: str
    payment_type: str
    status: str
    amount: float
    currency: str
    description: str
    paid_at: datetime | None
    invoice_url: str | None

    class Config:
        from_attributes = True


class UsageResponse(BaseModel):
    """Current usage statistics."""

    tier: str

    # Credit usage
    credits_used: int
    credits_remaining: int
    credits_total: int

    # Storage usage
    storage_used_gb: float
    storage_limit_gb: int

    # Generation usage
    generations_this_period: int
    generations_limit: int

    # Period info
    period_start: str | None
    period_end: str | None


class PublishableKeyResponse(BaseModel):
    """Stripe publishable key for frontend."""

    publishable_key: str


# =============================
# Endpoints
# =============================


@router.get("/config")
async def get_stripe_config() -> PublishableKeyResponse:
    """
    Get Stripe configuration for frontend.

    Returns the publishable key needed to initialize Stripe.js.
    """
    stripe_client = get_stripe_client()
    return PublishableKeyResponse(publishable_key=stripe_client.get_publishable_key())


@router.get("/plans")
async def list_plans(
    db: AsyncSession = Depends(get_db),
) -> list[PlanResponse]:
    """
    List all available subscription plans.

    Returns active subscription tiers with pricing and features.
    Public endpoint - no authentication required.
    """
    payment_service = PaymentService(db)
    plans = await payment_service.get_subscription_plans()

    return [
        PlanResponse(
            slug=p.slug,
            name=p.name,
            description=p.description,
            monthly_credits=p.monthly_credits,
            max_concurrent_jobs=p.max_concurrent_jobs,
            max_storage_gb=p.max_storage_gb,
            max_projects=p.max_projects,
            max_designs_per_project=p.max_designs_per_project,
            max_file_size_mb=p.max_file_size_mb,
            features=p.features,
            price_monthly=float(p.price_monthly),
            price_yearly=float(p.price_yearly),
            stripe_price_id_monthly=p.stripe_price_id_monthly,
            stripe_price_id_yearly=p.stripe_price_id_yearly,
        )
        for p in plans
    ]


@router.get("/current")
async def get_current_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """
    Get the current user's subscription status.

    Returns subscription tier, status, and billing period details.
    """
    payment_service = PaymentService(db)
    status = await payment_service.get_subscription_status(user)

    return SubscriptionResponse(**status)


@router.post("/checkout")
@audit_log(
    action="subscription_checkout",
    resource_type="subscription",
    context_builder=lambda **kwargs: {
        "plan_slug": kwargs["request"].plan_slug,
        "billing_interval": kwargs["request"].billing_interval,
    },
)
async def create_checkout(
    request: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """
    Create a Stripe Checkout session for subscription.

    Redirects the user to Stripe's hosted checkout page.

    Args:
        request: Checkout details including plan and billing interval

    Returns:
        Checkout URL to redirect the user to
    """
    payment_service = PaymentService(db)

    try:
        result = await payment_service.create_checkout_session(
            user=user,
            plan_slug=request.plan_slug,
            billing_interval=request.billing_interval,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )

        return CheckoutResponse(
            checkout_url=result["checkout_url"],
            session_id=result["session_id"],
        )

    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/portal")
async def create_portal_session(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    return_url: str | None = None,
) -> PortalResponse:
    """
    Create a Stripe Billing Portal session.

    Allows users to manage payment methods, view invoices,
    and update subscription.

    Returns:
        Portal URL to redirect the user to
    """
    payment_service = PaymentService(db)

    try:
        result = await payment_service.create_billing_portal_session(
            user=user,
            return_url=return_url,
        )

        return PortalResponse(portal_url=result["portal_url"])

    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/cancel")
@audit_log(
    action="subscription_cancel",
    resource_type="subscription",
    context_builder=lambda **kwargs: {
        "immediately": kwargs.get("immediately", False),
    },
)
async def cancel_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    immediately: bool = False,
) -> SubscriptionResponse:
    """
    Cancel the current subscription.

    By default, cancels at the end of the current billing period.
    User retains access until then.

    Args:
        immediately: If True, cancel immediately instead of at period end

    Returns:
        Updated subscription status
    """
    payment_service = PaymentService(db)

    try:
        status_dict = await payment_service.cancel_subscription(
            user=user,
            immediately=immediately,
        )

        return SubscriptionResponse(**status_dict)

    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/resume")
@audit_log(
    action="subscription_resume",
    resource_type="subscription",
)
async def resume_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """
    Resume a subscription that was set to cancel.

    Only works if the subscription was canceled at period end
    and the period hasn't ended yet.

    Returns:
        Updated subscription status
    """
    payment_service = PaymentService(db)

    try:
        status_dict = await payment_service.resume_subscription(user)
        return SubscriptionResponse(**status_dict)

    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/usage")
async def get_usage(
    user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_db),
) -> UsageResponse:
    """
    Get current usage statistics.

    Shows credits used, storage consumed, and generation counts
    against the user's tier limits.
    """
    # Get subscription info
    sub = user.subscription
    tier = sub.tier if sub else "free"

    # Get usage quota
    usage = user.usage_quota

    # Get credit balance
    credits = user.credit_balance

    # Determine limits based on tier
    tier_limits = {
        "free": {"credits": 10, "storage_gb": 1, "generations": 10},
        "pro": {"credits": 100, "storage_gb": 50, "generations": 100},
        "enterprise": {"credits": 1000, "storage_gb": 500, "generations": 1000},
    }
    limits = tier_limits.get(tier, tier_limits["free"])

    return UsageResponse(
        tier=tier,
        credits_used=credits.lifetime_spent if credits else 0,
        credits_remaining=credits.balance if credits else limits["credits"],
        credits_total=limits["credits"],
        storage_used_gb=usage.storage_used_gb if usage else 0.0,
        storage_limit_gb=limits["storage_gb"],
        generations_this_period=usage.period_generations if usage else 0,
        generations_limit=limits["generations"],
        period_start=sub.current_period_start.isoformat()
        if sub and sub.current_period_start
        else None,
        period_end=sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
    )


@router.get("/payments")
async def get_payment_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
) -> list[PaymentHistoryItem]:
    """
    Get payment history.

    Returns a list of past payments with invoice links.
    """
    payment_service = PaymentService(db)
    payments = await payment_service.get_payment_history(
        user=user,
        limit=limit,
        offset=offset,
    )

    return [
        PaymentHistoryItem(
            id=str(p.id),
            payment_type=p.payment_type,
            status=p.status,
            amount=p.amount,
            currency=p.currency,
            description=p.description,
            paid_at=p.paid_at,
            invoice_url=p.invoice_url,
        )
        for p in payments
    ]
