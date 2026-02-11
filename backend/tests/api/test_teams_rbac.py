"""
RBAC tests for Teams API endpoints.

Tests verify that role-based access control is properly enforced
on teams read endpoints to prevent IDOR vulnerabilities.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrganizationRole,
)
from app.models.team import Team
from app.models.user import User

# =============================================================================
# Fixtures
# =============================================================================


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
    org_viewer: User,
    org_member: User,
) -> Organization:
    """Create test organization with different role types."""
    org = Organization(
        id=uuid4(),
        name="Test Teams RBAC Organization",
        slug=f"test-teams-rbac-{uuid4().hex[:8]}",
        owner_id=org_viewer.id,
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
            user_id=org_viewer.id,
            role=OrganizationRole.VIEWER.value,
            joined_at=datetime.now(UTC),
        ),
        OrganizationMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=org_member.id,
            role=OrganizationRole.MEMBER.value,
            joined_at=datetime.now(UTC),
        ),
    ]
    for member in members:
        db_session.add(member)

    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def test_team(
    db_session: AsyncSession,
    test_org: Organization,
) -> Team:
    """Create a test team in the organization."""
    team = Team(
        id=uuid4(),
        organization_id=test_org.id,
        name="Engineering Team",
        slug="engineering-team",
        description="Test engineering team",
        is_active=True,
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


def make_auth_headers(user: User) -> dict[str, str]:
    """Create authentication headers for a user."""
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Test: GET /organizations/{org_id}/teams - VIEWER Required
# =============================================================================


class TestListTeamsRBAC:
    """Test RBAC for GET /organizations/{org_id}/teams."""

    async def test_viewer_can_list_teams(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_viewer: User,
        test_team: Team,
    ):
        """Viewer should be able to list organization teams."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams",
            headers=make_auth_headers(org_viewer),
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_member_can_list_teams(
        self,
        client: AsyncClient,
        test_org: Organization,
        org_member: User,
        test_team: Team,
    ):
        """Member should be able to list organization teams."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams",
            headers=make_auth_headers(org_member),
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_outsider_cannot_list_teams(
        self,
        client: AsyncClient,
        test_org: Organization,
        outsider: User,
        test_team: Team,
    ):
        """Non-member should not be able to list organization teams."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams",
            headers=make_auth_headers(outsider),
        )
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"].lower()

    async def test_unauthenticated_cannot_list_teams(
        self,
        client: AsyncClient,
        test_org: Organization,
        test_team: Team,
    ):
        """Unauthenticated user should not be able to list teams."""
        response = await client.get(f"/api/v1/organizations/{test_org.id}/teams")
        assert response.status_code == 401


# =============================================================================
# Test: GET /organizations/{org_id}/teams/{team_id} - VIEWER Required
# =============================================================================


class TestGetTeamRBAC:
    """Test RBAC for GET /organizations/{org_id}/teams/{team_id}."""

    async def test_viewer_can_get_team(
        self,
        client: AsyncClient,
        test_org: Organization,
        test_team: Team,
        org_viewer: User,
    ):
        """Viewer should be able to get team details."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams/{test_team.id}",
            headers=make_auth_headers(org_viewer),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_team.id)
        assert data["name"] == test_team.name

    async def test_member_can_get_team(
        self,
        client: AsyncClient,
        test_org: Organization,
        test_team: Team,
        org_member: User,
    ):
        """Member should be able to get team details."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams/{test_team.id}",
            headers=make_auth_headers(org_member),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_team.id)

    async def test_outsider_cannot_get_team(
        self,
        client: AsyncClient,
        test_org: Organization,
        test_team: Team,
        outsider: User,
    ):
        """Non-member should not be able to get team details."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams/{test_team.id}",
            headers=make_auth_headers(outsider),
        )
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"].lower()

    async def test_unauthenticated_cannot_get_team(
        self,
        client: AsyncClient,
        test_org: Organization,
        test_team: Team,
    ):
        """Unauthenticated user should not be able to get team."""
        response = await client.get(f"/api/v1/organizations/{test_org.id}/teams/{test_team.id}")
        assert response.status_code == 401


# =============================================================================
# Test: GET /organizations/{org_id}/teams/{team_id}/members - VIEWER Required
# =============================================================================


class TestListTeamMembersRBAC:
    """Test RBAC for GET /organizations/{org_id}/teams/{team_id}/members."""

    async def test_viewer_can_list_team_members(
        self,
        client: AsyncClient,
        test_org: Organization,
        test_team: Team,
        org_viewer: User,
    ):
        """Viewer should be able to list team members."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams/{test_team.id}/members",
            headers=make_auth_headers(org_viewer),
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_member_can_list_team_members(
        self,
        client: AsyncClient,
        test_org: Organization,
        test_team: Team,
        org_member: User,
    ):
        """Member should be able to list team members."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams/{test_team.id}/members",
            headers=make_auth_headers(org_member),
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_outsider_cannot_list_team_members(
        self,
        client: AsyncClient,
        test_org: Organization,
        test_team: Team,
        outsider: User,
    ):
        """Non-member should not be able to list team members."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams/{test_team.id}/members",
            headers=make_auth_headers(outsider),
        )
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"].lower()

    async def test_unauthenticated_cannot_list_team_members(
        self,
        client: AsyncClient,
        test_org: Organization,
        test_team: Team,
    ):
        """Unauthenticated user should not be able to list team members."""
        response = await client.get(
            f"/api/v1/organizations/{test_org.id}/teams/{test_team.id}/members"
        )
        assert response.status_code == 401
