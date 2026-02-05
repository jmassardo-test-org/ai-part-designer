"""
Component Specifications Schemas

Pydantic schemas for mechanical specifications extracted from
datasheets and CAD files.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class LengthUnit(StrEnum):
    """Length measurement units."""

    MM = "mm"
    CM = "cm"
    IN = "in"
    MIL = "mil"


class Face(StrEnum):
    """Component face/side."""

    TOP = "top"
    BOTTOM = "bottom"
    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"


class ConnectorType(StrEnum):
    """Common connector types."""

    USB_A = "usb_a"
    USB_B = "usb_b"
    USB_C = "usb_c"
    USB_MICRO = "usb_micro"
    USB_MINI = "usb_mini"
    HDMI = "hdmi"
    HDMI_MINI = "hdmi_mini"
    HDMI_MICRO = "hdmi_micro"
    DISPLAYPORT = "displayport"
    ETHERNET = "ethernet"
    POWER_BARREL = "power_barrel"
    SD_CARD = "sd_card"
    MICROSD = "microsd"
    GPIO_HEADER = "gpio_header"
    AUDIO_35MM = "audio_35mm"
    SATA = "sata"
    PCIE = "pcie"
    SPI = "spi"
    I2C = "i2c"
    UART = "uart"
    JTAG = "jtag"
    OTHER = "other"


class ThreadSize(StrEnum):
    """Common mounting hole thread sizes."""

    M2 = "M2"
    M2_5 = "M2.5"
    M3 = "M3"
    M4 = "M4"
    M5 = "M5"
    INCH_4_40 = "#4-40"
    INCH_6_32 = "#6-32"
    INCH_8_32 = "#8-32"
    THROUGH_HOLE = "through"
    NONE = "none"


class ClearanceType(StrEnum):
    """Clearance zone types."""

    HEAT_SINK = "heat_sink"
    AIRFLOW = "airflow"
    CABLE_BEND = "cable_bend"
    COMPONENT_HEIGHT = "component_height"
    USER_ACCESS = "user_access"
    LED_VISIBILITY = "led_visibility"
    ANTENNA = "antenna"
    OTHER = "other"


class ExtractionStatus(StrEnum):
    """Extraction job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
    MANUAL = "manual"


# =============================================================================
# Dimension Schemas
# =============================================================================


class Dimensions(BaseModel):
    """Overall component dimensions."""

    length: float = Field(..., gt=0, description="Length/X dimension")
    width: float = Field(..., gt=0, description="Width/Y dimension")
    height: float = Field(..., gt=0, description="Height/Z dimension")
    unit: LengthUnit = Field(default=LengthUnit.MM, description="Unit of measurement")

    # Optional for irregular shapes
    is_approximate: bool = Field(default=False, description="Dimensions are approximate")
    notes: str | None = Field(default=None, description="Additional dimension notes")

    def to_mm(self) -> "Dimensions":
        """Convert dimensions to millimeters."""
        if self.unit == LengthUnit.MM:
            return self

        factors = {
            LengthUnit.CM: 10.0,
            LengthUnit.IN: 25.4,
            LengthUnit.MIL: 0.0254,
        }
        factor = factors.get(self.unit, 1.0)

        return Dimensions(
            length=self.length * factor,
            width=self.width * factor,
            height=self.height * factor,
            unit=LengthUnit.MM,
            is_approximate=self.is_approximate,
            notes=self.notes,
        )


class Position3D(BaseModel):
    """3D position relative to component origin (bottom-left-back corner)."""

    x: float = Field(..., description="X position from left edge")
    y: float = Field(..., description="Y position from back edge")
    z: float = Field(default=0, description="Z position from bottom")
    unit: LengthUnit = Field(default=LengthUnit.MM)


class BoundingBox(BaseModel):
    """3D bounding box for a zone or feature."""

    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    unit: LengthUnit = Field(default=LengthUnit.MM)

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def depth(self) -> float:
        return self.max_y - self.min_y

    @property
    def height(self) -> float:
        return self.max_z - self.min_z


# =============================================================================
# Mounting Hole Schema
# =============================================================================


class MountingHole(BaseModel):
    """A mounting hole on the component."""

    # Position (from bottom-left corner of component)
    x: float = Field(..., description="X position from left edge")
    y: float = Field(..., description="Y position from front edge")
    unit: LengthUnit = Field(default=LengthUnit.MM)

    # Hole dimensions
    diameter: float = Field(..., gt=0, description="Hole diameter")
    depth: float | None = Field(default=None, description="Hole depth (None=through)")

    # Threading
    thread_size: ThreadSize | None = Field(
        default=None,
        description="Thread specification if tapped",
    )
    is_threaded: bool = Field(default=False, description="Whether hole is tapped")

    # Reference
    label: str | None = Field(default=None, description="Hole label from datasheet")
    from_corner: str | None = Field(
        default=None,
        description="Reference corner: bottom_left, bottom_right, etc.",
    )

    # Confidence
    confidence: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Extraction confidence",
    )


class MountingPattern(BaseModel):
    """Common mounting hole patterns."""

    holes: list[MountingHole]
    pattern_name: str | None = Field(
        default=None,
        description="Pattern name: rectangular, triangular, circular",
    )
    spacing_x: float | None = Field(default=None, description="X spacing between holes")
    spacing_y: float | None = Field(default=None, description="Y spacing between holes")
    unit: LengthUnit = Field(default=LengthUnit.MM)


# =============================================================================
# Connector Schema
# =============================================================================


class Connector(BaseModel):
    """A connector/port on the component."""

    # Identification
    name: str = Field(..., description="Connector name: USB-C, HDMI, GPIO")
    type: ConnectorType = Field(..., description="Connector type category")

    # Position on component
    position: Position3D = Field(..., description="Position of connector center")
    face: Face = Field(..., description="Which face the connector is on")

    # Cutout dimensions (for enclosure generation)
    cutout_width: float = Field(..., gt=0, description="Width of required cutout")
    cutout_height: float = Field(..., gt=0, description="Height of required cutout")
    cutout_depth: float = Field(default=0, description="Depth/protrusion from face")

    # Clearance for cables
    cable_clearance: float = Field(
        default=15.0,
        description="Minimum clearance for cable insertion (mm)",
    )
    requires_clearance: bool = Field(
        default=True,
        description="Whether connector needs access clearance",
    )

    # Additional info
    pin_count: int | None = Field(default=None, description="Number of pins")
    label: str | None = Field(default=None, description="Label from datasheet")

    # Confidence
    confidence: float = Field(default=1.0, ge=0, le=1)


# =============================================================================
# Clearance Zone Schema
# =============================================================================


class ClearanceZone(BaseModel):
    """An area requiring clearance above/around the component."""

    name: str = Field(..., description="Zone name: CPU heatsink, GPIO header")
    type: ClearanceType = Field(..., description="Type of clearance needed")
    description: str | None = Field(default=None)

    # Zone bounds
    bounds: BoundingBox = Field(..., description="3D bounds of the zone")

    # Requirements
    minimum_clearance: float = Field(
        default=5.0,
        description="Minimum clearance in mm",
    )
    requires_venting: bool = Field(
        default=False,
        description="Whether zone needs ventilation",
    )

    # For thermal zones
    heat_source: bool = Field(
        default=False,
        description="Whether this zone is a heat source",
    )
    max_temperature: float | None = Field(
        default=None,
        description="Maximum operating temperature (°C)",
    )

    # Confidence
    confidence: float = Field(default=1.0, ge=0, le=1)


# =============================================================================
# Thermal Properties Schema
# =============================================================================


class ThermalProperties(BaseModel):
    """Thermal characteristics of the component."""

    # Temperature ratings
    min_operating_temp: float | None = Field(
        default=None,
        description="Minimum operating temperature (°C)",
    )
    max_operating_temp: float | None = Field(
        default=None,
        description="Maximum operating temperature (°C)",
    )

    # Heat dissipation
    typical_power_consumption: float | None = Field(
        default=None,
        description="Typical power consumption (W)",
    )
    max_power_consumption: float | None = Field(
        default=None,
        description="Maximum power consumption (W)",
    )
    heat_dissipation: float | None = Field(
        default=None,
        description="Heat dissipation (W)",
    )

    # Cooling requirements
    requires_heatsink: bool = Field(
        default=False,
        description="Whether heatsink is recommended",
    )
    requires_active_cooling: bool = Field(
        default=False,
        description="Whether fan/active cooling needed",
    )
    requires_venting: bool = Field(
        default=False,
        description="Whether enclosure needs vent holes",
    )

    # Airflow
    airflow_direction: str | None = Field(
        default=None,
        description="Recommended airflow direction",
    )


# =============================================================================
# Electrical Properties Schema
# =============================================================================


class ElectricalProperties(BaseModel):
    """Electrical characteristics of the component."""

    # Power requirements
    input_voltage_min: float | None = Field(default=None, description="Min input voltage (V)")
    input_voltage_max: float | None = Field(default=None, description="Max input voltage (V)")
    input_voltage_typical: float | None = Field(
        default=None, description="Typical input voltage (V)"
    )

    input_current_typical: float | None = Field(default=None, description="Typical current (A)")
    input_current_max: float | None = Field(default=None, description="Max current (A)")

    # Logic levels
    gpio_voltage: float | None = Field(default=None, description="GPIO voltage level (V)")
    is_5v_tolerant: bool = Field(default=False, description="5V tolerant GPIO")


# =============================================================================
# Complete Component Specifications
# =============================================================================


class ComponentSpecifications(BaseModel):
    """Complete extracted specifications for a component."""

    # Overall dimensions
    dimensions: Dimensions = Field(..., description="Component dimensions")

    # Mounting
    mounting_holes: list[MountingHole] = Field(
        default_factory=list,
        description="All mounting holes",
    )
    mounting_pattern: MountingPattern | None = Field(
        default=None,
        description="Standard mounting pattern if detected",
    )

    # Connectors
    connectors: list[Connector] = Field(
        default_factory=list,
        description="All connectors/ports",
    )

    # Clearance
    clearance_zones: list[ClearanceZone] = Field(
        default_factory=list,
        description="Areas requiring clearance",
    )

    # Properties
    thermal: ThermalProperties | None = Field(default=None)
    electrical: ElectricalProperties | None = Field(default=None)

    # Extraction metadata
    extraction_method: str = Field(
        default="unknown",
        description="How specs were extracted: datasheet, cad, manual",
    )
    overall_confidence: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Overall extraction confidence",
    )
    source_url: str | None = Field(
        default=None,
        description="URL of source datasheet",
    )
    notes: str | None = Field(default=None, description="Additional notes")


# =============================================================================
# CAD Extraction Result
# =============================================================================


class CADExtraction(BaseModel):
    """Result of CAD file dimension extraction."""

    # Bounding box
    bounding_box: BoundingBox

    # Detected features
    detected_holes: list[MountingHole] = Field(default_factory=list)
    detected_openings: list[dict] = Field(
        default_factory=list,
        description="Detected openings/slots",
    )

    # Mesh info (for STL)
    vertex_count: int | None = Field(default=None)
    face_count: int | None = Field(default=None)

    # Analysis
    is_watertight: bool = Field(default=True)
    has_internal_geometry: bool = Field(default=False)
    estimated_volume: float | None = Field(default=None, description="Volume in mm³")

    # Quality
    extraction_quality: str = Field(
        default="good",
        description="Quality: good, partial, poor",
    )
    warnings: list[str] = Field(default_factory=list)


# =============================================================================
# Datasheet Extraction Result
# =============================================================================


class MechanicalDrawing(BaseModel):
    """Extracted mechanical drawing from datasheet."""

    page_number: int
    image_data: str | None = Field(default=None, description="Base64 encoded image")
    dimensions_found: list[dict] = Field(default_factory=list)
    scale: str | None = Field(default=None, description="Drawing scale if specified")
    view_type: str = Field(default="unknown", description="top, side, isometric, etc.")


class DatasheetExtraction(BaseModel):
    """Result of datasheet parsing."""

    # Source info
    page_count: int
    manufacturer: str | None = Field(default=None)
    model_number: str | None = Field(default=None)

    # Extracted specs
    specifications: ComponentSpecifications

    # Mechanical drawings found
    mechanical_drawings: list[MechanicalDrawing] = Field(default_factory=list)

    # Dimension table
    dimension_table: dict | None = Field(
        default=None,
        description="Parsed dimension table if found",
    )

    # Extraction quality
    pages_processed: int
    pages_with_dimensions: list[int] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.0, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
