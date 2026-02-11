"""
Iterative reasoning engine for conversational CAD generation.

This module implements a multi-pass reasoning approach:
1. CLASSIFY - Identify the type of part
2. EXTRACT - Pull out dimensions and features
3. VALIDATE - Check if we have enough information
4. CLARIFY - Generate questions for missing info
5. PLAN - Create step-by-step build plan
6. EXECUTE - Generate geometry
7. VALIDATE - Verify result matches intent

The key insight: Better understanding leads to better generation.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from app.ai.client import get_ai_client
from app.ai.exceptions import AIConnectionError

logger = logging.getLogger(__name__)


# =============================================================================
# Reasoning States
# =============================================================================


class ReasoningState(StrEnum):
    """Current state of the reasoning process."""

    CLASSIFYING = "classifying"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    NEEDS_CLARIFICATION = "needs_clarification"
    READY_TO_PLAN = "ready_to_plan"
    PLANNING = "planning"
    READY_TO_GENERATE = "ready_to_generate"
    GENERATING = "generating"
    VALIDATING_RESULT = "validating_result"
    COMPLETE = "complete"
    FAILED = "failed"


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class PartClassification:
    """High-level classification of the part."""

    category: str  # bracket, enclosure, adapter, mount, custom
    subcategory: str | None = None  # L-bracket, U-bracket, etc.
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class ExtractedDimension:
    """A dimension extracted from user input."""

    name: str  # e.g., "length", "flange_length", "thickness"
    value: float
    unit: str = "mm"
    confidence: float = 1.0
    source: str = "explicit"  # explicit, inferred, default


@dataclass
class ExtractedFeature:
    """A feature extracted from user input."""

    feature_type: str  # hole, fillet, chamfer, slot, pocket
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    location: str = ""
    count: int = 1
    confidence: float = 1.0


@dataclass
class ClarificationQuestion:
    """A question to ask the user for clarification."""

    question: str
    context: str  # Why we're asking
    options: list[str] = field(default_factory=list)  # Suggested answers
    default: str | None = None
    priority: int = 1  # 1=critical, 2=important, 3=nice-to-have
    dimension_key: str | None = None  # Which dimension this fills


@dataclass
class PartUnderstanding:
    """Complete accumulated understanding of the user's request."""

    # Raw input accumulation
    user_messages: list[str] = field(default_factory=list)

    # Model context (optional - for questions about existing models)
    model_context: dict[str, Any] | None = None

    # Classification
    classification: PartClassification | None = None

    # Extracted information
    dimensions: dict[str, ExtractedDimension] = field(default_factory=dict)
    features: list[ExtractedFeature] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    hardware_references: list[dict[str, Any]] = field(default_factory=list)

    # Validation
    missing_critical: list[str] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    # Clarification
    questions: list[ClarificationQuestion] = field(default_factory=list)

    # Overall readiness
    state: ReasoningState = ReasoningState.CLASSIFYING
    completeness_score: float = 0.0  # 0-1, needs >0.7 to proceed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_messages": self.user_messages,
            "model_context": self.model_context,
            "classification": asdict(self.classification) if self.classification else None,
            "dimensions": {k: asdict(v) for k, v in self.dimensions.items()},
            "features": [asdict(f) for f in self.features],
            "constraints": self.constraints,
            "hardware_references": self.hardware_references,
            "missing_critical": self.missing_critical,
            "ambiguities": self.ambiguities,
            "assumptions": self.assumptions,
            "questions": [asdict(q) for q in self.questions],
            "state": self.state.value,
            "completeness_score": self.completeness_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PartUnderstanding:
        """Create from dictionary."""
        understanding = cls()
        understanding.user_messages = data.get("user_messages", [])
        understanding.model_context = data.get("model_context")

        if data.get("classification"):
            try:
                understanding.classification = PartClassification(**data["classification"])
            except (TypeError, KeyError) as e:
                logger.warning(f"Failed to parse classification: {e}")
                understanding.classification = None

        for k, v in data.get("dimensions", {}).items():
            try:
                if isinstance(v, dict) and "name" in v and "value" in v:
                    understanding.dimensions[k] = ExtractedDimension(**v)
                elif isinstance(v, (int, float)):
                    # Handle raw numeric values - convert to ExtractedDimension
                    understanding.dimensions[k] = ExtractedDimension(
                        name=k, value=float(v), unit="mm", confidence=1.0, source="stored"
                    )
                else:
                    logger.warning(f"Skipping invalid dimension {k}: {v}")
            except (TypeError, KeyError) as e:
                logger.warning(f"Failed to parse dimension {k}: {e}")

        for f in data.get("features", []):
            try:
                understanding.features.append(ExtractedFeature(**f))
            except (TypeError, KeyError) as e:
                logger.warning(f"Failed to parse feature: {e}")
        understanding.constraints = data.get("constraints", [])
        understanding.hardware_references = data.get("hardware_references", [])
        understanding.missing_critical = data.get("missing_critical", [])
        understanding.ambiguities = data.get("ambiguities", [])
        understanding.assumptions = data.get("assumptions", [])

        for q in data.get("questions", []):
            try:
                understanding.questions.append(ClarificationQuestion(**q))
            except (TypeError, KeyError) as e:
                logger.warning(f"Failed to parse question: {e}")

        try:
            understanding.state = ReasoningState(data.get("state", "classifying"))
        except ValueError:
            understanding.state = ReasoningState.CLASSIFYING

        understanding.completeness_score = data.get("completeness_score", 0.0)

        return understanding


# =============================================================================
# Prompts for Each Reasoning Pass
# =============================================================================

CLASSIFY_PROMPT = """You are a mechanical engineering expert. Classify the type of CAD part the user wants.

Categories:
- bracket: L-bracket, angle bracket, U-bracket, mounting bracket, shelf bracket
- enclosure: box, case, housing, container with walls
- adapter: connects two different parts/sizes
- mount: holds/positions something (camera mount, motor mount)
- plate: flat sheet with features (holes, slots)
- cylinder: cylindrical shapes (tubes, rods, bushings)
- custom: anything that doesn't fit above

User request: {user_input}

Respond with JSON only:
{{
    "category": "string",
    "subcategory": "string or null",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation"
}}"""


EXTRACT_PROMPT = """You are a mechanical engineer extracting dimensions from a part description.

Part type: {part_type}
User request: {user_input}
Previous context: {previous_context}
{model_context_section}

For {part_type}, the typical dimension names are:
{dimension_hints}

=== CRITICAL: ALL VALUES MUST BE IN MILLIMETERS ===
Convert ALL dimensions to millimeters before responding:
- 1 inch = 25.4 mm
- 1 foot = 304.8 mm
- 1 cm = 10 mm

RECOGNIZE ALL UNIT FORMATS:
- Symbols: 2" = 2 inches = 50.8mm, 3' = 3 feet = 914.4mm
- Fractions: 1/2" = 12.7mm, 1/4 inch = 6.35mm, 3/4" = 19.05mm
- Mixed: 1-1/2" = 38.1mm, 2 1/4" = 57.15mm
- Words: "half inch" = 12.7mm, "quarter inch" = 6.35mm

FRACTION TO DECIMAL:
- 1/8=0.125, 1/4=0.25, 3/8=0.375, 1/2=0.5, 5/8=0.625, 3/4=0.75, 7/8=0.875

Examples:
- "2 inches diameter" → diameter: 50.8
- "1.5\" tall" → height: 38.1
- "make the hole 1/2 inch" → diameter: 12.7
- "1-1/2\" diameter" → diameter: 38.1

Extract ALL dimensions mentioned. For each dimension:
- Identify the name and value
- CONVERT TO MILLIMETERS (the "value" field must be in mm)
- "unit" field should always be "mm"

=== HOLES ARE FEATURES, NOT DIMENSIONS ===
A "hole", "center hole", or "hole through" is a FEATURE, not a dimension.
- Put holes in the "features" array with feature_type="hole"
- Include the hole diameter in parameters: {{"diameter": value_in_mm}}
- Do NOT set inner_diameter for a hole (inner_diameter is for hollow pipes/tubes)

Example: "cylinder with 10mm center hole"
- dimensions: [{{"name": "diameter", ...}}, {{"name": "height", ...}}]
- features: [{{"feature_type": "hole", "description": "center hole", "parameters": {{"diameter": 10}}, "location": "center", "count": 1}}]

Respond with JSON only:
{{
    "dimensions": [
        {{"name": "string", "value": number_in_mm, "unit": "mm", "confidence": 0.0-1.0, "source": "explicit|inferred"}}
    ],
    "features": [
        {{"feature_type": "hole|fillet|chamfer|slot|pocket", "description": "string", "parameters": {{}}, "location": "string", "count": number}}
    ],
    "hardware_references": [
        {{"type": "bolt|screw|nut", "specification": "M5|1/4-20|etc", "purpose": "string"}}
    ],
    "constraints": ["list of constraints mentioned"]
}}"""


VALIDATE_PROMPT = """You are a mechanical engineer validating if we have enough information to build a part.

Part type: {part_type}

ALREADY EXTRACTED DIMENSIONS (check these against requirements):
{dimensions}

ALREADY EXTRACTED FEATURES:
{features}

REQUIRED dimensions for a {part_type}:
{required_dimensions}

OPTIONAL dimensions:
{optional_dimensions}

IMPORTANT: Only list a dimension as "missing_critical" if it is NOT already present in ALREADY EXTRACTED DIMENSIONS above.

Check:
1. Are all required dimensions provided in the extracted dimensions?
2. Are the values physically reasonable?
3. Are there any ambiguities or conflicts?

Respond with JSON only:
{{
    "is_complete": true/false,
    "missing_critical": ["only dimensions NOT in the extracted list above"],
    "ambiguities": ["list of unclear aspects"],
    "assumptions_needed": ["what we'd have to assume"],
    "completeness_score": 0.0 to 1.0,
    "can_proceed_with_defaults": true/false
}}"""


CLARIFY_PROMPT = """You are a helpful assistant gathering missing information for a CAD part.

Part type: {part_type}
What we know: {known_info}
What's missing: {missing_info}
Ambiguities: {ambiguities}

Generate 1-3 clarifying questions. Prioritize critical missing info first.
For each question:
- Be specific and user-friendly
- Suggest reasonable defaults when possible
- Provide options if applicable

Respond with JSON only:
{{
    "questions": [
        {{
            "question": "What should the thickness be?",
            "context": "Needed to create the plate geometry",
            "options": ["2mm", "3mm", "4mm", "5mm"],
            "default": "3mm",
            "priority": 1,
            "dimension_key": "thickness"
        }}
    ]
}}"""


PLAN_PROMPT = """You are a CAD engineer creating a build plan.

Part type: {part_type}
Dimensions: {dimensions}
Features: {features}

Create a step-by-step build order:
1. Base geometry (primitives, unions)
2. Subtractive features (cuts, holes)
3. Modifying features (fillets, chamfers)

Each step should be atomic and verifiable.

Respond with JSON only:
{{
    "steps": [
        {{
            "step_number": 1,
            "description": "Create horizontal flange",
            "operation": "create_box|union|cut|add_holes|add_fillet",
            "parameters": {{}},
            "validation": "How to verify success"
        }}
    ],
    "complexity": "simple|moderate|complex"
}}"""


# =============================================================================
# Dimension Hints by Part Type
# =============================================================================

DIMENSION_HINTS = {
    "bracket": """
- flange_length: Length of each flange (the arms of the L)
- flange_width: Width/depth of the flanges
- thickness: Material thickness (how thick the metal is)
- horizontal_flange_length: If flanges differ
- vertical_flange_length: If flanges differ
""",
    "enclosure": """
- length: External X dimension
- width: External Y dimension
- height: External Z dimension
- wall_thickness: Thickness of walls
- lid_thickness: Thickness of lid if separate
""",
    "plate": """
- length: X dimension
- width: Y dimension
- thickness: Z dimension (the thin direction)
""",
    "cylinder": """
- diameter: Outer diameter of the cylinder
- height: Height/length of cylinder
- inner_diameter: ONLY for hollow tubes/pipes where the entire inside is hollow
- wall_thickness: ONLY if making a hollow tube/pipe

IMPORTANT: A "center hole" or "hole in the center" is a FEATURE (see features below), NOT inner_diameter.
- inner_diameter makes the ENTIRE cylinder hollow like a pipe
- A "hole" is a feature that cuts through the solid material
""",
    "mount": """
- base_length: Length of mounting base
- base_width: Width of mounting base
- base_thickness: Thickness of base
- arm_length: If it has an arm
- arm_height: Height of arm
""",
    "custom": """
- length: X dimension
- width: Y dimension
- height: Z dimension
- thickness: Material thickness if applicable
""",
}

REQUIRED_DIMENSIONS = {
    "bracket": ["flange_length", "thickness"],
    "enclosure": ["length", "width", "height", "wall_thickness"],
    "plate": ["length", "width", "thickness"],
    "cylinder": ["diameter", "height"],
    "mount": ["base_length", "base_width"],
    "custom": [],
}

OPTIONAL_DIMENSIONS = {
    "bracket": ["flange_width", "horizontal_flange_length", "vertical_flange_length"],
    "enclosure": ["lid_thickness", "corner_radius"],
    "plate": [],
    "cylinder": ["inner_diameter", "wall_thickness"],
    "mount": ["base_thickness", "arm_length", "arm_height"],
    "custom": ["length", "width", "height", "thickness"],
}

# Map common dimension name variations to canonical names
DIMENSION_NAME_ALIASES = {
    # Length variations
    "external_x_dimension": "length",
    "external_length": "length",
    "x_dimension": "length",
    "x": "length",
    "long": "length",
    # Width variations
    "external_y_dimension": "width",
    "external_width": "width",
    "y_dimension": "width",
    "y": "width",
    "wide": "width",
    # Height variations
    "external_z_dimension": "height",
    "external_height": "height",
    "z_dimension": "height",
    "z": "height",
    "tall": "height",
    "depth": "height",  # Sometimes used for Z
    # Thickness variations
    "wall": "wall_thickness",
    "walls": "wall_thickness",
    "lid": "lid_thickness",
    # Radius variations
    "fillet": "fillet_radius",
    "fillet_size": "fillet_radius",
    "corner_fillet": "fillet_radius",
    "edge_fillet": "fillet_radius",
}


def _normalize_dimension_name(name: str) -> str:
    """Normalize dimension name to canonical form."""
    # Convert to lowercase and replace spaces with underscores
    normalized = name.lower().replace(" ", "_").replace("-", "_")
    # Check for aliases
    return DIMENSION_NAME_ALIASES.get(normalized, normalized)


# =============================================================================
# Reasoning Functions
# =============================================================================


def _extract_json(content: str) -> dict[str, Any]:
    """Extract JSON from AI response, handling markdown and extra text."""
    content = content.strip()

    # Remove markdown code blocks
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    # Try to find JSON object
    json_match = re.search(r"\{[\s\S]*\}", content)
    if json_match:
        content = json_match.group(0)

    try:
        return json.loads(content)  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Content was: {content[:500]}")

        # Try to repair common issues
        # Remove trailing commas before } or ]
        repaired = re.sub(r",\s*([}\]])", r"\1", content)
        # Try again
        try:
            return json.loads(repaired)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

        raise ValueError(f"Could not parse AI response as JSON: {content[:200]}")


async def classify_part(user_input: str) -> PartClassification:
    """
    Pass 1: Classify what type of part the user wants.
    """
    client = get_ai_client()

    prompt = CLASSIFY_PROMPT.format(user_input=user_input)
    messages = [{"role": "system", "content": prompt}]

    logger.info("Pass 1: Classifying part type...")

    try:
        # Use complete_json for JSON response format
        content = await client.complete_json(messages, temperature=0.2)
        data = _extract_json(content)

        classification = PartClassification(
            category=data.get("category", "custom"),
            subcategory=data.get("subcategory"),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning", ""),
        )

        logger.info(
            f"Classified as: {classification.category}/{classification.subcategory} ({classification.confidence})"
        )
        return classification

    except AIConnectionError:
        # Re-raise connection errors - these need to bubble up
        raise
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return PartClassification(category="custom", confidence=0.3)


async def extract_dimensions(
    user_input: str,
    part_type: str,
    previous_context: str = "",
    model_context: dict[str, Any] | None = None,
) -> tuple[dict[str, ExtractedDimension], list[ExtractedFeature], list[dict[str, Any]], list[str]]:
    """
    Pass 2: Extract dimensions and features from user input.
    
    Args:
        user_input: The user's message
        part_type: Type of part being created
        previous_context: Previously extracted dimensions
        model_context: Optional context about an existing model being discussed
    """
    client = get_ai_client()

    hints = DIMENSION_HINTS.get(part_type, DIMENSION_HINTS["custom"])
    
    # Format model context if provided
    model_context_section = ""
    if model_context:
        model_context_section = "\n\nCURRENT MODEL BEING DISCUSSED:\n"
        if "name" in model_context:
            model_context_section += f"Model Name: {model_context['name']}\n"
        if "description" in model_context:
            model_context_section += f"Description: {model_context['description']}\n"
        if "dimensions" in model_context:
            dims = model_context["dimensions"]
            if dims:
                dim_str = ", ".join(f"{k}: {v}" for k, v in dims.items() if k != "unit")
                model_context_section += f"Dimensions: {dim_str}\n"
        if "features" in model_context:
            features = model_context["features"]
            if features and len(features) > 0:
                feature_list = ", ".join(f.get("type", "unknown") for f in features[:5])
                model_context_section += f"Features: {feature_list}\n"
        model_context_section += "\nThe user is asking about or referring to this existing model.\n"
    
    prompt = EXTRACT_PROMPT.format(
        part_type=part_type,
        user_input=user_input,
        previous_context=previous_context or "None",
        dimension_hints=hints,
        model_context_section=model_context_section,
    )
    messages = [{"role": "system", "content": prompt}]

    logger.info("Pass 2: Extracting dimensions and features...")

    # Detect if user mentioned imperial units - used for sanity checking later
    user_input_lower = user_input.lower()
    user_mentioned_inches = any(
        pattern in user_input_lower
        for pattern in ("inch", "inches", '"', "''", " in ", " in,", " in.")
    )
    user_mentioned_feet = any(
        pattern in user_input_lower for pattern in ("foot", "feet", "'", " ft ", " ft,", " ft.")
    )

    try:
        # Use complete_json for JSON response format
        content = await client.complete_json(messages, temperature=0.2)
        data = _extract_json(content)

        dimensions = {}
        for dim in data.get("dimensions", []):
            # Handle both proper format {"name": "x", "value": 10}
            # and malformed {"x": 10} responses from AI
            if isinstance(dim, dict) and "name" in dim:
                # Proper format
                raw_name = dim["name"]
                value = dim["value"]
                unit = dim.get("unit", "mm").lower().strip()
            elif isinstance(dim, dict) and len(dim) >= 1:
                # Malformed: AI returned {"diameter": 50} instead of {"name": "diameter", "value": 50}
                # Try to extract from first key-value pair
                first_key = next(iter(dim))
                if first_key not in ("name", "value", "unit", "confidence", "source"):
                    raw_name = first_key
                    value = dim[first_key]
                    unit = dim.get("unit", "mm") if isinstance(dim.get("unit"), str) else "mm"
                    unit = unit.lower().strip()
                    logger.warning(f"Recovered malformed dimension: {raw_name}={value}")
                else:
                    logger.warning(f"Skipping malformed dimension entry: {dim}")
                    continue
            else:
                logger.warning(f"Skipping invalid dimension entry: {dim}")
                continue

            # Normalize dimension name to canonical form
            canonical_name = _normalize_dimension_name(raw_name)

            # Convert to mm if not already (safety net in case AI didn't convert)
            if unit in ("in", "inch", "inches"):
                value = value * 25.4
                unit = "mm"
            elif unit in ("cm",):
                value = value * 10.0
                unit = "mm"
            elif unit in ("ft", "feet", "foot"):
                value = value * 304.8
                unit = "mm"

            # SANITY CHECK: Detect likely unconverted values
            # If user explicitly mentioned inches but the value is very small,
            # the AI likely failed to convert (e.g., returned 2 instead of 50.8 for "2 inches")
            if unit == "mm" and user_mentioned_inches:
                # Parse numeric values from user input to check for matches
                import re

                # Find all numbers in the user input that might be inch measurements
                # Pattern matches: "2 inches", "2 inch", "2\"", "2 in"
                inch_patterns = re.findall(
                    r'(\d+(?:\.\d+)?)\s*(?:inch|inches|"|in\b)', user_input_lower
                )
                for inch_val_str in inch_patterns:
                    inch_val = float(inch_val_str)
                    expected_mm = inch_val * 25.4
                    # If current value matches the raw inch number (not converted)
                    # and is significantly different from expected mm value
                    if abs(value - inch_val) < 1.0 and expected_mm > value * 1.5:
                        logger.warning(
                            f"Detected unconverted inch value for {canonical_name}: "
                            f"{value} should be {expected_mm}mm"
                        )
                        value = expected_mm
                        break

            if unit == "mm" and user_mentioned_feet:
                import re

                feet_patterns = re.findall(
                    r"(\d+(?:\.\d+)?)\s*(?:foot|feet|\'|ft\b)", user_input_lower
                )
                for feet_val_str in feet_patterns:
                    feet_val = float(feet_val_str)
                    expected_mm = feet_val * 304.8
                    if abs(value - feet_val) < 1.0 and expected_mm > value * 1.5:
                        logger.warning(
                            f"Detected unconverted feet value for {canonical_name}: "
                            f"{value} should be {expected_mm}mm"
                        )
                        value = expected_mm
                        break

            dimensions[canonical_name] = ExtractedDimension(
                name=canonical_name,
                value=round(value, 2),
                unit="mm",  # Always mm after conversion
                confidence=dim.get("confidence", 1.0),
                source=dim.get("source", "explicit"),
            )

        features = [
            ExtractedFeature(
                feature_type=f.get("feature_type", "unknown"),
                description=f.get("description", ""),
                parameters=f.get("parameters", {}),
                location=f.get("location", ""),
                count=f.get("count", 1),
            )
            for f in data.get("features", [])
        ]

        # SAFEGUARD: If there's a center hole feature, remove any inner_diameter dimension
        # (the AI sometimes confuses "center hole" with hollow cylinder)
        has_center_hole_feature = any(
            f.feature_type == "hole"
            and ("center" in f.location.lower() or "center" in f.description.lower())
            for f in features
        )
        if has_center_hole_feature and "inner_diameter" in dimensions:
            logger.warning(
                "Removing conflicting inner_diameter dimension - "
                "center hole is a feature, not a hollow cylinder"
            )
            del dimensions["inner_diameter"]

        hardware = data.get("hardware_references", [])
        constraints = data.get("constraints", [])

        logger.info(f"Extracted {len(dimensions)} dimensions, {len(features)} features")
        return dimensions, features, hardware, constraints

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {}, [], [], []


async def validate_completeness(
    part_type: str,
    dimensions: dict[str, ExtractedDimension],
    features: list[ExtractedFeature],
) -> tuple[bool, list[str], list[str], list[str], float]:
    """
    Pass 3: Validate if we have enough information.

    Returns: (is_complete, missing_critical, ambiguities, assumptions, completeness_score)
    """
    required = REQUIRED_DIMENSIONS.get(part_type, [])
    optional = OPTIONAL_DIMENSIONS.get(part_type, [])

    # Do a simple programmatic check first
    dim_names = set(dimensions.keys())
    missing_required = [r for r in required if r not in dim_names]

    # For brackets, also accept horizontal/vertical flange lengths
    if part_type == "bracket" and "flange_length" in missing_required:
        if "horizontal_flange_length" in dim_names or "vertical_flange_length" in dim_names:
            missing_required.remove("flange_length")

    # Calculate simple completeness score
    total_required = len(required) if required else 1
    provided = total_required - len(missing_required)
    base_score = provided / total_required if total_required > 0 else 0.5

    # Boost score if we have optional dimensions
    optional_count = sum(1 for o in optional if o in dim_names)
    score_boost = optional_count * 0.1
    score = min(1.0, base_score + score_boost)

    logger.info(
        f"Completeness check: required={required}, have={list(dim_names)}, missing={missing_required}, score={score:.2f}"
    )

    # If all required are present, we're complete
    if not missing_required:
        return True, [], [], [], score

    # Otherwise call LLM for deeper analysis only if missing something
    client = get_ai_client()

    dims_str = json.dumps({k: f"{v.value}mm" for k, v in dimensions.items()})
    features_str = json.dumps([asdict(f) for f in features])

    prompt = VALIDATE_PROMPT.format(
        part_type=part_type,
        dimensions=dims_str,
        features=features_str,
        required_dimensions=", ".join(required) or "none specific",
        optional_dimensions=", ".join(optional) or "none",
    )
    messages = [{"role": "system", "content": prompt}]

    logger.info("Pass 3: Validating completeness...")

    try:
        # Use complete_json for JSON response format
        content = await client.complete_json(messages, temperature=0.2)
        data = _extract_json(content)

        is_complete = data.get("is_complete", False)
        missing = data.get("missing_critical", [])
        ambiguities = data.get("ambiguities", [])
        assumptions = data.get("assumptions_needed", [])
        score = data.get("completeness_score", 0.5)

        logger.info(f"Completeness: {score:.2f}, missing: {missing}")
        return is_complete, missing, ambiguities, assumptions, score

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False, ["unknown"], [], [], 0.3


async def generate_clarifications(
    part_type: str,
    known: dict[str, ExtractedDimension],
    missing: list[str],
    ambiguities: list[str],
) -> list[ClarificationQuestion]:
    """
    Pass 4: Generate clarifying questions for the user.
    """
    client = get_ai_client()

    known_str = json.dumps({k: f"{v.value}mm" for k, v in known.items()})

    prompt = CLARIFY_PROMPT.format(
        part_type=part_type,
        known_info=known_str,
        missing_info=", ".join(missing) or "none",
        ambiguities=", ".join(ambiguities) or "none",
    )
    messages = [{"role": "system", "content": prompt}]

    logger.info("Pass 4: Generating clarifications...")

    try:
        # Use complete_json for JSON response format
        content = await client.complete_json(messages, temperature=0.4)
        data = _extract_json(content)

        questions = [
            ClarificationQuestion(
                question=q["question"],
                context=q.get("context", ""),
                options=q.get("options", []),
                default=q.get("default"),
                priority=q.get("priority", 2),
                dimension_key=q.get("dimension_key"),
            )
            for q in data.get("questions", [])
        ]

        logger.info(f"Generated {len(questions)} clarification questions")
        return questions

    except Exception as e:
        logger.error(f"Clarification generation failed: {e}")
        return []


# =============================================================================
# Main Reasoning Engine
# =============================================================================


async def process_user_message(
    user_message: str,
    understanding: PartUnderstanding | None = None,
) -> PartUnderstanding:
    """
    Process a user message through the iterative reasoning pipeline.

    This is the main entry point. It advances the understanding based
    on the current state and new input.
    """
    if understanding is None:
        understanding = PartUnderstanding()

    # Add message to history
    understanding.user_messages.append(user_message)
    all_input = " ".join(understanding.user_messages)

    # State machine
    if understanding.state == ReasoningState.CLASSIFYING:
        # Pass 1: Classify
        classification = await classify_part(all_input)
        understanding.classification = classification
        understanding.state = ReasoningState.EXTRACTING

    if understanding.state == ReasoningState.EXTRACTING:
        # Pass 2: Extract
        part_type = (
            understanding.classification.category if understanding.classification else "custom"
        )
        prev_context = json.dumps({k: f"{v.value}mm" for k, v in understanding.dimensions.items()})

        dims, features, hardware, constraints = await extract_dimensions(
            all_input, part_type, prev_context, understanding.model_context
        )

        # Merge with existing (new values override)
        understanding.dimensions.update(dims)
        understanding.features.extend(features)
        understanding.hardware_references.extend(hardware)
        understanding.constraints.extend(constraints)

        understanding.state = ReasoningState.VALIDATING

    if understanding.state == ReasoningState.VALIDATING:
        # Pass 3: Validate
        part_type = (
            understanding.classification.category if understanding.classification else "custom"
        )

        is_complete, missing, ambiguities, assumptions, score = await validate_completeness(
            part_type, understanding.dimensions, understanding.features
        )

        understanding.missing_critical = missing
        understanding.ambiguities = ambiguities
        understanding.assumptions = assumptions
        understanding.completeness_score = score

        # Ready if explicitly complete, high score, or no missing critical dimensions
        if is_complete or score >= 0.7 or (not missing and score >= 0.5):
            understanding.state = ReasoningState.READY_TO_PLAN
            understanding.questions = []
            logger.info(f"Ready to plan: complete={is_complete}, score={score}, missing={missing}")
        else:
            understanding.state = ReasoningState.NEEDS_CLARIFICATION
            logger.info(f"Needs clarification: score={score}, missing={missing}")

    if understanding.state == ReasoningState.NEEDS_CLARIFICATION:
        # Pass 4: Generate questions if we don't have them
        if not understanding.questions:
            part_type = (
                understanding.classification.category if understanding.classification else "custom"
            )
            questions = await generate_clarifications(
                part_type,
                understanding.dimensions,
                understanding.missing_critical,
                understanding.ambiguities,
            )
            understanding.questions = questions

    return understanding


async def apply_clarification_response(
    response: str,
    understanding: PartUnderstanding,
) -> PartUnderstanding:
    """
    Apply a user's response to clarification questions and re-process.
    """
    # The response is new input, so add it and re-run extraction/validation
    understanding.state = ReasoningState.EXTRACTING
    understanding.questions = []  # Clear old questions

    return await process_user_message(response, understanding)


def format_questions_for_user(understanding: PartUnderstanding) -> str:
    """
    Format clarification questions as a user-friendly message.
    Falls back to asking about missing_critical if no explicit questions.
    """
    lines = ["I need a bit more information to create your part:\n"]

    if understanding.questions:
        # Use AI-generated questions
        for i, q in enumerate(understanding.questions, 1):
            lines.append(f"**{i}. {q.question}**")
            if q.context:
                lines.append(f"   _{q.context}_")
            if q.options:
                lines.append(f"   Options: {', '.join(q.options)}")
            if q.default:
                lines.append(f"   (Default: {q.default})")
            lines.append("")
    elif understanding.missing_critical:
        # Fallback to asking about missing critical dimensions
        lines.append("Please provide the following dimensions:\n")
        for i, missing in enumerate(understanding.missing_critical, 1):
            # Format the dimension name nicely
            readable_name = missing.replace("_", " ").title()
            lines.append(f"**{i}. {readable_name}**")
            lines.append(
                f"   _This dimension is required for your {understanding.classification.category if understanding.classification else 'part'}._"
            )
            lines.append("")
    else:
        # Generic fallback
        lines.append("Could you provide more details about the dimensions and features you need?")

    return "\n".join(lines)


def format_understanding_summary(understanding: PartUnderstanding) -> str:
    """
    Format current understanding as a confirmation message.
    """
    lines = ["Here's what I understand:\n"]

    if understanding.classification:
        lines.append(f"**Part Type:** {understanding.classification.category}")
        if understanding.classification.subcategory:
            lines.append(f" ({understanding.classification.subcategory})")
        lines.append("")

    if understanding.dimensions:
        lines.append("**Dimensions:**")
        for name, dim in understanding.dimensions.items():
            source = " (assumed)" if dim.source == "inferred" else ""
            lines.append(f"  - {name}: {dim.value}mm{source}")
        lines.append("")

    if understanding.features:
        lines.append("**Features:**")
        for f in understanding.features:
            lines.append(f"  - {f.feature_type}: {f.description}")
        lines.append("")

    if understanding.assumptions:
        lines.append("**Assumptions:**")
        for a in understanding.assumptions:
            lines.append(f"  - {a}")
        lines.append("")

    lines.append(f"**Confidence:** {understanding.completeness_score:.0%}")

    return "\n".join(lines)
