"""
CAD primitive generation using CadQuery.

Provides parameterized 3D shape creation for basic primitives.
All dimensions are in millimeters unless otherwise specified.

Example:
    >>> from app.cad.primitives import create_box
    >>> box = create_box(100, 50, 30)
    >>> box.val().Volume()
    150000.0
"""

from __future__ import annotations

import cadquery as cq

from app.cad.exceptions import ValidationError


def create_box(
    length: float,
    width: float,
    height: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a box (rectangular prism) primitive.
    
    The box is created on the XY plane with the bottom face at Z=0.
    
    Args:
        length: Box length in mm (X axis)
        width: Box width in mm (Y axis)
        height: Box height in mm (Z axis)
        centered: If True, center on XY plane; if False, corner at origin
    
    Returns:
        CadQuery Workplane containing the box
    
    Raises:
        ValidationError: If any dimension is <= 0
    
    Example:
        >>> box = create_box(100, 50, 30)
        >>> bb = box.val().BoundingBox()
        >>> bb.xlen, bb.ylen, bb.zlen
        (100.0, 50.0, 30.0)
    """
    _validate_positive_dimensions(length=length, width=width, height=height)
    
    return cq.Workplane("XY").box(
        length, 
        width, 
        height, 
        centered=(centered, centered, False)
    )


def create_cylinder(
    radius: float,
    height: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a cylinder primitive.
    
    The cylinder is created with its axis along Z, base at Z=0.
    
    Args:
        radius: Cylinder radius in mm
        height: Cylinder height in mm (Z axis)
        centered: If True, center on XY plane; if False, edge at origin
    
    Returns:
        CadQuery Workplane containing the cylinder
    
    Raises:
        ValidationError: If radius or height is <= 0
    
    Example:
        >>> cyl = create_cylinder(25, 50)
        >>> import math
        >>> expected_volume = math.pi * 25**2 * 50
        >>> abs(cyl.val().Volume() - expected_volume) < 1  # Within 1mm³
        True
    """
    _validate_positive_dimensions(radius=radius, height=height)
    
    return cq.Workplane("XY").cylinder(
        height,
        radius,
        centered=(centered, centered, False)
    )


def create_sphere(
    radius: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a sphere primitive.
    
    Args:
        radius: Sphere radius in mm
        centered: If True, center at origin; if False, place tangent to XY at Z=0
    
    Returns:
        CadQuery Workplane containing the sphere
    
    Raises:
        ValidationError: If radius is <= 0
    
    Example:
        >>> sphere = create_sphere(25)
        >>> import math
        >>> expected_volume = (4/3) * math.pi * 25**3
        >>> abs(sphere.val().Volume() - expected_volume) < 10  # Within 10mm³
        True
    """
    _validate_positive_dimensions(radius=radius)
    
    sphere = cq.Workplane("XY").sphere(radius)
    
    if not centered:
        # Move sphere up so it sits on XY plane
        sphere = sphere.translate((0, 0, radius))
    
    return sphere


def create_cone(
    radius_bottom: float,
    radius_top: float,
    height: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a cone or truncated cone (frustum) primitive.
    
    Args:
        radius_bottom: Bottom radius in mm (at Z=0)
        radius_top: Top radius in mm (0 for pointed cone)
        height: Height in mm (Z axis)
        centered: If True, center on XY plane
    
    Returns:
        CadQuery Workplane containing the cone
    
    Raises:
        ValidationError: If height <= 0 or both radii are 0
    
    Example:
        >>> cone = create_cone(25, 0, 50)  # Pointed cone
        >>> cone.val().Volume() > 0
        True
    """
    _validate_positive_dimensions(height=height)
    
    if radius_bottom < 0 or radius_top < 0:
        raise ValidationError("Radii must be non-negative")
    
    if radius_bottom == 0 and radius_top == 0:
        raise ValidationError("At least one radius must be positive")
    
    # Use loft between circles
    if radius_top == 0:
        # Simple cone - use a very small top circle
        top_radius = 0.001
    else:
        top_radius = radius_top
    
    if radius_bottom == 0:
        # Inverted cone
        bottom_radius = 0.001
    else:
        bottom_radius = radius_bottom
    
    result = (
        cq.Workplane("XY")
        .circle(bottom_radius)
        .workplane(offset=height)
        .circle(top_radius)
        .loft()
    )
    
    if not centered:
        return result
    
    # Center on XY - loft is already centered on Z
    return result


def create_torus(
    major_radius: float,
    minor_radius: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a torus (donut shape) primitive.
    
    Args:
        major_radius: Distance from center of torus to center of tube (mm)
        minor_radius: Radius of the tube (mm)
        centered: If True, center at origin
    
    Returns:
        CadQuery Workplane containing the torus
    
    Raises:
        ValidationError: If any radius is <= 0 or minor >= major
    """
    _validate_positive_dimensions(major_radius=major_radius, minor_radius=minor_radius)
    
    if minor_radius >= major_radius:
        raise ValidationError(
            "Minor radius must be less than major radius",
            details={"major_radius": major_radius, "minor_radius": minor_radius}
        )
    
    # Create circle and revolve around Y axis
    result = (
        cq.Workplane("XZ")
        .center(major_radius, 0)
        .circle(minor_radius)
        .revolve(360, (0, 0, 0), (0, 0, 1))
    )
    
    return result


def create_wedge(
    length: float,
    width: float,
    height: float,
    *,
    centered: bool = True,
) -> cq.Workplane:
    """
    Create a wedge (triangular prism) primitive.
    
    The wedge has a rectangular base and slopes to a line at the top.
    
    Args:
        length: Wedge length in mm (X axis)
        width: Wedge width in mm (Y axis)
        height: Wedge height in mm (Z axis)
        centered: If True, center on XY plane
    
    Returns:
        CadQuery Workplane containing the wedge
    """
    _validate_positive_dimensions(length=length, width=width, height=height)
    
    half_length = length / 2 if centered else 0
    half_width = width / 2 if centered else 0
    
    # Define triangular cross-section and extrude
    pts = [
        (-half_length, 0),
        (length - half_length, 0),
        (length - half_length, height),
        (-half_length, 0),
    ]
    
    result = (
        cq.Workplane("XZ")
        .center(0, 0)
        .polyline(pts)
        .close()
        .extrude(width if not centered else width / 2, both=centered)
    )
    
    return result


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
            f"Dimensions must be positive: {names}",
            details={"invalid_dimensions": invalid}
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
) -> cq.Workplane:
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
        CadQuery Workplane containing the L-bracket
    
    Example:
        >>> bracket = create_l_bracket(50, 50, 3, holes_per_flange=4, hole_diameter=5, hole_offset=10, fillet_radius=5)
    """
    _validate_positive_dimensions(leg_length=leg_length, width=width, thickness=thickness)
    
    # Create horizontal flange (on XY plane, extends in +X direction)
    # The flange starts at X=0 and extends to X=leg_length
    h_flange = (
        cq.Workplane("XY")
        .box(leg_length, width, thickness, centered=False)
        .translate((0, -width/2, 0))
    )
    
    # Create vertical flange (perpendicular, extends in +Z direction)
    # The flange shares the back edge with the horizontal flange
    v_flange = (
        cq.Workplane("XY")
        .box(thickness, width, leg_length, centered=False)
        .translate((0, -width/2, 0))
    )
    
    # Union the flanges
    bracket = h_flange.union(v_flange)
    
    # Add holes if requested
    if holes_per_flange > 0:
        # Calculate hole positions based on count
        # Holes are positioned at 'hole_offset' from each edge
        if holes_per_flange == 2:
            # 2 holes per flange - centered on width, offset from edges
            h_hole_y = [0]  # Center on width
            h_hole_x = [hole_offset, leg_length - hole_offset]
        elif holes_per_flange >= 4:
            # 4 holes per flange - 2x2 grid pattern
            half_width_offset = (width / 2) - hole_offset
            h_hole_y = [half_width_offset, -half_width_offset]
            h_hole_x = [hole_offset, leg_length - hole_offset]
        else:
            h_hole_y = []
            h_hole_x = []
        
        # Holes on horizontal flange (top face at Z=thickness)
        if h_hole_x and h_hole_y:
            h_points = [(x, y) for x in h_hole_x for y in h_hole_y]
            # Select face at Z=thickness (top of horizontal flange, not top of bracket)
            bracket = (
                bracket
                .faces(cq.NearestToPointSelector((leg_length/2, 0, thickness)))
                .workplane()
                .pushPoints(h_points)
                .hole(hole_diameter)
            )
        
        # Holes on vertical flange (outer face at X=0)
        if holes_per_flange >= 2:
            if holes_per_flange == 2:
                v_hole_y = [0]
                v_hole_z = [hole_offset + thickness, leg_length - hole_offset]
            else:
                half_width_offset = (width / 2) - hole_offset
                v_hole_y = [half_width_offset, -half_width_offset]
                v_hole_z = [hole_offset + thickness, leg_length - hole_offset]
            
            v_points = [(y, z) for z in v_hole_z for y in v_hole_y]
            # Select face at X=0 (outer face of vertical flange)
            bracket = (
                bracket
                .faces(cq.NearestToPointSelector((0, 0, leg_length/2)))
                .workplane()
                .pushPoints(v_points)
                .hole(hole_diameter)
            )
    
    # Add fillets on outer corners if requested
    if fillet_radius > 0:
        try:
            # Fillet vertical edges (outer corners of flanges)
            bracket = bracket.edges("|Z").fillet(min(fillet_radius, thickness * 0.8))
        except Exception:
            # If fillet fails, try smaller radius
            try:
                bracket = bracket.edges("|Z").fillet(fillet_radius * 0.5)
            except Exception:
                pass  # Skip fillet if it fails
    
    return bracket
