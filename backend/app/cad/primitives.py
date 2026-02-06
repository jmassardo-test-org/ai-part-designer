"""
CAD primitive generation using Build123d.

Provides parameterized 3D shape creation for basic primitives.
All dimensions are in millimeters unless otherwise specified.

NOTE: Due to OCP 7.9.3 compatibility issues, we use direct object creation
instead of BuildPart context managers. The HashCode API changed in OCP 7.9.x.

Example:
    >>> from app.cad.primitives import create_box
    >>> box = create_box(100, 50, 30)
    >>> box.volume
    150000.0
"""

from __future__ import annotations

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    Hole,
    Location,
    Locations,
    Mode,
    Part,
    Wedge,
)
from build123d import (
    Cone as B3dCone,
)
from build123d import (
    Cylinder as B3dCylinder,
)
from build123d import (
    Sphere as B3dSphere,
)
from build123d import (
    Torus as B3dTorus,
)
from build123d import (
    fillet as b3d_fillet,
)

from app.cad.exceptions import ValidationError


def create_box(
    length: float,
    width: float,
    height: float,
    *,
    centered: bool = True,
) -> Part:
    """
    Create a box (rectangular prism) primitive.

    The box is created on the XY plane with the bottom face at Z=0.

    Args:
        length: Box length in mm (X axis)
        width: Box width in mm (Y axis)
        height: Box height in mm (Z axis)
        centered: If True, center on XY plane; if False, corner at origin

    Returns:
        Build123d Part containing the box

    Raises:
        ValidationError: If any dimension is <= 0

    Example:
        >>> box = create_box(100, 50, 30)
        >>> bb = box.bounding_box()
        >>> bb.size.X, bb.size.Y, bb.size.Z
        (100.0, 50.0, 30.0)
    """
    _validate_positive_dimensions(length=length, width=width, height=height)

    align = (
        (Align.CENTER, Align.CENTER, Align.MIN) if centered else (Align.MIN, Align.MIN, Align.MIN)
    )

    # Direct object creation (avoids BuildPart context manager OCP compatibility issues)
    return Box(length, width, height, align=align)


def create_cylinder(
    radius: float,
    height: float,
    *,
    centered: bool = True,
) -> Part:
    """
    Create a cylinder primitive.

    The cylinder is created with its axis along Z, base at Z=0.

    Args:
        radius: Cylinder radius in mm
        height: Cylinder height in mm (Z axis)
        centered: If True, center on XY plane; if False, edge at origin

    Returns:
        Build123d Part containing the cylinder

    Raises:
        ValidationError: If radius or height is <= 0

    Example:
        >>> cyl = create_cylinder(25, 50)
        >>> import math
        >>> expected_volume = math.pi * 25**2 * 50
        >>> abs(cyl.volume - expected_volume) < 1  # Within 1mm³
        True
    """
    _validate_positive_dimensions(radius=radius, height=height)

    align = (
        (Align.CENTER, Align.CENTER, Align.MIN) if centered else (Align.MIN, Align.MIN, Align.MIN)
    )

    # Direct object creation (avoids BuildPart context manager OCP compatibility issues)
    return B3dCylinder(radius, height, align=align)


def create_sphere(
    radius: float,
    *,
    centered: bool = True,
) -> Part:
    """
    Create a sphere primitive.

    Args:
        radius: Sphere radius in mm
        centered: If True, center at origin; if False, place tangent to XY at Z=0

    Returns:
        Build123d Part containing the sphere

    Raises:
        ValidationError: If radius is <= 0

    Example:
        >>> sphere = create_sphere(25)
        >>> import math
        >>> expected_volume = (4/3) * math.pi * 25**3
        >>> abs(sphere.volume - expected_volume) < 10  # Within 10mm³
        True
    """
    _validate_positive_dimensions(radius=radius)

    # Direct object creation (avoids BuildPart context manager OCP compatibility issues)
    sphere = B3dSphere(radius)
    if not centered:
        # Move sphere up so it sits on XY plane
        sphere = sphere.move(Location((0, 0, radius)))

    return sphere


def create_cone(
    radius_bottom: float,
    radius_top: float,
    height: float,
    *,
    centered: bool = True,
) -> Part:
    """
    Create a cone or truncated cone (frustum) primitive.

    Args:
        radius_bottom: Bottom radius in mm (at Z=0)
        radius_top: Top radius in mm (0 for pointed cone)
        height: Height in mm (Z axis)
        centered: If True, center on XY plane

    Returns:
        Build123d Part containing the cone

    Raises:
        ValidationError: If height <= 0 or both radii are 0

    Example:
        >>> cone = create_cone(25, 0, 50)  # Pointed cone
        >>> cone.volume > 0
        True
    """
    _validate_positive_dimensions(height=height)

    if radius_bottom < 0 or radius_top < 0:
        raise ValidationError("Radii must be non-negative")

    if radius_bottom == 0 and radius_top == 0:
        raise ValidationError("At least one radius must be positive")

    align = (
        (Align.CENTER, Align.CENTER, Align.MIN) if centered else (Align.MIN, Align.MIN, Align.MIN)
    )

    # Direct object creation (avoids BuildPart context manager OCP compatibility issues)
    return B3dCone(radius_bottom, radius_top, height, align=align)


def create_torus(
    major_radius: float,
    minor_radius: float,
    *,
    _centered: bool = True,
) -> Part:
    """
    Create a torus (donut shape) primitive.

    Args:
        major_radius: Distance from center of torus to center of tube (mm)
        minor_radius: Radius of the tube (mm)
        centered: If True, center at origin

    Returns:
        Build123d Part containing the torus

    Raises:
        ValidationError: If any radius is <= 0 or minor >= major
    """
    _validate_positive_dimensions(major_radius=major_radius, minor_radius=minor_radius)

    if minor_radius >= major_radius:
        raise ValidationError(
            "Minor radius must be less than major radius",
            details={"major_radius": major_radius, "minor_radius": minor_radius},
        )

    # Direct object creation (avoids BuildPart context manager OCP compatibility issues)
    return B3dTorus(major_radius, minor_radius)


def create_wedge(
    length: float,
    width: float,
    height: float,
    *,
    centered: bool = True,
) -> Part:
    """
    Create a wedge (triangular prism) primitive.

    The wedge has a rectangular base and slopes to a line at the top.

    Args:
        length: Wedge length in mm (X axis)
        width: Wedge width in mm (Y axis)
        height: Wedge height in mm (Z axis)
        centered: If True, center on XY plane

    Returns:
        Build123d Part containing the wedge
    """
    _validate_positive_dimensions(length=length, width=width, height=height)

    # Direct object creation (avoids BuildPart context manager OCP compatibility issues)
    # Wedge requires: xsize, ysize, zsize, xmin, zmin, xmax, zmax
    # For a standard wedge that goes from full width at base to a line at top:
    # xmin=0 (start of top edge at x=0), zmin=height (top edge at z=height)
    # xmax=length (end of top edge at x=length), zmax=height (same height)
    align = (
        (Align.CENTER, Align.CENTER, Align.MIN) if centered else (Align.MIN, Align.MIN, Align.MIN)
    )

    # Create a wedge that slopes from full base to a line at the top
    return Wedge(
        xsize=length,
        ysize=width,
        zsize=height,
        xmin=0,  # Top edge starts at x=0
        zmin=height,  # Top edge is at full height
        xmax=length,  # Top edge ends at x=length
        zmax=height,  # Top edge stays at full height
        align=align,
    )


def _validate_positive_dimensions(**dimensions: float) -> None:
    """
    Validate that all dimensions are positive.

    Args:
        **dimensions: Named dimension values to validate

    Raises:
        ValidationError: If any dimension is <= 0
    """
    invalid = {name: value for name, value in dimensions.items() if value <= 0}

    if invalid:
        names = ", ".join(invalid.keys())
        raise ValidationError(
            f"Dimensions must be positive: {names}", details={"invalid_dimensions": invalid}
        )


def create_l_bracket(
    leg_length: float,
    width: float,
    thickness: float,
    *,
    holes_per_flange: int = 0,
    hole_diameter: float = 5.0,
    hole_offset: float = 10.0,
    fillet_radius: float = 0.0,
) -> Part:
    """
    Create an L-bracket (angle bracket) with optional holes and fillets.

    The bracket has two equal perpendicular flanges meeting at a corner.

    Args:
        leg_length: Length of each flange leg in mm
        width: Width of the bracket (both flanges) in mm
        thickness: Material thickness in mm
        holes_per_flange: Number of holes per flange (0, 2, or 4)
        hole_diameter: Diameter of holes in mm
        hole_offset: Distance from edge to hole center in mm
        fillet_radius: Radius of fillets on outer corners (0 = no fillet)

    Returns:
        Build123d Part containing the L-bracket

    Example:
        >>> bracket = create_l_bracket(50, 50, 3, holes_per_flange=4, hole_diameter=5, hole_offset=10, fillet_radius=5)
    """
    _validate_positive_dimensions(leg_length=leg_length, width=width, thickness=thickness)

    with BuildPart() as part:
        # Create horizontal flange (on XY plane, extends in +X direction)
        with Location((leg_length / 2, 0, thickness / 2)):
            Box(leg_length, width, thickness)

        # Create vertical flange (perpendicular, extends in +Z direction)
        with Location((thickness / 2, 0, leg_length / 2)):
            Box(thickness, width, leg_length)

        # Add holes if requested
        if holes_per_flange > 0:
            # Calculate hole positions based on count
            if holes_per_flange == 2:
                h_hole_y = [0]
                h_hole_x = [hole_offset, leg_length - hole_offset]
            elif holes_per_flange >= 4:
                half_width_offset = (width / 2) - hole_offset
                h_hole_y = [half_width_offset, -half_width_offset]
                h_hole_x = [hole_offset, leg_length - hole_offset]
            else:
                h_hole_y = []
                h_hole_x = []

            # Holes on horizontal flange
            if h_hole_x and h_hole_y:
                for x in h_hole_x:
                    for y in h_hole_y:
                        with Location((x, y, thickness)):
                            Hole(hole_diameter / 2, thickness + 1)

            # Holes on vertical flange
            if holes_per_flange >= 2:
                if holes_per_flange == 2:
                    v_hole_y = [0]
                    v_hole_z = [hole_offset + thickness, leg_length - hole_offset]
                else:
                    half_width_offset = (width / 2) - hole_offset
                    v_hole_y = [half_width_offset, -half_width_offset]
                    v_hole_z = [hole_offset + thickness, leg_length - hole_offset]

                for z in v_hole_z:
                    for y in v_hole_y:
                        with Locations((0, y, z)):
                            Hole(hole_diameter / 2, thickness + 1, mode=Mode.SUBTRACT)

        # Add fillets on outer edges if requested
        if fillet_radius > 0:
            try:
                edges_to_fillet = part.edges().filter_by(Axis.Z)
                b3d_fillet(edges_to_fillet, min(fillet_radius, thickness * 0.8))
            except Exception:
                pass  # Skip fillet if it fails

    return part.part  # type: ignore[no-any-return]
