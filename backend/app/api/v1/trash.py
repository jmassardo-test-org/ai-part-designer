"""
Trash Bin API.

Provides endpoints for:
- Listing trashed items
- Restoring from trash
- Permanent deletion
- Configuring retention policy
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.design import Design
from app.models.user import User

router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================


class TrashedItemResponse(BaseModel):
    """A trashed item."""

    id: UUID
    name: str
    item_type: str  # design, project, file
    deleted_at: datetime
    deleted_by: str | None = None
    original_location: str | None = None
    size_bytes: int | None = None
    expires_at: datetime
    days_until_deletion: int

    class Config:
        from_attributes = True


class TrashListResponse(BaseModel):
    """List of trashed items."""

    items: list[TrashedItemResponse]
    total: int
    page: int
    page_size: int
    retention_days: int


class RestoreResponse(BaseModel):
    """Response after restoring item."""

    id: UUID
    name: str
    restored_at: datetime
    message: str


class TrashSettingsRequest(BaseModel):
    """Update trash settings."""

    retention_days: int = Field(
        ge=1,
        le=365,
        description="Days to keep items in trash before permanent deletion",
    )
    auto_empty: bool = Field(
        default=True,
        description="Automatically empty trash after retention period",
    )


class TrashSettingsResponse(BaseModel):
    """Current trash settings."""

    retention_days: int
    auto_empty: bool
    next_cleanup: datetime | None


class TrashStatsResponse(BaseModel):
    """Trash statistics."""

    total_items: int
    total_size_bytes: int
    oldest_item_date: datetime | None
    items_expiring_soon: int  # Within 7 days


# =============================================================================
# Configuration
# =============================================================================

# Default retention period (can be configured per-user or globally)
DEFAULT_RETENTION_DAYS = 30


def get_retention_days(user: User) -> int:
    """Get retention days for user (from settings or default)."""
    user_settings: dict[str, Any] = user.extra_data.get("trash_settings", {})
    retention: int = user_settings.get("retention_days", DEFAULT_RETENTION_DAYS)
    return retention


def calculate_expiry(deleted_at: datetime, retention_days: int) -> datetime:
    """Calculate when item will be permanently deleted."""
    return deleted_at + timedelta(days=retention_days)


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/trash",
    response_model=TrashListResponse,
    summary="List trashed items",
    description="Get paginated list of items in trash.",
)
async def list_trash(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    _item_type: Annotated[str | None, Query()] = None,  # TODO: Implement item type filtering
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrashListResponse:
    """List all items in user's trash."""
    retention_days = get_retention_days(current_user)

    # Base query for soft-deleted designs
    base_query = (
        select(Design)
        .where(Design.deleted_at.isnot(None))
        .where(Design.project.has(user_id=current_user.id))
    )

    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = base_query.order_by(Design.deleted_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    designs = result.scalars().all()

    # Build response
    items = []
    for design in designs:
        expires_at = calculate_expiry(design.deleted_at, retention_days)
        days_left = (expires_at - datetime.now(tz=UTC)).days

        items.append(
            TrashedItemResponse(
                id=design.id,
                name=design.name,
                item_type="design",
                deleted_at=design.deleted_at,
                deleted_by=None,  # Would track who deleted
                original_location=f"projects/{design.project_id}",
                size_bytes=None,  # Would get from file storage
                expires_at=expires_at,
                days_until_deletion=max(0, days_left),
            )
        )

    return TrashListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        retention_days=retention_days,
    )


@router.post(
    "/trash/{item_id}/restore",
    response_model=RestoreResponse,
    summary="Restore from trash",
    description="Restore a trashed item to its original location.",
)
async def restore_from_trash(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RestoreResponse:
    """Restore an item from trash."""
    # Find the trashed design
    query = (
        select(Design)
        .where(Design.id == item_id)
        .where(Design.deleted_at.isnot(None))
        .where(Design.project.has(user_id=current_user.id))
    )
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in trash",
        )

    # Restore by clearing deleted_at
    design.deleted_at = None
    design.updated_at = datetime.now(tz=UTC)

    await db.commit()

    return RestoreResponse(
        id=design.id,
        name=design.name,
        restored_at=datetime.now(tz=UTC),
        message=f"'{design.name}' has been restored",
    )


@router.delete(
    "/trash/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete",
    description="Permanently delete an item from trash.",
)
async def permanent_delete(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Permanently delete an item (no recovery)."""
    # Find the trashed design
    query = (
        select(Design)
        .where(Design.id == item_id)
        .where(Design.deleted_at.isnot(None))
        .where(Design.project.has(user_id=current_user.id))
    )
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in trash",
        )

    # Actually delete from database
    await db.delete(design)
    await db.commit()

    # Note: In production, also delete associated files from storage


@router.delete(
    "/trash",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Empty trash",
    description="Permanently delete all items in trash.",
)
async def empty_trash(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Empty the entire trash."""
    # Get all trashed designs
    query = (
        select(Design)
        .where(Design.deleted_at.isnot(None))
        .where(Design.project.has(user_id=current_user.id))
    )
    result = await db.execute(query)
    designs = result.scalars().all()

    # Delete all
    for design in designs:
        await db.delete(design)

    await db.commit()


@router.get(
    "/trash/stats",
    response_model=TrashStatsResponse,
    summary="Get trash stats",
    description="Get statistics about items in trash.",
)
async def get_trash_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrashStatsResponse:
    """Get trash statistics."""
    retention_days = get_retention_days(current_user)
    datetime.now(tz=UTC) + timedelta(days=7)

    # Base filter
    base_filter = and_(
        Design.deleted_at.isnot(None),
        Design.project.has(user_id=current_user.id),
    )

    # Total count
    total = (await db.execute(select(func.count()).where(base_filter))).scalar_one()

    # Oldest item
    oldest_query = (
        select(Design.deleted_at).where(base_filter).order_by(Design.deleted_at.asc()).limit(1)
    )
    oldest_result = await db.execute(oldest_query)
    oldest_date = oldest_result.scalar_one_or_none()

    # Items expiring soon (within 7 days)
    # This requires calculating expiry based on deleted_at + retention
    # Simplified: count items deleted more than (retention - 7) days ago
    expiring_threshold = datetime.now(tz=UTC) - timedelta(days=retention_days - 7)
    expiring_soon = (
        await db.execute(
            select(func.count()).where(base_filter).where(Design.deleted_at <= expiring_threshold)
        )
    ).scalar_one()

    return TrashStatsResponse(
        total_items=total,
        total_size_bytes=0,  # Would calculate from file storage
        oldest_item_date=oldest_date,
        items_expiring_soon=expiring_soon,
    )


@router.get(
    "/trash/settings",
    response_model=TrashSettingsResponse,
    summary="Get trash settings",
    description="Get current trash retention settings.",
)
async def get_trash_settings(
    current_user: User = Depends(get_current_user),
) -> TrashSettingsResponse:
    """Get user's trash settings."""
    settings = current_user.extra_data.get("trash_settings", {})

    return TrashSettingsResponse(
        retention_days=settings.get("retention_days", DEFAULT_RETENTION_DAYS),
        auto_empty=settings.get("auto_empty", True),
        next_cleanup=None,  # Would come from scheduled task
    )


@router.put(
    "/trash/settings",
    response_model=TrashSettingsResponse,
    summary="Update trash settings",
    description="Update trash retention settings.",
)
async def update_trash_settings(
    request: TrashSettingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrashSettingsResponse:
    """Update user's trash settings."""
    # Update user extra_data
    trash_settings = current_user.extra_data.get("trash_settings", {})
    trash_settings["retention_days"] = request.retention_days
    trash_settings["auto_empty"] = request.auto_empty
    current_user.extra_data["trash_settings"] = trash_settings

    await db.commit()

    return TrashSettingsResponse(
        retention_days=request.retention_days,
        auto_empty=request.auto_empty,
        next_cleanup=None,
    )
