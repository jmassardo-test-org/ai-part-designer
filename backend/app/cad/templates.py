"""
CAD template generators.

Each template is a parameterized function that generates CAD geometry.
Templates are registered in the TEMPLATE_REGISTRY for lookup by slug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import cadquery as cq


class TemplateGenerator(Protocol):
    """Protocol for template generator functions."""

    def __call__(self, **params: Any) -> cq.Workplane:
        """Generate CAD geometry from parameters."""
        ...


# Registry of all available template generators
TEMPLATE_REGISTRY: dict[str, TemplateGenerator] = {}


def register_template(slug: str):
    """Decorator to register a template generator function."""
    def decorator(func: TemplateGenerator) -> TemplateGenerator:
        TEMPLATE_REGISTRY[slug] = func
        return func
    return decorator


def get_template_generator(slug: str) -> TemplateGenerator | None:
    """Get template generator by slug."""
    return TEMPLATE_REGISTRY.get(slug)


def generate_from_template(slug: str, parameters: dict[str, Any]) -> cq.Workplane:
    """
    Generate CAD geometry from template.
    
    Args:
        slug: Template identifier
        parameters: Template parameters
        
    Returns:
        Generated CadQuery workplane
        
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


@register_template("project-box")
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
    ventilation_slots: bool = False,
    slot_width: float = 2.0,
    slot_length: float = 20.0,
    slot_count: int = 3,
    cable_hole: bool = False,
    cable_hole_diameter: float = 8.0,
    cable_hole_position: str = "back",
    **_kwargs,  # Ignore extra params
) -> cq.Workplane:
    """
    Generate a parameterized project box/enclosure.
    
    Creates a two-part box (base and lid) suitable for electronics projects.
    
    Returns:
        Assembly of base and lid as a single workplane
    """
    # Calculate internal dimensions
    inner_length = length - 2 * wall_thickness
    inner_width = width - 2 * wall_thickness
    base_height = height - lid_height
    
    # Auto screw post height
    if screw_post_height <= 0:
        screw_post_height = base_height - wall_thickness - 2
    
    # Create base outer shell
    if corner_style == "rounded" and corner_radius > 0:
        base = (
            cq.Workplane("XY")
            .box(length, width, base_height, centered=(True, True, False))
            .edges("|Z")
            .fillet(corner_radius)
        )
    elif corner_style == "chamfered" and corner_radius > 0:
        base = (
            cq.Workplane("XY")
            .box(length, width, base_height, centered=(True, True, False))
            .edges("|Z")
            .chamfer(corner_radius)
        )
    else:
        base = (
            cq.Workplane("XY")
            .box(length, width, base_height, centered=(True, True, False))
        )
    
    # Hollow out the base
    base = (
        base
        .faces(">Z")
        .workplane()
        .rect(inner_length, inner_width)
        .cutBlind(-(base_height - wall_thickness))
    )
    
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
            # Add post
            post = (
                cq.Workplane("XY")
                .center(x, y)
                .circle(screw_post_diameter / 2)
                .extrude(screw_post_height)
            )
            base = base.union(post)
            
            # Add screw hole
            hole = (
                cq.Workplane("XY")
                .center(x, y)
                .circle(screw_hole_diameter / 2)
                .extrude(screw_post_height)
            )
            base = base.cut(hole)
    
    # Add ventilation slots
    if ventilation_slots and slot_count > 0:
        slot_spacing = (inner_length - slot_length) / 2
        slot_start_y = -((slot_count - 1) * (slot_width + 2)) / 2
        
        for i in range(slot_count):
            y_pos = slot_start_y + i * (slot_width + 2)
            slot = (
                cq.Workplane("XY")
                .workplane(offset=base_height - wall_thickness / 2)
                .center(0, y_pos)
                .slot2D(slot_length, slot_width)
                .cutThruAll()
            )
            base = base.cut(slot)
    
    # Add cable hole
    if cable_hole:
        hole_z = base_height / 2
        if cable_hole_position == "back":
            hole = (
                cq.Workplane("XZ")
                .workplane(offset=-width / 2)
                .center(0, hole_z)
                .circle(cable_hole_diameter / 2)
                .extrude(wall_thickness + 1)
            )
        elif cable_hole_position == "left":
            hole = (
                cq.Workplane("YZ")
                .workplane(offset=-length / 2)
                .center(0, hole_z)
                .circle(cable_hole_diameter / 2)
                .extrude(wall_thickness + 1)
            )
        else:  # right
            hole = (
                cq.Workplane("YZ")
                .workplane(offset=length / 2 - wall_thickness - 1)
                .center(0, hole_z)
                .circle(cable_hole_diameter / 2)
                .extrude(wall_thickness + 1)
            )
        base = base.cut(hole)
    
    # Create lid
    lid_inner_length = inner_length - lid_tolerance * 2
    lid_inner_width = inner_width - lid_tolerance * 2
    
    if lid_style == "overlap":
        # Lid sits on top with lip that goes inside
        lip_depth = min(5.0, lid_height - wall_thickness)
        
        if corner_style == "rounded" and corner_radius > 0:
            lid = (
                cq.Workplane("XY")
                .workplane(offset=base_height)
                .box(length, width, lid_height, centered=(True, True, False))
                .edges("|Z")
                .fillet(corner_radius)
            )
        else:
            lid = (
                cq.Workplane("XY")
                .workplane(offset=base_height)
                .box(length, width, lid_height, centered=(True, True, False))
            )
        
        # Create inner lip
        lip = (
            cq.Workplane("XY")
            .workplane(offset=base_height - lip_depth)
            .box(lid_inner_length, lid_inner_width, lip_depth, centered=(True, True, False))
        )
        lid = lid.union(lip)
        
        # Add screw holes in lid if posts enabled
        if screw_posts:
            post_offset = wall_thickness + screw_post_diameter / 2 + 1
            for x, y in [
                (-length / 2 + post_offset, -width / 2 + post_offset),
                (-length / 2 + post_offset, width / 2 - post_offset),
                (length / 2 - post_offset, -width / 2 + post_offset),
                (length / 2 - post_offset, width / 2 - post_offset),
            ]:
                hole = (
                    cq.Workplane("XY")
                    .workplane(offset=base_height)
                    .center(x, y)
                    .circle(screw_hole_diameter / 2 + 0.5)  # Clearance hole
                    .extrude(lid_height)
                )
                lid = lid.cut(hole)
    else:
        # Simple flat lid
        if corner_style == "rounded" and corner_radius > 0:
            lid = (
                cq.Workplane("XY")
                .workplane(offset=base_height)
                .box(length, width, lid_height, centered=(True, True, False))
                .edges("|Z")
                .fillet(corner_radius)
            )
        else:
            lid = (
                cq.Workplane("XY")
                .workplane(offset=base_height)
                .box(length, width, lid_height, centered=(True, True, False))
            )
    
    # Combine base and lid
    result = base.union(lid)
    
    return result


# =============================================================================
# Mounting Bracket Template
# =============================================================================

@register_template("mounting-bracket")
def generate_mounting_bracket(
    width: float = 50.0,
    height: float = 30.0,
    depth: float = 20.0,
    thickness: float = 3.0,
    hole_diameter: float = 5.0,
    hole_count: int = 2,
    fillet_radius: float = 2.0,
    bracket_style: str = "L",  # L, U, Z
    **_kwargs,
) -> cq.Workplane:
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
    """
    if bracket_style == "L":
        # L-bracket: vertical + horizontal
        bracket = (
            cq.Workplane("XZ")
            .moveTo(0, 0)
            .lineTo(depth, 0)
            .lineTo(depth, thickness)
            .lineTo(thickness, thickness)
            .lineTo(thickness, height)
            .lineTo(0, height)
            .close()
            .extrude(width)
        )
        
        # Add fillet on inside corner
        if fillet_radius > 0:
            bracket = bracket.edges("|Y").edges("<Z and >X").fillet(fillet_radius)
        
        # Add holes in horizontal leg
        hole_spacing = (width - hole_diameter * 2) / (hole_count + 1)
        for i in range(hole_count):
            y = hole_diameter + (i + 1) * hole_spacing
            bracket = (
                bracket
                .faces("<Z")
                .workplane()
                .center(depth / 2, y - width / 2)
                .hole(hole_diameter)
            )
        
        # Add holes in vertical leg
        for i in range(hole_count):
            y = hole_diameter + (i + 1) * hole_spacing
            bracket = (
                bracket
                .faces(">X")
                .workplane()
                .center(y - width / 2, height / 2)
                .hole(hole_diameter)
            )
    
    elif bracket_style == "U":
        # U-bracket: two vertical legs
        bracket = (
            cq.Workplane("XZ")
            .moveTo(0, 0)
            .lineTo(depth, 0)
            .lineTo(depth, height)
            .lineTo(depth - thickness, height)
            .lineTo(depth - thickness, thickness)
            .lineTo(thickness, thickness)
            .lineTo(thickness, height)
            .lineTo(0, height)
            .close()
            .extrude(width)
        )
    
    else:  # Z-bracket
        bracket = (
            cq.Workplane("XZ")
            .moveTo(0, 0)
            .lineTo(depth, 0)
            .lineTo(depth, thickness)
            .lineTo(thickness, thickness)
            .lineTo(thickness, height - thickness)
            .lineTo(depth, height - thickness)
            .lineTo(depth, height)
            .lineTo(0, height)
            .lineTo(0, height - thickness)
            .lineTo(depth - thickness, height - thickness)
            .lineTo(depth - thickness, thickness)
            .lineTo(0, thickness)
            .close()
            .extrude(width)
        )
    
    return bracket


# =============================================================================
# Standoff Template
# =============================================================================

@register_template("standoff")
def generate_standoff(
    height: float = 10.0,
    outer_diameter: float = 8.0,
    inner_diameter: float = 3.2,
    head_diameter: float = 12.0,
    head_height: float = 2.0,
    thread_type: str = "none",  # none, m3, m4, m5
    hex_socket: bool = False,
    hex_size: float = 5.0,
    **_kwargs,
) -> cq.Workplane:
    """
    Generate a parameterized standoff/spacer.
    
    Args:
        height: Total height of standoff body
        outer_diameter: Outer diameter of body
        inner_diameter: Inner hole diameter
        head_diameter: Diameter of head/flange (0 for none)
        head_height: Height of head
        thread_type: Thread specification
        hex_socket: Add hex socket in top
        hex_size: Hex socket size (across flats)
    """
    # Create body
    standoff = (
        cq.Workplane("XY")
        .circle(outer_diameter / 2)
        .extrude(height)
    )
    
    # Add head if specified
    if head_diameter > outer_diameter:
        head = (
            cq.Workplane("XY")
            .circle(head_diameter / 2)
            .extrude(head_height)
        )
        standoff = standoff.union(head)
    
    # Add center hole
    standoff = (
        standoff
        .faces(">Z")
        .workplane()
        .hole(inner_diameter, height + head_height)
    )
    
    # Add hex socket
    if hex_socket:
        hex_depth = min(height / 2, 5.0)
        standoff = (
            standoff
            .faces(">Z")
            .workplane()
            .polygon(6, hex_size)
            .cutBlind(-hex_depth)
        )
    
    return standoff


# =============================================================================
# Cable Gland Template
# =============================================================================

@register_template("cable-gland")
def generate_cable_gland(
    body_diameter: float = 20.0,
    body_height: float = 15.0,
    thread_diameter: float = 16.0,
    thread_height: float = 8.0,
    cable_diameter: float = 6.0,
    hex_size: float = 22.0,
    seal_groove: bool = True,
    groove_diameter: float = 18.0,
    groove_width: float = 2.0,
    **_kwargs,
) -> cq.Workplane:
    """
    Generate a cable gland body.
    
    Args:
        body_diameter: Main body diameter
        body_height: Height of body (above panel)
        thread_diameter: Thread outer diameter
        thread_height: Thread length
        cable_diameter: Cable passage hole diameter
        hex_size: Hex nut size for tightening
        seal_groove: Add O-ring groove
        groove_diameter: O-ring groove diameter
        groove_width: O-ring groove width
    """
    total_height = body_height + thread_height
    
    # Create hex body
    gland = (
        cq.Workplane("XY")
        .polygon(6, hex_size)
        .extrude(body_height)
    )
    
    # Add thread portion (cylindrical)
    thread = (
        cq.Workplane("XY")
        .workplane(offset=-thread_height)
        .circle(thread_diameter / 2)
        .extrude(thread_height)
    )
    gland = gland.union(thread)
    
    # Cable hole through center
    gland = (
        gland
        .faces(">Z")
        .workplane()
        .hole(cable_diameter, total_height)
    )
    
    # Add O-ring groove
    if seal_groove:
        groove_z = -thread_height + 2
        groove = (
            cq.Workplane("XY")
            .workplane(offset=groove_z)
            .circle(groove_diameter / 2)
            .circle(groove_diameter / 2 - groove_width)
            .extrude(groove_width)
        )
        gland = gland.cut(groove)
    
    return gland
