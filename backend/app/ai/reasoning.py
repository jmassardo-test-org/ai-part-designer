"""
AI Reasoning and Intent Detection for CAD Generation.

This module implements a multi-step reasoning approach:
1. Understand - Parse and deeply understand what the user wants
2. Plan - Create a structured build plan with steps
3. Generate - Execute the plan with validation at each step
4. Validate - Verify the result meets the intent

The key insight: Better understanding leads to better generation.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.ai.client import get_ai_client

logger = logging.getLogger(__name__)


# =============================================================================
# Unit Conversion - Ensure all dimensions are in millimeters
# =============================================================================

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


def _normalize_dimensions_to_mm(raw_dims: dict[str, Any]) -> dict[str, Any]:
    """
    Convert all dimension values to millimeters.

    If a "unit" key is present and it's not "mm", convert all numeric values.
    Remove the "unit" key from the output since all values will be in mm.
    """
    if not raw_dims:
        return {}

    # Check if there's a unit specification
    unit = raw_dims.get("unit", "mm")
    unit = unit.lower().strip() if isinstance(unit, str) else "mm"

    conversion_factor = UNIT_TO_MM.get(unit, 1.0)

    normalized = {}
    for key, value in raw_dims.items():
        if key == "unit":
            continue  # Skip the unit key

        if isinstance(value, (int, float)):
            # Apply conversion
            normalized[key] = round(value * conversion_factor, 2)
        else:
            # Keep non-numeric values as-is
            normalized[key] = value

    if conversion_factor != 1.0:
        logger.info(f"Converted dimensions from {unit} to mm (factor: {conversion_factor})")

    return normalized


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class PartIntent:
    """Structured representation of what the user wants to build."""

    # Core understanding
    part_type: str  # e.g., "bracket", "enclosure", "adapter", "custom"
    primary_function: str  # What is this part for?

    # Geometric properties
    overall_dimensions: dict[str, float] = field(default_factory=dict)  # L, W, H or D, H
    material_thickness: float | None = None

    # Features
    features: list[dict[str, Any]] = field(default_factory=list)  # holes, fillets, etc.

    # Constraints
    constraints: list[str] = field(default_factory=list)  # "must fit M5 bolt", etc.

    # References
    referenced_hardware: list[dict[str, Any]] = field(default_factory=list)
    referenced_files: list[str] = field(default_factory=list)

    # Confidence and clarifications needed
    confidence: float = 0.0
    clarifications_needed: list[str] = field(default_factory=list)
    assumptions_made: list[str] = field(default_factory=list)


@dataclass
class BuildStep:
    """A single step in the build plan."""

    step_number: int
    description: str
    operation: str  # "create_base", "add_feature", "boolean", "modify"
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: list[int] = field(default_factory=list)
    validation: str | None = None  # How to validate this step succeeded


@dataclass
class BuildPlan:
    """Complete plan for building the part."""

    intent: PartIntent
    steps: list[BuildStep] = field(default_factory=list)
    estimated_complexity: str = "simple"  # simple, moderate, complex
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# Reasoning Prompts
# =============================================================================

UNDERSTAND_INTENT_PROMPT = """You are an expert mechanical engineer and CAD designer.
Your task is to deeply understand what the user wants to build.

Analyze the user's request and extract:
1. What TYPE of part is this? (bracket, enclosure, adapter, mount, custom shape, etc.)
2. What is its PRIMARY FUNCTION? (mounting, protection, connection, support, etc.)
3. What are the KEY DIMENSIONS? Extract ALL dimensions and CONVERT TO MILLIMETERS.
4. What FEATURES are needed? (holes, fillets, chamfers, slots, pockets, ribs, etc.)
5. What CONSTRAINTS exist? (must fit specific bolt, must mate with another part, etc.)
6. What HARDWARE is referenced? (M5 bolts, 1/4-20 screws, bearings, etc.)
7. What ASSUMPTIONS must you make? (if dimensions aren't fully specified)
8. What CLARIFICATIONS would help? (ambiguous requirements)

=== CRITICAL: UNIT CONVERSION ===
ALL dimension values MUST be in MILLIMETERS. Convert from other units:
- 1 inch = 25.4 mm
- 1 foot = 304.8 mm
- 1 cm = 10 mm
- 1 m = 1000 mm

RECOGNIZE ALL UNIT FORMATS:
- Symbols: 2" = 2 inches, 3' = 3 feet, 1'6" = 1.5 feet = 457.2mm
- Fractions: 1/2" = 0.5 inches = 12.7mm, 3/4 inch = 19.05mm
- Mixed: 1-1/2" = 1.5 inches = 38.1mm, 2 1/4" = 2.25 inches = 57.15mm
- Words: "half inch" = 12.7mm, "quarter inch" = 6.35mm
- Decimal: 1.5" = 38.1mm, 0.75 inch = 19.05mm

COMMON FRACTIONS TO DECIMAL:
- 1/8 = 0.125, 1/4 = 0.25, 3/8 = 0.375, 1/2 = 0.5
- 5/8 = 0.625, 3/4 = 0.75, 7/8 = 0.875

Examples:
- "2 inches diameter" → diameter: 50.8
- "1.5\" in diameter" → diameter: 38.1
- "1/2 inch hole" → hole diameter: 12.7
- "4' tall" → height: 1219.2
- "make the hole 1/2 inch" → hole diameter: 12.7

Think step by step about the geometry. Consider:
- How would this part be manufactured?
- What are standard practices for this type of part?
- Are the dimensions physically reasonable?

=== DIMENSION NAMING CONVENTIONS ===
For different part types, use these dimension names:

L-BRACKET/ANGLE BRACKET:
- flange_length: Length of each flange (both flanges if equal)
- flange_width: Width of the flanges (depth in Z direction)
- thickness: Material thickness (how thick the metal/material is)
- horizontal_flange_length: If horizontal flange differs
- vertical_flange_length: If vertical flange differs

BOX/ENCLOSURE:
- length: X dimension
- width: Y dimension
- height: Z dimension
- wall_thickness: For hollow enclosures

CYLINDER:
- diameter: Outer diameter
- height: Height of cylinder
- inner_diameter: For hollow cylinders

PLATE/SHEET:
- length: X dimension
- width: Y dimension
- thickness: Z dimension (the thin direction)

=== EXAMPLE FOR L-BRACKET ===
User says: "50mm flanges, 4mm thick, M5 mounting holes"
Correct interpretation:
{
    "part_type": "angle bracket",
    "overall_dimensions": {
        "flange_length": 50,
        "flange_width": 50,
        "thickness": 4
    },
    "material_thickness": 4,
    "features": [
        {"type": "hole", "description": "M5 clearance hole", "parameters": {"diameter": 5.3}, "location": "each flange", "count": 4}
    ]
}

=== EXAMPLE FOR CYLINDER WITH UNIT CONVERSION ===
User says: "2 inches diameter, 4 inches tall cylinder with 1/2\" center hole"
Correct interpretation (ALL VALUES IN MM):
{
    "part_type": "cylinder",
    "overall_dimensions": {
        "diameter": 50.8,
        "height": 101.6
    },
    "features": [
        {"type": "hole", "description": "center hole", "parameters": {"diameter": 12.7}, "location": "center through", "count": 1}
    ]
}

User says: "add another cylinder that's 1.5\" in diameter and 2 inches tall"
Correct interpretation:
{
    "overall_dimensions": {
        "diameter": 38.1,
        "height": 50.8
    }
}

Respond with a JSON object:
{
    "part_type": "string - category of part",
    "primary_function": "string - what is this part for",
    "overall_dimensions": {
        ... ALL VALUES MUST BE IN MILLIMETERS ...
    },
    "material_thickness": number or null (in mm),
    "features": [
        {
            "type": "hole|fillet|chamfer|slot|pocket|rib|boss|thread",
            "description": "string",
            "parameters": { ... all dimensions in mm ... },
            "location": "string describing where on the part",
            "count": number
        }
    ],
    "constraints": ["list of constraints"],
    "referenced_hardware": [
        {
            "type": "bolt|screw|nut|bearing|etc",
            "specification": "M5|1/4-20|etc",
            "quantity": number
        }
    ],
    "assumptions_made": ["list of assumptions"],
    "clarifications_needed": ["list of questions that would help"],
    "confidence": 0.0 to 1.0
}

User's request: """


CREATE_BUILD_PLAN_PROMPT = """You are an expert CAD engineer creating a build plan.

Given this understanding of what the user wants:
{intent_json}

Create a step-by-step plan to build this part in Build123d. Each step should be:
- Atomic (one operation)
- Verifiable (can check if it succeeded)
- Building on previous steps

Consider the ORDER of operations:
1. Create base geometry first (primitives, extrusions)
2. Add boolean operations (fuse, cut)
3. Add holes (they cut into existing geometry)
4. Add fillets/chamfers LAST (they modify existing edges)

For each step, specify:
- The Build123d operation to use
- Parameters needed
- How to validate success

Respond with a JSON object:
{
    "estimated_complexity": "simple|moderate|complex",
    "steps": [
        {
            "step_number": 1,
            "description": "Human-readable description",
            "operation": "create_box|create_cylinder|extrude|fuse|cut|add_holes|add_fillet|add_chamfer|transform",
            "parameters": {
                ... operation-specific parameters ...
            },
            "depends_on": [list of step numbers this depends on],
            "validation": "How to verify this step succeeded"
        }
    ],
    "warnings": ["Any concerns about the plan"]
}

IMPORTANT operation parameter schemas:

create_box: {"length": mm, "width": mm, "height": mm, "centered": bool}
create_cylinder: {"radius": mm, "height": mm}
extrude: {"sketch_description": "what to sketch", "depth": mm}
fuse: {"shapes": ["list of shape references"]}
cut: {"tool_shape": "description of cutting tool"}
add_holes: {
    "holes": [
        {"diameter": mm, "depth": mm or "through", "location": {"face": "selector", "position": [x, y] or "pattern"}}
    ]
}
add_fillet: {"radius": mm, "edges": "edge selector"}
add_chamfer: {"size": mm, "edges": "edge selector"}
transform: {"operation": "translate|rotate|mirror", "parameters": {...}}
"""


GENERATE_STEP_CODE_PROMPT = """You are an expert Build123d programmer.

Generate Python code for this build step:
{step_json}

Current state:
- Available variables: {available_vars}
- Previous code:
{previous_code}

RULES:
1. NO imports - Build123d classes (Box, Cylinder, Part, etc.) are already available
2. Use descriptive variable names
3. The result variable for this step should be: {result_var}
4. Add comments explaining the geometry
5. Handle edge cases (e.g., fillet too large)

BUILD123D REFERENCE:
- Create box: Box(length, width, height)
- Create cylinder: Cylinder(radius, height)
- Fuse: part1.fuse(part2)
- Cut: part1.cut(part2)
- Holes: Use Cylinder with Mode.SUBTRACT
- Fillet: fillet(edges, radius)
- Translate: part.moved(Location((x, y, z)))
- Rotate: part.rotate(Axis.Z, angle_degrees)
- Translate: shape.translate((x, y, z))
- Rotate: shape.rotate((0,0,0), (0,0,1), angle_degrees)

Generate ONLY the Python code for this step. No markdown, no explanations."""


VALIDATE_RESULT_PROMPT = """You are validating a CAD generation result.

Original user request: {original_request}

Intended result (from reasoning):
{intent_json}

Generated geometry properties:
- Bounding box: {bbox}
- Volume: {volume} mm³
- Number of faces: {face_count}
- Number of edges: {edge_count}
- Detected features: {detected_features}

Evaluate:
1. Does the bounding box match expected dimensions (within 5%)?
2. Is the volume reasonable for this type of part?
3. Are the expected features present?
4. Any obvious problems?

Respond with JSON:
{
    "is_valid": true/false,
    "dimension_check": {"passed": bool, "details": "..."},
    "feature_check": {"passed": bool, "details": "..."},
    "issues": ["list of problems found"],
    "suggestions": ["how to fix issues"],
    "confidence": 0.0 to 1.0
}
"""


# =============================================================================
# Reasoning Functions
# =============================================================================


async def understand_intent(description: str) -> PartIntent:
    """
    Deep understanding of what the user wants to build.

    This is the most important step - better understanding leads to
    better generation.
    """
    client = get_ai_client()

    logger.info(f"Understanding intent for: {description[:100]}...")

    messages = [
        {"role": "system", "content": UNDERSTAND_INTENT_PROMPT},
        {"role": "user", "content": description},
    ]

    content = await client.complete(messages, temperature=0.3)
    content = content.strip()

    # Parse JSON response
    try:
        # Clean up potential markdown
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)

        # Try to find JSON object in the response
        # Sometimes models add explanation text before/after the JSON
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            content = json_match.group(0)

        data = json.loads(content)

        # Extract and normalize dimensions - ensure all values are in mm
        raw_dims = data.get("overall_dimensions", {})
        normalized_dims = _normalize_dimensions_to_mm(raw_dims)

        # Also normalize material thickness if present
        material_thickness = data.get("material_thickness")
        if material_thickness and raw_dims.get("unit") in ("in", "inches", "inch"):
            material_thickness = material_thickness * 25.4

        # Build PartIntent from response
        intent = PartIntent(
            part_type=data.get("part_type", "custom"),
            primary_function=data.get("primary_function", "unknown"),
            overall_dimensions=normalized_dims,
            material_thickness=material_thickness,
            features=data.get("features", []),
            constraints=data.get("constraints", []),
            referenced_hardware=data.get("referenced_hardware", []),
            assumptions_made=data.get("assumptions_made", []),
            clarifications_needed=data.get("clarifications_needed", []),
            confidence=data.get("confidence", 0.5),
        )

        logger.info(
            f"Understood intent: {intent.part_type} for {intent.primary_function} (confidence: {intent.confidence})"
        )

        return intent

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse intent response: {e}")
        logger.debug(f"Raw response: {content[:500]}")

        # Return a basic intent
        return PartIntent(
            part_type="custom",
            primary_function="unknown",
            confidence=0.3,
            assumptions_made=["Could not fully parse user request"],
        )


async def create_build_plan(intent: PartIntent) -> BuildPlan:
    """
    Create a step-by-step plan for building the part.

    The plan breaks down the build into atomic, verifiable steps.
    """
    client = get_ai_client()

    intent_json = json.dumps(
        {
            "part_type": intent.part_type,
            "primary_function": intent.primary_function,
            "overall_dimensions": intent.overall_dimensions,
            "material_thickness": intent.material_thickness,
            "features": intent.features,
            "constraints": intent.constraints,
            "assumptions_made": intent.assumptions_made,
        },
        indent=2,
    )

    prompt = CREATE_BUILD_PLAN_PROMPT.format(intent_json=intent_json)

    logger.info(f"Creating build plan for {intent.part_type}...")

    messages = [{"role": "system", "content": prompt}]
    content = await client.complete(messages, temperature=0.3)
    content = content.strip()

    try:
        # Clean up potential markdown
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)

        # Try to find JSON object in the response
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            content = json_match.group(0)

        data = json.loads(content)

        steps: list[BuildStep] = []
        for step_data in data.get("steps", []):
            steps.append(
                BuildStep(
                    step_number=step_data.get("step_number", len(steps) + 1),
                    description=step_data.get("description", ""),
                    operation=step_data.get("operation", "unknown"),
                    parameters=step_data.get("parameters", {}),
                    depends_on=step_data.get("depends_on", []),
                    validation=step_data.get("validation"),
                )
            )

        plan = BuildPlan(
            intent=intent,
            steps=steps,
            estimated_complexity=data.get("estimated_complexity", "moderate"),
            warnings=data.get("warnings", []),
        )

        logger.info(
            f"Created build plan with {len(steps)} steps (complexity: {plan.estimated_complexity})"
        )

        return plan

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse build plan: {e}")
        logger.debug(f"Raw response: {content[:500]}")

        # Return a minimal plan
        return BuildPlan(
            intent=intent,
            estimated_complexity="unknown",
            warnings=["Could not create detailed build plan"],
        )


async def generate_step_code(
    step: BuildStep,
    available_vars: list[str],
    previous_code: str,
    result_var: str,
) -> str:
    """
    Generate Build123d code for a single build step.
    """
    client = get_ai_client()

    step_json = json.dumps(
        {
            "step_number": step.step_number,
            "description": step.description,
            "operation": step.operation,
            "parameters": step.parameters,
            "validation": step.validation,
        },
        indent=2,
    )

    prompt = GENERATE_STEP_CODE_PROMPT.format(
        step_json=step_json,
        available_vars=", ".join(available_vars) if available_vars else "None",
        previous_code=previous_code if previous_code else "# Starting fresh",
        result_var=result_var,
    )

    messages = [{"role": "system", "content": prompt}]
    code = await client.complete(messages, temperature=0.2)
    code = code.strip()

    # Clean up markdown if present
    if code.startswith("```"):
        code = re.sub(r"^```(?:python)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)

    return code


async def validate_result(
    _original_request: str,
    intent: PartIntent,
    shape: Any,  # build123d.Part
) -> dict[str, Any]:
    """
    Validate that the generated result matches the intent.
    """

    # Extract geometry properties
    try:
        bb = shape.bounding_box()
        volume = shape.volume

        faces = shape.faces()
        edges = shape.edges()

        # Detect features (simplified for Build123d)
        detected_features: list[str] = []
        # Feature detection is more complex in Build123d
        # Would need to analyze face/edge geometry types

        bbox = {
            "x": round(bb.max.X - bb.min.X, 2),
            "y": round(bb.max.Y - bb.min.Y, 2),
            "z": round(bb.max.Z - bb.min.Z, 2),
        }

    except Exception as e:
        logger.error(f"Failed to analyze shape: {e}")
        return {
            "is_valid": False,
            "issues": [f"Could not analyze shape: {e}"],
            "confidence": 0.0,
        }

    # For now, do basic validation without AI call
    # (AI validation can be added for complex cases)

    issues = []

    # Check dimensions if specified
    dims = intent.overall_dimensions
    if dims:
        expected_length = dims.get("length")
        expected_width = dims.get("width")
        expected_height = dims.get("height")

        tolerance = 0.05  # 5% tolerance

        if expected_length and abs(bbox["x"] - expected_length) / expected_length > tolerance:
            issues.append(f"Length mismatch: expected {expected_length}mm, got {bbox['x']}mm")

        if expected_width and abs(bbox["y"] - expected_width) / expected_width > tolerance:
            issues.append(f"Width mismatch: expected {expected_width}mm, got {bbox['y']}mm")

        if expected_height and abs(bbox["z"] - expected_height) / expected_height > tolerance:
            issues.append(f"Height mismatch: expected {expected_height}mm, got {bbox['z']}mm")

    # Check for expected features
    expected_holes = sum(1 for f in intent.features if f.get("type") == "hole")
    detected_holes = detected_features.count("hole") // 2  # Each hole has 2 circular edges

    if expected_holes > 0 and detected_holes < expected_holes:
        issues.append(f"Missing holes: expected {expected_holes}, found {detected_holes}")

    return {
        "is_valid": len(issues) == 0,
        "bbox": bbox,
        "volume": round(volume, 2),
        "face_count": len(faces),
        "edge_count": len(edges),
        "detected_features": list(set(detected_features)),
        "issues": issues,
        "confidence": 0.9 if len(issues) == 0 else 0.5,
    }


# =============================================================================
# Main Reasoning Pipeline
# =============================================================================


async def reason_and_plan(description: str) -> tuple[PartIntent, BuildPlan]:
    """
    Full reasoning pipeline: understand intent and create build plan.

    Returns:
        Tuple of (intent, plan) for use by the generator.
    """
    # Step 1: Deep understanding (most important)
    intent = await understand_intent(description)

    # Step 2: Create build plan (optional - may fail with simpler AI models)
    try:
        plan = await create_build_plan(intent)
    except Exception as e:
        logger.warning(f"Build plan creation failed: {e}, using simple plan")
        plan = BuildPlan(
            intent=intent,
            estimated_complexity="moderate",
            warnings=[],
        )

    return intent, plan
