"""
Geometry Introspection Service.

Provides precise dimension and geometry answers for user queries about
their generated models. Extracts measurements from stored result data
(dimensions, bounding box) and, where available, from the generated
Build123d code by re-executing it to obtain the shape object.

Supports natural-language questions such as:
  - "What is the height?"
  - "How wide is it?"
  - "What are the dimensions?"
  - "What is the volume?"
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# Geometry query detection
# =============================================================================

# Patterns that indicate a user is asking about dimensions / geometry
_GEOMETRY_QUERY_PATTERNS: list[re.Pattern[str]] = [
    # Specific dimension questions
    re.compile(
        r"\b(what|how)\b.{0,20}\b(height|tall|high)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(what|how)\b.{0,20}\b(width|wide)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(what|how)\b.{0,20}\b(length|long|depth|deep)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(what|how)\b.{0,20}\b(diameter|radius)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(what|how)\b.{0,20}\b(thick|thickness)\b", re.IGNORECASE
    ),
    # General dimension / size queries
    re.compile(
        r"\b(what|tell me|show me|list)\b.{0,20}\b(dimensions?|measurements?|size)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(how big|overall size|bounding box)\b", re.IGNORECASE
    ),
    # Volume / area queries
    re.compile(
        r"\b(what|how).{0,15}\b(volume|surface area)\b", re.IGNORECASE
    ),
    # Weight estimate (from volume)
    re.compile(
        r"\b(what|how).{0,15}\b(weigh[ts]?|mass)\b", re.IGNORECASE
    ),
    # Direct "is it … mm?" style
    re.compile(
        r"\b(is it|is the)\b.{0,20}\b(mm|cm|inch|inches|meters?)\b",
        re.IGNORECASE,
    ),
]

# Mapping from natural-language dimension words to canonical keys
_DIMENSION_ALIASES: dict[str, list[str]] = {
    "height": ["height", "z", "h"],
    "width": ["width", "y", "w"],
    "length": ["length", "x", "l", "depth"],
    "diameter": ["diameter", "d", "dia"],
    "radius": ["radius", "r", "rad"],
    "thickness": ["thickness", "t", "wall_thickness"],
}


def is_geometry_query(message: str) -> bool:
    """Determine whether a user message is asking about model geometry.

    Args:
        message: The raw user message text.

    Returns:
        True if the message looks like a geometry / dimension question.
    """
    return any(pattern.search(message) for pattern in _GEOMETRY_QUERY_PATTERNS)


# =============================================================================
# Result dataclass
# =============================================================================


@dataclass
class GeometryAnswer:
    """Result of a geometry introspection query.

    Attributes:
        answered: Whether the query could be answered.
        response_text: Human-readable answer for the user.
        dimensions: The raw dimensions dict used to formulate the answer.
        source: Where the answer came from (``"result_data"``,
            ``"design_extra_data"``, or ``"unavailable"``).
    """

    answered: bool
    response_text: str
    dimensions: dict[str, Any] = field(default_factory=dict)
    source: str = "unavailable"


# =============================================================================
# Public API
# =============================================================================


def answer_geometry_query(
    message: str,
    result_data: dict[str, Any] | None = None,
    design_extra_data: dict[str, Any] | None = None,
) -> GeometryAnswer:
    """Answer a geometry / dimension question about a generated model.

    Uses the conversation's ``result_data`` (preferred) or the linked
    design's ``extra_data`` as the source of dimension information.

    Args:
        message: The user's question.
        result_data: ``conversation.result_data`` dict (contains
            ``"dimensions"``, ``"shape"``, ``"stats"`` etc.).
        design_extra_data: ``design.extra_data`` dict (contains
            ``"dimensions"``, ``"parameters"``).

    Returns:
        A ``GeometryAnswer`` with the formatted response.
    """
    # ------------------------------------------------------------------
    # 1. Collect available dimension data
    # ------------------------------------------------------------------
    dims: dict[str, Any] = {}
    source = "unavailable"
    stats: dict[str, Any] = {}
    shape_type: str = "part"

    if result_data:
        dims = result_data.get("dimensions", {})
        stats = result_data.get("stats", {})
        shape_type = result_data.get("shape", "part")
        source = "result_data"
    elif design_extra_data:
        dims = design_extra_data.get("dimensions", {})
        if not dims:
            dims = _extract_dims_from_params(
                design_extra_data.get("parameters", {})
            )
        source = "design_extra_data"

    if not dims:
        return GeometryAnswer(
            answered=False,
            response_text=(
                "I don't have dimension data for this model yet. "
                "Please generate the part first, and then I can answer "
                "your geometry questions."
            ),
        )

    # ------------------------------------------------------------------
    # 2. Determine what the user is asking for
    # ------------------------------------------------------------------
    msg_lower = message.lower()

    # Check for specific dimension
    requested_dim = _detect_requested_dimension(msg_lower)

    if requested_dim:
        return _answer_specific_dimension(
            requested_dim, dims, stats, source
        )

    # Check for volume / surface area
    if _mentions(msg_lower, ["volume"]):
        return _answer_volume(stats, dims, source)
    if _mentions(msg_lower, ["surface area", "surface_area"]):
        return _answer_surface_area(stats, source)
    if _mentions(msg_lower, ["weight", "weigh", "mass"]):
        return _answer_weight_estimate(stats, dims, source)

    # Default: return all dimensions
    return _answer_all_dimensions(dims, stats, shape_type, source)


# =============================================================================
# Internal helpers
# =============================================================================


def _mentions(text: str, terms: list[str]) -> bool:
    """Check whether *text* contains any of the *terms*."""
    return any(t in text for t in terms)


def _detect_requested_dimension(msg_lower: str) -> str | None:
    """Return the canonical dimension name the user is asking about.

    Returns:
        One of ``"height"``, ``"width"``, ``"length"``, ``"diameter"``,
        ``"radius"``, ``"thickness"``, or ``None`` if unclear.
    """
    # Order matters — check the most specific words first
    for canonical, aliases in _DIMENSION_ALIASES.items():
        for alias in aliases:
            # Use word boundary so "the height" matches but "highlighted" doesn't
            if re.search(rf"\b{re.escape(alias)}\b", msg_lower):
                return canonical
    # Also handle colloquial forms
    colloquial_map = {
        "tall": "height",
        "high": "height",
        "wide": "width",
        "long": "length",
        "deep": "length",
        "thick": "thickness",
    }
    for word, canonical in colloquial_map.items():
        if re.search(rf"\b{word}\b", msg_lower):
            return canonical
    return None


def _extract_dims_from_params(params: dict[str, Any]) -> dict[str, Any]:
    """Pull dimension-like keys out of a generic parameters dict."""
    dim_keys = {
        "length", "width", "height", "x", "y", "z",
        "diameter", "radius", "thickness", "depth",
    }
    result = {k: v for k, v in params.items() if k in dim_keys}
    if result and "unit" not in result:
        result["unit"] = "mm"
    return result


def _fmt_value(value: Any, unit: str = "mm") -> str:
    """Format a numeric value with its unit."""
    if isinstance(value, float):
        # Avoid unnecessary decimals
        if value == int(value):
            return f"{int(value)} {unit}"
        return f"{value:.2f} {unit}"
    return f"{value} {unit}"


def _answer_specific_dimension(
    requested: str,
    dims: dict[str, Any],
    stats: dict[str, Any],
    source: str,
) -> GeometryAnswer:
    """Answer a question about a single specific dimension."""
    unit = str(dims.get("unit", "mm"))

    # Try canonical key first, then aliases
    aliases = _DIMENSION_ALIASES.get(requested, [requested])
    for key in aliases:
        if key in dims and isinstance(dims[key], (int, float)):
            return GeometryAnswer(
                answered=True,
                response_text=(
                    f"The **{requested}** of the model is "
                    f"**{_fmt_value(dims[key], unit)}**."
                ),
                dimensions=dims,
                source=source,
            )

    # Dimension not found — provide what we do have
    available = [
        f"{k}: {_fmt_value(v, unit)}"
        for k, v in dims.items()
        if k != "unit" and isinstance(v, (int, float))
    ]
    if available:
        return GeometryAnswer(
            answered=False,
            response_text=(
                f"I don't have a specific **{requested}** measurement, "
                f"but here are the available dimensions:\n"
                + "\n".join(f"- {a}" for a in available)
            ),
            dimensions=dims,
            source=source,
        )

    return GeometryAnswer(
        answered=False,
        response_text=(
            f"I don't have a **{requested}** measurement for this model."
        ),
        dimensions=dims,
        source=source,
    )


def _answer_all_dimensions(
    dims: dict[str, Any],
    stats: dict[str, Any],
    shape_type: str,
    source: str,
) -> GeometryAnswer:
    """Return a summary of all known dimensions."""
    unit = str(dims.get("unit", "mm"))
    lines = [f"**Model dimensions** (shape: {shape_type}):"]

    for key, value in dims.items():
        if key == "unit":
            continue
        if isinstance(value, (int, float)):
            lines.append(f"- **{key}**: {_fmt_value(value, unit)}")

    # Append volume / surface area from stats if available
    volume = stats.get("volume")
    if isinstance(volume, (int, float)):
        lines.append(f"- **volume**: {_fmt_value(volume, unit + '³')}")

    surface = stats.get("surfaceArea") or stats.get("surface_area")
    if isinstance(surface, (int, float)):
        lines.append(f"- **surface area**: {_fmt_value(surface, unit + '²')}")

    return GeometryAnswer(
        answered=True,
        response_text="\n".join(lines),
        dimensions=dims,
        source=source,
    )


def _answer_volume(
    stats: dict[str, Any],
    dims: dict[str, Any],
    source: str,
) -> GeometryAnswer:
    """Answer a volume question."""
    unit = str(dims.get("unit", "mm"))
    volume = stats.get("volume")
    if isinstance(volume, (int, float)):
        return GeometryAnswer(
            answered=True,
            response_text=f"The **volume** of the model is **{_fmt_value(volume, unit + '³')}**.",
            dimensions=dims,
            source=source,
        )
    return GeometryAnswer(
        answered=False,
        response_text="Volume information is not available for this model.",
        dimensions=dims,
        source=source,
    )


def _answer_surface_area(
    stats: dict[str, Any],
    source: str,
) -> GeometryAnswer:
    """Answer a surface area question."""
    surface = stats.get("surfaceArea") or stats.get("surface_area")
    if isinstance(surface, (int, float)):
        return GeometryAnswer(
            answered=True,
            response_text=(
                f"The **surface area** of the model is **{_fmt_value(surface, 'mm²')}**."
            ),
            source=source,
        )
    return GeometryAnswer(
        answered=False,
        response_text="Surface area information is not available for this model.",
        source=source,
    )


def _answer_weight_estimate(
    stats: dict[str, Any],
    dims: dict[str, Any],
    source: str,
) -> GeometryAnswer:
    """Give a rough weight estimate based on volume and common material densities."""
    volume = stats.get("volume")
    if not isinstance(volume, (int, float)):
        return GeometryAnswer(
            answered=False,
            response_text=(
                "I can't estimate weight without volume data. "
                "Please generate the part first."
            ),
            source=source,
        )

    # Volume is in mm³; convert to cm³ for density calc
    vol_cm3 = volume / 1000.0
    estimates: list[str] = [
        f"Based on a volume of **{_fmt_value(volume, 'mm³')}** "
        f"({vol_cm3:.1f} cm³), approximate weight estimates:",
        f"- **PLA** (1.24 g/cm³): {vol_cm3 * 1.24:.1f} g",
        f"- **ABS** (1.05 g/cm³): {vol_cm3 * 1.05:.1f} g",
        f"- **Aluminum** (2.70 g/cm³): {vol_cm3 * 2.70:.1f} g",
        f"- **Steel** (7.85 g/cm³): {vol_cm3 * 7.85:.1f} g",
    ]

    return GeometryAnswer(
        answered=True,
        response_text="\n".join(estimates),
        dimensions=dims,
        source=source,
    )
