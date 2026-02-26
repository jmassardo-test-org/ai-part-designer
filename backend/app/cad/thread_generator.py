"""
Thread geometry generator for CAD assemblies.

Generates simplified thread representations using Build123d primitives.
External threads produce a Part with correct diameters and helical groove
cuts that can be added via ``union()``.  Internal threads produce a Part
representing the threaded-hole shape to be subtracted via ``difference()``.

All dimensions are in millimeters.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

from build123d import (
    Cylinder,
    Location,
    Part,
)

from app.cad.exceptions import ThreadGenerationError, ValidationError
from app.cad.threads import (
    ThreadHand,
    ThreadSpec,
    ThreadType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

MAX_THREAD_LENGTH_MM: float = 200.0
"""Maximum allowable thread length in millimetres."""

MAX_REVOLUTIONS: int = 500
"""Maximum number of helix revolutions to prevent runaway geometry."""

GENERATION_TIMEOUT_SECONDS: float = 60.0
"""Hard timeout for a single thread generation call."""

DEFAULT_SEGMENTS_PER_REVOLUTION: int = 64
"""Number of linear segments used to approximate one full helix turn."""


# =============================================================================
# Configuration & Result Dataclasses
# =============================================================================


@dataclass(frozen=True)
class ThreadGeneratorConfig:
    """Immutable configuration for thread geometry generation.

    Attributes:
        spec: Thread specification from the thread data library.
        thread_type: Whether to generate an internal or external thread.
        length_mm: Axial length of the threaded section.
        hand: Helix direction (right-hand or left-hand).
        segments_per_revolution: Linear segments per helix turn for
            approximation fidelity.
        add_chamfer: Whether to add a lead-in chamfer at the thread
            entry.
        custom_pitch_mm: Optional override for the spec's pitch.
        custom_diameter_mm: Optional override for the spec's major
            diameter.
    """

    spec: ThreadSpec
    thread_type: ThreadType
    length_mm: float
    hand: ThreadHand = ThreadHand.RIGHT
    segments_per_revolution: int = DEFAULT_SEGMENTS_PER_REVOLUTION
    add_chamfer: bool = True
    custom_pitch_mm: float | None = None
    custom_diameter_mm: float | None = None


@dataclass
class ThreadGenerationResult:
    """Mutable result container returned by ``generate_thread``.

    Attributes:
        part: Generated Build123d Part.
        metadata: Descriptive metadata dictionary.
        generation_time_ms: Wall-clock generation time in milliseconds.
        estimated_face_count: Rough face-count estimate for the mesh.
    """

    part: Part
    metadata: dict[str, Any] = field(default_factory=dict)
    generation_time_ms: int = 0
    estimated_face_count: int = 0


# =============================================================================
# Public API
# =============================================================================


def generate_thread(config: ThreadGeneratorConfig) -> ThreadGenerationResult:
    """Generate thread geometry from a validated configuration.

    Produces a simplified thread representation with correct major and
    minor diameters.  External threads are solid cylinders with helical
    groove cuts; internal threads are hollow cylinders representing the
    material to be subtracted from a parent body.

    Args:
        config: Immutable thread generation configuration.

    Returns:
        ThreadGenerationResult containing the Part, metadata, timing,
        and estimated face count.

    Raises:
        ValidationError: If configuration values are out of range.
        ThreadGenerationError: If geometry generation fails.
    """
    _validate_config(config)

    start_ns = time.perf_counter_ns()

    pitch, major_dia, minor_dia = _get_effective_dimensions(config)
    revolutions = config.length_mm / pitch
    profile_angle = config.spec.profile_angle_deg
    taper = config.spec.taper_per_mm

    try:
        if config.thread_type == ThreadType.EXTERNAL:
            part = _build_external_thread(
                pitch=pitch,
                major_dia=major_dia,
                minor_dia=minor_dia,
                length=config.length_mm,
                profile_angle=profile_angle,
                taper_per_mm=taper,
                hand=config.hand,
                segments=config.segments_per_revolution,
            )
        else:
            part = _build_internal_thread(
                pitch=pitch,
                major_dia=major_dia,
                minor_dia=minor_dia,
                length=config.length_mm,
                profile_angle=profile_angle,
                taper_per_mm=taper,
                hand=config.hand,
                segments=config.segments_per_revolution,
            )

        if config.add_chamfer:
            part = _add_chamfer_lead_in(part, major_dia, pitch)

    except (ValidationError, ThreadGenerationError):
        raise
    except Exception as exc:
        raise ThreadGenerationError(
            f"Thread geometry generation failed: {exc}",
            details={"spec_size": config.spec.size},
        ) from exc

    elapsed_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

    metadata = _build_metadata(
        config=config,
        effective_pitch=pitch,
        effective_diameter=major_dia,
        revolutions=revolutions,
        generation_time_ms=elapsed_ms,
    )

    estimated_faces = _estimate_face_count(
        revolutions=revolutions,
        segments=config.segments_per_revolution,
        thread_type=config.thread_type,
    )

    logger.info(
        "Generated %s %s thread (%s) in %d ms",
        config.hand.value,
        config.thread_type.value,
        config.spec.size,
        elapsed_ms,
    )

    return ThreadGenerationResult(
        part=part,
        metadata=metadata,
        generation_time_ms=elapsed_ms,
        estimated_face_count=estimated_faces,
    )


# =============================================================================
# Validation Helpers
# =============================================================================


def _validate_config(config: ThreadGeneratorConfig) -> None:
    """Validate thread generation parameters.

    Checks length, pitch, diameter, segments, and computed revolution
    count against safety limits.

    Args:
        config: Thread configuration to validate.

    Raises:
        ValidationError: If any parameter is out of range.
    """
    # Length checks
    if config.length_mm <= 0:
        raise ValidationError(
            "Thread length must be positive.",
            details={"length_mm": config.length_mm},
        )
    if config.length_mm > MAX_THREAD_LENGTH_MM:
        raise ValidationError(
            f"Thread length {config.length_mm} mm exceeds maximum {MAX_THREAD_LENGTH_MM} mm.",
            details={
                "length_mm": config.length_mm,
                "max_length_mm": MAX_THREAD_LENGTH_MM,
            },
        )

    # Custom overrides must be positive when supplied
    if config.custom_pitch_mm is not None and config.custom_pitch_mm <= 0:
        raise ValidationError(
            "Custom pitch must be positive.",
            details={"custom_pitch_mm": config.custom_pitch_mm},
        )
    if config.custom_diameter_mm is not None and config.custom_diameter_mm <= 0:
        raise ValidationError(
            "Custom diameter must be positive.",
            details={"custom_diameter_mm": config.custom_diameter_mm},
        )

    # Effective pitch
    effective_pitch = config.custom_pitch_mm or config.spec.pitch_mm
    if effective_pitch <= 0:
        raise ValidationError(
            "Thread pitch must be positive.",
            details={"pitch_mm": effective_pitch},
        )

    # Effective diameter
    effective_dia = config.custom_diameter_mm or config.spec.major_diameter
    if effective_dia <= 0:
        raise ValidationError(
            "Thread diameter must be positive.",
            details={"diameter_mm": effective_dia},
        )

    # Revolution cap
    revolutions = config.length_mm / effective_pitch
    if revolutions > MAX_REVOLUTIONS:
        raise ValidationError(
            f"Computed revolutions ({revolutions:.0f}) exceed maximum ({MAX_REVOLUTIONS}).",
            details={
                "revolutions": revolutions,
                "max_revolutions": MAX_REVOLUTIONS,
            },
        )

    # Segments sanity
    if config.segments_per_revolution < 4:
        raise ValidationError(
            "segments_per_revolution must be at least 4.",
            details={"segments_per_revolution": config.segments_per_revolution},
        )


# =============================================================================
# Dimension Helpers
# =============================================================================


def _get_effective_dimensions(
    config: ThreadGeneratorConfig,
) -> tuple[float, float, float]:
    """Resolve effective pitch, major diameter, and minor diameter.

    Custom overrides take precedence.  When only the major diameter is
    overridden, the minor diameter is scaled proportionally.

    Args:
        config: Thread configuration.

    Returns:
        Tuple of ``(pitch_mm, major_diameter_mm, minor_diameter_mm)``.
    """
    pitch = config.custom_pitch_mm if config.custom_pitch_mm else config.spec.pitch_mm

    if config.custom_diameter_mm is not None:
        major_dia = config.custom_diameter_mm
        # Scale minor diameter proportionally
        if config.spec.major_diameter > 0:
            ratio = config.spec.minor_diameter_ext / config.spec.major_diameter
            minor_dia = major_dia * ratio
        else:
            # Fallback: approximate from pitch using 60° thread formula
            minor_dia = major_dia - 1.0825 * pitch
    else:
        if config.thread_type == ThreadType.EXTERNAL:
            major_dia = config.spec.major_diameter
            minor_dia = config.spec.minor_diameter_ext
        else:
            major_dia = config.spec.major_diameter_int
            minor_dia = config.spec.minor_diameter_int

    return pitch, major_dia, minor_dia


# =============================================================================
# Geometry Builders
# =============================================================================


def _build_external_thread(
    pitch: float,
    major_dia: float,
    minor_dia: float,
    length: float,
    profile_angle: float,  # noqa: ARG001
    taper_per_mm: float,
    hand: ThreadHand,
    segments: int,  # noqa: ARG001
) -> Part:
    """Build an external (bolt-style) thread Part.

    Creates a cylinder at the major diameter, then cuts helical grooves
    down to the minor diameter to approximate the thread form.  For
    tapered threads the cylinder diameters are averaged.

    Args:
        pitch: Thread pitch in mm.
        major_dia: Major (outer) diameter in mm.
        minor_dia: Minor (root) diameter in mm.
        length: Axial thread length in mm.
        profile_angle: Included thread angle in degrees.
        taper_per_mm: Taper per mm of axial length (0 for parallel).
        hand: Helix direction.
        segments: Segments per revolution.

    Returns:
        Build123d Part representing the external thread.

    Raises:
        ThreadGenerationError: If geometry construction fails.
    """
    try:
        # Average diameters for tapered threads
        avg_major = major_dia + (taper_per_mm * length / 2) if taper_per_mm else major_dia
        avg_minor = minor_dia + (taper_per_mm * length / 2) if taper_per_mm else minor_dia

        # Main body cylinder at major diameter
        body: Part = Cylinder(
            radius=avg_major / 2,
            height=length,
            align=None,
        )

        # Cut helical grooves using a series of thin ring cuts along the
        # thread axis.  Each pair of cuts removes material between crests.
        groove_depth = (avg_major - avg_minor) / 2
        groove_width = pitch * 0.5  # 50 % of pitch is groove
        revolutions = length / pitch
        num_grooves = math.ceil(revolutions)

        for i in range(num_grooves):
            z_offset = i * pitch + pitch * 0.25
            if z_offset + groove_width > length:
                break

            # Direction multiplier for hand
            _hand_mult = 1.0 if hand == ThreadHand.RIGHT else -1.0

            groove_ring: Part = Cylinder(
                radius=avg_major / 2 + 0.01,  # slightly oversize to ensure cut
                height=groove_width,
                align=None,
            )
            inner_keep: Part = Cylinder(
                radius=avg_major / 2 - groove_depth,
                height=groove_width + 0.02,
                align=None,
            )
            groove_cutter = groove_ring.cut(inner_keep)  # type: ignore[assignment]
            groove_cutter = groove_cutter.moved(  # type: ignore[assignment]
                Location((0, 0, z_offset)),
            )
            body = body.cut(groove_cutter)  # type: ignore[assignment]

        return body

    except Exception as exc:
        if isinstance(exc, (ThreadGenerationError, ValidationError)):
            raise
        raise ThreadGenerationError(
            f"External thread build failed: {exc}",
            details={"major_dia": major_dia, "length": length},
        ) from exc


def _build_internal_thread(
    pitch: float,
    major_dia: float,
    minor_dia: float,
    length: float,
    profile_angle: float,  # noqa: ARG001
    taper_per_mm: float,
    hand: ThreadHand,  # noqa: ARG001
    segments: int,  # noqa: ARG001
) -> Part:
    """Build an internal (nut-style) thread Part.

    Returns a Part representing the threaded bore volume, suitable for
    subtraction from a parent body using ``difference()``.  Constructs
    a cylinder at the major diameter with helical ridges built up from
    the minor diameter.

    Args:
        pitch: Thread pitch in mm.
        major_dia: Major (outer) diameter in mm.
        minor_dia: Minor (inner) diameter in mm.
        length: Axial thread length in mm.
        profile_angle: Included thread angle in degrees.
        taper_per_mm: Taper per mm of axial length (0 for parallel).
        hand: Helix direction.
        segments: Segments per revolution.

    Returns:
        Build123d Part representing the internal thread volume.

    Raises:
        ThreadGenerationError: If geometry construction fails.
    """
    try:
        avg_major = major_dia + (taper_per_mm * length / 2) if taper_per_mm else major_dia
        avg_minor = minor_dia + (taper_per_mm * length / 2) if taper_per_mm else minor_dia

        # Start with a bore at the minor diameter (the core hole)
        bore: Part = Cylinder(
            radius=avg_minor / 2,
            height=length,
            align=None,
        )

        # Add helical relief rings at major diameter for thread crests
        groove_width = pitch * 0.5
        revolutions = length / pitch
        num_grooves = math.ceil(revolutions)

        for i in range(num_grooves):
            z_offset = i * pitch + pitch * 0.25
            if z_offset + groove_width > length:
                break

            crest_ring: Part = Cylinder(
                radius=avg_major / 2,
                height=groove_width,
                align=None,
            )
            inner_cut: Part = Cylinder(
                radius=avg_minor / 2 - 0.01,
                height=groove_width + 0.02,
                align=None,
            )
            crest_ring = crest_ring.cut(inner_cut)  # type: ignore[assignment]
            crest_ring = crest_ring.moved(  # type: ignore[assignment]
                Location((0, 0, z_offset)),
            )
            bore = bore.fuse(crest_ring)  # type: ignore[assignment]

        return bore

    except Exception as exc:
        if isinstance(exc, (ThreadGenerationError, ValidationError)):
            raise
        raise ThreadGenerationError(
            f"Internal thread build failed: {exc}",
            details={"major_dia": major_dia, "length": length},
        ) from exc


# =============================================================================
# Post-Processing Helpers
# =============================================================================


def _add_chamfer_lead_in(part: Part, diameter: float, pitch: float) -> Part:
    """Add a chamfer at the thread entry for easier engagement.

    Creates a conical chamfer by subtracting a tapered ring from the
    thread start.  Chamfer height is one pitch.

    Args:
        part: Thread Part to modify.
        diameter: Major diameter of the thread.
        pitch: Thread pitch (used as chamfer height).

    Returns:
        Modified Part with lead-in chamfer applied.
    """
    try:
        chamfer_height = pitch
        outer_radius = diameter / 2 + 0.01

        # Chamfer cylinder slightly larger than thread
        chamfer_body: Part = Cylinder(
            radius=outer_radius,
            height=chamfer_height,
            align=None,
        )
        # Smaller cylinder to keep the core
        chamfer_keep: Part = Cylinder(
            radius=diameter / 2 - chamfer_height * 0.5,
            height=chamfer_height + 0.02,
            align=None,
        )
        chamfer_tool = chamfer_body.cut(chamfer_keep)  # type: ignore[assignment]
        part = part.cut(chamfer_tool)  # type: ignore[assignment]
    except Exception:
        # Chamfer is cosmetic; log and return original part on failure
        logger.warning("Failed to apply chamfer lead-in; returning unchamfered part.")

    return part


# =============================================================================
# Metadata & Utilities
# =============================================================================


def _build_metadata(
    config: ThreadGeneratorConfig,
    effective_pitch: float,
    effective_diameter: float,
    revolutions: float,
    generation_time_ms: int,
) -> dict[str, Any]:
    """Assemble metadata dictionary for a generated thread.

    Args:
        config: Original generation configuration.
        effective_pitch: Resolved pitch in mm.
        effective_diameter: Resolved major diameter in mm.
        revolutions: Number of helix revolutions.
        generation_time_ms: Elapsed time in milliseconds.

    Returns:
        Metadata dictionary with thread parameters, spec info, and
        generation statistics.
    """
    return {
        "family": config.spec.family.value,
        "size": config.spec.size,
        "thread_type": config.thread_type.value,
        "hand": config.hand.value,
        "pitch_mm": effective_pitch,
        "major_diameter_mm": effective_diameter,
        "revolutions": round(revolutions, 2),
        "length_mm": config.length_mm,
        "form": config.spec.form.value,
        "profile_angle_deg": config.spec.profile_angle_deg,
        "taper_per_mm": config.spec.taper_per_mm,
        "standard_ref": config.spec.standard_ref,
        "segments_per_revolution": config.segments_per_revolution,
        "chamfered": config.add_chamfer,
        "generation_time_ms": generation_time_ms,
        "custom_pitch_applied": config.custom_pitch_mm is not None,
        "custom_diameter_applied": config.custom_diameter_mm is not None,
    }


def _estimate_face_count(
    revolutions: float,
    segments: int,
    thread_type: ThreadType,
) -> int:
    """Estimate the number of mesh faces for the generated thread.

    Args:
        revolutions: Number of helix revolutions.
        segments: Segments per revolution.
        thread_type: Internal or external.

    Returns:
        Estimated face count.
    """
    # Each revolution produces segments quads on the cylinder body,
    # plus groove cut faces.  Internal threads have slightly more
    # faces due to the bore.
    base_faces = int(revolutions * segments * 2)
    groove_faces = int(revolutions * 4)  # top/bottom caps per groove
    multiplier = 1.3 if thread_type == ThreadType.INTERNAL else 1.0
    return int((base_faces + groove_faces) * multiplier)
