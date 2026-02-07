"""
Alignment API endpoints.

Provides endpoints for aligning and combining CAD files.
"""

from enum import StrEnum
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.design import Design
from app.models.user import User

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================


class Vector3(BaseModel):
    """3D vector for offsets and positions."""

    x: float = 0
    y: float = 0
    z: float = 0


class Matrix4x4(BaseModel):
    """4x4 transformation matrix (row-major)."""

    elements: list[float] = Field(..., min_length=16, max_length=16)


class FileAlignment(BaseModel):
    """A file with optional pre-transform."""

    id: UUID
    transform: Matrix4x4 | None = None


class AlignmentModeEnum(StrEnum):
    """Alignment modes available via API."""

    center = "center"
    origin = "origin"
    stack_z = "stack_z"
    stack_x = "stack_x"
    stack_y = "stack_y"
    side_by_side = "side_by_side"
    ground = "ground"


class AlignmentOptions(BaseModel):
    """Options for alignment operation."""

    offset: Vector3 = Field(default_factory=Vector3)
    gap: float = 0
    center_other_axes: bool = True
    align_bottoms: bool = True


class AlignmentRequest(BaseModel):
    """Request to align multiple files."""

    files: list[FileAlignment] = Field(..., min_length=1)
    alignment_mode: AlignmentModeEnum = AlignmentModeEnum.center
    options: AlignmentOptions = Field(default_factory=AlignmentOptions)


class BoundingBoxResponse(BaseModel):
    """Bounding box dimensions."""

    x_min: float
    y_min: float
    z_min: float
    x_max: float
    y_max: float
    z_max: float
    center: Vector3
    size: Vector3


class TransformResult(BaseModel):
    """Result of transforming a single file."""

    file_id: UUID
    translation: Vector3
    rotation: Vector3 | None = None
    original_bbox: BoundingBoxResponse | None = None
    final_bbox: BoundingBoxResponse | None = None


class AlignmentResponse(BaseModel):
    """Response from alignment operation."""

    preview_url: str
    combined_bbox: BoundingBoxResponse
    transforms: list[TransformResult]


class AlignmentPreviewResponse(BaseModel):
    """Preview-only response (transforms without saving)."""

    transforms: list[TransformResult]
    combined_bbox: BoundingBoxResponse


# ============================================================================
# Helper Functions
# ============================================================================


def bbox_to_response(bbox: Any) -> BoundingBoxResponse:
    """Convert internal BoundingBox to API response."""
    return BoundingBoxResponse(
        x_min=bbox.x_min,
        y_min=bbox.y_min,
        z_min=bbox.z_min,
        x_max=bbox.x_max,
        y_max=bbox.y_max,
        z_max=bbox.z_max,
        center=Vector3(x=bbox.center[0], y=bbox.center[1], z=bbox.center[2]),
        size=Vector3(x=bbox.size[0], y=bbox.size[1], z=bbox.size[2]),
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/preview", response_model=AlignmentPreviewResponse)
async def preview_alignment(
    request: AlignmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlignmentPreviewResponse:
    """
    Preview alignment transformations without saving.

    Returns the transformation matrices that would be applied.
    """
    # Verify all files belong to user
    file_ids = [f.id for f in request.files]
    result = await db.execute(
        select(Design).where(
            Design.id.in_(file_ids),
            Design.user_id == current_user.id,
        )
    )
    designs = result.scalars().all()

    if len(designs) != len(file_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="One or more files not found or not accessible",
        )

    # Create preview transforms based on alignment mode
    # For now, return placeholder transforms - actual CAD processing
    # would happen in a background job
    transforms = []
    for i, file in enumerate(request.files):
        # Calculate placeholder transform based on mode
        if request.alignment_mode == AlignmentModeEnum.stack_z:
            z_offset = i * (50 + request.options.gap)  # Placeholder stacking
            translation = Vector3(x=0, y=0, z=z_offset)
        elif request.alignment_mode == AlignmentModeEnum.stack_x:
            x_offset = i * (50 + request.options.gap)
            translation = Vector3(x=x_offset, y=0, z=0)
        elif request.alignment_mode == AlignmentModeEnum.side_by_side:
            x_offset = i * (60 + request.options.gap)
            translation = Vector3(x=x_offset, y=0, z=0)
        else:
            # Center/origin - apply user offset
            translation = Vector3(
                x=request.options.offset.x,
                y=request.options.offset.y,
                z=request.options.offset.z,
            )

        transforms.append(
            TransformResult(
                file_id=file.id,
                translation=translation,
                rotation=None,
            )
        )

    # Calculate combined bounding box (placeholder)
    combined_bbox = BoundingBoxResponse(
        x_min=0,
        y_min=0,
        z_min=0,
        x_max=100,
        y_max=100,
        z_max=50 * len(request.files),
        center=Vector3(x=50, y=50, z=25 * len(request.files)),
        size=Vector3(x=100, y=100, z=50 * len(request.files)),
    )

    return AlignmentPreviewResponse(
        transforms=transforms,
        combined_bbox=combined_bbox,
    )


@router.post("/", response_model=AlignmentResponse)
async def align_files(
    request: AlignmentRequest,
    _background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlignmentResponse:
    """
    Align multiple CAD files and generate combined preview.

    This creates a background job to process the alignment and
    returns immediately with a preview URL.
    """
    # Verify all files belong to user
    file_ids = [f.id for f in request.files]
    result = await db.execute(
        select(Design).where(
            Design.id.in_(file_ids),
            Design.user_id == current_user.id,
        )
    )
    designs = result.scalars().all()

    if len(designs) != len(file_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="One or more files not found or not accessible",
        )

    # For now, return preview data
    # Full implementation would:
    # 1. Load CAD files from storage
    # 2. Apply alignment using AlignmentService
    # 3. Export combined GLB for preview
    # 4. Store result

    preview = await preview_alignment(request, current_user, db)

    # Generate a temp preview URL (would be actual GLB in production)
    preview_url = f"/api/v1/files/preview/alignment-{file_ids[0]}.glb"

    return AlignmentResponse(
        preview_url=preview_url,
        combined_bbox=preview.combined_bbox,
        transforms=preview.transforms,
    )


@router.get("/modes")
async def get_alignment_modes() -> dict[str, Any]:
    """
    Get available alignment modes with descriptions.
    """
    return {
        "modes": [
            {
                "id": "center",
                "name": "Center Align",
                "description": "Align bounding box centers of all objects",
                "icon": "align-center",
            },
            {
                "id": "origin",
                "name": "Origin Align",
                "description": "Move all objects to origin",
                "icon": "crosshair",
            },
            {
                "id": "stack_z",
                "name": "Stack Vertical",
                "description": "Stack objects vertically (Z axis)",
                "icon": "layers",
            },
            {
                "id": "stack_x",
                "name": "Stack Horizontal",
                "description": "Stack objects horizontally (X axis)",
                "icon": "align-horizontal-distribute-center",
            },
            {
                "id": "side_by_side",
                "name": "Side by Side",
                "description": "Arrange objects in a row with gap",
                "icon": "columns",
            },
            {
                "id": "ground",
                "name": "Ground Align",
                "description": "Place all objects on Z=0 ground plane",
                "icon": "align-vertical-justify-end",
            },
        ]
    }


@router.post("/apply", response_model=dict)
async def apply_alignment(
    request: AlignmentRequest,
    _assembly_name: str = "Aligned Assembly",
    _assembly_description: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Apply alignment and save as a new assembly.
    """
    # Verify all files belong to user
    file_ids = [f.id for f in request.files]
    result = await db.execute(
        select(Design).where(
            Design.id.in_(file_ids),
            Design.user_id == current_user.id,
        )
    )
    designs = list(result.scalars().all())

    if len(designs) != len(file_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="One or more files not found or not accessible",
        )

    # TODO: Create assembly with aligned components
    # This would:
    # 1. Create new Assembly record
    # 2. Add AssemblyComponent for each file with transforms
    # 3. Generate combined export files

    return {
        "message": "Alignment applied successfully",
        "assembly_id": None,  # Would be actual ID
        "file_count": len(designs),
    }
