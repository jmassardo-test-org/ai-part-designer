"""
CAD generation endpoints.

Provides REST API for generating CAD files from natural language descriptions.

DEPRECATED: This v1 API is deprecated and will be removed in a future release.
Please migrate to /api/v2/generate/ for the new declarative schema-based CAD system.
See docs/cad-v1-to-v2-migration-guide.md for migration instructions.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.ai.exceptions import AIError, AIParseError, AIValidationError
from app.ai.generator import generate_from_description
from app.ai.parser import ShapeType
from app.api.deps import get_current_user_optional
from app.cad.exceptions import CADError
from app.cad.export import ExportQuality
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.job import Job

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Deprecation Helpers
# =============================================================================


def add_deprecation_headers(response: Response, settings: Settings) -> None:
    """Add deprecation headers to v1 CAD API responses.

    Follows RFC 8594 (Deprecation header) and Sunset header draft.

    Args:
        response: FastAPI Response object to add headers to.
        settings: Application settings for feature flag check.
    """
    if settings.CAD_V1_DEPRECATION_HEADERS:
        # RFC 8594 deprecation header with date
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "2025-06-01T00:00:00Z"
        response.headers["Link"] = '</api/v2/generate>; rel="successor-version"'
        response.headers["X-Deprecation-Notice"] = (
            "This API version is deprecated. "
            "Please migrate to /api/v2/generate/. "
            "See docs/cad-v1-to-v2-migration-guide.md"
        )


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
    export_solidworks: bool = Field(
        default=False,
        description="Whether to export SolidWorks-compatible STEP AP214 file",
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
    parts: list[dict[str, Any]] = Field(
        default_factory=list, description="Individual parts in assembly"
    )
    bom: list[dict[str, Any]] = Field(
        default_factory=list, description="Bill of materials for hardware"
    )


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
    "",
    response_model=GenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate CAD from description",
    description="[DEPRECATED] Parse a natural language description and generate CAD files. "
    "Please migrate to /api/v2/generate/ for the new declarative schema-based system.",
    responses={
        201: {"description": "CAD files generated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid description or parameters"},
        422: {"model": ErrorResponse, "description": "Could not parse description"},
        500: {"model": ErrorResponse, "description": "Generation failed"},
        503: {"model": ErrorResponse, "description": "AI service unavailable"},
    },
    deprecated=True,
)
async def generate_cad(
    request: GenerateRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> GenerateResponse:
    """
    Generate CAD file from natural language description.

    DEPRECATED: This endpoint is deprecated. Please use /api/v2/generate/ instead.

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
    # Add deprecation headers
    add_deprecation_headers(response, settings)

    # Route through v2 pipeline if enabled
    if settings.CAD_V2_ENABLED and settings.CAD_V2_AS_DEFAULT:
        return await _generate_via_v2(request, response, settings)

    # Legacy v1 pipeline below
    return await _generate_via_v1(request, response, settings)


async def _generate_via_v2(
    request: GenerateRequest,
    _response: Response,
    _settings: Settings,
) -> GenerateResponse:
    """Generate CAD using the v2 declarative schema pipeline.

    Converts v1 request to v2 format, processes through v2 pipeline,
    and converts response back to v1 format for backward compatibility.
    """
    import tempfile
    from uuid import uuid4

    from app.cad_v2.ai.schema_generator import SchemaGenerator
    from app.cad_v2.compiler.engine import CompilationEngine, ExportFormat

    job_id = str(uuid4())

    # Step 1: Generate schema from description
    generator = SchemaGenerator()

    try:
        result = await generator.generate(request.description)
    except Exception as e:
        logger.exception("V2 schema generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema generation failed: {e!s}",
        )

    # Handle clarification needed
    if result.clarification_needed:
        return GenerateResponse(
            job_id=job_id,
            status="needs_clarification",
            shape="unknown",
            confidence=0.0,
            dimensions={},
            warnings=[f"Clarification needed: {result.clarification_needed}"],
            timing={"total_ms": 0},
            downloads={},
        )

    # Handle validation errors
    if not result.success or result.spec is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse description: {', '.join(result.validation_errors or ['Unknown error'])}",
        )

    # Step 2: Compile to geometry
    engine = CompilationEngine()

    try:
        compilation = engine.compile_enclosure(result.spec)
    except Exception as e:
        logger.exception("V2 compilation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CAD generation failed: {e!s}",
        )

    if not compilation.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CAD generation failed: {', '.join(compilation.errors)}",
        )

    # Step 3: Export files
    export_format = ExportFormat.STL if request.export_stl else ExportFormat.STEP

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = compilation.export(tmpdir, export_format)

            # Build download URLs
            downloads = {}
            for p in paths:
                if p.suffix.lower() == ".step":
                    downloads["step"] = f"/api/v2/downloads/{job_id}/{p.name}"
                elif p.suffix.lower() == ".stl":
                    downloads["stl"] = f"/api/v2/downloads/{job_id}/{p.name}"
    except Exception as e:
        logger.exception("V2 export failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {e!s}",
        )

    # Extract dimensions from spec for v1 response format
    spec = result.spec
    dimensions = {
        "width": spec.exterior.width.mm,
        "depth": spec.exterior.depth.mm,
        "height": spec.exterior.height.mm,
    }

    return GenerateResponse(
        job_id=job_id,
        status="completed",
        shape="enclosure",
        confidence=0.95,  # V2 uses validated schema, high confidence
        dimensions=dimensions,
        warnings=result.warnings or [],
        timing={"total_ms": 0},  # TODO: Add timing
        downloads=downloads,
        is_assembly=len(compilation.parts) > 1,
        parts=[{"name": name} for name in compilation.parts],
        bom=[],
    )


async def _generate_via_v1(
    request: GenerateRequest,
    _response: Response,
    _settings: Settings,
) -> GenerateResponse:
    """Legacy v1 generation pipeline."""
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
            detail="Invalid stl_quality. Must be one of: draft, standard, high, ultra",
        )

    try:
        # Generate CAD
        result = await generate_from_description(
            request.description,
            export_step=request.export_step,
            export_stl=request.export_stl,
            export_solidworks=request.export_solidworks,
            stl_quality=stl_quality,
        )

        # Build download URLs (AI code generation always produces single parts)
        downloads = {}
        parts: list[dict[str, Any]] = []
        bom: list[dict[str, Any]] = []

        if result.step_path:
            downloads["step"] = f"/api/v1/generate/{result.job_id}/download/step"
        if result.stl_path:
            downloads["stl"] = f"/api/v1/generate/{result.job_id}/download/stl"
        if result.solidworks_path:
            downloads["solidworks"] = f"/api/v1/generate/{result.job_id}/download/solidworks"

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
            detail=f"CAD generation failed: {e!s}",
        )


@router.get(
    "/{job_id}/download/{file_format}",
    summary="Download generated CAD file",
    description="Download a generated STEP or STL file by job ID.",
    responses={
        200: {"description": "File content"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
)
async def download_generated_file(
    job_id: str,
    file_format: Literal["step", "stl", "solidworks"],
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
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
    # Validate job_id format to prevent path traversal
    try:
        # Validate it's a valid UUID format (prevents ../.. attacks)
        UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    # If user is authenticated, verify they own the job
    if current_user:
        query = select(Job).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()

        if job and job.user_id and job.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to download job {job_id} owned by {job.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this file",
            )

        # Check if job has file path in result
        if job and job.result:
            file_key = f"{file_format}_path"
            if file_key in job.result:
                stored_path = Path(job.result[file_key])
                if stored_path.exists():
                    logger.info(f"Serving file from job result: {stored_path}")
                    return _create_file_response(stored_path, file_format, job_id)  # type: ignore[return-value]

    # Fallback: Find the file in the temp export directory
    output_path = Path(tempfile.gettempdir()) / "cad_exports"

    # For solidworks, the actual file extension is .step
    search_ext = "step" if file_format == "solidworks" else file_format

    # Search for file matching the job_id pattern
    # Try multiple patterns to handle different naming conventions
    if file_format == "solidworks":
        patterns = [
            f"*{job_id[:8]}*solidworks.step",
            f"*_{job_id[:8]}_solidworks.step",
        ]
    else:
        patterns = [
            f"*_{job_id[:8]}.{search_ext}",
            f"*{job_id[:8]}*.{search_ext}",
            f"part_{job_id[:8]}.{search_ext}",
        ]

    matching_files: list[Path] = []
    for pattern in patterns:
        matching_files = list(output_path.glob(pattern))
        if matching_files:
            break

    if not matching_files:
        logger.warning(
            f"File not found for job {job_id}, format {file_format}. Searched in {output_path}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found for job {job_id}. The file may have expired.",
        )

    file_path = matching_files[0]
    return _create_file_response(file_path, file_format, job_id)  # type: ignore[return-value]


def _create_file_response(file_path: Path, file_format: str, job_id: str) -> Response:
    """Create a Response for the CAD file download with transparent decryption."""
    import asyncio

    # Determine content type
    if file_format == "step":
        media_type = "application/STEP"
        filename = f"part_{job_id[:8]}.step"
    elif file_format == "solidworks":
        media_type = "application/STEP"
        filename = f"part_{job_id[:8]}_solidworks.step"
    else:
        media_type = "application/sla"
        filename = f"part_{job_id[:8]}.stl"

    # Decrypt file content (handles both encrypted and unencrypted files)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context — use a sync read with decryption check
            from app.core.file_encryption import ENCRYPTED_MARKER_SUFFIX, is_encryption_enabled
            from app.core.security import encryption_service

            data = file_path.read_bytes()
            marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
            if marker_path.exists() and is_encryption_enabled():
                data = encryption_service.decrypt_bytes(data)

            return Response(
                content=data,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
    except RuntimeError:
        pass

    # Fallback: serve directly if no event loop
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
        400: {"model": ErrorResponse, "description": "Invalid input"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "File not found"},
    },
)
async def download_assembly_part(
    job_id: str,
    file_format: Literal["step", "stl"],
    part_name: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
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
    import re

    # Validate job_id format to prevent path traversal
    try:
        UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    # Validate part_name format (alphanumeric, underscore, hyphen only)
    if not re.match(r"^[a-zA-Z0-9_-]+$", part_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid part name format. Use only alphanumeric characters, underscores, and hyphens.",
        )

    # If user is authenticated, verify they own the job
    if current_user:
        query = select(Job).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()

        if job and job.user_id and job.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to download assembly part from job {job_id} owned by {job.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this file",
            )

    output_path = Path(tempfile.gettempdir()) / "cad_exports"

    # Search for file matching the part name and job_id
    pattern = f"{part_name}_{job_id[:8]}.{file_format}"
    file_path = output_path / pattern

    # Security: Verify resolved path is within expected directory
    resolved_path = file_path.resolve()
    resolved_output = output_path.resolve()
    if not str(resolved_path).startswith(str(resolved_output)):
        logger.warning(f"Path traversal attempt detected: {part_name}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path",
        )

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

    # Determine content type and decrypt
    from app.core.file_encryption import ENCRYPTED_MARKER_SUFFIX, is_encryption_enabled
    from app.core.security import encryption_service

    if file_format == "step":
        media_type = "application/STEP"
        filename = f"{part_name}_{job_id[:8]}.step"
    else:
        media_type = "application/sla"
        filename = f"{part_name}_{job_id[:8]}.stl"

    # Read and decrypt file content
    data = file_path.read_bytes()
    marker_path = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
    if marker_path.exists() and is_encryption_enabled():
        data = encryption_service.decrypt_bytes(data)

    return Response(  # type: ignore[return-value]
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post(
    "/parse",
    response_model=ParseResponse,
    summary="Parse description only",
    description="[DEPRECATED] Parse a description without generating CAD files. "
    "Please migrate to /api/v2/generate/preview for the new system.",
    deprecated=True,
)
async def parse_description_only(
    request: ParseRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> ParseResponse:
    """
    Parse a natural language description to preview extracted parameters.

    DEPRECATED: This endpoint is deprecated. Please use /api/v2/generate/preview instead.

    Useful for:
    - Validating a description before generation
    - Showing users what the AI understood
    - Debugging parsing issues
    """
    # Add deprecation headers
    add_deprecation_headers(response, settings)

    if not settings.ANTHROPIC_API_KEY:
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
