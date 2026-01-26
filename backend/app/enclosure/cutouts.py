"""
Connector Cutout Generator

Generates cutouts for connectors on enclosure walls
based on connector specifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import cadquery as cq

from app.schemas.component_specs import (
    Connector,
    Position3D,
    Face,
    ConnectorType,
)
from app.enclosure.schemas import (
    Cutout,
    CutoutProfile,
    STANDARD_CUTOUT_PROFILES,
)


# =============================================================================
# Cutout Generator
# =============================================================================

class CutoutGenerator:
    """
    Generates cutouts for connectors on enclosure walls.
    
    Supports standard connector profiles and custom dimensions.
    """
    
    def __init__(self):
        self.profiles = STANDARD_CUTOUT_PROFILES.copy()
    
    def get_profile(
        self,
        connector_type: ConnectorType,
    ) -> CutoutProfile:
        """
        Get standard cutout profile for a connector type.
        
        Args:
            connector_type: Type of connector
        
        Returns:
            CutoutProfile with dimensions
        """
        if connector_type in self.profiles:
            return self.profiles[connector_type]
        
        # Fallback for unknown types
        return CutoutProfile(
            connector_type=connector_type,
            width=10.0,
            height=10.0,
            corner_radius=0.5,
        )
    
    def register_profile(
        self,
        connector_type: ConnectorType,
        profile: CutoutProfile,
    ) -> None:
        """Register a custom cutout profile."""
        self.profiles[connector_type] = profile
    
    def calculate_cutout(
        self,
        connector: Connector,
        component_position: Position3D,
        wall_thickness: float,
        tolerance: float = 0.3,
        component_id: Optional[UUID] = None,
    ) -> Cutout:
        """
        Calculate cutout specification for a connector.
        
        Args:
            connector: Connector specification
            component_position: Position of component in enclosure
            wall_thickness: Enclosure wall thickness
            tolerance: Additional clearance around cutout
            component_id: Optional component reference
        
        Returns:
            Cutout specification
        """
        # Get dimensions from connector or profile
        if connector.cutout_width > 0 and connector.cutout_height > 0:
            width = connector.cutout_width + tolerance
            height = connector.cutout_height + tolerance
            corner_radius = 0.5
        else:
            profile = self.get_profile(connector.type)
            width = profile.width + profile.tolerance + tolerance
            height = profile.height + profile.tolerance + tolerance
            corner_radius = profile.corner_radius
        
        # Calculate center position on wall face
        # This depends on which face the connector is on
        center_x, center_y = self._calculate_cutout_position(
            connector=connector,
            component_position=component_position,
        )
        
        return Cutout(
            face=connector.face,
            center_x=round(center_x, 2),
            center_y=round(center_y, 2),
            width=round(width, 2),
            height=round(height, 2),
            depth=wall_thickness,
            corner_radius=corner_radius,
            connector_type=connector.type,
            connector_name=connector.name,
            component_id=component_id,
        )
    
    def _calculate_cutout_position(
        self,
        connector: Connector,
        component_position: Position3D,
    ) -> tuple[float, float]:
        """
        Calculate cutout center position on the wall face.
        
        Returns (center_x, center_y) where:
        - For FRONT/BACK faces: x is along enclosure X, y is along Z
        - For LEFT/RIGHT faces: x is along enclosure Y, y is along Z
        - For TOP/BOTTOM faces: x is along enclosure X, y is along Y
        """
        conn_pos = connector.position
        
        if connector.face in (Face.FRONT, Face.BACK):
            # X position is component X + connector X offset
            center_x = component_position.x + conn_pos.x
            # Y position is component Z + connector Z offset
            center_y = component_position.z + conn_pos.z
            
        elif connector.face in (Face.LEFT, Face.RIGHT):
            # X position is component Y + connector Y offset
            center_x = component_position.y + conn_pos.y
            # Y position is component Z + connector Z offset
            center_y = component_position.z + conn_pos.z
            
        elif connector.face in (Face.TOP, Face.BOTTOM):
            # X position is component X + connector X offset
            center_x = component_position.x + conn_pos.x
            # Y position is component Y + connector Y offset
            center_y = component_position.y + conn_pos.y
        else:
            # Default
            center_x = conn_pos.x
            center_y = conn_pos.z
        
        return center_x, center_y
    
    def generate_cutout_geometry(
        self,
        cutout: Cutout,
        enclosure_dims: tuple[float, float, float],
        wall_thickness: float,
    ) -> cq.Workplane:
        """
        Generate CadQuery geometry for a single cutout.
        
        This creates a solid that can be subtracted from the enclosure.
        
        Args:
            cutout: Cutout specification
            enclosure_dims: (length, width, height) of enclosure
            wall_thickness: Wall thickness
        
        Returns:
            CadQuery Workplane with cutout solid
        """
        length, width, height = enclosure_dims
        half_l = length / 2
        half_w = width / 2
        
        # Create rectangle with rounded corners
        def rounded_rect(w: float, h: float, r: float) -> cq.Workplane:
            """Create a rounded rectangle sketch."""
            if r <= 0:
                return cq.Workplane("XY").rect(w, h)
            
            # Clamp radius to half the smaller dimension
            r = min(r, w / 2, h / 2)
            
            return (
                cq.Workplane("XY")
                .rect(w - 2 * r, h)
                .union(cq.Workplane("XY").rect(w, h - 2 * r))
                .union(cq.Workplane("XY").center(-w/2 + r, -h/2 + r).circle(r))
                .union(cq.Workplane("XY").center(w/2 - r, -h/2 + r).circle(r))
                .union(cq.Workplane("XY").center(-w/2 + r, h/2 - r).circle(r))
                .union(cq.Workplane("XY").center(w/2 - r, h/2 - r).circle(r))
            )
        
        # Position and orient based on face
        if cutout.face == Face.FRONT:
            # Front face: -Y, looking toward +Y
            result = (
                cq.Workplane("XZ")
                .workplane(offset=-half_w)
                .center(cutout.center_x, cutout.center_y)
                .rect(cutout.width, cutout.height)
                .extrude(wall_thickness * 2)
            )
            
        elif cutout.face == Face.BACK:
            # Back face: +Y, looking toward -Y
            result = (
                cq.Workplane("XZ")
                .workplane(offset=half_w)
                .center(cutout.center_x, cutout.center_y)
                .rect(cutout.width, cutout.height)
                .extrude(-wall_thickness * 2)
            )
            
        elif cutout.face == Face.LEFT:
            # Left face: -X, looking toward +X
            result = (
                cq.Workplane("YZ")
                .workplane(offset=-half_l)
                .center(cutout.center_x, cutout.center_y)
                .rect(cutout.width, cutout.height)
                .extrude(wall_thickness * 2)
            )
            
        elif cutout.face == Face.RIGHT:
            # Right face: +X, looking toward -X
            result = (
                cq.Workplane("YZ")
                .workplane(offset=half_l)
                .center(cutout.center_x, cutout.center_y)
                .rect(cutout.width, cutout.height)
                .extrude(-wall_thickness * 2)
            )
            
        elif cutout.face == Face.TOP:
            # Top face: +Z
            result = (
                cq.Workplane("XY")
                .workplane(offset=height)
                .center(cutout.center_x, cutout.center_y)
                .rect(cutout.width, cutout.height)
                .extrude(-wall_thickness * 2)
            )
            
        elif cutout.face == Face.BOTTOM:
            # Bottom face: -Z
            result = (
                cq.Workplane("XY")
                .workplane(offset=0)
                .center(cutout.center_x, cutout.center_y)
                .rect(cutout.width, cutout.height)
                .extrude(wall_thickness * 2)
            )
        else:
            # Default to front
            result = (
                cq.Workplane("XZ")
                .center(cutout.center_x, cutout.center_y)
                .rect(cutout.width, cutout.height)
                .extrude(wall_thickness * 2)
            )
        
        return result
    
    def generate_all_cutouts(
        self,
        cutouts: list[Cutout],
        enclosure_dims: tuple[float, float, float],
        wall_thickness: float,
    ) -> cq.Workplane:
        """
        Generate combined geometry for all cutouts.
        
        Args:
            cutouts: List of cutout specifications
            enclosure_dims: (length, width, height) of enclosure
            wall_thickness: Wall thickness
        
        Returns:
            Combined CadQuery Workplane with all cutout solids
        """
        if not cutouts:
            return cq.Workplane("XY")
        
        # Generate first cutout
        result = self.generate_cutout_geometry(
            cutouts[0], enclosure_dims, wall_thickness
        )
        
        # Union with remaining cutouts
        for cutout in cutouts[1:]:
            new_cutout = self.generate_cutout_geometry(
                cutout, enclosure_dims, wall_thickness
            )
            result = result.union(new_cutout)
        
        return result


# =============================================================================
# Convenience Functions
# =============================================================================

def get_cutout_for_connector(
    connector_type: ConnectorType,
    face: Face,
    center_x: float,
    center_y: float,
    wall_thickness: float,
    tolerance: float = 0.3,
) -> Cutout:
    """
    Create a cutout for a known connector type.
    
    Args:
        connector_type: Type of connector
        face: Which face of enclosure
        center_x: X position on face
        center_y: Y position on face
        wall_thickness: Wall thickness
        tolerance: Additional clearance
    
    Returns:
        Cutout specification
    """
    generator = CutoutGenerator()
    profile = generator.get_profile(connector_type)
    
    return Cutout(
        face=face,
        center_x=center_x,
        center_y=center_y,
        width=profile.width + profile.tolerance + tolerance,
        height=profile.height + profile.tolerance + tolerance,
        depth=wall_thickness,
        corner_radius=profile.corner_radius,
        connector_type=connector_type,
    )


def create_rectangular_cutout(
    face: Face,
    center_x: float,
    center_y: float,
    width: float,
    height: float,
    wall_thickness: float,
    corner_radius: float = 0.5,
    name: Optional[str] = None,
) -> Cutout:
    """
    Create a custom rectangular cutout.
    
    Args:
        face: Which face of enclosure
        center_x: X position on face
        center_y: Y position on face
        width: Cutout width
        height: Cutout height
        wall_thickness: Wall thickness
        corner_radius: Corner radius
        name: Optional name for the cutout
    
    Returns:
        Cutout specification
    """
    return Cutout(
        face=face,
        center_x=center_x,
        center_y=center_y,
        width=width,
        height=height,
        depth=wall_thickness,
        corner_radius=corner_radius,
        connector_name=name,
    )
