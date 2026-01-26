"""
CAD Modification API endpoints.

Provides REST API for modifying uploaded CAD files.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings, Settings
from app.models.file import File as FileModel
from app.models.user import User
from app.api.deps import get_current_user
from app.cad.modifier import CADModifier, ModifyOperation, OperationType
from app.cad.export import ExportQuality

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
            FileModel.is_deleted == False,
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
            all_errors.extend([f"Operation {i+1} ({op.type}): {e}" for e in errors])
    
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
            detail=f"Invalid operation. Must be: union, difference, or intersection",
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
        result = modifier.ModifyResult.from_shape(combined, [f"{request.operation} of {len(shapes)} shapes"])
        
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
        
        result = modifier.ModifyResult.from_shape(shape, [])
        
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
