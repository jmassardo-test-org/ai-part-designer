"""
Tests for Stripe payment integration module.

Tests customer operations, subscription management, checkout sessions,
billing portal, and webhook verification.
"""

from unittest.mock import MagicMock, patch

import pytest
import stripe
from stripe import SignatureVerificationError, StripeError

from app.core.stripe import StripeClient, get_stripe_client


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_stripe_api():
    """Mock Stripe API with default success responses."""
    with patch("app.core.stripe.stripe") as mock_stripe:
        # Set up default successful mock responses
        mock_stripe.api_key = "test_stripe_secret_key"
        yield mock_stripe


@pytest.fixture
def stripe_client(mock_stripe_api):
    """Create a StripeClient instance with mocked API."""
    with patch("app.core.stripe.settings") as mock_settings:
        mock_settings.STRIPE_SECRET_KEY = "test_stripe_secret_key"
        mock_settings.STRIPE_PUBLISHABLE_KEY = "test_stripe_publishable_key"
        mock_settings.STRIPE_WEBHOOK_SECRET = "test_webhook_secret"
        client = StripeClient()
        yield client


@pytest.fixture
def mock_customer():
    """Create a mock Stripe customer object."""
    customer = MagicMock(spec=stripe.Customer)
    customer.id = "cus_test123"
    customer.email = "test@example.com"
    customer.name = "Test User"
    customer.metadata = {}
    return customer


@pytest.fixture
def mock_subscription():
    """Create a mock Stripe subscription object."""
    subscription = MagicMock(spec=stripe.Subscription)
    subscription.id = "sub_test123"
    subscription.customer = "cus_test123"
    subscription.status = "active"
    subscription.cancel_at_period_end = False
    subscription.items = {
        "data": [
            {
                "id": "si_test123",
                "price": {"id": "price_test123"},
            }
        ]
    }
    return subscription


@pytest.fixture
def mock_checkout_session():
    """Create a mock Stripe checkout session object."""
    session = MagicMock(spec=stripe.checkout.Session)
    session.id = "cs_test123"
    session.url = "https://checkout.stripe.com/test123"
    session.customer = "cus_test123"
    return session


@pytest.fixture
def mock_billing_portal_session():
    """Create a mock Stripe billing portal session object."""
    session = MagicMock(spec=stripe.billing_portal.Session)
    session.id = "bps_test123"
    session.url = "https://billing.stripe.com/test123"
    return session


@pytest.fixture
def mock_price():
    """Create a mock Stripe price object."""
    price = MagicMock(spec=stripe.Price)
    price.id = "price_test123"
    price.product = "prod_test123"
    price.unit_amount = 999
    price.currency = "usd"
    price.recurring = {"interval": "month"}
    price.active = True
    return price


# =============================================================================
# Customer Operations Tests
# =============================================================================


def test_create_customer_with_email_only(stripe_client, mock_stripe_api, mock_customer):
    """Test creating a customer with only email."""
    mock_stripe_api.Customer.create.return_value = mock_customer

    result = stripe_client.create_customer(email="test@example.com")

    mock_stripe_api.Customer.create.assert_called_once_with(
        email="test@example.com",
        name=None,
        metadata={},
    )
    assert result == mock_customer


def test_create_customer_with_all_fields(stripe_client, mock_stripe_api, mock_customer):
    """Test creating a customer with all fields."""
    mock_stripe_api.Customer.create.return_value = mock_customer

    result = stripe_client.create_customer(
        email="test@example.com",
        name="Test User",
        metadata={"user_id": "123"},
    )

    mock_stripe_api.Customer.create.assert_called_once_with(
        email="test@example.com",
        name="Test User",
        metadata={"user_id": "123"},
    )
    assert result == mock_customer


def test_create_customer_with_stripe_error(stripe_client, mock_stripe_api):
    """Test creating a customer when Stripe API fails."""
    mock_stripe_api.Customer.create.side_effect = StripeError("API Error")

    with pytest.raises(StripeError, match="API Error"):
        stripe_client.create_customer(email="test@example.com")


def test_get_customer_success(stripe_client, mock_stripe_api, mock_customer):
    """Test retrieving a customer by ID."""
    mock_stripe_api.Customer.retrieve.return_value = mock_customer

    result = stripe_client.get_customer("cus_test123")

    mock_stripe_api.Customer.retrieve.assert_called_once_with("cus_test123")
    assert result == mock_customer


def test_get_customer_not_found(stripe_client, mock_stripe_api):
    """Test retrieving a non-existent customer."""
    mock_stripe_api.Customer.retrieve.side_effect = StripeError("No such customer")

    with pytest.raises(StripeError, match="No such customer"):
        stripe_client.get_customer("cus_nonexistent")


def test_update_customer_with_email(stripe_client, mock_stripe_api, mock_customer):
    """Test updating a customer's email."""
    mock_stripe_api.Customer.modify.return_value = mock_customer

    result = stripe_client.update_customer("cus_test123", email="newemail@example.com")

    mock_stripe_api.Customer.modify.assert_called_once_with(
        "cus_test123",
        email="newemail@example.com",
    )
    assert result == mock_customer


def test_update_customer_with_all_fields(stripe_client, mock_stripe_api, mock_customer):
    """Test updating a customer with all fields."""
    mock_stripe_api.Customer.modify.return_value = mock_customer

    result = stripe_client.update_customer(
        "cus_test123",
        email="new@example.com",
        name="New Name",
        metadata={"updated": "true"},
    )

    mock_stripe_api.Customer.modify.assert_called_once_with(
        "cus_test123",
        email="new@example.com",
        name="New Name",
        metadata={"updated": "true"},
    )
    assert result == mock_customer


def test_update_customer_with_no_fields(stripe_client, mock_stripe_api, mock_customer):
    """Test updating a customer with no fields (no-op)."""
    mock_stripe_api.Customer.modify.return_value = mock_customer

    result = stripe_client.update_customer("cus_test123")

    mock_stripe_api.Customer.modify.assert_called_once_with("cus_test123")
    assert result == mock_customer


# =============================================================================
# Subscription Operations Tests
# =============================================================================


def test_get_subscription_success(stripe_client, mock_stripe_api, mock_subscription):
    """Test retrieving a subscription by ID."""
    mock_stripe_api.Subscription.retrieve.return_value = mock_subscription

    result = stripe_client.get_subscription("sub_test123")

    mock_stripe_api.Subscription.retrieve.assert_called_once_with("sub_test123")
    assert result == mock_subscription


def test_get_subscription_not_found(stripe_client, mock_stripe_api):
    """Test retrieving a non-existent subscription."""
    mock_stripe_api.Subscription.retrieve.side_effect = StripeError("No such subscription")

    with pytest.raises(StripeError, match="No such subscription"):
        stripe_client.get_subscription("sub_nonexistent")


def test_cancel_subscription_at_period_end(stripe_client, mock_stripe_api, mock_subscription):
    """Test canceling a subscription at period end."""
    mock_subscription.cancel_at_period_end = True
    mock_stripe_api.Subscription.modify.return_value = mock_subscription

    result = stripe_client.cancel_subscription("sub_test123", cancel_at_period_end=True)

    mock_stripe_api.Subscription.modify.assert_called_once_with(
        "sub_test123",
        cancel_at_period_end=True,
    )
    assert result.cancel_at_period_end is True


def test_cancel_subscription_immediately(stripe_client, mock_stripe_api, mock_subscription):
    """Test canceling a subscription immediately."""
    mock_subscription.status = "canceled"
    mock_stripe_api.Subscription.cancel.return_value = mock_subscription

    result = stripe_client.cancel_subscription("sub_test123", cancel_at_period_end=False)

    mock_stripe_api.Subscription.cancel.assert_called_once_with("sub_test123")
    assert result.status == "canceled"


def test_resume_subscription_success(stripe_client, mock_stripe_api, mock_subscription):
    """Test resuming a subscription that was set to cancel."""
    mock_subscription.cancel_at_period_end = False
    mock_stripe_api.Subscription.modify.return_value = mock_subscription

    result = stripe_client.resume_subscription("sub_test123")

    mock_stripe_api.Subscription.modify.assert_called_once_with(
        "sub_test123",
        cancel_at_period_end=False,
    )
    assert result.cancel_at_period_end is False


def test_update_subscription_with_default_proration(
    stripe_client, mock_stripe_api, mock_subscription
):
    """Test updating a subscription to a new price with default proration."""
    mock_stripe_api.Subscription.retrieve.return_value = mock_subscription
    mock_stripe_api.Subscription.modify.return_value = mock_subscription

    result = stripe_client.update_subscription("sub_test123", "price_new123")

    mock_stripe_api.Subscription.retrieve.assert_called_once_with("sub_test123")
    mock_stripe_api.Subscription.modify.assert_called_once_with(
        "sub_test123",
        items=[
            {
                "id": "si_test123",
                "price": "price_new123",
            }
        ],
        proration_behavior="create_prorations",
    )
    assert result == mock_subscription


def test_update_subscription_with_no_proration(
    stripe_client, mock_stripe_api, mock_subscription
):
    """Test updating a subscription without prorations."""
    mock_stripe_api.Subscription.retrieve.return_value = mock_subscription
    mock_stripe_api.Subscription.modify.return_value = mock_subscription

    result = stripe_client.update_subscription(
        "sub_test123",
        "price_new123",
        proration_behavior="none",
    )

    mock_stripe_api.Subscription.modify.assert_called_once_with(
        "sub_test123",
        items=[
            {
                "id": "si_test123",
                "price": "price_new123",
            }
        ],
        proration_behavior="none",
    )
    assert result == mock_subscription


# =============================================================================
# Checkout Operations Tests
# =============================================================================


def test_create_checkout_session_with_defaults(
    stripe_client, mock_stripe_api, mock_checkout_session
):
    """Test creating a checkout session with default parameters."""
    mock_stripe_api.checkout.Session.create.return_value = mock_checkout_session

    result = stripe_client.create_checkout_session(
        customer_id="cus_test123",
        price_id="price_test123",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )

    mock_stripe_api.checkout.Session.create.assert_called_once_with(
        customer="cus_test123",
        mode="subscription",
        line_items=[
            {
                "price": "price_test123",
                "quantity": 1,
            }
        ],
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
        allow_promotion_codes=True,
        metadata={},
    )
    assert result.url == "https://checkout.stripe.com/test123"


def test_create_checkout_session_with_custom_params(
    stripe_client, mock_stripe_api, mock_checkout_session
):
    """Test creating a checkout session with custom parameters."""
    mock_stripe_api.checkout.Session.create.return_value = mock_checkout_session

    result = stripe_client.create_checkout_session(
        customer_id="cus_test123",
        price_id="price_test123",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
        mode="payment",
        allow_promotion_codes=False,
        metadata={"order_id": "12345"},
    )

    mock_stripe_api.checkout.Session.create.assert_called_once_with(
        customer="cus_test123",
        mode="payment",
        line_items=[
            {
                "price": "price_test123",
                "quantity": 1,
            }
        ],
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
        allow_promotion_codes=False,
        metadata={"order_id": "12345"},
    )
    assert result == mock_checkout_session


def test_create_checkout_session_stripe_error(stripe_client, mock_stripe_api):
    """Test creating a checkout session when Stripe API fails."""
    mock_stripe_api.checkout.Session.create.side_effect = StripeError("Invalid price")

    with pytest.raises(StripeError, match="Invalid price"):
        stripe_client.create_checkout_session(
            customer_id="cus_test123",
            price_id="price_invalid",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )


# =============================================================================
# Billing Portal Tests
# =============================================================================


def test_create_billing_portal_session_success(
    stripe_client, mock_stripe_api, mock_billing_portal_session
):
    """Test creating a billing portal session."""
    mock_stripe_api.billing_portal.Session.create.return_value = mock_billing_portal_session

    result = stripe_client.create_billing_portal_session(
        customer_id="cus_test123",
        return_url="https://example.com/account",
    )

    mock_stripe_api.billing_portal.Session.create.assert_called_once_with(
        customer="cus_test123",
        return_url="https://example.com/account",
    )
    assert result.url == "https://billing.stripe.com/test123"


def test_create_billing_portal_session_stripe_error(stripe_client, mock_stripe_api):
    """Test creating a billing portal session when Stripe API fails."""
    mock_stripe_api.billing_portal.Session.create.side_effect = StripeError("Invalid customer")

    with pytest.raises(StripeError, match="Invalid customer"):
        stripe_client.create_billing_portal_session(
            customer_id="cus_invalid",
            return_url="https://example.com/account",
        )


# =============================================================================
# Product/Price Operations Tests
# =============================================================================


def test_list_prices_all_active(stripe_client, mock_stripe_api, mock_price):
    """Test listing all active prices."""
    mock_list = MagicMock()
    mock_list.__iter__ = MagicMock(return_value=iter([mock_price]))
    mock_stripe_api.Price.list.return_value = mock_list

    result = stripe_client.list_prices()

    mock_stripe_api.Price.list.assert_called_once_with(active=True)
    assert len(result) == 1
    assert result[0] == mock_price


def test_list_prices_for_product(stripe_client, mock_stripe_api, mock_price):
    """Test listing prices for a specific product."""
    mock_list = MagicMock()
    mock_list.__iter__ = MagicMock(return_value=iter([mock_price]))
    mock_stripe_api.Price.list.return_value = mock_list

    result = stripe_client.list_prices(product_id="prod_test123")

    mock_stripe_api.Price.list.assert_called_once_with(active=True, product="prod_test123")
    assert len(result) == 1


def test_list_prices_including_inactive(stripe_client, mock_stripe_api):
    """Test listing inactive prices."""
    mock_list = MagicMock()
    mock_list.__iter__ = MagicMock(return_value=iter([]))
    mock_stripe_api.Price.list.return_value = mock_list

    result = stripe_client.list_prices(active=False)

    mock_stripe_api.Price.list.assert_called_once_with(active=False)
    assert len(result) == 0


def test_get_price_success(stripe_client, mock_stripe_api, mock_price):
    """Test retrieving a price by ID."""
    mock_stripe_api.Price.retrieve.return_value = mock_price

    result = stripe_client.get_price("price_test123")

    mock_stripe_api.Price.retrieve.assert_called_once_with("price_test123")
    assert result == mock_price


def test_get_price_not_found(stripe_client, mock_stripe_api):
    """Test retrieving a non-existent price."""
    mock_stripe_api.Price.retrieve.side_effect = StripeError("No such price")

    with pytest.raises(StripeError, match="No such price"):
        stripe_client.get_price("price_nonexistent")


# =============================================================================
# Webhook Operations Tests
# =============================================================================


def test_construct_webhook_event_with_valid_signature(mock_stripe_api):
    """Test constructing a webhook event with valid signature."""
    mock_event = MagicMock()
    mock_event.type = "customer.subscription.created"
    mock_stripe_api.Webhook.construct_event.return_value = mock_event

    with patch("app.core.stripe.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test123"

        result = StripeClient.construct_webhook_event(
            payload=b'{"type": "customer.subscription.created"}',
            signature="t=123,v1=abc",
        )

        mock_stripe_api.Webhook.construct_event.assert_called_once_with(
            payload=b'{"type": "customer.subscription.created"}',
            sig_header="t=123,v1=abc",
            secret="whsec_test123",
        )
        assert result.type == "customer.subscription.created"


def test_construct_webhook_event_with_invalid_signature(mock_stripe_api):
    """Test constructing a webhook event with invalid signature."""
    mock_stripe_api.Webhook.construct_event.side_effect = SignatureVerificationError(
        "Invalid signature", "t=123,v1=invalid"
    )

    with patch("app.core.stripe.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test123"

        with pytest.raises(SignatureVerificationError, match="Invalid signature"):
            StripeClient.construct_webhook_event(
                payload=b'{"type": "customer.subscription.created"}',
                signature="t=123,v1=invalid",
            )


def test_construct_webhook_event_with_custom_secret(mock_stripe_api):
    """Test constructing a webhook event with custom secret."""
    mock_event = MagicMock()
    mock_stripe_api.Webhook.construct_event.return_value = mock_event

    result = StripeClient.construct_webhook_event(
        payload=b'{"type": "invoice.paid"}',
        signature="t=123,v1=abc",
        webhook_secret="whsec_custom123",
    )

    mock_stripe_api.Webhook.construct_event.assert_called_once_with(
        payload=b'{"type": "invoice.paid"}',
        sig_header="t=123,v1=abc",
        secret="whsec_custom123",
    )
    assert result == mock_event


def test_construct_webhook_event_without_secret_configured():
    """Test constructing a webhook event without secret configured."""
    with patch("app.core.stripe.settings") as mock_settings:
        # Remove the STRIPE_WEBHOOK_SECRET attribute
        mock_settings.STRIPE_WEBHOOK_SECRET = None

        with pytest.raises(ValueError, match="STRIPE_WEBHOOK_SECRET is not configured"):
            StripeClient.construct_webhook_event(
                payload=b'{"type": "customer.subscription.created"}',
                signature="t=123,v1=abc",
            )


# =============================================================================
# Client Initialization Tests
# =============================================================================


def test_stripe_client_initialization_success():
    """Test StripeClient initialization with valid configuration."""
    with patch("app.core.stripe.stripe") as mock_stripe:
        with patch("app.core.stripe.settings") as mock_settings:
            mock_stripe.api_key = "test_key"
            mock_settings.STRIPE_SECRET_KEY = "test_key"

            client = StripeClient()

            assert client is not None


def test_stripe_client_initialization_without_api_key():
    """Test StripeClient initialization without API key."""
    with patch("app.core.stripe.stripe") as mock_stripe:
        mock_stripe.api_key = None

        with pytest.raises(ValueError, match="STRIPE_SECRET_KEY is not configured"):
            StripeClient()


def test_get_publishable_key_success():
    """Test getting the publishable key."""
    with patch("app.core.stripe.stripe") as mock_stripe:
        with patch("app.core.stripe.settings") as mock_settings:
            mock_stripe.api_key = "test_secret_key"
            mock_settings.STRIPE_SECRET_KEY = "test_secret_key"
            mock_settings.STRIPE_PUBLISHABLE_KEY = "pk_test_123"

            client = StripeClient()
            key = client.get_publishable_key()

            assert key == "pk_test_123"


def test_get_publishable_key_not_configured():
    """Test getting publishable key when not configured."""
    with patch("app.core.stripe.stripe") as mock_stripe:
        with patch("app.core.stripe.settings") as mock_settings:
            mock_stripe.api_key = "test_secret_key"
            mock_settings.STRIPE_SECRET_KEY = "test_secret_key"
            # No STRIPE_PUBLISHABLE_KEY attribute

            client = StripeClient()
            key = client.get_publishable_key()

            assert key == ""


def test_get_stripe_client_singleton():
    """Test get_stripe_client returns singleton instance."""
    with patch("app.core.stripe.stripe") as mock_stripe:
        with patch("app.core.stripe.settings") as mock_settings:
            mock_stripe.api_key = "test_key"
            mock_settings.STRIPE_SECRET_KEY = "test_key"

            # Reset the global client
            import app.core.stripe as stripe_module

            stripe_module._stripe_client = None

            client1 = get_stripe_client()
            client2 = get_stripe_client()

            assert client1 is client2


def test_get_stripe_client_initialization_error():
    """Test get_stripe_client when initialization fails."""
    with patch("app.core.stripe.stripe") as mock_stripe:
        mock_stripe.api_key = None

        # Reset the global client
        import app.core.stripe as stripe_module

        stripe_module._stripe_client = None

        with pytest.raises(ValueError, match="STRIPE_SECRET_KEY is not configured"):
            get_stripe_client()
