"""
Natural language to CAD parameters parser.

Converts user descriptions into structured CADParameters using AI
with validation and unit conversion.

Example:
    >>> from app.ai.parser import parse_description
    >>> result = await parse_description("Create a box 100x50x30mm")
    >>> print(result.parameters.shape)  # "box"
    >>> print(result.parameters.dimensions)  # {"length": 100, "width": 50, "height": 30}
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.ai.client import ClaudeClient, get_ai_client
from app.ai.exceptions import AIParseError, AIValidationError
from app.ai.prompts import DIMENSION_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


# =============================================================================
# Unit Conversion
# =============================================================================


class Unit(StrEnum):
    """Supported measurement units."""

    MM = "mm"
    CM = "cm"
    M = "m"
    INCHES = "inches"
    IN = "in"
    FEET = "feet"
    FT = "ft"


# Conversion factors to millimeters
UNIT_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "inches": 25.4,
    "in": 25.4,
    "inch": 25.4,
    "feet": 304.8,
    "ft": 304.8,
    "foot": 304.8,
}


def convert_to_mm(value: float, unit: str) -> float:
    """
    Convert a value to millimeters.

    Args:
        value: Numeric value
        unit: Source unit name

    Returns:
        Value in millimeters

    Raises:
        ValueError: If unit not recognized
    """
    unit_lower = unit.lower().strip()

    if unit_lower not in UNIT_TO_MM:
        raise ValueError(f"Unknown unit: {unit}. Supported: {list(UNIT_TO_MM.keys())}")

    return value * UNIT_TO_MM[unit_lower]


# =============================================================================
# Data Models
# =============================================================================


class ShapeType(StrEnum):
    """Supported 3D shape types."""

    BOX = "box"
    CYLINDER = "cylinder"
    SPHERE = "sphere"
    CONE = "cone"
    TORUS = "torus"
    WEDGE = "wedge"
    ENCLOSURE = "enclosure"  # Multi-part assembly
    CUSTOM = "custom"


class AssemblyType(StrEnum):
    """Types of multi-part assemblies."""

    NONE = "none"  # Single part
    ENCLOSURE = "enclosure"  # Box with lid
    CLAMSHELL = "clamshell"  # Two-half shell
    STACKED = "stacked"  # Stacked components


class FeatureType(StrEnum):
    """Supported feature types."""

    HOLE = "hole"
    FILLET = "fillet"
    CHAMFER = "chamfer"
    SLOT = "slot"
    POCKET = "pocket"
    BOSS = "boss"


class Feature(BaseModel):
    """A feature to add to a shape (hole, fillet, etc.)."""

    type: FeatureType
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("parameters", mode="before")
    @classmethod
    def ensure_parameters_mm(cls, v: dict) -> dict:
        """Ensure feature parameters are in mm."""
        # Common dimension keys that should be converted
        dimension_keys = ["radius", "diameter", "depth", "width", "length", "height", "size"]

        result = {}
        for key, value in v.items():
            if key in dimension_keys and isinstance(value, (int, float)):
                # Already in mm (conversion happens at parse time)
                result[key] = float(value)
            else:
                result[key] = value

        return result


class CADParameters(BaseModel):
    """
    Structured CAD parameters extracted from natural language.

    All dimensions are normalized to millimeters.
    """

    shape: ShapeType
    dimensions: dict[str, float] = Field(
        description="Shape dimensions in mm (length, width, height, radius, etc.)"
    )
    features: list[Feature] = Field(
        default_factory=list, description="Additional features like holes, fillets"
    )
    units: str = Field(default="mm", description="Original units from user input")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="AI confidence score")
    assumptions: list[str] = Field(
        default_factory=list, description="Assumptions made during parsing"
    )

    # Assembly-specific fields
    assembly_type: AssemblyType = Field(
        default=AssemblyType.NONE, description="Type of multi-part assembly"
    )
    assembly_config: dict[str, Any] = Field(
        default_factory=dict, description="Assembly-specific configuration"
    )

    @model_validator(mode="after")
    def validate_dimensions(self) -> CADParameters:
        """Validate dimensions are appropriate for shape type."""
        shape = self.shape
        dims = self.dimensions

        # Required dimensions per shape
        required = {
            ShapeType.BOX: ["length", "width", "height"],
            ShapeType.CYLINDER: ["height"],  # Needs radius OR diameter
            ShapeType.SPHERE: [],  # Needs radius OR diameter
            ShapeType.CONE: ["height"],  # Needs at least one radius
            ShapeType.TORUS: ["major_radius", "minor_radius"],
            ShapeType.WEDGE: ["length", "width", "height"],
            ShapeType.ENCLOSURE: ["length", "width", "height"],  # Same as box
        }

        if shape in required:
            for dim in required[shape]:
                if dim not in dims:
                    raise ValueError(f"{shape.value} requires '{dim}' dimension")

        # Cylinder/sphere need radius or diameter
        if shape in (ShapeType.CYLINDER, ShapeType.SPHERE, ShapeType.CONE):
            has_radius = "radius" in dims or "radius1" in dims
            has_diameter = "diameter" in dims or "diameter1" in dims
            if not (has_radius or has_diameter):
                raise ValueError(f"{shape.value} requires 'radius' or 'diameter'")

        # Enclosures must have assembly type set
        if shape == ShapeType.ENCLOSURE and self.assembly_type == AssemblyType.NONE:
            self.assembly_type = AssemblyType.ENCLOSURE

        # All dimensions must be positive
        for key, value in dims.items():
            if value <= 0:
                raise ValueError(f"Dimension '{key}' must be positive, got {value}")

        return self

    def get_dimension(self, name: str, default: float | None = None) -> float:
        """Get a dimension value, with optional default."""
        if name in self.dimensions:
            return self.dimensions[name]
        if default is not None:
            return default
        raise KeyError(f"Dimension '{name}' not found")

    @property
    def has_features(self) -> bool:
        """Check if parameters include features."""
        return len(self.features) > 0


@dataclass
class ParseResult:
    """Result of parsing a natural language description."""

    parameters: CADParameters
    raw_response: str
    parse_time_ms: float

    @property
    def is_high_confidence(self) -> bool:
        """Check if parsing was high confidence (>0.8)."""
        return self.parameters.confidence >= 0.8


# =============================================================================
# Parser Implementation
# =============================================================================


class DescriptionParser:
    """
    Parses natural language descriptions into CAD parameters.

    Uses Claude to extract structured parameters from free-form text,
    then validates and normalizes the output.
    """

    MIN_CONFIDENCE_THRESHOLD = 0.5

    # Dimension name aliases for normalization
    BOX_DIMENSION_ALIASES = {
        # Height aliases
        "height": "height",
        "tall": "height",
        "h": "height",
        "z": "height",
        "depth": "height",  # Can be height in some contexts
        # Width aliases
        "width": "width",
        "wide": "width",
        "w": "width",
        "y": "width",
        # Length aliases
        "length": "length",
        "long": "length",
        "l": "length",
        "x": "length",
    }

    def __init__(self, client: ClaudeClient | None = None):
        """
        Initialize parser.

        Args:
            client: Claude client (default: singleton from get_ai_client)
        """
        self.client = client or get_ai_client()

    def _normalize_box_dimensions(self, dims: dict[str, float]) -> dict[str, float]:
        """
        Normalize box dimension names to standard length/width/height.

        Handles cases where AI returns 'depth', 'tall', 'wide', etc.
        """
        result = {}
        used_dims = set()

        # First pass: map known aliases
        for key, value in dims.items():
            normalized_key = self.BOX_DIMENSION_ALIASES.get(key.lower(), key.lower())
            if normalized_key in ("length", "width", "height"):
                if normalized_key not in result:
                    result[normalized_key] = value
                    used_dims.add(key)

        # Second pass: if we're missing required dims, try to infer
        required = ["length", "width", "height"]
        missing = [d for d in required if d not in result]

        # Get unused dimension values
        unused_values = [v for k, v in dims.items() if k not in used_dims]

        # Assign unused values to missing dimensions
        for dim, val in zip(missing, unused_values, strict=False):
            result[dim] = val

        # If we still have exactly 3 values but wrong keys, just assign them
        if len(result) < 3 and len(dims) >= 3:
            all_values = list(dims.values())[:3]
            for i, dim in enumerate(required):
                if dim not in result and i < len(all_values):
                    result[dim] = all_values[i]

        return result

    async def parse(self, description: str) -> ParseResult:
        """
        Parse a natural language description into CAD parameters.

        Args:
            description: User's description of the part

        Returns:
            ParseResult with extracted parameters

        Raises:
            AIParseError: If AI response cannot be parsed
            AIValidationError: If extracted parameters are invalid
        """
        import time

        start = time.monotonic()

        # Quick pre-processing
        description = description.strip()
        if not description:
            raise AIValidationError("Empty description provided")

        # Format prompt
        messages = DIMENSION_EXTRACTION_PROMPT.format_messages(user_input=description)

        # Call AI
        raw_response = await self.client.complete_json(
            messages,
            temperature=DIMENSION_EXTRACTION_PROMPT.temperature,
        )

        # Parse JSON response
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise AIParseError(
                f"Invalid JSON in AI response: {e}",
                raw_response=raw_response,
            )

        # Normalize and validate
        try:
            parameters = self._normalize_parameters(data)
        except ValueError as e:
            raise AIValidationError(
                f"Parameter validation failed: {e}",
                validation_errors=[str(e)],
            )

        elapsed_ms = (time.monotonic() - start) * 1000

        logger.info(
            f"Parsed description into {parameters.shape.value} with confidence {parameters.confidence:.2f}",
            extra={
                "shape": parameters.shape.value,
                "confidence": parameters.confidence,
                "parse_time_ms": round(elapsed_ms, 1),
            },
        )

        return ParseResult(
            parameters=parameters,
            raw_response=raw_response,
            parse_time_ms=elapsed_ms,
        )

    def _normalize_parameters(self, data: dict) -> CADParameters:
        """
        Normalize AI output into CADParameters.

        Handles unit conversion and data cleanup.
        """
        # Get original units
        original_units = data.get("units", "mm").lower()

        # Convert dimensions to mm if needed
        dimensions = data.get("dimensions", {})
        normalized_dims = {}

        for key, value in dimensions.items():
            if isinstance(value, (int, float)):
                if original_units != "mm":
                    normalized_dims[key] = convert_to_mm(value, original_units)
                else:
                    normalized_dims[key] = float(value)

        # Normalize dimension names for boxes and enclosures
        shape_str = data.get("shape", "box").lower()
        if shape_str in ("box", "enclosure"):
            normalized_dims = self._normalize_box_dimensions(normalized_dims)

        # Normalize features
        features = []
        for feature_data in data.get("features", []):
            feature_type = feature_data.get("type", "").lower()
            params = feature_data.get("parameters", {})

            # Convert feature dimensions if needed
            if original_units != "mm":
                for key in ["radius", "diameter", "depth", "width", "length", "height"]:
                    if key in params and isinstance(params[key], (int, float)):
                        params[key] = convert_to_mm(params[key], original_units)

            if feature_type and feature_type in [f.value for f in FeatureType]:
                features.append(Feature(type=FeatureType(feature_type), parameters=params))

        # Handle assembly configuration
        assembly_config = data.get("assembly_config", {})
        assembly_type = AssemblyType.NONE
        if shape_str == "enclosure":
            assembly_type = AssemblyType.ENCLOSURE

        # Build and validate
        return CADParameters(
            shape=ShapeType(shape_str),
            dimensions=normalized_dims,
            features=features,
            units=original_units,
            confidence=data.get("confidence", 0.5),
            assumptions=data.get("assumptions", []),
            assembly_type=assembly_type,
            assembly_config=assembly_config,
        )


# =============================================================================
# Convenience Function
# =============================================================================


async def parse_description(description: str) -> ParseResult:
    """
    Parse a natural language description into CAD parameters.

    Convenience function using default parser.

    Args:
        description: User's description of the part to create

    Returns:
        ParseResult with extracted CADParameters

    Example:
        >>> result = await parse_description("Create a box 100x50x30mm")
        >>> print(result.parameters.dimensions)
        {'length': 100.0, 'width': 50.0, 'height': 30.0}
    """
    parser = DescriptionParser()
    return await parser.parse(description)
