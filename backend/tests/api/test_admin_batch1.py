"""
Tests for admin API Batch 1 (Quick Wins) endpoints.

Tests the following new admin endpoints:
- Analytics: revenue, export
- User Management: force-email-verify, login-history, activity, bulk-action, export
- Design Management: transfer, versions, bulk-action
- Project Management: bulk-action
- Template Management: reorder, analytics
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from tests.factories import (
    Counter,
    DesignFactory,
    DesignVersionFactory,
    FileFactory,
    JobFactory,
    ProjectFactory,
    TemplateFactory,
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
# Analytics Revenue Tests
# =============================================================================


class TestRevenueAnalytics:
    """Tests for GET /admin/analytics/revenue."""

    async def test_get_revenue_analytics_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get revenue analytics."""
        response = await client.get(
            "/api/v1/admin/analytics/revenue?period=30d", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "monthly_recurring_revenue_cents" in data
        assert "total_revenue_cents" in data
        assert "churn_rate" in data
        assert "upgrades_count" in data
        assert "downgrades_count" in data
        assert "subscribers_by_tier" in data
        assert data["period"] == "30d"

    async def test_get_revenue_analytics_7d_period(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Revenue analytics works with 7d period."""
        response = await client.get(
            "/api/v1/admin/analytics/revenue?period=7d", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["period"] == "7d"

    async def test_get_revenue_analytics_90d_period(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Revenue analytics works with 90d period."""
        response = await client.get(
            "/api/v1/admin/analytics/revenue?period=90d", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["period"] == "90d"

    async def test_get_revenue_analytics_invalid_period(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Invalid period returns 422."""
        response = await client.get(
            "/api/v1/admin/analytics/revenue?period=invalid", headers=admin_headers
        )
        assert response.status_code == 422

    async def test_get_revenue_analytics_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot access revenue analytics."""
        response = await client.get(
            "/api/v1/admin/analytics/revenue", headers=auth_headers
        )
        assert response.status_code == 403


# =============================================================================
# Analytics Export Tests
# =============================================================================


class TestAnalyticsExport:
    """Tests for GET /admin/analytics/export."""

    async def test_export_users_csv(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can export users as CSV."""
        await UserFactory.create_batch(db_session, 2)

        response = await client.get(
            "/api/v1/admin/analytics/export?type=users&period=30d",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        content = response.text
        assert "id,email,display_name" in content

    async def test_export_generations_csv(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can export generations as CSV."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        await DesignFactory.create(db_session, project=project)

        response = await client.get(
            "/api/v1/admin/analytics/export?type=generations&period=30d",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        content = response.text
        assert "id,name,source_type" in content

    async def test_export_jobs_csv(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can export jobs as CSV."""
        user = await UserFactory.create(db_session)
        await JobFactory.create(db_session, user=user)

        response = await client.get(
            "/api/v1/admin/analytics/export?type=jobs&period=30d",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        content = response.text
        assert "id,job_type,status" in content

    async def test_export_storage_csv(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can export storage data as CSV."""
        user = await UserFactory.create(db_session)
        await FileFactory.create(db_session, user=user)

        response = await client.get(
            "/api/v1/admin/analytics/export?type=storage&period=30d",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        content = response.text
        assert "id,filename,size_bytes" in content

    async def test_export_invalid_type(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Invalid export type returns 422."""
        response = await client.get(
            "/api/v1/admin/analytics/export?type=invalid",
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_export_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot export analytics."""
        response = await client.get(
            "/api/v1/admin/analytics/export", headers=auth_headers
        )
        assert response.status_code == 403


# =============================================================================
# Force Email Verify Tests
# =============================================================================


class TestForceEmailVerify:
    """Tests for POST /admin/users/{user_id}/force-email-verify."""

    async def test_force_email_verify_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can force verify a user's email."""
        user = await UserFactory.create(
            db_session,
            status="pending_verification",
            email_verified_at=None,
        )

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/force-email-verify",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email_verified_at"] is not None
        assert data["message"] == "Email verified successfully"

    async def test_force_email_verify_already_verified(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Returns 400 if user email is already verified."""
        user = await UserFactory.create(
            db_session,
            email_verified_at=datetime.now(tz=UTC),
        )

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/force-email-verify",
            headers=admin_headers,
        )

        assert response.status_code == 400
        assert "already verified" in response.json()["detail"]

    async def test_force_email_verify_user_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Returns 404 for non-existent user."""
        response = await client.post(
            f"/api/v1/admin/users/{uuid4()}/force-email-verify",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_force_email_verify_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Non-admin users cannot force verify emails."""
        user = await UserFactory.create(db_session)
        response = await client.post(
            f"/api/v1/admin/users/{user.id}/force-email-verify",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# Login History Tests
# =============================================================================


class TestLoginHistory:
    """Tests for GET /admin/users/{user_id}/login-history."""

    async def test_get_login_history_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get user login history."""
        user = await UserFactory.create(db_session)

        # Create some audit log entries for login events
        for _ in range(3):
            log = AuditLog(
                user_id=user.id,
                action="login",
                resource_type="session",
                status="success",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0",
            )
            db_session.add(log)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/login-history",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert data["total"] == 3
        assert len(data["entries"]) == 3
        assert data["entries"][0]["ip_address"] == "127.0.0.1"
        assert data["entries"][0]["success"] is True

    async def test_get_login_history_pagination(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Login history supports pagination."""
        user = await UserFactory.create(db_session)

        for _ in range(5):
            log = AuditLog(
                user_id=user.id,
                action="login",
                resource_type="session",
                status="success",
            )
            db_session.add(log)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/login-history?page=1&page_size=2",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_get_login_history_user_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Returns 404 for non-existent user."""
        response = await client.get(
            f"/api/v1/admin/users/{uuid4()}/login-history",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_get_login_history_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Non-admin users cannot view login history."""
        user = await UserFactory.create(db_session)
        response = await client.get(
            f"/api/v1/admin/users/{user.id}/login-history",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# User Activity Tests
# =============================================================================


class TestUserActivity:
    """Tests for GET /admin/users/{user_id}/activity."""

    async def test_get_user_activity_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get user activity feed."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        await DesignFactory.create(db_session, project=project)

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/activity",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert data["total"] >= 2  # At least project + design
        # Verify activity types present
        types = {a["type"] for a in data["activities"]}
        assert "design_created" in types
        assert "project_created" in types

    async def test_get_user_activity_with_files(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Activity includes file uploads."""
        user = await UserFactory.create(db_session)
        await FileFactory.create(db_session, user=user)

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/activity",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        types = {a["type"] for a in data["activities"]}
        assert "file_uploaded" in types

    async def test_get_user_activity_pagination(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Activity feed supports pagination."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        for _ in range(5):
            await DesignFactory.create(db_session, project=project)

        response = await client.get(
            f"/api/v1/admin/users/{user.id}/activity?page=1&page_size=3",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) == 3
        assert data["total"] >= 6  # 5 designs + 1 project

    async def test_get_user_activity_user_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Returns 404 for non-existent user."""
        response = await client.get(
            f"/api/v1/admin/users/{uuid4()}/activity",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_get_user_activity_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Non-admin users cannot view activity feeds."""
        user = await UserFactory.create(db_session)
        response = await client.get(
            f"/api/v1/admin/users/{user.id}/activity",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# Bulk User Action Tests
# =============================================================================


class TestBulkUserAction:
    """Tests for POST /admin/users/bulk-action."""

    async def test_bulk_suspend_users_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can bulk suspend users."""
        users = await UserFactory.create_batch(db_session, 3)
        user_ids = [str(u.id) for u in users]

        response = await client.post(
            "/api/v1/admin/users/bulk-action",
            json={
                "action": "suspend",
                "user_ids": user_ids,
                "reason": "Test suspension",
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["success_count"] == 3
        assert data["failure_count"] == 0

    async def test_bulk_unsuspend_users_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can bulk unsuspend users."""
        users = await UserFactory.create_batch(db_session, 2, status="suspended")
        # Set extra_data for suspended users so unsuspend works
        for u in users:
            u.extra_data = {"suspension_reason": "test"}
        await db_session.commit()

        user_ids = [str(u.id) for u in users]

        response = await client.post(
            "/api/v1/admin/users/bulk-action",
            json={"action": "unsuspend", "user_ids": user_ids},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2

    async def test_bulk_delete_users_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can bulk soft-delete users."""
        users = await UserFactory.create_batch(db_session, 2)
        user_ids = [str(u.id) for u in users]

        response = await client.post(
            "/api/v1/admin/users/bulk-action",
            json={"action": "delete", "user_ids": user_ids},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2

    async def test_bulk_action_nonexistent_user(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Bulk action reports failure for non-existent users."""
        response = await client.post(
            "/api/v1/admin/users/bulk-action",
            json={"action": "suspend", "user_ids": [str(uuid4())]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["failure_count"] == 1
        assert len(data["errors"]) == 1

    async def test_bulk_action_invalid_action(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Invalid bulk action returns 422."""
        response = await client.post(
            "/api/v1/admin/users/bulk-action",
            json={"action": "invalid", "user_ids": [str(uuid4())]},
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_bulk_action_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot perform bulk actions."""
        response = await client.post(
            "/api/v1/admin/users/bulk-action",
            json={"action": "suspend", "user_ids": [str(uuid4())]},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# User Export Tests
# =============================================================================


class TestUserExport:
    """Tests for GET /admin/users/export."""

    async def test_export_users_csv_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can export user list as CSV."""
        await UserFactory.create_batch(db_session, 3)

        response = await client.get(
            "/api/v1/admin/users/export", headers=admin_headers
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        content = response.text
        assert "id,email,display_name" in content

    async def test_export_users_with_search_filter(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """User export supports search filter."""
        await UserFactory.create(db_session, email="exportme@test.com")
        await UserFactory.create(db_session, email="other@test.com")

        response = await client.get(
            "/api/v1/admin/users/export?search=exportme",
            headers=admin_headers,
        )

        assert response.status_code == 200
        content = response.text
        assert "exportme@test.com" in content

    async def test_export_users_with_role_filter(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """User export supports role filter."""
        await UserFactory.create(db_session, role="moderator")

        response = await client.get(
            "/api/v1/admin/users/export?role=moderator",
            headers=admin_headers,
        )

        assert response.status_code == 200
        content = response.text
        assert "moderator" in content

    async def test_export_users_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot export user list."""
        response = await client.get(
            "/api/v1/admin/users/export", headers=auth_headers
        )
        assert response.status_code == 403


# =============================================================================
# Design Transfer Tests
# =============================================================================


class TestDesignTransfer:
    """Tests for POST /admin/designs/{design_id}/transfer."""

    async def test_transfer_design_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can transfer design ownership."""
        user1 = await UserFactory.create(db_session)
        user2 = await UserFactory.create(db_session)
        project1 = await ProjectFactory.create(db_session, user=user1)
        project2 = await ProjectFactory.create(db_session, user=user2)
        design = await DesignFactory.create(db_session, project=project1)

        response = await client.post(
            f"/api/v1/admin/designs/{design.id}/transfer",
            json={"new_owner_id": str(user2.id)},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user2.id)
        assert data["user_email"] == user2.email

    async def test_transfer_design_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Returns 404 for non-existent design."""
        response = await client.post(
            f"/api/v1/admin/designs/{uuid4()}/transfer",
            json={"new_owner_id": str(uuid4())},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_transfer_design_new_owner_not_found(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Returns 404 when new owner doesn't exist."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project)

        response = await client.post(
            f"/api/v1/admin/designs/{design.id}/transfer",
            json={"new_owner_id": str(uuid4())},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_transfer_design_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Non-admin users cannot transfer designs."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project)

        response = await client.post(
            f"/api/v1/admin/designs/{design.id}/transfer",
            json={"new_owner_id": str(uuid4())},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# Design Versions Tests
# =============================================================================


class TestDesignVersions:
    """Tests for GET /admin/designs/{design_id}/versions."""

    async def test_get_design_versions_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get design version history."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project)
        await DesignVersionFactory.create(
            db_session, design=design, version_number=1
        )
        await DesignVersionFactory.create(
            db_session, design=design, version_number=2
        )

        response = await client.get(
            f"/api/v1/admin/designs/{design.id}/versions",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["versions"]) == 2
        # Should be ordered by version_number desc
        assert data["versions"][0]["version_number"] >= data["versions"][1]["version_number"]

    async def test_get_design_versions_pagination(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Design versions support pagination."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project)
        for i in range(5):
            await DesignVersionFactory.create(
                db_session, design=design, version_number=i + 1
            )

        response = await client.get(
            f"/api/v1/admin/designs/{design.id}/versions?page=1&page_size=2",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["versions"]) == 2
        assert data["total"] == 5

    async def test_get_design_versions_not_found(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Returns 404 for non-existent design."""
        response = await client.get(
            f"/api/v1/admin/designs/{uuid4()}/versions",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_get_design_versions_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Non-admin users cannot view design versions."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project)

        response = await client.get(
            f"/api/v1/admin/designs/{design.id}/versions",
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# Bulk Project Action Tests
# =============================================================================


class TestBulkProjectAction:
    """Tests for POST /admin/projects/bulk-action."""

    async def test_bulk_delete_projects_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can bulk delete projects."""
        user = await UserFactory.create(db_session)
        projects = [
            await ProjectFactory.create(db_session, user=user) for _ in range(3)
        ]
        project_ids = [str(p.id) for p in projects]

        response = await client.post(
            "/api/v1/admin/projects/bulk-action",
            json={"action": "delete", "project_ids": project_ids},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["success_count"] == 3

    async def test_bulk_suspend_projects_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can bulk suspend projects."""
        user = await UserFactory.create(db_session)
        projects = [
            await ProjectFactory.create(db_session, user=user) for _ in range(2)
        ]
        project_ids = [str(p.id) for p in projects]

        response = await client.post(
            "/api/v1/admin/projects/bulk-action",
            json={
                "action": "suspend",
                "project_ids": project_ids,
                "reason": "Test suspension",
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2

    async def test_bulk_transfer_projects_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can bulk transfer projects."""
        user1 = await UserFactory.create(db_session)
        user2 = await UserFactory.create(db_session)
        projects = [
            await ProjectFactory.create(db_session, user=user1) for _ in range(2)
        ]
        project_ids = [str(p.id) for p in projects]

        response = await client.post(
            "/api/v1/admin/projects/bulk-action",
            json={
                "action": "transfer",
                "project_ids": project_ids,
                "target": str(user2.id),
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2

    async def test_bulk_transfer_projects_missing_target(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Bulk transfer without target returns 400."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        response = await client.post(
            "/api/v1/admin/projects/bulk-action",
            json={"action": "transfer", "project_ids": [str(project.id)]},
            headers=admin_headers,
        )
        assert response.status_code == 400

    async def test_bulk_project_action_invalid_action(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Invalid bulk action returns 422."""
        response = await client.post(
            "/api/v1/admin/projects/bulk-action",
            json={"action": "invalid", "project_ids": [str(uuid4())]},
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_bulk_project_action_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot perform bulk project actions."""
        response = await client.post(
            "/api/v1/admin/projects/bulk-action",
            json={"action": "delete", "project_ids": [str(uuid4())]},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# Bulk Design Action Tests
# =============================================================================


class TestBulkDesignAction:
    """Tests for POST /admin/designs/bulk-action."""

    async def test_bulk_delete_designs_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can bulk delete designs."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        designs = [
            await DesignFactory.create(db_session, project=project) for _ in range(3)
        ]
        design_ids = [str(d.id) for d in designs]

        response = await client.post(
            "/api/v1/admin/designs/bulk-action",
            json={"action": "delete", "design_ids": design_ids},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["success_count"] == 3

    async def test_bulk_restore_designs_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can bulk restore soft-deleted designs."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        designs = [
            await DesignFactory.create(db_session, project=project) for _ in range(2)
        ]
        # Soft-delete them
        for d in designs:
            d.deleted_at = datetime.now(tz=UTC)
        await db_session.commit()

        design_ids = [str(d.id) for d in designs]

        response = await client.post(
            "/api/v1/admin/designs/bulk-action",
            json={"action": "restore", "design_ids": design_ids},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2

    async def test_bulk_transfer_designs_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can bulk transfer designs."""
        user1 = await UserFactory.create(db_session)
        user2 = await UserFactory.create(db_session)
        project1 = await ProjectFactory.create(db_session, user=user1)
        _project2 = await ProjectFactory.create(db_session, user=user2)
        designs = [
            await DesignFactory.create(db_session, project=project1) for _ in range(2)
        ]
        design_ids = [str(d.id) for d in designs]

        response = await client.post(
            "/api/v1/admin/designs/bulk-action",
            json={
                "action": "transfer",
                "design_ids": design_ids,
                "target": str(user2.id),
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2

    async def test_bulk_transfer_designs_missing_target(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Bulk transfer without target returns 400."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project)

        response = await client.post(
            "/api/v1/admin/designs/bulk-action",
            json={"action": "transfer", "design_ids": [str(design.id)]},
            headers=admin_headers,
        )
        assert response.status_code == 400

    async def test_bulk_design_action_nonexistent(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Bulk action reports failure for non-existent designs."""
        response = await client.post(
            "/api/v1/admin/designs/bulk-action",
            json={"action": "delete", "design_ids": [str(uuid4())]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["failure_count"] == 1

    async def test_bulk_design_action_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot perform bulk design actions."""
        response = await client.post(
            "/api/v1/admin/designs/bulk-action",
            json={"action": "delete", "design_ids": [str(uuid4())]},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# Template Reorder Tests
# =============================================================================


class TestTemplateReorder:
    """Tests for PATCH /admin/templates/reorder."""

    async def test_reorder_templates_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can reorder templates."""
        templates = await TemplateFactory.create_batch(db_session, 3)
        ordered_ids = [str(t.id) for t in reversed(templates)]

        response = await client.patch(
            "/api/v1/admin/templates/reorder",
            json={"ordered_ids": ordered_ids},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reordered_count"] == 3
        assert "Reordered" in data["message"]

    async def test_reorder_templates_partial_ids(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Reorder with some non-existent IDs still succeeds for valid ones."""
        template = await TemplateFactory.create(db_session)

        response = await client.patch(
            "/api/v1/admin/templates/reorder",
            json={"ordered_ids": [str(template.id), str(uuid4())]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reordered_count"] == 1

    async def test_reorder_templates_empty_list(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Empty ordered_ids list returns 422."""
        response = await client.patch(
            "/api/v1/admin/templates/reorder",
            json={"ordered_ids": []},
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_reorder_templates_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot reorder templates."""
        response = await client.patch(
            "/api/v1/admin/templates/reorder",
            json={"ordered_ids": [str(uuid4())]},
            headers=auth_headers,
        )
        assert response.status_code == 403


# =============================================================================
# Template Analytics Tests
# =============================================================================


class TestTemplateAnalytics:
    """Tests for GET /admin/templates/analytics."""

    async def test_get_template_analytics_success(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get template usage analytics."""
        template = await TemplateFactory.create(db_session)
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        await DesignFactory.create(
            db_session, project=project, template_id=template.id
        )

        response = await client.get(
            "/api/v1/admin/templates/analytics",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "total_template_designs" in data
        assert data["total_template_designs"] >= 1
        # At least one template with usage
        assert len(data["templates"]) >= 1

    async def test_get_template_analytics_most_popular(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Analytics correctly identifies most popular template."""
        template1 = await TemplateFactory.create(db_session)
        template2 = await TemplateFactory.create(db_session)
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        # Template1 gets 3 designs, template2 gets 1
        for _ in range(3):
            await DesignFactory.create(
                db_session, project=project, template_id=template1.id
            )
        await DesignFactory.create(
            db_session, project=project, template_id=template2.id
        )

        response = await client.get(
            "/api/v1/admin/templates/analytics",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["most_popular_template_id"] == str(template1.id)
        assert data["most_popular_template_name"] == template1.name

    async def test_get_template_analytics_empty(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Analytics works with no templates."""
        response = await client.get(
            "/api/v1/admin/templates/analytics",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_template_designs"] == 0
        assert data["most_popular_template_id"] is None

    async def test_get_template_analytics_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot view template analytics."""
        response = await client.get(
            "/api/v1/admin/templates/analytics",
            headers=auth_headers,
        )
        assert response.status_code == 403
