"""
Projects API endpoints.

CRUD operations for projects and managing designs within projects.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.design import Design


router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class ProjectCreate(BaseModel):
    """Request schema for creating a project."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class ProjectUpdate(BaseModel):
    """Request schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class ProjectResponse(BaseModel):
    """Response schema for a project."""
    id: UUID
    name: str
    description: Optional[str]
    design_count: int
    thumbnail_url: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """Response schema for project with designs."""
    designs: list[dict]


class ProjectListResponse(BaseModel):
    """Response schema for listing projects."""
    projects: list[ProjectResponse]
    total: int
    page: int
    per_page: int


class MoveDesignRequest(BaseModel):
    """Request schema for moving a design to a project."""
    target_project_id: UUID


class DesignBriefResponse(BaseModel):
    """Brief design info for project lists."""
    id: UUID
    name: str
    thumbnail_url: Optional[str]
    status: str
    source_type: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Create a new project.
    
    Projects organize designs into logical groups.
    """
    project = Project(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        design_count=0,
        thumbnail_url=None,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    """
    List all projects for the current user.
    
    Returns paginated list with design counts.
    """
    # Build base query
    query = (
        select(Project)
        .where(Project.user_id == current_user.id)
        .where(Project.deleted_at.is_(None))
    )
    
    # Apply search filter
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Project.updated_at.desc()).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    
    # Get design counts for each project
    project_responses = []
    for project in projects:
        # Count non-deleted designs
        design_count_query = (
            select(func.count())
            .where(Design.project_id == project.id)
            .where(Design.deleted_at.is_(None))
        )
        design_count_result = await db.execute(design_count_query)
        design_count = design_count_result.scalar() or 0
        
        # Get thumbnail from first design (if any)
        thumbnail_url = None
        first_design_query = (
            select(Design)
            .where(Design.project_id == project.id)
            .where(Design.deleted_at.is_(None))
            .order_by(Design.updated_at.desc())
            .limit(1)
        )
        first_design_result = await db.execute(first_design_query)
        first_design = first_design_result.scalar_one_or_none()
        if first_design and first_design.extra_data:
            thumbnail_url = first_design.extra_data.get("thumbnail_url")
        
        project_responses.append(ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            design_count=design_count,
            thumbnail_url=thumbnail_url,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
        ))
    
    return ProjectListResponse(
        projects=project_responses,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/projects/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectDetailResponse:
    """
    Get a project with its designs.
    
    Returns project details and paginated list of designs.
    """
    # Get project
    query = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Get designs in project
    offset = (page - 1) * per_page
    designs_query = (
        select(Design)
        .where(Design.project_id == project_id)
        .where(Design.deleted_at.is_(None))
        .order_by(Design.updated_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    designs_result = await db.execute(designs_query)
    designs = designs_result.scalars().all()
    
    # Get total design count
    design_count_query = (
        select(func.count())
        .where(Design.project_id == project_id)
        .where(Design.deleted_at.is_(None))
    )
    design_count_result = await db.execute(design_count_query)
    design_count = design_count_result.scalar() or 0
    
    # Format designs
    designs_data = []
    for design in designs:
        thumbnail_url = None
        if design.extra_data:
            thumbnail_url = design.extra_data.get("thumbnail_url")
        
        designs_data.append({
            "id": str(design.id),
            "name": design.name,
            "thumbnail_url": thumbnail_url,
            "status": design.status,
            "source_type": design.source_type,
            "created_at": design.created_at.isoformat(),
            "updated_at": design.updated_at.isoformat(),
        })
    
    # Get project thumbnail
    thumbnail_url = None
    if designs_data:
        thumbnail_url = designs_data[0].get("thumbnail_url")
    
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        design_count=design_count,
        thumbnail_url=thumbnail_url,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        designs=designs_data,
    )


class ProjectDesignsResponse(BaseModel):
    """Response for paginated project designs list."""
    items: list[dict]
    total: int
    page: int
    per_page: int


@router.get("/projects/{project_id}/designs", response_model=ProjectDesignsResponse)
async def get_project_designs(
    project_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by design status"),
    search: str | None = Query(None, description="Search by design name"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectDesignsResponse:
    """
    Get designs belonging to a project.
    
    Returns a paginated list of designs with optional filtering.
    """
    # Check project exists and user has access
    project_query = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.deleted_at.is_(None))
    )
    result = await db.execute(project_query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Build base query
    designs_query = (
        select(Design)
        .where(Design.project_id == project_id)
        .where(Design.deleted_at.is_(None))
    )
    
    # Apply filters
    if status:
        designs_query = designs_query.where(Design.status == status)
    
    if search:
        designs_query = designs_query.where(
            Design.name.ilike(f"%{search}%")
        )
    
    # Get total count before pagination
    count_query = (
        select(func.count())
        .select_from(Design)
        .where(Design.project_id == project_id)
        .where(Design.deleted_at.is_(None))
    )
    if status:
        count_query = count_query.where(Design.status == status)
    if search:
        count_query = count_query.where(Design.name.ilike(f"%{search}%"))
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Apply pagination and ordering
    offset = (page - 1) * per_page
    designs_query = (
        designs_query
        .order_by(Design.updated_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    
    designs_result = await db.execute(designs_query)
    designs = designs_result.scalars().all()
    
    # Format response
    items = []
    for design in designs:
        thumbnail_url = None
        if design.extra_data:
            thumbnail_url = design.extra_data.get("thumbnail_url")
        
        items.append({
            "id": str(design.id),
            "name": design.name,
            "description": design.description,
            "thumbnail_url": thumbnail_url,
            "status": design.status,
            "source_type": design.source_type,
            "created_at": design.created_at.isoformat(),
            "updated_at": design.updated_at.isoformat(),
        })
    
    return ProjectDesignsResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Update a project.
    
    Only the project owner can update it.
    """
    # Get project
    query = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Update fields
    if request.name is not None:
        project.name = request.name
    if request.description is not None:
        project.description = request.description
    
    await db.commit()
    await db.refresh(project)
    
    # Get design count
    design_count_query = (
        select(func.count())
        .where(Design.project_id == project.id)
        .where(Design.deleted_at.is_(None))
    )
    design_count_result = await db.execute(design_count_query)
    design_count = design_count_result.scalar() or 0
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        design_count=design_count,
        thumbnail_url=None,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    move_designs_to: Optional[UUID] = Query(None, description="Project to move designs to"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a project.
    
    Designs in the project will be moved to another project or the default project.
    """
    # Get project
    query = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Handle designs in the project
    if move_designs_to:
        # Verify target project exists and is owned by user
        target_query = (
            select(Project)
            .where(Project.id == move_designs_to)
            .where(Project.user_id == current_user.id)
            .where(Project.deleted_at.is_(None))
        )
        target_result = await db.execute(target_query)
        target_project = target_result.scalar_one_or_none()
        
        if not target_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target project not found",
            )
        
        # Move designs
        designs_query = (
            select(Design)
            .where(Design.project_id == project_id)
            .where(Design.deleted_at.is_(None))
        )
        designs_result = await db.execute(designs_query)
        designs = designs_result.scalars().all()
        
        for design in designs:
            design.project_id = move_designs_to
    else:
        # Get or create default project
        default_query = (
            select(Project)
            .where(Project.user_id == current_user.id)
            .where(Project.name == "My Designs")
            .where(Project.deleted_at.is_(None))
        )
        default_result = await db.execute(default_query)
        default_project = default_result.scalar_one_or_none()
        
        if not default_project:
            default_project = Project(
                user_id=current_user.id,
                name="My Designs",
                description="Default project for your designs",
            )
            db.add(default_project)
            await db.flush()
        
        # Move designs to default project
        designs_query = (
            select(Design)
            .where(Design.project_id == project_id)
            .where(Design.deleted_at.is_(None))
        )
        designs_result = await db.execute(designs_query)
        designs = designs_result.scalars().all()
        
        for design in designs:
            design.project_id = default_project.id
    
    # Soft delete the project
    from datetime import datetime, timezone
    project.deleted_at = datetime.now(timezone.utc)
    
    await db.commit()


@router.post("/projects/{project_id}/designs/{design_id}", response_model=dict)
async def move_design_to_project(
    project_id: UUID,
    design_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Move a design to a project.
    
    The user must own both the design and the target project.
    """
    # Get target project
    project_query = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.user_id == current_user.id)
        .where(Project.deleted_at.is_(None))
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Get design
    design_query = (
        select(Design)
        .where(Design.id == design_id)
        .where(Design.deleted_at.is_(None))
    )
    design_result = await db.execute(design_query)
    design = design_result.scalar_one_or_none()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )
    
    # Verify design ownership through project
    source_project_query = (
        select(Project)
        .where(Project.id == design.project_id)
    )
    source_project_result = await db.execute(source_project_query)
    source_project = source_project_result.scalar_one_or_none()
    
    if not source_project or source_project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    # Move design
    old_project_id = design.project_id
    design.project_id = project_id
    
    await db.commit()
    
    return {
        "message": "Design moved successfully",
        "design_id": str(design_id),
        "from_project_id": str(old_project_id),
        "to_project_id": str(project_id),
    }


@router.get("/projects/default", response_model=ProjectResponse)
async def get_or_create_default_project(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Get or create the user's default project.
    
    The default project is named "My Designs" and is created automatically
    for new users.
    """
    # Try to find existing default project
    query = (
        select(Project)
        .where(Project.user_id == current_user.id)
        .where(Project.name == "My Designs")
        .where(Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        # Create default project
        project = Project(
            user_id=current_user.id,
            name="My Designs",
            description="Default project for your designs",
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
    
    # Get design count
    design_count_query = (
        select(func.count())
        .where(Design.project_id == project.id)
        .where(Design.deleted_at.is_(None))
    )
    design_count_result = await db.execute(design_count_query)
    design_count = design_count_result.scalar() or 0
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        design_count=design_count,
        thumbnail_url=None,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
    )


# ============================================================================
# Example Projects
# ============================================================================


class ExampleProjectResponse(BaseModel):
    """Response schema for an example project."""
    id: UUID
    name: str
    description: Optional[str]
    design_count: int
    tags: list[str]
    thumbnail_url: Optional[str]


@router.get("/projects/examples", response_model=list[ExampleProjectResponse])
async def list_example_projects(
    db: AsyncSession = Depends(get_db),
) -> list[ExampleProjectResponse]:
    """
    List all example projects available for users to explore or copy.
    """
    # Query projects marked as examples
    query = (
        select(Project)
        .where(Project.deleted_at.is_(None))
        .where(Project.is_public.is_(True))
    )
    result = await db.execute(query)
    projects = result.scalars().all()
    
    examples = []
    for project in projects:
        # Check if marked as example
        if not project.extra_data.get("is_example"):
            continue
        
        # Get design count
        design_count_query = (
            select(func.count())
            .where(Design.project_id == project.id)
            .where(Design.deleted_at.is_(None))
        )
        design_count_result = await db.execute(design_count_query)
        design_count = design_count_result.scalar() or 0
        
        examples.append(ExampleProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            design_count=design_count,
            tags=project.extra_data.get("tags", []),
            thumbnail_url=None,
        ))
    
    return examples


@router.post("/projects/examples/{project_id}/copy", response_model=ProjectResponse)
async def copy_example_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Copy an example project to the user's library.
    
    Creates a copy of the example project and all its designs
    in the user's account.
    """
    from datetime import datetime
    
    # Get the example project
    query = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    example = result.scalar_one_or_none()
    
    if not example:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Example project not found",
        )
    
    # Verify it's an example project
    if not example.extra_data.get("is_example"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not an example project",
        )
    
    # Create copy
    new_project = Project(
        user_id=current_user.id,
        name=f"{example.name}",
        description=example.description,
        is_public=False,
        extra_data={
            "copied_from": str(project_id),
            "copied_at": datetime.utcnow().isoformat(),
            "tags": example.extra_data.get("tags", []),
        },
    )
    db.add(new_project)
    await db.flush()
    
    # Copy designs
    designs_query = (
        select(Design)
        .where(Design.project_id == project_id)
        .where(Design.deleted_at.is_(None))
    )
    designs_result = await db.execute(designs_query)
    
    for design in designs_result.scalars():
        new_design = Design(
            project_id=new_project.id,
            name=design.name,
            description=design.description,
            prompt=design.prompt,
            parameters=design.parameters,
            status="draft",
            is_public=False,
        )
        db.add(new_design)
    
    await db.commit()
    await db.refresh(new_project)
    
    # Get design count
    design_count_query = (
        select(func.count())
        .where(Design.project_id == new_project.id)
        .where(Design.deleted_at.is_(None))
    )
    design_count_result = await db.execute(design_count_query)
    design_count = design_count_result.scalar() or 0
    
    return ProjectResponse(
        id=new_project.id,
        name=new_project.name,
        description=new_project.description,
        design_count=design_count,
        thumbnail_url=None,
        created_at=new_project.created_at.isoformat(),
        updated_at=new_project.updated_at.isoformat(),
    )
