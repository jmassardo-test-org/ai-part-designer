"""
Webhook endpoints for external service callbacks.

Handles webhooks from Stripe and other external services.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.stripe import SignatureVerificationError, get_stripe_client
from app.services.payment import PaymentService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Handle Stripe webhook events.

    Stripe sends events for subscription lifecycle changes,
    successful payments, and failed payments.

    Webhook events handled:
    - checkout.session.completed: User completed checkout
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription canceled
    - invoice.paid: Successful payment
    - invoice.payment_failed: Payment failed
    """
    # Get raw body for signature verification
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")

    if not signature:
        logger.warning("Webhook received without signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    # Verify webhook signature and construct event
    try:
        stripe_client = get_stripe_client()
        event = stripe_client.construct_webhook_event(
            payload=payload,
            signature=signature,
        )
    except SignatureVerificationError as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )
    except ValueError as e:
        logger.warning(f"Invalid webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        )

    # Log event for debugging
    logger.info(f"Received Stripe webhook: {event.type}")

    # Initialize payment service
    payment_service = PaymentService(db)

    # Route to appropriate handler
    try:
        if event.type == "checkout.session.completed":
            session = event.data.object
            await payment_service.handle_checkout_completed(session)

        elif event.type == "customer.subscription.updated":
            subscription = event.data.object
            await payment_service.handle_subscription_updated(subscription)

        elif event.type == "customer.subscription.deleted":
            subscription = event.data.object
            await payment_service.handle_subscription_deleted(subscription)

        elif event.type == "invoice.paid":
            invoice = event.data.object
            await payment_service.handle_invoice_paid(invoice)

        elif event.type == "invoice.payment_failed":
            invoice = event.data.object
            await payment_service.handle_invoice_payment_failed(invoice)

        elif event.type == "customer.subscription.created":
            # Logged but handled via checkout.session.completed
            logger.info(f"Subscription created: {event.data.object.id}")

        elif event.type == "customer.updated":
            # Customer details updated (email, etc.)
            logger.info(f"Customer updated: {event.data.object.id}")

        elif event.type == "payment_intent.succeeded":
            # Payment succeeded (already handled via invoice.paid for subscriptions)
            logger.info(f"Payment intent succeeded: {event.data.object.id}")

        elif event.type == "payment_intent.payment_failed":
            # Payment failed (already handled via invoice.payment_failed)
            logger.info(f"Payment intent failed: {event.data.object.id}")

        else:
            # Unhandled event type - log but don't error
            logger.info(f"Unhandled webhook event type: {event.type}")

    except Exception as e:
        # Log error but return 200 to prevent Stripe retries for app errors
        # (Stripe will retry on 5xx but not on 2xx/4xx)
        logger.error(f"Error processing webhook {event.type}: {e}", exc_info=True)
        # Still return success to acknowledge receipt
        # The error is logged and can be investigated

    return {"received": True, "event_type": event.type}
