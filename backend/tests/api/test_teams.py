"""
Tests for Teams API endpoints.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models.team import Team, TeamMember, TeamRole
from app.services.team_service import (
    TeamDuplicateError,
    TeamMemberExistsError,
    TeamMemberNotFoundError,
    TeamNotFoundError,
    TeamService,
)


class TestCreateTeam:
    """Tests for POST /organizations/{org_id}/teams."""

    @pytest.mark.asyncio
    async def test_create_team_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test successful team creation."""
        org_id = uuid4()
        team_id = uuid4()

        mock_team = MagicMock(spec=Team)
        mock_team.id = team_id
        mock_team.organization_id = org_id
        mock_team.name = "Engineering"
        mock_team.slug = "engineering"
        mock_team.description = "Backend team"
        mock_team.settings = {"color": "#3B82F6"}
        mock_team.is_active = True
        mock_team.created_by_id = mock_current_user.id
        mock_team.created_at = datetime.now(tz=UTC)
        mock_team.updated_at = datetime.now(tz=UTC)
        mock_team.member_count = 1

        with (
            patch.object(TeamService, "check_org_team_permission", return_value=True),
            patch.object(TeamService, "create_team", return_value=mock_team),
        ):
            response = await async_client.post(
                f"/api/v1/organizations/{org_id}/teams",
                json={
                    "name": "Engineering",
                    "description": "Backend team",
                    "settings": {"color": "#3B82F6"},
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Engineering"
        assert data["slug"] == "engineering"

    @pytest.mark.asyncio
    async def test_create_team_forbidden(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test team creation without permission."""
        org_id = uuid4()

        with patch.object(TeamService, "check_org_team_permission", return_value=False):
            response = await async_client.post(
                f"/api/v1/organizations/{org_id}/teams",
                json={"name": "Engineering"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_team_duplicate_slug(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test team creation with duplicate slug."""
        org_id = uuid4()

        with (
            patch.object(TeamService, "check_org_team_permission", return_value=True),
            patch.object(
                TeamService,
                "create_team",
                side_effect=TeamDuplicateError("Slug exists"),
            ),
        ):
            response = await async_client.post(
                f"/api/v1/organizations/{org_id}/teams",
                json={"name": "Engineering"},
            )

        assert response.status_code == status.HTTP_409_CONFLICT


class TestListTeams:
    """Tests for GET /organizations/{org_id}/teams."""

    @pytest.mark.asyncio
    async def test_list_teams_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test successful team listing."""
        org_id = uuid4()

        mock_team = MagicMock(spec=Team)
        mock_team.id = uuid4()
        mock_team.organization_id = org_id
        mock_team.name = "Engineering"
        mock_team.slug = "engineering"
        mock_team.description = None
        mock_team.settings = {}
        mock_team.is_active = True
        mock_team.created_by_id = None
        mock_team.created_at = datetime.now(tz=UTC)
        mock_team.updated_at = datetime.now(tz=UTC)
        mock_team.member_count = 5

        with patch.object(TeamService, "list_teams", return_value=([mock_team], 1)):
            response = await async_client.get(f"/api/v1/organizations/{org_id}/teams")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Engineering"

    @pytest.mark.asyncio
    async def test_list_teams_pagination(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test team listing with pagination."""
        org_id = uuid4()

        with patch.object(TeamService, "list_teams", return_value=([], 0)) as mock_list:
            response = await async_client.get(
                f"/api/v1/organizations/{org_id}/teams",
                params={"page": 2, "page_size": 10},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_list.assert_called_once()
        # Verify pagination params were passed
        call_kwargs = mock_list.call_args[1]
        assert call_kwargs["page"] == 2
        assert call_kwargs["page_size"] == 10


class TestGetTeam:
    """Tests for GET /organizations/{org_id}/teams/{team_id}."""

    @pytest.mark.asyncio
    async def test_get_team_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test successful team retrieval."""
        org_id = uuid4()
        team_id = uuid4()

        mock_team = MagicMock(spec=Team)
        mock_team.id = team_id
        mock_team.organization_id = org_id
        mock_team.name = "Engineering"
        mock_team.slug = "engineering"
        mock_team.description = "Backend team"
        mock_team.settings = {}
        mock_team.is_active = True
        mock_team.created_by_id = None
        mock_team.created_at = datetime.now(tz=UTC)
        mock_team.updated_at = datetime.now(tz=UTC)
        mock_team.__dict__ = {
            "id": team_id,
            "organization_id": org_id,
            "name": "Engineering",
            "slug": "engineering",
            "description": "Backend team",
            "settings": {},
            "is_active": True,
            "created_by_id": None,
            "created_at": datetime.now(tz=UTC),
            "updated_at": datetime.now(tz=UTC),
        }

        with (
            patch.object(TeamService, "get_team_by_id", return_value=mock_team),
            patch.object(TeamService, "list_team_members", return_value=([], 0)),
        ):
            response = await async_client.get(f"/api/v1/organizations/{org_id}/teams/{team_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Engineering"
        assert "members" in data

    @pytest.mark.asyncio
    async def test_get_team_not_found(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test team retrieval when not found."""
        org_id = uuid4()
        team_id = uuid4()

        with patch.object(TeamService, "get_team_by_id", return_value=None):
            response = await async_client.get(f"/api/v1/organizations/{org_id}/teams/{team_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateTeam:
    """Tests for PATCH /organizations/{org_id}/teams/{team_id}."""

    @pytest.mark.asyncio
    async def test_update_team_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test successful team update."""
        org_id = uuid4()
        team_id = uuid4()

        mock_team = MagicMock(spec=Team)
        mock_team.id = team_id
        mock_team.organization_id = org_id
        mock_team.name = "Engineering Updated"
        mock_team.slug = "engineering"
        mock_team.description = "Updated description"
        mock_team.settings = {}
        mock_team.is_active = True
        mock_team.created_by_id = None
        mock_team.created_at = datetime.now(tz=UTC)
        mock_team.updated_at = datetime.now(tz=UTC)
        mock_team.member_count = 5

        with (
            patch.object(TeamService, "check_team_permission", return_value=True),
            patch.object(TeamService, "check_org_team_permission", return_value=False),
            patch.object(TeamService, "update_team", return_value=mock_team),
        ):
            response = await async_client.patch(
                f"/api/v1/organizations/{org_id}/teams/{team_id}",
                json={"name": "Engineering Updated"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Engineering Updated"

    @pytest.mark.asyncio
    async def test_update_team_forbidden(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test team update without permission."""
        org_id = uuid4()
        team_id = uuid4()

        with (
            patch.object(TeamService, "check_team_permission", return_value=False),
            patch.object(TeamService, "check_org_team_permission", return_value=False),
        ):
            response = await async_client.patch(
                f"/api/v1/organizations/{org_id}/teams/{team_id}",
                json={"name": "Updated"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteTeam:
    """Tests for DELETE /organizations/{org_id}/teams/{team_id}."""

    @pytest.mark.asyncio
    async def test_delete_team_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test successful team deletion."""
        org_id = uuid4()
        team_id = uuid4()

        with (
            patch.object(TeamService, "check_org_team_permission", return_value=True),
            patch.object(TeamService, "delete_team", return_value=None),
        ):
            response = await async_client.delete(f"/api/v1/organizations/{org_id}/teams/{team_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_team_not_found(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test team deletion when not found."""
        org_id = uuid4()
        team_id = uuid4()

        with (
            patch.object(TeamService, "check_org_team_permission", return_value=True),
            patch.object(
                TeamService,
                "delete_team",
                side_effect=TeamNotFoundError("Not found"),
            ),
        ):
            response = await async_client.delete(f"/api/v1/organizations/{org_id}/teams/{team_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTeamMembers:
    """Tests for team member endpoints."""

    @pytest.mark.asyncio
    async def test_list_team_members_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test successful member listing."""
        org_id = uuid4()
        team_id = uuid4()

        mock_member = MagicMock(spec=TeamMember)
        mock_member.id = uuid4()
        mock_member.team_id = team_id
        mock_member.user_id = mock_current_user.id
        mock_member.role = TeamRole.ADMIN.value
        mock_member.joined_at = datetime.now(tz=UTC)
        mock_member.is_active = True
        mock_member.added_by_id = None
        mock_member.created_at = datetime.now(tz=UTC)
        mock_member.updated_at = datetime.now(tz=UTC)
        mock_member.user = MagicMock()
        mock_member.user.email = "test@example.com"
        mock_member.user.full_name = "Test User"

        with patch.object(TeamService, "list_team_members", return_value=([mock_member], 1)):
            response = await async_client.get(
                f"/api/v1/organizations/{org_id}/teams/{team_id}/members"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_add_team_member_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test successful member addition."""
        org_id = uuid4()
        team_id = uuid4()
        new_user_id = uuid4()

        mock_member = MagicMock(spec=TeamMember)
        mock_member.id = uuid4()
        mock_member.team_id = team_id
        mock_member.user_id = new_user_id
        mock_member.role = TeamRole.MEMBER.value
        mock_member.joined_at = datetime.now(tz=UTC)
        mock_member.is_active = True
        mock_member.added_by_id = mock_current_user.id
        mock_member.created_at = datetime.now(tz=UTC)
        mock_member.updated_at = datetime.now(tz=UTC)

        with (
            patch.object(TeamService, "check_team_permission", return_value=True),
            patch.object(TeamService, "check_org_team_permission", return_value=False),
            patch.object(TeamService, "add_team_member", return_value=mock_member),
        ):
            response = await async_client.post(
                f"/api/v1/organizations/{org_id}/teams/{team_id}/members",
                json={"user_id": str(new_user_id), "role": "member"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_id"] == str(new_user_id)
        assert data["role"] == "member"

    @pytest.mark.asyncio
    async def test_add_team_member_already_exists(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test adding member that already exists."""
        org_id = uuid4()
        team_id = uuid4()
        user_id = uuid4()

        with (
            patch.object(TeamService, "check_team_permission", return_value=True),
            patch.object(TeamService, "check_org_team_permission", return_value=False),
            patch.object(
                TeamService,
                "add_team_member",
                side_effect=TeamMemberExistsError("Already member"),
            ),
        ):
            response = await async_client.post(
                f"/api/v1/organizations/{org_id}/teams/{team_id}/members",
                json={"user_id": str(user_id), "role": "member"},
            )

        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_remove_team_member_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test successful member removal."""
        org_id = uuid4()
        team_id = uuid4()
        user_id = uuid4()

        with (
            patch.object(TeamService, "check_team_permission", return_value=True),
            patch.object(TeamService, "check_org_team_permission", return_value=False),
            patch.object(TeamService, "remove_team_member", return_value=None),
        ):
            response = await async_client.delete(
                f"/api/v1/organizations/{org_id}/teams/{team_id}/members/{user_id}"
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestUserTeams:
    """Tests for user's teams endpoints."""

    @pytest.mark.asyncio
    async def test_get_my_teams_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test getting current user's teams."""
        team_data = {
            "id": uuid4(),
            "team_id": uuid4(),
            "team_name": "Engineering",
            "team_slug": "engineering",
            "organization_id": uuid4(),
            "organization_name": "Acme Corp",
            "role": "member",
            "joined_at": datetime.now(tz=UTC),
            "is_active": True,
        }

        with patch.object(TeamService, "get_user_teams", return_value=[team_data]):
            response = await async_client.get("/api/v1/users/me/teams")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["team_name"] == "Engineering"

    @pytest.mark.asyncio
    async def test_leave_team_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test leaving a team."""
        team_id = uuid4()

        with patch.object(TeamService, "leave_team", return_value=None):
            response = await async_client.delete(f"/api/v1/users/me/teams/{team_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_leave_team_not_member(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test leaving a team when not a member."""
        team_id = uuid4()

        with patch.object(
            TeamService,
            "leave_team",
            side_effect=TeamMemberNotFoundError("Not a member"),
        ):
            response = await async_client.delete(f"/api/v1/users/me/teams/{team_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestProjectTeams:
    """Tests for project-team assignment endpoints."""

    @pytest.mark.asyncio
    async def test_list_project_teams_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test listing teams assigned to a project."""
        project_id = uuid4()

        mock_assignment = MagicMock()
        mock_assignment.id = uuid4()
        mock_assignment.project_id = project_id
        mock_assignment.team_id = uuid4()
        mock_assignment.permission_level = "editor"
        mock_assignment.assigned_by_id = mock_current_user.id
        mock_assignment.assigned_at = datetime.now(tz=UTC)
        mock_assignment.created_at = datetime.now(tz=UTC)
        mock_assignment.updated_at = datetime.now(tz=UTC)
        mock_assignment.team = MagicMock()
        mock_assignment.team.name = "Engineering"

        with (
            patch.object(TeamService, "list_project_teams", return_value=[mock_assignment]),
            patch("app.api.v1.teams.check_project_permission", return_value=MagicMock()),
        ):
            response = await async_client.get(f"/api/v1/projects/{project_id}/teams")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["team_name"] == "Engineering"
        assert data[0]["permission_level"] == "editor"

    @pytest.mark.asyncio
    async def test_list_project_teams_unauthorized_returns_403(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test that unauthorized users cannot list project team assignments."""
        from fastapi import HTTPException

        project_id = uuid4()

        # Mock check_project_permission to raise 403
        with patch(
            "app.api.v1.teams.check_project_permission",
            side_effect=HTTPException(status_code=403, detail="Not authorized"),
        ):
            response = await async_client.get(f"/api/v1/projects/{project_id}/teams")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_assign_team_to_project_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test assigning a team to a project."""
        project_id = uuid4()
        team_id = uuid4()

        mock_assignment = MagicMock()
        mock_assignment.id = uuid4()
        mock_assignment.project_id = project_id
        mock_assignment.team_id = team_id
        mock_assignment.permission_level = "editor"
        mock_assignment.assigned_by_id = mock_current_user.id
        mock_assignment.assigned_at = datetime.now(tz=UTC)
        mock_assignment.created_at = datetime.now(tz=UTC)
        mock_assignment.updated_at = datetime.now(tz=UTC)

        with patch.object(TeamService, "assign_team_to_project", return_value=mock_assignment):
            response = await async_client.post(
                f"/api/v1/projects/{project_id}/teams",
                json={"team_id": str(team_id), "permission_level": "editor"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["team_id"] == str(team_id)
        assert data["permission_level"] == "editor"

    @pytest.mark.asyncio
    async def test_remove_team_from_project_success(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test removing a team from a project."""
        project_id = uuid4()
        team_id = uuid4()

        with patch.object(TeamService, "remove_team_from_project", return_value=None):
            response = await async_client.delete(f"/api/v1/projects/{project_id}/teams/{team_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_assign_team_unauthorized_returns_403(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test that unauthorized users cannot assign teams to projects."""
        from fastapi import HTTPException

        project_id = uuid4()
        team_id = uuid4()

        # Mock check_project_permission to raise 403
        with patch(
            "app.api.v1.teams.check_project_permission",
            side_effect=HTTPException(status_code=403, detail="Not authorized"),
        ):
            response = await async_client.post(
                f"/api/v1/projects/{project_id}/teams",
                json={"team_id": str(team_id), "permission_level": "editor"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_update_assignment_unauthorized_returns_403(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test that unauthorized users cannot update project team assignments."""
        from fastapi import HTTPException

        project_id = uuid4()
        team_id = uuid4()

        # Mock check_project_permission to raise 403
        with patch(
            "app.api.v1.teams.check_project_permission",
            side_effect=HTTPException(status_code=403, detail="Not authorized"),
        ):
            response = await async_client.patch(
                f"/api/v1/projects/{project_id}/teams/{team_id}",
                json={"permission_level": "viewer"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_remove_assignment_unauthorized_returns_403(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test that unauthorized users cannot remove team assignments."""
        from fastapi import HTTPException

        project_id = uuid4()
        team_id = uuid4()

        # Mock check_project_permission to raise 403
        with patch(
            "app.api.v1.teams.check_project_permission",
            side_effect=HTTPException(status_code=403, detail="Not authorized"),
        ):
            response = await async_client.delete(f"/api/v1/projects/{project_id}/teams/{team_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_assign_team_project_owner_returns_201(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test that project owners can assign teams."""
        from app.models.project import Project

        project_id = uuid4()
        team_id = uuid4()

        # Mock project with user as owner
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.user_id = mock_current_user.id
        mock_project.organization_id = None

        mock_assignment = MagicMock()
        mock_assignment.id = uuid4()
        mock_assignment.project_id = project_id
        mock_assignment.team_id = team_id
        mock_assignment.permission_level = "editor"
        mock_assignment.assigned_by_id = mock_current_user.id
        mock_assignment.assigned_at = datetime.now(tz=UTC)
        mock_assignment.created_at = datetime.now(tz=UTC)
        mock_assignment.updated_at = datetime.now(tz=UTC)

        with (
            patch(
                "app.api.v1.teams.check_project_permission",
                return_value=mock_project,
            ),
            patch.object(TeamService, "assign_team_to_project", return_value=mock_assignment),
        ):
            response = await async_client.post(
                f"/api/v1/projects/{project_id}/teams",
                json={"team_id": str(team_id), "permission_level": "editor"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["team_id"] == str(team_id)
        assert data["permission_level"] == "editor"

    @pytest.mark.asyncio
    async def test_assign_team_org_admin_returns_201(
        self,
        async_client: AsyncClient,
        mock_current_user,
    ) -> None:
        """Test that org admins can assign teams to org projects."""
        from app.models.project import Project

        project_id = uuid4()
        team_id = uuid4()
        org_id = uuid4()

        # Mock project belonging to org
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.user_id = uuid4()  # Different user
        mock_project.organization_id = org_id

        mock_assignment = MagicMock()
        mock_assignment.id = uuid4()
        mock_assignment.project_id = project_id
        mock_assignment.team_id = team_id
        mock_assignment.permission_level = "editor"
        mock_assignment.assigned_by_id = mock_current_user.id
        mock_assignment.assigned_at = datetime.now(tz=UTC)
        mock_assignment.created_at = datetime.now(tz=UTC)
        mock_assignment.updated_at = datetime.now(tz=UTC)

        with (
            patch(
                "app.api.v1.teams.check_project_permission",
                return_value=mock_project,
            ),
            patch.object(TeamService, "assign_team_to_project", return_value=mock_assignment),
        ):
            response = await async_client.post(
                f"/api/v1/projects/{project_id}/teams",
                json={"team_id": str(team_id), "permission_level": "editor"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["team_id"] == str(team_id)
        assert data["permission_level"] == "editor"
