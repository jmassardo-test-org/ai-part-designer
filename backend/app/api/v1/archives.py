"""
Admin Archive API.

Provides endpoints for managing archived designs:
- Listing archived designs (paginated)
- Restoring designs from cold storage
- Permanently deleting archived designs

All endpoints require admin authentication.
"""

import math
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.database import get_db
from app.schemas.archive import (
    ArchivedDesignListResponse,
    ArchivedDesignResponse,
    RestoreDesignResponse,
)
from app.services.design_archive import DesignArchiveService

router = APIRouter(
    dependencies=[Depends(require_admin())],
)


@router.get(
    "/archives/designs",
    response_model=ArchivedDesignListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_archived_designs(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db),
) -> ArchivedDesignListResponse:
    """List archived designs with pagination.

    Returns a paginated list of designs that have been archived
    to cold storage. Requires admin authentication.
    """
    service = DesignArchiveService(db)
    designs, total = await service.list_archived_designs(page=page, per_page=per_page)

    pages = math.ceil(total / per_page) if total > 0 else 0

    return ArchivedDesignListResponse(
        items=[
            ArchivedDesignResponse(
                id=d.id,
                name=d.name,
                archived_at=d.archived_at,  # type: ignore[arg-type]
                archive_location=d.archive_location or "",
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in designs
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post(
    "/archives/designs/{design_id}/restore",
    response_model=RestoreDesignResponse,
    status_code=status.HTTP_200_OK,
)
async def restore_archived_design(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RestoreDesignResponse:
    """Restore an archived design from cold storage.

    Copies design files back from the archives bucket to the designs
    bucket and resets the design status. Requires admin authentication.
    """
    service = DesignArchiveService(db)
    try:
        design = await service.restore_design(design_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return RestoreDesignResponse(
        id=design.id,
        name=design.name,
        status=design.status,
        restored_at=datetime.now(tz=UTC),
    )


@router.delete(
    "/archives/designs/{design_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_archived_design(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete an archived design and its storage files.

    This action cannot be undone. Requires admin authentication.
    """
    service = DesignArchiveService(db)
    try:
        await service.delete_archived_design(design_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
