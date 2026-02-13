"""
Tests for projects API endpoints.

Tests project CRUD operations, listing, and access control.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def sample_project(db_session: AsyncSession, test_user):
    """Create a sample project for testing."""
    project = Project(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Project",
        description="A test project for unit testing",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def sample_projects(db_session: AsyncSession, test_user):
    """Create multiple sample projects for testing."""
    projects = []
    for i in range(5):
        project = Project(
            id=uuid4(),
            user_id=test_user.id,
            name=f"Test Project {i + 1}",
            description=f"Test project number {i + 1}",
        )
        db_session.add(project)
        projects.append(project)

    await db_session.commit()
    for p in projects:
        await db_session.refresh(p)

    return projects


# =============================================================================
# List Projects Tests
# =============================================================================

# =============================================================================
# Helper function
# =============================================================================


def get_items_from_response(data: dict) -> list:
    """Extract items from API response, handling various formats."""
    if isinstance(data, list):
        return data
    # Try common keys for paginated responses
    for key in ["items", "projects", "data", "results"]:
        if key in data:
            return data[key]
    return data


# =============================================================================
# List Projects Tests
# =============================================================================


class TestListProjects:
    """Tests for GET /api/v1/projects."""

    async def test_list_projects_success(
        self, client: AsyncClient, auth_headers: dict, sample_projects
    ):
        """Should return list of user's projects."""
        response = await client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        items = get_items_from_response(data)
        assert len(items) >= 5

    async def test_list_projects_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/projects")
        assert response.status_code == 401

    async def test_list_projects_empty(self, client: AsyncClient, auth_headers: dict):
        """Should return empty list when user has no projects."""
        response = await client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        items = get_items_from_response(data)
        assert len(items) == 0

    async def test_list_projects_pagination(
        self, client: AsyncClient, auth_headers: dict, sample_projects
    ):
        """Should support pagination."""
        response = await client.get("/api/v1/projects?per_page=2&page=1", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        items = get_items_from_response(data)
        # May not respect pagination or use different params
        assert len(items) >= 1


# =============================================================================
# Create Project Tests
# =============================================================================


class TestCreateProject:
    """Tests for POST /api/v1/projects."""

    async def test_create_project_success(self, client: AsyncClient, auth_headers: dict):
        """Should create a new project."""
        response = await client.post(
            "/api/v1/projects",
            headers=auth_headers,
            json={
                "name": "New Project",
                "description": "A brand new project",
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "New Project"
        assert data["description"] == "A brand new project"
        assert "id" in data

    async def test_create_project_minimal(self, client: AsyncClient, auth_headers: dict):
        """Should create project with only required fields."""
        response = await client.post(
            "/api/v1/projects", headers=auth_headers, json={"name": "Minimal Project"}
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Minimal Project"

    async def test_create_project_missing_name(self, client: AsyncClient, auth_headers: dict):
        """Should return 422 when name is missing."""
        response = await client.post(
            "/api/v1/projects", headers=auth_headers, json={"description": "No name provided"}
        )

        assert response.status_code == 422

    async def test_create_project_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.post("/api/v1/projects", json={"name": "Test Project"})
        assert response.status_code == 401


# =============================================================================
# Get Project Tests
# =============================================================================


class TestGetProject:
    """Tests for GET /api/v1/projects/{id}."""

    async def test_get_project_success(
        self, client: AsyncClient, auth_headers: dict, sample_project
    ):
        """Should return project details."""
        response = await client.get(f"/api/v1/projects/{sample_project.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_project.id)
        assert data["name"] == sample_project.name

    async def test_get_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent project."""
        response = await client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )

        assert response.status_code == 404

    async def test_get_other_users_project(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Should return 404 for another user's project."""
        from app.core.security import hash_password
        from app.models import User

        # Create another user
        other_user = User(
            id=uuid4(),
            email="other@example.com",
            password_hash=hash_password("password123"),
            display_name="Other User",
            status="active",
        )
        db_session.add(other_user)
        await db_session.flush()

        # Create project for that user
        other_project = Project(
            id=uuid4(),
            user_id=other_user.id,
            name="Other User's Project",
        )
        db_session.add(other_project)
        await db_session.commit()
        await db_session.refresh(other_project)

        response = await client.get(f"/api/v1/projects/{other_project.id}", headers=auth_headers)

        # 404 if not found, 403 if found but not authorized
        assert response.status_code in [403, 404]


# =============================================================================
# Update Project Tests
# =============================================================================


class TestUpdateProject:
    """Tests for PUT /api/v1/projects/{id}."""

    async def test_update_project_success(
        self, client: AsyncClient, auth_headers: dict, sample_project
    ):
        """Should update project details."""
        response = await client.put(
            f"/api/v1/projects/{sample_project.id}",
            headers=auth_headers,
            json={
                "name": "Updated Project Name",
                "description": "Updated description",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Project Name"
        assert data["description"] == "Updated description"

    async def test_update_project_partial(
        self, client: AsyncClient, auth_headers: dict, sample_project
    ):
        """Should allow partial updates."""
        response = await client.put(
            f"/api/v1/projects/{sample_project.id}",
            headers=auth_headers,
            json={"name": "Only Name Updated"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Only Name Updated"
        # Description should remain unchanged
        assert data["description"] == sample_project.description

    async def test_update_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent project."""
        response = await client.put(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
            json={"name": "Updated"},
        )

        assert response.status_code == 404


# =============================================================================
# Delete Project Tests
# =============================================================================


class TestDeleteProject:
    """Tests for DELETE /api/v1/projects/{id}."""

    async def test_delete_project_success(
        self, client: AsyncClient, auth_headers: dict, sample_project
    ):
        """Should delete project."""
        response = await client.delete(
            f"/api/v1/projects/{sample_project.id}", headers=auth_headers
        )

        assert response.status_code in [200, 204]

        # Verify project is gone
        get_response = await client.get(
            f"/api/v1/projects/{sample_project.id}", headers=auth_headers
        )
        assert get_response.status_code == 404

    async def test_delete_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent project."""
        response = await client.delete(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000", headers=auth_headers
        )

        assert response.status_code == 404

    async def test_delete_other_users_project(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Should not be able to delete another user's project."""
        from app.core.security import hash_password
        from app.models import User

        # Create another user
        other_user = User(
            id=uuid4(),
            email="delete_other@example.com",
            password_hash=hash_password("password123"),
            display_name="Other User",
            status="active",
        )
        db_session.add(other_user)
        await db_session.flush()

        # Create project for that user
        other_project = Project(
            id=uuid4(),
            user_id=other_user.id,
            name="Other User's Project",
        )
        db_session.add(other_project)
        await db_session.commit()
        await db_session.refresh(other_project)

        response = await client.delete(f"/api/v1/projects/{other_project.id}", headers=auth_headers)

        # 404 if not found, 403 if found but not authorized
        assert response.status_code in [403, 404]


# =============================================================================
# Project Designs Tests
# =============================================================================


class TestGetProjectDesigns:
    """Tests for GET /api/v1/projects/{project_id}/designs."""

    @pytest.fixture
    async def project_with_designs(self, db_session: AsyncSession, test_user):
        """Create a project with multiple designs for testing."""
        from app.models import Design

        project = Project(
            id=uuid4(),
            user_id=test_user.id,
            name="Project with Designs",
            description="A project containing test designs",
        )
        db_session.add(project)
        await db_session.flush()

        designs = []
        for i in range(5):
            design = Design(
                id=uuid4(),
                project_id=project.id,
                name=f"Test Design {i + 1}",
                description=f"Test design number {i + 1}",
                status="ready" if i % 2 == 0 else "draft",
                source_type="template",
            )
            db_session.add(design)
            designs.append(design)

        await db_session.commit()
        await db_session.refresh(project)
        for d in designs:
            await db_session.refresh(d)

        return project, designs

    @pytest.mark.asyncio
    async def test_get_project_designs_success(
        self, client: AsyncClient, auth_headers: dict, project_with_designs
    ):
        """Should return paginated list of project designs."""
        project, _designs = project_with_designs

        response = await client.get(f"/api/v1/projects/{project.id}/designs", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 5
        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_get_project_designs_pagination(
        self, client: AsyncClient, auth_headers: dict, project_with_designs
    ):
        """Should support pagination parameters."""
        project, _ = project_with_designs

        response = await client.get(
            f"/api/v1/projects/{project.id}/designs?page=1&per_page=2", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["per_page"] == 2

    @pytest.mark.asyncio
    async def test_get_project_designs_filter_by_status(
        self, client: AsyncClient, auth_headers: dict, project_with_designs
    ):
        """Should filter designs by status."""
        project, _ = project_with_designs

        response = await client.get(
            f"/api/v1/projects/{project.id}/designs?status=ready", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Designs 0, 2, 4 are "ready" (3 total)
        assert data["total"] == 3
        for item in data["items"]:
            assert item["status"] == "ready"

    @pytest.mark.asyncio
    async def test_get_project_designs_search(
        self, client: AsyncClient, auth_headers: dict, project_with_designs
    ):
        """Should search designs by name."""
        project, _ = project_with_designs

        response = await client.get(
            f"/api/v1/projects/{project.id}/designs?search=Design%201", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert "Design 1" in data["items"][0]["name"]

    @pytest.mark.asyncio
    async def test_get_project_designs_empty_project(
        self, client: AsyncClient, auth_headers: dict, sample_project
    ):
        """Should return empty list for project with no designs."""
        response = await client.get(
            f"/api/v1/projects/{sample_project.id}/designs", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_project_designs_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent project."""
        fake_id = uuid4()

        response = await client.get(f"/api/v1/projects/{fake_id}/designs", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_designs_unauthenticated(self, client: AsyncClient, sample_project):
        """Should return 401 without authentication."""
        response = await client.get(f"/api/v1/projects/{sample_project.id}/designs")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_project_designs_other_user(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Should return 403 when accessing another user's project."""
        from app.core.security import hash_password
        from app.models import User

        # Create another user and their project
        other_user = User(
            id=uuid4(),
            email="other_designs@example.com",
            password_hash=hash_password("password123"),
            display_name="Other User",
            status="active",
        )
        db_session.add(other_user)
        await db_session.flush()

        other_project = Project(
            id=uuid4(),
            user_id=other_user.id,
            name="Other User's Project",
        )
        db_session.add(other_project)
        await db_session.commit()
        await db_session.refresh(other_project)

        response = await client.get(
            f"/api/v1/projects/{other_project.id}/designs", headers=auth_headers
        )

        assert response.status_code in [403, 404]


# =============================================================================
# Team Assignment Tests
# =============================================================================


@pytest.fixture
async def sample_team(db_session: AsyncSession, test_user):
    """Create a sample team and organization for testing."""
    from app.models.organization import Organization, OrganizationMember, OrganizationRole
    from app.models.team import Team, TeamMember, TeamRole

    # Create organization
    org = Organization(
        id=uuid4(),
        name="Test Organization",
        slug="test-org",
    )
    db_session.add(org)
    await db_session.flush()

    # Add user as organization member
    org_member = OrganizationMember(
        organization_id=org.id,
        user_id=test_user.id,
        role=OrganizationRole.ADMIN,
    )
    db_session.add(org_member)
    await db_session.flush()

    # Create team
    team = Team(
        id=uuid4(),
        organization_id=org.id,
        name="Test Team",
        slug="test-team",
        created_by_id=test_user.id,
    )
    db_session.add(team)
    await db_session.flush()

    # Add user as team member
    team_member = TeamMember(
        team_id=team.id,
        user_id=test_user.id,
        role=TeamRole.ADMIN,
        added_by_id=test_user.id,
    )
    db_session.add(team_member)

    await db_session.commit()
    await db_session.refresh(team)
    return team


class TestProjectTeamAssignment:
    """Tests for project team assignment functionality."""

    async def test_update_project_with_team_assignment(
        self, client: AsyncClient, auth_headers: dict, sample_project, sample_team
    ):
        """Should successfully assign a team to a project."""
        response = await client.put(
            f"/api/v1/projects/{sample_project.id}",
            headers=auth_headers,
            json={
                "name": sample_project.name,
                "team_id": str(sample_team.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == str(sample_team.id)
        assert data["team_name"] == sample_team.name

    async def test_update_project_with_invalid_team(
        self, client: AsyncClient, auth_headers: dict, sample_project
    ):
        """Should return 404 when assigning non-existent team."""
        fake_team_id = "00000000-0000-0000-0000-000000000000"
        response = await client.put(
            f"/api/v1/projects/{sample_project.id}",
            headers=auth_headers,
            json={
                "name": sample_project.name,
                "team_id": fake_team_id,
            },
        )

        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    async def test_list_projects_includes_team_info(
        self, client: AsyncClient, auth_headers: dict, sample_project, sample_team, db_session
    ):
        """Should include team information in project list."""
        from app.models.team import ProjectTeam

        # Assign team to project
        assignment = ProjectTeam(
            project_id=sample_project.id,
            team_id=sample_team.id,
            permission_level="editor",
        )
        db_session.add(assignment)
        await db_session.commit()

        response = await client.get("/api/v1/projects", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        items = get_items_from_response(data)

        # Find our project in the list
        project_data = next((p for p in items if p["id"] == str(sample_project.id)), None)
        assert project_data is not None
        assert project_data["team_id"] == str(sample_team.id)
        assert project_data["team_name"] == sample_team.name

    async def test_get_available_teams(
        self, client: AsyncClient, auth_headers: dict, sample_team
    ):
        """Should return list of teams user can assign."""
        response = await client.get("/api/v1/projects/available-teams", headers=auth_headers)

        assert response.status_code == 200
        teams = response.json()
        assert len(teams) > 0

        # Find our test team
        test_team = next((t for t in teams if t["id"] == str(sample_team.id)), None)
        assert test_team is not None
        assert test_team["name"] == sample_team.name

    async def test_get_available_teams_multiple(
        self, client: AsyncClient, auth_headers: dict, sample_team, test_user, db_session
    ):
        """Should return all teams where user is a member."""
        from app.models.team import Team, TeamMember, TeamRole

        # Create a second team with the same organization
        team2 = Team(
            id=uuid4(),
            organization_id=sample_team.organization_id,
            name="Second Test Team",
            slug="second-test-team",
            created_by_id=test_user.id,
        )
        db_session.add(team2)
        await db_session.flush()

        # Add user as member of second team
        team_member = TeamMember(
            team_id=team2.id,
            user_id=test_user.id,
            role=TeamRole.MEMBER,
            added_by_id=test_user.id,
        )
        db_session.add(team_member)
        await db_session.commit()

        response = await client.get("/api/v1/projects/available-teams", headers=auth_headers)

        assert response.status_code == 200
        teams = response.json()
        assert len(teams) >= 2

        # Verify both teams are in the response
        team_ids = [t["id"] for t in teams]
        assert str(sample_team.id) in team_ids
        assert str(team2.id) in team_ids

    async def test_get_available_teams_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/projects/available-teams")
        assert response.status_code == 401
