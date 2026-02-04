"""
CAD v2 enclosures endpoint.

CRUD operations for enclosure designs using declarative schemas.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.cad_v2.schemas.base import BoundingBox, Dimension
from app.cad_v2.schemas.enclosure import (
    EnclosureSpec,
    LidSpec,
    LidType,
    VentilationSpec,
    WallSide,
    WallSpec,
)
from app.cad_v2.compiler import CompilationEngine

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class EnclosureCreateRequest(BaseModel):
    """Request to create an enclosure from dimensions."""

    width_mm: float = Field(..., gt=0, description="Width in mm")
    depth_mm: float = Field(..., gt=0, description="Depth in mm")
    height_mm: float = Field(..., gt=0, description="Height in mm")
    wall_thickness_mm: float = Field(default=2.5, gt=0, description="Wall thickness in mm")
    corner_radius_mm: float | None = Field(default=None, ge=0, description="Corner radius in mm")
    
    # Lid options
    lid_type: str = Field(default="snap_fit", description="Lid type: snap_fit, screw_on, none")
    
    # Ventilation
    ventilation_enabled: bool = Field(default=False, description="Enable ventilation")
    ventilation_sides: list[str] = Field(
        default_factory=lambda: ["left", "right"],
        description="Sides with vents",
    )


class EnclosureResponse(BaseModel):
    """Response with enclosure information."""

    id: str = Field(description="Enclosure ID")
    enclosure_schema: dict[str, Any] = Field(description="Enclosure schema")
    exterior_mm: tuple[float, float, float] = Field(description="Exterior dimensions (W, D, H)")
    interior_mm: tuple[float, float, float] = Field(description="Interior dimensions (W, D, H)")
    validation_issues: list[str] = Field(default_factory=list, description="Validation warnings")


class ValidateSchemaRequest(BaseModel):
    """Request to validate a schema."""

    enclosure_schema: dict[str, Any] = Field(..., description="Schema to validate")


class ValidateSchemaResponse(BaseModel):
    """Validation result."""

    valid: bool
    issues: list[str] = Field(default_factory=list)


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=EnclosureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create enclosure from dimensions",
)
async def create_enclosure(request: EnclosureCreateRequest) -> EnclosureResponse:
    """Create an enclosure specification from explicit dimensions.
    
    This bypasses AI and creates a schema directly from parameters.
    """
    # Map lid type
    lid_type_map = {
        "snap_fit": LidType.SNAP_FIT,
        "screw_on": LidType.SCREW_ON,
        "friction": LidType.FRICTION,
        "none": LidType.NONE,
    }
    lid_type = lid_type_map.get(request.lid_type, LidType.SNAP_FIT)
    
    # Map ventilation sides
    side_map = {
        "front": WallSide.FRONT,
        "back": WallSide.BACK,
        "left": WallSide.LEFT,
        "right": WallSide.RIGHT,
        "top": WallSide.TOP,
        "bottom": WallSide.BOTTOM,
    }
    vent_sides = [
        side_map[s] for s in request.ventilation_sides
        if s in side_map
    ]
    
    # Build spec
    try:
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=request.width_mm),
                depth=Dimension(value=request.depth_mm),
                height=Dimension(value=request.height_mm),
            ),
            walls=WallSpec(thickness=Dimension(value=request.wall_thickness_mm)),
            corner_radius=Dimension(value=request.corner_radius_mm) if request.corner_radius_mm else None,
            lid=LidSpec(type=lid_type) if lid_type != LidType.NONE else None,
            ventilation=VentilationSpec(
                enabled=request.ventilation_enabled,
                sides=vent_sides,
            ) if request.ventilation_enabled else VentilationSpec(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid specification: {str(e)}",
        )
    
    # Validate with engine
    engine = CompilationEngine()
    issues = engine.validate_spec(spec)
    
    # Generate ID (in real system, would save to database)
    from uuid import uuid4
    enclosure_id = str(uuid4())
    
    return EnclosureResponse(
        id=enclosure_id,
        enclosure_schema=spec.model_dump(mode="json"),
        exterior_mm=spec.exterior.to_tuple_mm(),
        interior_mm=spec.interior.to_tuple_mm(),
        validation_issues=issues,
    )


@router.post(
    "/validate",
    response_model=ValidateSchemaResponse,
    summary="Validate an enclosure schema",
)
async def validate_enclosure(request: ValidateSchemaRequest) -> ValidateSchemaResponse:
    """Validate an enclosure schema without creating it.
    
    Checks:
    - Schema structure (Pydantic validation)
    - Physical constraints (wall thickness, dimensions)
    - Manufacturability warnings
    """
    from pydantic import ValidationError
    
    # First, validate against Pydantic model
    try:
        spec = EnclosureSpec.model_validate(request.enclosure_schema)
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return ValidateSchemaResponse(valid=False, issues=errors)
    
    # Then check physical constraints
    engine = CompilationEngine()
    issues = engine.validate_spec(spec)
    
    # Issues are warnings, not errors
    return ValidateSchemaResponse(
        valid=True,
        issues=issues,
    )


@router.get(
    "/presets",
    summary="Get enclosure presets",
    description="Get preset configurations for common boards",
)
async def get_presets() -> dict[str, Any]:
    """Get preset enclosure configurations for common boards.
    
    Returns pre-configured enclosure specs optimized for
    common development boards.
    """
    from app.cad_v2.components import get_registry
    
    registry = get_registry()
    presets = {}
    
    # Generate presets for boards
    for comp in registry.list_category("board"):
        dims = comp.dimensions
        # Add clearance
        preset = {
            "name": f"{comp.name} Enclosure",
            "component_id": comp.id,
            "suggested_dimensions": {
                "width_mm": dims.width_mm + 10,  # 5mm clearance each side
                "depth_mm": dims.depth_mm + 10,
                "height_mm": dims.height_mm + 20,  # Extra for standoffs and lid
            },
            "wall_thickness_mm": 2.5,
            "corner_radius_mm": 3,
        }
        presets[comp.id] = preset
    
    return {"presets": presets}
