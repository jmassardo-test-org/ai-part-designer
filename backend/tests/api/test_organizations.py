"""
Tests for organizations API endpoints.

Tests organization CRUD, membership, and invite operations.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMember, OrganizationRole

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def test_organization(db_session: AsyncSession, test_user):
    """Create a test organization owned by test_user."""
    org = Organization(
        id=uuid4(),
        name="Test Organization",
        slug=f"test-org-{uuid4().hex[:8]}",
        owner_id=test_user.id,
        settings={
            "allow_member_invites": False,
            "default_project_visibility": "private",
            "require_2fa": False,
            "allowed_domains": [],
        },
    )
    db_session.add(org)

    # Add owner as member
    member = OrganizationMember(
        id=uuid4(),
        organization_id=org.id,
        user_id=test_user.id,
        role=OrganizationRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(org)

    yield org

    # Cleanup
    try:
        await db_session.delete(member)
        await db_session.delete(org)
        await db_session.commit()
    except Exception:
        pass


# =============================================================================
# List Organizations Tests
# =============================================================================


class TestListOrganizations:
    """Tests for GET /api/v1/organizations."""

    async def test_list_organizations_success(
        self, client: AsyncClient, auth_headers: dict, test_organization
    ):
        """Should return list of user's organizations."""
        response = await client.get("/api/v1/organizations", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # At least our test org
        assert len(data) >= 1

        # Find our test org
        org_ids = [o["id"] for o in data]
        assert str(test_organization.id) in org_ids

    async def test_list_organizations_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/organizations")
        assert response.status_code == 401


# =============================================================================
# Create Organization Tests
# =============================================================================


class TestCreateOrganization:
    """Tests for POST /api/v1/organizations."""

    async def test_create_organization_success(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Should create new organization."""
        unique_slug = f"new-org-{uuid4().hex[:8]}"
        response = await client.post(
            "/api/v1/organizations",
            headers=auth_headers,
            json={
                "name": "New Organization",
                "slug": unique_slug,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Organization"
        assert data["slug"] == unique_slug

        # Cleanup - delete the created org
        org_id = data["id"]
        await client.delete(f"/api/v1/organizations/{org_id}", headers=auth_headers)

    async def test_create_organization_duplicate_slug(
        self, client: AsyncClient, auth_headers: dict, test_organization
    ):
        """Should reject duplicate slug."""
        response = await client.post(
            "/api/v1/organizations",
            headers=auth_headers,
            json={
                "name": "Another Org",
                "slug": test_organization.slug,  # Same slug
            },
        )

        assert response.status_code in [400, 409, 422]

    async def test_create_organization_invalid_slug(self, client: AsyncClient, auth_headers: dict):
        """Should reject invalid slug format."""
        response = await client.post(
            "/api/v1/organizations",
            headers=auth_headers,
            json={
                "name": "Test Org",
                "slug": "INVALID SLUG!",  # Invalid characters
            },
        )

        assert response.status_code == 422


# =============================================================================
# Get Organization Tests
# =============================================================================


class TestGetOrganization:
    """Tests for GET /api/v1/organizations/{org_id}."""

    async def test_get_organization_success(
        self, client: AsyncClient, auth_headers: dict, test_organization
    ):
        """Should return organization details."""
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_organization.id)
        assert data["name"] == test_organization.name

    async def test_get_organization_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent organization."""
        response = await client.get(
            "/api/v1/organizations/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )

        assert response.status_code == 404


# =============================================================================
# Update Organization Tests
# =============================================================================


class TestUpdateOrganization:
    """Tests for PATCH /api/v1/organizations/{org_id}."""

    async def test_update_organization_success(
        self, client: AsyncClient, auth_headers: dict, test_organization
    ):
        """Should update organization name."""
        response = await client.patch(
            f"/api/v1/organizations/{test_organization.id}",
            headers=auth_headers,
            json={"name": "Updated Org Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Org Name"


# =============================================================================
# Delete Organization Tests
# =============================================================================


class TestDeleteOrganization:
    """Tests for DELETE /api/v1/organizations/{org_id}."""

    async def test_delete_organization_success(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, test_user
    ):
        """Should delete organization."""
        # Create an org specifically for deletion
        org = Organization(
            id=uuid4(),
            name="To Delete",
            slug=f"to-delete-{uuid4().hex[:8]}",
            owner_id=test_user.id,
            settings={},
        )
        db_session.add(org)
        member = OrganizationMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=test_user.id,
            role=OrganizationRole.OWNER,
        )
        db_session.add(member)
        await db_session.commit()

        response = await client.delete(f"/api/v1/organizations/{org.id}", headers=auth_headers)

        assert response.status_code == 204

    async def test_delete_organization_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent organization."""
        response = await client.delete(
            "/api/v1/organizations/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )

        assert response.status_code == 404


# =============================================================================
# Organization Members Tests
# =============================================================================


class TestOrganizationMembers:
    """Tests for organization member endpoints."""

    async def test_list_members_success(
        self, client: AsyncClient, auth_headers: dict, test_organization
    ):
        """Should return list of organization members."""
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}/members", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # At least the owner
        assert len(data) >= 1


# =============================================================================
# Organization Features Tests
# =============================================================================


class TestOrganizationFeatures:
    """Tests for organization feature permissions endpoints."""

    async def test_get_features_success(
        self, client: AsyncClient, auth_headers: dict, test_organization
    ):
        """Should return enabled and available features."""
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}/features", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "enabled_features" in data
        assert "available_features" in data
        assert "subscription_tier" in data
        assert isinstance(data["enabled_features"], list)
        assert isinstance(data["available_features"], list)

    async def test_get_features_unauthenticated(self, client: AsyncClient, test_organization):
        """Should return 401 without authentication."""
        response = await client.get(f"/api/v1/organizations/{test_organization.id}/features")
        assert response.status_code == 401

    async def test_get_features_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent organization."""
        response = await client.get(
            "/api/v1/organizations/00000000-0000-0000-0000-000000000000/features",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_features_success(
        self, client: AsyncClient, auth_headers: dict, test_organization
    ):
        """Should update enabled features."""
        response = await client.put(
            f"/api/v1/organizations/{test_organization.id}/features",
            headers=auth_headers,
            json={"enabled_features": ["ai_generation", "templates"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "ai_generation" in data["enabled_features"]
        assert "templates" in data["enabled_features"]

    async def test_update_features_invalid_feature(
        self, client: AsyncClient, auth_headers: dict, test_organization
    ):
        """Should reject invalid feature names."""
        response = await client.put(
            f"/api/v1/organizations/{test_organization.id}/features",
            headers=auth_headers,
            json={"enabled_features": ["invalid_feature_xyz"]},
        )

        assert response.status_code == 422

    async def test_update_features_unavailable_for_tier(
        self, client: AsyncClient, auth_headers: dict, test_organization
    ):
        """Should reject features not available on the org's tier."""
        # Try to enable enterprise features on free tier
        response = await client.put(
            f"/api/v1/organizations/{test_organization.id}/features",
            headers=auth_headers,
            json={"enabled_features": ["advanced_cad", "external_storage"]},
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "invalid_features"

    async def test_has_feature_method(self, db_session: AsyncSession, test_user):
        """Test Organization.has_feature() method."""
        org = Organization(
            id=uuid4(),
            name="Test Org",
            slug=f"test-{uuid4().hex[:8]}",
            owner_id=test_user.id,
            settings={
                "enabled_features": ["ai_generation", "templates"],
                "subscription_tier": "free",
            },
        )
        db_session.add(org)
        await db_session.commit()

        assert org.has_feature("ai_generation") is True
        assert org.has_feature("templates") is True
        assert org.has_feature("advanced_cad") is False

        # Cleanup
        await db_session.delete(org)
        await db_session.commit()

    async def test_enabled_features_defaults_to_tier(
        self, db_session: AsyncSession, test_user
    ):
        """Test that enabled_features defaults to tier's features."""
        org = Organization(
            id=uuid4(),
            name="Test Org Pro",
            slug=f"test-pro-{uuid4().hex[:8]}",
            owner_id=test_user.id,
            settings={
                "subscription_tier": "pro",
                # No enabled_features specified
            },
        )
        db_session.add(org)
        await db_session.commit()

        # Should default to pro tier features
        features = org.enabled_features
        assert "ai_generation" in features
        assert "direct_generation" in features
        assert "custom_templates" in features

        # Cleanup
        await db_session.delete(org)
        await db_session.commit()

