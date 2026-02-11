"""
Teams API routes.

Provides endpoints for managing organization teams,
team members, and project-team assignments.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.organizations import require_org_role
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.organization import OrganizationRole
from app.models.project import Project
from app.models.team import TeamRole
from app.models.user import User
from app.schemas.team import (
    ProjectTeamAssign,
    ProjectTeamResponse,
    ProjectTeamUpdate,
    TeamCreate,
    TeamDetailResponse,
    TeamListResponse,
    TeamMemberAdd,
    TeamMemberBulkAdd,
    TeamMemberInfo,
    TeamMemberListResponse,
    TeamMemberResponse,
    TeamMemberUpdate,
    TeamResponse,
    TeamUpdate,
    UserTeamListResponse,
    UserTeamResponse,
)
from app.services.team_service import (
    TeamDuplicateError,
    TeamMemberExistsError,
    TeamMemberNotFoundError,
    TeamNotFoundError,
    TeamService,
)

router = APIRouter(tags=["teams"])


# Dependency for getting team service
async def get_team_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamService:
    """Get team service instance."""
    return TeamService(db)


async def check_project_permission(
    db: AsyncSession,
    project_id: UUID,
    user: User,
) -> Project:
    """Check if user has permission to manage project team assignments.

    User has permission if they are:
    - The project owner (user_id matches)
    - An ADMIN or OWNER in the project's organization (if project has one)

    Args:
        db: Database session.
        project_id: Project UUID.
        user: Current authenticated user.

    Returns:
        Project instance if user has permission.

    Raises:
        HTTPException 404: If project not found.
        HTTPException 403: If user lacks permission.
    """
    # Fetch project
    query = select(Project).where(Project.id == project_id).where(Project.deleted_at.is_(None))
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if user is project owner
    if project.user_id == user.id:
        return project

    # Check if project has organization and user is admin
    if project.organization_id:
        try:
            await require_org_role(
                db,
                project.organization_id,
                user.id,
                OrganizationRole.ADMIN,
            )
            return project
        except HTTPException:
            # User is not an admin in the organization
            pass

    # User has no permission
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to manage team assignments for this project",
    )


# Team CRUD endpoints


@router.post(
    "/organizations/{organization_id}/teams",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new team",
    description="Create a new team within an organization. Requires admin permission.",
)
async def create_team(
    organization_id: UUID,
    data: TeamCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TeamResponse:
    """Create a new team in an organization.

    Args:
        organization_id: Organization UUID.
        data: Team creation data.
        current_user: Authenticated user.
        service: Team service.

    Returns:
        Created team.

    Raises:
        HTTPException 403: If user lacks permission.
        HTTPException 409: If team slug already exists.
    """
    # Check permission
    has_permission = await service.check_org_team_permission(organization_id, current_user)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create teams in this organization",
        )

    try:
        team = await service.create_team(organization_id, data, current_user)
        return TeamResponse.model_validate(team)
    except TeamDuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/organizations/{organization_id}/teams",
    response_model=TeamListResponse,
    summary="List organization teams",
    description="List all teams in an organization.",
)
async def list_teams(
    organization_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    include_inactive: bool = Query(False, description="Include inactive teams"),
) -> TeamListResponse:
    """List teams in an organization.

    Args:
        organization_id: Organization UUID.
        current_user: Authenticated user.
        service: Team service.
        page: Page number.
        page_size: Items per page.
        include_inactive: Include inactive teams.

    Returns:
        Paginated team list.
    """
    teams, total = await service.list_teams(
        organization_id,
        page=page,
        page_size=page_size,
        include_inactive=include_inactive,
    )

    return TeamListResponse(
        items=[TeamResponse.model_validate(t) for t in teams],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get(
    "/organizations/{organization_id}/teams/{team_id}",
    response_model=TeamDetailResponse,
    summary="Get team details",
    description="Get detailed information about a team including members.",
)
async def get_team(
    organization_id: UUID,
    team_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TeamDetailResponse:
    """Get team details with members.

    Args:
        organization_id: Organization UUID.
        team_id: Team UUID.
        current_user: Authenticated user.
        service: Team service.

    Returns:
        Team details with member list.

    Raises:
        HTTPException 404: If team not found.
    """
    team = await service.get_team_by_id(team_id, include_members=True)
    if not team or team.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Get active members
    members, _ = await service.list_team_members(team_id, page_size=100)
    member_infos = [
        TeamMemberInfo(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email if m.user else "",
            full_name=m.user.display_name if m.user else None,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in members
    ]

    response_data = {
        **team.__dict__,
        "members": member_infos,
    }

    return TeamDetailResponse.model_validate(response_data)


@router.patch(
    "/organizations/{organization_id}/teams/{team_id}",
    response_model=TeamResponse,
    summary="Update a team",
    description="Update team details. Requires team admin or org admin permission.",
)
async def update_team(
    organization_id: UUID,
    team_id: UUID,
    data: TeamUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TeamResponse:
    """Update a team.

    Args:
        organization_id: Organization UUID.
        team_id: Team UUID.
        data: Update data.
        current_user: Authenticated user.
        service: Team service.

    Returns:
        Updated team.

    Raises:
        HTTPException 403: If user lacks permission.
        HTTPException 404: If team not found.
    """
    # Check permission (team admin or org admin)
    has_team_perm = await service.check_team_permission(team_id, current_user, TeamRole.ADMIN)
    has_org_perm = await service.check_org_team_permission(organization_id, current_user)

    if not has_team_perm and not has_org_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this team",
        )

    try:
        team = await service.update_team(team_id, data)
        return TeamResponse.model_validate(team)
    except TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )


@router.delete(
    "/organizations/{organization_id}/teams/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a team",
    description="Soft delete a team. Requires org admin permission.",
)
async def delete_team(
    organization_id: UUID,
    team_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> None:
    """Delete a team.

    Args:
        organization_id: Organization UUID.
        team_id: Team UUID.
        current_user: Authenticated user.
        service: Team service.

    Raises:
        HTTPException 403: If user lacks permission.
        HTTPException 404: If team not found.
    """
    # Check org admin permission
    has_permission = await service.check_org_team_permission(organization_id, current_user)
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete teams in this organization",
        )

    try:
        await service.delete_team(team_id)
    except TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )


# Team Member endpoints


@router.get(
    "/organizations/{organization_id}/teams/{team_id}/members",
    response_model=TeamMemberListResponse,
    summary="List team members",
    description="List all members of a team.",
)
async def list_team_members(
    _organization_id: UUID,
    team_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    include_inactive: bool = Query(False, description="Include inactive members"),
) -> TeamMemberListResponse:
    """List team members.

    Args:
        organization_id: Organization UUID.
        team_id: Team UUID.
        current_user: Authenticated user.
        service: Team service.
        page: Page number.
        page_size: Items per page.
        include_inactive: Include inactive members.

    Returns:
        Paginated member list.
    """
    members, total = await service.list_team_members(
        team_id,
        page=page,
        page_size=page_size,
        include_inactive=include_inactive,
    )

    items = []
    for m in members:
        item = TeamMemberResponse(
            id=m.id,
            team_id=m.team_id,
            user_id=m.user_id,
            role=m.role,
            joined_at=m.joined_at,
            is_active=m.is_active,
            added_by_id=m.added_by_id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            user_email=m.user.email if m.user else None,
            user_full_name=m.user.display_name if m.user else None,
        )
        items.append(item)

    return TeamMemberListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.post(
    "/organizations/{organization_id}/teams/{team_id}/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add team member",
    description="Add a member to a team. Requires team lead or admin permission.",
)
async def add_team_member(
    organization_id: UUID,
    team_id: UUID,
    data: TeamMemberAdd,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TeamMemberResponse:
    """Add a member to a team.

    Args:
        organization_id: Organization UUID.
        team_id: Team UUID.
        data: Member add data.
        current_user: Authenticated user.
        service: Team service.

    Returns:
        Created team member.

    Raises:
        HTTPException 403: If user lacks permission.
        HTTPException 404: If team not found.
        HTTPException 409: If user already a member.
    """
    # Check permission (team lead/admin or org admin)
    has_team_perm = await service.check_team_permission(team_id, current_user, TeamRole.LEAD)
    has_org_perm = await service.check_org_team_permission(organization_id, current_user)

    if not has_team_perm and not has_org_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add members to this team",
        )

    try:
        member = await service.add_team_member(team_id, data, current_user)
        return TeamMemberResponse(
            id=member.id,
            team_id=member.team_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            is_active=member.is_active,
            added_by_id=member.added_by_id,
            created_at=member.created_at,
            updated_at=member.updated_at,
        )
    except TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )
    except TeamMemberExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/organizations/{organization_id}/teams/{team_id}/members/bulk",
    response_model=list[TeamMemberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk add team members",
    description="Add multiple members to a team at once.",
)
async def bulk_add_team_members(
    organization_id: UUID,
    team_id: UUID,
    data: TeamMemberBulkAdd,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> list[TeamMemberResponse]:
    """Bulk add members to a team.

    Args:
        organization_id: Organization UUID.
        team_id: Team UUID.
        data: Bulk add data with member list.
        current_user: Authenticated user.
        service: Team service.

    Returns:
        List of created team members.
    """
    # Check permission
    has_team_perm = await service.check_team_permission(team_id, current_user, TeamRole.LEAD)
    has_org_perm = await service.check_org_team_permission(organization_id, current_user)

    if not has_team_perm and not has_org_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add members to this team",
        )

    results = []
    for member_data in data.members:
        try:
            member = await service.add_team_member(team_id, member_data, current_user)
            results.append(
                TeamMemberResponse(
                    id=member.id,
                    team_id=member.team_id,
                    user_id=member.user_id,
                    role=member.role,
                    joined_at=member.joined_at,
                    is_active=member.is_active,
                    added_by_id=member.added_by_id,
                    created_at=member.created_at,
                    updated_at=member.updated_at,
                )
            )
        except (TeamMemberExistsError, TeamNotFoundError):
            # Skip already existing members
            continue

    return results


@router.patch(
    "/organizations/{organization_id}/teams/{team_id}/members/{user_id}",
    response_model=TeamMemberResponse,
    summary="Update team member",
    description="Update a team member's role. Requires team admin permission.",
)
async def update_team_member(
    organization_id: UUID,
    team_id: UUID,
    user_id: UUID,
    data: TeamMemberUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> TeamMemberResponse:
    """Update a team member.

    Args:
        organization_id: Organization UUID.
        team_id: Team UUID.
        user_id: User UUID to update.
        data: Update data.
        current_user: Authenticated user.
        service: Team service.

    Returns:
        Updated team member.

    Raises:
        HTTPException 403: If user lacks permission.
        HTTPException 404: If member not found.
    """
    # Check permission (team admin or org admin)
    has_team_perm = await service.check_team_permission(team_id, current_user, TeamRole.ADMIN)
    has_org_perm = await service.check_org_team_permission(organization_id, current_user)

    if not has_team_perm and not has_org_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update team members",
        )

    try:
        member = await service.update_team_member(team_id, user_id, data)
        return TeamMemberResponse(
            id=member.id,
            team_id=member.team_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            is_active=member.is_active,
            added_by_id=member.added_by_id,
            created_at=member.created_at,
            updated_at=member.updated_at,
        )
    except TeamMemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found",
        )


@router.delete(
    "/organizations/{organization_id}/teams/{team_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove team member",
    description="Remove a member from a team. Requires team lead or admin permission.",
)
async def remove_team_member(
    organization_id: UUID,
    team_id: UUID,
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> None:
    """Remove a member from a team.

    Args:
        organization_id: Organization UUID.
        team_id: Team UUID.
        user_id: User UUID to remove.
        current_user: Authenticated user.
        service: Team service.

    Raises:
        HTTPException 403: If user lacks permission.
        HTTPException 404: If member not found.
    """
    # Check permission (team lead/admin or org admin) - or self-removal
    is_self = user_id == current_user.id
    has_team_perm = await service.check_team_permission(team_id, current_user, TeamRole.LEAD)
    has_org_perm = await service.check_org_team_permission(organization_id, current_user)

    if not is_self and not has_team_perm and not has_org_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove members from this team",
        )

    try:
        await service.remove_team_member(team_id, user_id)
    except TeamMemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found",
        )


# User's teams endpoints


@router.get(
    "/users/me/teams",
    response_model=UserTeamListResponse,
    summary="Get current user's teams",
    description="Get all teams the current user belongs to.",
)
async def get_my_teams(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> UserTeamListResponse:
    """Get current user's teams.

    Args:
        current_user: Authenticated user.
        service: Team service.

    Returns:
        List of user's team memberships.
    """
    teams = await service.get_user_teams(current_user.id)

    return UserTeamListResponse(
        items=[UserTeamResponse.model_validate(t) for t in teams],
        total=len(teams),
    )


@router.delete(
    "/users/me/teams/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Leave a team",
    description="Remove yourself from a team.",
)
async def leave_team(
    team_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> None:
    """Leave a team.

    Args:
        team_id: Team UUID.
        current_user: Authenticated user.
        service: Team service.

    Raises:
        HTTPException 404: If not a member.
    """
    try:
        await service.leave_team(team_id, current_user.id)
    except TeamMemberNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this team",
        )


# Project-Team assignment endpoints


@router.get(
    "/projects/{project_id}/teams",
    response_model=list[ProjectTeamResponse],
    summary="List project teams",
    description="List all teams assigned to a project.",
)
async def list_project_teams(
    project_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
) -> list[ProjectTeamResponse]:
    """List teams assigned to a project.

    Args:
        project_id: Project UUID.
        current_user: Authenticated user.
        service: Team service.

    Returns:
        List of project-team assignments.
    """
    assignments = await service.list_project_teams(project_id)

    return [
        ProjectTeamResponse(
            id=a.id,
            project_id=a.project_id,
            team_id=a.team_id,
            permission_level=a.permission_level,
            assigned_by_id=a.assigned_by_id,
            assigned_at=a.assigned_at,
            created_at=a.created_at,
            updated_at=a.updated_at,
            team_name=a.team.name if a.team else None,
        )
        for a in assignments
    ]


@router.post(
    "/projects/{project_id}/teams",
    response_model=ProjectTeamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign team to project",
    description="Assign a team to a project with specific permissions.",
)
async def assign_team_to_project(
    project_id: UUID,
    data: ProjectTeamAssign,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectTeamResponse:
    """Assign a team to a project.

    Args:
        project_id: Project UUID.
        data: Assignment data.
        current_user: Authenticated user.
        service: Team service.
        db: Database session.

    Returns:
        Created assignment.
    """
    await check_project_permission(db, project_id, current_user)
    assignment = await service.assign_team_to_project(data, project_id, current_user)

    return ProjectTeamResponse(
        id=assignment.id,
        project_id=assignment.project_id,
        team_id=assignment.team_id,
        permission_level=assignment.permission_level,
        assigned_by_id=assignment.assigned_by_id,
        assigned_at=assignment.assigned_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


@router.patch(
    "/projects/{project_id}/teams/{team_id}",
    response_model=ProjectTeamResponse,
    summary="Update team assignment",
    description="Update a team's permission level on a project.",
)
async def update_project_team(
    project_id: UUID,
    team_id: UUID,
    data: ProjectTeamUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectTeamResponse:
    """Update a project-team assignment.

    Args:
        project_id: Project UUID.
        team_id: Team UUID.
        data: Update data.
        current_user: Authenticated user.
        service: Team service.
        db: Database session.

    Returns:
        Updated assignment.

    Raises:
        HTTPException 404: If assignment not found.
    """
    await check_project_permission(db, project_id, current_user)
    try:
        assignment = await service.update_project_team(project_id, team_id, data)
        return ProjectTeamResponse(
            id=assignment.id,
            project_id=assignment.project_id,
            team_id=assignment.team_id,
            permission_level=assignment.permission_level,
            assigned_by_id=assignment.assigned_by_id,
            assigned_at=assignment.assigned_at,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
        )
    except TeamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team is not assigned to this project",
        )


@router.delete(
    "/projects/{project_id}/teams/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove team from project",
    description="Remove a team's access to a project.",
)
async def remove_team_from_project(
    project_id: UUID,
    team_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[TeamService, Depends(get_team_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a team from a project.

    Args:
        project_id: Project UUID.
        team_id: Team UUID.
        current_user: Authenticated user.
        service: Team service.
        db: Database session.
    """
    await check_project_permission(db, project_id, current_user)
    await service.remove_team_from_project(project_id, team_id)
