"""
CAD Modification API endpoints.

Provides REST API for modifying uploaded CAD files.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select

from app.api.deps import get_current_user
from app.cad.export import ExportQuality
from app.cad.modifier import CADModifier, ModifyOperation, OperationType
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.file import File as FileModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class OperationRequest(BaseModel):
    """A single modification operation."""

    type: str = Field(
        description="Operation type: translate, rotate, scale, mirror, fillet, chamfer, shell, add_hole"
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation parameters",
    )


class ModifyRequest(BaseModel):
    """Request to modify a file."""

    operations: list[OperationRequest] = Field(
        min_length=1,
        max_length=20,
        description="List of operations to apply in order",
    )
    output_format: str = Field(
        default="step",
        description="Output format: step or stl",
    )
    stl_quality: str = Field(
        default="standard",
        description="STL quality: draft, standard, high, ultra",
    )
    create_version: bool = Field(
        default=True,
        description="Whether to create a new version or overwrite",
    )


class CombineRequest(BaseModel):
    """Request to combine multiple files."""

    file_ids: list[UUID] = Field(
        min_length=1,
        max_length=10,
        description="Other file IDs to combine with",
    )
    operation: str = Field(
        default="union",
        description="Boolean operation: union, difference, intersection",
    )
    output_format: str = Field(
        default="step",
        description="Output format",
    )


class PreviewRequest(BaseModel):
    """Request to preview modifications without saving."""

    operations: list[OperationRequest]


class GeometryInfoResponse(BaseModel):
    """Geometry information."""

    volume: float
    area: float
    bounding_box: dict[str, float] | None = None
    center: dict[str, float] | None = None


class ModifyResponse(BaseModel):
    """Response after modifying a file."""

    file_id: str
    original_file_id: str
    operations_applied: list[str]
    geometry_info: GeometryInfoResponse
    download_url: str
    created_at: datetime


class PreviewResponse(BaseModel):
    """Response for modification preview."""

    operations_valid: bool
    geometry_info: GeometryInfoResponse | None = None
    stl_preview_url: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# =============================================================================
# Helper Functions
# =============================================================================


async def get_file_or_404(
    file_id: UUID,
    user: User,
    db: AsyncSession,
) -> FileModel:
    """Get file by ID or raise 404."""
    query = select(FileModel).where(
        and_(
            FileModel.id == file_id,
            FileModel.user_id == user.id,
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

    if not file_record.is_cad_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a CAD file",
        )

    return file_record


def parse_operations(operations: list[OperationRequest]) -> list[ModifyOperation]:
    """Convert request operations to ModifyOperation objects."""
    result = []

    for op in operations:
        try:
            op_type = OperationType(op.type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation type: {op.type}. Valid types: {[t.value for t in OperationType]}",
            )

        result.append(ModifyOperation(type=op_type, params=op.params))

    return result


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/{file_id}/modify",
    response_model=ModifyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Modify a CAD file",
    description="Apply modification operations to an uploaded CAD file.",
    responses={
        400: {"description": "Invalid operation or parameters"},
        404: {"description": "File not found"},
    },
)
async def modify_file(
    file_id: UUID,
    request: ModifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ModifyResponse:
    """
    Modify a CAD file with the specified operations.

    Operations are applied in order. A new version of the file is created.
    """
    # Get the file
    file_record = await get_file_or_404(file_id, current_user, db)

    # Parse operations
    operations = parse_operations(request.operations)

    # Load the CAD file
    file_path = Path(settings.UPLOAD_DIR) / file_record.storage_path

    modifier = CADModifier()

    try:
        # Load based on format
        if file_record.cad_format == "stl":
            shape = modifier.load_stl(file_path)
        else:
            shape = modifier.load_step(file_path)

        # Apply operations
        result = modifier.apply_operations(shape, operations)

        # Export to new file
        from uuid import uuid4

        new_file_id = uuid4()
        output_filename = f"modified.{request.output_format}"
        output_dir = Path(settings.UPLOAD_DIR) / f"users/{current_user.id}/{new_file_id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        # Get quality
        quality = ExportQuality(request.stl_quality.lower())

        modifier.export(
            result.shape,
            output_path,
            format=request.output_format,
            quality=quality,
        )

        # Create new file record
        new_file = FileModel(
            id=new_file_id,
            user_id=current_user.id,
            filename=output_filename,
            original_filename=f"modified_{file_record.original_filename}",
            mime_type="application/step" if request.output_format == "step" else "model/stl",
            size_bytes=output_path.stat().st_size,
            storage_bucket="uploads",
            storage_path=f"users/{current_user.id}/{new_file_id}/{output_filename}",
            file_type="cad",
            cad_format=request.output_format,
            status="ready",
            geometry_info=result.geometry_info,
        )

        db.add(new_file)
        await db.commit()

        logger.info(f"Modified file {file_id} -> {new_file_id}")

        return ModifyResponse(
            file_id=str(new_file_id),
            original_file_id=str(file_id),
            operations_applied=result.operations_applied,
            geometry_info=GeometryInfoResponse(**result.geometry_info),
            download_url=f"/api/v1/files/{new_file_id}/download",
            created_at=new_file.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Modification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{file_id}/preview",
    response_model=PreviewResponse,
    summary="Preview modifications",
    description="Preview modification results without saving.",
)
async def preview_modifications(
    file_id: UUID,
    request: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PreviewResponse:
    """
    Preview modification results.

    Returns geometry info and validation errors without saving.
    """
    # Get the file
    file_record = await get_file_or_404(file_id, current_user, db)

    # Parse and validate operations
    try:
        operations = parse_operations(request.operations)
    except HTTPException as e:
        return PreviewResponse(
            operations_valid=False,
            errors=[e.detail],
        )

    # Validate all operations
    all_errors = []
    for i, op in enumerate(operations):
        errors = op.validate()
        if errors:
            all_errors.extend([f"Operation {i + 1} ({op.type}): {e}" for e in errors])

    if all_errors:
        return PreviewResponse(
            operations_valid=False,
            errors=all_errors,
        )

    # Load and apply (without saving)
    file_path = Path(settings.UPLOAD_DIR) / file_record.storage_path
    modifier = CADModifier()

    try:
        if file_record.cad_format == "stl":
            shape = modifier.load_stl(file_path)
        else:
            shape = modifier.load_step(file_path)

        result = modifier.apply_operations(shape, operations)

        return PreviewResponse(
            operations_valid=True,
            geometry_info=GeometryInfoResponse(**result.geometry_info),
            warnings=result.warnings,
        )

    except Exception as e:
        return PreviewResponse(
            operations_valid=False,
            errors=[str(e)],
        )


@router.post(
    "/{file_id}/combine",
    response_model=ModifyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Combine multiple CAD files",
    description="Combine this file with other files using boolean operations.",
    responses={
        400: {"description": "Invalid files or operation"},
        404: {"description": "File not found"},
    },
)
async def combine_files(
    file_id: UUID,
    request: CombineRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ModifyResponse:
    """
    Combine multiple CAD files using boolean operations.

    Supported operations: union, difference, intersection.
    """
    # Validate operation
    if request.operation not in ["union", "difference", "intersection"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid operation. Must be: union, difference, or intersection",
        )

    # Get the base file
    base_file = await get_file_or_404(file_id, current_user, db)

    # Get all other files
    other_files = []
    for other_id in request.file_ids:
        other_file = await get_file_or_404(other_id, current_user, db)
        other_files.append(other_file)

    # Load all shapes
    modifier = CADModifier()
    shapes = []

    # Load base file
    base_path = Path(settings.UPLOAD_DIR) / base_file.storage_path
    if base_file.cad_format == "stl":
        shapes.append(modifier.load_stl(base_path))
    else:
        shapes.append(modifier.load_step(base_path))

    # Load other files
    for other_file in other_files:
        other_path = Path(settings.UPLOAD_DIR) / other_file.storage_path
        if other_file.cad_format == "stl":
            shapes.append(modifier.load_stl(other_path))
        else:
            shapes.append(modifier.load_step(other_path))

    try:
        # Combine shapes
        combined = modifier.combine_shapes(shapes, request.operation)
        result = modifier.ModifyResult.from_shape(  # type: ignore[attr-defined]
            combined, [f"{request.operation} of {len(shapes)} shapes"]
        )

        # Export
        from uuid import uuid4

        new_file_id = uuid4()
        output_filename = f"combined.{request.output_format}"
        output_dir = Path(settings.UPLOAD_DIR) / f"users/{current_user.id}/{new_file_id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename

        modifier.export(result.shape, output_path, format=request.output_format)

        # Create new file record
        new_file = FileModel(
            id=new_file_id,
            user_id=current_user.id,
            filename=output_filename,
            original_filename=f"combined_{base_file.original_filename}",
            mime_type="application/step" if request.output_format == "step" else "model/stl",
            size_bytes=output_path.stat().st_size,
            storage_bucket="uploads",
            storage_path=f"users/{current_user.id}/{new_file_id}/{output_filename}",
            file_type="cad",
            cad_format=request.output_format,
            status="ready",
            geometry_info=result.geometry_info,
        )

        db.add(new_file)
        await db.commit()

        logger.info(f"Combined {len(shapes)} files -> {new_file_id}")

        return ModifyResponse(
            file_id=str(new_file_id),
            original_file_id=str(file_id),
            operations_applied=result.operations_applied,
            geometry_info=GeometryInfoResponse(**result.geometry_info),
            download_url=f"/api/v1/files/{new_file_id}/download",
            created_at=new_file.created_at,
        )

    except Exception as e:
        logger.error(f"Combine failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{file_id}/geometry",
    response_model=GeometryInfoResponse,
    summary="Get geometry information",
    description="Get detailed geometry information about a CAD file.",
)
async def get_geometry_info(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GeometryInfoResponse:
    """
    Get geometry information for a CAD file.

    Returns volume, surface area, bounding box, etc.
    """
    file_record = await get_file_or_404(file_id, current_user, db)

    # Return cached geometry info if available
    if file_record.geometry_info:
        return GeometryInfoResponse(**file_record.geometry_info)

    # Load and calculate
    file_path = Path(settings.UPLOAD_DIR) / file_record.storage_path
    modifier = CADModifier()

    try:
        if file_record.cad_format == "stl":
            shape = modifier.load_stl(file_path)
        else:
            shape = modifier.load_step(file_path)

        result = modifier.ModifyResult.from_shape(shape, [])  # type: ignore[attr-defined]

        # Cache the result
        file_record.geometry_info = result.geometry_info
        await db.commit()

        return GeometryInfoResponse(**result.geometry_info)

    except Exception as e:
        logger.error(f"Failed to get geometry info: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to analyze geometry: {e}",
        )


# =============================================================================
# Alignment Endpoint
# =============================================================================


class AlignmentRequest(BaseModel):
    """Request to align multiple CAD files."""

    file_ids: list[UUID] = Field(
        min_length=2,
        max_length=10,
        description="IDs of files to align (first is reference)",
    )
    mode: str = Field(
        default="center",
        description="Alignment mode: center, face, edge, origin, stack_z, stack_x, stack_y",
    )
    gap: float = Field(
        default=0,
        ge=0,
        description="Gap between shapes for stacking modes (mm)",
    )
    output_format: str = Field(
        default="step",
        description="Output format: step or stl",
    )


class TransformationInfo(BaseModel):
    """Transformation applied to a shape."""

    file_id: UUID
    translation: tuple[float, float, float]
    rotation: tuple[float, float, float] | None = None
    original_center: tuple[float, float, float]
    final_center: tuple[float, float, float]


class AlignmentResponse(BaseModel):
    """Response after aligning files."""

    combined_file_id: UUID
    transformations: list[TransformationInfo]
    total_bounding_box: dict[str, float]
    download_url: str
    geometry_info: GeometryInfoResponse


@router.post(
    "/align",
    response_model=AlignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Align and combine CAD files",
    description="Align multiple CAD files using various alignment modes.",
)
async def align_files(
    request: AlignmentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AlignmentResponse:
    """
    Align multiple CAD files and combine them into a single file.

    Alignment modes:
    - center: Align bounding box centers
    - face: Place target on top of reference (face-to-face)
    - edge: Align left/bottom edges
    - origin: Move all shapes to origin
    - stack_z: Stack shapes vertically
    - stack_x: Arrange shapes side by side (X axis)
    - stack_y: Arrange shapes side by side (Y axis)
    """
    from uuid import uuid4

    from app.cad.alignment import AlignmentMode, AlignmentService

    # Validate alignment mode
    try:
        mode = AlignmentMode(request.mode)
    except ValueError:
        valid_modes = [m.value for m in AlignmentMode]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid alignment mode: {request.mode}. Valid modes: {valid_modes}",
        )

    # Load all files
    shapes = []
    file_records = []

    for file_id in request.file_ids:
        file_record = await get_file_or_404(file_id, current_user, db)
        file_records.append(file_record)

        file_path = Path(settings.UPLOAD_DIR) / file_record.storage_path

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found on disk: {file_id}",
            )

        modifier = CADModifier()
        try:
            if file_record.cad_format == "stl":
                shape = modifier.load_stl(file_path)
            else:
                shape = modifier.load_step(file_path)
            shapes.append(shape)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to load file {file_id}: {e}",
            )

    # Perform alignment
    service = AlignmentService()

    try:
        if len(shapes) == 2:
            result = service.align_shapes(shapes[0], shapes[1], mode, options={"gap": request.gap})
        else:
            # For more than 2 shapes, use stacking
            if mode in (AlignmentMode.STACK_X, AlignmentMode.STACK_Y, AlignmentMode.STACK_Z):
                from app.cad.alignment import AlignmentAxis

                axis_map = {
                    AlignmentMode.STACK_X: AlignmentAxis.X,
                    AlignmentMode.STACK_Y: AlignmentAxis.Y,
                    AlignmentMode.STACK_Z: AlignmentAxis.Z,
                }
                result = service.stack_shapes(shapes, axis=axis_map[mode], gap=request.gap)
            else:
                # Center all shapes on first
                current = shapes[0]
                all_transformations = []

                # First shape doesn't move
                bbox = service.get_bounding_box(current)
                from app.cad.alignment import TransformationResult

                all_transformations.append(
                    TransformationResult(
                        transformed_shape=current,
                        translation=(0, 0, 0),
                        original_bbox=bbox,
                        final_bbox=bbox,
                    )
                )

                for shape in shapes[1:]:
                    _, t_result = service.align_centers(current, shape)
                    all_transformations.append(t_result)
                    current = current.union(t_result.transformed_shape)

                total_bbox = service.get_bounding_box(current)
                from app.cad.alignment import AlignmentResult

                result = AlignmentResult(
                    combined_shape=current,
                    transformations=all_transformations,
                    total_bbox=total_bbox,
                )

        # Export combined shape
        import tempfile

        from app.cad.export import export_step, export_stl

        with tempfile.NamedTemporaryFile(
            suffix=f".{request.output_format}",
            delete=False,
        ) as tmp:
            output_path = Path(tmp.name)

        if request.output_format == "step":
            data = export_step(result.combined_shape)
            output_path.write_bytes(data)
        else:
            data = export_stl(result.combined_shape)
            output_path.write_bytes(data)

        # Create file record
        new_file_id = uuid4()
        storage_path = f"users/{current_user.id}/{new_file_id}/aligned.{request.output_format}"

        dest_dir = Path(settings.UPLOAD_DIR) / f"users/{current_user.id}/{new_file_id}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"aligned.{request.output_format}"

        import shutil

        shutil.move(str(output_path), str(dest_path))

        # Create geometry info
        modifier = CADModifier()
        geometry_result = modifier.ModifyResult.from_shape(result.combined_shape, [])  # type: ignore[attr-defined]

        # Create file record
        new_file = FileModel(
            id=new_file_id,
            user_id=current_user.id,
            filename=f"aligned.{request.output_format}",
            original_filename=f"aligned-{len(request.file_ids)}-files.{request.output_format}",
            mime_type="application/step" if request.output_format == "step" else "application/sla",
            size_bytes=dest_path.stat().st_size,
            storage_bucket="uploads",
            storage_path=storage_path,
            file_type="cad",
            cad_format=request.output_format,
            status="ready",
            geometry_info=geometry_result.geometry_info,
        )

        db.add(new_file)
        await db.commit()

        # Build transformation info
        transformation_infos = []
        for _i, (file_id, t) in enumerate(
            zip(request.file_ids, result.transformations, strict=False)
        ):
            transformation_infos.append(
                TransformationInfo(
                    file_id=file_id,
                    translation=t.translation,
                    rotation=t.rotation,
                    original_center=t.original_bbox.center if t.original_bbox else (0, 0, 0),
                    final_center=t.final_bbox.center if t.final_bbox else (0, 0, 0),
                )
            )

        return AlignmentResponse(
            combined_file_id=new_file_id,
            transformations=transformation_infos,
            total_bounding_box={
                "x_min": result.total_bbox.x_min,
                "y_min": result.total_bbox.y_min,
                "z_min": result.total_bbox.z_min,
                "x_max": result.total_bbox.x_max,
                "y_max": result.total_bbox.y_max,
                "z_max": result.total_bbox.z_max,
            },
            download_url=f"/api/v1/files/{new_file_id}/download",
            geometry_info=GeometryInfoResponse(**geometry_result.geometry_info),
        )

    except Exception as e:
        logger.error(f"Alignment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alignment failed: {e}",
        )


# =============================================================================
# Mounting Generation Models
# =============================================================================


class SnapFitRequest(BaseModel):
    """Request to generate a snap-fit clip."""

    length: float = Field(default=15.0, ge=5.0, le=50.0, description="Beam length in mm")
    width: float = Field(default=8.0, ge=3.0, le=30.0, description="Clip width in mm")
    thickness: float = Field(default=2.0, ge=1.0, le=5.0, description="Base thickness in mm")
    hook_height: float = Field(default=2.5, ge=1.0, le=8.0, description="Hook height in mm")
    include_receptacle: bool = Field(default=False, description="Generate matching receptacle")


class DINRailMountRequest(BaseModel):
    """Request to generate a DIN rail mount."""

    mount_width: float = Field(default=50.0, ge=20.0, le=200.0, description="Mount width in mm")
    mount_height: float = Field(default=30.0, ge=15.0, le=100.0, description="Mount height in mm")
    mount_thickness: float = Field(
        default=3.0, ge=2.0, le=10.0, description="Mount thickness in mm"
    )


class WallMountRequest(BaseModel):
    """Request to generate a wall mount bracket."""

    bracket_width: float = Field(default=40.0, ge=20.0, le=150.0, description="Bracket width in mm")
    bracket_height: float = Field(
        default=25.0, ge=15.0, le=100.0, description="Wall plate height in mm"
    )
    bracket_depth: float = Field(default=20.0, ge=10.0, le=80.0, description="Shelf depth in mm")
    keyhole_count: int = Field(default=2, ge=1, le=4, description="Number of keyhole slots")
    keyhole_spacing: float = Field(
        default=30.0, ge=15.0, le=100.0, description="Keyhole spacing in mm"
    )
    add_ribs: bool = Field(default=True, description="Add stiffener ribs")


class PCBStandoffRequest(BaseModel):
    """Request to generate PCB standoffs."""

    height: float = Field(default=10.0, ge=3.0, le=50.0, description="Standoff height in mm")
    screw_size: str = Field(default="M3", description="Metric screw size (M2, M2.5, M3, M4)")
    hex_outer: bool = Field(default=False, description="Use hex shape instead of round")
    count: int = Field(default=4, ge=1, le=20, description="Number of standoffs in array")
    spacing_x: float = Field(default=50.0, ge=10.0, le=200.0, description="X spacing in mm")
    spacing_y: float = Field(default=50.0, ge=10.0, le=200.0, description="Y spacing in mm")


class MountingResponse(BaseModel):
    """Response from mounting generation."""

    file_id: UUID
    mounting_type: str
    download_url: str
    geometry_info: GeometryInfoResponse
    metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Mounting Generation Endpoints
# =============================================================================


@router.post("/mounting/snap-fit", response_model=MountingResponse)
async def generate_snap_fit(
    request: SnapFitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> MountingResponse:
    """
    Generate a snap-fit clip.

    Creates a cantilever-style snap-fit clip suitable for 3D printing.
    Optionally includes a matching receptacle.
    """
    from uuid import uuid4

    from app.cad.export import export_step
    from app.cad.mounting import SnapFitConfig, SnapFitGenerator, create_snap_fit

    try:
        # Generate snap-fit
        result = create_snap_fit(
            length=request.length,
            width=request.width,
            thickness=request.thickness,
            hook_height=request.hook_height,
        )

        shape = result.clip

        # If receptacle requested, combine them
        if request.include_receptacle:
            config = SnapFitConfig(
                length=request.length,
                width=request.width,
                thickness=request.thickness,
                hook_height=request.hook_height,
            )
            receptacle = SnapFitGenerator(config).generate_receptacle()
            # Position receptacle next to clip
            receptacle = receptacle.translate((request.width * 2, 0, 0))
            shape = shape.union(receptacle)

        # Export and save
        new_file_id = uuid4()
        storage_path = f"users/{current_user.id}/{new_file_id}/snap_fit.step"

        dest_dir = Path(settings.UPLOAD_DIR) / f"users/{current_user.id}/{new_file_id}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "snap_fit.step"

        step_data = export_step(shape, product_name="Snap-Fit Clip")
        dest_path.write_bytes(step_data)

        # Get geometry info
        modifier = CADModifier()
        geometry_result = modifier.ModifyResult.from_shape(shape, [])  # type: ignore[attr-defined]

        # Create file record
        new_file = FileModel(
            id=new_file_id,
            user_id=current_user.id,
            filename="snap_fit.step",
            original_filename="snap_fit.step",
            mime_type="application/step",
            size_bytes=len(step_data),
            storage_bucket="uploads",
            storage_path=storage_path,
            file_type="cad",
            cad_format="step",
            status="ready",
            geometry_info=geometry_result.geometry_info,
        )

        db.add(new_file)
        await db.commit()

        return MountingResponse(
            file_id=new_file_id,
            mounting_type="snap_fit",
            download_url=f"/api/v1/files/{new_file_id}/download",
            geometry_info=GeometryInfoResponse(**geometry_result.geometry_info),
            metadata={
                "estimated_retention_force_n": result.estimated_retention_force,
                "max_deflection_mm": result.max_deflection,
            },
        )

    except Exception as e:
        logger.error(f"Snap-fit generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Snap-fit generation failed: {e}",
        )


@router.post("/mounting/din-rail", response_model=MountingResponse)
async def generate_din_rail_mount(
    request: DINRailMountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> MountingResponse:
    """
    Generate a DIN rail mounting adapter.

    Creates a mount compatible with standard 35mm TS (top-hat) DIN rails
    commonly used in industrial control panels.
    """
    from uuid import uuid4

    from app.cad.export import export_step
    from app.cad.mounting import create_din_rail_mount

    try:
        result = create_din_rail_mount(
            mount_width=request.mount_width,
            mount_height=request.mount_height,
            mount_thickness=request.mount_thickness,
        )

        # Export and save
        new_file_id = uuid4()
        storage_path = f"users/{current_user.id}/{new_file_id}/din_rail_mount.step"

        dest_dir = Path(settings.UPLOAD_DIR) / f"users/{current_user.id}/{new_file_id}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "din_rail_mount.step"

        step_data = export_step(result.mount, product_name="DIN Rail Mount")
        dest_path.write_bytes(step_data)

        # Get geometry info
        modifier = CADModifier()
        geometry_result = modifier.ModifyResult.from_shape(result.mount, [])  # type: ignore[attr-defined]

        # Create file record
        new_file = FileModel(
            id=new_file_id,
            user_id=current_user.id,
            filename="din_rail_mount.step",
            original_filename="din_rail_mount.step",
            mime_type="application/step",
            size_bytes=len(step_data),
            storage_bucket="uploads",
            storage_path=storage_path,
            file_type="cad",
            cad_format="step",
            status="ready",
            geometry_info=geometry_result.geometry_info,
        )

        db.add(new_file)
        await db.commit()

        return MountingResponse(
            file_id=new_file_id,
            mounting_type="din_rail",
            download_url=f"/api/v1/files/{new_file_id}/download",
            geometry_info=GeometryInfoResponse(**geometry_result.geometry_info),
            metadata={
                "rail_compatibility": result.rail_compatibility,
                **result.metadata,
            },
        )

    except Exception as e:
        logger.error(f"DIN rail mount generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DIN rail mount generation failed: {e}",
        )


@router.post("/mounting/wall-mount", response_model=MountingResponse)
async def generate_wall_mount(
    request: WallMountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> MountingResponse:
    """
    Generate a wall mounting bracket.

    Creates an L-bracket with keyhole slots for easy wall installation.
    Includes optional stiffener ribs for added strength.
    """
    from uuid import uuid4

    from app.cad.export import export_step
    from app.cad.mounting import create_wall_mount

    try:
        result = create_wall_mount(
            bracket_width=request.bracket_width,
            bracket_height=request.bracket_height,
            bracket_depth=request.bracket_depth,
            keyhole_count=request.keyhole_count,
            keyhole_spacing=request.keyhole_spacing,
            add_ribs=request.add_ribs,
        )

        # Export and save
        new_file_id = uuid4()
        storage_path = f"users/{current_user.id}/{new_file_id}/wall_mount.step"

        dest_dir = Path(settings.UPLOAD_DIR) / f"users/{current_user.id}/{new_file_id}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "wall_mount.step"

        step_data = export_step(result.bracket, product_name="Wall Mount Bracket")
        dest_path.write_bytes(step_data)

        # Get geometry info
        modifier = CADModifier()
        geometry_result = modifier.ModifyResult.from_shape(result.bracket, [])  # type: ignore[attr-defined]

        # Create file record
        new_file = FileModel(
            id=new_file_id,
            user_id=current_user.id,
            filename="wall_mount.step",
            original_filename="wall_mount.step",
            mime_type="application/step",
            size_bytes=len(step_data),
            storage_bucket="uploads",
            storage_path=storage_path,
            file_type="cad",
            cad_format="step",
            status="ready",
            geometry_info=geometry_result.geometry_info,
        )

        db.add(new_file)
        await db.commit()

        return MountingResponse(
            file_id=new_file_id,
            mounting_type="wall_mount",
            download_url=f"/api/v1/files/{new_file_id}/download",
            geometry_info=GeometryInfoResponse(**geometry_result.geometry_info),
            metadata={
                "recommended_screws": result.recommended_screws,
                "recommended_anchors": result.recommended_anchors,
                **result.metadata,
            },
        )

    except Exception as e:
        logger.error(f"Wall mount generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Wall mount generation failed: {e}",
        )


@router.post("/mounting/pcb-standoffs", response_model=MountingResponse)
async def generate_pcb_standoffs(
    request: PCBStandoffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> MountingResponse:
    """
    Generate PCB standoffs.

    Creates an array of standoffs for mounting circuit boards.
    Supports round or hex profiles and various screw sizes.
    """
    from uuid import uuid4

    from app.cad.export import export_step
    from app.cad.mounting import PCBStandoffConfig, PCBStandoffGenerator

    try:
        # Calculate positions for array
        positions = []
        cols = 2 if request.count >= 4 else 1
        rows = (request.count + cols - 1) // cols

        for row in range(rows):
            for col in range(cols):
                if row * cols + col >= request.count:
                    break
                x = col * request.spacing_x - (cols - 1) * request.spacing_x / 2
                y = row * request.spacing_y - (rows - 1) * request.spacing_y / 2
                positions.append((x, y))

        # Map screw size to dimensions
        screw_dims = {
            "M2": (4.0, 2.2),
            "M2.5": (5.0, 2.7),
            "M3": (6.0, 3.2),
            "M4": (8.0, 4.2),
        }
        outer, inner = screw_dims.get(request.screw_size, (6.0, 3.2))

        config = PCBStandoffConfig(
            height=request.height,
            outer_diameter=outer,
            inner_diameter=inner,
            base_diameter=outer + 2,
            screw_size=request.screw_size,
            hex_outer=request.hex_outer,
        )

        generator = PCBStandoffGenerator(config)
        standoffs = generator.generate_array(positions)

        # Combine all standoffs using Build123d fuse
        combined = standoffs[0]
        for standoff in standoffs[1:]:
            combined = combined.fuse(standoff)  # type: ignore[assignment]

        # Export and save
        new_file_id = uuid4()
        storage_path = f"users/{current_user.id}/{new_file_id}/pcb_standoffs.step"

        dest_dir = Path(settings.UPLOAD_DIR) / f"users/{current_user.id}/{new_file_id}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "pcb_standoffs.step"

        step_data = export_step(combined, product_name="PCB Standoffs")
        dest_path.write_bytes(step_data)

        # Get geometry info
        modifier = CADModifier()
        geometry_result = modifier.ModifyResult.from_shape(combined, [])  # type: ignore[attr-defined]

        # Create file record
        new_file = FileModel(
            id=new_file_id,
            user_id=current_user.id,
            filename="pcb_standoffs.step",
            original_filename="pcb_standoffs.step",
            mime_type="application/step",
            size_bytes=len(step_data),
            storage_bucket="uploads",
            storage_path=storage_path,
            file_type="cad",
            cad_format="step",
            status="ready",
            geometry_info=geometry_result.geometry_info,
        )

        db.add(new_file)
        await db.commit()

        return MountingResponse(
            file_id=new_file_id,
            mounting_type="pcb_standoffs",
            download_url=f"/api/v1/files/{new_file_id}/download",
            geometry_info=GeometryInfoResponse(**geometry_result.geometry_info),
            metadata={
                "count": request.count,
                "positions": positions,
                "screw_size": request.screw_size,
            },
        )

    except Exception as e:
        logger.error(f"PCB standoff generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PCB standoff generation failed: {e}",
        )
