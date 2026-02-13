"""
CAD template generators.

Each template is a parameterized function that generates CAD geometry.
Templates are registered in the TEMPLATE_REGISTRY for lookup by slug.

This module has been migrated from CadQuery to Build123d.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    Cylinder,
    Location,
    Mode,
    Part,
    chamfer,
    fillet,
)


class TemplateGenerator(Protocol):
    """Protocol for template generator functions."""

    def __call__(self, **params: Any) -> Part:
        """Generate CAD geometry from parameters."""
        ...


# Registry of all available template generators
TEMPLATE_REGISTRY: dict[str, TemplateGenerator] = {}


def register_template(slug: str) -> Any:
    """Decorator to register a template generator function."""

    def decorator(func: TemplateGenerator) -> TemplateGenerator:
        TEMPLATE_REGISTRY[slug] = func
        return func

    return decorator


def get_template_generator(slug: str) -> TemplateGenerator | None:
    """Get template generator by slug."""
    return TEMPLATE_REGISTRY.get(slug)


def generate_from_template(slug: str, parameters: dict[str, Any]) -> Part:
    """
    Generate CAD geometry from template.

    Args:
        slug: Template identifier
        parameters: Template parameters

    Returns:
        Generated Build123d Part

    Raises:
        ValueError: If template not found
    """
    generator = get_template_generator(slug)
    if generator is None:
        raise ValueError(f"Template not found: {slug}")
    return generator(**parameters)


# =============================================================================
# Project Box Template
# =============================================================================


@dataclass
class ProjectBoxParams:
    """Parameters for project box template."""

    # Outer dimensions
    length: float = 100.0  # mm
    width: float = 60.0
    height: float = 40.0

    # Wall properties
    wall_thickness: float = 2.0

    # Corner options
    corner_radius: float = 3.0
    corner_style: str = "rounded"  # rounded, chamfered, sharp

    # Lid options
    lid_style: str = "overlap"  # overlap, inset, snap
    lid_height: float = 10.0
    lid_tolerance: float = 0.3

    # Screw posts
    screw_posts: bool = True
    screw_post_diameter: float = 6.0
    screw_hole_diameter: float = 3.0
    screw_post_height: float = 0.0  # 0 = auto (height - lid_height - 2)

    # Ventilation
    ventilation_slots: bool = False
    slot_width: float = 2.0
    slot_length: float = 20.0
    slot_count: int = 3

    # Cable entry
    cable_hole: bool = False
    cable_hole_diameter: float = 8.0
    cable_hole_position: str = "back"  # back, left, right


@register_template("project-box")  # type: ignore[untyped-decorator]
def generate_project_box(
    length: float = 100.0,
    width: float = 60.0,
    height: float = 40.0,
    wall_thickness: float = 2.0,
    corner_radius: float = 3.0,
    corner_style: str = "rounded",
    lid_style: str = "overlap",
    lid_height: float = 10.0,
    lid_tolerance: float = 0.3,
    screw_posts: bool = True,
    screw_post_diameter: float = 6.0,
    screw_hole_diameter: float = 3.0,
    screw_post_height: float = 0.0,
    _ventilation_slots: bool = False,  # TODO: Implement ventilation slots
    _slot_width: float = 2.0,
    _slot_length: float = 20.0,
    _slot_count: int = 3,
    cable_hole: bool = False,
    cable_hole_diameter: float = 8.0,
    cable_hole_position: str = "back",
    **_kwargs: Any,
) -> Part:
    """
    Generate a parameterized project box/enclosure.

    Creates a two-part box (base and lid) suitable for electronics projects.

    Note: Ventilation slot parameters are reserved for future implementation
    and are currently not used in the generated design.

    Returns:
        Assembly of base and lid as a single Part
    """
    # Calculate internal dimensions
    inner_length = length - 2 * wall_thickness
    inner_width = width - 2 * wall_thickness
    base_height = height - lid_height

    # Auto screw post height
    if screw_post_height <= 0:
        screw_post_height = base_height - wall_thickness - 2

    with BuildPart() as builder:
        # Create base outer shell
        Box(length, width, base_height, align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Apply corner treatment
        if corner_style == "rounded" and corner_radius > 0:
            # Fillet vertical edges
            vertical_edges = builder.edges().filter_by(Axis.Z)
            if vertical_edges:
                fillet(vertical_edges, corner_radius)
        elif corner_style == "chamfered" and corner_radius > 0:
            vertical_edges = builder.edges().filter_by(Axis.Z)
            if vertical_edges:
                chamfer(vertical_edges, corner_radius)

        # Hollow out the base (cut internal cavity)
        with BuildPart(mode=Mode.SUBTRACT):
            Box(
                inner_length,
                inner_width,
                base_height - wall_thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            ).locate(Location((0, 0, wall_thickness)))

        # Add screw posts
        if screw_posts:
            post_offset = wall_thickness + screw_post_diameter / 2 + 1
            post_positions = [
                (-length / 2 + post_offset, -width / 2 + post_offset),
                (-length / 2 + post_offset, width / 2 - post_offset),
                (length / 2 - post_offset, -width / 2 + post_offset),
                (length / 2 - post_offset, width / 2 - post_offset),
            ]

            for x, y in post_positions:
                # Add post cylinder
                Cylinder(
                    screw_post_diameter / 2,
                    screw_post_height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                ).locate(Location((x, y, wall_thickness)))

                # Cut screw hole
                Cylinder(
                    screw_hole_diameter / 2,
                    screw_post_height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((x, y, wall_thickness)))

        # Add cable hole
        if cable_hole:
            hole_z = base_height / 2
            r = cable_hole_diameter / 2
            if cable_hole_position == "back":
                Cylinder(
                    r,
                    wall_thickness + 2,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((0, -width / 2, hole_z))).rotate(Axis.X, 90)
            elif cable_hole_position == "left":
                Cylinder(
                    r,
                    wall_thickness + 2,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((-length / 2, 0, hole_z))).rotate(Axis.Y, 90)
            else:  # right
                Cylinder(
                    r,
                    wall_thickness + 2,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((length / 2, 0, hole_z))).rotate(Axis.Y, -90)

        # Create lid
        inner_length - lid_tolerance * 2
        inner_width - lid_tolerance * 2

        # Main lid body
        Box(length, width, lid_height, align=(Align.CENTER, Align.CENTER, Align.MIN)).locate(
            Location((0, 0, base_height))
        )

        # Apply corner treatment to lid
        if corner_style == "rounded" and corner_radius > 0:
            top_vertical_edges = (
                builder.edges().filter_by(Axis.Z).filter_by(lambda e: base_height < e.center().Z)
            )
            if top_vertical_edges:
                try:
                    fillet(top_vertical_edges, corner_radius)
                except Exception:
                    pass  # Skip if fillet fails on complex geometry

        if lid_style == "overlap" and screw_posts:
            # Add screw holes in lid
            post_offset = wall_thickness + screw_post_diameter / 2 + 1
            clearance_r = screw_hole_diameter / 2 + 0.5
            for x, y in [
                (-length / 2 + post_offset, -width / 2 + post_offset),
                (-length / 2 + post_offset, width / 2 - post_offset),
                (length / 2 - post_offset, -width / 2 + post_offset),
                (length / 2 - post_offset, width / 2 - post_offset),
            ]:
                Cylinder(
                    clearance_r,
                    lid_height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((x, y, base_height)))

    return builder.part  # type: ignore[no-any-return]


# =============================================================================
# Mounting Bracket Template
# =============================================================================


@register_template("mounting-bracket")  # type: ignore[untyped-decorator]
def generate_mounting_bracket(
    width: float = 50.0,
    height: float = 30.0,
    depth: float = 20.0,
    thickness: float = 3.0,
    hole_diameter: float = 5.0,
    hole_count: int = 2,
    fillet_radius: float = 2.0,
    bracket_style: str = "L",  # L, U, Z
    **_kwargs: Any,
) -> Part:
    """
    Generate a parameterized mounting bracket.

    Args:
        width: Width of the bracket
        height: Height of the vertical portion
        depth: Depth of the horizontal portion
        thickness: Material thickness
        hole_diameter: Mounting hole diameter
        hole_count: Number of holes per leg
        fillet_radius: Fillet on inside corner
        bracket_style: Shape (L, U, Z)

    Returns:
        Generated bracket as Part
    """
    with BuildPart() as builder:
        if bracket_style == "L":
            # L-bracket: vertical leg + horizontal base
            # Vertical leg
            Box(thickness, width, height, align=(Align.MIN, Align.CENTER, Align.MIN))
            # Horizontal base
            Box(depth, width, thickness, align=(Align.MIN, Align.CENTER, Align.MIN))

            # Add fillet on inside corner if possible
            if fillet_radius > 0:
                try:
                    inside_edges = builder.edges().filter_by(
                        lambda e: (
                            abs(e.center().X - thickness) < 0.1
                            and abs(e.center().Z - thickness) < 0.1
                        )
                    )
                    if inside_edges:
                        fillet(inside_edges, fillet_radius)
                except Exception:
                    pass

            # Add holes in horizontal leg
            hole_spacing = width / (hole_count + 1)
            for i in range(hole_count):
                y = -width / 2 + (i + 1) * hole_spacing
                Cylinder(
                    hole_diameter / 2,
                    thickness,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((depth / 2, y, 0)))

            # Add holes in vertical leg
            v_hole_spacing = (height - thickness) / (hole_count + 1)
            for i in range(hole_count):
                y = -width / 2 + (i + 1) * hole_spacing
                z = thickness + (i + 1) * v_hole_spacing
                Cylinder(
                    hole_diameter / 2,
                    thickness,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((0, y, z))).rotate(Axis.Y, -90)

        elif bracket_style == "U":
            # U-bracket: two vertical legs connected by horizontal
            # Left leg
            Box(thickness, width, height, align=(Align.MIN, Align.CENTER, Align.MIN))
            # Right leg
            Box(thickness, width, height, align=(Align.MIN, Align.CENTER, Align.MIN)).locate(
                Location((depth - thickness, 0, 0))
            )
            # Base
            Box(depth, width, thickness, align=(Align.MIN, Align.CENTER, Align.MIN))

            # Holes in base
            hole_spacing = width / (hole_count + 1)
            for i in range(hole_count):
                y = -width / 2 + (i + 1) * hole_spacing
                Cylinder(
                    hole_diameter / 2,
                    thickness,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((depth / 2, y, 0)))

        else:  # Z-bracket
            # Z-bracket: offset mounting
            # Bottom horizontal
            Box(depth, width, thickness, align=(Align.MIN, Align.CENTER, Align.MIN))
            # Vertical section
            Box(thickness, width, height, align=(Align.MIN, Align.CENTER, Align.MIN)).locate(
                Location((depth - thickness, 0, 0))
            )
            # Top horizontal
            Box(depth, width, thickness, align=(Align.MIN, Align.CENTER, Align.MIN)).locate(
                Location((depth - thickness, 0, height - thickness))
            )

            # Holes in bottom
            hole_spacing = width / (hole_count + 1)
            for i in range(hole_count):
                y = -width / 2 + (i + 1) * hole_spacing
                Cylinder(
                    hole_diameter / 2,
                    thickness,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((depth / 2, y, 0)))

            # Holes in top
            for i in range(hole_count):
                y = -width / 2 + (i + 1) * hole_spacing
                Cylinder(
                    hole_diameter / 2,
                    thickness,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                ).locate(Location((depth * 1.5 - thickness, y, height - thickness)))

    return builder.part  # type: ignore[no-any-return]


# =============================================================================
# Simple Box Template
# =============================================================================


@register_template("simple-box")  # type: ignore[untyped-decorator]
def generate_simple_box(
    length: float = 50.0,
    width: float = 50.0,
    height: float = 50.0,
    wall_thickness: float = 2.0,
    open_top: bool = True,
    corner_radius: float = 0.0,
    **_kwargs: Any,
) -> Part:
    """
    Generate a simple hollow box.

    Args:
        length: Outer length
        width: Outer width
        height: Outer height
        wall_thickness: Wall thickness
        open_top: Whether top is open
        corner_radius: Fillet radius for corners

    Returns:
        Generated box as Part
    """
    with BuildPart() as builder:
        # Outer shell
        Box(length, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Apply corner treatment
        if corner_radius > 0:
            try:
                vertical_edges = builder.edges().filter_by(Axis.Z)
                fillet(vertical_edges, corner_radius)
            except Exception:
                pass

        # Hollow out
        inner_length = length - 2 * wall_thickness
        inner_width = width - 2 * wall_thickness
        inner_height = height - wall_thickness if open_top else height - 2 * wall_thickness

        Box(
            inner_length,
            inner_width,
            inner_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        ).locate(Location((0, 0, wall_thickness)))

    return builder.part  # type: ignore[no-any-return]


# =============================================================================
# Spacer/Standoff Template
# =============================================================================


@register_template("standoff")  # type: ignore[untyped-decorator]
def generate_standoff(
    outer_diameter: float = 8.0,
    inner_diameter: float = 3.0,
    height: float = 10.0,
    _hex_head: bool = False,  # TODO: Implement hex head feature
    _head_height: float = 3.0,
    **_kwargs: Any,
) -> Part:
    """
    Generate a cylindrical standoff/spacer.

    Args:
        outer_diameter: Outer diameter
        inner_diameter: Inner hole diameter
        height: Total height
        hex_head: Whether to add hex head for wrench
        head_height: Height of hex head

    Returns:
        Generated standoff as Part
    """
    with BuildPart() as builder:
        # Main cylinder body
        Cylinder(outer_diameter / 2, height, align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Through hole
        Cylinder(
            inner_diameter / 2,
            height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )

    return builder.part  # type: ignore[no-any-return]


# =============================================================================
# Cable Clip Template
# =============================================================================


@register_template("cable-clip")  # type: ignore[untyped-decorator]
def generate_cable_clip(
    cable_diameter: float = 6.0,
    clip_width: float = 10.0,
    base_thickness: float = 2.0,
    wall_thickness: float = 1.5,
    screw_hole_diameter: float = 3.0,
    _opening_angle: float = 60.0,  # TODO: Implement opening angle for snap-in
    **_kwargs: Any,
) -> Part:
    """
    Generate a cable management clip.

    Args:
        cable_diameter: Diameter of cable to hold
        clip_width: Width of the clip
        base_thickness: Thickness of mounting base
        wall_thickness: Thickness of clip walls
        screw_hole_diameter: Mounting screw hole diameter
        opening_angle: Opening angle for snap-in

    Returns:
        Generated cable clip as Part
    """
    outer_radius = cable_diameter / 2 + wall_thickness
    base_width = outer_radius * 2 + 4  # Extra for screw flanges
    base_length = clip_width

    with BuildPart() as builder:
        # Base plate
        Box(base_width, base_length, base_thickness, align=(Align.CENTER, Align.CENTER, Align.MIN))

        # Cable holder (partial cylinder)
        Cylinder(outer_radius, clip_width, align=(Align.CENTER, Align.CENTER, Align.MIN)).locate(
            Location((0, 0, base_thickness))
        ).rotate(Axis.X, 90)

        # Cut cable channel
        Cylinder(
            cable_diameter / 2,
            clip_width + 2,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        ).locate(Location((0, 0, base_thickness))).rotate(Axis.X, 90)

        # Screw holes
        hole_offset = base_width / 2 - screw_hole_diameter
        for x in [-hole_offset, hole_offset]:
            Cylinder(
                screw_hole_diameter / 2,
                base_thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            ).locate(Location((x, 0, 0)))

    return builder.part  # type: ignore[no-any-return]


# =============================================================================
# Hinge Template
# =============================================================================


@register_template("hinge")  # type: ignore[untyped-decorator]
def generate_hinge(
    leaf_width: float = 30.0,
    leaf_height: float = 40.0,
    thickness: float = 2.0,
    pin_diameter: float = 4.0,
    knuckle_count: int = 3,
    hole_diameter: float = 3.0,
    hole_count: int = 2,
    **_kwargs: Any,
) -> Part:
    """
    Generate a simple hinge.

    Args:
        leaf_width: Width of each leaf
        leaf_height: Height of each leaf
        thickness: Material thickness
        pin_diameter: Hinge pin diameter
        knuckle_count: Number of knuckles (odd number)
        hole_diameter: Mounting hole diameter
        hole_count: Number of mounting holes per leaf

    Returns:
        Generated hinge as Part
    """
    knuckle_radius = pin_diameter / 2 + thickness

    with BuildPart() as builder:
        # Left leaf
        Box(leaf_width, leaf_height, thickness, align=(Align.MAX, Align.CENTER, Align.MIN))

        # Right leaf
        Box(leaf_width, leaf_height, thickness, align=(Align.MIN, Align.CENTER, Align.MIN))

        # Add mounting holes to both leaves
        hole_spacing = leaf_height / (hole_count + 1)
        for i in range(hole_count):
            y = -leaf_height / 2 + (i + 1) * hole_spacing
            # Left leaf holes
            Cylinder(
                hole_diameter / 2,
                thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            ).locate(Location((-leaf_width / 2, y, 0)))
            # Right leaf holes
            Cylinder(
                hole_diameter / 2,
                thickness,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            ).locate(Location((leaf_width / 2, y, 0)))

        # Add knuckles (simplified - just cylinders at center)
        knuckle_height = leaf_height / knuckle_count
        for i in range(knuckle_count):
            y = -leaf_height / 2 + knuckle_height / 2 + i * knuckle_height
            Cylinder(
                knuckle_radius,
                knuckle_height * 0.9,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            ).locate(Location((0, y, knuckle_radius)))

        # Pin hole through knuckles
        Cylinder(
            pin_diameter / 2,
            leaf_height + 2,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        ).locate(Location((0, 0, knuckle_radius))).rotate(Axis.X, 90)

    return builder.part  # type: ignore[no-any-return]


# =============================================================================
# Enclosure Template (for cad v1 compatibility)
# =============================================================================


@register_template("enclosure")  # type: ignore[untyped-decorator]
def generate_enclosure(
    length: float = 100.0,
    width: float = 80.0,
    height: float = 50.0,
    wall_thickness: float = 2.5,
    corner_radius: float = 5.0,
    **_kwargs: Any,
) -> Part:
    """
    Generate a basic enclosure (alias for project-box with simpler params).

    This is a simplified enclosure for backwards compatibility.
    """
    return generate_project_box(  # type: ignore[no-any-return]
        length=length,
        width=width,
        height=height,
        wall_thickness=wall_thickness,
        corner_radius=corner_radius,
        corner_style="rounded" if corner_radius > 0 else "sharp",
        lid_style="overlap",
        lid_height=height * 0.25,
        screw_posts=True,
        **_kwargs,
    )


# =============================================================================
# Pipe Connector Template
# =============================================================================


@register_template("pipe-connector")  # type: ignore[untyped-decorator]
def generate_pipe_connector(
    pipe_od: float = 25.0,
    _pipe_id: float = 20.0,  # TODO: Use pipe_id for validation or internal features
    connector_type: str = "straight",  # straight, elbow, tee, cross
    socket_depth: float = 15.0,
    angle: float = 90.0,
    **_kwargs: Any,
) -> Part:
    """
    Generate a pipe connector fitting.

    Args:
        pipe_od: Outer diameter of pipe
        pipe_id: Inner diameter of pipe
        connector_type: Type of connector
        socket_depth: Depth of socket
        angle: Angle for elbow connector

    Returns:
        Generated connector as Part
    """
    connector_od = pipe_od + 4  # Wall thickness for connector
    socket_id = pipe_od + 0.5  # Tolerance for pipe fit

    with BuildPart() as builder:
        if connector_type == "straight":
            # Straight coupling
            total_length = socket_depth * 2

            # Outer shell
            Cylinder(connector_od / 2, total_length, align=(Align.CENTER, Align.CENTER, Align.MIN))

            # Inner socket
            Cylinder(
                socket_id / 2,
                total_length,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        elif connector_type == "elbow":
            # Simplified elbow - two cylinders at angle
            leg_length = socket_depth + connector_od / 2

            # First leg (vertical)
            Cylinder(connector_od / 2, leg_length, align=(Align.CENTER, Align.CENTER, Align.MIN))
            Cylinder(
                socket_id / 2,
                leg_length,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

            # Second leg (at angle)
            angle_rad = math.radians(angle)
            leg_length * math.sin(angle_rad)
            leg_length * (1 - math.cos(angle_rad))

            Cylinder(
                connector_od / 2, leg_length, align=(Align.CENTER, Align.CENTER, Align.MIN)
            ).locate(Location((0, 0, leg_length))).rotate(Axis.Y, angle)
            Cylinder(
                socket_id / 2,
                leg_length,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            ).locate(Location((0, 0, leg_length))).rotate(Axis.Y, angle)

        elif connector_type == "tee":
            # T-connector
            main_length = socket_depth * 2 + connector_od

            # Main pipe
            Cylinder(connector_od / 2, main_length, align=(Align.CENTER, Align.CENTER, Align.MIN))
            Cylinder(
                socket_id / 2,
                main_length,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

            # Branch
            branch_length = socket_depth + connector_od / 2
            Cylinder(
                connector_od / 2, branch_length, align=(Align.CENTER, Align.CENTER, Align.MIN)
            ).locate(Location((0, 0, main_length / 2))).rotate(Axis.X, 90)
            Cylinder(
                socket_id / 2,
                branch_length,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            ).locate(Location((0, 0, main_length / 2))).rotate(Axis.X, 90)

        else:  # cross
            # Cross connector (4-way)
            arm_length = socket_depth + connector_od / 2

            # Vertical
            Cylinder(
                connector_od / 2, arm_length * 2, align=(Align.CENTER, Align.CENTER, Align.CENTER)
            )
            Cylinder(
                socket_id / 2,
                arm_length * 2,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )

            # Horizontal (X axis)
            Cylinder(
                connector_od / 2, arm_length * 2, align=(Align.CENTER, Align.CENTER, Align.CENTER)
            ).rotate(Axis.Y, 90)
            Cylinder(
                socket_id / 2,
                arm_length * 2,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            ).rotate(Axis.Y, 90)

    return builder.part  # type: ignore[no-any-return]
