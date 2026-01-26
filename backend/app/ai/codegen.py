"""
AI-powered CadQuery code generation.

Uses an iterative, multi-pass approach to build up complex geometry:
1. First pass: Generate base geometry (shape primitives, unions)
2. Second pass: Add holes, cuts, pockets
3. Third pass: Add fillets, chamfers, and finishing features

Each pass validates and retries if needed before moving on.
"""

from __future__ import annotations

import logging
import re
import ast
import time
from dataclasses import dataclass, field
from typing import Any

import cadquery as cq

from app.ai.client import get_ai_client
from app.ai.exceptions import AIParseError, AIValidationError

logger = logging.getLogger(__name__)


# =============================================================================
# Intent Detection Prompt
# =============================================================================

INTENT_DETECTION_PROMPT = """Analyze this part description and break it down into build steps.

Respond with a JSON object containing:
- base_shape: description of the primary geometry (box, cylinder, L-bracket, etc.)
- holes: list of hole descriptions if any
- fillets: list of fillet/chamfer descriptions if any
- other_features: list of other features (ribs, bosses, pockets, etc.)

Example input: "Create an L-bracket 50mm x 50mm x 3mm thick with 4 corner holes 5mm diameter on each flange, 10mm from edges, and 5mm fillets on the outer corners"

Example output:
{
  "base_shape": "L-bracket/angle bracket with 50mm legs, 50mm wide, 3mm thick",
  "holes": ["4 holes per flange (8 total), 5mm diameter, positioned 10mm from edges in 2x2 grid pattern on each flange"],
  "fillets": ["5mm fillets on outer corners of each rectangular flange"],
  "other_features": []
}

IMPORTANT for angle brackets / L-brackets:
- "4 corner holes" typically means 4 holes on EACH flange (8 total)
- Holes are usually in a 2x2 grid pattern near the corners
- "outer corners" means the 4 corners of each rectangular flange plate

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

=== L-BRACKET / ANGLE BRACKET ===
An L-bracket has two perpendicular flanges meeting at a corner.
For a 50mm x 50mm x 3mm thick L-bracket (both flanges same size):

# Horizontal flange: 50mm long, 50mm wide, 3mm thick
h = cq.Workplane("XY").box(50, 50, 3).translate((25, 0, 1.5))
# Vertical flange: 3mm thick, 50mm wide, 50mm tall
v = cq.Workplane("XY").box(3, 50, 50).translate((1.5, 0, 25))
result = h.union(v)

=== SIMPLE BOX ===
result = cq.Workplane("XY").box(100, 50, 10)

=== CYLINDER ===
result = cq.Workplane("XY").cylinder(50, 25)

Output ONLY the Python code. No markdown. No explanations."""


ADD_HOLES_PROMPT = """You have an existing shape stored in `base_shape`. 
Add holes to it based on the description.

The variable `base_shape` is already defined as a CadQuery Workplane with the base geometry.

RULES:
1. NO imports - cq is already available
2. Start from `base_shape`, not from scratch
3. Use .faces().workplane().pushPoints([...]).hole(diameter)
4. Last line must be: result = <variable>
5. Assign intermediate results to variables

=== L-BRACKET HOLES (4 holes per flange, 10mm from edges) ===
For a 50mm x 50mm flange with 5mm diameter holes, 10mm from edges:
- Holes at corners: (10, 10), (10, -10), (40, 10), (40, -10) relative to flange center

# Horizontal flange - top face
hole_offset = 10  # distance from edge
shape = base_shape.faces(">Z").workplane()
shape = shape.pushPoints([
    (hole_offset, hole_offset), (hole_offset, -hole_offset),
    (40, hole_offset), (40, -hole_offset)
]).hole(5)

# Vertical flange - front face
shape = shape.faces("<X").workplane()
result = shape.pushPoints([
    (hole_offset, hole_offset + 3), (hole_offset, 40 + 3),
    (-hole_offset, hole_offset + 3), (-hole_offset, 40 + 3)
]).hole(5)

=== SIMPLE CENTER HOLE ===
result = base_shape.faces(">Z").workplane().hole(10)

=== CYLINDER WITH CENTER THROUGH HOLE ===
# For a cylinder, select the top circular face and add a through hole
# The hole will go through the entire cylinder
result = base_shape.faces(">Z").workplane().hole(10)

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


@dataclass
class CodeGenerationResult:
    """Result of AI code generation."""
    
    code: str
    shape: cq.Workplane | None = None
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
    - Removes cadquery import statements (we provide cq in globals)
    - Removes dangerous imports
    - Ensures result variable exists
    """
    # Remove markdown code blocks
    code = re.sub(r'^```python\s*', '', code, flags=re.MULTILINE)
    code = re.sub(r'^```\s*$', '', code, flags=re.MULTILINE)
    code = code.strip()
    
    # Fix common AI mistakes
    # push_points -> pushPoints (CadQuery uses camelCase)
    code = re.sub(r'\.push_points\s*\(', '.pushPoints(', code)
    # Remove extra arguments to pushPoints (should only take list)
    code = re.sub(r'\.pushPoints\(\[([^\]]+)\]\s*,\s*\d+\)', '.pushPoints([\\1])', code)
    
    # Fix invalid fillet/chamfer calls
    # Remove .fillet(0) and .chamfer(0) as they are invalid
    code = re.sub(r'\.fillet\(0\)', '', code)
    code = re.sub(r'\.chamfer\(0\)', '', code)
    # Remove chained .union() calls on fillets - they don't work that way
    code = re.sub(r'\.fillet\(([0-9.]+)\)\.union\([^)]+\)', '.fillet(\\1)', code)
    code = re.sub(r'\.chamfer\(([0-9.]+)\)\.union\([^)]+\)', '.chamfer(\\1)', code)
    
    # Remove cadquery imports (we provide cq/cadquery in globals)
    code = re.sub(r'^import cadquery.*$', '# import cadquery (provided)', code, flags=re.MULTILINE)
    code = re.sub(r'^from cadquery import.*$', '# from cadquery (provided)', code, flags=re.MULTILINE)
    code = re.sub(r'^import cq.*$', '# import cq (provided)', code, flags=re.MULTILINE)
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'\bimport\s+os\b',
        r'\bimport\s+sys\b',
        r'\bimport\s+subprocess\b',
        r'\bimport\s+shutil\b',
        r'\b__import__\b',
        r'\beval\b',
        r'\bexec\b',
        r'\bopen\s*\(',
        r'\bfile\s*\(',
        r'\bos\.',
        r'\bsys\.',
        r'\bsubprocess\.',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            raise AIValidationError(f"Generated code contains forbidden pattern: {pattern}")
    
    # Ensure code assigns to result
    if 'result' not in code:
        raise AIValidationError("Generated code must assign to 'result' variable")
    
    return code


def execute_cadquery_code(code: str, base_shape: cq.Workplane | None = None) -> cq.Workplane:
    """
    Safely execute CadQuery code and return the result.
    
    Args:
        code: Python code that creates a CadQuery Workplane
        base_shape: Optional existing shape to build upon (available as 'base_shape' variable)
        
    Returns:
        The CadQuery Workplane result
        
    Raises:
        AIValidationError: If code is invalid or execution fails
    """
    # Sanitize first
    code = sanitize_code(code)
    
    logger.debug(f"Executing sanitized code:\n{code}")
    
    # Create restricted execution environment
    allowed_globals = {
        'cq': cq,
        'cadquery': cq,
        'math': __import__('math'),
    }
    
    local_vars: dict[str, Any] = {}
    
    # If we have a base shape, make it available
    if base_shape is not None:
        local_vars['base_shape'] = base_shape
    
    try:
        # Parse to check syntax
        ast.parse(code)
        
        # Execute
        exec(code, allowed_globals, local_vars)
        
        if 'result' not in local_vars:
            raise AIValidationError("Code did not create 'result' variable")
        
        result = local_vars['result']
        
        if not isinstance(result, cq.Workplane):
            raise AIValidationError(f"Result is not a CadQuery Workplane: {type(result)}")
        
        # Ensure there's at least one solid on the stack
        try:
            val = result.val()
            if not hasattr(val, 'ShapeType') or val.ShapeType() not in ['Solid', 'Compound', 'CompSolid']:
                raise AIValidationError(f"Result has no valid solid geometry: {type(val)}")
        except Exception as e:
            raise AIValidationError(f"Result has no valid geometry: {e}")
        
        return result
        
    except SyntaxError as e:
        logger.error(f"Syntax error in generated code: {e}")
        raise AIValidationError(f"Syntax error in generated code: {e}")
    except AIValidationError:
        raise
    except Exception as e:
        logger.error(f"Error executing generated code: {e}", exc_info=True)
        raise AIValidationError(f"Error executing generated code: {type(e).__name__}: {e}")


def _apply_fillet_with_fallback(
    shape: cq.Workplane,
    edge_selector: str,
    requested_radius: float,
    operation: str = "fillet"
) -> tuple[cq.Workplane | None, float | None, str | None]:
    """
    Try to apply a fillet/chamfer, automatically reducing size if too large.
    Skips operations on complex geometry to prevent hanging.
    
    Args:
        shape: The shape to fillet
        edge_selector: CadQuery edge selector like "|Z", ">X"
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
            edges = shape.edges(edge_selector)
            
            # Log how many edges we're trying to fillet
            edge_count = edges.size()
            logger.info(f"Attempting {operation}({radius}) on {edge_count} edges matching {edge_selector}")
            
            # Skip if too many edges - OpenCASCADE hangs on complex filleting
            # Even 10+ edges with holes can hang indefinitely
            if edge_count > 8:
                last_error = f"Too many edges ({edge_count}) - skipping to avoid hang"
                logger.warning(f"Skipping fillet on {edge_selector}: {edge_count} edges is too many for reliable filleting")
                break
            
            # Skip small radii on even moderate edge counts
            if edge_count > 4 and radius < 0.3:
                last_error = f"Too many edges ({edge_count}) with small radius ({radius})"
                logger.info(f"Skipping small fillet on complex geometry")
                continue
            
            if operation == "fillet":
                result = edges.fillet(radius)
            else:
                result = edges.chamfer(radius)
            
            # Validate the result
            val = result.val()
            if hasattr(val, 'ShapeType') and val.ShapeType() in ['Solid', 'Compound', 'CompSolid']:
                if radius < requested_radius:
                    adjustment_msg = (
                        f"Adjusted {operation} from {requested_radius}mm to {radius}mm "
                        f"(requested size was too large for the geometry)"
                    )
                    logger.info(adjustment_msg)
                    return result, radius, adjustment_msg
                else:
                    return result, radius, None
                    
        except Exception as e:
            last_error = str(e)
            logger.debug(f"Fillet with selector {edge_selector} radius {radius} failed: {e}")
            continue
    
    # All attempts failed
    logger.warning(f"All {operation} attempts failed for selector {edge_selector}: {last_error}")
    return None, None, f"Could not apply {operation} - geometry may be too complex. Error: {last_error}"


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
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:fillet|chamfer|radius|rounded|round|edge)', description, re.IGNORECASE)
    if match:
        return float(match.group(1))
    # Also try reverse: "fillet 5mm", "rounded 2mm"
    match = re.search(r'(?:fillet|chamfer|radius|rounded|round)\s*(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:mm)?', description, re.IGNORECASE)
    if match:
        return float(match.group(1))
    # Just look for any number followed by mm
    match = re.search(r'(\d+(?:\.\d+)?)\s*mm', description, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 1.0  # Default


async def _generate_single_pass(
    client,
    system_prompt: str,
    user_prompt: str,
    base_shape: cq.Workplane | None = None,
    max_retries: int = 2,
) -> tuple[cq.Workplane | None, str, float, float, str | None]:
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
            messages.append({
                "role": "user",
                "content": f"Error: {last_error}\n\nFix the code. Avoid the same mistake. Output only code."
            })
        
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


async def _detect_intent(client, description: str) -> dict:
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
            response = re.sub(r'^```json?\s*', '', response)
            response = re.sub(r'\s*```$', '', response)
        
        intent = json.loads(response)
        logger.info(f"Detected intent: {intent}")
        return intent
    except Exception as e:
        logger.warning(f"Intent detection failed: {e}, using fallback")
        return {
            "base_shape": description,
            "holes": [],
            "fillets": [],
            "other_features": []
        }


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
    intent=None,  # PartIntent from reasoning module
    build_plan=None,  # BuildPlan from reasoning module
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
    
    if intent and hasattr(intent, 'part_type'):
        # Use structured intent from reasoning module
        detected_intent = {
            "base_shape": f"{intent.part_type}: {intent.primary_function}",
            "holes": [f.get("description", str(f)) for f in intent.features if f.get("type") == "hole"],
            "fillets": [f.get("description", str(f)) for f in intent.features if f.get("type") in ["fillet", "chamfer"]],
            "other_features": [f.get("description", str(f)) for f in intent.features if f.get("type") not in ["hole", "fillet", "chamfer"]],
        }
        # Build detailed dimension description
        dims = intent.overall_dimensions
        thickness = intent.material_thickness
        
        if dims:
            # Format dimensions clearly for the AI
            dim_parts = []
            for k, v in dims.items():
                if v and k != "unit":
                    dim_parts.append(f"{k}={v}mm")
            if thickness and "thickness" not in dims:
                dim_parts.append(f"thickness={thickness}mm")
            
            dim_str = ", ".join(dim_parts)
            detected_intent["base_shape"] = f"{detected_intent['base_shape']} ({dim_str})"
            detected_intent["dimensions"] = dims
            detected_intent["thickness"] = thickness
        
        logger.info(f"Using intent from reasoning: {detected_intent}")
    else:
        # Fall back to AI-based intent detection
        detected_intent = await _detect_intent(client, description)
    
    # Step 2: Generate base shape (required)
    logger.info("Pass 1: Generating base geometry...")
    
    # Build more explicit base prompt with dimension context
    base_info = detected_intent.get('base_shape', description)
    dims = detected_intent.get('dimensions', {})
    thickness = detected_intent.get('thickness')
    
    # Add explicit instruction for bracket-type parts
    if any(term in base_info.lower() for term in ['bracket', 'l-bracket', 'angle']):
        flange_len = dims.get('flange_length', 50)
        flange_width = dims.get('flange_width', flange_len)
        mat_thickness = thickness or dims.get('thickness', 3)
        base_prompt = (
            f"Create an L-bracket/angle bracket with:\n"
            f"- Flange length: {flange_len}mm (both flanges)\n"
            f"- Flange width: {flange_width}mm\n"
            f"- Material thickness: {mat_thickness}mm\n"
            f"Use the L-bracket pattern from the examples."
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
    holes = detected_intent.get('holes', [])
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
    fillets = detected_intent.get('fillets', [])
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
            if result_shape is not None:
                actual_code = f"result = base_shape.edges(\"{selector}\").fillet({actual_radius})"
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
                f"Could not apply fillet - the geometry is too complex for this feature. "
                f"Consider simplifying the part or applying fillets in CAD software."
            )
            logger.warning(f"All fillet attempts failed for: {fillets_desc}")
    
    # Step 5: Add other features (if any)
    other_features = detected_intent.get('other_features', [])
    if other_features:
        logger.info(f"Pass 4: Adding other features... ({len(other_features)} specifications)")
        features_desc = "; ".join(other_features) if isinstance(other_features, list) else str(other_features)
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
    
    logger.info(f"Iterative generation complete: {len(all_code)} passes successful, {len(adjustments)} adjustments made")
    
    return CodeGenerationResult(
        code=combined_code,
        shape=current_shape,
        generation_time_ms=total_gen_time,
        execution_time_ms=total_exec_time,
        adjustments=adjustments,
    )
