"""
Template API endpoints.

Provides template browsing, parameter customization, and generation.

DEPRECATED: This module is deprecated as of v2.0.
Use the new Starters system (/api/v2/starters) for design templates.

Migration guide:
- Browse templates → Browse starters (GET /api/v2/starters)
- Generate from template → Remix starter (POST /api/v2/starters/{id}/remix)
- View template detail → View starter detail (GET /api/v2/starters/{id})

The starters system provides:
- User-created and community starter designs
- Full EnclosureSpec schema (not just parameters)
- Remix/fork model with attribution
- Better discoverability and organization

These endpoints will be removed in a future version.
"""

from __future__ import annotations

import logging
import tempfile
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.cad.export import export_step, export_stl
from app.cad.templates import TEMPLATE_REGISTRY, generate_from_template
from app.core.auth import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.models.template import Template

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import User

logger = logging.getLogger(__name__)

# Emit deprecation warning when this module is imported
warnings.warn(
    "The templates API (v1) is deprecated. Use starters API (v2) at /api/v2/starters instead.",
    DeprecationWarning,
    stacklevel=2,
)

router = APIRouter(deprecated=True)


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
    tier_required: str  # Alias for frontend compatibility
    thumbnail_url: str | None
    use_count: int
    usage_count: int  # Alias for frontend compatibility
    tags: list[str]
    parameters: list[dict[str, Any]]  # Flattened parameter list for frontend
    is_featured: bool


class TemplateDetail(BaseModel):
    """Full template details including parameters."""

    id: UUID
    name: str
    slug: str
    category: str
    description: str | None
    min_tier: str
    tier_required: str  # Alias for frontend compatibility
    thumbnail_url: str | None
    preview_url: str | None
    parameters: list[dict[str, Any]]  # Flattened parameter list for frontend
    use_count: int
    usage_count: int  # Alias for frontend compatibility
    tags: list[str]
    is_featured: bool


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


class TemplateCreateRequest(BaseModel):
    """Request to create a custom template."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    category: str = Field(..., min_length=1, max_length=50)
    subcategory: str | None = Field(None, max_length=50)
    parameters: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Parameter definitions with type, label, default, min, max, etc.",
    )
    default_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Default values for parameters",
    )
    tags: list[str] = Field(default_factory=list, max_length=10)
    is_public: bool = Field(default=False, description="Whether the template is publicly visible")


class TemplateFromDesignRequest(BaseModel):
    """Request to create a template from a design."""

    design_id: UUID = Field(..., description="ID of the design to create template from")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    category: str = Field(default="custom", min_length=1, max_length=50)
    tags: list[str] = Field(default_factory=list)


class TemplateCreateResponse(BaseModel):
    """Response after creating a template."""

    id: UUID
    name: str
    slug: str
    category: str
    description: str | None
    created_at: str


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
    query = select(Template).where(Template.is_active)

    if category:
        query = query.where(Template.category == category)

    if tier:
        query = query.where(Template.min_tier == tier)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            Template.name.ilike(search_pattern) | Template.description.ilike(search_pattern)
        )

    # Get total count
    count_query = select(Template.id).where(Template.is_active)
    if category:
        count_query = count_query.where(Template.category == category)
    result = await db.execute(count_query)
    total = len(result.all())

    # Get categories
    cat_query = select(Template.category).where(Template.is_active).distinct()
    cat_result = await db.execute(cat_query)
    categories = [row[0] for row in cat_result.all()]

    # Get templates
    query = query.order_by(Template.category, Template.name).limit(limit).offset(offset)
    result = await db.execute(query)
    templates = result.scalars().all()

    # Filter by user tier if authenticated
    # Admin users can see all templates regardless of tier
    user_tier = current_user.tier if current_user else "free"
    is_admin = current_user.role == "admin" if current_user else False

    template_list = []
    for tmpl in templates:
        # Admins bypass tier restrictions
        if is_admin or tmpl.is_accessible_by_tier(user_tier):
            # Convert parameters dict to list format for frontend
            params_list = []
            if tmpl.parameters:
                for name, config in tmpl.parameters.items():
                    param = {"name": name, **config} if isinstance(config, dict) else {"name": name}
                    params_list.append(param)

            template_list.append(
                TemplateListItem(
                    id=tmpl.id,
                    name=tmpl.name,
                    slug=tmpl.slug,
                    category=tmpl.category,
                    description=tmpl.description,
                    min_tier=tmpl.min_tier,
                    tier_required=tmpl.min_tier,
                    thumbnail_url=tmpl.thumbnail_url,
                    use_count=tmpl.use_count or 0,
                    usage_count=tmpl.use_count or 0,
                    tags=tmpl.tags or [],
                    parameters=params_list,
                    is_featured=tmpl.is_featured or False,
                )
            )

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
        Template.is_active,
    )
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Check tier access
    user_tier = current_user.tier if current_user else "free"
    if not template.is_accessible_by_tier(user_tier):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This template requires {template.min_tier} tier",
        )

    # Convert parameters dict to list format for frontend
    # Merge default_values into each parameter
    params_list = []
    default_values = template.default_values or {}
    if template.parameters:
        for name, config in template.parameters.items():
            param = {"name": name, **config} if isinstance(config, dict) else {"name": name}
            # Add default value from default_values if not already set
            if "default" not in param or param["default"] is None:
                param["default"] = default_values.get(name, param.get("min", 0))
            params_list.append(param)

    return TemplateDetail(
        id=template.id,
        name=template.name,
        slug=template.slug,
        category=template.category,
        description=template.description,
        min_tier=template.min_tier,
        tier_required=template.min_tier,
        thumbnail_url=template.thumbnail_url,
        preview_url=template.preview_url,
        parameters=params_list,
        use_count=template.use_count or 0,
        usage_count=template.use_count or 0,
        tags=template.tags or [],
        is_featured=template.is_featured or False,
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
        Template.is_active,
    )
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Check tier access
    if not template.is_accessible_by_tier(current_user.tier):
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
            data = export_step(shape)
            output_path.write_bytes(data)
        else:
            data = export_stl(shape, quality=request.quality)
            output_path.write_bytes(data)

        # Increment usage count
        template.usage_count += 1
        await db.commit()

        # In production, upload to S3 and return presigned URL
        # For now, return local file path
        download_url = f"/api/v1/templates/{slug}/download/{output_path.name}"

        logger.info(f"Generated {request.format} from template {slug} for user {current_user.id}")

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
            detail=f"Generation failed: {e!s}",
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
        Template.is_active,
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

        data = export_stl(shape, quality="draft")
        output_path.write_bytes(data)

        return FileResponse(
            output_path,
            media_type="application/octet-stream",
            filename=f"{slug}-preview.stl",
        )

    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview failed: {e!s}",
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
    query = (
        select(
            Template.category,
        )
        .where(Template.is_active)
        .distinct()
    )

    result = await db.execute(query)
    categories = [row[0] for row in result.all()]

    # Get counts per category
    category_data = []
    for cat in sorted(categories):
        count_query = select(Template.id).where(
            Template.category == cat,
            Template.is_active,
        )
        count_result = await db.execute(count_query)
        count = len(count_result.all())

        category_data.append(
            {
                "name": cat,
                "slug": cat.lower().replace(" ", "-"),
                "count": count,
            }
        )

    return category_data


@router.get(
    "/my-templates",
    response_model=TemplateListResponse,
    summary="List user's templates",
    description="Get templates created by the current user.",
)
async def list_my_templates(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateListResponse:
    """
    List templates created by the current user.
    """
    query = (
        select(Template)
        .where(Template.created_by_user_id == current_user.id)
        .where(Template.is_active)
        .order_by(Template.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    templates = result.scalars().all()

    # Get total count
    count_query = (
        select(Template.id)
        .where(Template.created_by_user_id == current_user.id)
        .where(Template.is_active)
    )
    count_result = await db.execute(count_query)
    total = len(count_result.all())

    template_list = [
        TemplateListItem(
            id=tmpl.id,
            name=tmpl.name,
            slug=tmpl.slug,
            category=tmpl.category,
            description=tmpl.description,
            min_tier=tmpl.min_tier,
            thumbnail_url=tmpl.thumbnail_url,
            use_count=tmpl.use_count,
        )
        for tmpl in templates
    ]

    return TemplateListResponse(
        templates=template_list,
        total=total,
        categories=[],
    )


@router.post(
    "",
    response_model=TemplateCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create template",
    description="Create a new custom template.",
)
async def create_template(
    request: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateCreateResponse:
    """
    Create a new custom template.

    Templates can be kept private or made public for other users.
    """
    import re
    from uuid import uuid4

    # Generate slug from name
    base_slug = re.sub(r"[^a-z0-9]+", "-", request.name.lower()).strip("-")
    slug = f"{base_slug}-{str(uuid4())[:8]}"

    template = Template(
        name=request.name,
        slug=slug,
        description=request.description,
        category=request.category,
        subcategory=request.subcategory,
        parameters=request.parameters,
        default_values=request.default_values,
        tags=request.tags,
        min_tier="free",
        is_featured=False,
        is_active=True,
        is_public=request.is_public,
        created_by_user_id=current_user.id,
        cadquery_script="# Custom template - script to be defined",
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(f"Template created: {template.id} by user {current_user.id}")

    return TemplateCreateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        category=template.category,
        description=template.description,
        created_at=template.created_at.isoformat(),
    )


@router.post(
    "/from-design",
    response_model=TemplateCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create template from design",
    description="Create a template from an existing design.",
)
async def create_template_from_design(
    request: TemplateFromDesignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateCreateResponse:
    """
    Create a template from an existing design.

    Extracts parameters and configuration from the design.
    """
    import re
    from uuid import uuid4

    from app.models.design import Design
    from app.models.project import Project

    # Get the design
    design_query = (
        select(Design, Project)
        .join(Project, Design.project_id == Project.id)
        .where(Design.id == request.design_id)
        .where(Design.deleted_at.is_(None))
    )
    result = await db.execute(design_query)
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    design, project = row

    # Check ownership
    if project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create a template from this design",
        )

    # Extract parameters from design extra_data
    design_data = design.extra_data or {}
    parameters = {}
    default_values = {}

    # Extract dimensions as parameters
    dimensions = design_data.get("dimensions", {})
    for key, value in dimensions.items():
        if isinstance(value, (int, float)):
            parameters[key] = {
                "type": "number",
                "label": key.replace("_", " ").title(),
                "unit": "mm",
                "min": value * 0.1,  # Allow 10% - 500% of original
                "max": value * 5,
                "step": 0.1 if value < 10 else 1,
            }
            default_values[key] = value

    # Generate slug
    base_slug = re.sub(r"[^a-z0-9]+", "-", request.name.lower()).strip("-")
    slug = f"{base_slug}-{str(uuid4())[:8]}"

    # Build CadQuery script placeholder with original parameters
    script = f"""# Template created from design: {design.name}
# Original description: {design.description or "N/A"}
# Source: {design.source_type}

# Parameters are passed as 'params' dict
# Available parameters: {list(default_values.keys())}

# TODO: Implement parametric CAD generation
"""

    template = Template(
        name=request.name,
        slug=slug,
        description=request.description or design.description,
        category=request.category,
        parameters=parameters,
        default_values=default_values,
        tags=request.tags,
        min_tier="free",
        is_featured=False,
        is_active=True,
        is_public=False,
        created_by_user_id=current_user.id,
        source_design_id=design.id,
        cadquery_script=script,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(
        f"Template created from design: {template.id} from {design.id} by user {current_user.id}"
    )

    return TemplateCreateResponse(
        id=template.id,
        name=template.name,
        slug=template.slug,
        category=template.category,
        description=template.description,
        created_at=template.created_at.isoformat(),
    )
