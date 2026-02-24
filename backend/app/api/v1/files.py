"""
File upload and management API endpoints.

Provides REST API for uploading, downloading, and managing files.
"""

import hashlib
import logging
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_feature, require_org_feature
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.storage import StorageBucket, storage_client
from app.models.file import (
    CAD_EXTENSIONS,
    CAD_MIME_TYPES,
    FILE_SIZE_LIMITS,
)
from app.models.file import (
    File as FileModel,
)
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class FileResponse(BaseModel):
    """File metadata response."""

    id: str = Field(description="File UUID")
    filename: str = Field(description="Stored filename")
    original_filename: str = Field(description="Original upload filename")
    mime_type: str = Field(description="MIME type")
    size_bytes: int = Field(description="File size in bytes")
    file_type: str = Field(description="File type category")
    cad_format: str | None = Field(description="CAD format if applicable")
    status: str = Field(description="File status")
    thumbnail_url: str | None = Field(description="Thumbnail URL")
    download_url: str = Field(description="Download URL")
    geometry_info: dict[str, Any] | None = Field(description="CAD geometry info")
    created_at: datetime = Field(description="Upload timestamp")

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """Paginated list of files."""

    files: list[FileResponse]
    total: int
    skip: int
    limit: int
    has_more: bool
    total_size_bytes: int


class StorageQuotaResponse(BaseModel):
    """Storage quota information."""

    used_bytes: int
    limit_bytes: int
    file_count: int
    remaining_bytes: int
    usage_percent: float


class DeleteFileResponse(BaseModel):
    """Response after deleting a file."""

    id: str
    status: str
    message: str


# =============================================================================
# Helper Functions
# =============================================================================


def get_file_type(mime_type: str, filename: str) -> tuple[str, str | None]:
    """
    Determine file type and CAD format from MIME type and filename.

    Returns:
        Tuple of (file_type, cad_format)
    """
    # Check CAD MIME types
    if mime_type in CAD_MIME_TYPES:
        return "cad", CAD_MIME_TYPES[mime_type]

    # Check extension
    ext = Path(filename).suffix.lower()
    if ext in CAD_EXTENSIONS:
        return "cad", CAD_EXTENSIONS[ext]

    # Check other types
    if mime_type.startswith("image/"):
        return "image", None
    if mime_type.startswith("video/"):
        return "video", None
    if mime_type in ("application/pdf", "application/msword"):
        return "document", None

    return "other", None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for storage.

    Removes special characters and limits length.
    """
    # Get base name and extension
    path = Path(filename)
    name = path.stem
    ext = path.suffix

    # Remove special characters
    name = "".join(c for c in name if c.isalnum() or c in "._-")
    name = name[:100]  # Limit length

    if not name:
        name = "file"

    return f"{name}{ext}"


async def calculate_checksum(file: UploadFile) -> str:
    """Calculate SHA-256 checksum of file."""
    sha256 = hashlib.sha256()

    # Read in chunks
    while chunk := await file.read(8192):
        sha256.update(chunk)

    # Reset file position
    await file.seek(0)

    return sha256.hexdigest()


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/upload",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Upload a CAD file or other document.",
    responses={
        400: {"description": "Invalid file type or size"},
        413: {"description": "File too large"},
        507: {"description": "Storage quota exceeded"},
    },
)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _feature: None = Depends(require_feature("file_uploads")),
    _org_feature: None = Depends(require_org_feature("file_uploads")),
) -> FileResponse:
    """
    Upload a file.

    Supports CAD files (STEP, STL, IGES) and other document types.
    File size limits apply based on subscription tier.
    """
    # Get user tier and size limit
    tier = current_user.tier or "free"
    size_limit = FILE_SIZE_LIMITS.get(tier, FILE_SIZE_LIMITS["free"])

    # Check file size
    # Note: In production, use request.stream for large files
    file_content = await file.read()
    file_size = len(file_content)
    await file.seek(0)

    if file_size > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size} bytes) exceeds limit ({size_limit} bytes) for {tier} tier",
        )

    # Check storage quota
    quota = await get_storage_quota(current_user, db, settings)
    if quota.remaining_bytes < file_size:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail=f"Storage quota exceeded. {quota.remaining_bytes} bytes remaining",
        )

    # Determine file type
    file_type, cad_format = get_file_type(
        file.content_type or "application/octet-stream",
        file.filename or "file",
    )

    # Validate CAD files
    allowed_extensions = [*list(CAD_EXTENSIONS.keys()), ".pdf", ".png", ".jpg", ".jpeg"]
    ext = Path(file.filename or "").suffix.lower()
    if ext and ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Supported: {', '.join(allowed_extensions)}",
        )

    # Calculate checksum
    checksum = await calculate_checksum(file)

    # Generate storage path
    file_id = uuid4()
    safe_filename = sanitize_filename(file.filename or "file")
    storage_path = f"users/{current_user.id}/{file_id}/{safe_filename}"

    # Create file record
    file_record = FileModel(
        id=file_id,
        user_id=current_user.id,
        filename=safe_filename,
        original_filename=file.filename or "file",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=file_size,
        storage_bucket="uploads",
        storage_path=storage_path,
        file_type=file_type,
        cad_format=cad_format,
        status="uploading",
        checksum_sha256=checksum,
    )

    db.add(file_record)
    await db.flush()

    # Upload to object storage (S3/MinIO)
    try:
        await storage_client.upload_file(
            bucket=StorageBucket.UPLOADS,
            key=storage_path,
            file=file_content,
            content_type=file.content_type or "application/octet-stream",
            metadata={
                "user_id": str(current_user.id),
                "original_filename": file.filename or "file",
                "checksum": checksum,
            },
        )
        logger.debug(f"Uploaded {storage_path} to MinIO")
    except Exception as e:
        logger.warning(f"MinIO upload failed, falling back to local: {e}")
        # Fallback to local filesystem for development
        upload_dir = Path(settings.UPLOAD_DIR) / f"users/{current_user.id}/{file_id}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        with (upload_dir / safe_filename).open("wb") as f:
            f.write(file_content)

    # Mark as ready (skip processing for now)
    file_record.mark_ready()

    await db.commit()
    await db.refresh(file_record)

    logger.info(f"File uploaded: {file_record.id} by user {current_user.id}")

    # Check if storage is at 90%+ and send warning notification (max once per day)
    updated_quota = await get_storage_quota(current_user, db, settings)
    if updated_quota.usage_percent >= 90:
        from datetime import timedelta

        from app.models.notification import Notification, NotificationType
        from app.services.notification_service import notify_storage_warning

        # Only send if no storage warning was sent in the last 24 hours
        one_day_ago = datetime.now() - timedelta(days=1)
        recent_warning = await db.execute(
            select(Notification.id)
            .where(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.type == NotificationType.SYSTEM_ANNOUNCEMENT,
                    Notification.created_at >= one_day_ago,
                    Notification.data["kind"].astext == "storage_warning",
                )
            )
            .limit(1)
        )
        if not recent_warning.scalar_one_or_none():
            await notify_storage_warning(
                db=db,
                user_id=current_user.id,
                usage_percent=updated_quota.usage_percent,
            )

    return FileResponse(
        id=str(file_record.id),
        filename=file_record.filename,
        original_filename=file_record.original_filename,
        mime_type=file_record.mime_type,
        size_bytes=file_record.size_bytes,
        file_type=file_record.file_type,
        cad_format=file_record.cad_format,
        status=file_record.status,
        thumbnail_url=file_record.thumbnail_url,
        download_url=file_record.download_url,
        geometry_info=file_record.geometry_info,
        created_at=file_record.created_at,
    )


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List user's files",
    description="Get paginated list of uploaded files.",
)
async def list_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    file_type: str | None = Query(None, description="Filter by file type"),
    cad_format: str | None = Query(None, description="Filter by CAD format"),
) -> FileListResponse:
    """
    List files for the current user.
    """
    # Build query
    conditions: list[Any] = [
        FileModel.user_id == current_user.id,
        FileModel.is_deleted == False,  # noqa: E712
    ]

    if file_type:
        conditions.append(FileModel.file_type == file_type)
    if cad_format:
        conditions.append(FileModel.cad_format == cad_format)

    # Count total
    count_query = select(func.count(FileModel.id)).where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Get total size
    size_query = select(func.sum(FileModel.size_bytes)).where(and_(*conditions))
    total_size = await db.scalar(size_query) or 0

    # Get page
    query = (
        select(FileModel)
        .where(and_(*conditions))
        .order_by(desc(FileModel.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    files = result.scalars().all()

    return FileListResponse(
        files=[
            FileResponse(
                id=str(f.id),
                filename=f.filename,
                original_filename=f.original_filename,
                mime_type=f.mime_type,
                size_bytes=f.size_bytes,
                file_type=f.file_type,
                cad_format=f.cad_format,
                status=f.status,
                thumbnail_url=f.thumbnail_url,
                download_url=f.download_url,
                geometry_info=f.geometry_info,
                created_at=f.created_at,
            )
            for f in files
        ],
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + limit) < total,
        total_size_bytes=total_size,
    )


@router.get(
    "/quota",
    response_model=StorageQuotaResponse,
    summary="Get storage quota",
    description="Get current storage usage and limits.",
)
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StorageQuotaResponse:
    """
    Get storage quota for the current user.
    """
    return await get_storage_quota(current_user, db, settings)


async def get_storage_quota(
    user: User,
    db: AsyncSession,
    _settings: Settings,
) -> StorageQuotaResponse:
    """Calculate storage quota for a user."""
    # Get total used storage
    query = select(
        func.count(FileModel.id),
        func.sum(FileModel.size_bytes),
    ).where(
        and_(
            FileModel.user_id == user.id,
            FileModel.is_deleted == False,  # noqa: E712
        )
    )
    result = await db.execute(query)
    row = result.one()
    file_count = row[0] or 0
    used_bytes = row[1] or 0

    # Get limit based on tier
    tier = user.tier or "free"
    # Storage limits (example values)
    storage_limits = {
        "free": 100 * 1024 * 1024,  # 100 MB
        "basic": 1024 * 1024 * 1024,  # 1 GB
        "pro": 10 * 1024 * 1024 * 1024,  # 10 GB
        "enterprise": 100 * 1024 * 1024 * 1024,  # 100 GB
    }
    limit_bytes = storage_limits.get(tier, storage_limits["free"])

    remaining = max(0, limit_bytes - used_bytes)
    usage_percent = (used_bytes / limit_bytes * 100) if limit_bytes > 0 else 0

    return StorageQuotaResponse(
        used_bytes=used_bytes,
        limit_bytes=limit_bytes,
        file_count=file_count,
        remaining_bytes=remaining,
        usage_percent=round(usage_percent, 2),
    )


@router.get(
    "/{file_id}",
    response_model=FileResponse,
    summary="Get file details",
    description="Get metadata for a specific file.",
    responses={
        404: {"description": "File not found"},
    },
)
async def get_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Get file metadata.
    """
    query = select(FileModel).where(
        and_(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id,
            FileModel.is_deleted == False,  # noqa: E712
        )
    )
    result = await db.execute(query)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return FileResponse(
        id=str(file_record.id),
        filename=file_record.filename,
        original_filename=file_record.original_filename,
        mime_type=file_record.mime_type,
        size_bytes=file_record.size_bytes,
        file_type=file_record.file_type,
        cad_format=file_record.cad_format,
        status=file_record.status,
        thumbnail_url=file_record.thumbnail_url,
        download_url=file_record.download_url,
        geometry_info=file_record.geometry_info,
        created_at=file_record.created_at,
    )


@router.get(
    "/{file_id}/download",
    summary="Download a file",
    description="Download the file content.",
    responses={
        404: {"description": "File not found"},
    },
)
async def download_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """
    Download a file.
    """
    query = select(FileModel).where(
        and_(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id,
            FileModel.is_deleted == False,  # noqa: E712
        )
    )
    result = await db.execute(query)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Try to download from object storage (S3/MinIO)
    try:
        file_content = await storage_client.download_file(
            bucket=StorageBucket.UPLOADS,
            key=file_record.storage_path,
        )
        logger.debug(f"Downloaded {file_record.storage_path} from MinIO")

        async def iter_bytes() -> AsyncIterator[bytes]:
            yield file_content

        return StreamingResponse(
            iter_bytes(),
            media_type=file_record.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_record.original_filename}"',
                "Content-Length": str(file_record.size_bytes),
            },
        )
    except Exception as e:
        logger.warning(f"MinIO download failed, trying local filesystem: {e}")
        # Fallback to local filesystem for development
        file_path = Path(settings.UPLOAD_DIR) / file_record.storage_path

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File content not found",
            )

        def iterfile() -> Iterator[bytes]:
            with file_path.open("rb") as f:
                yield from f

        return StreamingResponse(
            iterfile(),
            media_type=file_record.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_record.original_filename}"',
                "Content-Length": str(file_record.size_bytes),
            },
        )


@router.delete(
    "/{file_id}",
    response_model=DeleteFileResponse,
    summary="Delete a file",
    description="Soft-delete a file (moves to trash).",
    responses={
        404: {"description": "File not found"},
    },
)
async def delete_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeleteFileResponse:
    """
    Delete a file (soft delete).

    File is moved to trash and can be restored within retention period.
    """
    query = select(FileModel).where(
        and_(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id,
            FileModel.is_deleted == False,  # noqa: E712
        )
    )
    result = await db.execute(query)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file_record.soft_delete()
    await db.commit()

    logger.info(f"File deleted: {file_id} by user {current_user.id}")

    return DeleteFileResponse(
        id=str(file_record.id),
        status="deleted",
        message="File moved to trash",
    )


# =============================================================================
# Presigned URL Endpoints
# =============================================================================


class PresignedUploadResponse(BaseModel):
    """Response containing presigned upload URL."""

    url: str = Field(description="Presigned upload URL")
    fields: dict[str, Any] = Field(description="Form fields to include in upload")
    key: str = Field(description="Object key to upload to")
    expires_in: int = Field(description="URL expiration in seconds")


class PresignedDownloadResponse(BaseModel):
    """Response containing presigned download URL."""

    url: str = Field(description="Presigned download URL")
    expires_in: int = Field(description="URL expiration in seconds")


@router.post(
    "/presigned-upload",
    response_model=PresignedUploadResponse,
    summary="Get presigned upload URL",
    description="Get a presigned URL for direct upload to storage.",
)
async def get_presigned_upload_url(
    filename: str = Query(..., description="Filename to upload"),
    content_type: str = Query("application/octet-stream", description="MIME type"),
    current_user: User = Depends(get_current_user),
) -> PresignedUploadResponse:
    """
    Get a presigned URL for direct file upload to storage.

    Allows clients to upload directly to S3/MinIO without going through the API.
    """
    file_id = uuid4()
    safe_filename = sanitize_filename(filename)
    key = f"users/{current_user.id}/{file_id}/{safe_filename}"
    expires_in = 3600  # 1 hour

    try:
        presigned = await storage_client.generate_presigned_upload_url(
            bucket=StorageBucket.UPLOADS,
            key=key,
            expires_in=expires_in,
            content_type=content_type,
        )
        return PresignedUploadResponse(
            url=presigned["url"],
            fields=presigned["fields"],
            key=key,
            expires_in=expires_in,
        )
    except Exception as e:
        logger.error(f"Failed to generate presigned upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )


@router.get(
    "/{file_id}/presigned-download",
    response_model=PresignedDownloadResponse,
    summary="Get presigned download URL",
    description="Get a presigned URL for direct download from storage.",
    responses={
        404: {"description": "File not found"},
    },
)
async def get_presigned_download_url(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PresignedDownloadResponse:
    """
    Get a presigned URL for direct file download from storage.

    Allows clients to download directly from S3/MinIO without going through the API.
    """
    query = select(FileModel).where(
        and_(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id,
            FileModel.is_deleted == False,  # noqa: E712
        )
    )
    result = await db.execute(query)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    expires_in = 3600  # 1 hour

    try:
        url = await storage_client.generate_presigned_download_url(
            bucket=StorageBucket.UPLOADS,
            key=file_record.storage_path,
            expires_in=expires_in,
            filename=file_record.original_filename,
        )
        return PresignedDownloadResponse(
            url=url,
            expires_in=expires_in,
        )
    except Exception as e:
        logger.error(f"Failed to generate presigned download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL",
        )
