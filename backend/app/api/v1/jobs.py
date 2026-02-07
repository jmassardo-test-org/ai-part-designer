"""
Job management API endpoints.

Provides REST API for tracking async job status and results.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.design import Design, DesignVersion
from app.models.job import Job
from app.models.project import Project
from app.worker.celery import celery_app

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class JobResponse(BaseModel):
    """Job status response."""

    id: str = Field(description="Job UUID")
    job_type: str = Field(description="Type of job")
    status: str = Field(description="Current status")
    priority: int = Field(description="Job priority (lower = higher)")
    progress: int = Field(description="Progress percentage (0-100)")
    progress_message: str | None = Field(description="Current progress message")

    input_params: dict[str, Any] = Field(description="Input parameters")
    result: dict[str, Any] | None = Field(description="Result data (when complete)")
    error_message: str | None = Field(description="Error message (when failed)")

    created_at: datetime = Field(description="When job was created")
    started_at: datetime | None = Field(description="When job started running")
    completed_at: datetime | None = Field(description="When job completed")
    execution_time_ms: int | None = Field(description="Execution time in ms")

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Paginated list of jobs."""

    jobs: list[JobResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class CancelJobResponse(BaseModel):
    """Response after cancelling a job."""

    id: str
    status: str
    message: str


# =============================================================================
# Helper Functions
# =============================================================================


def _requeue_job_task(job: Job) -> str | None:
    """
    Re-queue a Celery task for the given job.

    Args:
        job: The job to re-queue

    Returns:
        The new Celery task ID, or None if job type doesn't have a task

    Raises:
        ValueError: If job type is not supported for re-queuing
    """
    from app.worker.tasks.ai import generate_from_prompt
    from app.worker.tasks.cad_v2 import compile_enclosure_v2
    from app.worker.tasks.export import convert_format
    from app.worker.tasks.extraction import extract_component_task

    job_id = str(job.id)
    user_id = str(job.user_id) if job.user_id else None
    input_params = job.input_params or {}

    # Map job types to their Celery tasks
    task_result = None

    if job.job_type == "ai_generation":
        # AI generation task
        prompt = input_params.get("prompt")
        if not prompt:
            logger.error(
                "job_requeue_missing_param",
                job_id=job_id,
                job_type=job.job_type,
                missing_param="prompt",
            )
            raise ValueError("Missing required parameter 'prompt' for ai_generation job")

        task_result = generate_from_prompt.delay(
            job_id=job_id,
            prompt=prompt,
            _context=input_params.get("context"),
            user_id=user_id,
        )

    elif job.job_type == "cad_v2_compile":
        # CAD v2 compilation task
        enclosure_schema = input_params.get("enclosure_schema")
        if not enclosure_schema:
            logger.error(
                "job_requeue_missing_param",
                job_id=job_id,
                job_type=job.job_type,
                missing_param="enclosure_schema",
            )
            raise ValueError("Missing required parameter 'enclosure_schema' for cad_v2_compile job")

        task_result = compile_enclosure_v2.delay(
            job_id=job_id,
            enclosure_schema=enclosure_schema,
            export_format=input_params.get("export_format", "step"),
            user_id=user_id,
        )

    elif job.job_type == "format_conversion":
        # Format conversion task
        source_url = input_params.get("source_url")
        if not source_url:
            logger.error(
                "job_requeue_missing_param",
                job_id=job_id,
                job_type=job.job_type,
                missing_param="source_url",
            )
            raise ValueError("Missing required parameter 'source_url' for format_conversion job")

        task_result = convert_format.delay(
            job_id=job_id,
            source_url=source_url,
            target_format=input_params.get("target_format", "step"),
        )

    elif job.job_type in ("cad", "datasheet", "full"):
        # Component extraction task
        # Job types: "cad" (CAD only), "datasheet" (datasheet only), "full" (both)
        task_result = extract_component_task.delay(job_id)

    else:
        # For other job types, we don't currently support re-queuing
        logger.warning(
            "job_requeue_unsupported",
            job_id=job_id,
            job_type=job.job_type,
        )
        return None

    return task_result.id if task_result else None


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=JobListResponse,
    summary="List user's jobs",
    description="Get paginated list of the current user's jobs.",
)
async def list_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of jobs to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max jobs to return"),
    status_filter: str | None = Query(None, description="Filter by status"),
    job_type: str | None = Query(None, description="Filter by job type"),
) -> JobListResponse:
    """
    List jobs for the current user.

    Supports pagination and filtering by status/type.
    """
    # Build query
    conditions = [Job.user_id == current_user.id]

    if status_filter:
        conditions.append(Job.status == status_filter)
    if job_type:
        conditions.append(Job.job_type == job_type)

    # Count total
    count_query = select(Job).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    # Get page
    query = (
        select(Job)
        .where(and_(*conditions))
        .order_by(desc(Job.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[
            JobResponse(
                id=str(job.id),
                job_type=job.job_type,
                status=job.status,
                priority=job.priority,
                progress=job.progress,
                progress_message=job.progress_message,
                input_params=job.input_params,
                result=job.result,
                error_message=job.error_message,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                execution_time_ms=job.execution_time_ms,
            )
            for job in jobs
        ],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
    description="Get detailed status for a specific job.",
    responses={
        404: {"description": "Job not found"},
    },
)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Get status for a specific job.

    Returns current status, progress, and results if complete.
    """
    query = select(Job).where(
        and_(
            Job.id == job_id,
            Job.user_id == current_user.id,
        )
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobResponse(
        id=str(job.id),
        job_type=job.job_type,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        progress_message=job.progress_message,
        input_params=job.input_params,
        result=job.result,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        execution_time_ms=job.execution_time_ms,
    )


@router.post(
    "/{job_id}/cancel",
    response_model=CancelJobResponse,
    summary="Cancel a job",
    description="Request cancellation of a pending or running job.",
    responses={
        400: {"description": "Job cannot be cancelled"},
        404: {"description": "Job not found"},
    },
)
async def cancel_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CancelJobResponse:
    """
    Cancel a job.

    Only pending or running jobs can be cancelled.
    """
    query = select(Job).where(
        and_(
            Job.id == job_id,
            Job.user_id == current_user.id,
        )
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.is_terminal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is already {job.status} and cannot be cancelled",
        )

    # Cancel the job
    job.cancel()
    await db.commit()

    # Revoke the Celery task if it exists
    if job.celery_task_id:
        try:
            celery_app.control.revoke(
                job.celery_task_id,
                terminate=True,
                signal="SIGTERM",  # Allow graceful cleanup
            )
            logger.info(
                "celery_task_revoked",
                job_id=str(job_id),
                task_id=job.celery_task_id,
            )
        except Exception as e:
            # Log the error but don't fail the cancellation
            logger.warning(
                "celery_task_revoke_failed",
                job_id=str(job_id),
                task_id=job.celery_task_id,
                error=str(e),
            )
    else:
        logger.debug(
            "job_cancelled_no_task_id",
            job_id=str(job_id),
        )

    logger.info(
        "job_cancelled",
        job_id=str(job_id),
        user_id=str(current_user.id),
    )

    return CancelJobResponse(
        id=str(job.id),
        status=job.status,
        message="Job cancelled successfully",
    )


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    summary="Retry a failed job",
    description="Retry a failed job if retries remaining.",
    responses={
        400: {"description": "Job cannot be retried"},
        404: {"description": "Job not found"},
    },
)
async def retry_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Retry a failed job.

    Only failed jobs with remaining retries can be retried.
    """
    query = select(Job).where(
        and_(
            Job.id == job_id,
            Job.user_id == current_user.id,
        )
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if not job.can_retry:
        if job.status != "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job is {job.status}, only failed jobs can be retried",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job has exhausted all {job.max_retries} retries",
        )

    # Reset job for retry
    job.status = "pending"
    job.started_at = None
    job.completed_at = None
    job.error = None
    job.error_message = None
    job.progress = 0
    job.progress_message = None
    job.retry_count += 1

    # Log old task ID before clearing (for debugging)
    if job.celery_task_id:
        logger.debug(
            "clearing_old_task_id",
            job_id=str(job_id),
            old_task_id=job.celery_task_id,
        )
    job.celery_task_id = None

    await db.commit()

    # Re-queue the Celery task
    try:
        new_task_id = _requeue_job_task(job)
        if new_task_id:
            job.celery_task_id = new_task_id
            await db.commit()
            logger.info(
                "job_requeued",
                job_id=str(job_id),
                retry_count=job.retry_count,
                max_retries=job.max_retries,
                new_task_id=new_task_id,
            )
        else:
            logger.warning(
                "job_requeue_no_task",
                job_id=str(job_id),
                job_type=job.job_type,
            )
    except Exception as e:
        # Roll back the retry if re-queuing fails
        job.status = "failed"  # Revert to failed state
        job.retry_count -= 1
        job.celery_task_id = None
        await db.commit()
        logger.error(
            "job_requeue_failed",
            job_id=str(job_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-queue job: {e!s}",
        )

    return JobResponse(
        id=str(job.id),
        job_type=job.job_type,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        progress_message=job.progress_message,
        input_params=job.input_params,
        result=job.result,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        execution_time_ms=job.execution_time_ms,
    )


@router.get(
    "/stats/summary",
    summary="Get job statistics",
    description="Get summary statistics for user's jobs.",
)
async def get_job_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get job statistics for the current user.
    """
    # Get all user jobs
    query = select(Job).where(Job.user_id == current_user.id)
    result = await db.execute(query)
    jobs = result.scalars().all()

    stats = {
        "total": len(jobs),
        "pending": sum(1 for j in jobs if j.status == "pending"),
        "running": sum(1 for j in jobs if j.status == "running"),
        "completed": sum(1 for j in jobs if j.status == "completed"),
        "failed": sum(1 for j in jobs if j.status == "failed"),
        "cancelled": sum(1 for j in jobs if j.status == "cancelled"),
        "avg_execution_time_ms": None,
    }

    # Calculate average execution time
    completed_times = [j.execution_time_ms for j in jobs if j.execution_time_ms]
    if completed_times:
        stats["avg_execution_time_ms"] = sum(completed_times) // len(completed_times)

    return stats


# =============================================================================
# Save Generation Endpoint
# =============================================================================


class SaveGenerationRequest(BaseModel):
    """Request to save a generated design."""

    name: str = Field(..., min_length=1, max_length=255, description="Name for the saved design")
    description: str | None = Field(None, max_length=2000, description="Design description")
    project_id: UUID | None = Field(
        None, description="Project to save to (uses default if not provided)"
    )
    tags: list[str] = Field(default_factory=list, max_length=10, description="Tags for the design")


class SavedDesignResponse(BaseModel):
    """Response after saving a design."""

    design_id: str = Field(description="Created design UUID")
    version_id: str = Field(description="Initial version UUID")
    project_id: str = Field(description="Project the design was saved to")
    project_name: str = Field(description="Name of the project")
    name: str = Field(description="Design name")
    status: str = Field(description="Design status")
    thumbnail_url: str | None = Field(description="Thumbnail URL if available")
    file_urls: dict[str, Any] = Field(description="URLs for CAD files by format")
    message: str = Field(description="Success message")


@router.post(
    "/{job_id}/save",
    response_model=SavedDesignResponse,
    summary="Save a generated design",
    description="Persist a completed generation job as a permanent design.",
    responses={
        400: {"description": "Job not complete or already saved"},
        404: {"description": "Job not found"},
    },
)
async def save_generation(
    job_id: UUID,
    request: SaveGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SavedDesignResponse:
    """
    Save a generated design to the user's account.

    This persists the temporary generation files to permanent storage
    and creates a Design record with initial version.

    - If project_id is provided, saves to that project
    - Otherwise saves to user's default "My Designs" project
    - Can only be called once per job (idempotent check)
    """
    # Get the job
    query = select(Job).where(
        and_(
            Job.id == job_id,
            Job.user_id == current_user.id,
        )
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check job is completed generation
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is {job.status}, only completed jobs can be saved",
        )

    if job.job_type != "ai_generation":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only AI generation jobs can be saved as designs",
        )

    # Check if already saved (job already linked to a design)
    if job.design_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This generation has already been saved",
        )

    # Get or create target project
    project: Project | None = None
    if request.project_id:
        # Verify project exists and user owns it
        project_query = select(Project).where(
            and_(
                Project.id == request.project_id,
                Project.user_id == current_user.id,
                Project.deleted_at.is_(None),
            )
        )
        project_result = await db.execute(project_query)
        project = project_result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
    else:
        # Get or create default project
        default_query = select(Project).where(
            and_(
                Project.user_id == current_user.id,
                Project.name == "My Designs",
                Project.deleted_at.is_(None),
            )
        )
        default_result = await db.execute(default_query)
        project = default_result.scalar_one_or_none()

        if not project:
            project = Project(
                user_id=current_user.id,
                name="My Designs",
                description="Default project for your designs",
            )
            db.add(project)
            await db.flush()

    # Extract result data from job
    job_result = job.result or {}
    file_urls = job_result.get("file_urls", {})
    thumbnail_url = job_result.get("thumbnail_url")
    geometry_info = job_result.get("geometry_info", {})

    # Get primary file URL (prefer STEP format)
    primary_file_url = (
        file_urls.get("step")
        or file_urls.get("stl")
        or file_urls.get("3mf")
        or next(iter(file_urls.values()), "")
    )

    # Create the Design
    design = Design(
        project_id=project.id,
        template_id=None,  # AI generated, no template
        name=request.name,
        description=request.description,
        source_type="ai_generated",
        status="ready",
        tags=request.tags,
        metadata={
            "ai_prompt": job.input_params.get("prompt"),
            "ai_style": job.input_params.get("style"),
            "generation_job_id": str(job.id),
            "thumbnail_url": thumbnail_url,
            "file_urls": file_urls,
            "geometry_info": geometry_info,
            "dimensions": geometry_info.get("dimensions"),
        },
    )
    db.add(design)
    await db.flush()

    # Create initial version
    version = DesignVersion(
        design_id=design.id,
        version_number=1,
        file_url=primary_file_url,
        file_formats=file_urls,
        thumbnail_url=thumbnail_url,
        parameters=job.input_params,
        geometry_info=geometry_info,
        change_description="Initial version from AI generation",
        created_by=current_user.id,
    )
    db.add(version)
    await db.flush()

    # Link design to version
    design.current_version_id = version.id

    # Link job to design (prevents saving again)
    job.design_id = design.id

    await db.commit()

    logger.info(f"Saved generation {job_id} as design {design.id} for user {current_user.id}")

    return SavedDesignResponse(
        design_id=str(design.id),
        version_id=str(version.id),
        project_id=str(project.id),
        project_name=project.name,
        name=design.name,
        status=design.status,
        thumbnail_url=thumbnail_url,
        file_urls=file_urls,
        message="Design saved successfully",
    )
