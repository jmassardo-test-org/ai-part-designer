"""
Download endpoints for CAD v2 generated files.

Provides file download functionality for generated STEP/STL files.
"""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Directory where generated files are stored
EXPORTS_DIR = Path(get_settings().UPLOAD_DIR) / "cad_exports"

# Default retention period for generated files (24 hours)
DEFAULT_RETENTION_HOURS = 24


def get_exports_dir() -> Path:
    """Get the exports directory, creating if needed."""
    exports_dir = EXPORTS_DIR
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir


def get_job_dir(job_id: str) -> Path:
    """Get the directory for a specific job."""
    return get_exports_dir() / job_id


@router.get(
    "/{job_id}/{filename}",
    summary="Download generated CAD file",
    description="Download a generated STEP or STL file by job ID and filename.",
    responses={
        200: {"description": "File content"},
        404: {"description": "File not found"},
    },
)
async def download_file(
    job_id: str,
    filename: str,
) -> FileResponse:
    """Download a generated CAD file.

    Args:
        job_id: The job ID from generation.
        filename: The filename to download.

    Returns:
        The file content with appropriate content type.
    """
    # Validate job_id to prevent path traversal
    if ".." in job_id or "/" in job_id or "\\" in job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID",
        )

    # Validate filename
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    job_dir = get_job_dir(job_id)
    file_path = job_dir / filename

    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename}",
        )

    # Determine content type based on extension
    ext = file_path.suffix.lower()
    media_types = {
        ".step": "application/STEP",
        ".stp": "application/STEP",
        ".stl": "application/sla",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/{job_id}",
    summary="List files for a job",
    description="List all generated files for a job ID.",
    responses={
        200: {"description": "List of files"},
        404: {"description": "Job not found"},
    },
)
async def list_job_files(job_id: str) -> dict[str, Any]:
    """List all files generated for a job.

    Args:
        job_id: The job ID from generation.

    Returns:
        Dictionary with list of available files.
    """
    # Validate job_id
    if ".." in job_id or "/" in job_id or "\\" in job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID",
        )

    job_dir = get_job_dir(job_id)

    if not job_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    files = []
    for f in job_dir.iterdir():
        if f.is_file():
            files.append(
                {
                    "name": f.name,
                    "size_bytes": f.stat().st_size,
                    "download_url": f"/api/v2/downloads/{job_id}/{f.name}",
                }
            )

    return {
        "job_id": job_id,
        "files": files,
    }


# =============================================================================
# Cleanup Utilities
# =============================================================================


def cleanup_old_exports(max_age_hours: int = DEFAULT_RETENTION_HOURS) -> dict[str, Any]:
    """Clean up old export directories.

    Removes job directories older than max_age_hours.

    Args:
        max_age_hours: Maximum age in hours before cleanup.

    Returns:
        Dictionary with cleanup statistics.
    """
    exports_dir = get_exports_dir()
    cutoff_time = datetime.now(tz=UTC) - timedelta(hours=max_age_hours)

    removed_count = 0
    removed_size = 0
    errors = []

    for job_dir in exports_dir.iterdir():
        if not job_dir.is_dir():
            continue

        try:
            # Check directory modification time
            mtime = datetime.fromtimestamp(job_dir.stat().st_mtime, tz=UTC)
            if mtime < cutoff_time:
                # Calculate size before removal
                dir_size = sum(f.stat().st_size for f in job_dir.rglob("*") if f.is_file())

                # Remove directory
                shutil.rmtree(job_dir)

                removed_count += 1
                removed_size += dir_size
                logger.info(f"Cleaned up old export: {job_dir.name}")
        except Exception as e:
            errors.append(f"{job_dir.name}: {e!s}")
            logger.error(f"Failed to cleanup {job_dir}: {e}")

    return {
        "removed_count": removed_count,
        "removed_size_bytes": removed_size,
        "errors": errors,
    }


def delete_job(job_id: str) -> bool:
    """Delete a specific job's files.

    Args:
        job_id: The job ID to delete.

    Returns:
        True if deleted, False if not found.
    """
    # Validate job_id
    if ".." in job_id or "/" in job_id or "\\" in job_id:
        raise ValueError("Invalid job ID")

    job_dir = get_job_dir(job_id)

    if not job_dir.exists():
        return False

    shutil.rmtree(job_dir)
    logger.info(f"Deleted job: {job_id}")
    return True
