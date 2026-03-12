"""
Tests for admin API Batches 2-4 endpoints.

Tests the following new admin endpoints:
- Credits: deduct, history, quota, quota/override, distribution, low-balance-users
- Billing: failed-payments, revenue, subscription-tiers (GET), subscription-tiers/{id} (PATCH)
- Organizations: edit, add member, remove member, change role, transfer ownership,
                 add credits, change tier, audit-log, stats
- Components: detail, create, edit, analytics, approve-for-library
- Jobs: priority, stats, queue-status, purge, workers
- Notifications: targeted, scheduled, templates (GET), templates (POST)
- API Keys: detail, usage, stats, rate-limit-violations
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.audit import AuditLog
from app.models.notification import Notification, NotificationType
from app.models.organization import (
    Organization,
    OrganizationAuditLog,
    OrganizationCreditBalance,
    OrganizationMember,
    OrganizationRole,
)
from app.models.reference_component import ComponentLibrary, ReferenceComponent
from app.models.subscription import (
    CreditBalance,
    CreditTransaction,
    SubscriptionTier,
    UsageQuota,
)
from app.models.user import Subscription
from tests.factories import (
    Counter,
    JobFactory,
    UserFactory,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_counters():
    """Reset factory counters before each test."""
    Counter.reset()


# =============================================================================
# Helper Factories
# =============================================================================


async def _create_credit_balance(
    db: AsyncSession,
    user_id: UUID,
    balance: int = 100,
    lifetime_earned: int = 200,
    lifetime_spent: int = 100,
) -> CreditBalance:
    """Create a CreditBalance for a user."""
    cb = CreditBalance(
        user_id=user_id,
        balance=balance,
        lifetime_earned=lifetime_earned,
        lifetime_spent=lifetime_spent,
    )
    db.add(cb)
    await db.commit()
    await db.refresh(cb)
    return cb


async def _create_credit_transaction(
    db: AsyncSession,
    user_id: UUID,
    balance_id: UUID,
    amount: int = -5,
    transaction_type: str = "admin_adjustment",
    description: str = "Test deduction",
    balance_before: int = 100,
    balance_after: int = 95,
) -> CreditTransaction:
    """Create a CreditTransaction."""
    tx = CreditTransaction(
        user_id=user_id,
        balance_id=balance_id,
        amount=amount,
        transaction_type=transaction_type,
        description=description,
        balance_before=balance_before,
        balance_after=balance_after,
        extra_data={"admin_email": "admin@example.com"},
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


async def _create_subscription(
    db: AsyncSession,
    user_id: UUID,
    tier: str = "free",
    status: str = "active",
) -> Subscription:
    """Create a Subscription for a user."""
    sub = Subscription(
        user_id=user_id,
        tier=tier,
        status=status,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def _create_organization(
    db: AsyncSession,
    owner_id: UUID,
    name: str = "Test Org",
    slug: str | None = None,
) -> Organization:
    """Create an Organization."""
    org = Organization(
        name=name,
        slug=slug or f"test-org-{uuid4().hex[:8]}",
        owner_id=owner_id,
        settings={"subscription_tier": "free"},
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _add_org_member(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    role: str = "member",
) -> OrganizationMember:
    """Add a member to an organization."""
    member = OrganizationMember(
        organization_id=org_id,
        user_id=user_id,
        role=role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def _create_reference_component(
    db: AsyncSession,
    user_id: UUID | None = None,
    name: str = "Test Component",
    category: str = "electronics",
) -> ReferenceComponent:
    """Create a ReferenceComponent."""
    comp = ReferenceComponent(
        user_id=user_id,
        name=name,
        category=category,
        source_type="uploaded",
        extraction_status="complete",
        dimensions={"length": 85, "width": 56, "height": 17, "unit": "mm"},
    )
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return comp


async def _create_api_key(
    db: AsyncSession,
    user_id: UUID,
    name: str = "Test Key",
    is_active: bool = True,
) -> APIKey:
    """Create an APIKey."""
    api_key, _raw = APIKey.create_with_key(
        user_id=user_id,
        name=name,
        scopes=["designs:read", "projects:read"],
    )
    api_key.is_active = is_active
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key


# =============================================================================
# US-10.5a: Credit Deduct Tests
# =============================================================================


class TestDeductUserCredits:
    """Tests for POST /admin/users/{user_id}/credits/deduct."""

    async def test_deduct_credits_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can deduct credits from a user."""
        user = await UserFactory.create(db_session)
        await _create_credit_balance(db_session, user.id, balance=100)

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/credits/deduct",
            json={"amount": 10, "reason": "Test deduction"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Deducted 10 credits"
        assert data["new_balance"] == 90

    async def test_deduct_credits_insufficient_balance(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns 400 if user has insufficient credits."""
        user = await UserFactory.create(db_session)
        await _create_credit_balance(db_session, user.id, balance=5)

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/credits/deduct",
            json={"amount": 10, "reason": "Too much"},
            headers=admin_headers,
        )

        assert response.status_code == 400
        assert "Insufficient balance" in response.json()["detail"]

    async def test_deduct_credits_no_balance_record(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns 404 if user has no credit balance record."""
        user = await UserFactory.create(db_session)

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/credits/deduct",
            json={"amount": 5, "reason": "No balance"},
            headers=admin_headers,
        )

        assert response.status_code == 404

    async def test_deduct_credits_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot deduct credits."""
        user = await UserFactory.create(db_session)
        response = await client.post(
            f"/api/v1/admin/users/{user.id}/credits/deduct",
            json={"amount": 5, "reason": "Nope"},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.5a: Credit History Tests
# =============================================================================


class TestCreditHistory:
    """Tests for GET /admin/users/{user_id}/credits/history."""

    async def test_get_credit_history_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get a user's credit transaction history."""
        user = await UserFactory.create(db_session)
        balance = await _create_credit_balance(db_session, user.id, balance=90)
        await _create_credit_transaction(db_session, user.id, balance.id)

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/credits/history",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["transaction_type"] == "admin_adjustment"
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_get_credit_history_pagination(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Credit history supports pagination."""
        user = await UserFactory.create(db_session)
        balance = await _create_credit_balance(db_session, user.id, balance=90)
        for i in range(5):
            await _create_credit_transaction(
                db_session,
                user.id,
                balance.id,
                amount=-(i + 1),
                balance_before=100 - i,
                balance_after=99 - i,
            )

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/credits/history?page=1&page_size=2",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_get_credit_history_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns empty list when user has no transactions."""
        user = await UserFactory.create(db_session)

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/credits/history",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_get_credit_history_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot view credit history."""
        user = await UserFactory.create(db_session)
        response = await client.get(
            f"/api/v1/admin/users/{user.id}/credits/history",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.5a: Quota Tests
# =============================================================================


class TestUserQuota:
    """Tests for GET /admin/users/{user_id}/quota."""

    async def test_get_user_quota_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get a user's quota usage."""
        user = await UserFactory.create(db_session)

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/quota",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user.id)
        assert "storage_used_bytes" in data
        assert "storage_limit_gb" in data
        assert "projects_count" in data
        assert "projects_limit" in data
        assert "designs_count" in data
        assert "designs_limit" in data
        assert "jobs_today" in data
        assert "jobs_limit" in data

    async def test_get_user_quota_with_usage_data(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Quota shows actual usage data when present."""
        user = await UserFactory.create(db_session)
        quota = UsageQuota(
            user_id=user.id,
            storage_used_bytes=1024 * 1024 * 500,  # 500 MB
            projects_count=3,
            active_jobs_count=1,
        )
        db_session.add(quota)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/quota",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["storage_used_bytes"] == 1024 * 1024 * 500
        assert data["projects_count"] == 3

    async def test_get_user_quota_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot view quota."""
        user = await UserFactory.create(db_session)
        response = await client.get(
            f"/api/v1/admin/users/{user.id}/quota",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.5a: Quota Override Tests
# =============================================================================


class TestQuotaOverride:
    """Tests for POST /admin/users/{user_id}/quota/override."""

    async def test_override_quota_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can override a user's quota limits."""
        user = await UserFactory.create(db_session)

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/quota/override",
            json={"storage_limit_gb": 50, "projects_limit": 100},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Quota override applied"
        assert data["user_id"] == str(user.id)
        assert data["overrides"]["storage_limit_gb"] == 50
        assert data["overrides"]["projects_limit"] == 100

    async def test_override_quota_user_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 when user doesn't exist."""
        response = await client.post(
            f"/api/v1/admin/users/{uuid4()}/quota/override",
            json={"storage_limit_gb": 50},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_override_quota_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot override quotas."""
        user = await UserFactory.create(db_session)
        response = await client.post(
            f"/api/v1/admin/users/{user.id}/quota/override",
            json={"storage_limit_gb": 50},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.5a: Credit Distribution Tests
# =============================================================================


class TestCreditDistribution:
    """Tests for GET /admin/credits/distribution."""

    async def test_get_credit_distribution_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get platform credit distribution."""
        user = await UserFactory.create(db_session)
        await _create_credit_balance(db_session, user.id, balance=50)

        response = await client.get(
            "/api/v1/admin/credits/distribution",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_credits_issued" in data
        assert "total_credits_used" in data
        assert "avg_balance" in data
        assert "total_users_with_balance" in data
        assert "distribution_by_tier" in data

    async def test_get_credit_distribution_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns zero values when no credit balances exist."""
        response = await client.get(
            "/api/v1/admin/credits/distribution",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_credits_issued"] == 0
        assert data["total_credits_used"] == 0

    async def test_get_credit_distribution_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view credit distribution."""
        response = await client.get(
            "/api/v1/admin/credits/distribution",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.5a: Low Balance Users Tests
# =============================================================================


class TestLowBalanceUsers:
    """Tests for GET /admin/credits/low-balance-users."""

    async def test_get_low_balance_users_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get users with low credit balances."""
        user = await UserFactory.create(db_session)
        await _create_credit_balance(db_session, user.id, balance=3)

        response = await client.get(
            "/api/v1/admin/credits/low-balance-users?threshold=10",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == 10
        assert data["total"] >= 1
        assert any(u["balance"] == 3 for u in data["items"])

    async def test_get_low_balance_users_pagination(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Low balance users supports pagination."""
        for _ in range(3):
            user = await UserFactory.create(db_session)
            await _create_credit_balance(db_session, user.id, balance=1)

        response = await client.get(
            "/api/v1/admin/credits/low-balance-users?threshold=10&page=1&page_size=2",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 3

    async def test_get_low_balance_users_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view low balance users."""
        response = await client.get(
            "/api/v1/admin/credits/low-balance-users",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.5b: Failed Payments Tests
# =============================================================================


class TestFailedPayments:
    """Tests for GET /admin/billing/failed-payments."""

    async def test_list_failed_payments_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can list failed payment records."""
        user = await UserFactory.create(db_session)
        log = AuditLog(
            user_id=user.id,
            action="payment_failed",
            resource_type="payment",
            status="failure",
            context={"amount_cents": 1999, "error": "Card declined", "retry_count": 1},
        )
        db_session.add(log)
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/billing/failed-payments",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(p["amount_cents"] == 1999 for p in data["items"])

    async def test_list_failed_payments_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns empty list when no failed payments exist."""
        response = await client.get(
            "/api/v1/admin/billing/failed-payments",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_failed_payments_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view failed payments."""
        response = await client.get(
            "/api/v1/admin/billing/failed-payments",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.5b: Billing Revenue Tests
# =============================================================================


class TestBillingRevenue:
    """Tests for GET /admin/billing/revenue."""

    async def test_get_billing_revenue_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can get billing revenue report."""
        response = await client.get(
            "/api/v1/admin/billing/revenue?period=30d",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "30d"
        assert "total_revenue_cents" in data
        assert "revenue_by_tier" in data
        assert "revenue_by_period" in data

    async def test_get_billing_revenue_7d_period(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Revenue works with 7d period."""
        response = await client.get(
            "/api/v1/admin/billing/revenue?period=7d",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["period"] == "7d"

    async def test_get_billing_revenue_invalid_period(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Invalid period returns 422."""
        response = await client.get(
            "/api/v1/admin/billing/revenue?period=invalid",
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_get_billing_revenue_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view revenue reports."""
        response = await client.get(
            "/api/v1/admin/billing/revenue",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.5b: Subscription Tiers Tests
# =============================================================================


class TestSubscriptionTiers:
    """Tests for GET /admin/subscription-tiers and PATCH /admin/subscription-tiers/{id}."""

    async def test_list_subscription_tiers_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
        subscription_tiers,
    ):
        """Admin can list all subscription tier definitions."""
        response = await client.get(
            "/api/v1/admin/subscription-tiers",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # free + pro from fixture
        slugs = {t["slug"] for t in data}
        assert "free" in slugs
        assert "pro" in slugs

    async def test_update_subscription_tier_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
        subscription_tiers,
    ):
        """Admin can update a subscription tier."""
        # Get the pro tier
        tiers = subscription_tiers
        pro_tier = next(t for t in tiers if t.slug == "pro")

        response = await client.patch(
            f"/api/v1/admin/subscription-tiers/{pro_tier.id}",
            json={"monthly_credits": 2000, "price_monthly_cents": 2999},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["monthly_credits"] == 2000
        assert data["price_monthly_cents"] == 2999

    async def test_update_subscription_tier_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 for non-existent tier."""
        response = await client.patch(
            f"/api/v1/admin/subscription-tiers/{uuid4()}",
            json={"monthly_credits": 500},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_list_tiers_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot list tiers."""
        response = await client.get(
            "/api/v1/admin/subscription-tiers",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.6: Edit Organization Tests
# =============================================================================


class TestEditOrganization:
    """Tests for PATCH /admin/organizations/{org_id}."""

    async def test_edit_organization_name(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can edit an organization's name."""
        user = await UserFactory.create(db_session)
        org = await _create_organization(db_session, user.id, name="Old Name")
        await _add_org_member(db_session, org.id, user.id, "owner")

        response = await client.patch(
            f"/api/v1/admin/organizations/{org.id}",
            json={"name": "New Name"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    async def test_edit_organization_settings(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can update organization settings."""
        user = await UserFactory.create(db_session)
        org = await _create_organization(db_session, user.id)

        response = await client.patch(
            f"/api/v1/admin/organizations/{org.id}",
            json={"settings": {"require_2fa": True}},
            headers=admin_headers,
        )

        assert response.status_code == 200

    async def test_edit_organization_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 for non-existent organization."""
        response = await client.patch(
            f"/api/v1/admin/organizations/{uuid4()}",
            json={"name": "Nope"},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_edit_organization_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot edit organizations."""
        user = await UserFactory.create(db_session)
        org = await _create_organization(db_session, user.id)
        response = await client.patch(
            f"/api/v1/admin/organizations/{org.id}",
            json={"name": "Nope"},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.6: Add Organization Member Tests
# =============================================================================


class TestAddOrganizationMember:
    """Tests for POST /admin/organizations/{org_id}/members."""

    async def test_add_member_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can add a member to an organization."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        new_user = await UserFactory.create(db_session)

        response = await client.post(
            f"/api/v1/admin/organizations/{org.id}/members",
            json={"user_id": str(new_user.id), "role": "member"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(new_user.id)
        assert data["role"] == "member"

    async def test_add_member_already_exists(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns 409 if user is already a member."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        await _add_org_member(db_session, org.id, owner.id, "owner")

        response = await client.post(
            f"/api/v1/admin/organizations/{org.id}/members",
            json={"user_id": str(owner.id), "role": "member"},
            headers=admin_headers,
        )

        assert response.status_code == 409

    async def test_add_member_org_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns 404 if organization doesn't exist."""
        user = await UserFactory.create(db_session)
        response = await client.post(
            f"/api/v1/admin/organizations/{uuid4()}/members",
            json={"user_id": str(user.id), "role": "member"},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_add_member_user_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns 404 if user doesn't exist."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)

        response = await client.post(
            f"/api/v1/admin/organizations/{org.id}/members",
            json={"user_id": str(uuid4()), "role": "member"},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_add_member_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot add members."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        response = await client.post(
            f"/api/v1/admin/organizations/{org.id}/members",
            json={"user_id": str(uuid4()), "role": "member"},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.6: Remove Organization Member Tests
# =============================================================================


class TestRemoveOrganizationMember:
    """Tests for DELETE /admin/organizations/{org_id}/members/{user_id}."""

    async def test_remove_member_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can remove a member from an organization."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        member_user = await UserFactory.create(db_session)
        await _add_org_member(db_session, org.id, member_user.id, "member")

        response = await client.delete(
            f"/api/v1/admin/organizations/{org.id}/members/{member_user.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Member removed"

    async def test_remove_member_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns 404 if membership doesn't exist."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)

        response = await client.delete(
            f"/api/v1/admin/organizations/{org.id}/members/{uuid4()}",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_remove_member_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot remove members."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        response = await client.delete(
            f"/api/v1/admin/organizations/{org.id}/members/{uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.6: Change Organization Member Role Tests
# =============================================================================


class TestChangeOrgMemberRole:
    """Tests for PATCH /admin/organizations/{org_id}/members/{user_id}/role."""

    async def test_change_role_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can change a member's role."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        member_user = await UserFactory.create(db_session)
        await _add_org_member(db_session, org.id, member_user.id, "member")

        response = await client.patch(
            f"/api/v1/admin/organizations/{org.id}/members/{member_user.id}/role",
            json={"role": "admin"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

    async def test_change_role_member_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns 404 if membership doesn't exist."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)

        response = await client.patch(
            f"/api/v1/admin/organizations/{org.id}/members/{uuid4()}/role",
            json={"role": "admin"},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_change_role_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot change roles."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        response = await client.patch(
            f"/api/v1/admin/organizations/{org.id}/members/{uuid4()}/role",
            json={"role": "admin"},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.6: Transfer Organization Ownership Tests
# =============================================================================


class TestTransferOrgOwnership:
    """Tests for POST /admin/organizations/{org_id}/transfer-ownership."""

    async def test_transfer_ownership_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can transfer organization ownership."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        await _add_org_member(db_session, org.id, owner.id, "owner")

        new_owner = await UserFactory.create(db_session)
        await _add_org_member(db_session, org.id, new_owner.id, "admin")

        response = await client.post(
            f"/api/v1/admin/organizations/{org.id}/transfer-ownership",
            json={"new_owner_id": str(new_owner.id)},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Ownership transferred"

    async def test_transfer_ownership_org_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns 404 if organization doesn't exist."""
        user = await UserFactory.create(db_session)
        response = await client.post(
            f"/api/v1/admin/organizations/{uuid4()}/transfer-ownership",
            json={"new_owner_id": str(user.id)},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_transfer_ownership_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot transfer ownership."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        response = await client.post(
            f"/api/v1/admin/organizations/{org.id}/transfer-ownership",
            json={"new_owner_id": str(uuid4())},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.6: Add Organization Credits Tests
# =============================================================================


class TestAddOrgCredits:
    """Tests for POST /admin/organizations/{org_id}/credits/add."""

    async def test_add_credits_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can add credits to an organization."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)

        response = await client.post(
            f"/api/v1/admin/organizations/{org.id}/credits/add",
            json={"amount": 500, "reason": "Bonus credits"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Added 500 credits to organization"
        assert data["new_balance"] == 500

    async def test_add_credits_org_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 if organization doesn't exist."""
        response = await client.post(
            f"/api/v1/admin/organizations/{uuid4()}/credits/add",
            json={"amount": 100, "reason": "Test"},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_add_credits_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot add org credits."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        response = await client.post(
            f"/api/v1/admin/organizations/{org.id}/credits/add",
            json={"amount": 100, "reason": "Nope"},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.6: Change Organization Tier Tests
# =============================================================================


class TestChangeOrgTier:
    """Tests for PATCH /admin/organizations/{org_id}/tier."""

    async def test_change_tier_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can change an organization's tier."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)

        response = await client.patch(
            f"/api/v1/admin/organizations/{org.id}/tier",
            json={"tier": "pro"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Organization tier updated to pro"

    async def test_change_tier_org_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 if organization doesn't exist."""
        response = await client.patch(
            f"/api/v1/admin/organizations/{uuid4()}/tier",
            json={"tier": "pro"},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_change_tier_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot change org tier."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        response = await client.patch(
            f"/api/v1/admin/organizations/{org.id}/tier",
            json={"tier": "pro"},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.6: Organization Audit Log Tests
# =============================================================================


class TestOrgAuditLog:
    """Tests for GET /admin/organizations/{org_id}/audit-log."""

    async def test_get_audit_log_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get an organization's audit log."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)

        # Create audit entries
        for i in range(3):
            log = OrganizationAuditLog(
                organization_id=org.id,
                user_id=owner.id,
                action=f"test_action_{i}",
                resource_type="settings",
                details={"change": i},
            )
            db_session.add(log)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/organizations/{org.id}/audit-log",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_get_audit_log_pagination(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Audit log supports pagination."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)

        for i in range(5):
            log = OrganizationAuditLog(
                organization_id=org.id,
                user_id=owner.id,
                action=f"action_{i}",
            )
            db_session.add(log)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/organizations/{org.id}/audit-log?page=1&page_size=2",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_get_audit_log_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot view org audit logs."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        response = await client.get(
            f"/api/v1/admin/organizations/{org.id}/audit-log",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.6: Organization Stats Tests
# =============================================================================


class TestOrgStats:
    """Tests for GET /admin/organizations/{org_id}/stats."""

    async def test_get_org_stats_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get organization statistics."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        await _add_org_member(db_session, org.id, owner.id, "owner")

        response = await client.get(
            f"/api/v1/admin/organizations/{org.id}/stats",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["member_count"] >= 1
        assert "project_count" in data
        assert "design_count" in data
        assert "tier" in data
        assert "credit_balance" in data

    async def test_get_org_stats_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 if organization doesn't exist."""
        response = await client.get(
            f"/api/v1/admin/organizations/{uuid4()}/stats",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_get_org_stats_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot view org stats."""
        owner = await UserFactory.create(db_session)
        org = await _create_organization(db_session, owner.id)
        response = await client.get(
            f"/api/v1/admin/organizations/{org.id}/stats",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.7: Component Detail Tests
# =============================================================================


class TestComponentDetail:
    """Tests for GET /admin/components/{component_id}."""

    async def test_get_component_detail_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get component details."""
        comp = await _create_reference_component(db_session, name="Raspberry Pi 4")

        response = await client.get(
            f"/api/v1/admin/components/{comp.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Raspberry Pi 4"
        assert data["category"] == "electronics"

    async def test_get_component_detail_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 for non-existent component."""
        response = await client.get(
            f"/api/v1/admin/components/{uuid4()}",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_get_component_detail_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot view component details."""
        comp = await _create_reference_component(db_session)
        response = await client.get(
            f"/api/v1/admin/components/{comp.id}",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.7: Create Component Tests
# =============================================================================


class TestCreateComponent:
    """Tests for POST /admin/components."""

    async def test_create_component_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can create a new component."""
        response = await client.post(
            "/api/v1/admin/components",
            json={
                "name": "Arduino Uno",
                "category": "microcontroller",
                "manufacturer": "Arduino",
                "model_number": "A000066",
            },
            headers=admin_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Arduino Uno"
        assert data["category"] == "microcontroller"

    async def test_create_component_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot create components."""
        response = await client.post(
            "/api/v1/admin/components",
            json={"name": "Test", "category": "test"},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.7: Edit Component Tests
# =============================================================================


class TestEditComponent:
    """Tests for PATCH /admin/components/{component_id}."""

    async def test_edit_component_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can edit a component."""
        comp = await _create_reference_component(db_session, name="Old Name")

        response = await client.patch(
            f"/api/v1/admin/components/{comp.id}",
            json={"name": "New Name", "manufacturer": "ACME Corp"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    async def test_edit_component_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 for non-existent component."""
        response = await client.patch(
            f"/api/v1/admin/components/{uuid4()}",
            json={"name": "Test"},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_edit_component_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot edit components."""
        comp = await _create_reference_component(db_session)
        response = await client.patch(
            f"/api/v1/admin/components/{comp.id}",
            json={"name": "Nope"},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.7: Component Analytics Tests
# =============================================================================


class TestComponentAnalytics:
    """Tests for GET /admin/components/analytics."""

    async def test_get_component_analytics_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get component analytics."""
        await _create_reference_component(db_session, name="Comp 1")
        await _create_reference_component(db_session, name="Comp 2")

        response = await client.get(
            "/api/v1/admin/components/analytics",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_components" in data
        assert "verified_count" in data
        assert "by_category" in data
        assert "by_source_type" in data

    async def test_get_component_analytics_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view component analytics."""
        response = await client.get(
            "/api/v1/admin/components/analytics",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.7: Approve Component for Library Tests
# =============================================================================


class TestApproveComponentForLibrary:
    """Tests for POST /admin/components/{component_id}/approve-for-library."""

    async def test_approve_for_library_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can approve a component for the library."""
        comp = await _create_reference_component(db_session, name="Quality Component")

        response = await client.post(
            f"/api/v1/admin/components/{comp.id}/approve-for-library",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Component approved and added to library"

    async def test_approve_component_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 for non-existent component."""
        response = await client.post(
            f"/api/v1/admin/components/{uuid4()}/approve-for-library",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_approve_component_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot approve components."""
        comp = await _create_reference_component(db_session)
        response = await client.post(
            f"/api/v1/admin/components/{comp.id}/approve-for-library",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.8: Change Job Priority Tests
# =============================================================================


class TestChangeJobPriority:
    """Tests for PATCH /admin/jobs/{job_id}/priority."""

    async def test_change_priority_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can change a job's priority."""
        user = await UserFactory.create(db_session)
        job = await JobFactory.create(db_session, user=user)

        response = await client.patch(
            f"/api/v1/admin/jobs/{job.id}/priority",
            json={"priority": 1},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job.id)

    async def test_change_priority_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 for non-existent job."""
        response = await client.patch(
            f"/api/v1/admin/jobs/{uuid4()}/priority",
            json={"priority": 1},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_change_priority_invalid_value(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Invalid priority value returns 422."""
        response = await client.patch(
            f"/api/v1/admin/jobs/{uuid4()}/priority",
            json={"priority": 99},
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_change_priority_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot change job priority."""
        user = await UserFactory.create(db_session)
        job = await JobFactory.create(db_session, user=user)
        response = await client.patch(
            f"/api/v1/admin/jobs/{job.id}/priority",
            json={"priority": 1},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.8: Job Stats Tests
# =============================================================================


class TestJobStats:
    """Tests for GET /admin/jobs/stats."""

    async def test_get_job_stats_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get aggregate job statistics."""
        user = await UserFactory.create(db_session)
        await JobFactory.create(db_session, user=user)
        await JobFactory.create_completed(db_session, user=user)
        await JobFactory.create_failed(db_session, user=user)

        response = await client.get(
            "/api/v1/admin/jobs/stats",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert "by_status" in data
        assert "by_type" in data
        assert "success_rate" in data
        assert "failure_rate" in data

    async def test_get_job_stats_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns zeroed stats when no jobs exist."""
        response = await client.get(
            "/api/v1/admin/jobs/stats",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["success_rate"] == 0.0
        assert data["failure_rate"] == 0.0

    async def test_get_job_stats_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view job stats."""
        response = await client.get(
            "/api/v1/admin/jobs/stats",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.8: Queue Status Tests
# =============================================================================


class TestQueueStatus:
    """Tests for GET /admin/jobs/queue-status."""

    async def test_get_queue_status_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can get job queue status."""
        response = await client.get(
            "/api/v1/admin/jobs/queue-status",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "pending_count" in data
        assert "running_count" in data
        assert "queued_count" in data
        assert "workers_active" in data

    async def test_get_queue_status_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view queue status."""
        response = await client.get(
            "/api/v1/admin/jobs/queue-status",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.8: Purge Old Jobs Tests
# =============================================================================


class TestPurgeOldJobs:
    """Tests for DELETE /admin/jobs/purge."""

    async def test_purge_old_jobs_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can purge old jobs."""
        response = await client.delete(
            "/api/v1/admin/jobs/purge?older_than_days=30",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "purged_count" in data
        assert data["older_than_days"] == 30

    async def test_purge_old_jobs_default_days(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Purge defaults to 30 days."""
        response = await client.delete(
            "/api/v1/admin/jobs/purge",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.json()["older_than_days"] == 30

    async def test_purge_old_jobs_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot purge jobs."""
        response = await client.delete(
            "/api/v1/admin/jobs/purge",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.8: Worker Status Tests
# =============================================================================


class TestWorkerStatus:
    """Tests for GET /admin/jobs/workers."""

    async def test_get_worker_status_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can get worker status."""
        response = await client.get(
            "/api/v1/admin/jobs/workers",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "name" in data[0]
        assert "status" in data[0]

    async def test_get_worker_status_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view worker status."""
        response = await client.get(
            "/api/v1/admin/jobs/workers",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.9: Targeted Notification Tests
# =============================================================================


class TestTargetedNotification:
    """Tests for POST /admin/notifications/targeted."""

    async def test_send_targeted_by_role(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can send targeted notification by role."""
        # Create active users
        for _ in range(3):
            await UserFactory.create(db_session, role="user")

        response = await client.post(
            "/api/v1/admin/notifications/targeted",
            json={
                "title": "Important Update",
                "message": "This is a test notification.",
                "target_type": "role",
                "target_value": "user",
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sent_count"] >= 3
        assert data["target_type"] == "role"
        assert data["target_value"] == "user"

    async def test_send_targeted_invalid_target_type(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Invalid target_type returns 422."""
        response = await client.post(
            "/api/v1/admin/notifications/targeted",
            json={
                "title": "Test",
                "message": "Test message",
                "target_type": "invalid",
                "target_value": "whatever",
            },
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_send_targeted_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot send targeted notifications."""
        response = await client.post(
            "/api/v1/admin/notifications/targeted",
            json={
                "title": "Test",
                "message": "Test",
                "target_type": "role",
                "target_value": "user",
            },
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.9: Scheduled Notification Tests
# =============================================================================


class TestScheduledNotification:
    """Tests for POST /admin/notifications/scheduled."""

    async def test_schedule_notification_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can schedule a notification."""
        future = (datetime.now(tz=UTC) + timedelta(days=1)).isoformat()

        response = await client.post(
            "/api/v1/admin/notifications/scheduled",
            json={
                "title": "Maintenance Window",
                "message": "Scheduled maintenance on Saturday.",
                "scheduled_at": future,
                "recipient_type": "all",
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["scheduled"] is True
        assert data["title"] == "Maintenance Window"

    async def test_schedule_notification_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot schedule notifications."""
        future = (datetime.now(tz=UTC) + timedelta(days=1)).isoformat()
        response = await client.post(
            "/api/v1/admin/notifications/scheduled",
            json={
                "title": "Test",
                "message": "Test",
                "scheduled_at": future,
            },
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.9: Notification Templates Tests
# =============================================================================


class TestNotificationTemplates:
    """Tests for GET/POST /admin/notifications/templates."""

    async def test_list_templates_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can list notification templates."""
        response = await client.get(
            "/api/v1/admin/notifications/templates",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 4  # welcome, credit_low, maintenance, feature_announcement
        ids = {t["id"] for t in data}
        assert "welcome" in ids
        assert "credit_low" in ids

    async def test_create_template_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can create a notification template."""
        response = await client.post(
            "/api/v1/admin/notifications/templates",
            json={
                "name": "Password Reset",
                "subject": "Reset your password",
                "body_template": "Hi {{user_name}}, click here to reset.",
                "variables": ["user_name"],
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Template created"
        assert data["template"]["name"] == "Password Reset"
        assert data["template"]["id"] == "password_reset"

    async def test_list_templates_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot list templates."""
        response = await client.get(
            "/api/v1/admin/notifications/templates",
            headers=auth_headers,
        )
        assert response.status_code == 403

    async def test_create_template_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot create templates."""
        response = await client.post(
            "/api/v1/admin/notifications/templates",
            json={
                "name": "Test",
                "subject": "Test",
                "body_template": "Test",
            },
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.11: API Key Detail Tests
# =============================================================================


class TestAPIKeyDetail:
    """Tests for GET /admin/api-keys/{key_id}."""

    async def test_get_api_key_detail_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get API key details."""
        user = await UserFactory.create(db_session)
        api_key = await _create_api_key(db_session, user.id, name="My Key")

        response = await client.get(
            f"/api/v1/admin/api-keys/{api_key.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Key"
        assert data["user_id"] == str(user.id)
        assert "scopes" in data
        assert data["is_active"] is True

    async def test_get_api_key_detail_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 for non-existent API key."""
        response = await client.get(
            f"/api/v1/admin/api-keys/{uuid4()}",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_get_api_key_detail_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot view API key details."""
        user = await UserFactory.create(db_session)
        api_key = await _create_api_key(db_session, user.id)
        response = await client.get(
            f"/api/v1/admin/api-keys/{api_key.id}",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.11: API Key Usage Tests
# =============================================================================


class TestAPIKeyUsage:
    """Tests for GET /admin/api-keys/{key_id}/usage."""

    async def test_get_api_key_usage_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get API key usage stats."""
        user = await UserFactory.create(db_session)
        api_key = await _create_api_key(db_session, user.id)

        response = await client.get(
            f"/api/v1/admin/api-keys/{api_key.id}/usage",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["key_id"] == str(api_key.id)
        assert "total_requests" in data
        assert "requests_by_endpoint" in data
        assert "requests_by_day" in data

    async def test_get_api_key_usage_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 for non-existent API key."""
        response = await client.get(
            f"/api/v1/admin/api-keys/{uuid4()}/usage",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_get_api_key_usage_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot view API key usage."""
        user = await UserFactory.create(db_session)
        api_key = await _create_api_key(db_session, user.id)
        response = await client.get(
            f"/api/v1/admin/api-keys/{api_key.id}/usage",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.11: API Key Stats Tests
# =============================================================================


class TestAPIKeyStats:
    """Tests for GET /admin/api-keys/stats."""

    async def test_get_api_key_stats_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can get aggregate API key stats."""
        user = await UserFactory.create(db_session)
        await _create_api_key(db_session, user.id, name="Active Key", is_active=True)
        await _create_api_key(db_session, user.id, name="Revoked Key", is_active=False)

        response = await client.get(
            "/api/v1/admin/api-keys/stats",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_keys"] >= 2
        assert data["active_keys"] >= 1
        assert data["revoked_keys"] >= 1
        assert "expired_keys" in data
        assert "total_requests_24h" in data

    async def test_get_api_key_stats_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns zero stats when no API keys exist."""
        response = await client.get(
            "/api/v1/admin/api-keys/stats",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_keys"] == 0
        assert data["active_keys"] == 0

    async def test_get_api_key_stats_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view API key stats."""
        response = await client.get(
            "/api/v1/admin/api-keys/stats",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# US-10.11: Rate Limit Violations Tests
# =============================================================================


class TestRateLimitViolations:
    """Tests for GET /admin/api-keys/rate-limit-violations."""

    async def test_get_rate_limit_violations_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can list rate limit violations."""
        user = await UserFactory.create(db_session)
        log = AuditLog(
            user_id=user.id,
            action="rate_limit_exceeded",
            resource_type="api",
            status="blocked",
            context={"key_prefix": "apd_test", "endpoint": "/api/v1/designs"},
        )
        db_session.add(log)
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/api-keys/rate-limit-violations",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(v["key_prefix"] == "apd_test" for v in data["items"])

    async def test_get_rate_limit_violations_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns empty list when no violations exist."""
        response = await client.get(
            "/api/v1/admin/api-keys/rate-limit-violations",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_get_rate_limit_violations_pagination(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Rate limit violations supports pagination."""
        user = await UserFactory.create(db_session)
        for i in range(5):
            log = AuditLog(
                user_id=user.id,
                action="rate_limit_exceeded",
                resource_type="api",
                status="blocked",
                context={"endpoint": f"/api/v1/endpoint_{i}"},
            )
            db_session.add(log)
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/api-keys/rate-limit-violations?page=1&page_size=2",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5

    async def test_get_rate_limit_violations_forbidden_non_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Non-admin users cannot view rate limit violations."""
        response = await client.get(
            "/api/v1/admin/api-keys/rate-limit-violations",
            headers=auth_headers,
        )
        assert response.status_code == 403
