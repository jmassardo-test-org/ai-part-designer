"""
Team service for managing organization teams.

Handles business logic for team CRUD operations,
member management, and project assignments.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.organization import OrganizationMember, OrganizationRole
from app.models.team import ProjectTeam, Team, TeamMember, TeamRole
from app.models.user import User
from app.schemas.team import (
    ProjectTeamAssign,
    ProjectTeamUpdate,
    TeamCreate,
    TeamMemberAdd,
    TeamMemberUpdate,
    TeamUpdate,
)


class TeamServiceError(Exception):
    """Base exception for team service errors."""


class TeamNotFoundError(TeamServiceError):
    """Raised when team is not found."""


class TeamMemberNotFoundError(TeamServiceError):
    """Raised when team member is not found."""


class TeamPermissionError(TeamServiceError):
    """Raised when user lacks permission for team operation."""


class TeamDuplicateError(TeamServiceError):
    """Raised when team slug already exists in organization."""


class TeamMemberExistsError(TeamServiceError):
    """Raised when user is already a team member."""


class TeamService:
    """Service for team management operations."""

    def __init__(self, db: AsyncSession):
        """Initialize team service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def get_team_by_id(
        self,
        team_id: UUID,
        _include_members: bool = False,
    ) -> Team | None:
        """Get a team by ID.

        Args:
            team_id: Team UUID.
            include_members: Whether to load team members (ignored - use list_team_members instead).

        Returns:
            Team if found, None otherwise.
        """
        # Note: include_members parameter is kept for backwards compatibility but ignored
        # because Team.members uses lazy="dynamic" which doesn't support eager loading.
        # Use list_team_members() to get team members instead.
        query = select(Team).where(
            and_(
                Team.id == team_id,
                Team.deleted_at.is_(None),
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_team_by_slug(
        self,
        organization_id: UUID,
        slug: str,
    ) -> Team | None:
        """Get a team by organization and slug.

        Args:
            organization_id: Organization UUID.
            slug: Team slug.

        Returns:
            Team if found, None otherwise.
        """
        query = select(Team).where(
            and_(
                Team.organization_id == organization_id,
                Team.slug == slug,
                Team.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_team_member_count(self, team_id: UUID) -> int:
        """Get the count of active members in a team.

        Args:
            team_id: Team UUID.

        Returns:
            Number of active team members.
        """
        query = select(func.count(TeamMember.id)).where(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.is_active == True,  # noqa: E712
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one() or 0

    async def list_teams(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        include_inactive: bool = False,
    ) -> tuple[list[Team], int]:
        """List teams for an organization.

        Args:
            organization_id: Organization UUID.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            include_inactive: Whether to include inactive teams.

        Returns:
            Tuple of (teams list, total count).
        """
        conditions = [
            Team.organization_id == organization_id,
            Team.deleted_at.is_(None),
        ]

        if not include_inactive:
            conditions.append(Team.is_active == True)  # noqa: E712

        # Count query
        count_query = select(func.count(Team.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Data query with pagination
        query = (
            select(Team)
            .where(and_(*conditions))
            .order_by(Team.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        teams = list(result.scalars().all())

        return teams, total

    async def create_team(
        self,
        organization_id: UUID,
        data: TeamCreate,
        created_by: User,
    ) -> Team:
        """Create a new team.

        Args:
            organization_id: Organization UUID.
            data: Team creation data.
            created_by: User creating the team.

        Returns:
            Created team.

        Raises:
            TeamDuplicateError: If slug already exists.
        """
        # Check for duplicate slug
        if data.slug is None:
            raise ValueError("Team slug is required")
        existing = await self.get_team_by_slug(organization_id, data.slug)
        if existing:
            raise TeamDuplicateError(
                f"Team with slug '{data.slug}' already exists in this organization"
            )

        team = Team(
            organization_id=organization_id,
            name=data.name,
            slug=data.slug,
            description=data.description,
            settings=data.settings or {},
            created_by_id=created_by.id,
            is_active=True,
        )

        self.db.add(team)
        await self.db.flush()

        # Add creator as admin by default
        creator_member = TeamMember(
            team_id=team.id,
            user_id=created_by.id,
            role=TeamRole.ADMIN.value,
            added_by_id=created_by.id,
            is_active=True,
        )
        self.db.add(creator_member)

        await self.db.commit()
        await self.db.refresh(team)

        return team

    async def update_team(
        self,
        team_id: UUID,
        data: TeamUpdate,
    ) -> Team:
        """Update a team.

        Args:
            team_id: Team UUID.
            data: Team update data.

        Returns:
            Updated team.

        Raises:
            TeamNotFoundError: If team not found.
        """
        team = await self.get_team_by_id(team_id)
        if not team:
            raise TeamNotFoundError(f"Team with ID {team_id} not found")

        if data.name is not None:
            team.name = data.name

        if data.description is not None:
            team.description = data.description

        if data.settings is not None:
            # Merge settings
            team.settings = {**team.settings, **data.settings}

        if data.is_active is not None:
            team.is_active = data.is_active

        await self.db.commit()
        await self.db.refresh(team)

        return team

    async def delete_team(self, team_id: UUID) -> None:
        """Soft delete a team.

        Args:
            team_id: Team UUID.

        Raises:
            TeamNotFoundError: If team not found.
        """
        team = await self.get_team_by_id(team_id)
        if not team:
            raise TeamNotFoundError(f"Team with ID {team_id} not found")

        team.deleted_at = datetime.now(tz=UTC)
        team.is_active = False

        await self.db.commit()

    # Team Member operations

    async def get_team_member(
        self,
        team_id: UUID,
        user_id: UUID,
    ) -> TeamMember | None:
        """Get a team member.

        Args:
            team_id: Team UUID.
            user_id: User UUID.

        Returns:
            TeamMember if found, None otherwise.
        """
        query = select(TeamMember).where(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_team_members(
        self,
        team_id: UUID,
        page: int = 1,
        page_size: int = 50,
        include_inactive: bool = False,
    ) -> tuple[list[TeamMember], int]:
        """List members of a team.

        Args:
            team_id: Team UUID.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            include_inactive: Whether to include inactive members.

        Returns:
            Tuple of (members list, total count).
        """
        conditions = [TeamMember.team_id == team_id]

        if not include_inactive:
            conditions.append(TeamMember.is_active == True)  # noqa: E712

        # Count query
        count_query = select(func.count(TeamMember.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Data query with user info
        query = (
            select(TeamMember)
            .options(joinedload(TeamMember.user))
            .where(and_(*conditions))
            .order_by(TeamMember.joined_at)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        members = list(result.scalars().all())

        return members, total

    async def add_team_member(
        self,
        team_id: UUID,
        data: TeamMemberAdd,
        added_by: User,
    ) -> TeamMember:
        """Add a member to a team.

        Args:
            team_id: Team UUID.
            data: Member add data.
            added_by: User adding the member.

        Returns:
            Created team member.

        Raises:
            TeamNotFoundError: If team not found.
            TeamMemberExistsError: If user already a member.
        """
        # Verify team exists
        team = await self.get_team_by_id(team_id)
        if not team:
            raise TeamNotFoundError(f"Team with ID {team_id} not found")

        # Check if already a member
        existing = await self.get_team_member(team_id, data.user_id)
        if existing:
            if existing.is_active:
                raise TeamMemberExistsError("User is already a member of this team")
            # Reactivate inactive member
            existing.is_active = True
            existing.role = data.role
            existing.added_by_id = added_by.id
            existing.joined_at = datetime.now(tz=UTC)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        member = TeamMember(
            team_id=team_id,
            user_id=data.user_id,
            role=data.role,
            added_by_id=added_by.id,
            is_active=True,
        )

        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def update_team_member(
        self,
        team_id: UUID,
        user_id: UUID,
        data: TeamMemberUpdate,
    ) -> TeamMember:
        """Update a team member.

        Args:
            team_id: Team UUID.
            user_id: User UUID.
            data: Member update data.

        Returns:
            Updated team member.

        Raises:
            TeamMemberNotFoundError: If member not found.
        """
        member = await self.get_team_member(team_id, user_id)
        if not member:
            raise TeamMemberNotFoundError("User is not a member of this team")

        if data.role is not None:
            member.role = data.role

        if data.is_active is not None:
            member.is_active = data.is_active

        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def remove_team_member(
        self,
        team_id: UUID,
        user_id: UUID,
    ) -> None:
        """Remove a member from a team (soft delete).

        Args:
            team_id: Team UUID.
            user_id: User UUID.

        Raises:
            TeamMemberNotFoundError: If member not found.
        """
        member = await self.get_team_member(team_id, user_id)
        if not member:
            raise TeamMemberNotFoundError("User is not a member of this team")

        member.is_active = False
        await self.db.commit()

    # User's teams

    async def get_user_teams(
        self,
        user_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all teams a user belongs to.

        Args:
            user_id: User UUID.

        Returns:
            List of team membership info with team and org details.
        """
        query = (
            select(TeamMember)
            .options(joinedload(TeamMember.team).joinedload(Team.organization))
            .where(
                and_(
                    TeamMember.user_id == user_id,
                    TeamMember.is_active,
                )
            )
        )

        result = await self.db.execute(query)
        memberships = result.scalars().all()

        teams = []
        for membership in memberships:
            if membership.team and not membership.team.deleted_at:
                teams.append(
                    {
                        "id": membership.id,
                        "team_id": membership.team.id,
                        "team_name": membership.team.name,
                        "team_slug": membership.team.slug,
                        "organization_id": membership.team.organization_id,
                        "organization_name": membership.team.organization.name
                        if membership.team.organization
                        else None,
                        "role": membership.role,
                        "joined_at": membership.joined_at,
                        "is_active": membership.is_active,
                    }
                )

        return teams

    async def leave_team(
        self,
        team_id: UUID,
        user_id: UUID,
    ) -> None:
        """Remove user from a team (self-removal).

        Args:
            team_id: Team UUID.
            user_id: User UUID.

        Raises:
            TeamMemberNotFoundError: If not a member.
        """
        await self.remove_team_member(team_id, user_id)

    # Project-Team assignments

    async def get_project_team(
        self,
        project_id: UUID,
        team_id: UUID,
    ) -> ProjectTeam | None:
        """Get a project-team assignment.

        Args:
            project_id: Project UUID.
            team_id: Team UUID.

        Returns:
            ProjectTeam if found, None otherwise.
        """
        query = select(ProjectTeam).where(
            and_(
                ProjectTeam.project_id == project_id,
                ProjectTeam.team_id == team_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_project_teams(
        self,
        project_id: UUID,
    ) -> list[ProjectTeam]:
        """List teams assigned to a project.

        Args:
            project_id: Project UUID.

        Returns:
            List of project-team assignments.
        """
        query = (
            select(ProjectTeam)
            .options(joinedload(ProjectTeam.team))
            .where(ProjectTeam.project_id == project_id)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def assign_team_to_project(
        self,
        data: ProjectTeamAssign,
        project_id: UUID,
        assigned_by: User,
    ) -> ProjectTeam:
        """Assign a team to a project.

        Args:
            data: Assignment data.
            project_id: Project UUID.
            assigned_by: User making the assignment.

        Returns:
            Created project-team assignment.
        """
        # Check if already assigned
        existing = await self.get_project_team(project_id, data.team_id)
        if existing:
            # Update permission level
            existing.permission_level = data.permission_level
            existing.assigned_by_id = assigned_by.id
            existing.assigned_at = datetime.now(tz=UTC)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        assignment = ProjectTeam(
            project_id=project_id,
            team_id=data.team_id,
            permission_level=data.permission_level,
            assigned_by_id=assigned_by.id,
        )

        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)

        return assignment

    async def update_project_team(
        self,
        project_id: UUID,
        team_id: UUID,
        data: ProjectTeamUpdate,
    ) -> ProjectTeam:
        """Update a project-team assignment.

        Args:
            project_id: Project UUID.
            team_id: Team UUID.
            data: Update data.

        Returns:
            Updated assignment.
        """
        assignment = await self.get_project_team(project_id, team_id)
        if not assignment:
            raise TeamNotFoundError("Team is not assigned to this project")

        assignment.permission_level = data.permission_level
        await self.db.commit()
        await self.db.refresh(assignment)

        return assignment

    async def remove_team_from_project(
        self,
        project_id: UUID,
        team_id: UUID,
    ) -> None:
        """Remove a team from a project.

        Args:
            project_id: Project UUID.
            team_id: Team UUID.
        """
        assignment = await self.get_project_team(project_id, team_id)
        if assignment:
            await self.db.delete(assignment)
            await self.db.commit()

    # Permission checks

    async def check_team_permission(
        self,
        team_id: UUID,
        user: User,
        required_role: TeamRole,
    ) -> bool:
        """Check if user has required role in team.

        Args:
            team_id: Team UUID.
            user: User to check.
            required_role: Minimum required role.

        Returns:
            True if user has permission.
        """
        member = await self.get_team_member(team_id, user.id)
        if not member or not member.is_active:
            return False
        return member.has_permission(required_role)

    async def check_org_team_permission(
        self,
        organization_id: UUID,
        user: User,
    ) -> bool:
        """Check if user has permission to manage teams in org.

        Args:
            organization_id: Organization UUID.
            user: User to check.

        Returns:
            True if user has org admin permission.
        """
        query = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active,
            )
        )
        result = await self.db.execute(query)
        member = result.scalar_one_or_none()

        if not member:
            return False

        return member.has_permission(OrganizationRole.ADMIN)
