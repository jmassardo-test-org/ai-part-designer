"""
Enclosure Generation API

API endpoints for generating enclosures around project components.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, Depends, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.database import get_db
from app.enclosure.schemas import (
    EnclosureOptions,
    EnclosureResult,
    EnclosureStyle,
    EnclosureStyleType,
    SpatialLayout,
)
from app.enclosure.service import get_enclosure_service
from app.enclosure.templates import (
    get_style_description,
    get_style_template,
    list_available_styles,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enclosures", tags=["enclosures"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class GenerateEnclosureRequest(BaseModel):
    """Request to generate an enclosure."""

    style_type: EnclosureStyleType = Field(
        default=EnclosureStyleType.MINIMAL,
        description="Pre-defined style template",
    )
    style_overrides: dict | None = Field(
        default=None,
        description="Override specific style parameters",
    )
    options: EnclosureOptions = Field(
        default_factory=EnclosureOptions,
        description="Generation options",
    )
    layout: SpatialLayout | None = Field(
        default=None,
        description="Component layout (auto-calculated if None)",
    )
    component_ids: list[UUID] | None = Field(
        default=None,
        description="Specific components to include (all if None)",
    )
    name: str | None = Field(
        default=None,
        description="Name for the generated enclosure",
    )


class GenerateEnclosureResponse(BaseModel):
    """Response from enclosure generation."""

    job_id: UUID
    status: str = "queued"
    message: str = "Enclosure generation job queued"


class EnclosureJobStatus(BaseModel):
    """Status of an enclosure generation job."""

    job_id: UUID
    status: str
    progress: int = 0
    result: EnclosureResult | None = None
    error: str | None = None


class StyleTemplateInfo(BaseModel):
    """Information about a style template."""

    type: str
    name: str
    description: str
    wall_thickness: float
    lid_closure: str
    ventilation: str


class StyleTemplateListResponse(BaseModel):
    """Response listing available style templates."""

    styles: list[StyleTemplateInfo]


class PreviewDimensionsRequest(BaseModel):
    """Request to preview enclosure dimensions."""

    component_ids: list[UUID]
    style_type: EnclosureStyleType = Field(default=EnclosureStyleType.MINIMAL)
    options: EnclosureOptions = Field(default_factory=EnclosureOptions)


class PreviewDimensionsResponse(BaseModel):
    """Preview of enclosure dimensions."""

    internal_length: float
    internal_width: float
    internal_height: float
    external_length: float
    external_width: float
    external_height: float
    component_count: int
    standoff_count: int
    cutout_count: int


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/styles", response_model=StyleTemplateListResponse)
async def list_style_templates(
    current_user: User = Depends(get_current_user),
) -> StyleTemplateListResponse:
    """
    List available enclosure style templates.

    Returns pre-defined style templates with their parameters.
    """
    styles = list_available_styles()
    return StyleTemplateListResponse(styles=[StyleTemplateInfo(**s) for s in styles])


@router.get("/styles/{style_type}")
async def get_style_details(
    style_type: EnclosureStyleType,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get detailed parameters for a style template.

    Returns full EnclosureStyle parameters.
    """
    if style_type == EnclosureStyleType.CUSTOM:
        return {
            "type": "custom",
            "message": "Custom style - use your own parameters",
            "default_parameters": EnclosureStyle().model_dump(),
        }

    template = get_style_template(style_type)
    return {
        "type": style_type.value,
        "description": get_style_description(style_type),
        "parameters": template.model_dump(),
    }


@router.post(
    "/projects/{project_id}/generate",
    response_model=GenerateEnclosureResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_enclosure(
    project_id: UUID,
    request: GenerateEnclosureRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateEnclosureResponse:
    """
    Generate an enclosure for project components.

    Queues an enclosure generation job that:
    1. Fetches component specifications from the project
    2. Calculates internal dimensions
    3. Generates mounting standoffs for each component
    4. Creates connector cutouts
    5. Uses AI to generate CadQuery code
    6. Executes the code and exports to STEP/STL

    Returns a job ID for status polling.
    """
    # TODO: Verify project exists and user has access
    # TODO: Fetch components from project
    # TODO: Queue background job

    import uuid

    job_id = uuid.uuid4()

    # Queue the background task
    background_tasks.add_task(
        _run_enclosure_generation,
        job_id=job_id,
        project_id=project_id,
        request=request,
        user_id=current_user.id,
    )

    return GenerateEnclosureResponse(
        job_id=job_id,
        status="queued",
        message="Enclosure generation job queued successfully",
    )


@router.get("/jobs/{job_id}", response_model=EnclosureJobStatus)
async def get_enclosure_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnclosureJobStatus:
    """
    Get status of an enclosure generation job.

    Poll this endpoint to check job progress and get results.
    """
    # TODO: Fetch job status from database/cache

    return EnclosureJobStatus(
        job_id=job_id,
        status="pending",
        progress=0,
    )


@router.post("/preview-dimensions", response_model=PreviewDimensionsResponse)
async def preview_enclosure_dimensions(
    request: PreviewDimensionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreviewDimensionsResponse:
    """
    Preview enclosure dimensions without generating.

    Quickly calculates what the enclosure dimensions would be
    based on selected components and options.
    """
    # TODO: Fetch component specifications
    # TODO: Calculate dimensions

    # Placeholder response
    return PreviewDimensionsResponse(
        internal_length=100.0,
        internal_width=70.0,
        internal_height=30.0,
        external_length=104.0,
        external_width=74.0,
        external_height=34.0,
        component_count=len(request.component_ids),
        standoff_count=4,
        cutout_count=3,
    )


# =============================================================================
# Background Task
# =============================================================================


async def _run_enclosure_generation(
    job_id: UUID,
    project_id: UUID,
    request: GenerateEnclosureRequest,
    user_id: UUID,
) -> None:
    """
    Background task to run enclosure generation.

    This is run asynchronously after the API returns.
    """
    logger.info(f"Starting enclosure generation job {job_id}")

    try:
        # Get style
        if request.style_type == EnclosureStyleType.CUSTOM:
            style = EnclosureStyle(**(request.style_overrides or {}))
        else:
            style = get_style_template(request.style_type)
            if request.style_overrides:
                # Apply overrides
                style_dict = style.model_dump()
                style_dict.update(request.style_overrides)
                style = EnclosureStyle(**style_dict)

        # TODO: Fetch components from project
        # TODO: Convert to ComponentData format
        # TODO: Call enclosure service
        # TODO: Save results to database
        # TODO: Upload files to storage

        get_enclosure_service()

        # Placeholder - would fetch real components

        # Generate enclosure
        # result = await service.generate_enclosure(
        #     components=components,
        #     style=style,
        #     options=request.options,
        #     layout=request.layout,
        # )

        logger.info(f"Enclosure generation job {job_id} completed")

    except Exception as e:
        logger.error(f"Enclosure generation job {job_id} failed: {e}")
        # TODO: Update job status to failed


# =============================================================================
# Router Registration Helper
# =============================================================================


def get_enclosure_router() -> APIRouter:
    """Get the enclosure router for registration."""
    return router
