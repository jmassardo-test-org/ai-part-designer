"""
Designs API endpoints.

CRUD operations for designs.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limiter import design_operation_limit, expensive_operation_limit
from app.models.conversation import Conversation
from app.models.design import Design
from app.models.job import Job
from app.models.notification import NotificationType
from app.models.project import Project
from app.services.design_service import DesignService
from app.services.notification_service import NotificationService

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================


class DesignCreate(BaseModel):
    """Request schema for creating a design."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    project_id: UUID | None = Field(
        None, description="Project to save to. If not provided, uses default project."
    )


class DesignFromJobCreate(BaseModel):
    """Request schema for creating a design from a job."""

    job_id: UUID = Field(..., description="ID of the completed generation job")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    project_id: UUID | None = Field(
        None, description="Project to save to. If not provided, uses default project."
    )


class DesignFromConversationCreate(BaseModel):
    """Request schema for creating a design from a conversation result."""

    conversation_id: UUID = Field(..., description="ID of the completed conversation")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    project_id: UUID | None = Field(
        None, description="Project to save to. If not provided, uses default project."
    )


class DesignResponse(BaseModel):
    """Response schema for a design."""

    id: UUID
    name: str
    description: str | None
    project_id: UUID
    project_name: str
    source_type: str
    status: str
    thumbnail_url: str | None
    extra_data: dict[str, Any] | None = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DesignListResponse(BaseModel):
    """Response schema for listing designs."""

    designs: list[DesignResponse]
    total: int
    page: int
    per_page: int


# ============================================================================
# Helper Functions
# ============================================================================


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


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/designs", response_model=DesignResponse, status_code=status.HTTP_201_CREATED)
async def create_design(
    request: DesignCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """
    Create a new empty design.
    """
    # Get or create project
    if request.project_id:
        project_query = (
            select(Project)
            .where(Project.id == request.project_id)
            .where(Project.user_id == current_user.id)
            .where(Project.deleted_at.is_(None))
        )
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
    else:
        project = await get_or_create_default_project(current_user, db)

    design = Design(
        project_id=project.id,
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        source_type="manual",
        status="draft",
        extra_data={},
    )

    db.add(design)
    await db.commit()
    await db.refresh(design)

    logger.info(f"Design created: {design.id} by user {current_user.id}")

    return DesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        project_id=project.id,
        project_name=project.name,
        source_type=design.source_type,
        status=design.status,
        thumbnail_url=design.extra_data.get("thumbnail_url") if design.extra_data else None,
        created_at=design.created_at.isoformat(),
        updated_at=design.updated_at.isoformat(),
    )


@router.post(
    "/designs/from-job", response_model=DesignResponse, status_code=status.HTTP_201_CREATED
)
async def create_design_from_job(
    request: DesignFromJobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """
    Create a design from a completed generation job.

    This saves an AI-generated design to the user's library.
    """
    # Find the job
    job_query = select(Job).where(Job.id == request.job_id).where(Job.user_id == current_user.id)
    result = await db.execute(job_query)
    job = result.scalar_one_or_none()

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
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
    else:
        project = await get_or_create_default_project(current_user, db)

    # Extract job result data
    job_result = job.result or {}
    job_input = job.input_params or {}

    # Build extra_data from job result
    extra_data = {
        "job_id": str(job.id),
        "original_description": job_input.get("description", ""),
        "shape": job_result.get("shape"),
        "dimensions": job_result.get("dimensions", {}),
        "confidence": job_result.get("confidence"),
        "downloads": job_result.get("downloads", {}),
        "thumbnail_url": job_result.get("thumbnail_url"),
        "parameters": job_result.get("parameters", {}),
    }

    # Create the design
    design = Design(
        project_id=project.id,
        user_id=current_user.id,
        name=request.name,
        description=request.description or job_input.get("description", ""),
        source_type="ai_generated",
        status="ready",
        extra_data=extra_data,
    )

    db.add(design)

    # Link job to design
    job.design_id = design.id

    await db.commit()
    await db.refresh(design)

    logger.info(f"Design created from job: {design.id} from job {job.id} by user {current_user.id}")

    # Create notification for design saved
    try:
        notification_service = NotificationService(db)
        await notification_service.create_notification(
            user_id=current_user.id,
            notification_type=NotificationType.JOB_COMPLETED,
            title="Design Saved",
            message=f"Your design '{request.name}' has been saved to {project.name}",
            action_url=f"/projects/{project.id}/designs/{design.id}",
            entity_type="design",
            entity_id=design.id,
        )
    except Exception as e:
        # Don't fail the request if notification fails
        logger.warning(f"Failed to create notification for design save: {e}")

    return DesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        project_id=project.id,
        project_name=project.name,
        source_type=design.source_type,
        status=design.status,
        thumbnail_url=extra_data.get("thumbnail_url"),
        created_at=design.created_at.isoformat(),
        updated_at=design.updated_at.isoformat(),
    )


@router.post(
    "/designs/from-conversation", response_model=DesignResponse, status_code=status.HTTP_201_CREATED
)
async def create_design_from_conversation(
    request: DesignFromConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """
    Create a design from a completed conversation.

    This saves an AI-generated design from chat to the user's library.
    """
    # Find the conversation
    conversation_query = (
        select(Conversation)
        .where(Conversation.id == request.conversation_id)
        .where(Conversation.user_id == current_user.id)
    )
    result = await db.execute(conversation_query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    if not conversation.result_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation has no result data - generation may not be complete",
        )

    # Get or create project
    if request.project_id:
        project_query = (
            select(Project)
            .where(Project.id == request.project_id)
            .where(Project.user_id == current_user.id)
            .where(Project.deleted_at.is_(None))
        )
        result = await db.execute(project_query)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
    else:
        project = await get_or_create_default_project(current_user, db)

    # Extract result data from conversation
    result_data = conversation.result_data or {}
    intent_data = conversation.intent_data or {}

    # Build extra_data from conversation result
    extra_data = {
        "conversation_id": str(conversation.id),
        "job_id": conversation.result_job_id,
        "original_description": intent_data.get("description", ""),
        "shape": result_data.get("shape"),
        "dimensions": result_data.get("dimensions", {}),
        "confidence": result_data.get("confidence"),
        "downloads": result_data.get("downloads", {}),
        "thumbnail_url": result_data.get("thumbnail_url"),
        "parameters": result_data.get("parameters", {}),
        "enclosure_schema": result_data.get("enclosure_schema"),
    }

    # Create the design
    design = Design(
        project_id=project.id,
        user_id=current_user.id,
        name=request.name,
        description=request.description or intent_data.get("description", ""),
        source_type="ai_generated",
        status="ready",
        extra_data=extra_data,
    )

    db.add(design)
    await db.commit()
    await db.refresh(design)

    logger.info(
        f"Design created from conversation: {design.id} from conversation {conversation.id} by user {current_user.id}"
    )

    # Create notification for design saved
    try:
        notification_service = NotificationService(db)
        await notification_service.create_notification(
            user_id=current_user.id,
            notification_type=NotificationType.JOB_COMPLETED,
            title="Design Saved",
            message=f"Your design '{request.name}' has been saved to {project.name}",
            action_url=f"/projects/{project.id}/designs/{design.id}",
            entity_type="design",
            entity_id=design.id,
        )
    except Exception as e:
        # Don't fail the request if notification fails
        logger.warning(f"Failed to create notification for design save: {e}")

    return DesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        project_id=project.id,
        project_name=project.name,
        source_type=design.source_type,
        status=design.status,
        thumbnail_url=extra_data.get("thumbnail_url"),
        created_at=design.created_at.isoformat(),
        updated_at=design.updated_at.isoformat(),
    )


@router.get("/designs", response_model=DesignListResponse)
async def list_designs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    project_id: UUID | None = Query(None),
    source_type: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DesignListResponse:
    """
    List all designs for the current user.
    """
    # Build base query - join with Project to verify ownership
    query = (
        select(Design, Project.name.label("project_name"))
        .join(Project, Design.project_id == Project.id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
    )

    # Apply filters
    if search:
        query = query.where(Design.name.ilike(f"%{search}%"))

    if project_id:
        query = query.where(Design.project_id == project_id)

    if source_type:
        query = query.where(Design.source_type == source_type)

    # Get total count
    count_query = (
        select(func.count())
        .select_from(Design)
        .join(Project, Design.project_id == Project.id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
    )
    if search:
        count_query = count_query.where(Design.name.ilike(f"%{search}%"))
    if project_id:
        count_query = count_query.where(Design.project_id == project_id)
    if source_type:
        count_query = count_query.where(Design.source_type == source_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Design.updated_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    rows = result.all()

    design_responses = []
    for row in rows:
        design = row[0]
        project_name = row[1]

        thumbnail_url = None
        if design.extra_data:
            thumbnail_url = design.extra_data.get("thumbnail_url")

        design_responses.append(
            DesignResponse(
                id=design.id,
                name=design.name,
                description=design.description,
                project_id=design.project_id,
                project_name=project_name,
                source_type=design.source_type,
                status=design.status,
                thumbnail_url=thumbnail_url,
                created_at=design.created_at.isoformat(),
                updated_at=design.updated_at.isoformat(),
            )
        )

    return DesignListResponse(
        designs=design_responses,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/designs/{design_id}", response_model=DesignResponse)
async def get_design(
    design_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """
    Get a specific design.
    """
    query = (
        select(Design, Project.name.label("project_name"))
        .join(Project, Design.project_id == Project.id)
        .where(Design.id == design_id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
    )
    result = await db.execute(query)
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    design = row[0]
    project_name = row[1]

    thumbnail_url = None
    if design.extra_data:
        thumbnail_url = design.extra_data.get("thumbnail_url")

    return DesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        project_id=design.project_id,
        project_name=project_name,
        source_type=design.source_type,
        status=design.status,
        thumbnail_url=thumbnail_url,
        extra_data=design.extra_data,
        created_at=design.created_at.isoformat(),
        updated_at=design.updated_at.isoformat(),
    )


# NOTE: The delete endpoint with undo support is defined below (delete_design_with_undo)
# It replaces this simple delete endpoint to provide undo capability


# ============================================================================
# Update Design Endpoint
# ============================================================================


class DesignUpdate(BaseModel):
    """Request schema for updating a design."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    project_id: UUID | None = Field(None, description="Move design to a different project")


@router.patch("/designs/{design_id}", response_model=DesignResponse)
async def update_design(
    design_id: UUID,
    update_data: DesignUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """
    Update a design's name, description, or move to another project.

    Only the design owner can update it. Moving requires ownership of
    both the source and target projects.
    """
    # Get design with project for ownership check
    query = (
        select(Design)
        .join(Project, Design.project_id == Project.id)
        .where(Design.id == design_id)
        .where(Project.user_id == current_user.id)
        .where(Design.deleted_at.is_(None))
    )
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    # Handle move to different project
    if update_data.project_id is not None and update_data.project_id != design.project_id:
        # Verify user owns the target project
        target_query = (
            select(Project)
            .where(Project.id == update_data.project_id)
            .where(Project.user_id == current_user.id)
        )
        target_result = await db.execute(target_query)
        target_project = target_result.scalar_one_or_none()

        if not target_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target project not found or you don't have access",
            )

        # Use DesignService for the move operation
        design_service = DesignService(db)
        try:
            design = await design_service.move_design(
                design_id=design_id,
                target_project_id=update_data.project_id,
                user=current_user,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )

    # Apply other updates
    if update_data.name is not None:
        design.name = update_data.name
    if update_data.description is not None:
        design.description = update_data.description

    design.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(design)

    # Get project name for response
    project_query = select(Project.name).where(Project.id == design.project_id)
    project_result = await db.execute(project_query)
    project_name = project_result.scalar_one()

    # Get thumbnail URL if available
    thumbnail_url = None
    if design.extra_data and isinstance(design.extra_data, dict):
        thumbnail_url = design.extra_data.get("thumbnail_url")

    logger.info(f"Design updated: {design_id} by user {current_user.id}")

    return DesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        project_id=design.project_id,
        project_name=project_name,
        source_type=design.source_type,
        status=design.status,
        thumbnail_url=thumbnail_url,
        created_at=design.created_at.isoformat(),
        updated_at=design.updated_at.isoformat(),
    )


# ============================================================================
# Copy Design Endpoint
# ============================================================================


class CopyDesignRequest(BaseModel):
    """Request schema for copying a design."""

    name: str = Field(..., min_length=1, max_length=255, description="Name for the copy")
    target_project_id: UUID | None = Field(
        None, description="Project to copy to (default: same project)"
    )
    include_versions: bool = Field(False, description="Copy all versions (default: only current)")


class CopyDesignResponse(BaseModel):
    """Response schema for a copied design."""

    id: UUID
    name: str
    description: str | None
    project_id: UUID
    project_name: str
    source_type: str
    status: str
    thumbnail_url: str | None
    copied_from_id: UUID | None
    versions_copied: int
    files_copied: int
    created_at: str

    class Config:
        from_attributes = True


# Rate limited: 10 copies per minute per user
@router.post(
    "/designs/{design_id}/copy",
    response_model=CopyDesignResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(expensive_operation_limit)],
)
async def copy_design(
    design_id: UUID,
    copy_request: CopyDesignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CopyDesignResponse:
    """
    Create a copy of an existing design.

    Copies the design and optionally all its versions to the same
    or a different project.

    Rate limit: 10 copies per minute per user (recommended).
    """
    from app.services.design_service import (
        DesignCopyError,
        DesignNotFoundError,
        DesignPermissionError,
        DesignService,
        ProjectNotFoundError,
    )

    service = DesignService(db)

    try:
        result = await service.copy_design(
            design_id=design_id,
            user=current_user,
            name=copy_request.name,
            target_project_id=copy_request.target_project_id,
            include_versions=copy_request.include_versions,
        )
    except DesignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )
    except DesignPermissionError:
        # Return 404 to not reveal whether the design exists
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target project not found",
        )
    except DesignCopyError as e:
        logger.error(f"Copy failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to copy design",
        )

    design = result.design

    # Get project name
    project_query = select(Project.name).where(Project.id == design.project_id)
    project_result = await db.execute(project_query)
    project_name = project_result.scalar_one()

    # Get thumbnail
    thumbnail_url = None
    if design.extra_data and isinstance(design.extra_data, dict):
        thumbnail_url = design.extra_data.get("thumbnail_url")

    return CopyDesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        project_id=design.project_id,
        project_name=project_name,
        source_type=design.source_type,
        status=design.status,
        thumbnail_url=thumbnail_url,
        copied_from_id=design.copied_from_id,
        versions_copied=result.versions_copied,
        files_copied=result.files_copied,
        created_at=design.created_at.isoformat(),
    )


# ============================================================================
# Delete Design with Undo
# ============================================================================


class DeleteDesignResponse(BaseModel):
    """Response schema for delete with undo support."""

    message: str
    design_id: UUID
    undo_token: str
    expires_at: str


# Rate limited: 20 design operations per minute
@router.delete(
    "/designs/{design_id}",
    response_model=DeleteDesignResponse,
    dependencies=[Depends(design_operation_limit)],
)
async def delete_design_with_undo(
    design_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeleteDesignResponse:
    """
    Soft delete a design with undo support.

    Returns an undo token that can be used to restore the design
    within 30 seconds.
    """
    from app.services.design_service import (
        DesignNotFoundError,
        DesignPermissionError,
        DesignService,
    )

    service = DesignService(db)

    try:
        result = await service.delete_design(design_id, current_user)
    except DesignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )
    except DesignPermissionError:
        # Return 404 to not reveal whether the design exists
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    logger.info(f"Design {design_id} deleted by user {current_user.id}")

    return DeleteDesignResponse(
        message="Design deleted",
        design_id=result.design_id,
        undo_token=result.undo_token,
        expires_at=result.expires_at.isoformat(),
    )


class UndoDeleteResponse(BaseModel):
    """Response schema for undo delete."""

    message: str
    design: DesignResponse


@router.post(
    "/designs/undo/{undo_token}",
    response_model=UndoDeleteResponse,
)
async def undo_delete_design(
    undo_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UndoDeleteResponse:
    """
    Restore a recently deleted design using the undo token.

    The undo token expires after 30 seconds.
    """
    from app.services.design_service import (
        DesignPermissionError,
        DesignService,
        UndoTokenExpiredError,
    )

    service = DesignService(db)

    try:
        design = await service.undo_delete(undo_token, current_user)
    except (UndoTokenExpiredError, DesignPermissionError):
        # SECURITY: Use generic error to prevent token enumeration
        # Don't distinguish between invalid token, expired token, or wrong user
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired undo token",
        )

    # Get project name
    project_query = select(Project.name).where(Project.id == design.project_id)
    project_result = await db.execute(project_query)
    project_name = project_result.scalar_one()

    # Get thumbnail
    thumbnail_url = None
    if design.extra_data and isinstance(design.extra_data, dict):
        thumbnail_url = design.extra_data.get("thumbnail_url")

    logger.info(f"Design {design.id} restored by user {current_user.id}")

    return UndoDeleteResponse(
        message="Design restored",
        design=DesignResponse(
            id=design.id,
            name=design.name,
            description=design.description,
            project_id=design.project_id,
            project_name=project_name,
            source_type=design.source_type,
            status=design.status,
            thumbnail_url=thumbnail_url,
            created_at=design.created_at.isoformat(),
            updated_at=design.updated_at.isoformat(),
        ),
    )


# ============================================================================
# Version Endpoints
# ============================================================================


class VersionResponse(BaseModel):
    """Response schema for a design version."""

    id: UUID
    version_number: int
    thumbnail_url: str | None
    change_description: str | None
    created_by_id: UUID | None
    created_at: str
    is_current: bool
    file_formats: dict[str, Any]

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    """Response schema for listing versions."""

    versions: list[VersionResponse]
    total: int
    page: int
    per_page: int


@router.get(
    "/designs/{design_id}/versions",
    response_model=VersionListResponse,
)
async def list_design_versions(
    design_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionListResponse:
    """
    Get version history for a design.

    Returns a paginated list of all versions with metadata.
    """
    from app.services.design_service import (
        DesignNotFoundError,
        DesignPermissionError,
        DesignService,
    )

    service = DesignService(db)

    try:
        versions, total = await service.list_versions(design_id, current_user, page, per_page)
    except DesignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )
    except DesignPermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get design's current version ID
    design_query = select(Design.current_version_id).where(Design.id == design_id)
    design_result = await db.execute(design_query)
    current_version_id = design_result.scalar_one_or_none()

    version_responses = [
        VersionResponse(
            id=v.id,
            version_number=v.version_number,
            thumbnail_url=v.thumbnail_url,
            change_description=v.change_description,
            created_by_id=v.created_by,
            created_at=v.created_at.isoformat(),
            is_current=(v.id == current_version_id),
            file_formats=v.file_formats or {},
        )
        for v in versions
    ]

    return VersionListResponse(
        versions=version_responses,
        total=total,
        page=page,
        per_page=per_page,
    )


class CreateVersionRequest(BaseModel):
    """Request schema for creating a version snapshot."""

    change_description: str | None = Field(None, max_length=500)


@router.post(
    "/designs/{design_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_design_version(
    design_id: UUID,
    request: CreateVersionRequest = CreateVersionRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VersionResponse:
    """
    Create a new version snapshot of a design.

    Captures the current state of the design as a new version.
    """
    from app.services.design_service import (
        DesignNotFoundError,
        DesignPermissionError,
        DesignService,
    )

    service = DesignService(db)

    try:
        version = await service.create_version(design_id, current_user, request.change_description)
    except DesignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )
    except DesignPermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return VersionResponse(
        id=version.id,
        version_number=version.version_number,
        thumbnail_url=version.thumbnail_url,
        change_description=version.change_description,
        created_by_id=version.created_by,
        created_at=version.created_at.isoformat(),
        is_current=True,
        file_formats=version.file_formats or {},
    )


@router.post(
    "/designs/{design_id}/versions/{version_id}/restore",
    response_model=DesignResponse,
)
async def restore_design_version(
    design_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DesignResponse:
    """
    Restore a design to a previous version.

    Creates a new version with the restored state (preserves history).
    """
    from app.services.design_service import (
        DesignNotFoundError,
        DesignPermissionError,
        DesignService,
    )

    service = DesignService(db)

    try:
        design = await service.restore_version(design_id, version_id, current_user)
    except DesignNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design or version not found",
        )
    except DesignPermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get project name
    project_query = select(Project.name).where(Project.id == design.project_id)
    project_result = await db.execute(project_query)
    project_name = project_result.scalar_one()

    # Get thumbnail
    thumbnail_url = None
    if design.extra_data and isinstance(design.extra_data, dict):
        thumbnail_url = design.extra_data.get("thumbnail_url")

    return DesignResponse(
        id=design.id,
        name=design.name,
        description=design.description,
        project_id=design.project_id,
        project_name=project_name,
        source_type=design.source_type,
        status=design.status,
        thumbnail_url=thumbnail_url,
        created_at=design.created_at.isoformat(),
        updated_at=design.updated_at.isoformat(),
    )
