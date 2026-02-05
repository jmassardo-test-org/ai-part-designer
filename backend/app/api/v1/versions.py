"""
Version History API.

Provides endpoints for design version management:
- List version history
- Get version details
- Restore previous version
- Compare versions
- Get version diff
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.design import Design, DesignVersion
from app.models.user import User

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class VersionSummary(BaseModel):
    """Summary info for a design version."""

    id: UUID
    version_number: int
    created_at: datetime
    created_by_name: str | None = None
    change_description: str | None = None
    file_url: str
    thumbnail_url: str | None = None
    geometry_info: dict[str, Any] = Field(default_factory=dict[str, Any])

    class Config:
        from_attributes = True


class VersionDetail(VersionSummary):
    """Full version details including parameters and formats."""

    parameters: dict[str, Any] = Field(default_factory=dict[str, Any])
    file_formats: dict[str, Any] = Field(default_factory=dict[str, Any])


class VersionListResponse(BaseModel):
    """Paginated version list response."""

    versions: list[VersionSummary]
    total: int
    page: int
    page_size: int


class RestoreVersionRequest(BaseModel):
    """Request to restore a version."""

    description: str | None = Field(
        default=None,
        description="Optional description for the restoration",
        max_length=500,
    )


class RestoreVersionResponse(BaseModel):
    """Response after restoring a version."""

    new_version_id: UUID
    new_version_number: int
    restored_from_version: int
    message: str


class VersionComparisonResponse(BaseModel):
    """Response comparing two versions."""

    version_a: VersionSummary
    version_b: VersionSummary
    parameter_diff: dict[str, Any]
    geometry_diff: dict[str, Any]


class VersionDiffItem(BaseModel):
    """Single diff item between versions."""

    field: str
    old_value: str | float | int | bool | None
    new_value: str | float | int | bool | None
    change_type: str  # "added", "removed", "modified"


class VersionDiffResponse(BaseModel):
    """Detailed diff between two versions."""

    from_version: int
    to_version: int
    parameter_changes: list[VersionDiffItem]
    geometry_changes: list[VersionDiffItem]
    summary: str


# =============================================================================
# Helper Functions
# =============================================================================


async def get_design_or_404(
    design_id: UUID,
    db: AsyncSession,
    user: User,
) -> Design:
    """Get design with ownership check."""
    query = select(Design).where(Design.id == design_id).where(Design.deleted_at.is_(None))
    result = await db.execute(query)
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    # Check ownership or share access
    if design.project.user_id != user.id:
        # TODO: Check for share access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return design


async def get_version_or_404(
    version_id: UUID,
    db: AsyncSession,
    user: User,
) -> DesignVersion:
    """Get version with ownership check."""
    query = (
        select(DesignVersion)
        .options(selectinload(DesignVersion.design))
        .where(DesignVersion.id == version_id)
    )
    result = await db.execute(query)
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    # Check ownership through design
    design = version.design
    if design.project.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return version


def compute_dict_diff(
    old_dict: dict[str, Any],
    new_dict: dict[str, Any],
    prefix: str = "",
) -> list[VersionDiffItem]:
    """Compute differences between two dictionaries."""
    changes = []
    all_keys = set(old_dict.keys()) | set(new_dict.keys())

    for key in all_keys:
        field = f"{prefix}{key}" if prefix else key
        old_val = old_dict.get(key)
        new_val = new_dict.get(key)

        if key not in old_dict:
            changes.append(
                VersionDiffItem(
                    field=field,
                    old_value=None,
                    new_value=new_val,
                    change_type="added",
                )
            )
        elif key not in new_dict:
            changes.append(
                VersionDiffItem(
                    field=field,
                    old_value=old_val,
                    new_value=None,
                    change_type="removed",
                )
            )
        elif old_val != new_val:
            # Recurse for nested dicts
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                changes.extend(compute_dict_diff(old_val, new_val, f"{field}."))
            else:
                changes.append(
                    VersionDiffItem(
                        field=field,
                        old_value=old_val,
                        new_value=new_val,
                        change_type="modified",
                    )
                )

    return changes


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/designs/{design_id}/versions",
    response_model=VersionListResponse,
    summary="List version history",
    description="Get paginated list of all versions for a design.",
)
async def list_versions(
    design_id: UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VersionListResponse:
    """List all versions of a design."""
    # Verify access
    await get_design_or_404(design_id, db, current_user)

    # Count total
    count_query = (
        select(func.count()).select_from(DesignVersion).where(DesignVersion.design_id == design_id)
    )
    total = (await db.execute(count_query)).scalar_one()

    # Fetch versions
    offset = (page - 1) * page_size
    query = (
        select(DesignVersion)
        .options(selectinload(DesignVersion.creator))
        .where(DesignVersion.design_id == design_id)
        .order_by(DesignVersion.version_number.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    versions = result.scalars().all()

    return VersionListResponse(
        versions=[
            VersionSummary(
                id=v.id,
                version_number=v.version_number,
                created_at=v.created_at,
                created_by_name=v.creator.display_name if v.creator else None,
                change_description=v.change_description,
                file_url=v.file_url,
                thumbnail_url=v.thumbnail_url,
                geometry_info=v.geometry_info,
            )
            for v in versions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/versions/{version_id}",
    response_model=VersionDetail,
    summary="Get version details",
    description="Get full details for a specific version.",
)
async def get_version(
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VersionDetail:
    """Get detailed version information."""
    version = await get_version_or_404(version_id, db, current_user)

    return VersionDetail(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        created_by_name=version.creator.display_name if version.creator else None,
        change_description=version.change_description,
        file_url=version.file_url,
        thumbnail_url=version.thumbnail_url,
        geometry_info=version.geometry_info,
        parameters=version.parameters,
        file_formats=version.file_formats,
    )


@router.post(
    "/versions/{version_id}/restore",
    response_model=RestoreVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Restore version",
    description="Restore a previous version as the new current version.",
)
async def restore_version(
    version_id: UUID,
    request: RestoreVersionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RestoreVersionResponse:
    """Restore a previous version, creating a new version."""
    version = await get_version_or_404(version_id, db, current_user)
    design = version.design

    # Get the latest version number
    latest_query = select(func.max(DesignVersion.version_number)).where(
        DesignVersion.design_id == design.id
    )
    latest_num = (await db.execute(latest_query)).scalar_one() or 0

    # Create new version as copy of restored version
    new_version = DesignVersion(
        design_id=design.id,
        created_by=current_user.id,
        version_number=latest_num + 1,
        file_url=version.file_url,
        thumbnail_url=version.thumbnail_url,
        file_formats=version.file_formats,
        parameters=version.parameters,
        geometry_info=version.geometry_info,
        change_description=request.description or f"Restored from version {version.version_number}",
    )

    db.add(new_version)

    # Update design to point to new version
    design.current_version_id = new_version.id
    design.updated_at = func.now()

    await db.commit()
    await db.refresh(new_version)

    return RestoreVersionResponse(
        new_version_id=new_version.id,
        new_version_number=new_version.version_number,
        restored_from_version=version.version_number,
        message=f"Successfully restored version {version.version_number} as version {new_version.version_number}",
    )


@router.get(
    "/designs/{design_id}/versions/compare",
    response_model=VersionComparisonResponse,
    summary="Compare versions",
    description="Compare two versions of a design side-by-side.",
)
async def compare_versions(
    design_id: UUID,
    version_a: Annotated[int, Query(description="First version number")],
    version_b: Annotated[int, Query(description="Second version number")],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VersionComparisonResponse:
    """Compare two versions of a design."""
    # Verify access
    await get_design_or_404(design_id, db, current_user)

    # Fetch both versions
    query = (
        select(DesignVersion)
        .options(selectinload(DesignVersion.creator))
        .where(DesignVersion.design_id == design_id)
        .where(DesignVersion.version_number.in_([version_a, version_b]))
    )
    result = await db.execute(query)
    versions = {v.version_number: v for v in result.scalars().all()}

    if version_a not in versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_a} not found",
        )
    if version_b not in versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_b} not found",
        )

    v_a = versions[version_a]
    v_b = versions[version_b]

    # Compute parameter differences
    param_diff = {}
    all_params = set(v_a.parameters.keys()) | set(v_b.parameters.keys())
    for key in all_params:
        val_a = v_a.parameters.get(key)
        val_b = v_b.parameters.get(key)
        if val_a != val_b:
            param_diff[key] = {"version_a": val_a, "version_b": val_b}

    # Compute geometry differences
    geo_diff = {}
    for key in ["volume", "surfaceArea", "triangleCount"]:
        val_a = v_a.geometry_info.get(key)
        val_b = v_b.geometry_info.get(key)
        if val_a != val_b:
            geo_diff[key] = {"version_a": val_a, "version_b": val_b}

    return VersionComparisonResponse(
        version_a=VersionSummary(
            id=v_a.id,
            version_number=v_a.version_number,
            created_at=v_a.created_at,
            created_by_name=v_a.creator.display_name if v_a.creator else None,
            change_description=v_a.change_description,
            file_url=v_a.file_url,
            thumbnail_url=v_a.thumbnail_url,
            geometry_info=v_a.geometry_info,
        ),
        version_b=VersionSummary(
            id=v_b.id,
            version_number=v_b.version_number,
            created_at=v_b.created_at,
            created_by_name=v_b.creator.display_name if v_b.creator else None,
            change_description=v_b.change_description,
            file_url=v_b.file_url,
            thumbnail_url=v_b.thumbnail_url,
            geometry_info=v_b.geometry_info,
        ),
        parameter_diff=param_diff,
        geometry_diff=geo_diff,
    )


@router.get(
    "/designs/{design_id}/versions/diff",
    response_model=VersionDiffResponse,
    summary="Get version diff",
    description="Get detailed diff between two versions.",
)
async def get_version_diff(
    design_id: UUID,
    from_version: Annotated[int, Query(description="Source version number")],
    to_version: Annotated[int, Query(description="Target version number")],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VersionDiffResponse:
    """Get detailed diff between two versions."""
    # Verify access
    await get_design_or_404(design_id, db, current_user)

    # Fetch both versions
    query = (
        select(DesignVersion)
        .where(DesignVersion.design_id == design_id)
        .where(DesignVersion.version_number.in_([from_version, to_version]))
    )
    result = await db.execute(query)
    versions = {v.version_number: v for v in result.scalars().all()}

    if from_version not in versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {from_version} not found",
        )
    if to_version not in versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {to_version} not found",
        )

    v_from = versions[from_version]
    v_to = versions[to_version]

    # Compute diffs
    param_changes = compute_dict_diff(v_from.parameters, v_to.parameters)
    geo_changes = compute_dict_diff(v_from.geometry_info, v_to.geometry_info)

    # Build summary
    added = sum(1 for c in param_changes + geo_changes if c.change_type == "added")
    removed = sum(1 for c in param_changes + geo_changes if c.change_type == "removed")
    modified = sum(1 for c in param_changes + geo_changes if c.change_type == "modified")

    summary_parts = []
    if added:
        summary_parts.append(f"{added} added")
    if removed:
        summary_parts.append(f"{removed} removed")
    if modified:
        summary_parts.append(f"{modified} modified")

    summary = ", ".join(summary_parts) if summary_parts else "No changes"

    return VersionDiffResponse(
        from_version=from_version,
        to_version=to_version,
        parameter_changes=param_changes,
        geometry_changes=geo_changes,
        summary=summary,
    )


@router.get(
    "/designs/{design_id}/versions/latest",
    response_model=VersionDetail,
    summary="Get latest version",
    description="Get the latest (current) version of a design.",
)
async def get_latest_version(
    design_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VersionDetail:
    """Get the latest version of a design."""
    await get_design_or_404(design_id, db, current_user)

    # Get the latest version
    query = (
        select(DesignVersion)
        .options(selectinload(DesignVersion.creator))
        .where(DesignVersion.design_id == design_id)
        .order_by(DesignVersion.version_number.desc())
        .limit(1)
    )
    result = await db.execute(query)
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No versions found for this design",
        )

    return VersionDetail(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        created_by_name=version.creator.display_name if version.creator else None,
        change_description=version.change_description,
        file_url=version.file_url,
        thumbnail_url=version.thumbnail_url,
        geometry_info=version.geometry_info,
        parameters=version.parameters,
        file_formats=version.file_formats,
    )
