"""
AI-powered Build123d code generation.

Uses an iterative, multi-pass approach to build up complex geometry:
1. First pass: Generate base geometry (shape primitives, unions)
2. Second pass: Add holes, cuts, pockets
3. Third pass: Add fillets, chamfers, and finishing features

Each pass validates and retries if needed before moving on.
"""

from __future__ import annotations

import ast
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

# Build123d imports
from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    Cone,
    Cylinder,
    Hole,
    Location,
    Locations,
    Mode,
    Part,
    Plane,
    Sphere,
    add,
    chamfer,
    extrude,
    fillet,
)

from app.ai.client import get_ai_client
from app.ai.exceptions import AIValidationError

logger = logging.getLogger(__name__)


# =============================================================================
# Intent Detection Prompt
# =============================================================================

INTENT_DETECTION_PROMPT = """Analyze this part description and break it down into build steps.

Respond with a JSON object containing:
- base_shape: description of the primary geometry (box, cylinder, sphere, L-bracket, etc.)
- holes: list of hole descriptions if any
- fillets: list of fillet/chamfer descriptions if any
- other_features: list of other features (ribs, bosses, pockets, etc.)

Example input: "Make a cylinder 2 inches in diameter and 4 inches tall with a 10mm center hole"

Example output:
{
  "base_shape": "cylinder 2 inches diameter (50.8mm), 4 inches tall (101.6mm)",
  "holes": ["10mm diameter center hole through the cylinder"],
  "fillets": [],
  "other_features": []
}

Example input: "Create an L-bracket 50mm x 50mm x 3mm thick with 4 corner holes 5mm diameter on each flange, 10mm from edges, and 5mm fillets on the outer corners"

Example output:
{
  "base_shape": "L-bracket/angle bracket with 50mm legs, 50mm wide, 3mm thick",
  "holes": ["4 holes per flange (8 total), 5mm diameter, positioned 10mm from edges in 2x2 grid pattern on each flange"],
  "fillets": ["5mm fillets on outer corners of each rectangular flange"],
  "other_features": []
}

IMPORTANT:
- For cylinders: Extract diameter and height, note if hollow or solid
- For L-brackets: "4 corner holes" typically means 4 holes on EACH flange (8 total)
- Always convert units to mm in parentheses: "2 inches (50.8mm)"

Only output the JSON. No markdown."""


# =============================================================================
# Pass-specific prompts
# =============================================================================

BASE_SHAPE_PROMPT = """Generate CadQuery code for the BASE GEOMETRY only.
Do NOT add holes, fillets, chamfers, or other features yet - just the primary solid shape.

RULES:
1. NO imports - cq is already available
2. Last line must be: result = <variable>
3. Use simple primitives: box(), cylinder(), sphere()
4. For unions, use .union()

=== CYLINDER ===
CadQuery cylinder() takes (height, radius) - NOT diameter!
For a cylinder 2 inches diameter (50.8mm) and 4 inches tall (101.6mm):
# diameter = 50.8mm, so radius = 25.4mm
# height = 101.6mm
result = cq.Workplane("XY").cylinder(101.6, 25.4)

For a 50mm diameter, 100mm tall cylinder:
result = cq.Workplane("XY").cylinder(100, 25)  # height=100, radius=25

=== SIMPLE BOX ===
For a box 100mm long, 50mm wide, 30mm tall:
result = cq.Workplane("XY").box(100, 50, 30)

=== SPHERE ===
For a 60mm diameter sphere:
result = cq.Workplane("XY").sphere(30)  # radius = diameter/2

=== L-BRACKET / ANGLE BRACKET ===
An L-bracket has two perpendicular flanges meeting at a corner.
For a 50mm x 50mm x 3mm thick L-bracket (both flanges same size):

# Horizontal flange: 50mm long, 50mm wide, 3mm thick
h = cq.Workplane("XY").box(50, 50, 3).translate((25, 0, 1.5))
# Vertical flange: 3mm thick, 50mm wide, 50mm tall
v = cq.Workplane("XY").box(3, 50, 50).translate((1.5, 0, 25))
result = h.union(v)

UNIT CONVERSIONS (convert to mm before using):
- 1 inch = 25.4 mm
- 1 cm = 10 mm

Output ONLY the Python code. No markdown. No explanations."""


ADD_HOLES_PROMPT = """You have an existing shape stored in `base_shape`.
Add holes to it based on the description.

The variable `base_shape` is already defined as a CadQuery Workplane with the base geometry.

RULES:
1. NO imports - cq is already available
2. Start from `base_shape`, not from scratch
3. Use .faces().workplane().hole(diameter) for through holes
4. Last line must be: result = <variable>
5. Assign intermediate results to variables

=== CYLINDER WITH CENTER THROUGH HOLE ===
# For a cylinder, select the top circular face (">Z") and add a center hole
# hole() takes diameter, not radius
# For a 10mm diameter hole:
result = base_shape.faces(">Z").workplane().hole(10)

# For a 12.7mm (1/2 inch) diameter hole:
result = base_shape.faces(">Z").workplane().hole(12.7)

=== BOX WITH CENTER HOLE ===
result = base_shape.faces(">Z").workplane().hole(10)

=== MULTIPLE HOLES IN PATTERN ===
# For multiple holes, use pushPoints with coordinates
result = base_shape.faces(">Z").workplane().pushPoints([
    (10, 10), (10, -10), (-10, 10), (-10, -10)
]).hole(5)

=== L-BRACKET HOLES ===
For a 50mm x 50mm flange with 5mm diameter holes, 10mm from edges:
hole_offset = 10
shape = base_shape.faces(">Z").workplane()
shape = shape.pushPoints([
    (hole_offset, hole_offset), (hole_offset, -hole_offset),
    (40, hole_offset), (40, -hole_offset)
]).hole(5)
result = shape

UNIT CONVERSION: 1 inch = 25.4mm, so 1/2 inch = 12.7mm

Output ONLY the Python code. No markdown. No explanations."""


ADD_FILLETS_PROMPT = """You have an existing shape stored in `base_shape`.
Add fillets or chamfers based on the description.

RULES:
1. Use `base_shape` variable directly
2. Write exactly ONE line of code
3. Last line must be: result = base_shape.edges("SELECTOR").fillet(RADIUS)

VALID SELECTORS:
"|Z" = vertical edges
"|X" = edges parallel to X
"|Y" = edges parallel to Y

EXAMPLES:
result = base_shape.edges("|Z").fillet(1)
result = base_shape.edges("|X").fillet(0.5)
result = base_shape.edges("|Y").chamfer(1)

IMPORTANT:
- Use fillet radius of 1mm or less for complex shapes
- Write only ONE line of code
- Do NOT chain multiple .edges() calls

Output ONLY one line of Python code."""


ADD_FEATURES_PROMPT = """You have an existing shape stored in `base_shape`.
Add the specified features to it.

The variable `base_shape` is already defined as a CadQuery Workplane.

RULES:
1. NO imports - cq is already available
2. Start from `base_shape`, not from scratch
3. Use .cut() for subtractive features, .union() for additive features
4. Last line must be: result = <variable>

EXAMPLE - Adding a boss:
boss = cq.Workplane("XY").transformed(offset=(0, 0, 5)).cylinder(10, 8)
result = base_shape.union(boss)

EXAMPLE - Adding a pocket:
pocket = cq.Workplane("XY").transformed(offset=(0, 0, 3)).box(20, 20, 10)
result = base_shape.cut(pocket)

Output ONLY the Python code. No markdown. No explanations."""


# =============================================================================
# Modification Context Prompt
# =============================================================================

MODIFICATION_CONTEXT_PROMPT = """You are modifying an existing CAD part. The user has an existing part and wants to change it.

IMPORTANT: Start with the EXACT original code below and add ONLY the modification requested.
Do NOT recreate the part from scratch - use the original code as your starting point.

=== ORIGINAL CADQUERY CODE (use this as your base) ===
{original_code}
=== END ORIGINAL CODE ===

Part description: {original_description}
Existing dimensions: {existing_dimensions}

User's modification request:
{modification_request}

RULES:
1. NO imports - cq is already available
2. Start with the original code above (copy it exactly, then add modifications)
3. Add the modification by continuing the CadQuery chain or applying operations to the existing shape
4. Last line must be: result = <variable_name>
5. Apply ONLY the modification the user requested

CADQUERY HOLE DRILLING GUIDE:
- For holes in a HORIZONTAL surface (XY plane): use .faces(">Z") or .faces("<Z")
- For holes in a VERTICAL surface facing Y: use .faces(">Y") or .faces("<Y")
- For holes in a VERTICAL surface facing X: use .faces(">X") or .faces("<X")
- The .hole(diameter) drills PERPENDICULAR to the selected face
- For an L-bracket: horizontal leg uses .faces(">Z"), vertical leg uses .faces(">Y") or .faces("<Y")

EXAMPLE - Adding holes to both legs of an L-bracket:
```
# Holes in horizontal leg (top face)
result = result.faces(">Z").workplane().pushPoints([(x1, y1), (x2, y2)]).hole(diameter)
# Holes in vertical leg (front/back face - NOT the side face)
result = result.faces("<Y").workplane().pushPoints([(x1, z1), (x2, z2)]).hole(diameter)
```

Output ONLY the Python code. No markdown. No explanations."""


@dataclass
class CodeGenerationResult:
    """Result of AI code generation."""

    code: str
    shape: Part | None = None
    execution_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    error: str | None = None
    adjustments: list[str] = field(default_factory=list)  # User-facing messages about changes made

    @property
    def is_successful(self) -> bool:
        return self.shape is not None and self.error is None


def sanitize_code(code: str) -> str:
    """
    Sanitize generated code to ensure it's safe to execute.

    - Removes markdown code blocks
    - Removes build123d/cadquery import statements (we provide symbols in globals)
    - Removes dangerous imports
    - Ensures result variable exists
    """
    # Remove markdown code blocks
    code = re.sub(r"^```python\s*", "", code, flags=re.MULTILINE)
    code = re.sub(r"^```\s*$", "", code, flags=re.MULTILINE)
    code = code.strip()

    # Remove build123d imports (we provide symbols in globals)
    code = re.sub(
        r"^from build123d import.*$", "# from build123d (provided)", code, flags=re.MULTILINE
    )
    code = re.sub(
        r"^import build123d.*$", "# import build123d (provided)", code, flags=re.MULTILINE
    )

    # Also remove legacy cadquery imports
    code = re.sub(r"^import cadquery.*$", "# import cadquery (legacy)", code, flags=re.MULTILINE)
    code = re.sub(r"^from cadquery import.*$", "# from cadquery (legacy)", code, flags=re.MULTILINE)
    code = re.sub(r"^import cq.*$", "# import cq (legacy)", code, flags=re.MULTILINE)

    # Fix common CadQuery method naming issues (snake_case -> camelCase)
    code = re.sub(r"\.push_points\(", ".pushPoints(", code)
    code = re.sub(r"\.fillet\(0\)", "", code)  # Remove invalid .fillet(0) calls

    # Check for dangerous patterns
    dangerous_patterns = [
        r"\bimport\s+os\b",
        r"\bimport\s+sys\b",
        r"\bimport\s+subprocess\b",
        r"\bimport\s+shutil\b",
        r"\b__import__\b",
        r"\beval\b",
        r"\bexec\b",
        r"\bopen\s*\(",
        r"\bfile\s*\(",
        r"\bos\.",
        r"\bsys\.",
        r"\bsubprocess\.",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            raise AIValidationError(f"Generated code contains forbidden pattern: {pattern}")

    # Ensure code assigns to result
    if "result" not in code:
        raise AIValidationError("Generated code must assign to 'result' variable")

    return code


def execute_cadquery_code(code: str, base_shape: Part | None = None) -> Part:
    """
    Safely execute Build123d code and return the result.

    Note: Function name kept for backward compatibility, but now executes Build123d code.

    Args:
        code: Python code that creates a Build123d Part
        base_shape: Optional existing shape to build upon (available as 'base_shape' variable)

    Returns:
        The Build123d Part result

    Raises:
        AIValidationError: If code is invalid or execution fails
    """
    # Sanitize first
    code = sanitize_code(code)

    logger.debug(f"Executing sanitized code:\n{code}")

    # Create restricted execution environment with Build123d symbols
    allowed_globals = {
        # Build123d core
        "BuildPart": BuildPart,
        "BuildSketch": __import__("build123d").BuildSketch,
        "Part": Part,
        "Plane": Plane,
        "Mode": Mode,
        "Align": Align,
        "Axis": Axis,
        # Shapes
        "Box": Box,
        "Cylinder": Cylinder,
        "Sphere": Sphere,
        "Cone": Cone,
        "Hole": Hole,
        # Positioning
        "Location": Location,
        "Locations": Locations,
        # Operations
        "add": add,
        "fillet": fillet,
        "chamfer": chamfer,
        "extrude": extrude,
        # Utils
        "math": __import__("math"),
    }

    local_vars: dict[str, Any] = {}

    # If we have a base shape, make it available
    if base_shape is not None:
        local_vars["base_shape"] = base_shape

    try:
        # Parse to check syntax
        ast.parse(code)

        # Execute
        exec(code, allowed_globals, local_vars)  # nosec B102 - intentional exec for AI-generated CAD code in sandboxed namespace

        if "result" not in local_vars:
            raise AIValidationError("Code did not create 'result' variable")

        result = local_vars["result"]

        # Check for Build123d Part
        if not hasattr(result, "wrapped"):
            raise AIValidationError(f"Result is not a Build123d Part: {type(result)}")

        # Ensure there's valid geometry
        try:
            bbox = result.bounding_box()
            if bbox is None:
                raise AIValidationError("Result has no valid geometry")
        except Exception as e:
            raise AIValidationError(f"Result has no valid geometry: {e}")

        return result  # type: ignore[no-any-return]

    except SyntaxError as e:
        logger.error(f"Syntax error in generated code: {e}")
        raise AIValidationError(f"Syntax error in generated code: {e}")
    except AIValidationError:
        raise
    except Exception as e:
        logger.error(f"Error executing generated code: {e}", exc_info=True)
        raise AIValidationError(f"Error executing generated code: {type(e).__name__}: {e}")


def _apply_fillet_with_fallback(
    shape: Part, edge_selector: str, requested_radius: float, operation: str = "fillet"
) -> tuple[Part | None, float | None, str | None]:
    """
    Try to apply a fillet/chamfer, automatically reducing size if too large.
    Skips operations on complex geometry to prevent hanging.

    Args:
        shape: The shape to fillet
        edge_selector: Edge selector (not used in Build123d the same way)
        requested_radius: The requested fillet radius
        operation: "fillet" or "chamfer"

    Returns:
        Tuple of (result_shape, actual_radius_used, adjustment_message)
        If all attempts fail, returns (None, None, error_message)
    """
    # Try the requested radius first, then progressively smaller
    radii_to_try = [requested_radius]

    # Add fallback radii (75%, 50%, 25%, 10% of requested)
    for factor in [0.75, 0.5, 0.25, 0.1]:
        fallback = round(requested_radius * factor, 2)
        if fallback >= 0.1:  # Minimum useful fillet
            radii_to_try.append(fallback)

    # Also try some absolute minimums
    for min_radius in [0.5, 0.25, 0.1]:
        if min_radius not in radii_to_try and min_radius < requested_radius:
            radii_to_try.append(min_radius)

    radii_to_try = sorted(set(radii_to_try), reverse=True)

    logger.info(f"Trying {operation} on {edge_selector} with radii: {radii_to_try}")

    last_error = None
    for radius in radii_to_try:
        try:
            edges = shape.edges(edge_selector)  # type: ignore[call-arg]

            # Log how many edges we're trying to fillet
            edge_count = edges.size()  # type: ignore[attr-defined]
            logger.info(
                f"Attempting {operation}({radius}) on {edge_count} edges matching {edge_selector}"
            )

            # Skip if too many edges - OpenCASCADE hangs on complex filleting
            # Even 10+ edges with holes can hang indefinitely
            if edge_count > 8:
                last_error = f"Too many edges ({edge_count}) - skipping to avoid hang"
                logger.warning(
                    f"Skipping fillet on {edge_selector}: {edge_count} edges is too many for reliable filleting"
                )
                break

            # Skip small radii on even moderate edge counts
            if edge_count > 4 and radius < 0.3:
                last_error = f"Too many edges ({edge_count}) with small radius ({radius})"
                logger.info("Skipping small fillet on complex geometry")
                continue

            result = edges.fillet(radius) if operation == "fillet" else edges.chamfer(radius)  # type: ignore[attr-defined]

            # Validate the result
            val = result.val()
            if hasattr(val, "ShapeType") and val.ShapeType() in ["Solid", "Compound", "CompSolid"]:
                if radius < requested_radius:
                    adjustment_msg = (
                        f"Adjusted {operation} from {requested_radius}mm to {radius}mm "
                        f"(requested size was too large for the geometry)"
                    )
                    logger.info(adjustment_msg)
                    return result, radius, adjustment_msg
                return result, radius, None

        except Exception as e:
            last_error = str(e)
            logger.debug(f"Fillet with selector {edge_selector} radius {radius} failed: {e}")
            continue

    # All attempts failed
    logger.warning(f"All {operation} attempts failed for selector {edge_selector}: {last_error}")
    return (
        None,
        None,
        f"Could not apply {operation} - geometry may be too complex. Error: {last_error}",
    )


def _extract_fillet_params_from_code(code: str) -> tuple[str | None, float | None, str]:
    """
    Extract edge selector and radius from generated fillet code.

    Returns:
        Tuple of (edge_selector, radius, operation)
    """
    if not code:
        return None, None, "fillet"

    # Match patterns like: .edges("|Z").fillet(2) or .edges(">X").chamfer(1.5)
    fillet_match = re.search(r'\.edges\(["\']([^"\']+)["\']\)\.fillet\(([0-9.]+)\)', code)
    if fillet_match:
        return fillet_match.group(1), float(fillet_match.group(2)), "fillet"

    chamfer_match = re.search(r'\.edges\(["\']([^"\']+)["\']\)\.chamfer\(([0-9.]+)\)', code)
    if chamfer_match:
        return chamfer_match.group(1), float(chamfer_match.group(2)), "chamfer"

    return None, None, "fillet"


def _extract_radius_from_description(description: str) -> float:
    """Extract a fillet/chamfer radius from a text description."""
    # Look for patterns like "5mm fillet", "3 mm chamfer", "2mm radius", "2mm rounded"
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:fillet|chamfer|radius|rounded|round|edge)",
        description,
        re.IGNORECASE,
    )
    if match:
        return float(match.group(1))
    # Also try reverse: "fillet 5mm", "rounded 2mm"
    match = re.search(
        r"(?:fillet|chamfer|radius|rounded|round)\s*(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:mm)?",
        description,
        re.IGNORECASE,
    )
    if match:
        return float(match.group(1))
    # Just look for any number followed by mm
    match = re.search(r"(\d+(?:\.\d+)?)\s*mm", description, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 1.0  # Default


async def _generate_single_pass(
    client: Any,
    system_prompt: str,
    user_prompt: str,
    base_shape: Part | None = None,
    max_retries: int = 2,
) -> tuple[Part | None, str, float, float, str | None]:
    """
    Generate and execute code for a single pass.

    Returns:
        Tuple of (shape, code, gen_time_ms, exec_time_ms, error)
    """
    last_error = None
    last_code = ""
    total_gen_time = 0.0
    total_exec_time = 0.0

    for attempt in range(max_retries + 1):
        gen_start = time.monotonic()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # If retrying, add error context
        if last_error and attempt > 0:
            messages.append({"role": "assistant", "content": f"```python\n{last_code}\n```"})
            messages.append(
                {
                    "role": "user",
                    "content": f"Error: {last_error}\n\nFix the code. Avoid the same mistake. Output only code.",
                }
            )

        try:
            code = await client.complete(messages, temperature=0.2 + (attempt * 0.1))
            gen_time = (time.monotonic() - gen_start) * 1000
            total_gen_time += gen_time
            logger.info(f"Pass generated code (attempt {attempt + 1}):\n{code[:300]}...")

        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return None, "", total_gen_time, 0.0, f"AI generation failed: {e}"

        # Execute
        exec_start = time.monotonic()
        try:
            shape = execute_cadquery_code(code, base_shape)
            exec_time = (time.monotonic() - exec_start) * 1000
            total_exec_time += exec_time
            logger.info(f"Pass execution successful in {exec_time:.0f}ms")
            return shape, code, total_gen_time, total_exec_time, None

        except AIValidationError as e:
            last_error = str(e)
            last_code = code
            total_exec_time += (time.monotonic() - exec_start) * 1000
            logger.warning(f"Pass failed (attempt {attempt + 1}/{max_retries + 1}): {e}")

    return None, last_code, total_gen_time, total_exec_time, last_error


async def _detect_intent(client: Any, description: str) -> dict[Any, Any]:
    """
    Use AI to break down the part description into build steps.
    """
    import json

    messages = [
        {"role": "system", "content": INTENT_DETECTION_PROMPT},
        {"role": "user", "content": description},
    ]

    try:
        response = await client.complete(messages, temperature=0.1)
        # Clean up response
        response = response.strip()
        if response.startswith("```"):
            response = re.sub(r"^```json?\s*", "", response)
            response = re.sub(r"\s*```$", "", response)

        intent = json.loads(response)
        logger.info(f"Detected intent: {intent}")
        return intent  # type: ignore[no-any-return]
    except Exception as e:
        logger.warning(f"Intent detection failed: {e}, using fallback")
        return {"base_shape": description, "holes": [], "fillets": [], "other_features": []}


@dataclass
class BuildStep:
    """A single step in the iterative build process."""

    name: str
    prompt: str
    description: str
    required: bool = True


async def generate_cadquery_code(
    description: str,
    *,
    intent: Any = None,  # PartIntent from reasoning module
    _build_plan: Any = None,  # BuildPlan from reasoning module
) -> CodeGenerationResult:
    """
    Generate CadQuery code from a natural language description.

    Uses an iterative multi-pass approach:
    1. Detect intent and break down into steps (or use provided intent)
    2. Generate base geometry
    3. Add holes/cuts
    4. Add fillets/chamfers
    5. Add other features

    Each step validates and retries before proceeding.

    Args:
        description: Natural language description of the part
        intent: Optional pre-computed PartIntent from reasoning module
        build_plan: Optional pre-computed BuildPlan from reasoning module

    Returns:
        CodeGenerationResult with the generated code and shape
    """
    client = get_ai_client()
    total_gen_time = 0.0
    total_exec_time = 0.0
    all_code = []

    # Step 1: Detect intent (or use provided intent from reasoning)
    logger.info(f"Starting iterative generation for: {description[:100]}...")

    if intent and hasattr(intent, "part_type"):
        # Use structured intent from reasoning module
        detected_intent = {
            "base_shape": f"{intent.part_type}: {intent.primary_function}",
            "holes": [
                f.get("description", str(f)) for f in intent.features if f.get("type") == "hole"
            ],
            "fillets": [
                f.get("description", str(f))
                for f in intent.features
                if f.get("type") in ["fillet", "chamfer"]
            ],
            "other_features": [
                f.get("description", str(f))
                for f in intent.features
                if f.get("type") not in ["hole", "fillet", "chamfer"]
            ],
        }
        # Build detailed dimension description
        intent_dims = intent.overall_dimensions
        thickness = intent.material_thickness

        if intent_dims:
            # Format dimensions clearly for the AI
            dim_parts = []
            for k, v in intent_dims.items():
                if v and k != "unit":
                    dim_parts.append(f"{k}={v}mm")
            if thickness and "thickness" not in intent_dims:
                dim_parts.append(f"thickness={thickness}mm")

            dim_str = ", ".join(dim_parts)
            detected_intent["base_shape"] = f"{detected_intent['base_shape']} ({dim_str})"
            detected_intent["dimensions"] = intent_dims
            detected_intent["thickness"] = thickness

        logger.info(f"Using intent from reasoning: {detected_intent}")
    else:
        # Fall back to AI-based intent detection
        detected_intent = await _detect_intent(client, description)

    # Step 2: Generate base shape (required)
    logger.info("Pass 1: Generating base geometry...")

    # Build more explicit base prompt with dimension context
    base_info_raw = detected_intent.get("base_shape", description)
    base_info = str(base_info_raw) if base_info_raw else str(description)
    # Ensure dims is always a dict for attribute access
    dims_raw: Any = detected_intent.get("dimensions", {})
    dims: dict[str, Any] = dims_raw if isinstance(dims_raw, dict) else {}
    thickness = detected_intent.get("thickness")

    # Add explicit instruction based on detected shape type
    base_info_lower = base_info.lower()

    if any(term in base_info_lower for term in ["cylinder", "cylindrical", "tube", "pipe", "rod"]):
        # Handle cylinder shapes explicitly
        diameter = dims.get("diameter", 50)
        radius = dims.get("radius", diameter / 2 if diameter else 25)
        height = dims.get("height", 100)

        base_prompt = (
            f"Create a CYLINDER with:\n"
            f"- Diameter: {diameter}mm (radius: {radius}mm)\n"
            f"- Height: {height}mm\n"
            f"Use: result = cq.Workplane('XY').cylinder({height}, {radius})\n"
            f"Remember: cylinder(height, radius) - height first, then radius!"
        )
    elif any(term in base_info_lower for term in ["sphere", "ball", "spherical"]):
        # Handle sphere shapes explicitly
        diameter = dims.get("diameter", 50)
        radius = dims.get("radius", diameter / 2 if diameter else 25)

        base_prompt = (
            f"Create a SPHERE with:\n"
            f"- Diameter: {diameter}mm (radius: {radius}mm)\n"
            f"Use: result = cq.Workplane('XY').sphere({radius})"
        )
    elif any(term in base_info_lower for term in ["bracket", "l-bracket", "angle"]):
        flange_len = dims.get("flange_length", 50)
        flange_width = dims.get("flange_width", flange_len)
        mat_thickness = thickness or dims.get("thickness", 3)
        base_prompt = (
            f"Create an L-bracket/angle bracket with:\n"
            f"- Flange length: {flange_len}mm (both flanges)\n"
            f"- Flange width: {flange_width}mm\n"
            f"- Material thickness: {mat_thickness}mm\n"
            f"Use the L-bracket pattern from the examples."
        )
    elif any(term in base_info_lower for term in ["box", "cube", "rectangular", "block"]):
        # Handle box shapes explicitly
        length = dims.get("length", 100)
        width = dims.get("width", 50)
        height = dims.get("height", 30)

        base_prompt = (
            f"Create a BOX with:\n"
            f"- Length: {length}mm\n"
            f"- Width: {width}mm\n"
            f"- Height: {height}mm\n"
            f"Use: result = cq.Workplane('XY').box({length}, {width}, {height})"
        )
    else:
        base_prompt = f"Create the base shape: {base_info}"

    shape, code, gen_t, exec_t, error = await _generate_single_pass(
        client, BASE_SHAPE_PROMPT, base_prompt, None, max_retries=3
    )
    total_gen_time += gen_t
    total_exec_time += exec_t

    if error or shape is None:
        return CodeGenerationResult(
            code=code,
            error=f"Failed to generate base shape: {error}",
            generation_time_ms=total_gen_time,
            execution_time_ms=total_exec_time,
        )

    all_code.append(f"# === Base Shape ===\n{code}")
    current_shape = shape
    adjustments = []  # Track adjustments made for user feedback

    # Step 3: Add holes (if any)
    holes = detected_intent.get("holes", [])
    if holes:
        logger.info(f"Pass 2: Adding holes... ({len(holes)} hole specifications)")
        holes_desc = "; ".join(holes) if isinstance(holes, list) else str(holes)
        holes_prompt = f"Add these holes to the shape: {holes_desc}"

        shape, code, gen_t, exec_t, error = await _generate_single_pass(
            client, ADD_HOLES_PROMPT, holes_prompt, current_shape, max_retries=3
        )
        total_gen_time += gen_t
        total_exec_time += exec_t

        if shape is not None:
            all_code.append(f"# === Holes ===\n{code}")
            current_shape = shape
        else:
            logger.warning(f"Holes pass failed, continuing without: {error}")

    # Step 4: Add fillets/chamfers (if any) - direct approach (AI generates too much garbage for fillets)
    fillets = detected_intent.get("fillets", [])
    if fillets:
        logger.info(f"Pass 3: Adding fillets/chamfers... ({len(fillets)} specifications)")
        fillets_desc = "; ".join(fillets) if isinstance(fillets, list) else str(fillets)

        # Extract the requested radius from the description
        requested_radius = _extract_radius_from_description(fillets_desc)
        logger.info(f"Extracted fillet radius: {requested_radius}mm from '{fillets_desc}'")

        # Skip AI code generation for fillets - just apply directly with fallback
        # The AI tends to generate invalid fillet code
        exec_start = time.monotonic()
        fillet_applied = False

        for selector in ["|Z", "|X", "|Y"]:
            result_shape, actual_radius, adjustment_msg = _apply_fillet_with_fallback(
                current_shape, selector, requested_radius, "fillet"
            )
            if result_shape is not None and actual_radius is not None:
                actual_code = f'result = base_shape.edges("{selector}").fillet({actual_radius})'
                all_code.append(f"# === Fillets ===\n{actual_code}")
                current_shape = result_shape

                if actual_radius < requested_radius:
                    adjustment_msg = (
                        f"Adjusted fillet from {requested_radius}mm to {actual_radius}mm on {selector} edges "
                        f"(requested size was too large for the geometry)"
                    )
                else:
                    adjustment_msg = f"Applied {actual_radius}mm fillet to {selector} edges"

                adjustments.append(adjustment_msg)
                logger.info(f"Fillet success: {adjustment_msg}")
                fillet_applied = True
                break

        total_exec_time += (time.monotonic() - exec_start) * 1000

        if not fillet_applied:
            adjustments.append(
                "Could not apply fillet - the geometry is too complex for this feature. "
                "Consider simplifying the part or applying fillets in CAD software."
            )
            logger.warning(f"All fillet attempts failed for: {fillets_desc}")

    # Step 5: Add other features (if any)
    other_features = detected_intent.get("other_features", [])
    if other_features:
        logger.info(f"Pass 4: Adding other features... ({len(other_features)} specifications)")
        features_desc = (
            "; ".join(other_features) if isinstance(other_features, list) else str(other_features)
        )
        features_prompt = f"Add these features: {features_desc}"

        shape, code, gen_t, exec_t, error = await _generate_single_pass(
            client, ADD_FEATURES_PROMPT, features_prompt, current_shape, max_retries=3
        )
        total_gen_time += gen_t
        total_exec_time += exec_t

        if shape is not None:
            all_code.append(f"# === Other Features ===\n{code}")
            current_shape = shape
        else:
            logger.warning(f"Features pass failed, continuing without: {error}")

    # Combine all code
    combined_code = "\n\n".join(all_code)

    logger.info(
        f"Iterative generation complete: {len(all_code)} passes successful, {len(adjustments)} adjustments made"
    )

    return CodeGenerationResult(
        code=combined_code,
        shape=current_shape,
        generation_time_ms=total_gen_time,
        execution_time_ms=total_exec_time,
        adjustments=adjustments,
    )


async def generate_modification(
    original_description: str,
    modification_request: str,
    original_code: str | None = None,
    existing_dimensions: dict[str, float] | None = None,
    _existing_features: list[str] | None = None,
) -> CodeGenerationResult:
    """
    Generate CadQuery code that applies a modification to an existing part.

    This is used when a user requests changes to an already-generated part,
    such as "add a 10mm hole in the center" or "make it 20mm taller".

    Args:
        original_description: The original part description that was generated
        modification_request: The user's modification request
        original_code: The original CadQuery code that generated the part
        existing_dimensions: Dictionary of existing dimensions (e.g., {"length": 100, "width": 50})
        existing_features: List of existing features (e.g., ["3mm fillets on all edges"])

    Returns:
        CodeGenerationResult with the modified geometry
    """
    client = get_ai_client()

    logger.info(
        f"Generating modification: '{modification_request}' on '{original_description[:50]}...'"
    )
    logger.info(f"Original code provided: {bool(original_code)}")
    if original_code:
        logger.info(f"Original code length: {len(original_code)} chars")
        logger.info(f"Original code preview: {original_code[:200]}...")

    # Format existing dimensions for the prompt
    dims_str = "None specified"
    if existing_dimensions:
        dims_str = ", ".join([f"{k}: {v}mm" for k, v in existing_dimensions.items()])

    # If no original code provided, create a placeholder
    code_str = (
        original_code
        if original_code
        else "# Original code not available - recreate from dimensions"
    )

    # Build the modification prompt
    prompt = MODIFICATION_CONTEXT_PROMPT.format(
        original_description=original_description,
        original_code=code_str,
        existing_dimensions=dims_str,
        modification_request=modification_request,
    )

    messages = [
        {"role": "system", "content": prompt},
    ]

    gen_start = time.monotonic()

    try:
        code = await client.complete(messages, temperature=0.2)
        gen_time = (time.monotonic() - gen_start) * 1000

        logger.info(f"Modification code generated:\n{code[:500]}...")

        # Execute the code
        exec_start = time.monotonic()
        try:
            shape = execute_cadquery_code(code)
            exec_time = (time.monotonic() - exec_start) * 1000

            return CodeGenerationResult(
                code=code,
                shape=shape,
                generation_time_ms=gen_time,
                execution_time_ms=exec_time,
                adjustments=[f"Applied modification: {modification_request}"],
            )
        except AIValidationError as e:
            logger.error(f"Modification execution failed: {e}")
            return CodeGenerationResult(
                code=code,
                error=f"Failed to apply modification: {e}",
                generation_time_ms=gen_time,
                execution_time_ms=(time.monotonic() - exec_start) * 1000,
            )

    except Exception as e:
        logger.error(f"Modification generation failed: {e}")
        return CodeGenerationResult(
            code="",
            error=f"Failed to generate modification: {e}",
            generation_time_ms=(time.monotonic() - gen_start) * 1000,
        )
