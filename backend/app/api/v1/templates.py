"""
Template API endpoints.

Provides template browsing, parameter customization, and generation.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_user_optional
from app.models import User
from app.models.template import Template
from app.cad.templates import generate_from_template, TEMPLATE_REGISTRY
from app.cad.export import export_step, export_stl

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ParameterDefinition(BaseModel):
    """Template parameter definition."""
    
    type: str = Field(description="Parameter type: number, enum, boolean, string")
    label: str = Field(description="Human-readable label")
    description: str | None = Field(default=None, description="Help text")
    default: Any = Field(description="Default value")
    min: float | None = Field(default=None, description="Minimum value (numbers)")
    max: float | None = Field(default=None, description="Maximum value (numbers)")
    unit: str | None = Field(default=None, description="Unit of measure")
    options: list[str] | None = Field(default=None, description="Enum options")
    required: bool = Field(default=True)


class TemplateListItem(BaseModel):
    """Template summary for list views."""
    
    id: UUID
    name: str
    slug: str
    category: str
    description: str | None
    min_tier: str
    thumbnail_url: str | None
    use_count: int


class TemplateDetail(BaseModel):
    """Full template details including parameters."""
    
    id: UUID
    name: str
    slug: str
    category: str
    description: str | None
    min_tier: str
    thumbnail_url: str | None
    preview_url: str | None
    parameters: dict[str, ParameterDefinition]
    use_count: int


class TemplateListResponse(BaseModel):
    """Response for template list endpoint."""
    
    templates: list[TemplateListItem]
    total: int
    categories: list[str]


class GenerateRequest(BaseModel):
    """Request to generate from template."""
    
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Template parameter values",
    )
    format: str = Field(
        default="step",
        pattern="^(step|stl)$",
        description="Export format: step or stl",
    )
    quality: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",
        description="STL quality (only for STL format)",
    )


class GenerateResponse(BaseModel):
    """Response with generation result."""
    
    message: str
    download_url: str
    format: str
    parameters_used: dict[str, Any]


class PreviewRequest(BaseModel):
    """Request for template preview with custom parameters."""
    
    parameters: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "",
    response_model=TemplateListResponse,
    summary="List templates",
    description="Get all available templates, optionally filtered by category or tier.",
)
async def list_templates(
    category: str | None = Query(None, description="Filter by category"),
    tier: str | None = Query(None, description="Filter by tier"),
    search: str | None = Query(None, description="Search in name/description"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> TemplateListResponse:
    """
    List all available templates.
    
    Templates are filtered based on user tier (if authenticated).
    """
    # Build query
    query = select(Template).where(Template.is_active == True)
    
    if category:
        query = query.where(Template.category == category)
    
    if tier:
        query = query.where(Template.min_tier == tier)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            Template.name.ilike(search_pattern) |
            Template.description.ilike(search_pattern)
        )
    
    # Get total count
    count_query = select(Template.id).where(Template.is_active == True)
    if category:
        count_query = count_query.where(Template.category == category)
    result = await db.execute(count_query)
    total = len(result.all())
    
    # Get categories
    cat_query = select(Template.category).where(Template.is_active == True).distinct()
    cat_result = await db.execute(cat_query)
    categories = [row[0] for row in cat_result.all()]
    
    # Get templates
    query = query.order_by(Template.category, Template.name).limit(limit).offset(offset)
    result = await db.execute(query)
    templates = result.scalars().all()
    
    # Filter by user tier if authenticated
    user_tier = current_user.subscription_tier if current_user else "free"
    
    template_list = []
    for tmpl in templates:
        if tmpl.is_accessible_by_tier(user_tier):
            template_list.append(TemplateListItem(
                id=tmpl.id,
                name=tmpl.name,
                slug=tmpl.slug,
                category=tmpl.category,
                description=tmpl.description,
                min_tier=tmpl.min_tier,
                thumbnail_url=tmpl.thumbnail_url,
                use_count=tmpl.use_count,
            ))
    
    return TemplateListResponse(
        templates=template_list,
        total=total,
        categories=categories,
    )


@router.get(
    "/{slug}",
    response_model=TemplateDetail,
    summary="Get template details",
    description="Get full template details including parameter definitions.",
)
async def get_template(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> TemplateDetail:
    """
    Get template details by slug.
    """
    query = select(Template).where(
        Template.slug == slug,
        Template.is_active == True,
    )
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Check tier access
    user_tier = current_user.subscription_tier if current_user else "free"
    if not template.is_accessible_by_tier(user_tier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This template requires {template.min_tier} tier",
        )
    
    # Convert parameters to ParameterDefinition
    params = {}
    for name, defn in template.parameters.items():
        params[name] = ParameterDefinition(
            type=defn.get("type", "string"),
            label=defn.get("label", name),
            description=defn.get("description"),
            default=defn.get("default"),
            min=defn.get("min"),
            max=defn.get("max"),
            unit=defn.get("unit"),
            options=defn.get("options"),
            required=defn.get("required", True),
        )
    
    return TemplateDetail(
        id=template.id,
        name=template.name,
        slug=template.slug,
        category=template.category,
        description=template.description,
        min_tier=template.min_tier,
        thumbnail_url=template.thumbnail_url,
        preview_url=template.preview_url,
        parameters=params,
        use_count=template.use_count,
    )


@router.post(
    "/{slug}/generate",
    response_model=GenerateResponse,
    summary="Generate from template",
    description="Generate CAD file from template with custom parameters.",
)
async def generate_template(
    slug: str,
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateResponse:
    """
    Generate a CAD file from template.
    
    Validates parameters and generates the file in the requested format.
    """
    # Get template
    query = select(Template).where(
        Template.slug == slug,
        Template.is_active == True,
    )
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Check tier access
    if not template.is_accessible_by_tier(current_user.subscription_tier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This template requires {template.min_tier} tier",
        )
    
    # Merge with defaults
    params = template.get_parameter_defaults()
    params.update(request.parameters)
    
    # Validate parameters
    errors = template.validate_parameters(params)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid parameters", "errors": errors},
        )
    
    # Check if template generator exists
    if slug not in TEMPLATE_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Template generator not implemented",
        )
    
    try:
        # Generate CAD geometry
        shape = generate_from_template(slug, params)
        
        # Export to file
        with tempfile.NamedTemporaryFile(
            suffix=f".{request.format}",
            delete=False,
        ) as tmp:
            output_path = Path(tmp.name)
        
        if request.format == "step":
            export_step(shape, output_path)
        else:
            export_stl(shape, output_path, quality=request.quality)
        
        # Increment usage count
        template.usage_count += 1
        await db.commit()
        
        # In production, upload to S3 and return presigned URL
        # For now, return local file path
        download_url = f"/api/v1/templates/{slug}/download/{output_path.name}"
        
        logger.info(
            f"Generated {request.format} from template {slug} for user {current_user.id}"
        )
        
        return GenerateResponse(
            message="Generation complete",
            download_url=download_url,
            format=request.format,
            parameters_used=params,
        )
        
    except Exception as e:
        logger.error(f"Template generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}",
        )


@router.post(
    "/{slug}/preview",
    summary="Generate preview mesh",
    description="Generate a low-poly preview mesh for 3D viewer.",
)
async def preview_template(
    slug: str,
    request: PreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Generate a low-poly STL for preview.
    
    This is optimized for fast loading in the 3D viewer.
    """
    # Get template
    query = select(Template).where(
        Template.slug == slug,
        Template.is_active == True,
    )
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Check if template generator exists
    if slug not in TEMPLATE_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Template generator not implemented",
        )
    
    # Merge with defaults
    params = template.get_parameter_defaults()
    params.update(request.parameters)
    
    try:
        # Generate CAD geometry
        shape = generate_from_template(slug, params)
        
        # Export low-quality STL for preview
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
            output_path = Path(tmp.name)
        
        export_stl(shape, output_path, quality="low")
        
        return FileResponse(
            output_path,
            media_type="application/octet-stream",
            filename=f"{slug}-preview.stl",
        )
        
    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview failed: {str(e)}",
        )


@router.get(
    "/categories",
    summary="List template categories",
    description="Get list of all template categories.",
)
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Get all template categories with counts.
    """
    query = select(
        Template.category,
    ).where(Template.is_active == True).distinct()
    
    result = await db.execute(query)
    categories = [row[0] for row in result.all()]
    
    # Get counts per category
    category_data = []
    for cat in sorted(categories):
        count_query = select(Template.id).where(
            Template.category == cat,
            Template.is_active == True,
        )
        count_result = await db.execute(count_query)
        count = len(count_result.all())
        
        category_data.append({
            "name": cat,
            "slug": cat.lower().replace(" ", "-"),
            "count": count,
        })
    
    return category_data
