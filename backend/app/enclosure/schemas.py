"""
Enclosure Generation Schemas

Pydantic models for enclosure generation configuration,
style options, and results.
"""

from enum import Enum
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.component_specs import (
    Face,
    ThreadSize,
    ConnectorType,
    Dimensions,
    Position3D,
    LengthUnit,
)


# =============================================================================
# Enums
# =============================================================================

class EnclosureStyleType(str, Enum):
    """Pre-defined enclosure style types."""
    MINIMAL = "minimal"
    RUGGED = "rugged"
    VENTED = "vented"
    STACKABLE = "stackable"
    DESKTOP = "desktop"
    CUSTOM = "custom"


class LidClosureType(str, Enum):
    """How the lid attaches to the enclosure."""
    SNAP_FIT = "snap_fit"
    SCREW = "screw"
    SLIDE = "slide"
    FRICTION = "friction"
    HINGE = "hinge"
    MAGNETIC = "magnetic"


class VentilationPattern(str, Enum):
    """Ventilation slot patterns."""
    NONE = "none"
    PARALLEL_SLOTS = "parallel_slots"
    GRID = "grid"
    HONEYCOMB = "honeycomb"
    PERFORATED = "perforated"
    LOUVERS = "louvers"


class StandoffType(str, Enum):
    """Standoff mounting types."""
    SOLID = "solid"
    HOLLOW = "hollow"
    HEAT_SET_INSERT = "heat_set_insert"
    THREADED = "threaded"
    SNAP_FIT = "snap_fit"


class BossStyle(str, Enum):
    """Boss/pillar style around standoffs."""
    CYLINDRICAL = "cylindrical"
    SQUARE = "square"
    RIBBED = "ribbed"
    GUSSETED = "gusseted"


# =============================================================================
# Standoff Schemas
# =============================================================================

class StandoffOptions(BaseModel):
    """Options for standoff generation."""
    
    type: StandoffType = Field(
        default=StandoffType.HOLLOW,
        description="Type of standoff",
    )
    boss_style: BossStyle = Field(
        default=BossStyle.CYLINDRICAL,
        description="Style of boss around standoff",
    )
    outer_diameter: Optional[float] = Field(
        default=None,
        description="Outer diameter (auto-calculated if None)",
    )
    inner_diameter: Optional[float] = Field(
        default=None,
        description="Inner hole diameter (for hollow/threaded)",
    )
    thread_size: Optional[ThreadSize] = Field(
        default=None,
        description="Thread size for threaded standoffs",
    )
    fillet_radius: float = Field(
        default=0.5,
        ge=0,
        description="Fillet radius at base",
    )


class Standoff(BaseModel):
    """A single standoff in the enclosure."""
    
    # Position
    x: float = Field(..., description="X position in enclosure")
    y: float = Field(..., description="Y position in enclosure")
    height: float = Field(..., gt=0, description="Standoff height")
    
    # Dimensions
    outer_diameter: float = Field(..., gt=0)
    inner_diameter: float = Field(default=0, ge=0, description="0 for solid")
    
    # Options
    type: StandoffType = Field(default=StandoffType.HOLLOW)
    thread_size: Optional[ThreadSize] = Field(default=None)
    boss_style: BossStyle = Field(default=BossStyle.CYLINDRICAL)
    
    # Reference
    component_id: Optional[UUID] = Field(
        default=None,
        description="Component this standoff is for",
    )
    hole_label: Optional[str] = Field(
        default=None,
        description="Label of the mounting hole",
    )


# =============================================================================
# Cutout Schemas
# =============================================================================

class CutoutProfile(BaseModel):
    """Standard cutout profile for a connector type."""
    
    connector_type: ConnectorType
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    corner_radius: float = Field(default=0.5, ge=0)
    
    # Additional features
    has_flange: bool = Field(default=False)
    flange_width: float = Field(default=1.0)
    
    # Tolerance
    tolerance: float = Field(
        default=0.3,
        ge=0,
        description="Additional clearance around connector",
    )


class Cutout(BaseModel):
    """A cutout in the enclosure wall."""
    
    # Position on wall
    face: Face = Field(..., description="Which face the cutout is on")
    center_x: float = Field(..., description="X position on face")
    center_y: float = Field(..., description="Y position on face")
    
    # Dimensions
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    depth: float = Field(..., gt=0, description="Wall thickness to cut through")
    corner_radius: float = Field(default=0.5, ge=0)
    
    # Reference
    connector_type: Optional[ConnectorType] = Field(default=None)
    connector_name: Optional[str] = Field(default=None)
    component_id: Optional[UUID] = Field(default=None)


# =============================================================================
# Style Schemas
# =============================================================================

class EnclosureStyle(BaseModel):
    """Enclosure style parameters."""
    
    style_type: EnclosureStyleType = Field(
        default=EnclosureStyleType.MINIMAL,
        description="Style template to use",
    )
    
    # Wall parameters
    wall_thickness: float = Field(
        default=2.0,
        gt=0,
        le=10,
        description="Wall thickness in mm",
    )
    floor_thickness: float = Field(
        default=2.0,
        gt=0,
        le=10,
        description="Floor thickness in mm",
    )
    lid_thickness: float = Field(
        default=2.0,
        gt=0,
        le=10,
        description="Lid thickness in mm",
    )
    
    # Corner styling
    corner_radius: float = Field(
        default=3.0,
        ge=0,
        le=20,
        description="External corner radius",
    )
    internal_corner_radius: float = Field(
        default=1.0,
        ge=0,
        description="Internal corner radius (fillet)",
    )
    
    # Lid closure
    lid_closure: LidClosureType = Field(
        default=LidClosureType.SNAP_FIT,
        description="How lid attaches",
    )
    lid_overlap: float = Field(
        default=3.0,
        ge=0,
        description="How much lid overlaps base (for snap/friction)",
    )
    
    # Ventilation
    ventilation: VentilationPattern = Field(
        default=VentilationPattern.NONE,
        description="Ventilation pattern",
    )
    vent_slot_width: float = Field(
        default=2.0,
        gt=0,
        description="Width of ventilation slots",
    )
    vent_slot_spacing: float = Field(
        default=3.0,
        gt=0,
        description="Spacing between vent slots",
    )
    
    # Feet/mounting
    add_feet: bool = Field(
        default=False,
        description="Add rubber feet mounting points",
    )
    feet_diameter: float = Field(default=8.0, gt=0)
    feet_inset: float = Field(default=5.0, ge=0)


class EnclosureOptions(BaseModel):
    """Options for enclosure generation."""
    
    # Clearances
    component_clearance: float = Field(
        default=2.0,
        ge=0,
        description="Clearance around components (mm)",
    )
    pcb_standoff_height: float = Field(
        default=5.0,
        gt=0,
        description="Height of PCB standoffs (mm)",
    )
    lid_clearance: float = Field(
        default=3.0,
        ge=0,
        description="Clearance above tallest component to lid",
    )
    
    # Cutouts
    auto_cutouts: bool = Field(
        default=True,
        description="Automatically generate connector cutouts",
    )
    cutout_tolerance: float = Field(
        default=0.3,
        ge=0,
        description="Additional tolerance on cutouts",
    )
    
    # Ventilation
    auto_ventilation: bool = Field(
        default=True,
        description="Auto-add ventilation based on thermal properties",
    )
    
    # Output options
    generate_lid_separately: bool = Field(
        default=True,
        description="Generate lid as separate body",
    )
    add_assembly_guides: bool = Field(
        default=True,
        description="Add alignment features for assembly",
    )


# =============================================================================
# Component Position Schema
# =============================================================================

class ComponentPosition(BaseModel):
    """Position of a component in the enclosure."""
    
    component_id: UUID
    position: Position3D = Field(
        ...,
        description="Position of component origin in enclosure",
    )
    rotation: float = Field(
        default=0,
        ge=0,
        lt=360,
        description="Z-axis rotation in degrees",
    )


class SpatialLayout(BaseModel):
    """Spatial layout of all components in enclosure."""
    
    components: list[ComponentPosition]
    internal_dimensions: Optional[Dimensions] = Field(
        default=None,
        description="Override internal dimensions",
    )
    auto_arrange: bool = Field(
        default=False,
        description="Let AI arrange components automatically",
    )


# =============================================================================
# Request/Response Schemas
# =============================================================================

class EnclosureRequest(BaseModel):
    """Request to generate an enclosure."""
    
    project_id: UUID
    style: EnclosureStyle = Field(default_factory=EnclosureStyle)
    options: EnclosureOptions = Field(default_factory=EnclosureOptions)
    layout: Optional[SpatialLayout] = Field(
        default=None,
        description="Component layout (auto-calculated if None)",
    )
    
    # Optional overrides
    component_ids: Optional[list[UUID]] = Field(
        default=None,
        description="Specific components to include (all if None)",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name for the generated enclosure",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description for the generated enclosure",
    )


class EnclosureResult(BaseModel):
    """Result of enclosure generation."""
    
    # Identifiers
    job_id: UUID
    enclosure_id: Optional[UUID] = None
    
    # Generated geometry info
    external_dimensions: Dimensions
    internal_dimensions: Dimensions
    
    # Generated features
    standoffs: list[Standoff]
    cutouts: list[Cutout]
    
    # Component positions
    component_positions: list[ComponentPosition]
    
    # Files
    step_file_url: Optional[str] = None
    stl_file_url: Optional[str] = None
    lid_step_file_url: Optional[str] = None
    lid_stl_file_url: Optional[str] = None
    
    # Generation info
    cadquery_code: Optional[str] = None
    generation_time_ms: float = 0
    ai_model: Optional[str] = None
    
    # Warnings
    warnings: list[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


# =============================================================================
# Standard Cutout Profiles
# =============================================================================

STANDARD_CUTOUT_PROFILES: dict[ConnectorType, CutoutProfile] = {
    ConnectorType.USB_A: CutoutProfile(
        connector_type=ConnectorType.USB_A,
        width=13.0,
        height=5.5,
        corner_radius=0.5,
    ),
    ConnectorType.USB_C: CutoutProfile(
        connector_type=ConnectorType.USB_C,
        width=9.0,
        height=3.5,
        corner_radius=1.0,
    ),
    ConnectorType.USB_MICRO: CutoutProfile(
        connector_type=ConnectorType.USB_MICRO,
        width=8.0,
        height=3.0,
        corner_radius=0.5,
    ),
    ConnectorType.HDMI: CutoutProfile(
        connector_type=ConnectorType.HDMI,
        width=15.0,
        height=5.5,
        corner_radius=0.5,
    ),
    ConnectorType.HDMI_MINI: CutoutProfile(
        connector_type=ConnectorType.HDMI_MINI,
        width=11.5,
        height=3.5,
        corner_radius=0.5,
    ),
    ConnectorType.HDMI_MICRO: CutoutProfile(
        connector_type=ConnectorType.HDMI_MICRO,
        width=7.0,
        height=3.5,
        corner_radius=0.5,
    ),
    ConnectorType.ETHERNET: CutoutProfile(
        connector_type=ConnectorType.ETHERNET,
        width=16.0,
        height=13.5,
        corner_radius=0.5,
    ),
    ConnectorType.POWER_BARREL: CutoutProfile(
        connector_type=ConnectorType.POWER_BARREL,
        width=9.0,  # Diameter for round cutout
        height=9.0,
        corner_radius=4.5,  # Makes it circular
    ),
    ConnectorType.SD_CARD: CutoutProfile(
        connector_type=ConnectorType.SD_CARD,
        width=24.5,
        height=2.5,
        corner_radius=0.5,
    ),
    ConnectorType.MICROSD: CutoutProfile(
        connector_type=ConnectorType.MICROSD,
        width=13.0,
        height=1.5,
        corner_radius=0.3,
    ),
    ConnectorType.GPIO_HEADER: CutoutProfile(
        connector_type=ConnectorType.GPIO_HEADER,
        width=52.0,  # 40-pin header
        height=6.0,
        corner_radius=0.5,
    ),
    ConnectorType.AUDIO_35MM: CutoutProfile(
        connector_type=ConnectorType.AUDIO_35MM,
        width=7.0,
        height=7.0,
        corner_radius=3.5,  # Circular
    ),
}
