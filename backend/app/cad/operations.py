"""
Boolean and transformation operations for CadQuery shapes.

Provides operations to combine, modify, and transform 3D geometry.

Example:
    >>> from app.cad.primitives import create_box, create_cylinder
    >>> from app.cad.operations import difference
    >>> box = create_box(100, 100, 50)
    >>> hole = create_cylinder(10, 50)
    >>> result = difference(box, hole)  # Box with hole
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cadquery as cq

from app.cad.exceptions import GeometryError, ValidationError

if TYPE_CHECKING:
    pass


# =============================================================================
# Boolean Operations
# =============================================================================

def union(*shapes: cq.Workplane) -> cq.Workplane:
    """
    Combine multiple shapes into one (boolean union).
    
    Args:
        *shapes: Two or more shapes to combine
    
    Returns:
        Combined shape containing all input geometry
    
    Raises:
        ValidationError: If fewer than 2 shapes provided
    
    Example:
        >>> from app.cad.primitives import create_box
        >>> box1 = create_box(50, 50, 50)
        >>> box2 = create_box(50, 50, 50).translate((25, 0, 0))
        >>> combined = union(box1, box2)
    """
    if len(shapes) < 2:
        raise ValidationError("Union requires at least 2 shapes")
    
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.union(shape)
    
    return result


def difference(base: cq.Workplane, *tools: cq.Workplane) -> cq.Workplane:
    """
    Subtract tools from base shape (boolean difference).
    
    Args:
        base: Shape to subtract from
        *tools: One or more shapes to subtract
    
    Returns:
        Result of subtracting all tools from base
    
    Raises:
        GeometryError: If result is empty (tools remove everything)
    
    Example:
        >>> from app.cad.primitives import create_box, create_cylinder
        >>> box = create_box(100, 100, 50)
        >>> hole = create_cylinder(10, 60)  # Taller than box to go through
        >>> box_with_hole = difference(box, hole)
    """
    if not tools:
        return base
    
    result = base
    for tool in tools:
        result = result.cut(tool)
    
    # Validate result
    try:
        volume = result.val().Volume()
        if volume <= 0:
            raise GeometryError(
                "Boolean difference resulted in empty geometry",
                details={"result_volume": volume}
            )
    except Exception as e:
        if isinstance(e, GeometryError):
            raise
        raise GeometryError(f"Failed to compute difference: {e}")
    
    return result


def intersection(*shapes: cq.Workplane) -> cq.Workplane:
    """
    Return the common volume of shapes (boolean intersection).
    
    Args:
        *shapes: Two or more shapes to intersect
    
    Returns:
        Shape containing only the volume common to all inputs
    
    Raises:
        ValidationError: If fewer than 2 shapes provided
        GeometryError: If shapes have no common volume
    
    Example:
        >>> from app.cad.primitives import create_box, create_sphere
        >>> box = create_box(100, 100, 100)
        >>> sphere = create_sphere(60)
        >>> common = intersection(box, sphere)  # Rounded box shape
    """
    if len(shapes) < 2:
        raise ValidationError("Intersection requires at least 2 shapes")
    
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.intersect(shape)
    
    # Validate result
    try:
        volume = result.val().Volume()
        if volume <= 0:
            raise GeometryError(
                "Shapes have no common volume",
                details={"result_volume": volume}
            )
    except Exception as e:
        if isinstance(e, GeometryError):
            raise
        raise GeometryError(f"Failed to compute intersection: {e}")
    
    return result


# =============================================================================
# Transformation Operations
# =============================================================================

def translate(
    shape: cq.Workplane,
    x: float = 0,
    y: float = 0,
    z: float = 0,
) -> cq.Workplane:
    """
    Move a shape by the specified offset.
    
    Args:
        shape: Shape to translate
        x: X offset in mm (default: 0)
        y: Y offset in mm (default: 0)
        z: Z offset in mm (default: 0)
    
    Returns:
        New shape at the translated position
    
    Example:
        >>> from app.cad.primitives import create_box
        >>> box = create_box(10, 10, 10)
        >>> moved = translate(box, x=50, z=25)
    """
    return shape.translate((x, y, z))


def rotate(
    shape: cq.Workplane,
    angle: float,
    axis: tuple[float, float, float] = (0, 0, 1),
    center: tuple[float, float, float] = (0, 0, 0),
) -> cq.Workplane:
    """
    Rotate a shape around an axis.
    
    Args:
        shape: Shape to rotate
        angle: Rotation angle in degrees
        axis: Rotation axis as (x, y, z) tuple (default: Z axis)
        center: Point on axis (default: origin)
    
    Returns:
        Rotated shape
    
    Example:
        >>> from app.cad.primitives import create_box
        >>> box = create_box(100, 50, 30)
        >>> rotated = rotate(box, 45)  # 45° around Z axis
    """
    return shape.rotate(center, axis, angle)


def scale(shape: cq.Workplane, factor: float) -> cq.Workplane:
    """
    Uniformly scale a shape.
    
    Args:
        shape: Shape to scale
        factor: Scale factor (1.0 = no change, 2.0 = double size)
    
    Returns:
        Scaled shape
    
    Raises:
        ValidationError: If factor <= 0
    
    Example:
        >>> from app.cad.primitives import create_box
        >>> box = create_box(10, 10, 10)
        >>> big_box = scale(box, 2.0)
        >>> big_box.val().Volume()  # 8x original (2³)
        8000.0
    """
    if factor <= 0:
        raise ValidationError(
            "Scale factor must be positive",
            details={"factor": factor}
        )
    
    if factor == 1.0:
        return shape
    
    # Use OCP for scaling transformation
    from OCP.gp import gp_Trsf, gp_Pnt
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    
    trsf = gp_Trsf()
    trsf.SetScale(gp_Pnt(0, 0, 0), factor)
    
    transformer = BRepBuilderAPI_Transform(shape.val().wrapped, trsf, True)
    return cq.Workplane(obj=cq.Shape(transformer.Shape()))


def mirror(
    shape: cq.Workplane,
    plane: str = "XY",
) -> cq.Workplane:
    """
    Mirror a shape across a plane.
    
    Args:
        shape: Shape to mirror
        plane: Plane to mirror across ("XY", "XZ", or "YZ")
    
    Returns:
        Mirrored shape
    
    Raises:
        ValidationError: If plane is invalid
    """
    plane = plane.upper()
    
    if plane == "XY":
        return shape.mirror("XY")
    elif plane == "XZ":
        return shape.mirror("XZ")
    elif plane == "YZ":
        return shape.mirror("YZ")
    else:
        raise ValidationError(
            f"Invalid mirror plane: {plane}",
            details={"valid_planes": ["XY", "XZ", "YZ"]}
        )


# =============================================================================
# Edge/Face Modifications
# =============================================================================

def fillet(
    shape: cq.Workplane,
    radius: float,
    edges: str = "all",
) -> cq.Workplane:
    """
    Apply fillet (rounded edge) to edges.
    
    Args:
        shape: Shape to fillet
        radius: Fillet radius in mm
        edges: Edge selector ("all", ">Z", "<Z", etc.)
    
    Returns:
        Filleted shape
    
    Raises:
        ValidationError: If radius <= 0
        GeometryError: If fillet radius is too large for geometry
    
    Example:
        >>> from app.cad.primitives import create_box
        >>> box = create_box(50, 50, 50)
        >>> rounded = fillet(box, 5)  # 5mm fillet on all edges
    """
    if radius <= 0:
        raise ValidationError(
            "Fillet radius must be positive",
            details={"radius": radius}
        )
    
    try:
        if edges == "all":
            return shape.edges().fillet(radius)
        else:
            return shape.edges(edges).fillet(radius)
    except Exception as e:
        raise GeometryError(
            f"Fillet operation failed (radius may be too large): {e}",
            details={"radius": radius, "edges": edges}
        )


def chamfer(
    shape: cq.Workplane,
    distance: float,
    edges: str = "all",
) -> cq.Workplane:
    """
    Apply chamfer (beveled edge) to edges.
    
    Args:
        shape: Shape to chamfer
        distance: Chamfer distance in mm
        edges: Edge selector ("all", ">Z", "<Z", etc.)
    
    Returns:
        Chamfered shape
    
    Raises:
        ValidationError: If distance <= 0
        GeometryError: If chamfer distance is too large
    
    Example:
        >>> from app.cad.primitives import create_box
        >>> box = create_box(50, 50, 50)
        >>> beveled = chamfer(box, 3)  # 3mm chamfer on all edges
    """
    if distance <= 0:
        raise ValidationError(
            "Chamfer distance must be positive",
            details={"distance": distance}
        )
    
    try:
        if edges == "all":
            return shape.edges().chamfer(distance)
        else:
            return shape.edges(edges).chamfer(distance)
    except Exception as e:
        raise GeometryError(
            f"Chamfer operation failed: {e}",
            details={"distance": distance, "edges": edges}
        )


def shell(
    shape: cq.Workplane,
    thickness: float,
    faces_to_remove: str | None = None,
) -> cq.Workplane:
    """
    Hollow out a solid, creating a shell with specified wall thickness.
    
    Args:
        shape: Solid shape to shell
        thickness: Wall thickness in mm (positive = inward, negative = outward)
        faces_to_remove: Face selector for openings (e.g., ">Z" for top)
    
    Returns:
        Shelled (hollow) shape
    
    Raises:
        ValidationError: If thickness is 0
        GeometryError: If shell operation fails
    
    Example:
        >>> from app.cad.primitives import create_box
        >>> box = create_box(50, 50, 50)
        >>> hollow = shell(box, 2, ">Z")  # Open-top box with 2mm walls
    """
    if thickness == 0:
        raise ValidationError("Shell thickness cannot be zero")
    
    try:
        if faces_to_remove:
            return shape.faces(faces_to_remove).shell(thickness)
        else:
            return shape.shell(thickness)
    except Exception as e:
        raise GeometryError(
            f"Shell operation failed: {e}",
            details={"thickness": thickness, "faces_to_remove": faces_to_remove}
        )


# =============================================================================
# Hole Operations
# =============================================================================

def add_hole(
    shape: cq.Workplane,
    diameter: float,
    depth: float | None = None,
    position: tuple[float, float] = (0, 0),
    face: str = ">Z",
) -> cq.Workplane:
    """
    Add a cylindrical hole to a shape.
    
    Args:
        shape: Shape to add hole to
        diameter: Hole diameter in mm
        depth: Hole depth in mm (None = through all)
        position: (X, Y) position on selected face
        face: Face selector for hole location
    
    Returns:
        Shape with hole added
    
    Example:
        >>> from app.cad.primitives import create_box
        >>> box = create_box(50, 50, 20)
        >>> box_with_hole = add_hole(box, 10, depth=15)  # M10 hole, 15mm deep
    """
    if diameter <= 0:
        raise ValidationError("Hole diameter must be positive")
    
    radius = diameter / 2
    
    # Select face and position
    workplane = shape.faces(face).workplane().center(position[0], position[1])
    
    if depth is None:
        # Through hole
        return workplane.hole(diameter)
    else:
        # Blind hole
        return workplane.hole(diameter, depth)
