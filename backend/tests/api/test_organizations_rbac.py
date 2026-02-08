"""
Comprehensive RBAC tests for organization endpoints.

Tests verify that role-based access control is properly enforced
on all organization endpoints, not just hidden in the UI.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.organization import (
    InviteStatus,
    Organization,
    OrganizationInvite,
    OrganizationMember,
    OrganizationRole,
)
from app.models.user import User


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def org_owner(db_session: AsyncSession) -> User:
    """Create organization owner user."""
    from app.core.security import hash_password

    user = User(
        email="owner@example.com",
        password_hash=hash_password("OwnerPass123!"),
        display_name="Org Owner",
        status="active",
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def org_admin(db_session: AsyncSession) -> User:
    """Create organization admin user."""
    from app.core.security import hash_password

    user = User(
        email="admin@example.com",
        password_hash=hash_password("AdminPass123!"),
        display_name="Org Admin",
        status="active",
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def org_member(db_session: AsyncSession) -> User:
    """Create organization member user."""
    from app.core.security import hash_password

    user = User(
        email="member@example.com",
        password_hash=hash_password("MemberPass123!"),
        display_name="Org Member",
        status="active",
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def org_viewer(db_session: AsyncSession) -> User:
    """Create organization viewer user."""
    from app.core.security import hash_password

    user = User(
        email="viewer@example.com",
        password_hash=hash_password("ViewerPass123!"),
        display_name="Org Viewer",
        status="active",
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def outsider(db_session: AsyncSession) -> User:
    """Create user not in the organization."""
    from app.core.security import hash_password

    user = User(
        email="outsider@example.com",
        password_hash=hash_password("OutsiderPass123!"),
        display_name="Outsider",
        status="active",
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_org(
    db_session: AsyncSession,
    org_owner: User,
    org_admin: User,
    org_member: User,
    org_viewer: User,
) -> Organization:
    """Create test organization with all role types."""
    org = Organization(
        id=uuid4(),
        name="Test RBAC Organization",
        slug=f"test-rbac-{uuid4().hex[:8]}",
        owner_id=org_owner.id,
        settings={
            "allow_member_invites": False,
            "default_project_visibility": "private",
            "require_2fa": False,
            "allowed_domains": [],
        },
    )
    db_session.add(org)
    await db_session.flush()

    # Add members with different roles
    members = [
        OrganizationMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=org_owner.id,
            role=OrganizationRole.OWNER.value,
            joined_at=datetime.now(UTC),
        ),
        OrganizationMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=org_admin.id,
            role=OrganizationRole.ADMIN.value,
            joined_at=datetime.now(UTC),
        ),
        OrganizationMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=org_member.id,
            role=OrganizationRole.MEMBER.value,
            joined_at=datetime.now(UTC),
        ),
        OrganizationMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=org_viewer.id,
            role=OrganizationRole.VIEWER.value,
            joined_at=datetime.now(UTC),
        ),
    ]
    for member in members:
        db_session.add(member)

    await db_session.commit()
    await db_session.refresh(org)
    return org


def make_auth_headers(user: User) -> dict[str, str]:
    """Create authentication headers for a user."""
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Test: GET /organizations/{org_id} - VIEWER Required
# =============================================================================


class TestGetOrganizationRBAC:
    """Test RBAC for GET /organizations/{org_id}."""

    async def test_owner_can_view(self, client: AsyncClient, test_org: Organization, org_owner: User):
        """Owner should be able to view organization."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_owner),
        )
        assert response.status_code == 200

    async def test_admin_can_view(self, client: AsyncClient, test_org: Organization, org_admin: User):
        """Admin should be able to view organization."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_admin),
        )
        assert response.status_code == 200

    async def test_member_can_view(self, client: AsyncClient, test_org: Organization, org_member: User):
        """Member should be able to view organization."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_member),
        )
        assert response.status_code == 200

    async def test_viewer_can_view(self, client: AsyncClient, test_org: Organization, org_viewer: User):
        """Viewer should be able to view organization."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_viewer),
        )
        assert response.status_code == 200

    async def test_outsider_cannot_view(self, client: AsyncClient, test_org: Organization, outsider: User):
        """Non-member should not be able to view organization."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(outsider),
        )
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"].lower()

    async def test_unauthenticated_cannot_view(self, client: AsyncClient, test_org: Organization):
        """Unauthenticated user should not be able to view organization."""
        response = await client.get(f"/api/v1/organizations/{test_org.id}")
        assert response.status_code == 401


# =============================================================================
# Test: PATCH /organizations/{org_id} - ADMIN Required
# =============================================================================


class TestUpdateOrganizationRBAC:
    """Test RBAC for PATCH /organizations/{org_id}."""

    async def test_owner_can_update(self, client: AsyncClient, test_org: Organization, org_owner: User):
        """Owner should be able to update organization."""
        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_owner),
            json={"name": "Updated by Owner"},
        )
        assert response.status_code == 200

    async def test_admin_can_update(self, client: AsyncClient, test_org: Organization, org_admin: User):
        """Admin should be able to update organization."""
        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_admin),
            json={"name": "Updated by Admin"},
        )
        assert response.status_code == 200

    async def test_member_cannot_update(self, client: AsyncClient, test_org: Organization, org_member: User):
        """Member should not be able to update organization."""
        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_member),
            json={"name": "Updated by Member"},
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    async def test_viewer_cannot_update(self, client: AsyncClient, test_org: Organization, org_viewer: User):
        """Viewer should not be able to update organization."""
        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_viewer),
            json={"name": "Updated by Viewer"},
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    async def test_outsider_cannot_update(self, client: AsyncClient, test_org: Organization, outsider: User):
        """Non-member should not be able to update organization."""
        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(outsider),
            json={"name": "Updated by Outsider"},
        )
        assert response.status_code == 403


# =============================================================================
# Test: DELETE /organizations/{org_id} - OWNER Required
# =============================================================================


class TestDeleteOrganizationRBAC:
    """Test RBAC for DELETE /organizations/{org_id}."""

    async def test_owner_can_delete(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org_owner: User,
    ):
        """Owner should be able to delete organization."""
        # Create a separate org for deletion
        org = Organization(
            id=uuid4(),
            name="To Delete By Owner",
            slug=f"delete-owner-{uuid4().hex[:8]}",
            owner_id=org_owner.id,
            settings={},
        )
        db_session.add(org)
        member = OrganizationMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=org_owner.id,
            role=OrganizationRole.OWNER.value,
            joined_at=datetime.now(UTC),
        )
        db_session.add(member)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/organizations/{org.id}",
            headers=make_auth_headers(org_owner),
        )
        assert response.status_code == 204

    async def test_admin_cannot_delete(self, client: AsyncClient, test_org: Organization, org_admin: User):
        """Admin should not be able to delete organization."""
        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_admin),
        )
        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()

    async def test_member_cannot_delete(self, client: AsyncClient, test_org: Organization, org_member: User):
        """Member should not be able to delete organization."""
        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_member),
        )
        assert response.status_code == 403

    async def test_viewer_cannot_delete(self, client: AsyncClient, test_org: Organization, org_viewer: User):
        """Viewer should not be able to delete organization."""
        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}",
            headers=make_auth_headers(org_viewer),
        )
        assert response.status_code == 403


# =============================================================================
# Test: GET /organizations/{org_id}/members - VIEWER Required
# =============================================================================


class TestListMembersRBAC:
    """Test RBAC for GET /organizations/{org_id}/members."""

    async def test_owner_can_list_members(
        self, client: AsyncClient, test_org: Organization, org_owner: User
    ):
        """Owner should be able to list members."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/members",
            headers=make_auth_headers(org_owner),
        )
        assert response.status_code == 200
        assert len(response.json()) >= 4  # All 4 members

    async def test_viewer_can_list_members(
        self, client: AsyncClient, test_org: Organization, org_viewer: User
    ):
        """Viewer should be able to list members."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/members",
            headers=make_auth_headers(org_viewer),
        )
        assert response.status_code == 200

    async def test_outsider_cannot_list_members(
        self, client: AsyncClient, test_org: Organization, outsider: User
    ):
        """Non-member should not be able to list members."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/members",
            headers=make_auth_headers(outsider),
        )
        assert response.status_code == 403


# =============================================================================
# Test: PATCH /organizations/{org_id}/members/{member_id}/role - ADMIN Required
# =============================================================================


class TestChangeRoleRBAC:
    """Test RBAC for PATCH /organizations/{org_id}/members/{member_id}/role."""

    async def test_owner_can_change_roles(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_owner: User,
        org_viewer: User,
    ):
        """Owner should be able to change member roles."""
        # Get viewer's membership ID
        from sqlalchemy import select

        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == org_viewer.id,
            )
        )
        member = result.scalar_one()

        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}/members/{member.id}/role",
            headers=make_auth_headers(org_owner),
            json={"role": "member"},
        )
        assert response.status_code == 200

    async def test_admin_can_change_roles(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_admin: User,
        org_viewer: User,
    ):
        """Admin should be able to change member roles."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == org_viewer.id,
            )
        )
        member = result.scalar_one()

        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}/members/{member.id}/role",
            headers=make_auth_headers(org_admin),
            json={"role": "member"},
        )
        assert response.status_code == 200

    async def test_member_cannot_change_roles(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_member: User,
        org_viewer: User,
    ):
        """Member should not be able to change roles."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == org_viewer.id,
            )
        )
        member = result.scalar_one()

        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}/members/{member.id}/role",
            headers=make_auth_headers(org_member),
            json={"role": "admin"},
        )
        assert response.status_code == 403

    async def test_cannot_change_owner_role(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_admin: User,
        org_owner: User,
    ):
        """Admin should not be able to change owner's role."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == org_owner.id,
            )
        )
        owner_member = result.scalar_one()

        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}/members/{owner_member.id}/role",
            headers=make_auth_headers(org_admin),
            json={"role": "admin"},
        )
        assert response.status_code == 400
        assert "owner" in response.json()["detail"].lower()


# =============================================================================
# Test: DELETE /organizations/{org_id}/members/{member_id} - ADMIN Required
# =============================================================================


class TestRemoveMemberRBAC:
    """Test RBAC for DELETE /organizations/{org_id}/members/{member_id}."""

    async def test_admin_can_remove_members(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_admin: User,
        org_viewer: User,
    ):
        """Admin should be able to remove members."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == org_viewer.id,
            )
        )
        member = result.scalar_one()

        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}/members/{member.id}",
            headers=make_auth_headers(org_admin),
        )
        assert response.status_code == 204

    async def test_member_cannot_remove_others(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_member: User,
        org_viewer: User,
    ):
        """Member should not be able to remove other members."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == org_viewer.id,
            )
        )
        viewer_member = result.scalar_one()

        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}/members/{viewer_member.id}",
            headers=make_auth_headers(org_member),
        )
        assert response.status_code == 403

    async def test_member_can_remove_self(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_member: User,
    ):
        """Member should be able to remove themselves."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == org_member.id,
            )
        )
        member = result.scalar_one()

        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}/members/{member.id}",
            headers=make_auth_headers(org_member),
        )
        assert response.status_code == 204

    async def test_cannot_remove_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_admin: User,
        org_owner: User,
    ):
        """Admin should not be able to remove owner."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == org_owner.id,
            )
        )
        owner_member = result.scalar_one()

        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}/members/{owner_member.id}",
            headers=make_auth_headers(org_admin),
        )
        assert response.status_code == 400
        assert "owner" in response.json()["detail"].lower()


# =============================================================================
# Test: POST /organizations/{org_id}/transfer-ownership - OWNER Required
# =============================================================================


class TestTransferOwnershipRBAC:
    """Test RBAC for POST /organizations/{org_id}/transfer-ownership."""

    async def test_owner_can_transfer(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_owner: User,
        org_admin: User,
    ):
        """Owner should be able to transfer ownership."""
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/transfer-ownership",
            headers=make_auth_headers(org_owner),
            json={"new_owner_id": str(org_admin.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["owner_id"] == str(org_admin.id)

    async def test_admin_cannot_transfer(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_admin: User,
        org_member: User,
    ):
        """Admin should not be able to transfer ownership."""
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/transfer-ownership",
            headers=make_auth_headers(org_admin),
            json={"new_owner_id": str(org_member.id)},
        )
        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()

    async def test_member_cannot_transfer(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_member: User,
        org_admin: User,
    ):
        """Member should not be able to transfer ownership."""
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/transfer-ownership",
            headers=make_auth_headers(org_member),
            json={"new_owner_id": str(org_admin.id)},
        )
        assert response.status_code == 403


# =============================================================================
# Test: POST /organizations/{org_id}/invites - ADMIN Required
# =============================================================================


class TestInviteMemberRBAC:
    """Test RBAC for POST /organizations/{org_id}/invites."""

    async def test_owner_can_invite(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_owner: User,
    ):
        """Owner should be able to invite members."""
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/invites",
            headers=make_auth_headers(org_owner),
            json={"email": "newmember@example.com", "role": "member"},
        )
        assert response.status_code == 201

    async def test_admin_can_invite(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_admin: User,
    ):
        """Admin should be able to invite members."""
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/invites",
            headers=make_auth_headers(org_admin),
            json={"email": "another@example.com", "role": "viewer"},
        )
        assert response.status_code == 201

    async def test_member_cannot_invite(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_member: User,
    ):
        """Member should not be able to invite."""
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/invites",
            headers=make_auth_headers(org_member),
            json={"email": "wannabe@example.com", "role": "member"},
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    async def test_viewer_cannot_invite(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_viewer: User,
    ):
        """Viewer should not be able to invite."""
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/invites",
            headers=make_auth_headers(org_viewer),
            json={"email": "nope@example.com", "role": "viewer"},
        )
        assert response.status_code == 403


# =============================================================================
# Test: GET /organizations/{org_id}/invites - ADMIN Required
# =============================================================================


class TestListInvitesRBAC:
    """Test RBAC for GET /organizations/{org_id}/invites."""

    async def test_admin_can_list_invites(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_admin: User,
    ):
        """Admin should be able to list invites."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/invites",
            headers=make_auth_headers(org_admin),
        )
        assert response.status_code == 200

    async def test_member_cannot_list_invites(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_member: User,
    ):
        """Member should not be able to list invites."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/invites",
            headers=make_auth_headers(org_member),
        )
        assert response.status_code == 403

    async def test_viewer_cannot_list_invites(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_viewer: User,
    ):
        """Viewer should not be able to list invites."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/invites",
            headers=make_auth_headers(org_viewer),
        )
        assert response.status_code == 403


# =============================================================================
# Test: DELETE /organizations/{org_id}/invites/{invite_id} - ADMIN Required
# =============================================================================


class TestRevokeInviteRBAC:
    """Test RBAC for DELETE /organizations/{org_id}/invites/{invite_id}."""

    async def test_admin_can_revoke_invite(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_admin: User,
    ):
        """Admin should be able to revoke invites."""
        # Create an invite
        invite = OrganizationInvite(
            id=uuid4(),
            organization_id=test_org.id,
            invited_by_id=org_admin.id,
            email="revokeme@example.com",
            role=OrganizationRole.MEMBER.value,
            status=InviteStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(invite)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}/invites/{invite.id}",
            headers=make_auth_headers(org_admin),
        )
        assert response.status_code == 204

    async def test_member_cannot_revoke_invite(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_member: User,
        org_admin: User,
    ):
        """Member should not be able to revoke invites."""
        # Create an invite
        invite = OrganizationInvite(
            id=uuid4(),
            organization_id=test_org.id,
            invited_by_id=org_admin.id,
            email="cantrevoke@example.com",
            role=OrganizationRole.MEMBER.value,
            status=InviteStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(invite)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/organizations/{test_org.id}/invites/{invite.id}",
            headers=make_auth_headers(org_member),
        )
        assert response.status_code == 403


# =============================================================================
# Test: POST /organizations/invites/accept - Authentication Only
# =============================================================================


class TestAcceptInviteRBAC:
    """Test RBAC for POST /organizations/invites/accept."""

    async def test_authenticated_can_accept_own_invite(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_admin: User,
        outsider: User,
    ):
        """User should be able to accept invite sent to their email."""
        # Create an invite for outsider
        invite = OrganizationInvite(
            id=uuid4(),
            organization_id=test_org.id,
            invited_by_id=org_admin.id,
            email=outsider.email,
            role=OrganizationRole.MEMBER.value,
            status=InviteStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(invite)
        await db_session.commit()
        await db_session.refresh(invite)

        response = await client.post(
            "/api/v1/organizations/invites/accept",
            headers=make_auth_headers(outsider),
            json={"token": invite.token},
        )
        assert response.status_code == 200

    async def test_cannot_accept_others_invite(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_admin: User,
        outsider: User,
    ):
        """User should not be able to accept invite for different email."""
        # Create an invite for someone else
        invite = OrganizationInvite(
            id=uuid4(),
            organization_id=test_org.id,
            invited_by_id=org_admin.id,
            email="someoneelse@example.com",
            role=OrganizationRole.MEMBER.value,
            status=InviteStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(invite)
        await db_session.commit()
        await db_session.refresh(invite)

        response = await client.post(
            "/api/v1/organizations/invites/accept",
            headers=make_auth_headers(outsider),
            json={"token": invite.token},
        )
        assert response.status_code == 403
        assert "different email" in response.json()["detail"].lower()

    async def test_unauthenticated_cannot_accept(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_admin: User,
    ):
        """Unauthenticated user should not be able to accept invites."""
        invite = OrganizationInvite(
            id=uuid4(),
            organization_id=test_org.id,
            invited_by_id=org_admin.id,
            email="test@example.com",
            role=OrganizationRole.MEMBER.value,
            status=InviteStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db_session.add(invite)
        await db_session.commit()
        await db_session.refresh(invite)

        response = await client.post(
            "/api/v1/organizations/invites/accept",
            json={"token": invite.token},
        )
        assert response.status_code == 401


# =============================================================================
# Test: Privilege Escalation Prevention
# =============================================================================


class TestPrivilegeEscalation:
    """Test that privilege escalation is properly prevented."""

    async def test_cannot_escalate_via_role_change(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_org: Organization,
        org_admin: User,
        org_member: User,
    ):
        """Admin should not be able to escalate member to owner."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == test_org.id,
                OrganizationMember.user_id == org_member.id,
            )
        )
        member = result.scalar_one()

        # Try to set role to owner (not in valid roles for endpoint)
        response = await client.patch(
            f"/api/v1/organizations/{test_org.id}/members/{member.id}/role",
            headers=make_auth_headers(org_admin),
            json={"role": "owner"},
        )
        # Should be rejected by validation
        assert response.status_code == 422

    async def test_cannot_invite_as_owner(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_admin: User,
    ):
        """Admin should not be able to invite someone as owner."""
        response = await client.post(
            f"/api/v1/organizations/{test_org.id}/invites",
            headers=make_auth_headers(org_admin),
            json={"email": "fake-owner@example.com", "role": "owner"},
        )
        # Should be rejected by validation
        assert response.status_code == 422

    async def test_member_limit_enforced(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        org_owner: User,
    ):
        """Invites should be rejected when member limit reached."""
        # Create org with max_members = 1
        org = Organization(
            id=uuid4(),
            name="Limited Org",
            slug=f"limited-{uuid4().hex[:8]}",
            owner_id=org_owner.id,
            max_members=1,
            settings={},
        )
        db_session.add(org)
        member = OrganizationMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=org_owner.id,
            role=OrganizationRole.OWNER.value,
            joined_at=datetime.now(UTC),
        )
        db_session.add(member)
        await db_session.commit()

        # Try to invite (should fail - limit reached)
        response = await client.post(
            f"/api/v1/organizations/{org.id}/invites",
            headers=make_auth_headers(org_owner),
            json={"email": "exceed-limit@example.com", "role": "member"},
        )
        assert response.status_code == 400
        assert "limit" in response.json()["detail"].lower()
