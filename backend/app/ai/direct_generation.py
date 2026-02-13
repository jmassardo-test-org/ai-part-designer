"""
Direct AI-to-Build123d code generation.

This module takes a simpler, more AI-centric approach:
1. User describes what they want in natural language
2. AI directly generates Build123d code
3. Code is executed and validated
4. If errors, AI fixes the code

No templates. No pattern matching. Just AI understanding → code.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

# Import Build123d conditionally
try:
    from build123d import (
        Align,
        Axis,
        Box,
        BuildPart,
        BuildSketch,
        Circle,
        Cone,
        CounterBoreHole,
        CounterSinkHole,
        Cylinder,
        Hole,
        Location,
        Locations,
        Mode,
        Part,
        Plane,
        Rectangle,
        Sketch,
        Sphere,
        add,
        chamfer,
        export_step,
        export_stl,
        extrude,
        fillet,
    )

    BUILD123D_AVAILABLE = True
except ImportError:
    BUILD123D_AVAILABLE = False
    Part = Any  # type: ignore[assignment, misc]

from app.ai.client import get_ai_client
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Build123d Reference for AI
# =============================================================================

BUILD123D_REFERENCE = """
=== BUILD123D QUICK REFERENCE ===

Build123d uses a context manager pattern with BuildPart(), BuildSketch(), etc.
All operations happen inside these context managers.

COORDINATE SYSTEM:
- XY plane is horizontal (ground), Z is up
- By default, Box/Cylinder are centered at origin

ALIGN CONSTANTS (for positioning):
- Align.CENTER - centered on that axis
- Align.MIN - aligned to minimum (e.g., bottom for Z)
- Align.MAX - aligned to maximum (e.g., top for Z)

BASIC SHAPES (use inside BuildPart context):
- Box(length, width, height)  # XYZ dimensions, centered at origin
- Box(length, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN))  # bottom at Z=0
- Cylinder(radius, height)  # NOTE: radius first, then height!
- Sphere(radius)
- Cone(bottom_radius, top_radius, height)

BOOLEAN OPERATIONS:
- with BuildPart(mode=Mode.ADD):  # add geometry (default)
- with BuildPart(mode=Mode.SUBTRACT):  # cut/subtract geometry
- Use nested contexts for boolean operations

FACE SELECTION:
- part.faces().sort_by(Axis.Z)[-1]  # highest Z face (top)
- part.faces().sort_by(Axis.Z)[0]   # lowest Z face (bottom)
- part.faces().sort_by(Axis.X)[-1]  # highest X face (right)
- part.faces().sort_by(Axis.X)[0]   # lowest X face (left)

ADDING HOLES (inside BuildPart context):
- Hole(radius, depth)  # centered at current location
- CounterBoreHole(radius, counter_bore_radius, counter_bore_depth, depth)
- CounterSinkHole(radius, counter_sink_radius, depth)

POSITIONING:
- Location((x, y, z))  # position in 3D space
- with Locations([Location((x1, y1, z1)), Location((x2, y2, z2))]):  # multiple positions

FILLETS AND CHAMFERS:
- fillet(edges, radius)
- chamfer(edges, length)

=== L-BRACKET WITH HOLES (WORKING EXAMPLE) ===
# Creates an L-bracket with 2 holes in each leg
# leg_length=100mm, width=25mm, thickness=3mm

leg_length = 100
width = 25
thickness = 3
hole_diameter = 6

with BuildPart() as bracket:
    # Horizontal leg - centered, bottom at Z=0
    Box(leg_length, width, thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # Vertical leg - attached at left side, going up
    with Locations([Location((-(leg_length - thickness) / 2, 0, (leg_length + thickness) / 2))]):
        Box(thickness, width, leg_length)

    # Add 2 holes in horizontal leg (drilling from top, through thickness)
    with BuildPart(mode=Mode.SUBTRACT):
        with Locations([Location((-20, 0, thickness)), Location((20, 0, thickness))]):
            Cylinder(hole_diameter / 2, thickness * 2)

    # Add 2 holes in vertical leg (drilling from left side)
    left_x = -(leg_length - thickness) / 2 - thickness / 2
    with BuildPart(mode=Mode.SUBTRACT):
        with Locations([Location((left_x, 0, 30)), Location((left_x, 0, 70))]):
            Cylinder(hole_diameter / 2, thickness * 2, rotation=(0, 90, 0))

result = bracket.part

=== SIMPLE BOX EXAMPLE ===
with BuildPart() as box:
    Box(50, 30, 20)  # 50mm x 30mm x 20mm box centered at origin

result = box.part

=== CYLINDER WITH HOLE EXAMPLE ===
with BuildPart() as part:
    Cylinder(25, 50)  # radius=25mm, height=50mm

    # Center hole through the cylinder
    with BuildPart(mode=Mode.SUBTRACT):
        Cylinder(10, 50)  # subtract smaller cylinder for hole

result = part.part

=== HOLLOW BOX (ENCLOSURE) EXAMPLE ===
outer_width, outer_depth, outer_height = 100, 60, 40
wall_thickness = 3

with BuildPart() as enclosure:
    # Outer shell
    Box(outer_width, outer_depth, outer_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # Hollow out (subtract inner box, leaving bottom wall)
    with BuildPart(mode=Mode.SUBTRACT):
        with Locations([Location((0, 0, wall_thickness))]):
            Box(
                outer_width - 2 * wall_thickness,
                outer_depth - 2 * wall_thickness,
                outer_height,  # Goes through top
                align=(Align.CENTER, Align.CENTER, Align.MIN)
            )

result = enclosure.part

=== UNIT CONVERSIONS ===
1 inch = 25.4 mm
1 cm = 10 mm
"""


# =============================================================================
# Main Generation Prompt
# =============================================================================

DIRECT_GENERATION_PROMPT = """You are an expert Build123d programmer. Generate Build123d Python code for the 3D part described.

{build123d_reference}

=== USER'S REQUEST ===
{description}

=== RULES ===
1. NO imports - all Build123d classes are already available (BuildPart, Box, Cylinder, Sphere, etc.)
2. Use the context manager pattern: with BuildPart() as part: ...
3. The last line MUST be: result = <builder>.part
4. Use millimeters (convert from inches/cm if needed)
5. For Cylinder(): first argument is RADIUS, second is HEIGHT
6. Add helpful comments explaining each step
7. If dimensions aren't specified, use sensible defaults and note them in comments

=== OUTPUT ===
Generate ONLY the Python code. No markdown code blocks. No explanations before or after.
Just the raw Python code that creates the shape."""


DIRECT_MODIFICATION_PROMPT = """You are an expert Build123d programmer. Modify the existing Build123d code based on the user's request.

{build123d_reference}

=== ORIGINAL CODE ===
{original_code}

=== USER'S MODIFICATION REQUEST ===
{modification_request}

=== RULES ===
1. NO imports - all Build123d classes are already available
2. Start with the original code as your base
3. The last line MUST be: result = <builder>.part
4. Apply ONLY the modification requested
5. Keep all original geometry intact unless specifically asked to change it
6. Add comments explaining the modification

=== OUTPUT ===
Generate ONLY the Python code. No markdown code blocks. No explanations.
Include the complete code (original + modifications)."""


# =============================================================================
# Result Data Class
# =============================================================================


@dataclass
class DirectGenerationResult:
    """Result of direct AI code generation."""

    code: str
    shape: Part | None = None
    execution_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    error: str | None = None
    retry_count: int = 0

    @property
    def is_successful(self) -> bool:
        return self.shape is not None and self.error is None


# =============================================================================
# Code Execution
# =============================================================================


def sanitize_code(code: str) -> str:
    """Clean up AI-generated code for safe execution."""
    # Remove markdown code blocks
    code = re.sub(r"^```python\s*", "", code, flags=re.MULTILINE)
    code = re.sub(r"^```\s*$", "", code, flags=re.MULTILINE)
    code = code.strip()

    # Remove import statements (we provide all Build123d symbols)
    code = re.sub(r"^from build123d import.*$", "", code, flags=re.MULTILINE)
    code = re.sub(r"^import build123d.*$", "", code, flags=re.MULTILINE)
    # Also remove any cadquery imports in case AI still generates them
    code = re.sub(r"^import cadquery.*$", "", code, flags=re.MULTILINE)
    code = re.sub(r"^from cadquery import.*$", "", code, flags=re.MULTILINE)

    return code.strip()


def execute_build123d_code(code: str) -> Part:
    """Execute Build123d code and return the result Part."""
    if not BUILD123D_AVAILABLE:
        raise RuntimeError("Build123d is not available")

    code = sanitize_code(code)

    # Create execution namespace with all Build123d symbols available
    namespace = {
        # Core classes
        "BuildPart": BuildPart,
        "BuildSketch": BuildSketch,
        "Sketch": Sketch,
        "Part": Part,
        "Plane": Plane,
        # Shapes
        "Box": Box,
        "Cylinder": Cylinder,
        "Sphere": Sphere,
        "Cone": Cone,
        "Circle": Circle,
        "Rectangle": Rectangle,
        # Positioning
        "Location": Location,
        "Locations": Locations,
        "Align": Align,
        "Axis": Axis,
        "Mode": Mode,
        # Operations
        "add": add,
        "fillet": fillet,
        "chamfer": chamfer,
        "extrude": extrude,
        # Holes
        "Hole": Hole,
        "CounterBoreHole": CounterBoreHole,
        "CounterSinkHole": CounterSinkHole,
        # Export
        "export_step": export_step,
        "export_stl": export_stl,
    }

    # Execute the code
    exec(code, namespace)  # nosec B102 - intentional exec for AI-generated CAD code in sandboxed namespace

    # Get the result
    if "result" not in namespace:
        raise ValueError("Code did not define 'result' variable")

    result = namespace["result"]

    # Build123d Part objects
    if not hasattr(result, "wrapped"):
        raise ValueError(f"'result' is not a Build123d Part, got {type(result)}")

    return result  # type: ignore[return-value]


# =============================================================================
# Main Generation Function
# =============================================================================


async def generate_directly(
    description: str,
    max_retries: int = 2,
) -> DirectGenerationResult:
    """
    Generate Build123d code directly from natural language description.

    This bypasses all templates and pattern matching - just AI understanding.

    Args:
        description: Natural language description of the part
        max_retries: Number of retry attempts if code execution fails

    Returns:
        DirectGenerationResult with generated code and shape
    """
    client = get_ai_client()

    logger.info(
        "direct_generation_started",
        description_preview=description[:100],
        max_retries=max_retries,
    )

    prompt = DIRECT_GENERATION_PROMPT.format(
        build123d_reference=BUILD123D_REFERENCE,
        description=description,
    )

    messages = [
        {"role": "user", "content": prompt},
    ]

    gen_start = time.monotonic()
    retry_count = 0
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            # Generate code
            code = await client.complete(messages, temperature=0.1)
            gen_time = (time.monotonic() - gen_start) * 1000

            code = sanitize_code(code)
            logger.info(
                "code_generated",
                attempt=attempt + 1,
                code_length=len(code),
                generation_time_ms=round(gen_time, 1),
            )

            # Execute code
            exec_start = time.monotonic()
            shape = execute_build123d_code(code)
            exec_time = (time.monotonic() - exec_start) * 1000

            logger.info(
                "code_executed_successfully",
                execution_time_ms=round(exec_time, 1),
                attempt=attempt + 1,
            )

            return DirectGenerationResult(
                code=code,
                shape=shape,
                execution_time_ms=exec_time,
                generation_time_ms=gen_time,
                retry_count=retry_count,
            )

        except Exception as e:
            last_error = str(e)
            retry_count += 1
            logger.warning(
                "code_generation_attempt_failed",
                attempt=attempt + 1,
                error=str(e),
                error_type=type(e).__name__,
                retries_remaining=max_retries - attempt,
            )

            if attempt < max_retries:
                # Ask AI to fix the error
                messages.append({"role": "assistant", "content": code})
                messages.append(
                    {
                        "role": "user",
                        "content": f"That code produced an error: {e}\n\nPlease fix it. Output ONLY the corrected Python code.",
                    }
                )

    # All retries exhausted
    return DirectGenerationResult(
        code=code if "code" in dir() else "",
        error=last_error,
        generation_time_ms=(time.monotonic() - gen_start) * 1000,
        retry_count=retry_count,
    )


async def modify_directly(
    original_code: str,
    modification_request: str,
    max_retries: int = 2,
) -> DirectGenerationResult:
    """
    Modify existing Build123d code based on user request.

    Args:
        original_code: The original Build123d code to modify
        modification_request: What the user wants to change
        max_retries: Number of retry attempts if code execution fails

    Returns:
        DirectGenerationResult with modified code and shape
    """
    client = get_ai_client()

    logger.info(
        "direct_modification_started",
        modification_request_preview=modification_request[:100],
        original_code_length=len(original_code),
    )

    prompt = DIRECT_MODIFICATION_PROMPT.format(
        build123d_reference=BUILD123D_REFERENCE,
        original_code=original_code,
        modification_request=modification_request,
    )

    messages = [
        {"role": "user", "content": prompt},
    ]

    gen_start = time.monotonic()
    retry_count = 0
    last_error = None
    code = ""

    for attempt in range(max_retries + 1):
        try:
            # Generate code
            code = await client.complete(messages, temperature=0.1)
            gen_time = (time.monotonic() - gen_start) * 1000

            code = sanitize_code(code)
            logger.info(
                "modified_code_generated",
                attempt=attempt + 1,
                code_length=len(code),
                generation_time_ms=round(gen_time, 1),
            )

            # Execute code
            exec_start = time.monotonic()
            shape = execute_build123d_code(code)
            exec_time = (time.monotonic() - exec_start) * 1000

            logger.info(
                "modified_code_executed_successfully",
                execution_time_ms=round(exec_time, 1),
                attempt=attempt + 1,
            )

            return DirectGenerationResult(
                code=code,
                shape=shape,
                execution_time_ms=exec_time,
                generation_time_ms=gen_time,
                retry_count=retry_count,
            )

        except Exception as e:
            last_error = str(e)
            retry_count += 1
            logger.warning(
                "code_modification_attempt_failed",
                attempt=attempt + 1,
                error=str(e),
                error_type=type(e).__name__,
                retries_remaining=max_retries - attempt,
            )

            if attempt < max_retries:
                # Ask AI to fix the error
                messages.append({"role": "assistant", "content": code})
                messages.append(
                    {
                        "role": "user",
                        "content": f"That code produced an error: {e}\n\nPlease fix it. Output ONLY the corrected Python code.",
                    }
                )

    # All retries exhausted
    return DirectGenerationResult(
        code=code,
        error=last_error,
        generation_time_ms=(time.monotonic() - gen_start) * 1000,
        retry_count=retry_count,
    )
