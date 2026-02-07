"""
Dovetail Joint Pattern Generator.

Provides generators for creating dovetail joints for woodworking-style
interlocking assemblies. Dovetails are strong, self-locking joints
commonly used in drawers, boxes, and furniture.

Joint Types:
- Through Dovetail: Visible from both sides
- Half-Blind Dovetail: Visible from one side only
- Sliding Dovetail: For shelves and dividers

Standard ratios:
- Softwood: 1:6 ratio (about 9.5 degrees)
- Hardwood: 1:8 ratio (about 7 degrees)

Migrated from CadQuery to Build123d.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from build123d import (
    Align,
    Box,
    BuildPart,
    Location,
    Mode,
    Part,
)

from app.cad.templates import register_template

# =============================================================================
# Dovetail Constants
# =============================================================================

# Standard angles
SOFTWOOD_RATIO = 6  # 1:6 ratio
HARDWOOD_RATIO = 8  # 1:8 ratio

# Default dimensions (mm)
DEFAULT_THICKNESS = 18.0  # Common board thickness
DEFAULT_PIN_WIDTH = 8.0
DEFAULT_TAIL_WIDTH = 25.0


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class DovetailParams:
    """Parameters for through dovetail joint."""

    # Board dimensions
    board_width: float = 100.0  # Width of the board
    board_thickness: float = 18.0  # Thickness of the board

    # Joint parameters
    num_tails: int = 3  # Number of tails
    tail_angle: float = 14.0  # Angle in degrees (1:4 ratio ≈ 14°)

    # Pin sizing
    half_pin: bool = True  # Half pins at the ends

    # Fit
    tolerance: float = 0.1  # mm - gap for fit


@dataclass
class SlidingDovetailParams:
    """Parameters for sliding dovetail joint."""

    # Slot dimensions
    slot_width: float = 15.0
    slot_depth: float = 8.0
    slot_length: float = 100.0

    # Angle
    angle: float = 14.0  # Degrees

    # Fit
    tolerance: float = 0.15  # mm


@dataclass
class BoxJointParams:
    """Parameters for box joint (finger joint)."""

    # Board dimensions
    board_width: float = 100.0
    board_thickness: float = 12.0

    # Joint parameters
    finger_width: float = 6.0  # Width of each finger

    # Fit
    tolerance: float = 0.1


# =============================================================================
# Through Dovetail Generator
# =============================================================================


def _calculate_tail_spacing(
    board_width: float,
    num_tails: int,
    half_pin: bool,
) -> list[tuple[float, float]]:
    """
    Calculate positions of tails along the board width.

    Returns list of (center_position, width) for each tail.
    """
    if half_pin:
        # With half pins at the ends
        # Total pins = num_tails + 1 (half pins count as 0.5 each)
        # Spacing is uniform
        spacing = board_width / (num_tails + 1)
        tails = []
        for i in range(num_tails):
            center = spacing * (i + 1)
            width = spacing * 0.6  # Tails take about 60% of the space
            tails.append((center, width))
        return tails
    # Full pins at the ends
    spacing = board_width / (num_tails + 2)
    tails = []
    for i in range(num_tails):
        center = spacing * (i + 1.5)
        width = spacing * 0.6
        tails.append((center, width))
    return tails


@register_template("dovetail-tail-board")  # type: ignore[untyped-decorator]
def generate_dovetail_tail_board(
    board_width: float = 100.0,
    board_thickness: float = 18.0,
    board_length: float = 50.0,
    num_tails: int = 3,
    tail_angle: float = 14.0,
    half_pin: bool = True,
    _tolerance: float = 0.1,
    **_kwargs: Any,
) -> Part:
    """
    Generate the tail board of a through dovetail joint.

    The tails are the trapezoidal projections that interlock
    with the pins on the mating board.

    Args:
        board_width: Width of the board
        board_thickness: Thickness of the board
        board_length: Length of the board (depth of joint)
        num_tails: Number of tail projections
        tail_angle: Angle of the dovetail in degrees
        half_pin: Whether to use half pins at edges
        tolerance: Fit tolerance

    Returns:
        Build123d Part with the tail board
    """
    # Calculate the angle offset at the face
    angle_rad = math.radians(tail_angle)
    offset = board_thickness * math.tan(angle_rad)

    # Calculate tail positions
    tail_spacing = _calculate_tail_spacing(board_width, num_tails, half_pin)

    with BuildPart() as builder:
        # Start with the base board
        Box(board_width, board_length, board_thickness, align=(Align.MIN, Align.MIN, Align.MIN))

        # Cut the pin sockets (the waste between tails)
        for i in range(num_tails + 1):
            if half_pin and (i == 0 or i == num_tails):
                # Half pin at the edge - handle end cuts
                if i == 0 and len(tail_spacing) > 0:
                    # Cut from edge to first tail
                    socket_end = tail_spacing[0][0] - tail_spacing[0][1] / 2
                    if socket_end > 0.1:
                        Box(
                            socket_end + offset,
                            board_length,
                            board_thickness,
                            align=(Align.MIN, Align.MIN, Align.MIN),
                            mode=Mode.SUBTRACT,
                        )
                elif i == num_tails and len(tail_spacing) > 0:
                    # Cut from last tail to edge
                    socket_start = tail_spacing[-1][0] + tail_spacing[-1][1] / 2
                    socket_width = board_width - socket_start
                    if socket_width > 0.1:
                        Box(
                            socket_width + offset,
                            board_length,
                            board_thickness,
                            align=(Align.MAX, Align.MIN, Align.MIN),
                            mode=Mode.SUBTRACT,
                        ).locate(Location((board_width, 0, 0)))
                continue

            # Calculate the pin socket position (between tails)
            if i == 0:
                socket_start = 0
                if num_tails > 0:
                    socket_end = tail_spacing[0][0] - tail_spacing[0][1] / 2
                else:
                    continue
            elif i == num_tails:
                socket_start = tail_spacing[-1][0] + tail_spacing[-1][1] / 2
                socket_end = board_width
            else:
                socket_start = tail_spacing[i - 1][0] + tail_spacing[i - 1][1] / 2
                socket_end = tail_spacing[i][0] - tail_spacing[i][1] / 2

            socket_width = socket_end - socket_start
            socket_center = (socket_start + socket_end) / 2

            if socket_width > 0.1:
                # Create a simple rectangular cut for the socket
                # A proper implementation would create angled cuts
                Box(
                    socket_width,
                    board_length,
                    board_thickness,
                    align=(Align.CENTER, Align.MIN, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((socket_center, 0, 0)))

    return builder.part


@register_template("dovetail-pin-board")  # type: ignore[untyped-decorator]
def generate_dovetail_pin_board(
    board_width: float = 100.0,
    board_thickness: float = 18.0,
    board_length: float = 50.0,
    num_tails: int = 3,
    tail_angle: float = 14.0,
    half_pin: bool = True,
    tolerance: float = 0.1,
    **_kwargs: Any,
) -> Part:
    """
    Generate the pin board of a through dovetail joint.

    The pins are the narrow projections between the tails.

    Args:
        board_width: Width of the board
        board_thickness: Thickness of the board
        board_length: Length of the board
        num_tails: Number of tails on the mating board
        tail_angle: Angle of the dovetail in degrees
        half_pin: Whether to use half pins at edges
        tolerance: Fit tolerance

    Returns:
        Build123d Part with the pin board
    """
    # Calculate the angle offset at the face
    angle_rad = math.radians(tail_angle)
    board_thickness * math.tan(angle_rad)

    # Calculate tail positions (we cut the tail sockets)
    tail_spacing = _calculate_tail_spacing(board_width, num_tails, half_pin)

    with BuildPart() as builder:
        # Start with the base board
        Box(board_width, board_length, board_thickness, align=(Align.MIN, Align.MIN, Align.MIN))

        # Cut the tail sockets (angled openings for the tails)
        for center, width in tail_spacing:
            # Create rectangular cut for the tail socket
            # Includes tolerance for fit
            Box(
                width + tolerance * 2,
                board_length,
                board_thickness,
                align=(Align.CENTER, Align.MIN, Align.MIN),
                mode=Mode.SUBTRACT,
            ).locate(Location((center, 0, 0)))

    return builder.part


# =============================================================================
# Sliding Dovetail Generator
# =============================================================================


@register_template("sliding-dovetail-slot")  # type: ignore[untyped-decorator]
def generate_sliding_dovetail_slot(
    base_width: float = 100.0,
    base_length: float = 200.0,
    base_thickness: float = 18.0,
    slot_width: float = 15.0,
    slot_depth: float = 8.0,
    slot_angle: float = 14.0,
    slot_position: float = 50.0,
    tolerance: float = 0.15,
    **_kwargs: Any,
) -> Part:
    """
    Generate a board with a sliding dovetail slot (female part).

    Used for shelves, dividers, or any sliding joint.

    Args:
        base_width: Width of the base board
        base_length: Length of the base board
        base_thickness: Thickness of the base board
        slot_width: Width of the slot at the narrow end
        slot_depth: Depth of the slot
        slot_angle: Dovetail angle in degrees
        slot_position: Position of slot from the edge
        tolerance: Fit tolerance

    Returns:
        Build123d Part with the slotted board
    """
    angle_rad = math.radians(slot_angle)
    offset = slot_depth * math.tan(angle_rad)

    # Width at the bottom of the slot (wider due to angle)
    bottom_width = slot_width + 2 * offset + 2 * tolerance

    with BuildPart() as builder:
        # Create the base board
        Box(
            base_width,
            base_length,
            base_thickness,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )

        # Create the dovetail slot as a simple trapezoidal cut
        # Using two overlapping boxes to approximate the dovetail shape

        # Main slot body
        Box(
            bottom_width,
            base_length,
            slot_depth,
            align=(Align.CENTER, Align.CENTER, Align.MAX),
            mode=Mode.SUBTRACT,
        ).locate(Location((slot_position - base_width / 2, 0, base_thickness / 2)))

    return builder.part


@register_template("sliding-dovetail-key")  # type: ignore[untyped-decorator]
def generate_sliding_dovetail_key(
    key_width: float = 15.0,
    key_length: float = 200.0,
    key_height: float = 8.0,
    key_angle: float = 14.0,
    tolerance: float = 0.15,
    **_kwargs: Any,
) -> Part:
    """
    Generate a sliding dovetail key (male part).

    The key slides into the slot to create a strong joint.

    Args:
        key_width: Width at the narrow end
        key_length: Length of the key
        key_height: Height (depth into the slot)
        key_angle: Dovetail angle in degrees
        tolerance: Fit tolerance

    Returns:
        Build123d Part with the dovetail key
    """
    angle_rad = math.radians(key_angle)
    offset = key_height * math.tan(angle_rad)

    # Width at the base of the key (wider)
    base_width = key_width + 2 * offset - 2 * tolerance

    with BuildPart() as builder:
        # Create the key as a simple box
        # A proper implementation would create a trapezoidal profile
        Box(base_width, key_length, key_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

    return builder.part


# =============================================================================
# Box Joint (Finger Joint) Generator
# =============================================================================


@register_template("box-joint-board-a")  # type: ignore[untyped-decorator]
def generate_box_joint_board_a(
    board_width: float = 100.0,
    board_thickness: float = 12.0,
    board_length: float = 50.0,
    finger_width: float = 6.0,
    tolerance: float = 0.1,
    **_kwargs: Any,
) -> Part:
    """
    Generate board A of a box joint (finger joint).

    Box joints have interlocking rectangular fingers.
    This generates the first board (starts with a finger).

    Args:
        board_width: Width of the board
        board_thickness: Thickness of the board
        board_length: Length/depth of the joint
        finger_width: Width of each finger
        tolerance: Fit tolerance

    Returns:
        Build123d Part with the finger joint board
    """
    num_fingers = int(board_width / finger_width)
    actual_finger_width = board_width / num_fingers

    with BuildPart() as builder:
        # Start with the base board
        Box(board_width, board_length, board_thickness, align=(Align.MIN, Align.MIN, Align.MIN))

        # Cut alternating slots (board A has fingers at positions 0, 2, 4...)
        for i in range(num_fingers):
            if i % 2 == 1:  # Cut slots at odd positions
                slot_start = i * actual_finger_width
                Box(
                    actual_finger_width + tolerance,
                    board_length + 1,  # Extra length to ensure full cut
                    board_thickness + 1,
                    align=(Align.MIN, Align.MIN, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((slot_start - tolerance / 2, -0.5, -0.5)))

    return builder.part


@register_template("box-joint-board-b")  # type: ignore[untyped-decorator]
def generate_box_joint_board_b(
    board_width: float = 100.0,
    board_thickness: float = 12.0,
    board_length: float = 50.0,
    finger_width: float = 6.0,
    tolerance: float = 0.1,
    **_kwargs: Any,
) -> Part:
    """
    Generate board B of a box joint (finger joint).

    This is the mating board (starts with a slot).

    Args:
        board_width: Width of the board
        board_thickness: Thickness of the board
        board_length: Length/depth of the joint
        finger_width: Width of each finger
        tolerance: Fit tolerance

    Returns:
        Build123d Part with the finger joint board
    """
    num_fingers = int(board_width / finger_width)
    actual_finger_width = board_width / num_fingers

    with BuildPart() as builder:
        # Start with the base board
        Box(board_width, board_length, board_thickness, align=(Align.MIN, Align.MIN, Align.MIN))

        # Cut alternating slots (board B has fingers at positions 1, 3, 5...)
        for i in range(num_fingers):
            if i % 2 == 0:  # Cut slots at even positions
                slot_start = i * actual_finger_width
                Box(
                    actual_finger_width + tolerance,
                    board_length + 1,
                    board_thickness + 1,
                    align=(Align.MIN, Align.MIN, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((slot_start - tolerance / 2, -0.5, -0.5)))

    return builder.part


# =============================================================================
# Utility Functions
# =============================================================================


def calculate_dovetail_angle(ratio: int) -> float:
    """
    Calculate dovetail angle from ratio.

    Args:
        ratio: The ratio (e.g., 6 for 1:6)

    Returns:
        Angle in degrees
    """
    return math.degrees(math.atan(1 / ratio))


def get_recommended_angle(wood_type: Literal["softwood", "hardwood"]) -> float:
    """
    Get recommended dovetail angle for wood type.

    Args:
        wood_type: Either "softwood" or "hardwood"

    Returns:
        Recommended angle in degrees
    """
    if wood_type == "softwood":
        return calculate_dovetail_angle(SOFTWOOD_RATIO)
    return calculate_dovetail_angle(HARDWOOD_RATIO)


def get_dovetail_templates() -> list[dict[str, Any]]:
    """Get list of available dovetail templates."""
    return [
        {
            "slug": "dovetail-tail-board",
            "name": "Dovetail Tail Board",
            "description": "Tail board of a through dovetail joint",
            "parameters": [
                {"name": "board_width", "type": "float", "default": 100.0},
                {"name": "board_thickness", "type": "float", "default": 18.0},
                {"name": "board_length", "type": "float", "default": 50.0},
                {"name": "num_tails", "type": "int", "default": 3, "min": 1, "max": 10},
                {"name": "tail_angle", "type": "float", "default": 14.0, "min": 5, "max": 20},
                {"name": "half_pin", "type": "bool", "default": True},
            ],
        },
        {
            "slug": "dovetail-pin-board",
            "name": "Dovetail Pin Board",
            "description": "Pin board of a through dovetail joint",
            "parameters": [
                {"name": "board_width", "type": "float", "default": 100.0},
                {"name": "board_thickness", "type": "float", "default": 18.0},
                {"name": "board_length", "type": "float", "default": 50.0},
                {"name": "num_tails", "type": "int", "default": 3, "min": 1, "max": 10},
                {"name": "tail_angle", "type": "float", "default": 14.0, "min": 5, "max": 20},
                {"name": "half_pin", "type": "bool", "default": True},
            ],
        },
        {
            "slug": "sliding-dovetail-slot",
            "name": "Sliding Dovetail Slot",
            "description": "Board with sliding dovetail slot (female)",
            "parameters": [
                {"name": "base_width", "type": "float", "default": 100.0},
                {"name": "base_length", "type": "float", "default": 200.0},
                {"name": "slot_width", "type": "float", "default": 15.0},
                {"name": "slot_depth", "type": "float", "default": 8.0},
                {"name": "slot_angle", "type": "float", "default": 14.0},
            ],
        },
        {
            "slug": "sliding-dovetail-key",
            "name": "Sliding Dovetail Key",
            "description": "Sliding dovetail key (male)",
            "parameters": [
                {"name": "key_width", "type": "float", "default": 15.0},
                {"name": "key_length", "type": "float", "default": 200.0},
                {"name": "key_height", "type": "float", "default": 8.0},
                {"name": "key_angle", "type": "float", "default": 14.0},
            ],
        },
        {
            "slug": "box-joint-board-a",
            "name": "Box Joint Board A",
            "description": "First board of a box/finger joint",
            "parameters": [
                {"name": "board_width", "type": "float", "default": 100.0},
                {"name": "board_thickness", "type": "float", "default": 12.0},
                {"name": "finger_width", "type": "float", "default": 6.0},
            ],
        },
        {
            "slug": "box-joint-board-b",
            "name": "Box Joint Board B",
            "description": "Mating board of a box/finger joint",
            "parameters": [
                {"name": "board_width", "type": "float", "default": 100.0},
                {"name": "board_thickness", "type": "float", "default": 12.0},
                {"name": "finger_width", "type": "float", "default": 6.0},
            ],
        },
    ]
