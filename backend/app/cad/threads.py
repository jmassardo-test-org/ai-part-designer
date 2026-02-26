"""
Standard thread data library for CAD assemblies.

Provides comprehensive thread specifications for ISO Metric, UNC, UNF, NPT,
BSPP, BSPT, ACME, and Trapezoidal thread families. All dimensions are in
millimeters. Data sourced from ISO 261, ASME B1.1, ASME B1.20.1, ISO 228-1,
ISO 7-1, ASME B1.5, and ISO 2904 standards.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from app.cad.exceptions import ThreadDataError

# =============================================================================
# Enums
# =============================================================================


class ThreadFamily(StrEnum):
    """Thread standard families."""

    ISO_METRIC = "iso_metric"
    UNC = "unc"
    UNF = "unf"
    NPT = "npt"
    BSPP = "bspp"
    BSPT = "bspt"
    ACME = "acme"
    TRAPEZOIDAL = "trapezoidal"


class ThreadType(StrEnum):
    """Internal vs external thread."""

    INTERNAL = "internal"
    EXTERNAL = "external"


class PitchSeries(StrEnum):
    """Pitch classification within a family."""

    COARSE = "coarse"
    FINE = "fine"
    SUPERFINE = "superfine"


class ThreadForm(StrEnum):
    """Thread profile geometry."""

    TRIANGULAR = "triangular"
    TRUNCATED_TRIANGULAR = "truncated_triangular"
    TRAPEZOIDAL = "trapezoidal"
    ACME = "acme"
    NPT = "npt"
    SQUARE = "square"


class ThreadHand(StrEnum):
    """Thread helix direction."""

    RIGHT = "right"
    LEFT = "left"


# =============================================================================
# ThreadSpec dataclass
# =============================================================================


@dataclass(frozen=True)
class ThreadSpec:
    """
    Complete specification for a single thread size.

    All linear dimensions are in millimeters.
    Angles are in degrees.

    Attributes:
        family: Thread standard family.
        size: Human-readable size label (e.g. "M8", "1/4-20").
        pitch_mm: Axial distance between threads in mm.
        form: Thread profile geometry.
        pitch_series: Coarse/fine/superfine classification.
        major_diameter: Nominal (major) diameter for external thread.
        pitch_diameter_ext: Pitch diameter for external thread.
        minor_diameter_ext: Minor diameter for external thread.
        major_diameter_int: Major diameter for internal thread.
        pitch_diameter_int: Pitch diameter for internal thread.
        minor_diameter_int: Minor diameter for internal thread.
        profile_angle_deg: Included angle of the thread profile.
        taper_per_mm: Taper per mm of axial length (0 for parallel).
        tap_drill_mm: Recommended tap drill diameter.
        clearance_hole_close_mm: Close-fit clearance hole diameter.
        clearance_hole_medium_mm: Medium-fit clearance hole diameter.
        clearance_hole_free_mm: Free-fit clearance hole diameter.
        tpi: Threads per inch (imperial families).
        nominal_size_inch: Nominal size in inches (imperial families).
        engagement_length_mm: Recommended thread engagement length.
        standard_ref: Reference standard designation.
        notes: Additional notes or caveats.
    """

    family: ThreadFamily
    size: str
    pitch_mm: float
    form: ThreadForm = ThreadForm.TRIANGULAR
    pitch_series: PitchSeries | None = None
    major_diameter: float = 0.0
    pitch_diameter_ext: float = 0.0
    minor_diameter_ext: float = 0.0
    major_diameter_int: float = 0.0
    pitch_diameter_int: float = 0.0
    minor_diameter_int: float = 0.0
    profile_angle_deg: float = 60.0
    taper_per_mm: float = 0.0
    tap_drill_mm: float = 0.0
    clearance_hole_close_mm: float = 0.0
    clearance_hole_medium_mm: float = 0.0
    clearance_hole_free_mm: float = 0.0
    tpi: float | None = None
    nominal_size_inch: str | None = None
    engagement_length_mm: float = 0.0
    standard_ref: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, omitting None optional fields.

        Returns:
            Dictionary representation with None-valued optional fields removed.
        """
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


# =============================================================================
# ISO Metric Coarse Threads (ISO 261)
# =============================================================================

ISO_METRIC_COARSE: dict[str, ThreadSpec] = {
    "M2": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M2",
        pitch_mm=0.4,
        pitch_series=PitchSeries.COARSE,
        major_diameter=2.0,
        pitch_diameter_ext=1.740,
        minor_diameter_ext=1.509,
        major_diameter_int=2.0,
        pitch_diameter_int=1.740,
        minor_diameter_int=1.567,
        tap_drill_mm=1.6,
        clearance_hole_close_mm=2.2,
        clearance_hole_medium_mm=2.4,
        clearance_hole_free_mm=2.6,
        standard_ref="ISO 261",
    ),
    "M2.5": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M2.5",
        pitch_mm=0.45,
        pitch_series=PitchSeries.COARSE,
        major_diameter=2.5,
        pitch_diameter_ext=2.208,
        minor_diameter_ext=1.948,
        major_diameter_int=2.5,
        pitch_diameter_int=2.208,
        minor_diameter_int=2.013,
        tap_drill_mm=2.05,
        clearance_hole_close_mm=2.7,
        clearance_hole_medium_mm=2.9,
        clearance_hole_free_mm=3.1,
        standard_ref="ISO 261",
    ),
    "M3": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M3",
        pitch_mm=0.5,
        pitch_series=PitchSeries.COARSE,
        major_diameter=3.0,
        pitch_diameter_ext=2.675,
        minor_diameter_ext=2.387,
        major_diameter_int=3.0,
        pitch_diameter_int=2.675,
        minor_diameter_int=2.459,
        tap_drill_mm=2.5,
        clearance_hole_close_mm=3.2,
        clearance_hole_medium_mm=3.4,
        clearance_hole_free_mm=3.6,
        standard_ref="ISO 261",
    ),
    "M4": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M4",
        pitch_mm=0.7,
        pitch_series=PitchSeries.COARSE,
        major_diameter=4.0,
        pitch_diameter_ext=3.545,
        minor_diameter_ext=3.141,
        major_diameter_int=4.0,
        pitch_diameter_int=3.545,
        minor_diameter_int=3.242,
        tap_drill_mm=3.3,
        clearance_hole_close_mm=4.3,
        clearance_hole_medium_mm=4.5,
        clearance_hole_free_mm=4.8,
        standard_ref="ISO 261",
    ),
    "M5": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M5",
        pitch_mm=0.8,
        pitch_series=PitchSeries.COARSE,
        major_diameter=5.0,
        pitch_diameter_ext=4.480,
        minor_diameter_ext=4.019,
        major_diameter_int=5.0,
        pitch_diameter_int=4.480,
        minor_diameter_int=4.134,
        tap_drill_mm=4.2,
        clearance_hole_close_mm=5.3,
        clearance_hole_medium_mm=5.5,
        clearance_hole_free_mm=5.8,
        standard_ref="ISO 261",
    ),
    "M6": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M6",
        pitch_mm=1.0,
        pitch_series=PitchSeries.COARSE,
        major_diameter=6.0,
        pitch_diameter_ext=5.350,
        minor_diameter_ext=4.773,
        major_diameter_int=6.0,
        pitch_diameter_int=5.350,
        minor_diameter_int=4.917,
        tap_drill_mm=5.0,
        clearance_hole_close_mm=6.4,
        clearance_hole_medium_mm=6.6,
        clearance_hole_free_mm=7.0,
        standard_ref="ISO 261",
    ),
    "M8": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M8",
        pitch_mm=1.25,
        pitch_series=PitchSeries.COARSE,
        major_diameter=8.0,
        pitch_diameter_ext=7.188,
        minor_diameter_ext=6.466,
        major_diameter_int=8.0,
        pitch_diameter_int=7.188,
        minor_diameter_int=6.647,
        tap_drill_mm=6.8,
        clearance_hole_close_mm=8.4,
        clearance_hole_medium_mm=9.0,
        clearance_hole_free_mm=10.0,
        standard_ref="ISO 261",
    ),
    "M10": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M10",
        pitch_mm=1.5,
        pitch_series=PitchSeries.COARSE,
        major_diameter=10.0,
        pitch_diameter_ext=9.026,
        minor_diameter_ext=8.160,
        major_diameter_int=10.0,
        pitch_diameter_int=9.026,
        minor_diameter_int=8.376,
        tap_drill_mm=8.5,
        clearance_hole_close_mm=10.5,
        clearance_hole_medium_mm=11.0,
        clearance_hole_free_mm=12.0,
        standard_ref="ISO 261",
    ),
    "M12": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M12",
        pitch_mm=1.75,
        pitch_series=PitchSeries.COARSE,
        major_diameter=12.0,
        pitch_diameter_ext=10.863,
        minor_diameter_ext=9.853,
        major_diameter_int=12.0,
        pitch_diameter_int=10.863,
        minor_diameter_int=10.106,
        tap_drill_mm=10.2,
        clearance_hole_close_mm=13.0,
        clearance_hole_medium_mm=13.5,
        clearance_hole_free_mm=14.5,
        standard_ref="ISO 261",
    ),
    "M16": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M16",
        pitch_mm=2.0,
        pitch_series=PitchSeries.COARSE,
        major_diameter=16.0,
        pitch_diameter_ext=14.701,
        minor_diameter_ext=13.546,
        major_diameter_int=16.0,
        pitch_diameter_int=14.701,
        minor_diameter_int=13.835,
        tap_drill_mm=14.0,
        clearance_hole_close_mm=17.0,
        clearance_hole_medium_mm=17.5,
        clearance_hole_free_mm=18.0,
        standard_ref="ISO 261",
    ),
    "M20": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M20",
        pitch_mm=2.5,
        pitch_series=PitchSeries.COARSE,
        major_diameter=20.0,
        pitch_diameter_ext=18.376,
        minor_diameter_ext=16.933,
        major_diameter_int=20.0,
        pitch_diameter_int=18.376,
        minor_diameter_int=17.294,
        tap_drill_mm=17.5,
        clearance_hole_close_mm=21.0,
        clearance_hole_medium_mm=22.0,
        clearance_hole_free_mm=24.0,
        standard_ref="ISO 261",
    ),
    "M24": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M24",
        pitch_mm=3.0,
        pitch_series=PitchSeries.COARSE,
        major_diameter=24.0,
        pitch_diameter_ext=22.051,
        minor_diameter_ext=20.319,
        major_diameter_int=24.0,
        pitch_diameter_int=22.051,
        minor_diameter_int=20.752,
        tap_drill_mm=21.0,
        clearance_hole_close_mm=25.0,
        clearance_hole_medium_mm=26.0,
        clearance_hole_free_mm=28.0,
        standard_ref="ISO 261",
    ),
}


# =============================================================================
# ISO Metric Fine Threads (ISO 261)
# =============================================================================

ISO_METRIC_FINE: dict[str, ThreadSpec] = {
    "M8x1.0": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M8x1.0",
        pitch_mm=1.0,
        pitch_series=PitchSeries.FINE,
        major_diameter=8.0,
        pitch_diameter_ext=7.350,
        minor_diameter_ext=6.773,
        major_diameter_int=8.0,
        pitch_diameter_int=7.350,
        minor_diameter_int=6.917,
        tap_drill_mm=7.0,
        clearance_hole_close_mm=8.4,
        clearance_hole_medium_mm=9.0,
        clearance_hole_free_mm=10.0,
        standard_ref="ISO 261",
    ),
    "M10x1.0": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M10x1.0",
        pitch_mm=1.0,
        pitch_series=PitchSeries.FINE,
        major_diameter=10.0,
        pitch_diameter_ext=9.350,
        minor_diameter_ext=8.773,
        major_diameter_int=10.0,
        pitch_diameter_int=9.350,
        minor_diameter_int=8.917,
        tap_drill_mm=9.0,
        clearance_hole_close_mm=10.5,
        clearance_hole_medium_mm=11.0,
        clearance_hole_free_mm=12.0,
        standard_ref="ISO 261",
    ),
    "M10x1.25": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M10x1.25",
        pitch_mm=1.25,
        pitch_series=PitchSeries.FINE,
        major_diameter=10.0,
        pitch_diameter_ext=9.188,
        minor_diameter_ext=8.466,
        major_diameter_int=10.0,
        pitch_diameter_int=9.188,
        minor_diameter_int=8.647,
        tap_drill_mm=8.8,
        clearance_hole_close_mm=10.5,
        clearance_hole_medium_mm=11.0,
        clearance_hole_free_mm=12.0,
        standard_ref="ISO 261",
    ),
    "M12x1.25": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M12x1.25",
        pitch_mm=1.25,
        pitch_series=PitchSeries.FINE,
        major_diameter=12.0,
        pitch_diameter_ext=11.188,
        minor_diameter_ext=10.466,
        major_diameter_int=12.0,
        pitch_diameter_int=11.188,
        minor_diameter_int=10.647,
        tap_drill_mm=10.8,
        clearance_hole_close_mm=13.0,
        clearance_hole_medium_mm=13.5,
        clearance_hole_free_mm=14.5,
        standard_ref="ISO 261",
    ),
    "M12x1.5": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M12x1.5",
        pitch_mm=1.5,
        pitch_series=PitchSeries.FINE,
        major_diameter=12.0,
        pitch_diameter_ext=11.026,
        minor_diameter_ext=10.160,
        major_diameter_int=12.0,
        pitch_diameter_int=11.026,
        minor_diameter_int=10.376,
        tap_drill_mm=10.5,
        clearance_hole_close_mm=13.0,
        clearance_hole_medium_mm=13.5,
        clearance_hole_free_mm=14.5,
        standard_ref="ISO 261",
    ),
    "M16x1.5": ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M16x1.5",
        pitch_mm=1.5,
        pitch_series=PitchSeries.FINE,
        major_diameter=16.0,
        pitch_diameter_ext=15.026,
        minor_diameter_ext=14.160,
        major_diameter_int=16.0,
        pitch_diameter_int=15.026,
        minor_diameter_int=14.376,
        tap_drill_mm=14.5,
        clearance_hole_close_mm=17.0,
        clearance_hole_medium_mm=17.5,
        clearance_hole_free_mm=18.0,
        standard_ref="ISO 261",
    ),
}


# =============================================================================
# UNC Threads (ASME B1.1)
# =============================================================================

UNC_THREADS: dict[str, ThreadSpec] = {
    "#6-32": ThreadSpec(
        family=ThreadFamily.UNC,
        size="#6-32",
        pitch_mm=0.794,
        pitch_series=PitchSeries.COARSE,
        major_diameter=3.505,
        pitch_diameter_ext=3.073,
        minor_diameter_ext=2.717,
        tap_drill_mm=2.85,
        clearance_hole_close_mm=3.6,
        clearance_hole_medium_mm=3.8,
        clearance_hole_free_mm=4.1,
        tpi=32.0,
        nominal_size_inch='#6 (0.138")',
        standard_ref="ASME B1.1",
    ),
    "#8-32": ThreadSpec(
        family=ThreadFamily.UNC,
        size="#8-32",
        pitch_mm=0.794,
        pitch_series=PitchSeries.COARSE,
        major_diameter=4.166,
        pitch_diameter_ext=3.734,
        minor_diameter_ext=3.378,
        tap_drill_mm=3.45,
        clearance_hole_close_mm=4.3,
        clearance_hole_medium_mm=4.5,
        clearance_hole_free_mm=4.8,
        tpi=32.0,
        nominal_size_inch='#8 (0.164")',
        standard_ref="ASME B1.1",
    ),
    "#10-24": ThreadSpec(
        family=ThreadFamily.UNC,
        size="#10-24",
        pitch_mm=1.058,
        pitch_series=PitchSeries.COARSE,
        major_diameter=4.826,
        pitch_diameter_ext=4.248,
        minor_diameter_ext=3.767,
        tap_drill_mm=3.90,
        clearance_hole_close_mm=5.1,
        clearance_hole_medium_mm=5.3,
        clearance_hole_free_mm=5.6,
        tpi=24.0,
        nominal_size_inch='#10 (0.190")',
        standard_ref="ASME B1.1",
    ),
    "#10-32": ThreadSpec(
        family=ThreadFamily.UNC,
        size="#10-32",
        pitch_mm=0.794,
        pitch_series=PitchSeries.COARSE,
        major_diameter=4.826,
        pitch_diameter_ext=4.394,
        minor_diameter_ext=4.038,
        tap_drill_mm=4.09,
        clearance_hole_close_mm=5.1,
        clearance_hole_medium_mm=5.3,
        clearance_hole_free_mm=5.6,
        tpi=32.0,
        nominal_size_inch='#10 (0.190")',
        standard_ref="ASME B1.1",
    ),
    "1/4-20": ThreadSpec(
        family=ThreadFamily.UNC,
        size="1/4-20",
        pitch_mm=1.270,
        pitch_series=PitchSeries.COARSE,
        major_diameter=6.350,
        pitch_diameter_ext=5.657,
        minor_diameter_ext=5.080,
        tap_drill_mm=5.10,
        clearance_hole_close_mm=6.6,
        clearance_hole_medium_mm=6.9,
        clearance_hole_free_mm=7.4,
        tpi=20.0,
        nominal_size_inch='1/4"',
        standard_ref="ASME B1.1",
    ),
    "5/16-18": ThreadSpec(
        family=ThreadFamily.UNC,
        size="5/16-18",
        pitch_mm=1.411,
        pitch_series=PitchSeries.COARSE,
        major_diameter=7.938,
        pitch_diameter_ext=7.149,
        minor_diameter_ext=6.487,
        tap_drill_mm=6.60,
        clearance_hole_close_mm=8.3,
        clearance_hole_medium_mm=8.7,
        clearance_hole_free_mm=9.1,
        tpi=18.0,
        nominal_size_inch='5/16"',
        standard_ref="ASME B1.1",
    ),
    "3/8-16": ThreadSpec(
        family=ThreadFamily.UNC,
        size="3/8-16",
        pitch_mm=1.588,
        pitch_series=PitchSeries.COARSE,
        major_diameter=9.525,
        pitch_diameter_ext=8.641,
        minor_diameter_ext=7.899,
        tap_drill_mm=7.94,
        clearance_hole_close_mm=9.9,
        clearance_hole_medium_mm=10.3,
        clearance_hole_free_mm=10.7,
        tpi=16.0,
        nominal_size_inch='3/8"',
        standard_ref="ASME B1.1",
    ),
    "1/2-13": ThreadSpec(
        family=ThreadFamily.UNC,
        size="1/2-13",
        pitch_mm=1.954,
        pitch_series=PitchSeries.COARSE,
        major_diameter=12.700,
        pitch_diameter_ext=11.607,
        minor_diameter_ext=10.681,
        tap_drill_mm=10.80,
        clearance_hole_close_mm=13.1,
        clearance_hole_medium_mm=13.5,
        clearance_hole_free_mm=14.3,
        tpi=13.0,
        nominal_size_inch='1/2"',
        standard_ref="ASME B1.1",
    ),
    "5/8-11": ThreadSpec(
        family=ThreadFamily.UNC,
        size="5/8-11",
        pitch_mm=2.309,
        pitch_series=PitchSeries.COARSE,
        major_diameter=15.875,
        pitch_diameter_ext=14.584,
        minor_diameter_ext=13.495,
        tap_drill_mm=13.50,
        clearance_hole_close_mm=16.3,
        clearance_hole_medium_mm=16.7,
        clearance_hole_free_mm=17.5,
        tpi=11.0,
        nominal_size_inch='5/8"',
        standard_ref="ASME B1.1",
    ),
    "3/4-10": ThreadSpec(
        family=ThreadFamily.UNC,
        size="3/4-10",
        pitch_mm=2.540,
        pitch_series=PitchSeries.COARSE,
        major_diameter=19.050,
        pitch_diameter_ext=17.627,
        minor_diameter_ext=16.424,
        tap_drill_mm=16.50,
        clearance_hole_close_mm=19.5,
        clearance_hole_medium_mm=20.0,
        clearance_hole_free_mm=21.0,
        tpi=10.0,
        nominal_size_inch='3/4"',
        standard_ref="ASME B1.1",
    ),
}


# =============================================================================
# UNF Threads (ASME B1.1)
# =============================================================================

UNF_THREADS: dict[str, ThreadSpec] = {
    "#6-40": ThreadSpec(
        family=ThreadFamily.UNF,
        size="#6-40",
        pitch_mm=0.635,
        pitch_series=PitchSeries.FINE,
        major_diameter=3.505,
        pitch_diameter_ext=3.153,
        minor_diameter_ext=2.860,
        tap_drill_mm=2.95,
        clearance_hole_close_mm=3.6,
        clearance_hole_medium_mm=3.8,
        clearance_hole_free_mm=4.1,
        tpi=40.0,
        nominal_size_inch='#6 (0.138")',
        standard_ref="ASME B1.1",
    ),
    "#8-36": ThreadSpec(
        family=ThreadFamily.UNF,
        size="#8-36",
        pitch_mm=0.706,
        pitch_series=PitchSeries.FINE,
        major_diameter=4.166,
        pitch_diameter_ext=3.780,
        minor_diameter_ext=3.454,
        tap_drill_mm=3.50,
        clearance_hole_close_mm=4.3,
        clearance_hole_medium_mm=4.5,
        clearance_hole_free_mm=4.8,
        tpi=36.0,
        nominal_size_inch='#8 (0.164")',
        standard_ref="ASME B1.1",
    ),
    "#10-32": ThreadSpec(
        family=ThreadFamily.UNF,
        size="#10-32",
        pitch_mm=0.794,
        pitch_series=PitchSeries.FINE,
        major_diameter=4.826,
        pitch_diameter_ext=4.394,
        minor_diameter_ext=4.038,
        tap_drill_mm=4.09,
        clearance_hole_close_mm=5.1,
        clearance_hole_medium_mm=5.3,
        clearance_hole_free_mm=5.6,
        tpi=32.0,
        nominal_size_inch='#10 (0.190")',
        standard_ref="ASME B1.1",
    ),
    "1/4-28": ThreadSpec(
        family=ThreadFamily.UNF,
        size="1/4-28",
        pitch_mm=0.907,
        pitch_series=PitchSeries.FINE,
        major_diameter=6.350,
        pitch_diameter_ext=5.842,
        minor_diameter_ext=5.410,
        tap_drill_mm=5.50,
        clearance_hole_close_mm=6.6,
        clearance_hole_medium_mm=6.9,
        clearance_hole_free_mm=7.4,
        tpi=28.0,
        nominal_size_inch='1/4"',
        standard_ref="ASME B1.1",
    ),
    "5/16-24": ThreadSpec(
        family=ThreadFamily.UNF,
        size="5/16-24",
        pitch_mm=1.058,
        pitch_series=PitchSeries.FINE,
        major_diameter=7.938,
        pitch_diameter_ext=7.360,
        minor_diameter_ext=6.879,
        tap_drill_mm=6.90,
        clearance_hole_close_mm=8.3,
        clearance_hole_medium_mm=8.7,
        clearance_hole_free_mm=9.1,
        tpi=24.0,
        nominal_size_inch='5/16"',
        standard_ref="ASME B1.1",
    ),
    "3/8-24": ThreadSpec(
        family=ThreadFamily.UNF,
        size="3/8-24",
        pitch_mm=1.058,
        pitch_series=PitchSeries.FINE,
        major_diameter=9.525,
        pitch_diameter_ext=8.947,
        minor_diameter_ext=8.466,
        tap_drill_mm=8.50,
        clearance_hole_close_mm=9.9,
        clearance_hole_medium_mm=10.3,
        clearance_hole_free_mm=10.7,
        tpi=24.0,
        nominal_size_inch='3/8"',
        standard_ref="ASME B1.1",
    ),
    "1/2-20": ThreadSpec(
        family=ThreadFamily.UNF,
        size="1/2-20",
        pitch_mm=1.270,
        pitch_series=PitchSeries.FINE,
        major_diameter=12.700,
        pitch_diameter_ext=12.007,
        minor_diameter_ext=11.430,
        tap_drill_mm=11.50,
        clearance_hole_close_mm=13.1,
        clearance_hole_medium_mm=13.5,
        clearance_hole_free_mm=14.3,
        tpi=20.0,
        nominal_size_inch='1/2"',
        standard_ref="ASME B1.1",
    ),
}


# =============================================================================
# NPT Threads (ASME B1.20.1)
# Taper: 1:16 on diameter = 0.0625 in/in per side ≈ 0.0625 taper_per_mm
# 60° included angle
# =============================================================================

NPT_THREADS: dict[str, ThreadSpec] = {
    "1/8": ThreadSpec(
        family=ThreadFamily.NPT,
        size="1/8",
        pitch_mm=0.941,
        form=ThreadForm.NPT,
        major_diameter=10.287,
        pitch_diameter_ext=9.728,
        minor_diameter_ext=9.169,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,
        tap_drill_mm=8.73,
        tpi=27.0,
        nominal_size_inch='1/8"',
        engagement_length_mm=6.71,
        standard_ref="ASME B1.20.1",
    ),
    "1/4": ThreadSpec(
        family=ThreadFamily.NPT,
        size="1/4",
        pitch_mm=1.411,
        form=ThreadForm.NPT,
        major_diameter=13.716,
        pitch_diameter_ext=12.926,
        minor_diameter_ext=12.136,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,
        tap_drill_mm=11.11,
        tpi=18.0,
        nominal_size_inch='1/4"',
        engagement_length_mm=10.16,
        standard_ref="ASME B1.20.1",
    ),
    "3/8": ThreadSpec(
        family=ThreadFamily.NPT,
        size="3/8",
        pitch_mm=1.411,
        form=ThreadForm.NPT,
        major_diameter=17.145,
        pitch_diameter_ext=16.355,
        minor_diameter_ext=15.565,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,
        tap_drill_mm=14.29,
        tpi=18.0,
        nominal_size_inch='3/8"',
        engagement_length_mm=10.39,
        standard_ref="ASME B1.20.1",
    ),
    "1/2": ThreadSpec(
        family=ThreadFamily.NPT,
        size="1/2",
        pitch_mm=1.814,
        form=ThreadForm.NPT,
        major_diameter=21.336,
        pitch_diameter_ext=20.320,
        minor_diameter_ext=19.304,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,
        tap_drill_mm=17.93,
        tpi=14.0,
        nominal_size_inch='1/2"',
        engagement_length_mm=13.56,
        standard_ref="ASME B1.20.1",
    ),
    "3/4": ThreadSpec(
        family=ThreadFamily.NPT,
        size="3/4",
        pitch_mm=1.814,
        form=ThreadForm.NPT,
        major_diameter=26.670,
        pitch_diameter_ext=25.654,
        minor_diameter_ext=24.638,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,
        tap_drill_mm=23.01,
        tpi=14.0,
        nominal_size_inch='3/4"',
        engagement_length_mm=13.86,
        standard_ref="ASME B1.20.1",
    ),
    "1": ThreadSpec(
        family=ThreadFamily.NPT,
        size="1",
        pitch_mm=2.209,
        form=ThreadForm.NPT,
        major_diameter=33.401,
        pitch_diameter_ext=32.154,
        minor_diameter_ext=30.907,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,
        tap_drill_mm=28.85,
        tpi=11.5,
        nominal_size_inch='1"',
        engagement_length_mm=17.34,
        standard_ref="ASME B1.20.1",
    ),
    "1-1/4": ThreadSpec(
        family=ThreadFamily.NPT,
        size="1-1/4",
        pitch_mm=2.209,
        form=ThreadForm.NPT,
        major_diameter=42.164,
        pitch_diameter_ext=40.917,
        minor_diameter_ext=39.670,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,
        tap_drill_mm=37.47,
        tpi=11.5,
        nominal_size_inch='1-1/4"',
        engagement_length_mm=17.95,
        standard_ref="ASME B1.20.1",
    ),
    "1-1/2": ThreadSpec(
        family=ThreadFamily.NPT,
        size="1-1/2",
        pitch_mm=2.209,
        form=ThreadForm.NPT,
        major_diameter=48.260,
        pitch_diameter_ext=47.013,
        minor_diameter_ext=45.766,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,
        tap_drill_mm=43.56,
        tpi=11.5,
        nominal_size_inch='1-1/2"',
        engagement_length_mm=18.38,
        standard_ref="ASME B1.20.1",
    ),
    "2": ThreadSpec(
        family=ThreadFamily.NPT,
        size="2",
        pitch_mm=2.209,
        form=ThreadForm.NPT,
        major_diameter=60.325,
        pitch_diameter_ext=59.078,
        minor_diameter_ext=57.831,
        profile_angle_deg=60.0,
        taper_per_mm=0.0625,
        tap_drill_mm=55.63,
        tpi=11.5,
        nominal_size_inch='2"',
        engagement_length_mm=19.22,
        standard_ref="ASME B1.20.1",
    ),
}


# =============================================================================
# BSPP Threads - ISO 228-1 (Parallel, 55° Whitworth)
# =============================================================================

BSPP_THREADS: dict[str, ThreadSpec] = {
    "G1/8": ThreadSpec(
        family=ThreadFamily.BSPP,
        size="G1/8",
        pitch_mm=0.907,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=9.728,
        pitch_diameter_ext=9.147,
        minor_diameter_ext=8.566,
        profile_angle_deg=55.0,
        tap_drill_mm=8.57,
        clearance_hole_close_mm=9.9,
        clearance_hole_medium_mm=10.0,
        clearance_hole_free_mm=10.2,
        tpi=28.0,
        nominal_size_inch='1/8"',
        standard_ref="ISO 228-1",
    ),
    "G1/4": ThreadSpec(
        family=ThreadFamily.BSPP,
        size="G1/4",
        pitch_mm=1.337,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=13.157,
        pitch_diameter_ext=12.301,
        minor_diameter_ext=11.445,
        profile_angle_deg=55.0,
        tap_drill_mm=11.45,
        clearance_hole_close_mm=13.3,
        clearance_hole_medium_mm=13.5,
        clearance_hole_free_mm=13.8,
        tpi=19.0,
        nominal_size_inch='1/4"',
        standard_ref="ISO 228-1",
    ),
    "G3/8": ThreadSpec(
        family=ThreadFamily.BSPP,
        size="G3/8",
        pitch_mm=1.337,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=16.662,
        pitch_diameter_ext=15.806,
        minor_diameter_ext=14.950,
        profile_angle_deg=55.0,
        tap_drill_mm=14.95,
        clearance_hole_close_mm=16.8,
        clearance_hole_medium_mm=17.0,
        clearance_hole_free_mm=17.3,
        tpi=19.0,
        nominal_size_inch='3/8"',
        standard_ref="ISO 228-1",
    ),
    "G1/2": ThreadSpec(
        family=ThreadFamily.BSPP,
        size="G1/2",
        pitch_mm=1.814,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=20.955,
        pitch_diameter_ext=19.793,
        minor_diameter_ext=18.631,
        profile_angle_deg=55.0,
        tap_drill_mm=18.63,
        clearance_hole_close_mm=21.1,
        clearance_hole_medium_mm=21.3,
        clearance_hole_free_mm=21.7,
        tpi=14.0,
        nominal_size_inch='1/2"',
        standard_ref="ISO 228-1",
    ),
    "G3/4": ThreadSpec(
        family=ThreadFamily.BSPP,
        size="G3/4",
        pitch_mm=1.814,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=26.441,
        pitch_diameter_ext=25.279,
        minor_diameter_ext=24.117,
        profile_angle_deg=55.0,
        tap_drill_mm=24.12,
        clearance_hole_close_mm=26.6,
        clearance_hole_medium_mm=26.8,
        clearance_hole_free_mm=27.2,
        tpi=14.0,
        nominal_size_inch='3/4"',
        standard_ref="ISO 228-1",
    ),
    "G1": ThreadSpec(
        family=ThreadFamily.BSPP,
        size="G1",
        pitch_mm=2.309,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=33.249,
        pitch_diameter_ext=31.770,
        minor_diameter_ext=30.291,
        profile_angle_deg=55.0,
        tap_drill_mm=30.29,
        clearance_hole_close_mm=33.5,
        clearance_hole_medium_mm=33.8,
        clearance_hole_free_mm=34.2,
        tpi=11.0,
        nominal_size_inch='1"',
        standard_ref="ISO 228-1",
    ),
}


# =============================================================================
# BSPT Threads - ISO 7-1 (Tapered, 55° Whitworth, 1:16 taper)
# =============================================================================

BSPT_THREADS: dict[str, ThreadSpec] = {
    "R1/8": ThreadSpec(
        family=ThreadFamily.BSPT,
        size="R1/8",
        pitch_mm=0.907,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=9.728,
        pitch_diameter_ext=9.147,
        minor_diameter_ext=8.566,
        profile_angle_deg=55.0,
        taper_per_mm=0.0625,
        tap_drill_mm=8.57,
        tpi=28.0,
        nominal_size_inch='1/8"',
        engagement_length_mm=6.5,
        standard_ref="ISO 7-1",
    ),
    "R1/4": ThreadSpec(
        family=ThreadFamily.BSPT,
        size="R1/4",
        pitch_mm=1.337,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=13.157,
        pitch_diameter_ext=12.301,
        minor_diameter_ext=11.445,
        profile_angle_deg=55.0,
        taper_per_mm=0.0625,
        tap_drill_mm=11.45,
        tpi=19.0,
        nominal_size_inch='1/4"',
        engagement_length_mm=9.7,
        standard_ref="ISO 7-1",
    ),
    "R3/8": ThreadSpec(
        family=ThreadFamily.BSPT,
        size="R3/8",
        pitch_mm=1.337,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=16.662,
        pitch_diameter_ext=15.806,
        minor_diameter_ext=14.950,
        profile_angle_deg=55.0,
        taper_per_mm=0.0625,
        tap_drill_mm=14.95,
        tpi=19.0,
        nominal_size_inch='3/8"',
        engagement_length_mm=10.1,
        standard_ref="ISO 7-1",
    ),
    "R1/2": ThreadSpec(
        family=ThreadFamily.BSPT,
        size="R1/2",
        pitch_mm=1.814,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=20.955,
        pitch_diameter_ext=19.793,
        minor_diameter_ext=18.631,
        profile_angle_deg=55.0,
        taper_per_mm=0.0625,
        tap_drill_mm=18.63,
        tpi=14.0,
        nominal_size_inch='1/2"',
        engagement_length_mm=13.2,
        standard_ref="ISO 7-1",
    ),
    "R3/4": ThreadSpec(
        family=ThreadFamily.BSPT,
        size="R3/4",
        pitch_mm=1.814,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=26.441,
        pitch_diameter_ext=25.279,
        minor_diameter_ext=24.117,
        profile_angle_deg=55.0,
        taper_per_mm=0.0625,
        tap_drill_mm=24.12,
        tpi=14.0,
        nominal_size_inch='3/4"',
        engagement_length_mm=14.5,
        standard_ref="ISO 7-1",
    ),
    "R1": ThreadSpec(
        family=ThreadFamily.BSPT,
        size="R1",
        pitch_mm=2.309,
        form=ThreadForm.TRUNCATED_TRIANGULAR,
        major_diameter=33.249,
        pitch_diameter_ext=31.770,
        minor_diameter_ext=30.291,
        profile_angle_deg=55.0,
        taper_per_mm=0.0625,
        tap_drill_mm=30.29,
        tpi=11.0,
        nominal_size_inch='1"',
        engagement_length_mm=16.8,
        standard_ref="ISO 7-1",
    ),
}


# =============================================================================
# ACME Threads (ASME B1.5) — 29° included angle
# =============================================================================

ACME_THREADS: dict[str, ThreadSpec] = {
    "1/4-16": ThreadSpec(
        family=ThreadFamily.ACME,
        size="1/4-16",
        pitch_mm=1.588,
        form=ThreadForm.ACME,
        major_diameter=6.350,
        pitch_diameter_ext=5.556,
        minor_diameter_ext=4.762,
        profile_angle_deg=29.0,
        tpi=16.0,
        nominal_size_inch='1/4"',
        standard_ref="ASME B1.5",
    ),
    "3/8-12": ThreadSpec(
        family=ThreadFamily.ACME,
        size="3/8-12",
        pitch_mm=2.117,
        form=ThreadForm.ACME,
        major_diameter=9.525,
        pitch_diameter_ext=8.467,
        minor_diameter_ext=7.408,
        profile_angle_deg=29.0,
        tpi=12.0,
        nominal_size_inch='3/8"',
        standard_ref="ASME B1.5",
    ),
    "1/2-10": ThreadSpec(
        family=ThreadFamily.ACME,
        size="1/2-10",
        pitch_mm=2.540,
        form=ThreadForm.ACME,
        major_diameter=12.700,
        pitch_diameter_ext=11.430,
        minor_diameter_ext=10.160,
        profile_angle_deg=29.0,
        tpi=10.0,
        nominal_size_inch='1/2"',
        standard_ref="ASME B1.5",
    ),
    "5/8-8": ThreadSpec(
        family=ThreadFamily.ACME,
        size="5/8-8",
        pitch_mm=3.175,
        form=ThreadForm.ACME,
        major_diameter=15.875,
        pitch_diameter_ext=14.288,
        minor_diameter_ext=12.700,
        profile_angle_deg=29.0,
        tpi=8.0,
        nominal_size_inch='5/8"',
        standard_ref="ASME B1.5",
    ),
    "3/4-6": ThreadSpec(
        family=ThreadFamily.ACME,
        size="3/4-6",
        pitch_mm=4.233,
        form=ThreadForm.ACME,
        major_diameter=19.050,
        pitch_diameter_ext=16.934,
        minor_diameter_ext=14.817,
        profile_angle_deg=29.0,
        tpi=6.0,
        nominal_size_inch='3/4"',
        standard_ref="ASME B1.5",
    ),
    "1-5": ThreadSpec(
        family=ThreadFamily.ACME,
        size="1-5",
        pitch_mm=5.080,
        form=ThreadForm.ACME,
        major_diameter=25.400,
        pitch_diameter_ext=22.860,
        minor_diameter_ext=20.320,
        profile_angle_deg=29.0,
        tpi=5.0,
        nominal_size_inch='1"',
        standard_ref="ASME B1.5",
    ),
}


# =============================================================================
# Trapezoidal Threads (ISO 2904) — 30° included angle
# =============================================================================

TRAPEZOIDAL_THREADS: dict[str, ThreadSpec] = {
    "Tr8x1.5": ThreadSpec(
        family=ThreadFamily.TRAPEZOIDAL,
        size="Tr8x1.5",
        pitch_mm=1.5,
        form=ThreadForm.TRAPEZOIDAL,
        major_diameter=8.0,
        pitch_diameter_ext=7.250,
        minor_diameter_ext=6.200,
        profile_angle_deg=30.0,
        standard_ref="ISO 2904",
    ),
    "Tr10x2": ThreadSpec(
        family=ThreadFamily.TRAPEZOIDAL,
        size="Tr10x2",
        pitch_mm=2.0,
        form=ThreadForm.TRAPEZOIDAL,
        major_diameter=10.0,
        pitch_diameter_ext=9.000,
        minor_diameter_ext=7.500,
        profile_angle_deg=30.0,
        standard_ref="ISO 2904",
    ),
    "Tr12x3": ThreadSpec(
        family=ThreadFamily.TRAPEZOIDAL,
        size="Tr12x3",
        pitch_mm=3.0,
        form=ThreadForm.TRAPEZOIDAL,
        major_diameter=12.0,
        pitch_diameter_ext=10.500,
        minor_diameter_ext=8.500,
        profile_angle_deg=30.0,
        standard_ref="ISO 2904",
    ),
    "Tr16x4": ThreadSpec(
        family=ThreadFamily.TRAPEZOIDAL,
        size="Tr16x4",
        pitch_mm=4.0,
        form=ThreadForm.TRAPEZOIDAL,
        major_diameter=16.0,
        pitch_diameter_ext=14.000,
        minor_diameter_ext=11.500,
        profile_angle_deg=30.0,
        standard_ref="ISO 2904",
    ),
    "Tr20x4": ThreadSpec(
        family=ThreadFamily.TRAPEZOIDAL,
        size="Tr20x4",
        pitch_mm=4.0,
        form=ThreadForm.TRAPEZOIDAL,
        major_diameter=20.0,
        pitch_diameter_ext=18.000,
        minor_diameter_ext=15.500,
        profile_angle_deg=30.0,
        standard_ref="ISO 2904",
    ),
    "Tr24x5": ThreadSpec(
        family=ThreadFamily.TRAPEZOIDAL,
        size="Tr24x5",
        pitch_mm=5.0,
        form=ThreadForm.TRAPEZOIDAL,
        major_diameter=24.0,
        pitch_diameter_ext=21.500,
        minor_diameter_ext=18.500,
        profile_angle_deg=30.0,
        standard_ref="ISO 2904",
    ),
}


# =============================================================================
# Unified Thread Registry
# =============================================================================

THREAD_REGISTRY: dict[ThreadFamily, dict[str, ThreadSpec]] = {
    ThreadFamily.ISO_METRIC: {**ISO_METRIC_COARSE, **ISO_METRIC_FINE},
    ThreadFamily.UNC: UNC_THREADS,
    ThreadFamily.UNF: UNF_THREADS,
    ThreadFamily.NPT: NPT_THREADS,
    ThreadFamily.BSPP: BSPP_THREADS,
    ThreadFamily.BSPT: BSPT_THREADS,
    ThreadFamily.ACME: ACME_THREADS,
    ThreadFamily.TRAPEZOIDAL: TRAPEZOIDAL_THREADS,
}


# =============================================================================
# Thread Family Info
# =============================================================================

THREAD_FAMILY_INFO: dict[ThreadFamily, dict[str, str]] = {
    ThreadFamily.ISO_METRIC: {
        "name": "ISO Metric",
        "description": (
            "International standard metric threads with 60° profile. "
            "Available in coarse and fine pitch series."
        ),
        "standard_ref": "ISO 261 / ISO 262",
    },
    ThreadFamily.UNC: {
        "name": "Unified National Coarse",
        "description": (
            "US standard coarse-pitch threads with 60° profile. "
            "Most common general-purpose inch thread."
        ),
        "standard_ref": "ASME B1.1",
    },
    ThreadFamily.UNF: {
        "name": "Unified National Fine",
        "description": (
            "US standard fine-pitch threads with 60° profile. "
            "Higher tensile strength and vibration resistance than UNC."
        ),
        "standard_ref": "ASME B1.1",
    },
    ThreadFamily.NPT: {
        "name": "National Pipe Taper",
        "description": (
            "US standard tapered pipe threads with 60° profile and "
            "1:16 taper. Used for sealed pipe connections."
        ),
        "standard_ref": "ASME B1.20.1",
    },
    ThreadFamily.BSPP: {
        "name": "British Standard Pipe Parallel",
        "description": (
            "Parallel (non-tapered) pipe threads with 55° Whitworth "
            "profile. Sealed with gasket or O-ring."
        ),
        "standard_ref": "ISO 228-1",
    },
    ThreadFamily.BSPT: {
        "name": "British Standard Pipe Taper",
        "description": (
            "Tapered pipe threads with 55° Whitworth profile and "
            "1:16 taper. Self-sealing when assembled."
        ),
        "standard_ref": "ISO 7-1",
    },
    ThreadFamily.ACME: {
        "name": "ACME",
        "description": (
            "Power transmission threads with 29° trapezoidal profile. "
            "Used for lead screws and linear actuators."
        ),
        "standard_ref": "ASME B1.5",
    },
    ThreadFamily.TRAPEZOIDAL: {
        "name": "Trapezoidal (Metric)",
        "description": (
            "Metric power transmission threads with 30° trapezoidal "
            "profile. ISO equivalent of ACME threads."
        ),
        "standard_ref": "ISO 2904",
    },
}


# =============================================================================
# Lookup Functions
# =============================================================================


def get_thread_spec(
    family: ThreadFamily,
    size: str,
    pitch_series: PitchSeries | None = None,
) -> ThreadSpec:
    """Look up a thread specification by family, size, and optional pitch series.

    Args:
        family: Thread standard family to search.
        size: Thread size label (e.g. "M8", "1/4-20").
        pitch_series: Optional pitch series filter for families with
            multiple pitch options (e.g. ISO Metric coarse vs fine).

    Returns:
        The matching ThreadSpec.

    Raises:
        ThreadDataError: If family or size is not found, or if pitch_series
            filter yields no match.
    """
    if family not in THREAD_REGISTRY:
        raise ThreadDataError(
            f"Unknown thread family: {family}",
            details={"family": str(family)},
        )

    family_specs = THREAD_REGISTRY[family]

    if size not in family_specs:
        available = sorted(family_specs.keys())
        raise ThreadDataError(
            f"Unknown size '{size}' for family '{family}'. Available: {', '.join(available)}",
            details={"family": str(family), "size": size},
        )

    spec = family_specs[size]

    if pitch_series is not None and spec.pitch_series != pitch_series:
        raise ThreadDataError(
            f"Size '{size}' in family '{family}' does not match pitch series '{pitch_series}'.",
            details={
                "family": str(family),
                "size": size,
                "requested_series": str(pitch_series),
                "actual_series": str(spec.pitch_series),
            },
        )

    return spec


def list_thread_sizes(
    family: ThreadFamily,
    pitch_series: PitchSeries | None = None,
) -> list[str]:
    """List available thread sizes for a family, optionally filtered by pitch series.

    Args:
        family: Thread standard family.
        pitch_series: If provided, only return sizes matching this series.

    Returns:
        Sorted list of size labels.

    Raises:
        ThreadDataError: If family is not found.
    """
    if family not in THREAD_REGISTRY:
        raise ThreadDataError(
            f"Unknown thread family: {family}",
            details={"family": str(family)},
        )

    specs = THREAD_REGISTRY[family]

    if pitch_series is not None:
        sizes = [size for size, spec in specs.items() if spec.pitch_series == pitch_series]
    else:
        sizes = list(specs.keys())

    return sorted(sizes)


def list_thread_families() -> list[ThreadFamily]:
    """Return all available thread families.

    Returns:
        List of ThreadFamily enum members present in the registry.
    """
    return list(THREAD_REGISTRY.keys())


def get_tap_drill_info(
    family: ThreadFamily,
    size: str,
) -> dict[str, float]:
    """Get drilling information for a thread size.

    Args:
        family: Thread standard family.
        size: Thread size label.

    Returns:
        Dictionary with tap_drill_mm, clearance_hole_close_mm,
        clearance_hole_medium_mm, and clearance_hole_free_mm.

    Raises:
        ThreadDataError: If family or size is not found.
    """
    spec = get_thread_spec(family, size)
    return {
        "tap_drill_mm": spec.tap_drill_mm,
        "clearance_hole_close_mm": spec.clearance_hole_close_mm,
        "clearance_hole_medium_mm": spec.clearance_hole_medium_mm,
        "clearance_hole_free_mm": spec.clearance_hole_free_mm,
    }
