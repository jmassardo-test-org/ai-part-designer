"""
User Data Export API (GDPR Compliance).

Provides endpoints for users to:
- Request export of their personal data
- Check export status
- Download completed exports
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class ExportRequestResponse(BaseModel):
    """Response when requesting a data export."""

    export_id: UUID
    status: str
    requested_at: datetime
    estimated_completion: datetime | None = None
    message: str


class ExportStatusResponse(BaseModel):
    """Status of a data export request."""

    export_id: UUID
    status: str  # pending, processing, completed, failed, expired
    requested_at: datetime
    completed_at: datetime | None = None
    download_url: str | None = None
    expires_at: datetime | None = None
    file_size_bytes: int | None = None
    error_message: str | None = None


class ExportListResponse(BaseModel):
    """List of user's export requests."""

    exports: list[ExportStatusResponse]
    total: int


# =============================================================================
# In-memory storage for export jobs (would be database in production)
# =============================================================================

# Simple in-memory store for demo - in production use database table
_export_jobs: dict[str, dict] = {}


# =============================================================================
# Background task for export
# =============================================================================


async def process_export(
    export_id: str,
    user_id: str,
):
    """
    Background task to process data export.

    This would be a Celery task in production.
    """
    from app.core.backup import data_exporter
    from app.core.storage import StorageBucket, storage_client

    try:
        # Update status to processing
        if export_id in _export_jobs:
            _export_jobs[export_id]["status"] = "processing"

        # Generate export
        export_path = await data_exporter.export_user_data(user_id)

        # Upload to storage
        storage_key = f"exports/{user_id}/{export_path.name}"
        with open(export_path, "rb") as f:
            download_url = await storage_client.upload_file(
                StorageBucket.TEMP,
                storage_key,
                f,
                content_type="application/zip",
                metadata={
                    "user_id": user_id,
                    "export_type": "user_data",
                    "created_at": datetime.now(UTC).isoformat(),
                },
            )

        # Get file size
        file_size = export_path.stat().st_size

        # Clean up local file
        export_path.unlink()

        # Update export record
        if export_id in _export_jobs:
            _export_jobs[export_id].update(
                {
                    "status": "completed",
                    "completed_at": datetime.now(UTC),
                    "download_url": download_url,
                    "file_size_bytes": file_size,
                    "expires_at": datetime.now(UTC) + timedelta(days=7),
                }
            )

    except Exception as e:
        if export_id in _export_jobs:
            _export_jobs[export_id].update(
                {
                    "status": "failed",
                    "error_message": str(e),
                }
            )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/request",
    response_model=ExportRequestResponse,
    summary="Request data export",
    description="Request an export of all your personal data (GDPR compliant).",
)
async def request_data_export(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Request export of user's personal data.

    This initiates an async export job that will:
    - Collect all user profile data
    - Export all projects and designs metadata
    - Export job history
    - Export activity/audit logs

    The export will be available for download once complete.
    """
    # Check for existing pending/processing export
    user_id_str = str(current_user.id)

    for job in _export_jobs.values():
        if job.get("user_id") == user_id_str and job.get("status") in ("pending", "processing"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a pending export request. Please wait for it to complete.",
            )

    # Rate limit: max 1 export per 24 hours
    recent_cutoff = datetime.now(UTC) - timedelta(hours=24)
    for job in _export_jobs.values():
        if (
            job.get("user_id") == user_id_str
            and job.get("requested_at", datetime.min) > recent_cutoff
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You can only request one data export per 24 hours.",
            )

    # Create export job
    export_id = uuid4()
    export_job = {
        "export_id": str(export_id),
        "user_id": user_id_str,
        "status": "pending",
        "requested_at": datetime.now(UTC),
    }
    _export_jobs[str(export_id)] = export_job

    # Queue background task
    background_tasks.add_task(
        process_export,
        str(export_id),
        user_id_str,
    )

    return ExportRequestResponse(
        export_id=export_id,
        status="pending",
        requested_at=export_job["requested_at"],
        estimated_completion=datetime.now(UTC) + timedelta(minutes=5),
        message="Your data export has been requested. You will be notified when it's ready.",
    )


@router.get(
    "/{export_id}",
    response_model=ExportStatusResponse,
    summary="Get export status",
    description="Check the status of a data export request.",
)
async def get_export_status(
    export_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get the status of a specific export request."""
    export_id_str = str(export_id)

    if export_id_str not in _export_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found.",
        )

    job = _export_jobs[export_id_str]

    # Verify ownership
    if job.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found.",
        )

    return ExportStatusResponse(
        export_id=UUID(job["export_id"]),
        status=job["status"],
        requested_at=job["requested_at"],
        completed_at=job.get("completed_at"),
        download_url=job.get("download_url"),
        expires_at=job.get("expires_at"),
        file_size_bytes=job.get("file_size_bytes"),
        error_message=job.get("error_message"),
    )


@router.get(
    "",
    response_model=ExportListResponse,
    summary="List export requests",
    description="List all your data export requests.",
)
async def list_exports(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """List all export requests for the current user."""
    user_id_str = str(current_user.id)

    user_exports = [
        ExportStatusResponse(
            export_id=UUID(job["export_id"]),
            status=job["status"],
            requested_at=job["requested_at"],
            completed_at=job.get("completed_at"),
            download_url=job.get("download_url"),
            expires_at=job.get("expires_at"),
            file_size_bytes=job.get("file_size_bytes"),
            error_message=job.get("error_message"),
        )
        for job in _export_jobs.values()
        if job.get("user_id") == user_id_str
    ]

    # Sort by requested_at descending
    user_exports.sort(key=lambda x: x.requested_at, reverse=True)

    return ExportListResponse(
        exports=user_exports,
        total=len(user_exports),
    )


@router.delete(
    "/{export_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel or delete export",
    description="Cancel a pending export or delete a completed export record.",
)
async def delete_export(
    export_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Cancel or delete an export request."""
    export_id_str = str(export_id)

    if export_id_str not in _export_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found.",
        )

    job = _export_jobs[export_id_str]

    # Verify ownership
    if job.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export not found.",
        )

    # Delete from storage if completed
    if job.get("download_url"):
        try:
            from app.core.storage import StorageBucket, storage_client

            f"exports/{job['user_id']}/{export_id_str}"
            await storage_client.delete_files(
                StorageBucket.TEMP,
                [job["download_url"]],
            )
        except Exception:
            pass  # Ignore storage errors

    # Remove job record
    del _export_jobs[export_id_str]
