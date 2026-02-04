"""
Tests for organizations API endpoints.

Tests organization CRUD, membership, and invite operations.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

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
            }
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
            }
        )
        
        assert response.status_code in [400, 409, 422]

    async def test_create_organization_invalid_slug(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should reject invalid slug format."""
        response = await client.post(
            "/api/v1/organizations",
            headers=auth_headers,
            json={
                "name": "Test Org",
                "slug": "INVALID SLUG!",  # Invalid characters
            }
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
            f"/api/v1/organizations/{test_organization.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_organization.id)
        assert data["name"] == test_organization.name

    async def test_get_organization_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent organization."""
        response = await client.get(
            "/api/v1/organizations/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
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
            json={"name": "Updated Org Name"}
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
        
        response = await client.delete(
            f"/api/v1/organizations/{org.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204

    async def test_delete_organization_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent organization."""
        response = await client.delete(
            "/api/v1/organizations/00000000-0000-0000-0000-000000000000",
            headers=auth_headers
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
            f"/api/v1/organizations/{test_organization.id}/members",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # At least the owner
        assert len(data) >= 1
