"""
Gridfinity Pattern Generator.

Gridfinity is a modular storage system designed by Zack Freedman.
Standard base grid: 42mm x 42mm units
Standard height: 7mm unit height

This module provides generators for:
- Base plates
- Storage bins/boxes
- Dividers
- Custom inserts

Migrated from CadQuery to Build123d.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from build123d import (
    Box, Cylinder, Location, Part,
    Axis, Align, fillet, chamfer,
    Sphere, Pos, Locations, GridLocations,
    Sketch, Circle, Rectangle, BuildSketch, extrude,
    Plane, add, offset, loft
)
import math

from app.cad.templates import register_template


# =============================================================================
# Gridfinity Constants
# =============================================================================

# Core grid dimensions (standard Gridfinity)
GRID_UNIT = 42.0  # mm - base unit size
HEIGHT_UNIT = 7.0  # mm - height unit
BASE_HEIGHT = 5.0  # mm - height of the base profile
STACKING_LIP_HEIGHT = 4.2  # mm
TOLERANCE = 0.25  # mm - fit tolerance

# Base profile dimensions
BASE_OUTER_RADIUS = 3.75  # mm
BASE_INNER_RADIUS = 2.4  # mm
BASE_FILLET = 0.6  # mm


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class GridfinityBaseParams:
    """Parameters for Gridfinity base plate."""
    
    # Grid dimensions
    grid_x: int = 3  # Number of grid units in X
    grid_y: int = 2  # Number of grid units in Y
    
    # Options
    magnet_holes: bool = True
    magnet_diameter: float = 6.5  # mm - for 6mm magnets with tolerance
    magnet_depth: float = 2.4  # mm
    screw_holes: bool = False
    screw_diameter: float = 3.0  # mm
    
    # Material
    wall_thickness: float = 2.0  # mm


@dataclass
class GridfinityBinParams:
    """Parameters for Gridfinity storage bin."""
    
    # Grid dimensions
    grid_x: int = 1  # Number of grid units in X
    grid_y: int = 1  # Number of grid units in Y
    height_units: int = 3  # Height in 7mm units
    
    # Interior options
    dividers_x: int = 0  # Internal dividers in X direction
    dividers_y: int = 0  # Internal dividers in Y direction
    
    # Features
    label_tab: bool = False
    label_angle: float = 45.0  # degrees
    stacking_lip: bool = True
    scoop: bool = False  # Finger scoop for easy access
    
    # Wall properties
    wall_thickness: float = 1.2  # mm
    floor_thickness: float = 1.0  # mm


@dataclass
class GridfinityDividerParams:
    """Parameters for Gridfinity bin divider insert."""
    
    # Grid dimensions
    grid_x: int = 1
    grid_y: int = 1
    height_units: int = 3
    
    # Divider grid
    cells_x: int = 2  # Number of cells in X
    cells_y: int = 2  # Number of cells in Y
    
    # Properties
    wall_thickness: float = 1.0  # mm
    floor_thickness: float = 1.0  # mm


# =============================================================================
# Base Plate Generator
# =============================================================================

def _create_base_profile(width: float, depth: float) -> Part:
    """Create the Gridfinity base profile for a single grid unit."""
    # Create the characteristic Gridfinity stepped base profile
    # This is a simplified version - the full spec has more complex geometry
    
    # Main base body
    result = Box(
        width - TOLERANCE * 2, 
        depth - TOLERANCE * 2, 
        BASE_HEIGHT,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    
    # Apply fillet to vertical edges
    vertical_edges = result.edges().filter_by(Axis.Z)
    if vertical_edges:
        try:
            result = fillet(vertical_edges, min(BASE_OUTER_RADIUS, (width - TOLERANCE * 2) / 4))
        except Exception:
            pass  # Skip if fillet fails
    
    # Add the rim profile
    rim_height = 0.8
    rim_offset = 0.4
    
    rim = Box(
        width - rim_offset * 2, 
        depth - rim_offset * 2, 
        rim_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    ).moved(Location((0, 0, BASE_HEIGHT)))
    
    result = result.fuse(rim)
    
    # Fillet rim edges
    rim_edges = result.edges().filter_by(Axis.Z).filter_by(
        lambda e: e.center().Z > BASE_HEIGHT
    )
    if rim_edges:
        try:
            result = fillet(rim_edges, min(BASE_OUTER_RADIUS - rim_offset, rim_height / 2))
        except Exception:
            pass  # Skip if fillet fails
    
    return result


@register_template("gridfinity-baseplate")
def generate_gridfinity_baseplate(
    grid_x: int = 3,
    grid_y: int = 2,
    magnet_holes: bool = True,
    magnet_diameter: float = 6.5,
    magnet_depth: float = 2.4,
    screw_holes: bool = False,
    screw_diameter: float = 3.0,
    wall_thickness: float = 2.0,
    **_kwargs: Any,
) -> Part:
    """
    Generate a Gridfinity base plate.
    
    The base plate provides a stable mounting surface for bins.
    It features the characteristic grid of receptacles.
    
    Args:
        grid_x: Number of grid units in X direction
        grid_y: Number of grid units in Y direction
        magnet_holes: Whether to include magnet mounting holes
        magnet_diameter: Diameter of magnet holes
        magnet_depth: Depth of magnet holes
        screw_holes: Whether to include screw mounting holes
        screw_diameter: Diameter of screw holes
        wall_thickness: Thickness of base plate walls
        
    Returns:
        Build123d Part with the base plate
    """
    outer_x = grid_x * GRID_UNIT
    outer_y = grid_y * GRID_UNIT
    base_thickness = wall_thickness + BASE_HEIGHT
    
    # Create outer shell
    result = Box(
        outer_x, outer_y, base_thickness,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    
    # Fillet vertical edges
    vertical_edges = result.edges().filter_by(Axis.Z)
    if vertical_edges:
        try:
            result = fillet(vertical_edges, min(BASE_OUTER_RADIUS, outer_x / 10))
        except Exception:
            pass  # Skip if fillet fails
    
    # Create grid of receptacles (pockets for bins to sit in)
    receptacle_depth = BASE_HEIGHT - 0.5
    receptacle_size = GRID_UNIT - wall_thickness * 2
    
    for ix in range(grid_x):
        for iy in range(grid_y):
            # Calculate center of this grid cell
            cx = (ix + 0.5) * GRID_UNIT - outer_x / 2
            cy = (iy + 0.5) * GRID_UNIT - outer_y / 2
            
            # Cut receptacle pocket
            pocket = Box(
                receptacle_size, receptacle_size, receptacle_depth,
                align=(Align.CENTER, Align.CENTER, Align.MAX)
            ).moved(Location((cx, cy, base_thickness)))
            result = result.cut(pocket)
            
            # Add magnet holes if requested
            if magnet_holes:
                for mx, my in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    magnet_x = cx + mx * (receptacle_size / 2 - 4)
                    magnet_y = cy + my * (receptacle_size / 2 - 4)
                    
                    magnet_hole = Cylinder(
                        magnet_diameter / 2, magnet_depth,
                        align=(Align.CENTER, Align.CENTER, Align.MAX)
                    ).moved(Location((magnet_x, magnet_y, base_thickness)))
                    result = result.cut(magnet_hole)
            
            # Add screw holes if requested
            if screw_holes:
                screw_hole = Cylinder(
                    screw_diameter / 2, base_thickness,
                    align=(Align.CENTER, Align.CENTER, Align.MIN)
                ).moved(Location((cx, cy, 0)))
                result = result.cut(screw_hole)
    
    return result


# =============================================================================
# Storage Bin Generator
# =============================================================================

@register_template("gridfinity-bin")
def generate_gridfinity_bin(
    grid_x: int = 1,
    grid_y: int = 1,
    height_units: int = 3,
    dividers_x: int = 0,
    dividers_y: int = 0,
    label_tab: bool = False,
    label_angle: float = 45.0,
    stacking_lip: bool = True,
    scoop: bool = False,
    wall_thickness: float = 1.2,
    floor_thickness: float = 1.0,
    **_kwargs: Any,
) -> Part:
    """
    Generate a Gridfinity storage bin.
    
    Standard modular bin that fits on a Gridfinity base plate.
    
    Args:
        grid_x: Number of grid units in X direction
        grid_y: Number of grid units in Y direction
        height_units: Height in 7mm units
        dividers_x: Number of internal dividers in X direction
        dividers_y: Number of internal dividers in Y direction
        label_tab: Whether to include a label tab
        label_angle: Angle of the label tab
        stacking_lip: Whether to include stacking lip
        scoop: Whether to include finger scoop
        wall_thickness: Wall thickness
        floor_thickness: Floor thickness
        
    Returns:
        Build123d Part with the bin
    """
    # Calculate dimensions
    outer_x = grid_x * GRID_UNIT - TOLERANCE * 2
    outer_y = grid_y * GRID_UNIT - TOLERANCE * 2
    outer_height = height_units * HEIGHT_UNIT
    
    inner_x = outer_x - wall_thickness * 2
    inner_y = outer_y - wall_thickness * 2
    inner_height = outer_height - floor_thickness
    
    # Create outer shell
    result = Box(
        outer_x, outer_y, outer_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    
    # Fillet vertical edges
    fillet_radius = min(BASE_OUTER_RADIUS - TOLERANCE, outer_x / 10)
    if fillet_radius > 0:
        vertical_edges = result.edges().filter_by(Axis.Z)
        if vertical_edges:
            try:
                result = fillet(vertical_edges, fillet_radius)
            except Exception:
                pass
    
    # Hollow out interior
    interior = Box(
        inner_x, inner_y, inner_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN)
    ).moved(Location((0, 0, floor_thickness)))
    result = result.cut(interior)
    
    # Add base profile (the part that fits into the baseplate)
    base_profile = Box(
        outer_x - 0.5, outer_y - 0.5, BASE_HEIGHT,
        align=(Align.CENTER, Align.CENTER, Align.MAX)
    ).moved(Location((0, 0, 0)))
    result = result.fuse(base_profile)
    
    # Fillet base profile edges
    base_fillet = min(BASE_INNER_RADIUS, (outer_x - 0.5) / 10)
    if base_fillet > 0:
        base_edges = result.edges().filter_by(Axis.Z).filter_by(
            lambda e: e.center().Z < 0
        )
        if base_edges:
            try:
                result = fillet(base_edges, base_fillet)
            except Exception:
                pass
    
    # Add stepped bottom profile
    step_height = 0.5
    step = Box(
        outer_x - 1.5, outer_y - 1.5, step_height,
        align=(Align.CENTER, Align.CENTER, Align.MAX)
    ).moved(Location((0, 0, -BASE_HEIGHT + 1.8 + step_height)))
    result = result.fuse(step)
    
    # Add dividers if requested
    if dividers_x > 0 or dividers_y > 0:
        divider_thickness = 1.0
        divider_height = inner_height - 2  # Leave some clearance
        
        # X dividers (walls running in X direction, dividing Y)
        if dividers_y > 0:
            spacing_y = inner_y / (dividers_y + 1)
            for i in range(1, dividers_y + 1):
                div_y = -inner_y / 2 + i * spacing_y
                divider = Box(
                    inner_x, divider_thickness, divider_height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN)
                ).moved(Location((0, div_y, floor_thickness)))
                result = result.fuse(divider)
        
        # Y dividers (walls running in Y direction, dividing X)
        if dividers_x > 0:
            spacing_x = inner_x / (dividers_x + 1)
            for i in range(1, dividers_x + 1):
                div_x = -inner_x / 2 + i * spacing_x
                divider = Box(
                    divider_thickness, inner_y, divider_height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN)
                ).moved(Location((div_x, 0, floor_thickness)))
                result = result.fuse(divider)
        
    # Add stacking lip if requested
    if stacking_lip:
        lip_width = 1.2
        
        # Outer lip shell
        lip_outer = Box(
            outer_x, outer_y, STACKING_LIP_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN)
        ).moved(Location((0, 0, outer_height)))
        
        # Cut inner part of lip
        lip_inner = Box(
            outer_x - lip_width * 2, outer_y - lip_width * 2, STACKING_LIP_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN)
        ).moved(Location((0, 0, outer_height)))
        
        lip = lip_outer.cut(lip_inner)
        result = result.fuse(lip)
        
        # Fillet top edges
        top_edges = result.edges().filter_by(
            lambda e: abs(e.center().Z - (outer_height + STACKING_LIP_HEIGHT)) < 0.5
        )
        if top_edges:
            try:
                result = fillet(top_edges, 0.4)
            except Exception:
                pass
    
    # Add label tab if requested
    if label_tab:
        tab_height = 12.0
        tab_depth = 8.0
        tab_width = inner_x * 0.7
        
        # Create angled label tab on front face
        # Simple approximation - a box rotated
        tab = Box(
            tab_width, tab_depth, tab_height,
            align=(Align.CENTER, Align.MAX, Align.CENTER)
        ).moved(Location((0, -outer_y / 2 + tab_depth / 2, outer_height / 2 + tab_height / 2)))
        result = result.fuse(tab)
    
    # Add finger scoop if requested
    if scoop:
        scoop_radius = 15.0
        # Cut a cylindrical scoop from the front
        scoop_cyl = Cylinder(
            scoop_radius, outer_y,
            align=(Align.CENTER, Align.CENTER, Align.MIN)
        ).moved(Location((0, 0, floor_thickness + scoop_radius / 2))).rotate(Axis.X, 90)
        result = result.cut(scoop_cyl)
    
    return result


# =============================================================================
# Divider Insert Generator
# =============================================================================

@register_template("gridfinity-divider")
def generate_gridfinity_divider(
    grid_x: int = 1,
    grid_y: int = 1,
    height_units: int = 3,
    cells_x: int = 2,
    cells_y: int = 2,
    wall_thickness: float = 1.0,
    floor_thickness: float = 1.0,
    **_kwargs: Any,
) -> Part:
    """
    Generate a Gridfinity divider insert.
    
    An insert with a grid of cells for organizing small items.
    
    Args:
        grid_x: Number of grid units in X direction
        grid_y: Number of grid units in Y direction
        height_units: Height in 7mm units
        cells_x: Number of cells in X direction
        cells_y: Number of cells in Y direction
        wall_thickness: Wall thickness
        floor_thickness: Floor thickness
        
    Returns:
        Build123d Part with the divider
    """
    # Start with a base bin that has the appropriate dividers
    return generate_gridfinity_bin(
        grid_x=grid_x,
        grid_y=grid_y,
        height_units=height_units,
        dividers_x=cells_x - 1,
        dividers_y=cells_y - 1,
        stacking_lip=False,
        wall_thickness=wall_thickness,
        floor_thickness=floor_thickness,
    )


# =============================================================================
# Utility Functions
# =============================================================================

def calculate_gridfinity_dimensions(
    grid_x: int,
    grid_y: int,
    height_units: int,
) -> dict[str, float]:
    """Calculate the actual dimensions of a Gridfinity bin."""
    return {
        "outer_width": grid_x * GRID_UNIT,
        "outer_depth": grid_y * GRID_UNIT,
        "outer_height": height_units * HEIGHT_UNIT,
        "grid_unit": GRID_UNIT,
        "height_unit": HEIGHT_UNIT,
    }


def get_gridfinity_templates() -> list[dict[str, Any]]:
    """Get list of available Gridfinity templates."""
    return [
        {
            "slug": "gridfinity-baseplate",
            "name": "Gridfinity Base Plate",
            "description": "Mounting base for Gridfinity bins",
            "parameters": [
                {"name": "grid_x", "type": "int", "default": 3, "min": 1, "max": 10},
                {"name": "grid_y", "type": "int", "default": 2, "min": 1, "max": 10},
                {"name": "magnet_holes", "type": "bool", "default": True},
                {"name": "screw_holes", "type": "bool", "default": False},
            ],
        },
        {
            "slug": "gridfinity-bin",
            "name": "Gridfinity Storage Bin",
            "description": "Modular storage bin for Gridfinity system",
            "parameters": [
                {"name": "grid_x", "type": "int", "default": 1, "min": 1, "max": 6},
                {"name": "grid_y", "type": "int", "default": 1, "min": 1, "max": 6},
                {"name": "height_units", "type": "int", "default": 3, "min": 1, "max": 10},
                {"name": "dividers_x", "type": "int", "default": 0, "min": 0, "max": 5},
                {"name": "dividers_y", "type": "int", "default": 0, "min": 0, "max": 5},
                {"name": "label_tab", "type": "bool", "default": False},
                {"name": "stacking_lip", "type": "bool", "default": True},
                {"name": "scoop", "type": "bool", "default": False},
            ],
        },
        {
            "slug": "gridfinity-divider",
            "name": "Gridfinity Divider Insert",
            "description": "Grid divider insert for organizing small items",
            "parameters": [
                {"name": "grid_x", "type": "int", "default": 1, "min": 1, "max": 6},
                {"name": "grid_y", "type": "int", "default": 1, "min": 1, "max": 6},
                {"name": "height_units", "type": "int", "default": 3, "min": 1, "max": 10},
                {"name": "cells_x", "type": "int", "default": 2, "min": 1, "max": 10},
                {"name": "cells_y", "type": "int", "default": 2, "min": 1, "max": 10},
            ],
        },
    ]
