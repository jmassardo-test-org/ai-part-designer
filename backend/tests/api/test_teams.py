"""
Tests for Teams API endpoints.

Tests team CRUD operations and team membership management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi import status

from app.models.team import TeamRole

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.organization import Organization
    from app.models.user import User


# =============================================================================
# Helper Functions
# =============================================================================


async def create_team(
    db_session: AsyncSession,
    org: Organization,
    name: str = "Engineering",
    slug: str | None = None,
    created_by: User | None = None,
) -> "Team":
    """Create a team for testing."""
    from app.models.team import Team

    team = Team(
        id=uuid4(),
        organization_id=org.id,
        name=name,
        slug=slug or name.lower().replace(" ", "-"),
        description=f"{name} team",
        created_by_id=created_by.id if created_by else None,
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


async def add_team_member(
    db_session: AsyncSession,
    team: "Team",
    user: User,
    role: TeamRole = TeamRole.MEMBER,
) -> "TeamMember":
    """Add a member to a team."""
    from app.models.team import TeamMember

    member = TeamMember(
        id=uuid4(),
        team_id=team.id,
        user_id=user.id,
        role=role,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


# =============================================================================
# Create Team Tests
# =============================================================================


class TestCreateTeam:
    """Tests for POST /organizations/{org_id}/teams."""

    @pytest.mark.asyncio
    async def test_create_team_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test successful team creation."""
        response = await client.post(
            f"/api/v1/organizations/{test_org_with_features.id}/teams",
            headers=auth_headers,
            json={
                "name": "Engineering",
                "slug": "engineering",
                "description": "Backend team",
                "settings": {"color": "#3B82F6"},
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Engineering"
        assert data["slug"] == "engineering"
        assert data["description"] == "Backend team"

    @pytest.mark.asyncio
    async def test_create_team_requires_auth(
        self,
        client: AsyncClient,
        test_org_with_features: Organization,
    ) -> None:
        """Test that team creation requires authentication."""
        response = await client.post(
            f"/api/v1/organizations/{test_org_with_features.id}/teams",
            json={"name": "Engineering"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_team_org_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Test team creation with non-existent org."""
        response = await client.post(
            f"/api/v1/organizations/{uuid4()}/teams",
            headers=auth_headers,
            json={"name": "Engineering"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_team_duplicate_slug(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test team creation with duplicate slug."""
        # Create initial team
        await create_team(db_session, test_org_with_features, "Engineering", "engineering")

        # Try to create another with same slug
        response = await client.post(
            f"/api/v1/organizations/{test_org_with_features.id}/teams",
            headers=auth_headers,
            json={"name": "Engineering 2", "slug": "engineering"},
        )

        assert response.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# List Teams Tests
# =============================================================================


class TestListTeams:
    """Tests for GET /organizations/{org_id}/teams."""

    @pytest.mark.asyncio
    async def test_list_teams_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test successful team listing."""
        # Create some teams
        await create_team(db_session, test_org_with_features, "Engineering")
        await create_team(db_session, test_org_with_features, "Design")

        response = await client.get(
            f"/api/v1/organizations/{test_org_with_features.id}/teams",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 2
        names = [t["name"] for t in data["items"]]
        assert "Engineering" in names
        assert "Design" in names

    @pytest.mark.asyncio
    async def test_list_teams_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test listing teams when none exist."""
        response = await client.get(
            f"/api/v1/organizations/{test_org_with_features.id}/teams",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_teams_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test team listing with pagination."""
        # Create 5 teams
        for i in range(5):
            await create_team(db_session, test_org_with_features, f"Team {i}")

        # Get first page
        response = await client.get(
            f"/api/v1/organizations/{test_org_with_features.id}/teams",
            headers=auth_headers,
            params={"page": 1, "page_size": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


# =============================================================================
# Get Team Tests
# =============================================================================


class TestGetTeam:
    """Tests for GET /organizations/{org_id}/teams/{team_id}."""

    @pytest.mark.asyncio
    async def test_get_team_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test successful team retrieval."""
        team = await create_team(db_session, test_org_with_features, "Engineering")

        response = await client.get(
            f"/api/v1/organizations/{test_org_with_features.id}/teams/{team.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Engineering"
        assert "members" in data

    @pytest.mark.asyncio
    async def test_get_team_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test team retrieval when not found."""
        response = await client.get(
            f"/api/v1/organizations/{test_org_with_features.id}/teams/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Update Team Tests
# =============================================================================


class TestUpdateTeam:
    """Tests for PATCH /organizations/{org_id}/teams/{team_id}."""

    @pytest.mark.asyncio
    async def test_update_team_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test successful team update."""
        team = await create_team(
            db_session, test_org_with_features, "Engineering", created_by=test_user
        )
        # Add user as team admin
        await add_team_member(db_session, team, test_user, TeamRole.ADMIN)

        response = await client.patch(
            f"/api/v1/organizations/{test_org_with_features.id}/teams/{team.id}",
            headers=auth_headers,
            json={"name": "Engineering Updated", "description": "New description"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Engineering Updated"
        assert data["description"] == "New description"


# =============================================================================
# Delete Team Tests
# =============================================================================


class TestDeleteTeam:
    """Tests for DELETE /organizations/{org_id}/teams/{team_id}."""

    @pytest.mark.asyncio
    async def test_delete_team_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test successful team deletion."""
        team = await create_team(db_session, test_org_with_features)

        response = await client.delete(
            f"/api/v1/organizations/{test_org_with_features.id}/teams/{team.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_team_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test team deletion when not found."""
        response = await client.delete(
            f"/api/v1/organizations/{test_org_with_features.id}/teams/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Team Members Tests
# =============================================================================


class TestTeamMembers:
    """Tests for team member endpoints."""

    @pytest.mark.asyncio
    async def test_list_team_members_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test successful member listing."""
        team = await create_team(db_session, test_org_with_features)
        await add_team_member(db_session, team, test_user, TeamRole.ADMIN)

        response = await client.get(
            f"/api/v1/organizations/{test_org_with_features.id}/teams/{team.id}/members",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_add_team_member_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test successful member addition."""
        team = await create_team(db_session, test_org_with_features, created_by=test_user)
        await add_team_member(db_session, team, test_user, TeamRole.ADMIN)

        # Create another user to add
        from app.core.security import hash_password
        from app.models.user import User as UserModel

        new_user = UserModel(
            email="newuser@example.com",
            password_hash=hash_password("Password123!"),
            display_name="New User",
            status="active",
        )
        db_session.add(new_user)
        await db_session.commit()
        await db_session.refresh(new_user)

        response = await client.post(
            f"/api/v1/organizations/{test_org_with_features.id}/teams/{team.id}/members",
            headers=auth_headers,
            json={"user_id": str(new_user.id), "role": "member"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_id"] == str(new_user.id)
        assert data["role"] == "member"

    @pytest.mark.asyncio
    async def test_remove_team_member_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test successful member removal."""
        team = await create_team(db_session, test_org_with_features, created_by=test_user)
        await add_team_member(db_session, team, test_user, TeamRole.ADMIN)

        # Create and add another user
        from app.core.security import hash_password
        from app.models.user import User as UserModel

        other_user = UserModel(
            email="other@example.com",
            password_hash=hash_password("Password123!"),
            display_name="Other User",
            status="active",
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)
        await add_team_member(db_session, team, other_user)

        response = await client.delete(
            f"/api/v1/organizations/{test_org_with_features.id}/teams/{team.id}/members/{other_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# User Teams Tests
# =============================================================================


class TestUserTeams:
    """Tests for user's teams endpoints."""

    @pytest.mark.asyncio
    async def test_get_my_teams_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test getting current user's teams."""
        team = await create_team(db_session, test_org_with_features, "Engineering")
        await add_team_member(db_session, team, test_user)

        response = await client.get(
            "/api/v1/users/me/teams",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        team_names = [t["team_name"] for t in data["items"]]
        assert "Engineering" in team_names

    @pytest.mark.asyncio
    async def test_get_my_teams_empty(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Test getting user's teams when not in any."""
        response = await client.get(
            "/api/v1/users/me/teams",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_leave_team_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test leaving a team."""
        team = await create_team(db_session, test_org_with_features)
        await add_team_member(db_session, team, test_user)

        response = await client.delete(
            f"/api/v1/users/me/teams/{team.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_leave_team_not_member(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
        test_org_with_features: Organization,
    ) -> None:
        """Test leaving a team when not a member."""
        team = await create_team(db_session, test_org_with_features)

        response = await client.delete(
            f"/api/v1/users/me/teams/{team.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
