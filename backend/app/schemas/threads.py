"""
Thread library Pydantic schemas.

Request and response models for the thread standards API (v2).
Covers thread family listing, spec lookup, tap drill info,
thread generation, and print-optimised generation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Response Models — Thread Standards
# =============================================================================


class ThreadFamilyResponse(BaseModel):
    """Response for a single thread family."""

    model_config = ConfigDict(from_attributes=True)

    family: str = Field(description="Family identifier")
    name: str = Field(description="Human-readable name")
    description: str = Field(description="Family description")
    standard_ref: str = Field(description="Standard reference")
    size_count: int = Field(description="Number of sizes available")


class ThreadFamilyListResponse(BaseModel):
    """Response listing all thread families."""

    families: list[ThreadFamilyResponse]
    total: int


class ThreadSpecResponse(BaseModel):
    """Complete thread specification response."""

    model_config = ConfigDict(from_attributes=True)

    family: str
    size: str
    pitch_mm: float
    form: str
    pitch_series: str | None = None
    major_diameter: float
    pitch_diameter_ext: float
    minor_diameter_ext: float
    major_diameter_int: float
    pitch_diameter_int: float
    minor_diameter_int: float
    profile_angle_deg: float
    taper_per_mm: float
    tap_drill_mm: float
    clearance_hole_close_mm: float
    clearance_hole_medium_mm: float
    clearance_hole_free_mm: float
    tpi: float | None = None
    nominal_size_inch: str | None = None
    engagement_length_mm: float
    standard_ref: str
    notes: str


class ThreadSizeListResponse(BaseModel):
    """Response listing available sizes for a family."""

    family: str
    sizes: list[str]
    total: int
    pitch_series: str | None = None


class TapDrillResponse(BaseModel):
    """Tap drill and clearance hole information."""

    family: str
    size: str
    tap_drill_mm: float
    clearance_hole_close_mm: float
    clearance_hole_medium_mm: float
    clearance_hole_free_mm: float


# =============================================================================
# Request / Response Models — Thread Generation
# =============================================================================


class ThreadGenerateRequest(BaseModel):
    """Request to generate thread geometry."""

    family: str = Field(description="Thread family")
    size: str = Field(description="Thread size")
    thread_type: str = Field(
        default="external",
        description="internal or external",
    )
    length_mm: float = Field(
        gt=0,
        le=200,
        description="Thread length in mm",
    )
    hand: str = Field(default="right", description="right or left")
    pitch_series: str | None = Field(
        default=None,
        description="coarse or fine (metric)",
    )
    custom_pitch_mm: float | None = Field(
        default=None,
        gt=0,
        description="Override pitch",
    )
    custom_diameter_mm: float | None = Field(
        default=None,
        gt=0,
        description="Override diameter",
    )
    add_chamfer: bool = Field(
        default=True,
        description="Add lead-in chamfer",
    )


class ThreadGenerateResponse(BaseModel):
    """Response from thread generation."""

    success: bool
    metadata: dict
    generation_time_ms: int
    estimated_face_count: int
    message: str


# =============================================================================
# Request / Response Models — Print-Optimised Generation
# =============================================================================


class PrintOptimizedGenerateRequest(BaseModel):
    """Request to generate print-optimized thread."""

    family: str = Field(description="Thread family")
    size: str = Field(description="Thread size")
    thread_type: str = Field(
        default="external",
        description="internal or external",
    )
    length_mm: float = Field(
        gt=0,
        le=200,
        description="Thread length in mm",
    )
    process: str = Field(
        default="fdm",
        description="fdm, sla, sls, or mjf",
    )
    tolerance_class: str = Field(
        default="standard",
        description="tight, standard, or loose",
    )
    nozzle_diameter_mm: float = Field(
        default=0.4,
        gt=0,
        le=2.0,
        description="FDM nozzle diameter in mm",
    )
    layer_height_mm: float = Field(
        default=0.2,
        gt=0,
        le=1.0,
        description="Print layer height in mm",
    )
    use_flat_bottom: bool = False
    custom_clearance_mm: float | None = Field(
        default=None,
        ge=0,
        description="Override clearance value",
    )
    pitch_series: str | None = None
    hand: str = "right"
    add_chamfer: bool = True


class PrintRecommendationResponse(BaseModel):
    """Print feasibility recommendation."""

    family: str
    size: str
    feasibility: str
    min_recommended_size: str
    recommended_tolerance: str
    clearance_mm: float
    notes: list[str]
    orientation_advice: str
    estimated_strength_pct: float


class PrintOptimizedGenerateResponse(BaseModel):
    """Response from print-optimized thread generation."""

    success: bool
    feasibility: str
    adjustments_applied: dict[str, float]
    recommendation: PrintRecommendationResponse
    generation_result: ThreadGenerateResponse | None = None
    message: str
