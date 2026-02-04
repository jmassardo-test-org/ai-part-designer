"""
CAD v2 generation endpoint.

Generates CAD files from natural language using the declarative schema approach.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.cad_v2.ai import SchemaGenerator
from app.cad_v2.compiler import CompilationEngine, CompilationResult
from app.cad_v2.compiler.export import ExportFormat
from app.core.database import get_db
from app.core.auth import get_current_user_optional
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class GenerateV2Request(BaseModel):
    """Request to generate CAD from natural language."""

    description: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language description of the enclosure",
        examples=[
            "Create a case for Raspberry Pi 5 with USB ports accessible",
            "Make a project box 100mm x 80mm x 40mm with ventilation",
        ],
    )
    export_format: str = Field(
        default="step",
        description="Export format: step or stl",
    )


class GenerateV2Response(BaseModel):
    """Response from CAD v2 generation."""

    job_id: str = Field(description="Unique job identifier")
    success: bool = Field(description="Whether generation succeeded")
    
    # Schema information
    generated_schema: dict[str, Any] | None = Field(
        default=None,
        description="Generated schema (for debugging/preview)",
    )
    
    # Results
    parts: list[str] = Field(
        default_factory=list,
        description="Generated part names",
    )
    downloads: dict[str, str] = Field(
        default_factory=dict,
        description="Download URLs for generated files",
    )
    
    # Metadata
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Errors (if failed)",
    )
    
    # Clarification (if needed)
    clarification_needed: str | None = Field(
        default=None,
        description="Question to ask user if more info needed",
    )


class SchemaPreviewRequest(BaseModel):
    """Request to preview schema without compiling."""

    description: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural language description",
    )


class SchemaPreviewResponse(BaseModel):
    """Response with generated schema for preview."""

    success: bool
    generated_schema: dict[str, Any] | None = None
    validation_errors: list[str] | None = None
    clarification_needed: str | None = None


class DirectSchemaRequest(BaseModel):
    """Request to compile a schema directly."""

    enclosure_schema: dict[str, Any] = Field(
        ...,
        description="EnclosureSpec schema as JSON",
    )
    export_format: str = Field(
        default="step",
        description="Export format: step or stl",
    )
    async_mode: bool = Field(
        default=False,
        description="If true, queue as background job and return job_id immediately",
    )


class AsyncCompileResponse(BaseModel):
    """Response when async compilation is queued."""

    job_id: str = Field(description="Job ID for status polling")
    status: str = Field(default="queued", description="Job status")
    message: str = Field(default="Compilation queued", description="Status message")


class JobStatusResponse(BaseModel):
    """Response for job status queries."""

    job_id: str
    status: str = Field(description="pending, running, completed, failed, needs_clarification")
    progress: int = Field(default=0, description="Progress percentage 0-100")
    progress_message: str | None = Field(default=None, description="Human-readable progress")
    result: dict[str, Any] | None = Field(default=None, description="Result if completed")
    error: str | None = Field(default=None, description="Error message if failed")


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=GenerateV2Response,
    status_code=status.HTTP_200_OK,
    summary="Generate CAD from description",
    description="Convert natural language to CAD using CAD v2 pipeline",
)
async def generate_from_description(request: GenerateV2Request) -> GenerateV2Response:
    """Generate CAD files from natural language description.
    
    Uses the CAD v2 declarative schema pipeline:
    1. Parse intent from description
    2. Generate EnclosureSpec schema via Claude
    3. Compile schema to Build123d geometry
    4. Export to requested format
    """
    job_id = str(uuid4())
    
    # Step 1: Generate schema from description
    generator = SchemaGenerator()
    
    try:
        result = await generator.generate(request.description)
    except Exception as e:
        logger.exception("Schema generation failed")
        return GenerateV2Response(
            job_id=job_id,
            success=False,
            errors=[f"Schema generation failed: {str(e)}"],
        )
    
    # Check if clarification needed
    if result.clarification_needed:
        return GenerateV2Response(
            job_id=job_id,
            success=False,
            clarification_needed=result.clarification_needed,
        )
    
    # Check for validation errors
    if not result.success or result.spec is None:
        return GenerateV2Response(
            job_id=job_id,
            success=False,
            errors=result.validation_errors or ["Unknown error"],
            generated_schema=result.raw_json,
        )
    
    # Step 2: Compile to geometry
    engine = CompilationEngine()
    
    try:
        compilation = engine.compile_enclosure(result.spec)
    except Exception as e:
        logger.exception("Compilation failed")
        return GenerateV2Response(
            job_id=job_id,
            success=False,
            errors=[f"Compilation failed: {str(e)}"],
            generated_schema=result.raw_json,
        )
    
    if not compilation.success:
        return GenerateV2Response(
            job_id=job_id,
            success=False,
            errors=compilation.errors,
            generated_schema=result.raw_json,
        )
    
    # Step 3: Export files to persistent storage
    export_format = (
        ExportFormat.STL if request.export_format.lower() == "stl"
        else ExportFormat.STEP
    )
    
    try:
        from app.api.v2.downloads import get_job_dir
        job_dir = get_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        
        paths = compilation.export(str(job_dir), export_format)
        downloads = {
            p.stem: f"/api/v2/downloads/{job_id}/{p.name}"
            for p in paths
        }
    except Exception as e:
        logger.exception("Export failed")
        return GenerateV2Response(
            job_id=job_id,
            success=False,
            errors=[f"Export failed: {str(e)}"],
            generated_schema=result.raw_json,
        )
    
    return GenerateV2Response(
        job_id=job_id,
        success=True,
        generated_schema=result.raw_json,
        parts=list(compilation.parts.keys()),
        downloads=downloads,
        warnings=result.warnings or [],
    )


@router.post(
    "/preview",
    response_model=SchemaPreviewResponse,
    summary="Preview schema without compiling",
    description="Generate and validate schema from description",
)
async def preview_schema(request: SchemaPreviewRequest) -> SchemaPreviewResponse:
    """Preview the generated schema without compiling to CAD.
    
    Useful for:
    - Debugging schema generation
    - Previewing before expensive compilation
    - Interactive refinement
    """
    generator = SchemaGenerator()
    
    try:
        result = await generator.generate(request.description)
    except Exception as e:
        logger.exception("Schema generation failed")
        return SchemaPreviewResponse(
            success=False,
            validation_errors=[str(e)],
        )
    
    if result.clarification_needed:
        return SchemaPreviewResponse(
            success=False,
            clarification_needed=result.clarification_needed,
        )
    
    return SchemaPreviewResponse(
        success=result.success,
        generated_schema=result.raw_json,
        validation_errors=result.validation_errors,
    )


@router.post(
    "/compile",
    response_model=GenerateV2Response,
    status_code=status.HTTP_200_OK,
    summary="Compile schema directly",
    description="Compile a pre-defined schema to CAD",
    responses={
        202: {"model": AsyncCompileResponse, "description": "Async job queued"},
    },
)
async def compile_schema(
    request: DirectSchemaRequest,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> GenerateV2Response | AsyncCompileResponse:
    """Compile a schema directly without AI generation.
    
    Useful when schema is known or was refined by user.
    
    If async_mode=true, returns immediately with job_id for polling.
    """
    from app.cad_v2.schemas.enclosure import EnclosureSpec
    from pydantic import ValidationError
    
    job_id = str(uuid4())
    
    # Validate schema first (fast, always sync)
    try:
        spec = EnclosureSpec.model_validate(request.enclosure_schema)
    except ValidationError as e:
        errors = [str(err) for err in e.errors()]
        return GenerateV2Response(
            job_id=job_id,
            success=False,
            errors=errors,
            generated_schema=request.enclosure_schema,
        )
    
    # Async mode: queue job and return immediately
    if request.async_mode:
        from app.models.job import Job
        from app.worker.tasks.cad_v2 import compile_enclosure_v2
        
        # Create job record
        job = Job(
            id=UUID(job_id),
            user_id=user.id if user else None,
            job_type="cad_v2_compile",
            status="pending",
            input_params={
                "enclosure_schema": request.enclosure_schema,
                "export_format": request.export_format,
            },
        )
        db.add(job)
        await db.commit()
        
        # Queue Celery task
        user_id = str(user.id) if user else None
        compile_enclosure_v2.delay(
            job_id=job_id,
            enclosure_schema=request.enclosure_schema,
            export_format=request.export_format,
            user_id=user_id,
        )
        
        return AsyncCompileResponse(
            job_id=job_id,
            status="queued",
            message="Compilation queued. Poll /job/{job_id}/status for updates.",
        )
    
    # Sync mode: compile immediately
    engine = CompilationEngine()
    
    try:
        compilation = engine.compile_enclosure(spec)
    except Exception as e:
        return GenerateV2Response(
            job_id=job_id,
            success=False,
            errors=[str(e)],
            generated_schema=request.enclosure_schema,
        )
    
    if not compilation.success:
        return GenerateV2Response(
            job_id=job_id,
            success=False,
            errors=compilation.errors,
            generated_schema=request.enclosure_schema,
        )
    
    # Export to persistent storage
    export_format = (
        ExportFormat.STL if request.export_format.lower() == "stl"
        else ExportFormat.STEP
    )
    
    from app.api.v2.downloads import get_job_dir
    job_dir = get_job_dir(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    
    paths = compilation.export(str(job_dir), export_format)
    downloads = {
        p.stem: f"/api/v2/downloads/{job_id}/{p.name}"
        for p in paths
    }
    
    return GenerateV2Response(
        job_id=job_id,
        success=True,
        generated_schema=request.enclosure_schema,
        parts=list(compilation.parts.keys()),
        downloads=downloads,
    )


@router.get(
    "/job/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Poll for async job status and results",
)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Get the status of an async compilation job.
    
    Returns current progress and result when complete.
    """
    from sqlalchemy import select
    from app.models.job import Job
    
    # Validate job_id format
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job_id format",
        )
    
    # Get job from database
    result = await db.execute(
        select(Job).where(Job.id == job_uuid)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    
    return JobStatusResponse(
        job_id=job_id,
        status=job.status,
        progress=job.progress or 0,
        progress_message=job.progress_message,
        result=job.result if job.status == "completed" else None,
        error=job.error_message if job.status == "failed" else None,
    )
