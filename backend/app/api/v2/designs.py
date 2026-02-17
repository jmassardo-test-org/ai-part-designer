"""
CAD v2 designs endpoints.

Handles saving generated enclosures to projects.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.design import Design
from app.models.job import Job
from app.models.project import Project

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class SaveDesignV2Request(BaseModel):
    """Request to save a v2 generated design to a project."""

    job_id: str = Field(
        ...,
        description="ID of the completed v2 generation job",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name for the saved design",
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional description",
    )
    project_id: UUID | None = Field(
        default=None,
        description="Project to save to. If not provided, uses default project.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )


class SaveDesignV2Response(BaseModel):
    """Response after saving a design."""

    id: UUID = Field(description="Design ID")
    name: str = Field(description="Design name")
    description: str | None = Field(description="Design description")
    project_id: UUID = Field(description="Project ID")
    project_name: str = Field(description="Project name")
    source_type: str = Field(description="Source type (v2_generated)")
    status: str = Field(description="Design status")
    job_id: str = Field(description="Original generation job ID")
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization",
    )
    enclosure_spec: dict[str, Any] | None = Field(
        default=None,
        description="The EnclosureSpec used to generate this design",
    )
    downloads: dict[str, str] = Field(
        default_factory=dict,
        description="Download URLs for the design files",
    )
    created_at: str = Field(description="Creation timestamp")

    class Config:
        from_attributes = True


class ListDesignsV2Response(BaseModel):
    """Response for listing v2 designs."""

    designs: list[SaveDesignV2Response]
    total: int
    page: int
    per_page: int


# =============================================================================
# Helper Functions
# =============================================================================


async def get_or_create_default_project(user: User, db: AsyncSession) -> Project:
    """Get or create the user's default project."""
    query = (
        select(Project)
        .where(Project.user_id == user.id)
        .where(Project.name == "My Designs")
        .where(Project.deleted_at.is_(None))
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if not project:
        project = Project(
            user_id=user.id,
            name="My Designs",
            description="Default project for your designs",
        )
        db.add(project)
        await db.flush()

    return project


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/save", response_model=SaveDesignV2Response, status_code=status.HTTP_201_CREATED)
async def save_design_v2(
    request: SaveDesignV2Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SaveDesignV2Response:
    """
    Save a v2 generated enclosure to a project.

    This creates a Design record linked to the generation job,
    allowing the user to access the generated files later.

    Args:
        request: Save design request with job_id and metadata
        current_user: Authenticated user
        db: Database session

    Returns:
        SaveDesignV2Response with the created design details

    Raises:
        HTTPException 404: If job or project not found
        HTTPException 400: If job is not completed
    """
    # Find the job
    try:
        job_uuid = UUID(request.job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job_id format",
        )

    job_query = select(Job).where(Job.id == job_uuid).where(Job.user_id == current_user.id)
    job_query_result = await db.execute(job_query)
    job = job_query_result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed (status: {job.status})",
        )

    # Get or create project
    if request.project_id:
        project_query = (
            select(Project)
            .where(Project.id == request.project_id)
            .where(Project.user_id == current_user.id)
            .where(Project.deleted_at.is_(None))
        )
        project_query_result = await db.execute(project_query)
        project = project_query_result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
    else:
        project = await get_or_create_default_project(current_user, db)

    # Extract job data
    job_result = job.result or {}
    job_input = job.input_params or {}

    # Build extra_data from job
    extra_data = {
        "job_id": str(job.id),
        "original_description": job_input.get("description", ""),
        "enclosure_spec": job_result.get("generated_schema") or job_input.get("enclosure_schema"),
        "parts": job_result.get("parts", []),
        "downloads": job_result.get("downloads", {}),
        "thumbnail_url": job_result.get("thumbnail_url"),
        "v2_metadata": {
            "export_format": job_input.get("export_format", "step"),
            "warnings": job_result.get("warnings", []),
        },
    }

    # Create the design
    design = Design(
        project_id=project.id,
        user_id=current_user.id,  # Required field
        name=request.name,
        description=request.description or job_input.get("description", ""),
        source_type="v2_generated",
        status="ready",
        extra_data=extra_data,
        tags=request.tags,
    )

    db.add(design)

    # Link job to design
    job.design_id = design.id

    await db.commit()
    await db.refresh(design)

    logger.info(f"V2 design saved: {design.id} from job {job.id} by user {current_user.id}")

    return SaveDesignV2Response(
        id=design.id,
        name=design.name,
        description=design.description,
        project_id=project.id,
        project_name=project.name,
        source_type=design.source_type,
        status=design.status,
        job_id=str(job.id),
        tags=design.tags or [],
        enclosure_spec=extra_data.get("enclosure_spec"),
        downloads=extra_data.get("downloads", {}),
        created_at=design.created_at.isoformat(),
    )


@router.get("/{design_id}", response_model=SaveDesignV2Response)
async def get_design_v2(
    design_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SaveDesignV2Response:
    """
    Get a v2 design by ID.

    Args:
        design_id: The design ID
        current_user: Authenticated user
        db: Database session

    Returns:
        SaveDesignV2Response with design details

    Raises:
        HTTPException 404: If design not found
    """
    query = (
        select(Design)
        .join(Project, Design.project_id == Project.id)
        .where(Design.id == design_id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
        .where(Design.source_type == "v2_generated")
    )
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    # Get project name
    project_query = select(Project).where(Project.id == design.project_id)
    result = await db.execute(project_query)
    project = result.scalar_one()

    extra_data = design.extra_data or {}

    return SaveDesignV2Response(
        id=design.id,
        name=design.name,
        description=design.description,
        project_id=design.project_id,
        project_name=project.name,
        source_type=design.source_type,
        status=design.status,
        job_id=extra_data.get("job_id", ""),
        enclosure_spec=extra_data.get("enclosure_spec"),
        downloads=extra_data.get("downloads", {}),
        created_at=design.created_at.isoformat(),
    )


@router.get("/", response_model=ListDesignsV2Response)
async def list_designs_v2(
    project_id: UUID | None = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListDesignsV2Response:
    """
    List v2 designs for the current user.

    Args:
        project_id: Optional filter by project
        page: Page number (1-based)
        per_page: Items per page
        current_user: Authenticated user
        db: Database session

    Returns:
        ListDesignsV2Response with paginated designs
    """
    # Build base query
    base_query = (
        select(Design)
        .join(Project, Design.project_id == Project.id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
        .where(Design.source_type == "v2_generated")
    )

    if project_id:
        base_query = base_query.where(Design.project_id == project_id)

    # Get total count
    from sqlalchemy import func

    count_query = select(func.count()).select_from(base_query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * per_page
    query = base_query.order_by(Design.created_at.desc()).offset(offset).limit(per_page)
    result = await db.execute(query)
    designs = result.scalars().all()

    # Get project names
    project_ids = {d.project_id for d in designs}  # type: ignore[attr-defined]
    if project_ids:
        projects_query = select(Project).where(Project.id.in_(project_ids))
        result = await db.execute(projects_query)
        projects = {p.id: p for p in result.scalars().all()}  # type: ignore[attr-defined]
    else:
        projects = {}

    # Build response
    design_responses = []
    for design in designs:
        project = projects.get(design.project_id)  # type: ignore[attr-defined]
        extra_data = design.extra_data or {}  # type: ignore[attr-defined]

        design_responses.append(
            SaveDesignV2Response(
                id=design.id,  # type: ignore[attr-defined]
                name=design.name,  # type: ignore[attr-defined]
                description=design.description,  # type: ignore[attr-defined]
                project_id=design.project_id,  # type: ignore[attr-defined]
                project_name=project.name if project else "Unknown",  # type: ignore[attr-defined]
                source_type=design.source_type,  # type: ignore[attr-defined]
                status=design.status,  # type: ignore[attr-defined]
                job_id=extra_data.get("job_id", ""),
                enclosure_spec=extra_data.get("enclosure_spec"),
                downloads=extra_data.get("downloads", {}),
                created_at=design.created_at.isoformat(),  # type: ignore[attr-defined]
            )
        )

    return ListDesignsV2Response(
        designs=design_responses,
        total=total,
        page=page,
        per_page=per_page,
    )
