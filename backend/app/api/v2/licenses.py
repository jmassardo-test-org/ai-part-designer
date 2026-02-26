"""
License API endpoints (Epic 13).

Provides the license type catalog and user-scoped license views.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.licenses import LICENSE_METADATA, LicenseType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User
from app.schemas.license import (
    LicenseTypeResponse,
    PaginatedPublishedLicensesResponse,
    PaginatedRemixedLicensesResponse,
)
from app.services.license_service import LicenseService

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# License Catalog
# =============================================================================


@router.get("/types", response_model=list[LicenseTypeResponse])
async def list_license_types() -> list[LicenseTypeResponse]:
    """List all supported license types with metadata.

    Returns the static license catalog. This endpoint is cacheable
    (Cache-Control: public, max-age=86400).
    """
    return [
        LicenseTypeResponse(
            spdx_id=info.spdx_id,
            name=info.name,
            url=info.url,
            allows_remix=info.allows_remix,
            requires_attribution=info.requires_attribution,
            allows_commercial=info.allows_commercial,
            requires_share_alike=info.requires_share_alike,
            icon=info.icon,
        )
        for lt, info in LICENSE_METADATA.items()
        if lt != LicenseType.CUSTOM  # CUSTOM metadata is not meaningful standalone
    ] + [
        # Add CUSTOM as last item with explicit defaults
        LicenseTypeResponse(
            spdx_id="CUSTOM",
            name="Custom License",
            url=None,
            allows_remix=False,
            requires_attribution=False,
            allows_commercial=False,
            requires_share_alike=False,
            icon="file-text",
        )
    ]


# =============================================================================
# User License Views
# =============================================================================


@router.get("/my/published", response_model=PaginatedPublishedLicensesResponse)
async def get_my_published_licenses(
    license_type: str | None = Query(None, description="Filter by license type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedPublishedLicensesResponse:
    """Get the current user's published designs with license information.

    Returns a paginated list of designs the user has published,
    including the license type and metadata for each.
    """
    service = LicenseService(db)
    return await service.get_user_published_licenses(
        user=current_user,
        license_type_filter=license_type,
        page=page,
        page_size=page_size,
    )


@router.get("/my/remixed", response_model=PaginatedRemixedLicensesResponse)
async def get_my_remixed_licenses(
    license_type: str | None = Query(None, description="Filter by parent license type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedRemixedLicensesResponse:
    """Get designs the current user has remixed, with parent license info.

    Returns a paginated list of remixed designs with the original
    design's license type and attribution requirements.
    """
    service = LicenseService(db)
    return await service.get_user_remixed_licenses(
        user=current_user,
        license_type_filter=license_type,
        page=page,
        page_size=page_size,
    )
