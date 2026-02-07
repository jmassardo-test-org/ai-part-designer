"""
Tests for admin API endpoints.

Tests administrative functionality including:
- Analytics endpoints
- User management
- Project/design management
- Template management
- Job management
- Content moderation
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    Counter,
    DesignFactory,
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
# Admin Access Tests
# =============================================================================


class TestAdminAccess:
    """Tests for admin access control."""

    async def test_admin_endpoint_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/admin/users")
        assert response.status_code == 401

    async def test_admin_endpoint_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Should return 403 for non-admin users."""
        response = await client.get("/api/v1/admin/users", headers=auth_headers)
        assert response.status_code == 403

    async def test_admin_analytics_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot access analytics."""
        response = await client.get("/api/v1/admin/analytics/overview", headers=auth_headers)
        assert response.status_code == 403

    async def test_admin_projects_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot list all projects."""
        response = await client.get("/api/v1/admin/projects", headers=auth_headers)
        assert response.status_code == 403

    async def test_admin_templates_forbidden_non_admin(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-admin users cannot manage templates."""
        response = await client.get("/api/v1/admin/templates", headers=auth_headers)
        assert response.status_code == 403

    async def test_admin_jobs_forbidden_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Non-admin users cannot view all jobs."""
        response = await client.get("/api/v1/admin/jobs", headers=auth_headers)
        assert response.status_code == 403


# =============================================================================
# Analytics Endpoint Tests
# =============================================================================


class TestAdminAnalytics:
    """Tests for admin analytics endpoints."""

    async def test_get_analytics_overview(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get platform analytics overview."""
        # Create some test data
        await UserFactory.create_batch(db_session, 3)

        response = await client.get("/api/v1/admin/analytics/overview", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        # At least admin user exists
        assert data["total_users"] >= 1
        assert "active_users_daily" in data
        assert "active_users_weekly" in data
        assert "active_users_monthly" in data
        assert "new_signups_today" in data
        assert "total_projects" in data
        assert "total_designs" in data
        assert "pending_jobs" in data

    async def test_get_user_analytics(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get user analytics for a period."""
        await UserFactory.create_batch(db_session, 2)

        response = await client.get(
            "/api/v1/admin/analytics/users?period=30d", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "30d"
        assert "total_users" in data
        assert "new_users" in data
        assert "active_users" in data

    async def test_get_user_analytics_invalid_period(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Invalid period returns 422."""
        response = await client.get(
            "/api/v1/admin/analytics/users?period=invalid", headers=admin_headers
        )
        assert response.status_code == 422

    async def test_get_generation_analytics(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get generation analytics."""
        # Create some designs
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        await DesignFactory.create(db_session, project=project, source_type="ai_generated")
        await DesignFactory.create(db_session, project=project, source_type="template")

        response = await client.get(
            "/api/v1/admin/analytics/generations?period=7d", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "7d"
        assert "total_generations" in data
        assert "ai_generations" in data
        assert "template_generations" in data

    async def test_get_job_analytics(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get job analytics."""
        user = await UserFactory.create(db_session)
        await JobFactory.create(db_session, user=user, status="completed")
        await JobFactory.create_failed(db_session, user=user)

        response = await client.get(
            "/api/v1/admin/analytics/jobs?period=30d", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "completed_jobs" in data
        assert "failed_jobs" in data
        assert "success_rate" in data

    async def test_get_storage_analytics(self, client: AsyncClient, admin_headers: dict):
        """Admin can get storage analytics."""
        response = await client.get("/api/v1/admin/analytics/storage", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_storage_bytes" in data
        assert "used_storage_bytes" in data


# =============================================================================
# User Management Tests
# =============================================================================


class TestAdminUserManagement:
    """Tests for admin user management."""

    async def test_list_users(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can list all users."""
        await UserFactory.create_batch(db_session, 3)

        response = await client.get("/api/v1/admin/users", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 3

    async def test_list_users_with_pagination(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can paginate user list."""
        await UserFactory.create_batch(db_session, 5)

        response = await client.get("/api/v1/admin/users?page=1&page_size=2", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) <= 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_list_users_with_search(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can search users by email or display name."""
        await UserFactory.create(db_session, email="searchable@test.com")
        await UserFactory.create(db_session, email="other@test.com")

        response = await client.get("/api/v1/admin/users?search=searchable", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert any("searchable" in u["email"] for u in data["users"])

    async def test_list_users_with_role_filter(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter users by role."""
        await UserFactory.create(db_session, role="moderator")
        await UserFactory.create(db_session, role="user")

        response = await client.get("/api/v1/admin/users?role=moderator", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert all(u["role"] == "moderator" for u in data["users"])

    async def test_list_users_with_status_filter(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter users by status."""
        await UserFactory.create(db_session, status="suspended")
        await UserFactory.create(db_session, status="active")

        response = await client.get("/api/v1/admin/users?status=suspended", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert all(u["status"] == "suspended" for u in data["users"])

    async def test_get_user_details(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get complete user details."""
        user = await UserFactory.create(db_session)

        response = await client.get(f"/api/v1/admin/users/{user.id}", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email"] == user.email
        assert "project_count" in data
        assert "design_count" in data

    async def test_get_user_details_not_found(self, client: AsyncClient, admin_headers: dict):
        """Returns 404 for nonexistent user."""
        response = await client.get(f"/api/v1/admin/users/{uuid4()}", headers=admin_headers)
        assert response.status_code == 404

    async def test_update_user_profile(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can update user profile."""
        user = await UserFactory.create(db_session)

        response = await client.patch(
            f"/api/v1/admin/users/{user.id}",
            headers=admin_headers,
            json={"display_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"

    async def test_update_user_role(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can change user role."""
        user = await UserFactory.create(db_session, role="user")

        response = await client.patch(
            f"/api/v1/admin/users/{user.id}", headers=admin_headers, json={"role": "moderator"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "moderator"

    async def test_update_user_role_invalid(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Invalid role returns 422."""
        user = await UserFactory.create(db_session)

        response = await client.patch(
            f"/api/v1/admin/users/{user.id}",
            headers=admin_headers,
            json={"role": "superadmin"},  # Invalid role
        )

        assert response.status_code == 422

    async def test_suspend_user(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can suspend a user."""
        user = await UserFactory.create(db_session, status="active")

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/suspend",
            headers=admin_headers,
            json={"reason": "Terms violation"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suspended"

    async def test_suspend_user_with_duration(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can suspend a user with duration."""
        user = await UserFactory.create(db_session, status="active")

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/suspend",
            headers=admin_headers,
            json={"reason": "Temporary ban", "duration_days": 7},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suspended"

    async def test_suspend_already_suspended_user(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Cannot suspend already suspended user."""
        user = await UserFactory.create(db_session, status="suspended")

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/suspend", headers=admin_headers, json={"reason": "Test"}
        )

        assert response.status_code == 400

    async def test_unsuspend_user(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can unsuspend a user."""
        user = await UserFactory.create(db_session, status="suspended")

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/unsuspend", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    async def test_unsuspend_non_suspended_user(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Cannot unsuspend non-suspended user."""
        user = await UserFactory.create(db_session, status="active")

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/unsuspend", headers=admin_headers
        )

        assert response.status_code == 400

    async def test_delete_user(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can soft-delete a user."""
        user = await UserFactory.create(db_session)

        response = await client.delete(f"/api/v1/admin/users/{user.id}", headers=admin_headers)

        assert response.status_code == 204

    async def test_impersonate_user(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can impersonate a user."""
        user = await UserFactory.create(db_session, role="user")

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/impersonate", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user_id"] == str(user.id)
        assert "audit_id" in data

    async def test_cannot_impersonate_admin(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Cannot impersonate another admin."""
        admin = await UserFactory.create_admin(db_session)

        response = await client.post(
            f"/api/v1/admin/users/{admin.id}/impersonate", headers=admin_headers
        )

        assert response.status_code == 400


# =============================================================================
# Project Management Tests
# =============================================================================


class TestAdminProjectManagement:
    """Tests for admin project management."""

    async def test_list_all_projects(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can list all projects."""
        user = await UserFactory.create(db_session)
        await ProjectFactory.create(db_session, user=user)
        await ProjectFactory.create(db_session, user=user)

        response = await client.get("/api/v1/admin/projects", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert data["total"] >= 2

    async def test_list_projects_filter_by_user(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter projects by user."""
        user1 = await UserFactory.create(db_session)
        user2 = await UserFactory.create(db_session)
        await ProjectFactory.create(db_session, user=user1)
        await ProjectFactory.create(db_session, user=user2)

        response = await client.get(
            f"/api/v1/admin/projects?user_id={user1.id}", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(p["user_id"] == str(user1.id) for p in data["projects"])

    async def test_get_project_details(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get project details."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        response = await client.get(f"/api/v1/admin/projects/{project.id}", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(project.id)
        assert "design_count" in data

    async def test_delete_project(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can soft-delete a project."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        response = await client.delete(
            f"/api/v1/admin/projects/{project.id}", headers=admin_headers
        )

        assert response.status_code == 204

    async def test_transfer_project_ownership(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can transfer project ownership."""
        user1 = await UserFactory.create(db_session)
        user2 = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user1)

        response = await client.post(
            f"/api/v1/admin/projects/{project.id}/transfer",
            headers=admin_headers,
            json={"new_owner_id": str(user2.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user2.id)

    async def test_transfer_project_to_nonexistent_user(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Cannot transfer to nonexistent user."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        response = await client.post(
            f"/api/v1/admin/projects/{project.id}/transfer",
            headers=admin_headers,
            json={"new_owner_id": str(uuid4())},
        )

        assert response.status_code == 404

    async def test_suspend_project(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can suspend a project."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        response = await client.post(
            f"/api/v1/admin/projects/{project.id}/suspend",
            headers=admin_headers,
            json={"reason": "Policy violation"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suspended"

    async def test_suspend_project_already_suspended(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Cannot suspend already suspended project."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user, status="suspended")

        response = await client.post(
            f"/api/v1/admin/projects/{project.id}/suspend",
            headers=admin_headers,
            json={"reason": "Policy violation"},
        )

        assert response.status_code == 400

    async def test_unsuspend_project(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can unsuspend a project."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user, status="suspended")

        response = await client.post(
            f"/api/v1/admin/projects/{project.id}/unsuspend", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    async def test_unsuspend_project_not_suspended(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Cannot unsuspend non-suspended project."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)

        response = await client.post(
            f"/api/v1/admin/projects/{project.id}/unsuspend", headers=admin_headers
        )

        assert response.status_code == 400

    async def test_list_projects_filter_by_status(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter projects by status."""
        user = await UserFactory.create(db_session)
        await ProjectFactory.create(db_session, user=user, status="active")
        await ProjectFactory.create(db_session, user=user, status="suspended")

        response = await client.get(
            "/api/v1/admin/projects?status=suspended", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(p["status"] == "suspended" for p in data["projects"])


# =============================================================================
# Design Management Tests
# =============================================================================


class TestAdminDesignManagement:
    """Tests for admin design management."""

    async def test_list_all_designs(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can list all designs."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        await DesignFactory.create(db_session, project=project)
        await DesignFactory.create(db_session, project=project)

        response = await client.get("/api/v1/admin/designs", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "designs" in data
        assert data["total"] >= 2

    async def test_list_designs_filter_by_source_type(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter designs by source type."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        await DesignFactory.create(db_session, project=project, source_type="ai_generated")
        await DesignFactory.create(db_session, project=project, source_type="template")

        response = await client.get(
            "/api/v1/admin/designs?source_type=ai_generated", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(d["source_type"] == "ai_generated" for d in data["designs"])

    async def test_list_designs_filter_by_status(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter designs by status."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        await DesignFactory.create(db_session, project=project, status="ready")
        await DesignFactory.create(db_session, project=project, status="failed")

        response = await client.get("/api/v1/admin/designs?status=failed", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert all(d["status"] == "failed" for d in data["designs"])

    async def test_get_design_details(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get design details."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project)

        response = await client.get(f"/api/v1/admin/designs/{design.id}", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(design.id)

    async def test_delete_design(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can soft-delete a design."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project)

        response = await client.delete(f"/api/v1/admin/designs/{design.id}", headers=admin_headers)

        assert response.status_code == 204

    async def test_restore_deleted_design(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can restore a soft-deleted design."""

        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project)

        # Soft delete
        design.deleted_at = datetime.now(tz=UTC)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/admin/designs/{design.id}/restore", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(design.id)

    async def test_change_design_visibility(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can change design visibility."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, project=project, is_public=False)

        response = await client.patch(
            f"/api/v1/admin/designs/{design.id}/visibility",
            headers=admin_headers,
            json={"is_public": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_public"] is True


# =============================================================================
# Template Management Tests
# =============================================================================


class TestAdminTemplateManagement:
    """Tests for admin template management."""

    async def test_list_templates(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can list all templates."""
        await TemplateFactory.create_batch(db_session, 3)

        response = await client.get("/api/v1/admin/templates", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert data["total"] >= 3

    async def test_list_templates_filter_by_category(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter templates by category."""
        await TemplateFactory.create(db_session, category="mechanical")
        await TemplateFactory.create(db_session, category="enclosures")

        response = await client.get(
            "/api/v1/admin/templates?category=mechanical", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(t["category"] == "mechanical" for t in data["templates"])

    async def test_list_templates_filter_by_active(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter templates by active status."""
        await TemplateFactory.create(db_session, is_active=True)
        await TemplateFactory.create(db_session, is_active=False)

        response = await client.get("/api/v1/admin/templates?is_active=true", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert all(t["is_active"] is True for t in data["templates"])

    async def test_get_template_details(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get template details."""
        template = await TemplateFactory.create(db_session)

        response = await client.get(f"/api/v1/admin/templates/{template.id}", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(template.id)
        assert data["slug"] == template.slug

    async def test_create_template(self, client: AsyncClient, admin_headers: dict):
        """Admin can create a new template."""
        response = await client.post(
            "/api/v1/admin/templates",
            headers=admin_headers,
            json={
                "name": "New Template",
                "slug": "new-template-unique",
                "category": "mechanical",
                "parameters": {"length": {"type": "number", "default": 100}},
                "default_values": {"length": 100},
                "cadquery_script": "# test script",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Template"
        assert data["slug"] == "new-template-unique"

    async def test_create_template_duplicate_slug(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Cannot create template with duplicate slug."""
        template = await TemplateFactory.create(db_session)

        response = await client.post(
            "/api/v1/admin/templates",
            headers=admin_headers,
            json={
                "name": "Another Template",
                "slug": template.slug,  # Duplicate
                "category": "mechanical",
                "parameters": {},
                "default_values": {},
                "cadquery_script": "# test",
            },
        )

        assert response.status_code == 400

    async def test_update_template(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can update a template."""
        template = await TemplateFactory.create(db_session)

        response = await client.patch(
            f"/api/v1/admin/templates/{template.id}",
            headers=admin_headers,
            json={"name": "Updated Name", "min_tier": "pro"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["min_tier"] == "pro"

    async def test_delete_template(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can delete a template."""
        template = await TemplateFactory.create(db_session)

        response = await client.delete(
            f"/api/v1/admin/templates/{template.id}", headers=admin_headers
        )

        assert response.status_code == 204

    async def test_enable_template(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can enable a template."""
        template = await TemplateFactory.create(db_session, is_active=False)

        response = await client.post(
            f"/api/v1/admin/templates/{template.id}/enable", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    async def test_disable_template(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can disable a template."""
        template = await TemplateFactory.create(db_session, is_active=True)

        response = await client.post(
            f"/api/v1/admin/templates/{template.id}/disable", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_feature_template(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can feature a template."""
        template = await TemplateFactory.create(db_session, is_featured=False)

        response = await client.post(
            f"/api/v1/admin/templates/{template.id}/feature", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_featured"] is True

    async def test_unfeature_template(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can unfeature a template."""
        template = await TemplateFactory.create(db_session, is_featured=True)

        response = await client.post(
            f"/api/v1/admin/templates/{template.id}/unfeature", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_featured"] is False

    async def test_clone_template(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can clone a template."""
        template = await TemplateFactory.create(db_session)

        response = await client.post(
            f"/api/v1/admin/templates/{template.id}/clone", headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] != str(template.id)
        assert "(Copy)" in data["name"]
        assert data["is_active"] is False  # Clone starts inactive


# =============================================================================
# Job Management Tests
# =============================================================================


class TestAdminJobManagement:
    """Tests for admin job management."""

    async def test_list_jobs(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can list all jobs."""
        user = await UserFactory.create(db_session)
        await JobFactory.create(db_session, user=user)
        await JobFactory.create(db_session, user=user)

        response = await client.get("/api/v1/admin/jobs", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert data["total"] >= 2

    async def test_list_jobs_filter_by_status(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter jobs by status."""
        user = await UserFactory.create(db_session)
        await JobFactory.create(db_session, user=user, status="pending")
        await JobFactory.create_completed(db_session, user=user)

        response = await client.get("/api/v1/admin/jobs?status=pending", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert all(j["status"] == "pending" for j in data["jobs"])

    async def test_list_jobs_filter_by_type(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can filter jobs by type."""
        user = await UserFactory.create(db_session)
        await JobFactory.create(db_session, user=user, job_type="ai_generation")
        await JobFactory.create(db_session, user=user, job_type="export")

        response = await client.get(
            "/api/v1/admin/jobs?job_type=ai_generation", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(j["job_type"] == "ai_generation" for j in data["jobs"])

    async def test_get_job_details(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get job details."""
        user = await UserFactory.create(db_session)
        job = await JobFactory.create(db_session, user=user)

        response = await client.get(f"/api/v1/admin/jobs/{job.id}", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job.id)
        assert data["job_type"] == job.job_type

    async def test_cancel_pending_job(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can cancel a pending job."""
        user = await UserFactory.create(db_session)
        job = await JobFactory.create(db_session, user=user, status="pending")

        response = await client.post(f"/api/v1/admin/jobs/{job.id}/cancel", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    async def test_cancel_processing_job(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can cancel a processing job."""
        user = await UserFactory.create(db_session)
        job = await JobFactory.create(db_session, user=user, status="processing")

        response = await client.post(f"/api/v1/admin/jobs/{job.id}/cancel", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    async def test_cannot_cancel_completed_job(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Cannot cancel already completed job."""
        user = await UserFactory.create(db_session)
        job = await JobFactory.create_completed(db_session, user=user)

        response = await client.post(f"/api/v1/admin/jobs/{job.id}/cancel", headers=admin_headers)

        assert response.status_code == 400

    async def test_retry_failed_job(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can retry a failed job."""
        user = await UserFactory.create(db_session)
        job = await JobFactory.create_failed(db_session, user=user)

        response = await client.post(f"/api/v1/admin/jobs/{job.id}/retry", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["progress"] == 0

    async def test_cannot_retry_non_failed_job(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Cannot retry non-failed job."""
        user = await UserFactory.create(db_session)
        job = await JobFactory.create(db_session, user=user, status="pending")

        response = await client.post(f"/api/v1/admin/jobs/{job.id}/retry", headers=admin_headers)

        assert response.status_code == 400


# =============================================================================
# Moderation Queue Tests
# =============================================================================


class TestModerationQueue:
    """Tests for content moderation queue."""

    async def test_get_moderation_queue(self, client: AsyncClient, admin_headers: dict):
        """Admin can get moderation queue."""
        response = await client.get("/api/v1/admin/moderation/queue", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "pending_count" in data

    async def test_get_moderation_stats(self, client: AsyncClient, admin_headers: dict):
        """Admin can get moderation stats."""
        response = await client.get("/api/v1/admin/moderation/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "pending_count" in data
        assert "escalated_count" in data
        assert "approved_today" in data
        assert "rejected_today" in data


# =============================================================================
# Subscription Management Tests
# =============================================================================


class TestSubscriptionManagement:
    """Tests for admin subscription management."""

    async def test_list_subscriptions(self, client: AsyncClient, admin_headers: dict):
        """Admin can list all subscriptions."""
        response = await client.get("/api/v1/admin/subscriptions", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    async def test_list_subscriptions_with_filters(self, client: AsyncClient, admin_headers: dict):
        """Admin can filter subscriptions by status."""
        response = await client.get(
            "/api/v1/admin/subscriptions?status_filter=active", headers=admin_headers
        )

        assert response.status_code == 200

    async def test_get_user_credits(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can get user credit balance."""
        user = await UserFactory.create(db_session)

        response = await client.get(f"/api/v1/admin/users/{user.id}/credits", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "balance" in data

    async def test_add_user_credits(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin can add credits to user."""
        user = await UserFactory.create(db_session)

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/credits/add?amount=100&reason=Test",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "new_balance" in data


# =============================================================================
# Organization Management Tests
# =============================================================================


class TestOrganizationManagement:
    """Tests for admin organization management."""

    async def test_list_organizations(self, client: AsyncClient, admin_headers: dict):
        """Admin can list all organizations."""
        response = await client.get("/api/v1/admin/organizations", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_organizations_with_search(self, client: AsyncClient, admin_headers: dict):
        """Admin can search organizations."""
        response = await client.get(
            "/api/v1/admin/organizations?search=test", headers=admin_headers
        )

        assert response.status_code == 200


# =============================================================================
# Component Management Tests
# =============================================================================


class TestComponentManagement:
    """Tests for admin component library management."""

    async def test_list_components(self, client: AsyncClient, admin_headers: dict):
        """Admin can list all components."""
        response = await client.get("/api/v1/admin/components", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_library_components_only(self, client: AsyncClient, admin_headers: dict):
        """Admin can filter to library components only."""
        response = await client.get(
            "/api/v1/admin/components?library_only=true", headers=admin_headers
        )

        assert response.status_code == 200


# =============================================================================
# Notification Management Tests
# =============================================================================


class TestNotificationManagement:
    """Tests for admin notification management."""

    async def test_list_notifications(self, client: AsyncClient, admin_headers: dict):
        """Admin can list all notifications."""
        response = await client.get("/api/v1/admin/notifications", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_create_announcement(self, client: AsyncClient, admin_headers: dict):
        """Admin can create system announcement."""
        response = await client.post(
            "/api/v1/admin/notifications/announcement",
            headers=admin_headers,
            json={"title": "Test Announcement", "message": "This is a test announcement."},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


# =============================================================================
# Storage Management Tests
# =============================================================================


class TestStorageManagement:
    """Tests for admin file/storage management."""

    async def test_get_storage_stats(self, client: AsyncClient, admin_headers: dict):
        """Admin can get storage statistics."""
        response = await client.get("/api/v1/admin/storage/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_files" in data
        assert "total_size_bytes" in data
        assert "total_size_gb" in data
        assert "files_by_type" in data
        assert "top_users" in data

    async def test_list_files(self, client: AsyncClient, admin_headers: dict):
        """Admin can list all files."""
        response = await client.get("/api/v1/admin/files", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


# =============================================================================
# Audit Log Tests
# =============================================================================


class TestAuditLogs:
    """Tests for admin audit log access."""

    async def test_get_audit_logs(self, client: AsyncClient, admin_headers: dict):
        """Admin can get audit logs."""
        response = await client.get("/api/v1/admin/audit-logs", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_filter_audit_logs_by_action(self, client: AsyncClient, admin_headers: dict):
        """Admin can filter audit logs by action."""
        response = await client.get("/api/v1/admin/audit-logs?action=login", headers=admin_headers)

        assert response.status_code == 200


# =============================================================================
# API Key Management Tests
# =============================================================================


class TestAPIKeyManagement:
    """Tests for admin API key management."""

    async def test_list_api_keys(self, client: AsyncClient, admin_headers: dict):
        """Admin can list all API keys."""
        response = await client.get("/api/v1/admin/api-keys", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


# =============================================================================
# System Health Tests
# =============================================================================


class TestSystemHealth:
    """Tests for admin system health monitoring."""

    async def test_get_system_health(self, client: AsyncClient, admin_headers: dict):
        """Admin can get system health status."""
        response = await client.get("/api/v1/admin/system/health", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "services" in data
        assert "version" in data

    async def test_get_system_version(self, client: AsyncClient, admin_headers: dict):
        """Admin can get system version info."""
        response = await client.get("/api/v1/admin/system/version", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "api_version" in data


# =============================================================================
# Audit Logging Tests
# =============================================================================


class TestAuditLogging:
    """Tests for admin action audit logging."""

    async def test_update_user_role_creates_audit_log(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Changing user role creates an audit log entry."""
        from sqlalchemy import select

        from app.models.audit import AuditLog

        user = await UserFactory.create(db_session, role="user")

        # Change role
        response = await client.patch(
            f"/api/v1/admin/users/{user.id}", headers=admin_headers, json={"role": "moderator"}
        )

        assert response.status_code == 200

        # Verify audit log entry was created
        audit_query = select(AuditLog).where(
            AuditLog.action == "admin.role.changed", AuditLog.resource_id == user.id
        )
        result = await db_session.execute(audit_query)
        audit_entry = result.scalar_one_or_none()

        assert audit_entry is not None
        assert audit_entry.changes["old_role"] == "user"
        assert audit_entry.changes["new_role"] == "moderator"

    async def test_admin_reset_password_creates_audit_log(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Admin-initiated password reset creates an audit log entry."""
        from sqlalchemy import select

        from app.models.audit import AuditLog

        user = await UserFactory.create(db_session)

        # Request password reset
        response = await client.post(
            f"/api/v1/admin/users/{user.id}/reset-password", headers=admin_headers
        )

        assert response.status_code == 200

        # Verify audit log entry was created
        audit_query = select(AuditLog).where(
            AuditLog.action == "auth.password.reset_requested", AuditLog.resource_id == user.id
        )
        result = await db_session.execute(audit_query)
        audit_entry = result.scalar_one_or_none()

        assert audit_entry is not None
        assert audit_entry.changes["target_user_email"] == user.email
