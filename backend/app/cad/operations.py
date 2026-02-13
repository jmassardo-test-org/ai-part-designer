"""
Boolean and transformation operations for Build123d shapes.

Provides operations to combine, modify, and transform 3D geometry.

Example:
    >>> from app.cad.primitives import create_box, create_cylinder
    >>> from app.cad.operations import difference
    >>> box = create_box(100, 100, 50)
    >>> hole = create_cylinder(10, 50)
    >>> result = difference(box, hole)  # Box with hole
"""

from __future__ import annotations

from typing import Any

from build123d import (
    Axis,
    Location,
    Part,
    Plane,
)
from build123d import (
    chamfer as b3d_chamfer,
)
from build123d import (
    fillet as b3d_fillet,
)
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf

from app.cad.exceptions import GeometryError, ValidationError

# =============================================================================
# Boolean Operations
# =============================================================================


def union(*shapes: Part) -> Part:
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
        >>> box2 = create_box(50, 50, 50).move(Location((25, 0, 0)))
        >>> combined = union(box1, box2)
    """
    if len(shapes) < 2:
        raise ValidationError("Union requires at least 2 shapes")

    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)  # type: ignore[assignment]

    return result


def difference(base: Part, *tools: Part) -> Part:
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
        result = result.cut(tool)  # type: ignore[assignment]

    # Validate result
    try:
        volume = result.volume
        if volume <= 0:
            raise GeometryError(
                "Boolean difference resulted in empty geometry", details={"result_volume": volume}
            )
    except Exception as e:
        if isinstance(e, GeometryError):
            raise
        raise GeometryError(f"Failed to compute difference: {e}")

    return result


def intersection(*shapes: Part) -> Part:
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
        result = result.intersect(shape)  # type: ignore[assignment]

    # Validate result
    try:
        volume = result.volume
        if volume <= 0:
            raise GeometryError("Shapes have no common volume", details={"result_volume": volume})
    except Exception as e:
        if isinstance(e, GeometryError):
            raise
        raise GeometryError(f"Failed to compute intersection: {e}")

    return result


# =============================================================================
# Transformation Operations
# =============================================================================


def translate(
    shape: Part,
    x: float = 0,
    y: float = 0,
    z: float = 0,
) -> Part:
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
    return shape.move(Location((x, y, z)))


def rotate(
    shape: Part,
    angle: float,
    axis: tuple[float, float, float] = (0, 0, 1),
    center: tuple[float, float, float] = (0, 0, 0),
) -> Part:
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
    # Use OCP for rotation around arbitrary axis
    import math

    trsf = gp_Trsf()
    ax = gp_Ax1(gp_Pnt(center[0], center[1], center[2]), gp_Dir(axis[0], axis[1], axis[2]))
    trsf.SetRotation(ax, math.radians(angle))

    transformer = BRepBuilderAPI_Transform(shape.wrapped, trsf, True)
    return Part(transformer.Shape())


def scale(shape: Part, factor: float) -> Part:
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
        >>> big_box.volume  # 8x original (2³)
        8000.0
    """
    if factor <= 0:
        raise ValidationError("Scale factor must be positive", details={"factor": factor})

    if factor == 1.0:
        return shape

    trsf = gp_Trsf()
    trsf.SetScale(gp_Pnt(0, 0, 0), factor)

    transformer = BRepBuilderAPI_Transform(shape.wrapped, trsf, True)
    return Part(transformer.Shape())


def mirror(
    shape: Part,
    plane: str = "XY",
) -> Part:
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
        return shape.mirror(Plane.XY)
    if plane == "XZ":
        return shape.mirror(Plane.XZ)
    if plane == "YZ":
        return shape.mirror(Plane.YZ)
    raise ValidationError(
        f"Invalid mirror plane: {plane}", details={"valid_planes": ["XY", "XZ", "YZ"]}
    )


# =============================================================================
# Edge/Face Modifications
# =============================================================================


def fillet(
    shape: Part,
    radius: float,
    edges: str = "all",
) -> Part:
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
        raise ValidationError("Fillet radius must be positive", details={"radius": radius})

    try:
        if edges == "all":
            # Use module-level fillet function to avoid type issues with Box/Cylinder
            return b3d_fillet(shape.edges(), radius)
        # Parse edge selector
        selected_edges = _select_edges(shape, edges)
        return b3d_fillet(selected_edges, radius)
    except Exception as e:
        raise GeometryError(
            f"Fillet operation failed (radius may be too large): {e}",
            details={"radius": radius, "edges": edges},
        )


def chamfer(
    shape: Part,
    distance: float,
    edges: str = "all",
) -> Part:
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
        raise ValidationError("Chamfer distance must be positive", details={"distance": distance})

    try:
        if edges == "all":
            # Use module-level chamfer function to avoid type issues with Box/Cylinder
            return b3d_chamfer(shape.edges(), distance)
        selected_edges = _select_edges(shape, edges)
        return b3d_chamfer(selected_edges, distance)
    except Exception as e:
        raise GeometryError(
            f"Chamfer operation failed: {e}", details={"distance": distance, "edges": edges}
        )


def shell(
    shape: Part,
    thickness: float,
    faces_to_remove: str | None = None,
) -> Part:
    """
    Hollow out a solid, creating a shell with specified wall thickness.

    Uses Build123d's offset function to create hollow geometry.

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
    from build123d import offset

    if thickness == 0:
        raise ValidationError("Shell thickness cannot be zero")

    try:
        # Build123d uses offset() for shell operations
        # Negative offset creates inward shell (walls inside original)
        # Positive offset creates outward shell (walls outside original)
        offset_amount = -abs(thickness) if thickness > 0 else abs(thickness)

        if faces_to_remove:
            open_faces = _select_faces(shape, faces_to_remove)
            return offset(shape, offset_amount, openings=open_faces)
        return offset(shape, offset_amount)
    except Exception as e:
        raise GeometryError(
            f"Shell operation failed: {e}",
            details={"thickness": thickness, "faces_to_remove": faces_to_remove},
        )


# =============================================================================
# Hole Operations
# =============================================================================


def add_hole(
    shape: Part,
    diameter: float,
    depth: float | None = None,
    position: tuple[float, float] = (0, 0),
    face: str = ">Z",
) -> Part:
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
        >>> box_with_hole = add_hole(box, 10, depth=15)  # 10mm diameter hole, 15mm deep
    """
    if diameter <= 0:
        raise ValidationError("Hole diameter must be positive")

    from build123d import Align, Location
    from build123d import Cylinder as B3dCylinder

    radius = diameter / 2

    # Get the bounding box to determine hole depth if not specified
    bb = shape.bounding_box()
    if depth is None:
        depth = bb.size.Z + 2  # Through all plus margin

    # Create hole cylinder aligned at bottom (MIN Z)
    # This makes positioning easier - hole extends upward from its base
    hole = B3dCylinder(radius, depth, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # Position the hole based on face selector
    if face == ">Z":
        # Hole from top face going down
        hole = hole.move(Location((position[0], position[1], bb.max.Z - depth)))
    elif face == "<Z":
        # Hole from bottom face going up (but start below to ensure clean cut)
        hole = hole.move(Location((position[0], position[1], bb.min.Z - 1)))
    else:
        # Default to top face
        hole = hole.move(Location((position[0], position[1], bb.max.Z - depth)))

    return shape.cut(hole)  # type: ignore[return-value]


# =============================================================================
# Helper Functions
# =============================================================================


def _select_edges(shape: Part, selector: str) -> Any:
    """
    Select edges based on a selector string.

    Args:
        shape: Shape to select edges from
        selector: Edge selector (">Z", "<Z", "|Z", etc.)

    Returns:
        List of selected edges
    """
    all_edges = shape.edges()

    if selector.startswith(">"):
        axis = selector[1]
        if axis == "Z":
            return all_edges.filter_by(Axis.Z).sort_by(Axis.Z)[-1:]
        if axis == "Y":
            return all_edges.filter_by(Axis.Y).sort_by(Axis.Y)[-1:]
        if axis == "X":
            return all_edges.filter_by(Axis.X).sort_by(Axis.X)[-1:]
    elif selector.startswith("<"):
        axis = selector[1]
        if axis == "Z":
            return all_edges.filter_by(Axis.Z).sort_by(Axis.Z)[:1]
        if axis == "Y":
            return all_edges.filter_by(Axis.Y).sort_by(Axis.Y)[:1]
        if axis == "X":
            return all_edges.filter_by(Axis.X).sort_by(Axis.X)[:1]
    elif selector.startswith("|"):
        axis = selector[1]
        if axis == "Z":
            return all_edges.filter_by(Axis.Z)
        if axis == "Y":
            return all_edges.filter_by(Axis.Y)
        if axis == "X":
            return all_edges.filter_by(Axis.X)

    return all_edges


def _select_faces(shape: Part, selector: str) -> Any:
    """
    Select faces based on a selector string.

    Args:
        shape: Shape to select faces from
        selector: Face selector (">Z", "<Z", etc.)

    Returns:
        List of selected faces
    """
    all_faces = shape.faces()

    if selector.startswith(">"):
        axis = selector[1]
        if axis == "Z":
            return all_faces.sort_by(Axis.Z)[-1:]
        if axis == "Y":
            return all_faces.sort_by(Axis.Y)[-1:]
        if axis == "X":
            return all_faces.sort_by(Axis.X)[-1:]
    elif selector.startswith("<"):
        axis = selector[1]
        if axis == "Z":
            return all_faces.sort_by(Axis.Z)[:1]
        if axis == "Y":
            return all_faces.sort_by(Axis.Y)[:1]
        if axis == "X":
            return all_faces.sort_by(Axis.X)[:1]

    return all_faces
