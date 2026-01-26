"""
CAD generation endpoints.

Provides REST API for generating CAD files from natural language descriptions.
"""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings, Settings
from app.ai.parser import CADParameters, ShapeType
from app.ai.generator import generate_from_description, GenerationResult
from app.ai.exceptions import AIError, AIParseError, AIValidationError
from app.cad.exceptions import CADError
from app.cad.export import ExportQuality

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class GenerateRequest(BaseModel):
    """Request to generate CAD from description."""
    
    description: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language description of the part to generate",
        examples=[
            "Create a box 100mm long, 50mm wide, and 30mm tall",
            "Make a cylinder 2 inches in diameter and 4 inches tall with a center hole",
        ],
    )
    export_step: bool = Field(
        default=True,
        description="Whether to export STEP file",
    )
    export_stl: bool = Field(
        default=True,
        description="Whether to export STL file",
    )
    stl_quality: str = Field(
        default="standard",
        description="STL quality: draft, standard, high, ultra",
    )


class GenerateResponse(BaseModel):
    """Response from CAD generation."""
    
    job_id: str = Field(description="Unique job identifier")
    status: str = Field(description="Generation status")
    shape: str = Field(description="Generated shape type")
    confidence: float = Field(description="AI confidence score")
    dimensions: dict[str, float] = Field(description="Extracted dimensions in mm")
    warnings: list[str] = Field(default_factory=list, description="Generation warnings")
    timing: dict[str, float] = Field(description="Timing breakdown in ms")
    downloads: dict[str, str] = Field(description="Download URLs for generated files")
    
    # Assembly support
    is_assembly: bool = Field(default=False, description="Whether this is a multi-part assembly")
    parts: list[dict[str, Any]] = Field(default_factory=list, description="Individual parts in assembly")
    bom: list[dict[str, Any]] = Field(default_factory=list, description="Bill of materials for hardware")


class ParseRequest(BaseModel):
    """Request to parse description without generating."""
    
    description: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language description to parse",
    )


class ParseResponse(BaseModel):
    """Response from parsing description."""
    
    shape: str
    dimensions: dict[str, float]
    features: list[dict[str, Any]]
    units: str
    confidence: float
    assumptions: list[str]
    parse_time_ms: float


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str
    detail: str | None = None
    code: str | None = None


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/",
    response_model=GenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate CAD from description",
    description="Parse a natural language description and generate CAD files.",
    responses={
        201: {"description": "CAD files generated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid description or parameters"},
        422: {"model": ErrorResponse, "description": "Could not parse description"},
        500: {"model": ErrorResponse, "description": "Generation failed"},
        503: {"model": ErrorResponse, "description": "AI service unavailable"},
    },
)
async def generate_cad(
    request: GenerateRequest,
    settings: Settings = Depends(get_settings),
) -> GenerateResponse:
    """
    Generate CAD file from natural language description.
    
    This endpoint:
    1. Parses the description using AI to extract parameters
    2. Generates 3D geometry using CadQuery
    3. Exports to STEP and/or STL format
    4. Returns download URLs for the generated files
    
    Example:
        POST /api/v1/generate
        {
            "description": "Create a box 100mm x 50mm x 30mm with 3mm fillets"
        }
    """
    # Validate AI is configured (check for any provider)
    from app.ai.providers import get_ai_provider
    try:
        provider = get_ai_provider()
        if not provider.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"AI provider '{provider.name}' is not properly configured",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    
    # Validate STL quality
    try:
        stl_quality = ExportQuality(request.stl_quality.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stl_quality. Must be one of: draft, standard, high, ultra",
        )
    
    try:
        # Generate CAD
        result = await generate_from_description(
            request.description,
            export_step=request.export_step,
            export_stl=request.export_stl,
            stl_quality=stl_quality,
        )
        
        # Build download URLs (AI code generation always produces single parts)
        downloads = {}
        parts = []
        bom = []
        
        if result.step_path:
            downloads["step"] = f"/api/v1/generate/{result.job_id}/download/step"
        if result.stl_path:
            downloads["stl"] = f"/api/v1/generate/{result.job_id}/download/stl"
        
        return GenerateResponse(
            job_id=result.job_id,
            status="completed",
            shape=result.shape_type,
            confidence=result.confidence,
            dimensions=result.dimensions,
            warnings=result.warnings,
            timing={
                "parse_ms": result.parse_time_ms,
                "generate_ms": result.generate_time_ms,
                "export_ms": result.export_time_ms,
                "total_ms": result.total_time_ms,
            },
            downloads=downloads,
            is_assembly=False,  # AI code generation is single-part for now
            parts=parts,
            bom=bom,
        )
    
    except AIValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    except AIParseError as e:
        logger.warning(f"Parse error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse description: {e.message}",
        )
    
    except AIError as e:
        logger.error(f"AI error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service error: {e.message}",
        )
    
    except CADError as e:
        logger.error(f"CAD error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CAD generation failed: {str(e)}",
        )


@router.get(
    "/{job_id}/download/{file_format}",
    summary="Download generated CAD file",
    description="Download a generated STEP or STL file by job ID.",
    responses={
        200: {"description": "File content"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
)
async def download_generated_file(
    job_id: str,
    file_format: Literal["step", "stl"],
) -> FileResponse:
    """
    Download a generated CAD file.
    
    Files are stored temporarily after generation and can be downloaded
    using the job ID returned from the generate endpoint.
    
    Args:
        job_id: The job ID from generation
        file_format: The format to download (step or stl)
    
    Returns:
        The file content with appropriate content type
    """
    # Find the file in the temp export directory
    output_path = Path(tempfile.gettempdir()) / "cad_exports"
    
    # Search for file matching the job_id pattern
    pattern = f"*_{job_id[:8]}.{file_format}"
    matching_files = list(output_path.glob(pattern))
    
    if not matching_files:
        logger.warning(f"File not found for job {job_id}, format {file_format}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found for job {job_id}",
        )
    
    file_path = matching_files[0]
    
    # Determine content type
    if file_format == "step":
        media_type = "application/STEP"
        filename = f"part_{job_id[:8]}.step"
    else:
        media_type = "application/sla"
        filename = f"part_{job_id[:8]}.stl"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/{job_id}/download/{file_format}/{part_name}",
    summary="Download assembly part CAD file",
    description="Download a specific part from a generated assembly.",
    responses={
        200: {"description": "File content"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
)
async def download_assembly_part(
    job_id: str,
    file_format: Literal["step", "stl"],
    part_name: str,
) -> FileResponse:
    """
    Download a specific part from an assembly.
    
    Args:
        job_id: The job ID from generation
        file_format: The format to download (step or stl)
        part_name: The part name (e.g., 'enclosure_base', 'enclosure_lid')
    
    Returns:
        The file content with appropriate content type
    """
    output_path = Path(tempfile.gettempdir()) / "cad_exports"
    
    # Search for file matching the part name and job_id
    pattern = f"{part_name}_{job_id[:8]}.{file_format}"
    file_path = output_path / pattern
    
    if not file_path.exists():
        # Try alternate pattern
        alt_pattern = f"*{part_name}*_{job_id[:8]}.{file_format}"
        matching_files = list(output_path.glob(alt_pattern))
        if not matching_files:
            logger.warning(f"Part file not found: {pattern}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Part '{part_name}' not found for job {job_id}",
            )
        file_path = matching_files[0]
    
    # Determine content type
    if file_format == "step":
        media_type = "application/STEP"
        filename = f"{part_name}_{job_id[:8]}.step"
    else:
        media_type = "application/sla"
        filename = f"{part_name}_{job_id[:8]}.stl"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post(
    "/parse",
    response_model=ParseResponse,
    summary="Parse description only",
    description="Parse a description without generating CAD files.",
)
async def parse_description_only(
    request: ParseRequest,
    settings: Settings = Depends(get_settings),
) -> ParseResponse:
    """
    Parse a natural language description to preview extracted parameters.
    
    Useful for:
    - Validating a description before generation
    - Showing users what the AI understood
    - Debugging parsing issues
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured",
        )
    
    try:
        from app.ai.parser import parse_description
        
        result = await parse_description(request.description)
        
        return ParseResponse(
            shape=result.parameters.shape.value,
            dimensions=result.parameters.dimensions,
            features=[
                {"type": f.type.value, "parameters": f.parameters}
                for f in result.parameters.features
            ],
            units=result.parameters.units,
            confidence=result.parameters.confidence,
            assumptions=result.parameters.assumptions,
            parse_time_ms=result.parse_time_ms,
        )
    
    except AIValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    except AIParseError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse: {e.message}",
        )


@router.get(
    "/shapes",
    summary="List supported shapes",
    description="Get list of supported primitive shapes.",
)
async def list_shapes() -> dict[str, Any]:
    """Return list of supported shape types."""
    return {
        "shapes": [
            {
                "id": shape.value,
                "name": shape.value.title(),
                "required_dimensions": _get_required_dimensions(shape),
            }
            for shape in ShapeType
            if shape != ShapeType.CUSTOM
        ],
    }


@router.get(
    "/qualities",
    summary="List STL quality presets",
    description="Get list of available STL quality presets.",
)
async def list_qualities() -> dict[str, Any]:
    """Return list of STL quality presets."""
    return {
        "qualities": [
            {
                "id": quality.value,
                "name": quality.value.title(),
                "description": _get_quality_description(quality),
            }
            for quality in ExportQuality
        ],
    }


# =============================================================================
# Helpers
# =============================================================================

def _get_required_dimensions(shape: ShapeType) -> list[str]:
    """Get required dimensions for a shape type."""
    required = {
        ShapeType.BOX: ["length", "width", "height"],
        ShapeType.CYLINDER: ["radius OR diameter", "height"],
        ShapeType.SPHERE: ["radius OR diameter"],
        ShapeType.CONE: ["radius1 OR diameter1", "radius2 OR diameter2", "height"],
        ShapeType.TORUS: ["major_radius", "minor_radius"],
        ShapeType.WEDGE: ["length", "width", "height"],
    }
    return required.get(shape, [])


def _get_quality_description(quality: ExportQuality) -> str:
    """Get description for quality preset."""
    descriptions = {
        ExportQuality.DRAFT: "Fast preview, larger facets",
        ExportQuality.STANDARD: "Balanced quality and file size",
        ExportQuality.HIGH: "Fine detail for 3D printing",
        ExportQuality.ULTRA: "Maximum detail, slower export",
    }
    return descriptions.get(quality, "")
