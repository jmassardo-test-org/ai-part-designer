# Epic 10: Admin Panel — Development Specification

**Created:** 2026-02-27  
**Status:** Actionable Development Plan  
**Target:** Complete all 17 user stories for full platform management  

---

## Architecture Overview

### Backend Structure
- **Existing file:** `backend/app/api/v1/admin.py` (5,899 lines — already has ~70 endpoints)
- **Refactoring needed:** Split into sub-modules under `backend/app/api/v1/admin/` package
- **Models:** Most exist. New models needed: `Coupon`, `ContentArticle`, `FAQ`, `SecurityEvent`
- **Schemas:** New Pydantic schemas needed per batch under `backend/app/schemas/admin/`

### Frontend Structure
- **Existing:** `AdminDashboard.tsx` (~5,000 lines, 15 inline tab components)
- **Existing tabs:** analytics, users, projects, designs, templates, jobs, moderation, subscriptions, organizations, components, notifications, storage, audit, apikeys, system
- **API client:** `frontend/src/lib/api/admin.ts` (minimal — 3 functions)

### Shared Patterns (All Endpoints)
- All admin routes require `require_admin` dependency
- All mutations create audit log entries
- All list endpoints support pagination: `?page=1&page_size=20`
- All list endpoints support sorting: `?sort_by=created_at&sort_order=desc`
- All responses use Pydantic `model_validate` with `from_attributes=True`
- All inputs validated with Pydantic; sanitized before DB operations
- Rate limiting applied via existing middleware
- Security event logging for sensitive operations (role changes, deletions, impersonation)

---

## Batch 1: Quick Wins — Complete "Mostly Done" Stories
**Complexity:** S | **Estimate:** 2–3 days | **Dependencies:** None

Finish US-10.1, US-10.2, US-10.3, US-10.4 — the 80%+ complete stories.

### Batch 1A: US-10.1 Analytics Gaps

**Backend — New Endpoints:**

```
GET /api/v1/admin/analytics/revenue?period=30d
```
```python
# Response: RevenueAnalyticsResponse
{
    "mrr": 12500.00,
    "arr": 150000.00,
    "churn_rate": 2.3,
    "upgrades": 15,
    "downgrades": 3,
    "new_subscriptions": 42,
    "cancelled_subscriptions": 5,
    "revenue_by_tier": [
        {"tier": "pro", "revenue": 8500.00, "subscribers": 170},
        {"tier": "enterprise", "revenue": 4000.00, "subscribers": 20}
    ],
    "period": "30d",
    "trend": [{"date": "2026-02-01", "revenue": 400.00}, ...]
}
```

```
GET /api/v1/admin/analytics/ai-costs?period=30d
```
```python
# Response: AICostAnalyticsResponse
{
    "total_cost": 342.50,
    "cost_by_provider": [
        {"provider": "openai", "cost": 280.00, "requests": 1420},
        {"provider": "ollama", "cost": 62.50, "requests": 3200}
    ],
    "cost_per_generation": 0.074,
    "daily_trend": [{"date": "2026-02-01", "cost": 11.20}, ...],
    "period": "30d"
}
```

```
GET /api/v1/admin/analytics/export?type={users|generations|revenue|jobs}&format={csv|xlsx}
```
```python
# Response: StreamingResponse with Content-Disposition header
# Content-Type: text/csv or application/vnd.openxmlformats-officedml.spreadsheetml.sheet
```

**Backend Implementation Notes:**
- Revenue: Query `Subscription` + `Payment` models, aggregate by tier/period
- AI costs: Query `Job` model with `job_type='ai_generation'`, estimate cost from token counts stored in `result_metadata`
- Export: Use Python `csv` module for CSV; `openpyxl` for Excel (add to requirements.txt)

**Frontend Changes:**
- `AdminDashboard.tsx` → `AnalyticsTab`: Add revenue chart section, AI cost section, export button
- Add `adminApi.getRevenueAnalytics(period)`, `adminApi.getAICostAnalytics(period)`, `adminApi.exportAnalytics(type, format)` to `frontend/src/lib/api/admin.ts`

**Tests:**
```
backend/tests/api/test_admin_analytics.py
  - test_revenue_analytics_returns_mrr
  - test_revenue_analytics_filters_by_period
  - test_revenue_analytics_requires_admin
  - test_ai_cost_analytics_returns_provider_breakdown
  - test_export_csv_returns_streaming_response
  - test_export_xlsx_returns_streaming_response
  - test_export_invalid_type_returns_422
  - test_export_requires_admin

frontend/src/lib/api/admin.test.ts (expand)
  - test_get_revenue_analytics
  - test_get_ai_cost_analytics
  - test_export_analytics_csv
```

---

### Batch 1B: US-10.2 User Management Gaps

**Backend — New Endpoints:**

```
POST /api/v1/admin/users/{id}/force-email-verify
```
```python
# Request: (no body)
# Response: {"message": "Email verified", "user_id": "...", "verified_at": "..."}
```

```
GET /api/v1/admin/users/{id}/login-history?page=1&page_size=20
```
```python
# Response: LoginHistoryResponse
{
    "items": [
        {
            "id": "uuid",
            "timestamp": "2026-02-27T10:00:00Z",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
            "location": "San Francisco, CA",
            "success": true,
            "method": "password"  # password | oauth_github | oauth_google
        }
    ],
    "total": 150,
    "page": 1,
    "page_size": 20
}
```

```
GET /api/v1/admin/users/{id}/activity?page=1&page_size=20
```
```python
# Response: UserActivityResponse
{
    "items": [
        {
            "action": "design.created",
            "resource_type": "design",
            "resource_id": "uuid",
            "resource_name": "My Gear",
            "timestamp": "2026-02-27T09:30:00Z",
            "details": {}
        }
    ],
    "total": 85,
    "page": 1,
    "page_size": 20
}
```

```
GET /api/v1/admin/users/{id}/oauth-connections
```
```python
# Response: OAuthConnectionsResponse
{
    "connections": [
        {
            "provider": "github",
            "provider_user_id": "12345",
            "connected_at": "2026-01-15T00:00:00Z",
            "last_used": "2026-02-27T08:00:00Z"
        }
    ]
}
```

```
POST /api/v1/admin/users/bulk-action
```
```python
# Request: BulkUserActionRequest
{
    "user_ids": ["uuid1", "uuid2", ...],
    "action": "suspend" | "unsuspend" | "change_role" | "delete",
    "params": {"role": "moderator"}  # optional, depends on action
}
# Response: BulkActionResponse
{
    "success_count": 8,
    "failure_count": 2,
    "failures": [{"user_id": "uuid", "error": "Cannot suspend admin"}],
    "action": "suspend"
}
```

```
GET /api/v1/admin/users/export?format=csv
```
```python
# Response: StreamingResponse (CSV)
# Columns: id, email, display_name, role, tier, status, created_at, last_login
```

**Backend Implementation Notes:**
- Login history: Query `AuditLog` where `action='auth.login'` filtered by user_id
- Activity: Query `AuditLog` filtered by user_id, all non-auth actions
- OAuth connections: Query `OAuthAccount` model (already exists)
- Force email verify: Set `user.email_verified = True`, `user.email_verified_at = utcnow()`
- Bulk actions: Iterate user_ids in transaction, collect successes/failures

**Frontend Changes:**
- `UsersTab`: Add "Login History" and "Activity" sections to user detail modal
- Add "OAuth Connections" section to user detail
- Add "Bulk Actions" toolbar (checkboxes on user list, action dropdown)
- Add "Export CSV" button to user list header

**Tests:**
```
backend/tests/api/test_admin_users.py
  - test_force_email_verify_sets_verified
  - test_force_email_verify_already_verified
  - test_login_history_returns_entries
  - test_login_history_pagination
  - test_user_activity_returns_audit_entries
  - test_user_activity_filters_by_user
  - test_oauth_connections_returns_providers
  - test_oauth_connections_empty_for_password_user
  - test_bulk_suspend_users
  - test_bulk_action_cannot_suspend_admin
  - test_bulk_action_requires_admin
  - test_export_users_csv
  - test_export_users_csv_columns
```

---

### Batch 1C: US-10.3 Projects/Designs Gaps

**Backend — New Endpoints:**

```
POST /api/v1/admin/designs/{id}/transfer
```
```python
# Request: {"target_user_id": "uuid"}
# Response: {"message": "Design transferred", "design_id": "...", "new_owner_id": "..."}
```

```
GET /api/v1/admin/designs/{id}/versions?page=1&page_size=20
```
```python
# Response: DesignVersionHistoryResponse
{
    "items": [
        {
            "version": 3,
            "created_at": "2026-02-27T10:00:00Z",
            "change_summary": "Updated dimensions",
            "parameters": {"width": 100, "height": 50},
            "file_url": "/files/design-v3.step",
            "created_by": "uuid"
        }
    ],
    "total": 3,
    "design_id": "uuid"
}
```

```
POST /api/v1/admin/projects/bulk-action
```
```python
# Request: {"project_ids": [...], "action": "delete" | "transfer", "params": {"target_user_id": "uuid"}}
# Response: BulkActionResponse (same shape as users)
```

```
POST /api/v1/admin/designs/bulk-action
```
```python
# Request: {"design_ids": [...], "action": "delete" | "transfer" | "change_visibility", "params": {"visibility": "public"}}
# Response: BulkActionResponse
```

**Backend Implementation Notes:**
- Design transfer: Update `design.user_id`, create audit log
- Version history: Query `Design` + related version records (if `DesignVersion` model exists) or use audit log for change tracking
- Bulk operations: Transaction-wrapped iteration

**Frontend Changes:**
- `DesignsTab`: Add "Transfer" button in design detail, "Version History" expandable section
- `ProjectsTab` + `DesignsTab`: Add checkbox selection + bulk action toolbar

**Tests:**
```
backend/tests/api/test_admin_designs.py
  - test_transfer_design_changes_owner
  - test_transfer_design_invalid_user_returns_404
  - test_transfer_design_creates_audit_log
  - test_design_version_history_returns_versions
  - test_design_version_history_empty
  - test_bulk_delete_projects
  - test_bulk_transfer_designs
  - test_bulk_change_visibility
```

---

### Batch 1D: US-10.4 Template Gaps

**Backend — New Endpoints:**

```
PATCH /api/v1/admin/templates/reorder
```
```python
# Request: {"template_ids": ["uuid1", "uuid2", "uuid3"]}  # ordered list
# Response: {"message": "Templates reordered", "count": 3}
```

```
GET /api/v1/admin/templates/analytics
```
```python
# Response: TemplateAnalyticsResponse
{
    "total_templates": 22,
    "total_generations": 4500,
    "templates": [
        {
            "id": "uuid",
            "name": "Simple Box",
            "slug": "simple-box",
            "generation_count": 1200,
            "unique_users": 340,
            "avg_generation_time_ms": 450,
            "success_rate": 98.5,
            "last_generated": "2026-02-27T09:00:00Z",
            "trend_7d": [120, 130, 115, 140, 125, 150, 145]
        }
    ],
    "most_popular": "simple-box",
    "least_popular": "pipe-connector"
}
```

**Backend Implementation Notes:**
- Reorder: Requires `display_order` column on `Template` model. Add Alembic migration if missing.
- Analytics: Query `Job` model grouped by `template_id`, join with `Template`

**Frontend Changes:**
- `TemplatesTab`: Add drag-and-drop reorder (or up/down arrows), add "Analytics" section with usage chart

**Tests:**
```
backend/tests/api/test_admin_templates.py
  - test_reorder_templates_updates_display_order
  - test_reorder_templates_partial_list
  - test_template_analytics_returns_usage
  - test_template_analytics_includes_trends
  - test_template_analytics_requires_admin
```

---

## Batch 2: Credits, Billing & Subscriptions
**Complexity:** M | **Estimate:** 3–4 days | **Dependencies:** None (models exist)

Complete US-10.5a (Credits/Quotas), US-10.5b (Subscriptions), grouped since they share billing domain.

### Batch 2A: US-10.5a Credits/Quotas Completion

**Backend — New Endpoints:**

```
POST /api/v1/admin/users/{id}/credits/deduct
```
```python
# Request: CreditDeductRequest
{
    "amount": 50,
    "reason": "Refund adjustment"  # required
}
# Response: CreditBalanceResponse
{
    "user_id": "uuid",
    "previous_balance": 200,
    "new_balance": 150,
    "amount_deducted": 50,
    "reason": "Refund adjustment",
    "performed_by": "admin-uuid",
    "timestamp": "2026-02-27T10:00:00Z"
}
```

```
GET /api/v1/admin/users/{id}/credits/history?page=1&page_size=20
```
```python
# Response: CreditHistoryResponse
{
    "items": [
        {
            "id": "uuid",
            "type": "add" | "deduct" | "usage" | "refund" | "coupon",
            "amount": 50,
            "balance_after": 250,
            "reason": "Manual addition by admin",
            "performed_by": "admin-uuid",
            "created_at": "2026-02-27T10:00:00Z"
        }
    ],
    "total": 45,
    "current_balance": 250
}
```

```
GET /api/v1/admin/users/{id}/quota
```
```python
# Response: UserQuotaResponse
{
    "user_id": "uuid",
    "tier": "pro",
    "quotas": {
        "storage_mb": {"limit": 5000, "used": 2300, "remaining": 2700},
        "projects": {"limit": 50, "used": 12, "remaining": 38},
        "generations_per_day": {"limit": 100, "used": 23, "remaining": 77},
        "api_calls_per_hour": {"limit": 1000, "used": 45, "remaining": 955}
    },
    "overrides": [
        {
            "id": "uuid",
            "quota_type": "storage_mb",
            "override_limit": 10000,
            "expires_at": "2026-03-27T00:00:00Z",
            "reason": "Beta tester bonus"
        }
    ]
}
```

```
POST /api/v1/admin/users/{id}/quota/override
```
```python
# Request: QuotaOverrideRequest
{
    "quota_type": "storage_mb" | "projects" | "generations_per_day" | "api_calls_per_hour",
    "override_limit": 10000,
    "expires_at": "2026-03-27T00:00:00Z",  # optional, null = permanent
    "reason": "Beta tester bonus"
}
# Response: {"message": "Quota override applied", "override_id": "uuid"}
```

```
DELETE /api/v1/admin/users/{id}/quota/override
```
```python
# Request: {"quota_type": "storage_mb"}
# Response: {"message": "Quota override removed"}
```

```
GET /api/v1/admin/credits/distribution
```
```python
# Response: CreditDistributionResponse
{
    "total_credits_issued": 500000,
    "total_credits_consumed": 320000,
    "total_credits_outstanding": 180000,
    "distribution": [
        {"range": "0-100", "user_count": 450},
        {"range": "101-500", "user_count": 200},
        {"range": "501-1000", "user_count": 80},
        {"range": "1001+", "user_count": 20}
    ],
    "avg_balance": 240.0,
    "median_balance": 120.0
}
```

```
GET /api/v1/admin/credits/low-balance-users?threshold=10&page=1&page_size=20
```
```python
# Response: PaginatedUserListResponse
{
    "items": [
        {"user_id": "uuid", "email": "user@example.com", "balance": 5, "tier": "pro", "last_active": "..."}
    ],
    "total": 23,
    "threshold": 10
}
```

```
POST /api/v1/admin/credits/bulk-add
```
```python
# Request: BulkCreditAddRequest
{
    "user_ids": ["uuid1", "uuid2"],  # OR
    "filter": {"tier": "pro", "min_activity_days": 30},  # segment filter
    "amount": 100,
    "reason": "Monthly bonus"
}
# Response: BulkActionResponse
{
    "success_count": 150,
    "failure_count": 0,
    "total_credits_added": 15000,
    "failures": []
}
```

**New Model (if not exists):**
```python
# backend/app/models/credit_transaction.py
class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str]  # add, deduct, usage, refund, coupon
    amount: Mapped[int]
    balance_after: Mapped[int]
    reason: Mapped[str | None]
    performed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())

class QuotaOverride(Base):
    __tablename__ = "quota_overrides"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    quota_type: Mapped[str]
    override_limit: Mapped[int]
    expires_at: Mapped[datetime | None]
    reason: Mapped[str | None]
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

**Frontend Changes:**
- `SubscriptionsTab` → Split or extend with "Credits" sub-tab
- Add credit history table, deduct button, quota viewer, override form
- Add low-balance alert widget in AnalyticsTab

**Tests:**
```
backend/tests/api/test_admin_credits.py
  - test_deduct_credits_reduces_balance
  - test_deduct_credits_requires_reason
  - test_deduct_credits_insufficient_balance
  - test_credit_history_returns_transactions
  - test_credit_history_pagination
  - test_get_user_quota_returns_limits
  - test_quota_override_applies_new_limit
  - test_quota_override_with_expiration
  - test_remove_quota_override
  - test_credit_distribution_returns_ranges
  - test_low_balance_users_filters_by_threshold
  - test_bulk_add_credits_to_users
  - test_bulk_add_credits_by_filter
  - test_all_credit_ops_require_admin
```

---

### Batch 2B: US-10.5b Subscription Gaps

**Backend — New Endpoints:**

```
GET /api/v1/admin/billing/failed-payments?page=1&page_size=20
```
```python
# Response: FailedPaymentsResponse
{
    "items": [
        {
            "id": "uuid",
            "user_id": "uuid",
            "user_email": "user@example.com",
            "amount": 49.99,
            "currency": "usd",
            "failure_reason": "card_declined",
            "stripe_payment_intent_id": "pi_...",
            "attempted_at": "2026-02-27T10:00:00Z",
            "retry_count": 2,
            "next_retry_at": "2026-02-28T10:00:00Z"
        }
    ],
    "total": 12,
    "total_failed_amount": 599.88
}
```

```
POST /api/v1/admin/billing/refund
```
```python
# Request: RefundRequest
{
    "payment_id": "uuid",  # or stripe_payment_intent_id
    "amount": 49.99,  # partial or full
    "reason": "customer_request" | "duplicate" | "fraudulent" | "other",
    "notes": "Customer reported billing issue"
}
# Response: RefundResponse
{
    "refund_id": "uuid",
    "stripe_refund_id": "re_...",
    "amount": 49.99,
    "status": "succeeded",
    "user_id": "uuid"
}
```

```
GET /api/v1/admin/billing/revenue?period=30d&group_by=tier
```
```python
# Response: RevenueReportResponse
{
    "total_revenue": 45000.00,
    "revenue_by_tier": [
        {"tier": "pro", "revenue": 35000.00, "count": 700},
        {"tier": "enterprise", "revenue": 10000.00, "count": 50}
    ],
    "revenue_by_period": [
        {"date": "2026-02-01", "revenue": 1500.00}
    ],
    "refunds_total": 500.00,
    "net_revenue": 44500.00,
    "period": "30d"
}
```

```
GET /api/v1/admin/subscription-tiers
```
```python
# Response: list[SubscriptionTierResponse]
[
    {
        "id": "uuid",
        "name": "Pro",
        "slug": "pro",
        "price_monthly": 49.99,
        "price_yearly": 499.99,
        "features": {"storage_mb": 5000, "projects": 50, "generations_per_day": 100},
        "is_active": true,
        "subscriber_count": 700
    }
]
```

```
PATCH /api/v1/admin/subscription-tiers/{id}
```
```python
# Request: SubscriptionTierUpdateRequest
{
    "price_monthly": 39.99,
    "features": {"storage_mb": 10000},
    "is_active": true
}
# Response: SubscriptionTierResponse
```

```
GET /api/v1/admin/billing/webhook-events?page=1&page_size=20
```
```python
# Response: WebhookEventsResponse
{
    "items": [
        {
            "id": "uuid",
            "stripe_event_id": "evt_...",
            "type": "invoice.payment_succeeded",
            "status": "processed" | "failed" | "ignored",
            "received_at": "2026-02-27T10:00:00Z",
            "processed_at": "2026-02-27T10:00:01Z",
            "error": null
        }
    ],
    "total": 500
}
```

**Backend Implementation Notes:**
- Failed payments: Query `Payment` model where `status='failed'`
- Refund: Call Stripe API `stripe.Refund.create()`, update local Payment record
- Revenue: Aggregate from `Payment` model, group by tier/period
- Webhook events: Needs new `WebhookEvent` model or query from Stripe API directly
- Tier definitions: Query `SubscriptionTier` enum/model

**Frontend Changes:**
- `SubscriptionsTab`: Add "Failed Payments" table, "Refund" button on payment rows
- Add revenue chart, tier management section, webhook event viewer

**Tests:**
```
backend/tests/api/test_admin_billing.py
  - test_failed_payments_returns_list
  - test_failed_payments_pagination
  - test_refund_creates_stripe_refund
  - test_refund_requires_valid_payment
  - test_refund_partial_amount
  - test_revenue_report_by_tier
  - test_revenue_report_by_period
  - test_list_subscription_tiers
  - test_update_subscription_tier
  - test_webhook_events_list
  - test_all_billing_ops_require_admin
```

---

## Batch 3: Organizations & Components
**Complexity:** M | **Estimate:** 3–4 days | **Dependencies:** None

Complete US-10.6 (Organizations) and US-10.7 (Components).

### Batch 3A: US-10.6 Organization Gaps

**Backend — New Endpoints:**

```
PATCH /api/v1/admin/organizations/{id}
```
```python
# Request: OrgUpdateRequest
{
    "name": "Updated Org Name",
    "description": "New description",
    "settings": {"allow_public_designs": true}
}
# Response: OrganizationResponse
```

```
POST /api/v1/admin/organizations/{id}/members
```
```python
# Request: {"user_id": "uuid", "role": "member" | "admin" | "owner"}
# Response: {"message": "Member added", "org_id": "...", "user_id": "..."}
```

```
DELETE /api/v1/admin/organizations/{id}/members/{user_id}
```
```python
# Response: {"message": "Member removed"}
```

```
PATCH /api/v1/admin/organizations/{id}/members/{user_id}/role
```
```python
# Request: {"role": "admin"}
# Response: {"message": "Role updated", "new_role": "admin"}
```

```
POST /api/v1/admin/organizations/{id}/transfer-ownership
```
```python
# Request: {"new_owner_id": "uuid"}
# Response: {"message": "Ownership transferred", "previous_owner": "uuid", "new_owner": "uuid"}
```

```
POST /api/v1/admin/organizations/{id}/credits/add
```
```python
# Request: {"amount": 500, "reason": "Enterprise bonus"}
# Response: {"previous_balance": 1000, "new_balance": 1500}
```

```
PATCH /api/v1/admin/organizations/{id}/tier
```
```python
# Request: {"tier": "enterprise"}
# Response: {"message": "Tier updated", "previous_tier": "pro", "new_tier": "enterprise"}
```

```
GET /api/v1/admin/organizations/{id}/audit-log?page=1&page_size=20
```
```python
# Response: PaginatedAuditLogResponse (same shape as main audit log, filtered by org)
```

```
GET /api/v1/admin/organizations/{id}/stats
```
```python
# Response: OrgStatsResponse
{
    "member_count": 25,
    "project_count": 120,
    "design_count": 450,
    "storage_used_mb": 3200,
    "credits_balance": 1500,
    "generations_30d": 890,
    "active_members_30d": 18
}
```

**Frontend Changes:**
- `OrganizationsTab`: Add edit form, member management table (add/remove/role change), transfer button, credits/tier sections, audit log viewer, stats dashboard

**Tests:**
```
backend/tests/api/test_admin_organizations.py
  - test_update_organization_name
  - test_add_member_to_organization
  - test_add_duplicate_member_returns_409
  - test_remove_member_from_organization
  - test_remove_nonexistent_member_returns_404
  - test_change_member_role
  - test_transfer_ownership
  - test_transfer_ownership_to_non_member_fails
  - test_add_org_credits
  - test_change_org_tier
  - test_org_audit_log_returns_entries
  - test_org_stats_returns_counts
  - test_all_org_ops_require_admin
```

---

### Batch 3B: US-10.7 Component Gaps

**Backend — New Endpoints:**

```
GET /api/v1/admin/components/{id}
```
```python
# Response: ComponentDetailResponse
{
    "id": "uuid",
    "name": "NE555 Timer",
    "category": "IC",
    "manufacturer": "Texas Instruments",
    "mpn": "NE555P",
    "specs": {"package": "DIP-8", "supply_voltage": "4.5-16V"},
    "is_verified": true,
    "is_featured": false,
    "is_library": true,
    "usage_count": 42,
    "created_by": "uuid",
    "created_at": "2026-01-15T00:00:00Z",
    "updated_at": "2026-02-27T00:00:00Z"
}
```

```
POST /api/v1/admin/components
```
```python
# Request: ComponentCreateRequest
{
    "name": "LM7805",
    "category": "Voltage Regulator",
    "manufacturer": "STMicroelectronics",
    "mpn": "LM7805CT",
    "specs": {"output_voltage": "5V", "max_current": "1.5A"},
    "is_library": true
}
# Response: ComponentDetailResponse
```

```
PATCH /api/v1/admin/components/{id}
```
```python
# Request: ComponentUpdateRequest (all fields optional)
# Response: ComponentDetailResponse
```

```
POST /api/v1/admin/components/merge
```
```python
# Request: {"source_ids": ["uuid1", "uuid2"], "target_id": "uuid3"}
# Response: {"message": "Components merged", "merged_count": 2, "target_id": "uuid3"}
```

```
GET /api/v1/admin/components/analytics
```
```python
# Response: ComponentAnalyticsResponse
{
    "total_components": 500,
    "library_components": 200,
    "user_components": 300,
    "verified_count": 150,
    "most_used": [
        {"id": "uuid", "name": "NE555 Timer", "usage_count": 42}
    ],
    "recently_added": [...],
    "by_category": [
        {"category": "IC", "count": 120},
        {"category": "Resistor", "count": 80}
    ]
}
```

```
POST /api/v1/admin/components/bulk-import
```
```python
# Request: multipart/form-data with CSV file
# Columns: name, category, manufacturer, mpn, specs_json
# Response: BulkImportResponse
{
    "imported": 45,
    "skipped": 3,
    "errors": [{"row": 12, "error": "Missing required field 'name'"}]
}
```

```
POST /api/v1/admin/components/{id}/approve-for-library
```
```python
# Response: {"message": "Component approved for library", "component_id": "uuid"}
```

**Frontend Changes:**
- `ComponentsTab`: Add detail view panel, create form, edit form, merge UI, analytics charts, bulk import (file upload), approve button

**Tests:**
```
backend/tests/api/test_admin_components.py
  - test_get_component_detail
  - test_get_nonexistent_component_returns_404
  - test_create_library_component
  - test_create_component_missing_name_returns_422
  - test_update_component_specs
  - test_merge_components
  - test_merge_components_invalid_target
  - test_component_analytics
  - test_bulk_import_csv
  - test_bulk_import_invalid_csv
  - test_approve_for_library
  - test_all_component_ops_require_admin
```

---

## Batch 4: Jobs, Notifications & API Keys
**Complexity:** M | **Estimate:** 3–4 days | **Dependencies:** None

Complete US-10.8 (Jobs), US-10.9 (Notifications), US-10.11 (API Keys).

### Batch 4A: US-10.8 Job Queue Gaps

**Backend — New Endpoints:**

```
PATCH /api/v1/admin/jobs/{id}/priority
```
```python
# Request: {"priority": "high" | "normal" | "low"}
# Response: {"message": "Priority updated", "job_id": "uuid", "new_priority": "high"}
```

```
GET /api/v1/admin/jobs/stats
```
```python
# Response: JobStatsResponse
{
    "total_jobs": 15000,
    "by_status": {"pending": 12, "running": 5, "completed": 14800, "failed": 183},
    "by_type": {
        "cad_generation": {"total": 8000, "avg_time_ms": 4500, "success_rate": 97.2},
        "ai_generation": {"total": 5000, "avg_time_ms": 12000, "success_rate": 92.1},
        "export": {"total": 2000, "avg_time_ms": 1200, "success_rate": 99.5}
    },
    "last_24h": {"completed": 320, "failed": 8},
    "avg_queue_wait_ms": 250
}
```

```
GET /api/v1/admin/jobs/queue-status
```
```python
# Response: QueueStatusResponse
{
    "queues": [
        {
            "name": "default",
            "pending": 12,
            "active": 3,
            "reserved": 0,
            "scheduled": 5
        },
        {"name": "priority", "pending": 2, "active": 1, "reserved": 0, "scheduled": 0}
    ],
    "total_pending": 14,
    "total_active": 4,
    "oldest_pending_age_seconds": 45
}
```

```
DELETE /api/v1/admin/jobs/purge
```
```python
# Request: {"older_than_days": 30, "status": "completed"}  # query params
# Response: {"message": "Purged 1200 jobs", "purged_count": 1200}
```

```
GET /api/v1/admin/jobs/workers
```
```python
# Response: WorkerStatusResponse
{
    "workers": [
        {
            "hostname": "worker-1@abc123",
            "status": "online",
            "active_tasks": 2,
            "processed": 5000,
            "uptime_seconds": 86400,
            "last_heartbeat": "2026-02-27T10:00:00Z",
            "queues": ["default", "priority"]
        }
    ],
    "total_workers": 3,
    "total_active_tasks": 5
}
```

```
POST /api/v1/admin/jobs/alerts
```
```python
# Request: JobAlertConfigRequest
{
    "queue_depth_threshold": 100,
    "failure_rate_threshold": 10.0,  # percentage
    "avg_wait_threshold_ms": 5000,
    "notify_email": "admin@example.com"
}
# Response: {"message": "Alert configuration updated"}
```

**Backend Implementation Notes:**
- Queue status: Use Celery inspect API (`app.control.inspect()`)
- Workers: Use `celery.control.inspect().active()`, `.stats()`, `.ping()`
- Purge: DELETE from `Job` table with filters
- Alert config: Store in Redis or DB settings table

**Frontend Changes:**
- `JobsTab`: Add stats dashboard, real-time queue status widget (poll every 10s), worker status table, priority dropdown on job rows, purge button with confirmation, alert config modal

**Tests:**
```
backend/tests/api/test_admin_jobs.py
  - test_change_job_priority
  - test_change_priority_invalid_job
  - test_job_stats_returns_aggregates
  - test_job_stats_by_type
  - test_queue_status_returns_queues
  - test_purge_old_jobs
  - test_purge_requires_confirmation_params
  - test_worker_status_returns_list
  - test_configure_job_alerts
  - test_all_job_ops_require_admin
```

---

### Batch 4B: US-10.9 Notification Gaps

**Backend — New Endpoints:**

```
POST /api/v1/admin/notifications/targeted
```
```python
# Request: TargetedNotificationRequest
{
    "title": "Pro users: new feature available",
    "message": "We've added bulk export...",
    "type": "info" | "warning" | "promotion",
    "target": {
        "tier": "pro",           # optional filters
        "active_since": "2026-01-01",
        "min_generations": 10
    }
}
# Response: {"message": "Notification queued", "target_count": 150, "notification_id": "uuid"}
```

```
POST /api/v1/admin/notifications/scheduled
```
```python
# Request: ScheduledNotificationRequest
{
    "title": "Maintenance window",
    "message": "Scheduled downtime...",
    "type": "warning",
    "scheduled_at": "2026-03-01T02:00:00Z",
    "target": {"all": true}
}
# Response: {"message": "Notification scheduled", "notification_id": "uuid", "scheduled_at": "..."}
```

```
GET /api/v1/admin/notifications/templates
```
```python
# Response: list[NotificationTemplateResponse]
[
    {
        "id": "uuid",
        "name": "welcome_email",
        "subject": "Welcome to AssemblematicAI!",
        "body_template": "Hi {{user.name}}, ...",
        "type": "email",
        "variables": ["user.name", "user.tier"],
        "created_at": "2026-01-01T00:00:00Z"
    }
]
```

```
POST /api/v1/admin/notifications/templates
```
```python
# Request: NotificationTemplateCreateRequest
{
    "name": "upgrade_reminder",
    "subject": "Upgrade to Pro",
    "body_template": "Hi {{user.name}}, you're running low on credits...",
    "type": "email" | "in_app" | "both",
    "variables": ["user.name", "user.credits"]
}
# Response: NotificationTemplateResponse
```

```
PATCH /api/v1/admin/notifications/templates/{id}
```
```python
# Request: (partial update)
# Response: NotificationTemplateResponse
```

```
GET /api/v1/admin/notifications/email-status?page=1&page_size=20
```
```python
# Response: EmailDeliveryStatusResponse
{
    "items": [
        {
            "id": "uuid",
            "recipient": "user@example.com",
            "subject": "Welcome to AssemblematicAI!",
            "status": "delivered" | "bounced" | "complained" | "pending",
            "sent_at": "2026-02-27T10:00:00Z",
            "delivered_at": "2026-02-27T10:00:02Z",
            "error": null
        }
    ],
    "total": 5000,
    "delivery_rate": 98.5,
    "bounce_rate": 0.8,
    "complaint_rate": 0.1
}
```

```
POST /api/v1/admin/users/{id}/disable-notifications
```
```python
# Request: {"disable": true, "channels": ["email", "in_app"]}  # or {"disable": false} to re-enable
# Response: {"message": "Notifications disabled for user", "user_id": "uuid"}
```

```
GET /api/v1/admin/notifications/audit-log?page=1&page_size=20
```
```python
# Response: PaginatedAuditLogResponse (filtered to notification actions)
```

**New Models:**
```python
# backend/app/models/notification_template.py
class NotificationTemplate(Base):
    __tablename__ = "notification_templates"
    id: Mapped[UUID]
    name: Mapped[str]  # unique
    subject: Mapped[str]
    body_template: Mapped[str]
    type: Mapped[str]  # email, in_app, both
    variables: Mapped[list[str]]  # JSON column
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

**Frontend Changes:**
- `NotificationsTab`: Add targeted notification form (with user segment filters), scheduled notification form with date picker, template CRUD table, email delivery status table, per-user disable toggle

**Tests:**
```
backend/tests/api/test_admin_notifications.py
  - test_create_targeted_notification
  - test_targeted_notification_filters_by_tier
  - test_schedule_notification_for_future
  - test_schedule_notification_past_date_returns_422
  - test_create_notification_template
  - test_update_notification_template
  - test_list_notification_templates
  - test_email_delivery_status
  - test_disable_user_notifications
  - test_re_enable_user_notifications
  - test_notification_audit_log
  - test_all_notification_ops_require_admin
```

---

### Batch 4C: US-10.11 API Key Gaps

**Backend — New Endpoints:**

```
GET /api/v1/admin/api-keys/{id}
```
```python
# Response: APIKeyDetailResponse
{
    "id": "uuid",
    "name": "Production Key",
    "key_prefix": "ak_prod_****",
    "owner_id": "uuid",
    "owner_email": "user@example.com",
    "scopes": ["read", "write", "generate"],
    "created_at": "2026-01-15T00:00:00Z",
    "last_used_at": "2026-02-27T09:00:00Z",
    "last_used_ip": "192.168.1.1",
    "is_active": true,
    "total_requests": 12500,
    "requests_today": 45
}
```

```
GET /api/v1/admin/api-keys/{id}/usage?period=30d
```
```python
# Response: APIKeyUsageResponse
{
    "key_id": "uuid",
    "total_requests": 12500,
    "daily_usage": [{"date": "2026-02-27", "requests": 45, "errors": 1}],
    "by_endpoint": [
        {"endpoint": "/api/v1/generate", "requests": 5000},
        {"endpoint": "/api/v1/templates", "requests": 3000}
    ],
    "error_rate": 0.8,
    "avg_response_time_ms": 320,
    "period": "30d"
}
```

```
GET /api/v1/admin/api-keys/stats
```
```python
# Response: APIKeyStatsResponse
{
    "total_keys": 250,
    "active_keys": 200,
    "revoked_keys": 50,
    "total_requests_24h": 15000,
    "keys_by_scope": {"read": 200, "write": 150, "generate": 100},
    "top_users": [
        {"user_id": "uuid", "email": "...", "key_count": 5, "total_requests": 50000}
    ]
}
```

```
GET /api/v1/admin/api-keys/rate-limit-violations?page=1&page_size=20
```
```python
# Response:
{
    "items": [
        {
            "key_id": "uuid",
            "owner_email": "user@example.com",
            "violation_count": 15,
            "last_violation": "2026-02-27T09:30:00Z",
            "limit_type": "per_minute",
            "limit_value": 60
        }
    ],
    "total": 8
}
```

```
GET /api/v1/admin/api-keys/suspicious-activity
```
```python
# Response:
{
    "alerts": [
        {
            "key_id": "uuid",
            "owner_email": "user@example.com",
            "alert_type": "unusual_volume" | "geographic_anomaly" | "error_spike",
            "description": "Request volume 10x above average",
            "severity": "high",
            "detected_at": "2026-02-27T09:00:00Z"
        }
    ]
}
```

```
GET /api/v1/admin/api-keys/audit-log?page=1&page_size=20
```
```python
# Response: PaginatedAuditLogResponse (filtered to api_key actions)
```

```
PATCH /api/v1/admin/api-keys/rate-limits
```
```python
# Request: RateLimitConfigRequest
{
    "per_minute": 60,
    "per_hour": 1000,
    "per_day": 10000,
    "per_key_per_minute": 30
}
# Response: {"message": "Rate limits updated"}
```

**Backend Implementation Notes:**
- API key usage tracking: Query from request logs or add counter in Redis
- Suspicious activity: Heuristic detection — compare current usage to rolling average
- Rate limit violations: Log in Redis, query via admin endpoint

**Frontend Changes:**
- `APIKeysTab`: Add detail panel, usage charts (per key and aggregated), rate limit violations table, suspicious activity alerts, audit log viewer, rate limit config form

**Tests:**
```
backend/tests/api/test_admin_apikeys.py
  - test_get_api_key_detail
  - test_get_api_key_not_found
  - test_api_key_usage_by_period
  - test_api_key_aggregated_stats
  - test_rate_limit_violations_list
  - test_suspicious_activity_detection
  - test_api_key_audit_log
  - test_update_rate_limits
  - test_all_apikey_ops_require_admin
```

---

## Batch 5: Files/Storage & Audit/Security
**Complexity:** M–L | **Estimate:** 4–5 days | **Dependencies:** None

Complete US-10.12 (Files/Storage) and US-10.13 (Audit/Security).

### Batch 5A: US-10.12 Files/Storage Gaps

**Backend — New Endpoints:**

```
GET /api/v1/admin/files/{id}
```
```python
# Response: FileDetailResponse
{
    "id": "uuid",
    "filename": "gear-v2.step",
    "original_filename": "my_gear.step",
    "content_type": "application/step",
    "size_bytes": 245000,
    "storage_path": "users/uuid/files/gear-v2.step",
    "owner_id": "uuid",
    "owner_email": "user@example.com",
    "download_url": "/files/uuid/download",  # presigned
    "checksum_sha256": "abc123...",
    "is_flagged": false,
    "created_at": "2026-02-27T10:00:00Z",
    "last_accessed": "2026-02-27T12:00:00Z",
    "associated_design_id": "uuid" | null
}
```

```
GET /api/v1/admin/files/flagged?page=1&page_size=20
```
```python
# Response: PaginatedFileListResponse (filtered to flagged files)
```

```
POST /api/v1/admin/users/{id}/storage-quota
```
```python
# Request: {"quota_mb": 10000, "reason": "Enterprise upgrade"}
# Response: {"message": "Storage quota updated", "previous_quota_mb": 5000, "new_quota_mb": 10000}
```

```
GET /api/v1/admin/storage/top-users?limit=20
```
```python
# Response: TopStorageUsersResponse
{
    "users": [
        {
            "user_id": "uuid",
            "email": "user@example.com",
            "storage_used_mb": 4500,
            "storage_quota_mb": 5000,
            "file_count": 230,
            "usage_percentage": 90.0
        }
    ]
}
```

```
GET /api/v1/admin/storage/analytics
```
```python
# Response: StorageAnalyticsResponse
{
    "total_storage_used_gb": 250.5,
    "total_files": 50000,
    "uploads_24h": 120,
    "downloads_24h": 450,
    "avg_file_size_mb": 5.01,
    "by_type": [
        {"content_type": "application/step", "count": 20000, "total_size_gb": 100},
        {"content_type": "application/stl", "count": 15000, "total_size_gb": 80}
    ],
    "daily_trend": [{"date": "2026-02-27", "uploads": 120, "downloads": 450, "storage_delta_mb": 600}]
}
```

```
POST /api/v1/admin/storage/garbage-collect
```
```python
# Response: GarbageCollectionResponse
{
    "orphaned_files_found": 45,
    "orphaned_files_deleted": 45,
    "space_reclaimed_mb": 230.5,
    "duration_seconds": 12.3
}
```

```
GET /api/v1/admin/files/failed-uploads?page=1&page_size=20
```
```python
# Response:
{
    "items": [
        {
            "id": "uuid",
            "user_id": "uuid",
            "filename": "large_file.step",
            "error": "File size exceeds limit",
            "attempted_at": "2026-02-27T10:00:00Z",
            "size_bytes": 500000000
        }
    ],
    "total": 8
}
```

**Frontend Changes:**
- `StorageTab`: Add file detail panel with download button, flagged files filter, quota adjustment per user, top users table, analytics charts, garbage collection trigger button, failed uploads table

**Tests:**
```
backend/tests/api/test_admin_storage.py
  - test_get_file_detail
  - test_get_file_not_found
  - test_list_flagged_files
  - test_adjust_storage_quota
  - test_top_storage_users
  - test_storage_analytics
  - test_garbage_collection
  - test_failed_uploads_list
  - test_all_storage_ops_require_admin
```

---

### Batch 5B: US-10.13 Audit/Security Gaps

**Backend — New Endpoints:**

```
GET /api/v1/admin/audit-logs/export?format=csv&start_date=2026-02-01&end_date=2026-02-28
```
```python
# Response: StreamingResponse (CSV)
# Columns: id, user_id, user_email, action, resource_type, resource_id, ip_address, timestamp, details
```

```
GET /api/v1/admin/security/events?page=1&page_size=20&severity=high
```
```python
# Response: SecurityEventsResponse
{
    "items": [
        {
            "id": "uuid",
            "event_type": "unauthorized_access" | "brute_force" | "suspicious_ip" | "privilege_escalation",
            "severity": "low" | "medium" | "high" | "critical",
            "user_id": "uuid" | null,
            "ip_address": "192.168.1.1",
            "description": "5 failed login attempts in 60 seconds",
            "details": {},
            "created_at": "2026-02-27T10:00:00Z",
            "resolved": false
        }
    ],
    "total": 45
}
```

```
GET /api/v1/admin/security/failed-logins?page=1&page_size=20
```
```python
# Response:
{
    "items": [
        {
            "email": "user@example.com",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
            "attempted_at": "2026-02-27T10:00:00Z",
            "failure_reason": "invalid_password" | "account_locked" | "unknown_email"
        }
    ],
    "total": 120,
    "unique_ips": 45,
    "unique_emails": 30
}
```

```
GET /api/v1/admin/security/rate-limits
```
```python
# Response: RateLimitSummaryResponse
{
    "current_config": {"login": "5/min", "api": "60/min", "generate": "10/min"},
    "violations_24h": 23,
    "top_violators": [
        {"ip_address": "...", "violation_count": 15, "last_violation": "..."}
    ]
}
```

```
GET /api/v1/admin/security/blocked-ips
```
```python
# Response:
{
    "blocked_ips": [
        {
            "ip_address": "192.168.1.100",
            "reason": "Brute force attack",
            "blocked_at": "2026-02-27T08:00:00Z",
            "blocked_by": "uuid" | "system",
            "expires_at": "2026-03-27T08:00:00Z" | null
        }
    ]
}
```

```
POST /api/v1/admin/security/blocked-ips
```
```python
# Request: {"ip_address": "192.168.1.100", "reason": "Abuse", "duration_hours": 720}
# Response: {"message": "IP blocked", "ip_address": "...", "expires_at": "..."}
```

```
DELETE /api/v1/admin/security/blocked-ips/{ip}
```
```python
# Response: {"message": "IP unblocked"}
```

```
GET /api/v1/admin/security/sessions?page=1&page_size=20
```
```python
# Response: ActiveSessionsResponse
{
    "items": [
        {
            "session_id": "uuid",
            "user_id": "uuid",
            "user_email": "user@example.com",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
            "started_at": "2026-02-27T08:00:00Z",
            "last_activity": "2026-02-27T10:00:00Z",
            "is_current": false
        }
    ],
    "total": 250,
    "active_now": 45
}
```

```
DELETE /api/v1/admin/security/sessions/{id}
```
```python
# Response: {"message": "Session terminated", "user_id": "uuid"}
```

```
GET /api/v1/admin/security/threats
```
```python
# Response: ThreatDashboardResponse
{
    "active_threats": 3,
    "threats": [
        {
            "id": "uuid",
            "type": "brute_force" | "credential_stuffing" | "api_abuse" | "data_exfiltration",
            "severity": "critical",
            "source_ip": "192.168.1.100",
            "target_user": "uuid" | null,
            "description": "Ongoing brute force attack from IP",
            "first_seen": "2026-02-27T09:00:00Z",
            "last_seen": "2026-02-27T10:00:00Z",
            "event_count": 150,
            "auto_mitigated": true
        }
    ]
}
```

```
PATCH /api/v1/admin/security/thresholds
```
```python
# Request: SecurityThresholdsRequest
{
    "failed_login_lockout": 5,
    "failed_login_window_minutes": 15,
    "rate_limit_login_per_minute": 5,
    "rate_limit_api_per_minute": 60,
    "auto_block_threshold": 20,
    "session_timeout_minutes": 480
}
# Response: {"message": "Security thresholds updated"}
```

```
GET /api/v1/admin/security/dashboard
```
```python
# Response: SecurityDashboardResponse
{
    "risk_level": "low" | "medium" | "high" | "critical",
    "active_threats": 3,
    "failed_logins_24h": 120,
    "blocked_ips": 5,
    "active_sessions": 250,
    "rate_limit_violations_24h": 23,
    "security_events_24h": 15,
    "last_incident": "2026-02-27T09:00:00Z"
}
```

**New Model:**
```python
# backend/app/models/security_event.py (if not exists in security_audit service)
class SecurityEvent(Base):
    __tablename__ = "security_events"
    id: Mapped[UUID]
    event_type: Mapped[str]
    severity: Mapped[str]
    user_id: Mapped[UUID | None]
    ip_address: Mapped[str | None]
    description: Mapped[str]
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    resolved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]

class BlockedIP(Base):
    __tablename__ = "blocked_ips"
    id: Mapped[UUID]
    ip_address: Mapped[str] = mapped_column(unique=True)
    reason: Mapped[str]
    blocked_by: Mapped[UUID | None]
    blocked_at: Mapped[datetime]
    expires_at: Mapped[datetime | None]
```

**Frontend Changes:**
- `AuditTab`: Add export button, security events table with severity filter, failed logins table, blocked IPs table with add/remove, active sessions table with terminate button, threat dashboard, threshold config form, security summary dashboard

**Tests:**
```
backend/tests/api/test_admin_security.py
  - test_export_audit_logs_csv
  - test_export_audit_logs_date_filter
  - test_security_events_list
  - test_security_events_filter_by_severity
  - test_failed_logins_list
  - test_rate_limit_summary
  - test_list_blocked_ips
  - test_block_ip
  - test_block_duplicate_ip_returns_409
  - test_unblock_ip
  - test_list_active_sessions
  - test_terminate_session
  - test_threat_dashboard
  - test_update_security_thresholds
  - test_security_dashboard_summary
  - test_all_security_ops_require_admin
```

---

## Batch 6: System Health Completion
**Complexity:** S–M | **Estimate:** 2–3 days | **Dependencies:** None

Complete US-10.14 (System Health).

**Backend — New Endpoints:**

```
GET /api/v1/admin/system/services/{service}
```
```python
# service: "database" | "redis" | "storage" | "ai" | "celery"
# Response: ServiceDetailResponse
{
    "service": "database",
    "status": "healthy",
    "latency_ms": 2.3,
    "details": {
        "host": "postgres:5432",
        "version": "PostgreSQL 15.4",
        "connections_active": 12,
        "connections_max": 100,
        "database_size_mb": 450,
        "slow_queries_24h": 3
    },
    "last_checked": "2026-02-27T10:00:00Z"
}
```

```
GET /api/v1/admin/system/performance
```
```python
# Response: PerformanceMetricsResponse
{
    "api": {
        "avg_response_time_ms": 120,
        "p95_response_time_ms": 450,
        "p99_response_time_ms": 1200,
        "requests_per_minute": 85,
        "error_rate": 0.5
    },
    "slowest_endpoints": [
        {"endpoint": "POST /api/v1/generate", "avg_ms": 12000, "count": 500}
    ],
    "daily_trend": [{"date": "2026-02-27", "avg_ms": 120, "requests": 12000}]
}
```

```
GET /api/v1/admin/system/resources
```
```python
# Response: ResourceUtilizationResponse
{
    "cpu": {"usage_percent": 45.2, "cores": 4},
    "memory": {"used_mb": 2048, "total_mb": 8192, "usage_percent": 25.0},
    "disk": {"used_gb": 50, "total_gb": 200, "usage_percent": 25.0},
    "network": {"bytes_in_24h": 5000000000, "bytes_out_24h": 12000000000}
}
```

```
GET /api/v1/admin/system/errors?page=1&page_size=20&severity=error
```
```python
# Response: ErrorLogsResponse
{
    "items": [
        {
            "id": "uuid",
            "level": "error",
            "message": "CadQuery generation failed: invalid parameter",
            "module": "app.cad.templates",
            "stack_trace": "Traceback...",
            "timestamp": "2026-02-27T10:00:00Z",
            "request_id": "uuid",
            "user_id": "uuid" | null
        }
    ],
    "total": 45,
    "errors_24h": 12,
    "warnings_24h": 35
}
```

```
GET /api/v1/admin/system/ai-providers
```
```python
# Response: AIProviderStatusResponse
{
    "providers": [
        {
            "name": "openai",
            "status": "healthy",
            "model": "gpt-4",
            "latency_ms": 850,
            "tokens_used_24h": 150000,
            "cost_24h": 4.50,
            "quota_remaining": "95%",
            "error_rate": 0.2,
            "last_request": "2026-02-27T10:00:00Z"
        },
        {
            "name": "ollama",
            "status": "healthy",
            "model": "llama3",
            "latency_ms": 1200,
            "tokens_used_24h": 500000,
            "cost_24h": 0,
            "error_rate": 1.5,
            "last_request": "2026-02-27T09:58:00Z"
        }
    ],
    "primary_provider": "ollama",
    "fallback_provider": "openai"
}
```

```
GET /api/v1/admin/system/config
```
```python
# Response: SystemConfigResponse (sanitized — no secrets)
{
    "app_name": "AssemblematicAI",
    "environment": "production",
    "debug": false,
    "features": {
        "ai_generation": true,
        "oauth_login": true,
        "file_uploads": true,
        "stripe_billing": true
    },
    "limits": {
        "max_file_size_mb": 100,
        "max_projects_free": 5,
        "max_generations_free_daily": 10
    },
    "storage_backend": "minio",
    "ai_primary_provider": "ollama",
    "celery_broker": "redis://***"
}
```

```
POST /api/v1/admin/system/health-check
```
```python
# Response: (same as GET /admin/system/health but forces a fresh check, no cache)
```

```
GET /api/v1/admin/system/uptime
```
```python
# Response: UptimeHistoryResponse
{
    "current_uptime_seconds": 864000,
    "current_uptime_formatted": "10d 0h 0m",
    "started_at": "2026-02-17T10:00:00Z",
    "history": [
        {
            "date": "2026-02-27",
            "uptime_percent": 99.95,
            "incidents": 1,
            "total_downtime_seconds": 43
        }
    ],
    "avg_uptime_30d": 99.98
}
```

**Backend Implementation Notes:**
- Performance metrics: Use middleware to track response times, store in Redis with TTL
- Resources: Use `psutil` library (add to requirements.txt)
- Error logs: Query structured logs from DB or log file
- Config: Sanitize settings object, redact secrets
- Uptime: Track server start time, store incidents

**Frontend Changes:**
- `SystemTab`: Add per-service detail cards (expandable), performance metrics dashboard, resource utilization gauges, error log viewer with stack trace expansion, AI provider status cards, config viewer (read-only), manual health check button, uptime chart

**Tests:**
```
backend/tests/api/test_admin_system.py
  - test_service_detail_database
  - test_service_detail_redis
  - test_service_detail_invalid_service_returns_404
  - test_performance_metrics
  - test_resource_utilization
  - test_error_logs_paginated
  - test_error_logs_filter_by_severity
  - test_ai_provider_status
  - test_config_sanitized_no_secrets
  - test_manual_health_check
  - test_uptime_history
  - test_all_system_ops_require_admin
```

---

## Batch 7: New Feature — Coupons/Promotions (US-10.5c)
**Complexity:** L | **Estimate:** 4–5 days | **Dependencies:** Batch 2 (billing models)

### New Models

```python
# backend/app/models/coupon.py
class Coupon(Base):
    __tablename__ = "coupons"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    type: Mapped[str]  # percent_off, fixed_amount, free_credits, tier_upgrade
    value: Mapped[float]  # percentage or amount depending on type
    currency: Mapped[str] = mapped_column(default="usd")
    max_uses: Mapped[int | None]  # null = unlimited
    max_uses_per_user: Mapped[int] = mapped_column(default=1)
    current_uses: Mapped[int] = mapped_column(default=0)
    valid_from: Mapped[datetime]
    valid_until: Mapped[datetime | None]
    restricted_to_tiers: Mapped[list[str] | None]  # JSON
    restricted_to_new_users: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime]

class CouponUsage(Base):
    __tablename__ = "coupon_usages"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    coupon_id: Mapped[UUID] = mapped_column(ForeignKey("coupons.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    applied_at: Mapped[datetime]
    discount_amount: Mapped[float | None]
    credits_granted: Mapped[int | None]
    tier_granted: Mapped[str | None]
```

### Endpoints

```
GET    /api/v1/admin/coupons?page=1&page_size=20&status=active
POST   /api/v1/admin/coupons
GET    /api/v1/admin/coupons/{code}
PATCH  /api/v1/admin/coupons/{code}
DELETE /api/v1/admin/coupons/{code}
GET    /api/v1/admin/coupons/{code}/usage?page=1&page_size=20
POST   /api/v1/admin/users/{id}/apply-coupon
POST   /api/v1/admin/users/{id}/grant-trial
POST   /api/v1/admin/users/{id}/extend-trial
GET    /api/v1/admin/promotions/analytics
POST   /api/v1/admin/coupons/bulk-apply
```

**Response shapes** follow the same pattern as the planning spec (section US-10.5c).

### Frontend
- New "Coupons" sub-tab under billing section of AdminDashboard
- Coupon CRUD form, usage table, analytics charts, bulk apply form

### Tests
```
backend/tests/api/test_admin_coupons.py
  - test_create_coupon_percent_off
  - test_create_coupon_free_credits
  - test_create_coupon_tier_upgrade
  - test_create_coupon_duplicate_code_returns_409
  - test_get_coupon_by_code
  - test_update_coupon
  - test_deactivate_coupon
  - test_delete_coupon
  - test_coupon_usage_list
  - test_apply_coupon_to_user
  - test_apply_expired_coupon_returns_400
  - test_apply_coupon_max_uses_exceeded
  - test_apply_coupon_tier_restricted
  - test_apply_coupon_new_users_only
  - test_grant_trial
  - test_extend_trial
  - test_promotions_analytics
  - test_bulk_apply_coupon
  - test_all_coupon_ops_require_admin
```

---

## Batch 8: New Feature — Content Management (US-10.10)
**Complexity:** M | **Estimate:** 3–4 days | **Dependencies:** None

### New Models

```python
# backend/app/models/content.py
class ContentCategory(Base):
    __tablename__ = "content_categories"
    id: Mapped[UUID]
    name: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("content_categories.id"))
    display_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime]

class FAQ(Base):
    __tablename__ = "faqs"
    id: Mapped[UUID]
    question: Mapped[str]
    answer: Mapped[str]  # Markdown
    category_id: Mapped[UUID] = mapped_column(ForeignKey("content_categories.id"))
    status: Mapped[str]  # draft, published, archived
    display_order: Mapped[int] = mapped_column(default=0)
    view_count: Mapped[int] = mapped_column(default=0)
    helpful_count: Mapped[int] = mapped_column(default=0)
    not_helpful_count: Mapped[int] = mapped_column(default=0)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    published_at: Mapped[datetime | None]

class HelpArticle(Base):
    __tablename__ = "help_articles"
    id: Mapped[UUID]
    title: Mapped[str]
    slug: Mapped[str] = mapped_column(unique=True)
    body: Mapped[str]  # Markdown
    excerpt: Mapped[str | None]
    category_id: Mapped[UUID] = mapped_column(ForeignKey("content_categories.id"))
    tags: Mapped[list[str]]  # JSON
    status: Mapped[str]  # draft, published, archived
    version: Mapped[int] = mapped_column(default=1)
    view_count: Mapped[int] = mapped_column(default=0)
    helpful_count: Mapped[int] = mapped_column(default=0)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    published_at: Mapped[datetime | None]
```

### Endpoints

```
# FAQs
GET    /api/v1/admin/content/faqs?page=1&page_size=20&status=all&category_id=uuid
POST   /api/v1/admin/content/faqs
PATCH  /api/v1/admin/content/faqs/{id}
DELETE /api/v1/admin/content/faqs/{id}
POST   /api/v1/admin/content/faqs/{id}/publish
POST   /api/v1/admin/content/faqs/{id}/archive

# Articles
GET    /api/v1/admin/content/articles?page=1&page_size=20
POST   /api/v1/admin/content/articles
PATCH  /api/v1/admin/content/articles/{id}
DELETE /api/v1/admin/content/articles/{id}
POST   /api/v1/admin/content/articles/{id}/publish
POST   /api/v1/admin/content/articles/{id}/archive

# Categories
GET    /api/v1/admin/content/categories
POST   /api/v1/admin/content/categories
PATCH  /api/v1/admin/content/categories/{id}
DELETE /api/v1/admin/content/categories/{id}

# Misc
PATCH  /api/v1/admin/content/reorder
GET    /api/v1/admin/content/analytics

# Public (non-admin)
GET    /api/v1/content/faqs?category=slug
GET    /api/v1/content/articles?category=slug&tag=tag
GET    /api/v1/content/articles/{slug}
POST   /api/v1/content/articles/{slug}/helpful
```

### Frontend
- New "Content" tab in AdminDashboard
- FAQ list/create/edit with markdown editor
- Article list/create/edit with markdown editor and live preview
- Category management sidebar
- Content analytics (view counts, helpful ratings)
- Public-facing FAQ page and Help Center page

### Tests
```
backend/tests/api/test_admin_content.py
  - test_create_faq
  - test_update_faq
  - test_delete_faq
  - test_publish_faq
  - test_archive_faq
  - test_create_article
  - test_update_article_body
  - test_publish_article
  - test_create_category
  - test_update_category
  - test_delete_category_with_content_fails
  - test_reorder_content
  - test_content_analytics
  - test_public_faq_list
  - test_public_article_by_slug
  - test_public_article_helpful_vote
  - test_all_admin_content_ops_require_admin
```

---

## Batch 9: New Features — Assemblies, Conversations, Trash
**Complexity:** L | **Estimate:** 5–6 days | **Dependencies:** None

Complete US-10.15, US-10.16, US-10.17.

### Batch 9A: US-10.15 Assemblies & BOM

**Endpoints:**
```
GET    /api/v1/admin/assemblies?page=1&page_size=20
GET    /api/v1/admin/assemblies/stats
GET    /api/v1/admin/vendors
POST   /api/v1/admin/vendors
PATCH  /api/v1/admin/vendors/{id}
DELETE /api/v1/admin/vendors/{id}
GET    /api/v1/admin/vendors/analytics
POST   /api/v1/admin/components/bulk-price-update
GET    /api/v1/admin/bom/audit-queue
```

Shapes follow the planning spec. Leverages existing `Assembly` model.

### Batch 9B: US-10.16 Conversations

**Endpoints:**
```
GET    /api/v1/admin/conversations/stats
GET    /api/v1/admin/conversations/flagged
GET    /api/v1/admin/conversations/{id}
GET    /api/v1/admin/conversations/quality-metrics
GET    /api/v1/admin/conversations/drop-off-analytics
GET    /api/v1/admin/conversations/export?format=csv
```

Leverages existing `Conversation` model.

### Batch 9C: US-10.17 Trash & Retention

**New Model:**
```python
class RetentionPolicy(Base):
    __tablename__ = "retention_policies"
    id: Mapped[UUID]
    resource_type: Mapped[str]  # design, project, file, component
    tier: Mapped[str | None]  # null = default for all tiers
    retention_days: Mapped[int]
    updated_by: Mapped[UUID]
    updated_at: Mapped[datetime]
```

**Endpoints:**
```
GET    /api/v1/admin/trash/stats
PATCH  /api/v1/admin/trash/retention-policy
DELETE /api/v1/admin/trash/{type}/{id}/permanent
POST   /api/v1/admin/trash/{type}/{id}/restore
POST   /api/v1/admin/trash/cleanup
GET    /api/v1/admin/trash/reclamation-potential
PATCH  /api/v1/admin/trash/tier-limits
```

### Frontend
- New tabs: "Assemblies", "Conversations", "Trash" in AdminDashboard
- Assembly browser with stats, vendor CRUD, BOM audit queue
- Conversation stats dashboard, flagged conversation viewer, quality metrics charts
- Trash browser, retention policy config, cleanup trigger

### Tests (combined for Batch 9)
```
backend/tests/api/test_admin_assemblies.py (8 tests)
backend/tests/api/test_admin_conversations.py (8 tests)
backend/tests/api/test_admin_trash.py (8 tests)
```

---

## Batch 10: Backend Refactoring & Cross-Cutting Concerns
**Complexity:** M | **Estimate:** 2–3 days | **Dependencies:** All above batches

### Split admin.py Into Package

Current `admin.py` is 5,899 lines. After all batches, it would be ~10,000+ lines. Refactor:

```
backend/app/api/v1/admin/
├── __init__.py            # Re-exports combined router
├── analytics.py           # US-10.1
├── users.py               # US-10.2
├── projects.py            # US-10.3
├── templates.py           # US-10.4
├── credits.py             # US-10.5a
├── billing.py             # US-10.5b
├── coupons.py             # US-10.5c
├── organizations.py       # US-10.6
├── components.py          # US-10.7
├── jobs.py                # US-10.8
├── notifications.py       # US-10.9
├── content.py             # US-10.10
├── api_keys.py            # US-10.11
├── storage.py             # US-10.12
├── security.py            # US-10.13
├── system.py              # US-10.14
├── assemblies.py          # US-10.15
├── conversations.py       # US-10.16
├── trash.py               # US-10.17
├── moderation.py          # (existing moderation endpoints)
├── schemas.py             # Shared Pydantic models
└── dependencies.py        # Shared admin deps
```

### Frontend Admin API Client Refactoring

Split `frontend/src/lib/api/admin.ts` into:
```
frontend/src/lib/api/admin/
├── index.ts               # Re-exports all
├── analytics.ts
├── users.ts
├── projects.ts
├── billing.ts
├── organizations.ts
├── components.ts
├── jobs.ts
├── notifications.ts
├── content.ts
├── apikeys.ts
├── storage.ts
├── security.ts
├── system.ts
└── types.ts               # Shared admin types
```

### Alembic Migrations

New migrations needed for:
1. `credit_transactions` table (Batch 2)
2. `quota_overrides` table (Batch 2)
3. `coupons` + `coupon_usages` tables (Batch 7)
4. `notification_templates` table (Batch 4)
5. `content_categories` + `faqs` + `help_articles` tables (Batch 8)
6. `security_events` + `blocked_ips` tables (Batch 5)
7. `retention_policies` table (Batch 9)
8. `display_order` column on `templates` table (Batch 1)
9. `webhook_events` table (Batch 2)

### Tests
```
backend/tests/api/test_admin_refactored_imports.py
  - test_all_admin_routers_imported
  - test_admin_route_count_matches_expected
  - test_no_circular_imports
```

---

## Dependency Graph

```
Batch 1 (Quick Wins)  ──────────────────────────────── No deps
Batch 2 (Credits/Billing) ──────────────────────────── No deps
Batch 3 (Orgs/Components) ──────────────────────────── No deps
Batch 4 (Jobs/Notifications/API Keys) ──────────────── No deps
Batch 5 (Files/Security) ───────────────────────────── No deps
Batch 6 (System Health) ────────────────────────────── No deps
Batch 7 (Coupons) ──────────────────────────────────── Batch 2 (billing models)
Batch 8 (Content Mgmt) ─────────────────────────────── No deps
Batch 9 (Assemblies/Conversations/Trash) ────────────── No deps
Batch 10 (Refactoring) ─────────────────────────────── ALL previous batches
```

Batches 1–6 are fully independent and can be parallelized across developers.
Batch 7 depends on Batch 2 billing models.
Batch 10 should be done last.

---

## Complexity Summary

| Batch | Stories | Complexity | Estimate | New Endpoints | New Tests |
|-------|---------|-----------|----------|---------------|-----------|
| 1: Quick Wins | 10.1, 10.2, 10.3, 10.4 | **S** | 2–3 days | ~12 | ~30 |
| 2: Credits/Billing | 10.5a, 10.5b | **M** | 3–4 days | ~16 | ~25 |
| 3: Orgs/Components | 10.6, 10.7 | **M** | 3–4 days | ~18 | ~25 |
| 4: Jobs/Notifs/Keys | 10.8, 10.9, 10.11 | **M** | 3–4 days | ~22 | ~30 |
| 5: Files/Security | 10.12, 10.13 | **M–L** | 4–5 days | ~20 | ~25 |
| 6: System Health | 10.14 | **S–M** | 2–3 days | ~8 | ~12 |
| 7: Coupons | 10.5c | **L** | 4–5 days | ~11 | ~19 |
| 8: Content Mgmt | 10.10 | **M** | 3–4 days | ~16 | ~17 |
| 9: New Features | 10.15, 10.16, 10.17 | **L** | 5–6 days | ~18 | ~24 |
| 10: Refactoring | Cross-cutting | **M** | 2–3 days | 0 | ~3 |
| **TOTAL** | **17 stories** | | **~31–41 days** | **~141** | **~210** |

---

## Recommended Execution Order

1. **Batch 1** → Quick wins, closes 4 stories, builds momentum
2. **Batch 2** → Billing foundation needed for Batch 7 (coupons)
3. **Batch 3** → Orgs + Components (medium value, moderate effort)
4. **Batch 4** → Jobs/Notifications/API Keys (operational visibility)
5. **Batch 6** → System Health (quick, high admin value)
6. **Batch 5** → Files/Security (important but complex)
7. **Batch 7** → Coupons (depends on Batch 2)
8. **Batch 8** → Content Management (new feature, lower priority)
9. **Batch 9** → Assemblies/Conversations/Trash (lowest priority new features)
10. **Batch 10** → Refactoring (after all features landed)

---

## Security Considerations (All Batches)

- **Authentication:** All endpoints use `require_admin` dependency — verified via `get_current_user` → role check
- **Authorization:** Only `admin` and `superadmin` roles can access `/admin/*` routes
- **Input Validation:** All request bodies use Pydantic models with field constraints
- **Data Sanitization:** User inputs sanitized before DB queries (SQLAlchemy parameterized queries)
- **Rate Limiting:** Admin endpoints subject to stricter rate limits (10 req/s)
- **Audit Logging:** All state-changing admin operations create audit log entries with admin user ID, action, resource, timestamp
- **Secret Redaction:** Config endpoint strips secrets, API keys shown as masked prefixes only
- **Bulk Operations:** Capped at 100 items per request to prevent abuse
- **Export Operations:** Streamed to prevent memory exhaustion; rate-limited to 1 export/minute
- **Session Termination:** Invalidates JWT in Redis blacklist when admin terminates a session
