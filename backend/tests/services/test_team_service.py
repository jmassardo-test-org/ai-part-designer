"""
Tests for team service.

Tests team CRUD operations, member management, and permissions.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.team import Team, TeamMember, TeamRole
from app.models.user import User
from app.schemas.team import TeamCreate, TeamMemberAdd, TeamUpdate
from app.services.team_service import (
    TeamDuplicateError,
    TeamMemberExistsError,
    TeamMemberNotFoundError,
    TeamNotFoundError,
    TeamPermissionError,
    TeamService,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def team_service(db_session: AsyncSession) -> TeamService:
    """Create a team service instance."""
    return TeamService(db_session)


@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(
        id=uuid4(),
        name="Test Organization",
        slug="test-org",
    )
    db_session.add(org)
    await db_session.commit()
    return org


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession, test_org: Organization) -> User:
    """Create a test admin user."""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        username="adminuser",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    # Make user an admin of the organization
    member = OrganizationMember(
        organization_id=test_org.id,
        user_id=user.id,
        role=OrganizationRole.ADMIN,
    )
    db_session.add(member)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_team(db_session: AsyncSession, test_org: Organization) -> Team:
    """Create a test team."""
    team = Team(
        id=uuid4(),
        organization_id=test_org.id,
        name="Test Team",
        slug="test-team",
        description="Test team description",
    )
    db_session.add(team)
    await db_session.commit()
    return team


# =============================================================================
# Team CRUD Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_team_by_id_success(
    team_service: TeamService,
    test_team: Team,
):
    """Test retrieving a team by ID."""
    result = await team_service.get_team_by_id(test_team.id)

    assert result is not None
    assert result.id == test_team.id
    assert result.name == test_team.name
    assert result.slug == test_team.slug


@pytest.mark.asyncio
async def test_get_team_by_id_not_found(
    team_service: TeamService,
):
    """Test retrieving a non-existent team."""
    result = await team_service.get_team_by_id(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_team_by_slug_success(
    team_service: TeamService,
    test_org: Organization,
    test_team: Team,
):
    """Test retrieving a team by organization and slug."""
    result = await team_service.get_team_by_slug(test_org.id, test_team.slug)

    assert result is not None
    assert result.id == test_team.id
    assert result.slug == test_team.slug


@pytest.mark.asyncio
async def test_get_team_by_slug_not_found(
    team_service: TeamService,
    test_org: Organization,
):
    """Test retrieving a non-existent team by slug."""
    result = await team_service.get_team_by_slug(test_org.id, "nonexistent-slug")

    assert result is None


@pytest.mark.asyncio
async def test_create_team_success(
    team_service: TeamService,
    test_org: Organization,
    test_admin_user: User,
    db_session: AsyncSession,
):
    """Test creating a new team."""
    team_data = TeamCreate(
        name="New Team",
        slug="new-team",
        description="A new team",
    )

    result = await team_service.create_team(
        organization_id=test_org.id,
        team_data=team_data,
        creator_id=test_admin_user.id,
    )

    assert result is not None
    assert result.name == "New Team"
    assert result.slug == "new-team"
    assert result.organization_id == test_org.id

    # Verify team was saved to database
    await db_session.refresh(result)
    assert result.id is not None


@pytest.mark.asyncio
async def test_create_team_duplicate_slug_raises_error(
    team_service: TeamService,
    test_org: Organization,
    test_admin_user: User,
    test_team: Team,
):
    """Test creating a team with duplicate slug raises error."""
    team_data = TeamCreate(
        name="Duplicate Team",
        slug=test_team.slug,  # Use existing slug
        description="This should fail",
    )

    with pytest.raises(TeamDuplicateError):
        await team_service.create_team(
            organization_id=test_org.id,
            team_data=team_data,
            creator_id=test_admin_user.id,
        )


@pytest.mark.asyncio
async def test_update_team_success(
    team_service: TeamService,
    test_team: Team,
    test_admin_user: User,
    db_session: AsyncSession,
):
    """Test updating a team."""
    update_data = TeamUpdate(
        name="Updated Team Name",
        description="Updated description",
    )

    result = await team_service.update_team(
        team_id=test_team.id,
        team_data=update_data,
        user_id=test_admin_user.id,
    )

    assert result is not None
    assert result.name == "Updated Team Name"
    assert result.description == "Updated description"

    # Verify changes were saved
    await db_session.refresh(test_team)
    assert test_team.name == "Updated Team Name"


@pytest.mark.asyncio
async def test_update_team_not_found_raises_error(
    team_service: TeamService,
    test_admin_user: User,
):
    """Test updating a non-existent team raises error."""
    update_data = TeamUpdate(
        name="Updated Team",
    )

    with pytest.raises(TeamNotFoundError):
        await team_service.update_team(
            team_id=uuid4(),
            team_data=update_data,
            user_id=test_admin_user.id,
        )


@pytest.mark.asyncio
async def test_delete_team_success(
    team_service: TeamService,
    test_team: Team,
    test_admin_user: User,
    db_session: AsyncSession,
):
    """Test deleting a team (soft delete)."""
    result = await team_service.delete_team(
        team_id=test_team.id,
        user_id=test_admin_user.id,
    )

    assert result is True

    # Verify team is soft deleted
    await db_session.refresh(test_team)
    assert test_team.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_team_not_found_raises_error(
    team_service: TeamService,
    test_admin_user: User,
):
    """Test deleting a non-existent team raises error."""
    with pytest.raises(TeamNotFoundError):
        await team_service.delete_team(
            team_id=uuid4(),
            user_id=test_admin_user.id,
        )


# =============================================================================
# Team Member Management Tests
# =============================================================================


@pytest.mark.asyncio
async def test_add_team_member_success(
    team_service: TeamService,
    test_team: Team,
    test_user: User,
    test_admin_user: User,
    db_session: AsyncSession,
):
    """Test adding a member to a team."""
    member_data = TeamMemberAdd(
        user_id=test_user.id,
        role=TeamRole.MEMBER,
    )

    result = await team_service.add_team_member(
        team_id=test_team.id,
        member_data=member_data,
        added_by_id=test_admin_user.id,
    )

    assert result is not None
    assert result.user_id == test_user.id
    assert result.team_id == test_team.id
    assert result.role == TeamRole.MEMBER

    # Verify member was saved
    await db_session.refresh(result)
    assert result.id is not None


@pytest.mark.asyncio
async def test_add_team_member_duplicate_raises_error(
    team_service: TeamService,
    test_team: Team,
    test_user: User,
    test_admin_user: User,
    db_session: AsyncSession,
):
    """Test adding a duplicate team member raises error."""
    # Add member first time
    member = TeamMember(
        team_id=test_team.id,
        user_id=test_user.id,
        role=TeamRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()

    # Try to add same member again
    member_data = TeamMemberAdd(
        user_id=test_user.id,
        role=TeamRole.MEMBER,
    )

    with pytest.raises(TeamMemberExistsError):
        await team_service.add_team_member(
            team_id=test_team.id,
            member_data=member_data,
            added_by_id=test_admin_user.id,
        )


@pytest.mark.asyncio
async def test_remove_team_member_success(
    team_service: TeamService,
    test_team: Team,
    test_user: User,
    test_admin_user: User,
    db_session: AsyncSession,
):
    """Test removing a team member."""
    # Add member first
    member = TeamMember(
        team_id=test_team.id,
        user_id=test_user.id,
        role=TeamRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()

    # Remove member
    result = await team_service.remove_team_member(
        team_id=test_team.id,
        user_id=test_user.id,
        removed_by_id=test_admin_user.id,
    )

    assert result is True

    # Verify member was removed
    from sqlalchemy import select

    query = select(TeamMember).where(
        TeamMember.team_id == test_team.id,
        TeamMember.user_id == test_user.id,
    )
    result_check = await db_session.execute(query)
    assert result_check.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_remove_team_member_not_found_raises_error(
    team_service: TeamService,
    test_team: Team,
    test_admin_user: User,
):
    """Test removing a non-existent team member raises error."""
    with pytest.raises(TeamMemberNotFoundError):
        await team_service.remove_team_member(
            team_id=test_team.id,
            user_id=uuid4(),
            removed_by_id=test_admin_user.id,
        )


@pytest.mark.asyncio
async def test_list_team_members(
    team_service: TeamService,
    test_team: Team,
    test_user: User,
    db_session: AsyncSession,
):
    """Test listing team members."""
    # Add a team member
    member = TeamMember(
        team_id=test_team.id,
        user_id=test_user.id,
        role=TeamRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()

    # List members
    members = await team_service.list_team_members(test_team.id)

    assert len(members) == 1
    assert members[0].user_id == test_user.id
    assert members[0].team_id == test_team.id


@pytest.mark.asyncio
async def test_list_team_members_empty_team(
    team_service: TeamService,
    test_team: Team,
):
    """Test listing members of empty team."""
    members = await team_service.list_team_members(test_team.id)

    assert len(members) == 0


# =============================================================================
# Permission Tests
# =============================================================================


@pytest.mark.asyncio
async def test_check_team_permission_admin_has_permission(
    team_service: TeamService,
    test_team: Team,
    test_admin_user: User,
):
    """Test admin user has team permissions."""
    has_permission = await team_service.check_team_permission(
        team_id=test_team.id,
        user_id=test_admin_user.id,
        required_role=TeamRole.MEMBER,
    )

    assert has_permission is True


@pytest.mark.asyncio
async def test_check_team_permission_member_has_permission(
    team_service: TeamService,
    test_team: Team,
    test_user: User,
    db_session: AsyncSession,
):
    """Test team member has appropriate permissions."""
    # Add user as team member
    member = TeamMember(
        team_id=test_team.id,
        user_id=test_user.id,
        role=TeamRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()

    has_permission = await team_service.check_team_permission(
        team_id=test_team.id,
        user_id=test_user.id,
        required_role=TeamRole.MEMBER,
    )

    assert has_permission is True


@pytest.mark.asyncio
async def test_check_team_permission_non_member_denied(
    team_service: TeamService,
    test_team: Team,
    test_user: User,
):
    """Test non-member is denied team permissions."""
    has_permission = await team_service.check_team_permission(
        team_id=test_team.id,
        user_id=test_user.id,
        required_role=TeamRole.MEMBER,
    )

    assert has_permission is False


# =============================================================================
# Exception Tests
# =============================================================================


def test_team_service_error_hierarchy():
    """Test exception hierarchy for team service."""
    assert issubclass(TeamNotFoundError, TeamServiceError)
    assert issubclass(TeamMemberNotFoundError, TeamServiceError)
    assert issubclass(TeamPermissionError, TeamServiceError)
    assert issubclass(TeamDuplicateError, TeamServiceError)
    assert issubclass(TeamMemberExistsError, TeamServiceError)


def test_team_service_exceptions_can_be_raised():
    """Test team service exceptions can be raised and caught."""
    with pytest.raises(TeamServiceError):
        raise TeamNotFoundError("Team not found")

    with pytest.raises(TeamNotFoundError):
        raise TeamNotFoundError("Team not found")

    with pytest.raises(TeamPermissionError):
        raise TeamPermissionError("Permission denied")
