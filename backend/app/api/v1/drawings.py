"""
2D Drawing API endpoints.

Generate and manage technical 2D drawings from 3D CAD models.
"""

from typing import Any, cast

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.cad.drawing_generator import (
    DimensionStyle,
    DrawingConfig,
    DrawingFormat,
    DrawingView,
    DrawingViewType,
    PaperSize,
    TitleBlock,
    drawing_generator,
)
from app.models import Design, User

router = APIRouter(prefix="/designs/{design_id}/drawings", tags=["drawings"])


# --- Schemas ---


class ViewConfig(BaseModel):
    """Configuration for a drawing view."""

    view_type: str = Field(
        ...,
        description="View type: front, back, left, right, top, bottom, isometric, section, detail",
    )
    position_x: float = Field(default=0.5, ge=0, le=1, description="X position on sheet (0-1)")
    position_y: float = Field(default=0.5, ge=0, le=1, description="Y position on sheet (0-1)")
    scale: float = Field(default=1.0, gt=0, le=10, description="View scale")
    show_hidden_lines: bool = False
    show_center_lines: bool = True
    label: str | None = None

    # Section view options
    section_plane: str | None = None
    section_offset: float = 0.0

    # Detail view options
    detail_scale: float = 2.0


class DimensionStyleConfig(BaseModel):
    """Dimension style configuration."""

    font_size: float = Field(default=3.5, gt=0, le=10)
    arrow_size: float = Field(default=3.0, gt=0, le=10)
    decimal_places: int = Field(default=2, ge=0, le=6)
    units: str = Field(default="mm", pattern="^(mm|cm|m|in|ft)$")
    show_units: bool = False


class TitleBlockConfig(BaseModel):
    """Title block configuration."""

    company_name: str = ""
    project_name: str = ""
    drawing_title: str = ""
    part_number: str = ""
    revision: str = "A"
    drawn_by: str = ""
    checked_by: str = ""
    approved_by: str = ""
    date: str = ""
    scale: str = ""
    sheet: str = "1 of 1"
    material: str = ""
    finish: str = ""
    notes: list[str] = Field(default_factory=list)


class DrawingRequest(BaseModel):
    """Request to generate a 2D drawing."""

    paper_size: str = Field(
        default="A4", description="Paper size: A4, A3, A2, A1, A0, letter, legal, tabloid"
    )
    orientation: str = Field(default="landscape", pattern="^(portrait|landscape)$")
    output_format: str = Field(default="svg", description="Output format: svg, pdf, dxf, png")
    views: list[ViewConfig] = Field(
        default_factory=list,
        description="View configurations. If empty, uses default 3-view layout.",
    )
    dimension_style: DimensionStyleConfig | None = None
    title_block: TitleBlockConfig | None = None
    auto_dimensions: bool = True
    show_border: bool = True
    projection_type: str = Field(default="third_angle", pattern="^(third_angle|first_angle)$")


class DrawingPreviewResponse(BaseModel):
    """Preview of drawing configuration."""

    paper_size: str
    orientation: str
    width_mm: float
    height_mm: float
    view_count: int
    views: list[dict[str, Any]]
    estimated_file_size_kb: int


# --- Helper Functions ---


async def get_design_or_404(
    design_id: UUID,
    db: AsyncSession,
    user: User,
) -> Design:
    """Get design or raise 404, checking ownership."""
    result = await db.execute(
        select(Design)
        .where(Design.id == design_id)
        .options(
            selectinload(Design.project),
            selectinload(Design.versions),
        )
    )
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    if design.project.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return design


def get_step_file_path(design: Design) -> str | None:
    """Get the STEP file path for a design."""
    # Check file_formats for STEP file
    if design.current_version:
        formats = design.current_version.file_formats or {}
        step_url = formats.get("step") or formats.get("STEP")
        if step_url and Path(step_url).exists():
            return cast(str, step_url)

    # Check versions for STEP file
    for version in design.versions:
        formats = version.file_formats or {}
        step_url = formats.get("step") or formats.get("STEP")
        if step_url and Path(step_url).exists():
            return cast(str, step_url)

    # Fall back to file_url if it's a STEP file
    if design.current_version and design.current_version.file_url:
        file_url = design.current_version.file_url
        if file_url.lower().endswith((".step", ".stp")) and Path(file_url).exists():
            return file_url

    return None


def parse_drawing_config(request: DrawingRequest, design: Design, user: User) -> DrawingConfig:
    """Parse request into DrawingConfig."""
    # Parse paper size
    paper_size = (
        PaperSize(request.paper_size.upper())
        if request.paper_size.upper() in [p.value for p in PaperSize]
        else PaperSize.A4
    )

    # Parse views
    views = []
    if request.views:
        for v in request.views:
            view_type = (
                DrawingViewType(v.view_type.lower())
                if v.view_type.lower() in [t.value for t in DrawingViewType]
                else DrawingViewType.FRONT
            )
            views.append(
                DrawingView(
                    view_type=view_type,
                    position_x=v.position_x,
                    position_y=v.position_y,
                    scale=v.scale,
                    show_hidden_lines=v.show_hidden_lines,
                    show_center_lines=v.show_center_lines,
                    label=v.label,
                    section_plane=v.section_plane,
                    section_offset=v.section_offset,
                    detail_scale=v.detail_scale,
                )
            )
    else:
        # Use default views
        views = drawing_generator.get_default_views(request.projection_type)

    # Parse dimension style
    dim_style = DimensionStyle()
    if request.dimension_style:
        dim_style = DimensionStyle(
            font_size=request.dimension_style.font_size,
            arrow_size=request.dimension_style.arrow_size,
            decimal_places=request.dimension_style.decimal_places,
            units=request.dimension_style.units,
            show_units=request.dimension_style.show_units,
        )

    # Parse title block
    title = TitleBlock()
    if request.title_block:
        title = TitleBlock(
            company_name=request.title_block.company_name,
            project_name=request.title_block.project_name or design.project.name,
            drawing_title=request.title_block.drawing_title or design.name,
            part_number=request.title_block.part_number,
            revision=request.title_block.revision,
            drawn_by=request.title_block.drawn_by or user.display_name or user.email,
            checked_by=request.title_block.checked_by,
            approved_by=request.title_block.approved_by,
            date=request.title_block.date,
            scale=request.title_block.scale,
            sheet=request.title_block.sheet,
            material=request.title_block.material,
            finish=request.title_block.finish,
            notes=request.title_block.notes,
        )
    else:
        # Default title block
        title = TitleBlock(
            project_name=design.project.name,
            drawing_title=design.name,
            drawn_by=user.display_name or user.email,
        )

    return DrawingConfig(
        paper_size=paper_size,
        orientation=request.orientation,
        views=views,
        dimension_style=dim_style,
        title_block=title,
        show_border=request.show_border,
        auto_dimensions=request.auto_dimensions,
        projection_type=request.projection_type,
    )


# --- Endpoints ---


@router.post("/generate")
async def generate_drawing(
    design_id: UUID,
    request: DrawingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Generate a 2D technical drawing from a 3D design.

    Returns the drawing file in the requested format (SVG, PDF, DXF, or PNG).
    """
    design = await get_design_or_404(design_id, db, current_user)

    # Get STEP file path
    step_path = get_step_file_path(design)
    if not step_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Design does not have a STEP file for drawing generation",
        )

    # Parse configuration
    config = parse_drawing_config(request, design, current_user)

    # Parse output format
    try:
        output_format = DrawingFormat(request.output_format.lower())
    except ValueError:
        output_format = DrawingFormat.SVG

    # Generate drawing
    drawing_bytes = await drawing_generator.generate_drawing(
        step_path,
        config,
        output_format,
    )

    # Set content type
    content_types = {
        DrawingFormat.SVG: "image/svg+xml",
        DrawingFormat.PDF: "application/pdf",
        DrawingFormat.DXF: "application/dxf",
        DrawingFormat.PNG: "image/png",
    }
    content_type = content_types.get(output_format, "application/octet-stream")

    # Set filename
    filename = f"{design.name}_drawing.{output_format.value}"

    return Response(
        content=drawing_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/preview", response_model=DrawingPreviewResponse)
async def preview_drawing(
    design_id: UUID,
    request: DrawingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DrawingPreviewResponse:
    """
    Preview drawing configuration without generating the actual file.

    Returns information about the drawing that would be generated.
    """
    design = await get_design_or_404(design_id, db, current_user)
    config = parse_drawing_config(request, design, current_user)

    # Get paper dimensions
    from app.cad.drawing_generator import PAPER_DIMENSIONS

    width, height = PAPER_DIMENSIONS[config.paper_size]
    if config.orientation == "landscape":
        width, height = height, width

    # Estimate file size based on format and view count
    base_size = 10  # KB
    per_view_size = 5  # KB per view
    format_multipliers = {
        "svg": 1.0,
        "pdf": 1.5,
        "dxf": 2.0,
        "png": 10.0,
    }
    multiplier = format_multipliers.get(request.output_format.lower(), 1.0)
    estimated_size = int((base_size + len(config.views) * per_view_size) * multiplier)

    return DrawingPreviewResponse(
        paper_size=config.paper_size.value,
        orientation=config.orientation,
        width_mm=width,
        height_mm=height,
        view_count=len(config.views),
        views=[
            {
                "type": v.view_type.value,
                "position": {"x": v.position_x, "y": v.position_y},
                "scale": v.scale,
            }
            for v in config.views
        ],
        estimated_file_size_kb=estimated_size,
    )


@router.get("/formats")
async def list_formats() -> dict[str, Any]:
    """List available drawing formats."""
    return {
        "formats": [
            {
                "id": "svg",
                "name": "SVG",
                "description": "Scalable Vector Graphics - best for web viewing",
                "extension": ".svg",
            },
            {
                "id": "pdf",
                "name": "PDF",
                "description": "Portable Document Format - best for printing",
                "extension": ".pdf",
            },
            {
                "id": "dxf",
                "name": "DXF",
                "description": "AutoCAD Drawing Exchange - for CAD software",
                "extension": ".dxf",
            },
            {
                "id": "png",
                "name": "PNG",
                "description": "PNG Image - for quick previews",
                "extension": ".png",
            },
        ],
    }


@router.get("/paper-sizes")
async def list_paper_sizes() -> dict[str, Any]:
    """List available paper sizes."""
    from app.cad.drawing_generator import PAPER_DIMENSIONS

    return {
        "paper_sizes": [
            {
                "id": size.value,
                "name": size.value,
                "width_mm": dims[0],
                "height_mm": dims[1],
            }
            for size, dims in PAPER_DIMENSIONS.items()
        ],
    }


@router.get("/view-types")
async def list_view_types() -> dict[str, Any]:
    """List available view types."""
    return {
        "view_types": [
            {"id": "front", "name": "Front View", "description": "View from the front"},
            {"id": "back", "name": "Back View", "description": "View from the back"},
            {"id": "left", "name": "Left View", "description": "View from the left side"},
            {"id": "right", "name": "Right View", "description": "View from the right side"},
            {"id": "top", "name": "Top View", "description": "View from above"},
            {"id": "bottom", "name": "Bottom View", "description": "View from below"},
            {"id": "isometric", "name": "Isometric View", "description": "3D isometric projection"},
            {
                "id": "section",
                "name": "Section View",
                "description": "Cross-section through the part",
            },
            {
                "id": "detail",
                "name": "Detail View",
                "description": "Magnified detail of a specific area",
            },
        ],
    }
