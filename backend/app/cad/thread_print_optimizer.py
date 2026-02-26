"""
Print-optimized thread profile generator.

Adjusts thread dimensions for reliable 3D printing across FDM, SLA, SLS,
and MJF processes. Provides feasibility assessment, clearance adjustments,
orientation advice, and strength estimates.

All dimensions are in millimeters.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from app.cad.threads import ThreadSpec, ThreadType

# =============================================================================
# Enums
# =============================================================================


class PrintProcess(StrEnum):
    """3D printing process types."""

    FDM = "fdm"  # Fused Deposition Modeling
    SLA = "sla"  # Stereolithography
    SLS = "sls"  # Selective Laser Sintering
    MJF = "mjf"  # Multi Jet Fusion


class ToleranceClass(StrEnum):
    """Thread tolerance/fit classes for printing."""

    TIGHT = "tight"  # Close fit, may need post-processing
    STANDARD = "standard"  # Good balance for most prints
    LOOSE = "loose"  # Easy assembly, forgiving tolerances


class PrintFeasibility(StrEnum):
    """Feasibility rating for printing a thread."""

    EXCELLENT = "excellent"  # Will print well
    GOOD = "good"  # Reasonable results expected
    MARGINAL = "marginal"  # May need tuning/post-processing
    NOT_RECOMMENDED = "not_recommended"  # Too small / too fine


# =============================================================================
# Configuration & Result Dataclasses
# =============================================================================


@dataclass(frozen=True)
class PrintThreadConfig:
    """Immutable configuration for print-optimized thread generation.

    Attributes:
        spec: Base thread specification from the thread data library.
        process: Target 3D printing process.
        tolerance_class: Desired fit/tolerance level.
        thread_type: Whether generating an internal or external thread.
        nozzle_diameter_mm: FDM nozzle diameter in mm.
        layer_height_mm: Layer height in mm.
        use_flat_bottom: Use flat roots instead of V-profile (FDM).
        add_lead_in_chamfer: Add a lead-in chamfer at thread entry.
        custom_clearance_mm: Override the default clearance value.
    """

    spec: ThreadSpec
    process: PrintProcess = PrintProcess.FDM
    tolerance_class: ToleranceClass = ToleranceClass.STANDARD
    thread_type: ThreadType = ThreadType.EXTERNAL
    nozzle_diameter_mm: float = 0.4
    layer_height_mm: float = 0.2
    use_flat_bottom: bool = False
    add_lead_in_chamfer: bool = True
    custom_clearance_mm: float | None = None


@dataclass(frozen=True)
class PrintRecommendation:
    """Printing feasibility assessment and recommendations.

    Attributes:
        feasibility: Overall feasibility rating.
        min_recommended_size: Smallest recommended thread size label.
        recommended_tolerance: Suggested tolerance class.
        clearance_mm: Total radial clearance to add in mm.
        notes: Human-readable recommendation notes.
        orientation_advice: Print orientation guidance.
        estimated_strength_pct: Estimated percentage of machined strength.
    """

    feasibility: PrintFeasibility
    min_recommended_size: str
    recommended_tolerance: ToleranceClass
    clearance_mm: float
    notes: list[str]
    orientation_advice: str
    estimated_strength_pct: float


@dataclass(frozen=True)
class PrintThreadResult:
    """Result of print-optimizing a thread specification.

    Attributes:
        config: The input configuration used.
        adjusted_spec: New ThreadSpec with clearances applied.
        recommendation: Feasibility assessment and recommendations.
        adjustments_applied: Map of adjustment names to values applied.
    """

    config: PrintThreadConfig
    adjusted_spec: ThreadSpec
    recommendation: PrintRecommendation
    adjustments_applied: dict[str, float]


# =============================================================================
# Clearance & Printability Constants
# =============================================================================

CLEARANCE_DEFAULTS: dict[PrintProcess, dict[ToleranceClass, float]] = {
    PrintProcess.FDM: {
        ToleranceClass.TIGHT: 0.15,
        ToleranceClass.STANDARD: 0.3,
        ToleranceClass.LOOSE: 0.5,
    },
    PrintProcess.SLA: {
        ToleranceClass.TIGHT: 0.05,
        ToleranceClass.STANDARD: 0.1,
        ToleranceClass.LOOSE: 0.2,
    },
    PrintProcess.SLS: {
        ToleranceClass.TIGHT: 0.1,
        ToleranceClass.STANDARD: 0.2,
        ToleranceClass.LOOSE: 0.35,
    },
    PrintProcess.MJF: {
        ToleranceClass.TIGHT: 0.1,
        ToleranceClass.STANDARD: 0.15,
        ToleranceClass.LOOSE: 0.3,
    },
}
"""Radial clearance (mm) added to dimensions per process and tolerance."""

MIN_PRINTABLE_PITCH_MM: dict[PrintProcess, float] = {
    PrintProcess.FDM: 1.0,  # ~M6 coarse pitch
    PrintProcess.SLA: 0.5,  # ~M3 coarse pitch
    PrintProcess.SLS: 0.75,  # ~M5
    PrintProcess.MJF: 0.75,  # ~M5
}
"""Minimum thread pitch for reliable printing per process."""

_MIN_RECOMMENDED_SIZES: dict[PrintProcess, str] = {
    PrintProcess.FDM: "M6",
    PrintProcess.SLA: "M3",
    PrintProcess.SLS: "M5",
    PrintProcess.MJF: "M5",
}
"""Smallest recommended thread size label per process."""

_STRENGTH_ESTIMATES: dict[PrintProcess, tuple[float, float]] = {
    PrintProcess.FDM: (40.0, 60.0),
    PrintProcess.SLA: (70.0, 80.0),
    PrintProcess.SLS: (60.0, 75.0),
    PrintProcess.MJF: (65.0, 80.0),
}
"""Estimated strength percentage range (min, max) of machined thread."""


# =============================================================================
# Public API
# =============================================================================


def get_print_recommendation(
    spec: ThreadSpec,
    process: PrintProcess = PrintProcess.FDM,
    nozzle_diameter_mm: float = 0.4,
    layer_height_mm: float = 0.2,
) -> PrintRecommendation:
    """Get printing feasibility and recommendations for a thread spec.

    Evaluates whether a thread can be reliably printed with the given
    process and settings.  Provides actionable recommendations including
    orientation advice, strength estimates, and tolerance suggestions.

    Args:
        spec: Thread specification to evaluate.
        process: Target 3D printing process.
        nozzle_diameter_mm: FDM nozzle diameter in mm.
        layer_height_mm: Print layer height in mm.

    Returns:
        PrintRecommendation with feasibility rating and guidance.
    """
    min_pitch = MIN_PRINTABLE_PITCH_MM[process]
    pitch_ratio = spec.pitch_mm / min_pitch if min_pitch > 0 else 0.0

    # Thread depth is half the difference between major and minor diameters
    thread_depth = (spec.major_diameter - spec.minor_diameter_ext) / 2.0

    notes: list[str] = []

    # --- Feasibility rating ---
    if pitch_ratio >= 2.0:
        feasibility = PrintFeasibility.EXCELLENT
    elif pitch_ratio >= 1.5:
        feasibility = PrintFeasibility.GOOD
    elif pitch_ratio >= 1.0:
        feasibility = PrintFeasibility.MARGINAL
    else:
        feasibility = PrintFeasibility.NOT_RECOMMENDED

    # --- Nozzle / depth check (FDM-specific) ---
    if process == PrintProcess.FDM:
        if thread_depth < 2.0 * nozzle_diameter_mm:
            notes.append(
                f"Thread depth ({thread_depth:.2f} mm) is less than "
                f"2x nozzle diameter ({nozzle_diameter_mm} mm); "
                "detail may be lost."
            )
            if feasibility in (
                PrintFeasibility.EXCELLENT,
                PrintFeasibility.GOOD,
            ):
                feasibility = PrintFeasibility.MARGINAL

    # --- Layer height note ---
    if layer_height_mm > spec.pitch_mm / 4.0:
        notes.append(
            f"Layer height ({layer_height_mm} mm) is large relative to "
            f"pitch ({spec.pitch_mm} mm); consider reducing layer height."
        )

    # --- Feasibility-specific notes ---
    if feasibility == PrintFeasibility.NOT_RECOMMENDED:
        notes.append(
            f"Thread pitch ({spec.pitch_mm} mm) is below the minimum "
            f"recommended ({min_pitch} mm) for {process.value.upper()}."
        )
    elif feasibility == PrintFeasibility.MARGINAL:
        notes.append("Thread may require post-processing or careful tuning.")

    # --- Strength estimate (midpoint of range) ---
    strength_lo, strength_hi = _STRENGTH_ESTIMATES[process]
    if feasibility == PrintFeasibility.EXCELLENT:
        estimated_strength = strength_hi
    elif feasibility == PrintFeasibility.GOOD:
        estimated_strength = (strength_lo + strength_hi) / 2.0
    elif feasibility == PrintFeasibility.MARGINAL:
        estimated_strength = strength_lo
    else:
        estimated_strength = strength_lo * 0.75

    # --- Recommended tolerance ---
    if feasibility in (
        PrintFeasibility.MARGINAL,
        PrintFeasibility.NOT_RECOMMENDED,
    ):
        recommended_tolerance = ToleranceClass.LOOSE
    else:
        recommended_tolerance = ToleranceClass.STANDARD

    clearance = CLEARANCE_DEFAULTS[process][recommended_tolerance]
    orientation = get_orientation_advice(spec, process)

    return PrintRecommendation(
        feasibility=feasibility,
        min_recommended_size=_MIN_RECOMMENDED_SIZES[process],
        recommended_tolerance=recommended_tolerance,
        clearance_mm=clearance,
        notes=notes,
        orientation_advice=orientation,
        estimated_strength_pct=estimated_strength,
    )


def optimize_thread_for_print(
    config: PrintThreadConfig,
) -> PrintThreadResult:
    """Adjust thread dimensions for 3D printing.

    Applies clearance adjustments based on process, tolerance class, and
    thread type.  External threads have diameters reduced; internal
    threads have diameters increased.  Returns a new ThreadSpec with all
    adjustments documented.

    Args:
        config: Print-optimized thread configuration.

    Returns:
        PrintThreadResult containing the adjusted spec, recommendation,
        and a log of all adjustments applied.
    """
    # Determine clearance value
    if config.custom_clearance_mm is not None:
        clearance = config.custom_clearance_mm
    else:
        clearance = CLEARANCE_DEFAULTS[config.process][config.tolerance_class]

    adjustments: dict[str, float] = {}

    # Apply clearance depending on thread type
    sign = -1.0 if config.thread_type == ThreadType.EXTERNAL else 1.0

    new_major = config.spec.major_diameter + sign * clearance
    new_minor_ext = config.spec.minor_diameter_ext + sign * clearance
    new_pitch_ext = config.spec.pitch_diameter_ext + sign * clearance
    new_major_int = config.spec.major_diameter_int + sign * clearance
    new_minor_int = config.spec.minor_diameter_int + sign * clearance
    new_pitch_int = config.spec.pitch_diameter_int + sign * clearance

    adjustments["major_diameter"] = sign * clearance
    adjustments["minor_diameter_ext"] = sign * clearance
    adjustments["pitch_diameter_ext"] = sign * clearance
    adjustments["major_diameter_int"] = sign * clearance
    adjustments["minor_diameter_int"] = sign * clearance
    adjustments["pitch_diameter_int"] = sign * clearance
    adjustments["clearance_mm"] = clearance

    if config.use_flat_bottom:
        adjustments["flat_bottom"] = 1.0

    # Build adjusted ThreadSpec (frozen, so use dataclasses.replace)
    adjusted_spec = replace(
        config.spec,
        major_diameter=new_major,
        minor_diameter_ext=new_minor_ext,
        pitch_diameter_ext=new_pitch_ext,
        major_diameter_int=new_major_int,
        minor_diameter_int=new_minor_int,
        pitch_diameter_int=new_pitch_int,
    )

    recommendation = get_print_recommendation(
        spec=config.spec,
        process=config.process,
        nozzle_diameter_mm=config.nozzle_diameter_mm,
        layer_height_mm=config.layer_height_mm,
    )

    return PrintThreadResult(
        config=config,
        adjusted_spec=adjusted_spec,
        recommendation=recommendation,
        adjustments_applied=adjustments,
    )


def get_orientation_advice(
    spec: ThreadSpec,  # noqa: ARG001
    process: PrintProcess,
) -> str:
    """Get print orientation advice for a thread.

    Provides process-specific guidance on how to orient the part during
    printing for best thread quality.

    Args:
        spec: Thread specification (used for context in advice).
        process: Target 3D printing process.

    Returns:
        Human-readable orientation advice string.
    """
    advice_map: dict[PrintProcess, str] = {
        PrintProcess.FDM: (
            "Print with thread axis vertical (Z-axis) for best thread "
            "quality. Avoid horizontal orientation as layer lines will "
            "cross thread crests."
        ),
        PrintProcess.SLA: (
            "Any orientation works; vertical alignment reduces support "
            "contact with thread surfaces and preserves detail."
        ),
        PrintProcess.SLS: (
            "Orientation is flexible with SLS. Vertical alignment can "
            "improve dimensional accuracy of thread profiles."
        ),
        PrintProcess.MJF: (
            "Vertical alignment recommended for best surface finish on "
            "thread flanks. MJF detail resolution is orientation-dependent."
        ),
    }
    return advice_map.get(process, "No specific orientation advice available.")
