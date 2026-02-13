"""Feature compiler for CAD v2.

Compiles feature schemas (cutouts, ports, vents) into Build123d operations.
"""

from typing import Any

from app.cad_v2.schemas.base import Point2D
from app.cad_v2.schemas.enclosure import EnclosureSpec, WallSide
from app.cad_v2.schemas.features import (
    BaseCutout,
    ButtonCutout,
    CircleCutout,
    DisplayCutout,
    Feature,
    PortCutout,
    RectangleCutout,
    SlotCutout,
    TextFeature,
    VentPattern,
)

# Import Build123d conditionally
try:
    from build123d import (
        Axis,
        Box,
        BuildPart,
        Cylinder,
        Location,
        Locations,
        Mode,
        Part,
        Plane,
        Rectangle,
        extrude,
    )

    BUILD123D_AVAILABLE = True
except ImportError:
    BUILD123D_AVAILABLE = False
    Part = Any  # type: ignore[assignment, misc]


# Standard port dimensions (width x height in mm)
PORT_DIMENSIONS: dict[str, tuple[float, float]] = {
    "usb-c": (9.0, 3.5),
    "usb-a": (13.0, 6.0),
    "micro-usb": (8.0, 3.0),
    "mini-usb": (8.0, 4.0),
    "hdmi": (15.0, 6.0),
    "micro-hdmi": (7.0, 3.5),
    "mini-hdmi": (11.0, 3.5),
    "ethernet": (16.0, 13.5),
    "audio-jack": (7.0, 7.0),  # Circular, this is bounding box
    "barrel-jack": (8.0, 8.0),  # Circular
    "sd-card": (26.0, 3.0),
}


class FeatureCompiler:
    """Compiles features into Build123d operations."""

    def __init__(self, enclosure_spec: EnclosureSpec) -> None:
        """Initialize feature compiler.

        Args:
            enclosure_spec: The enclosure specification for context.
        """
        self.spec = enclosure_spec

    def apply_feature(self, body: Part, feature: Feature) -> Part:
        """Apply a feature to the enclosure body.

        Args:
            body: Current enclosure body.
            feature: Feature to apply.

        Returns:
            Modified body with feature applied.
        """
        if not BUILD123D_AVAILABLE:
            return body

        if isinstance(feature, BaseCutout):
            return self._apply_cutout(body, feature)
        if isinstance(feature, PortCutout):
            return self._apply_port_cutout(body, feature)
        if isinstance(feature, ButtonCutout):
            return self._apply_button_cutout(body, feature)
        if isinstance(feature, DisplayCutout):
            return self._apply_display_cutout(body, feature)
        if isinstance(feature, VentPattern):
            return self._apply_vent_pattern(body, feature)
        if isinstance(feature, TextFeature):
            return self._apply_text_feature(body, feature)
        # Unknown feature type - return unchanged
        return body

    def _get_wall_position(
        self,
        side: WallSide,
        position: Point2D,
    ) -> tuple[float, float, float]:
        """Convert wall position to 3D coordinates.

        Args:
            side: Which wall.
            position: 2D position on wall (from center).

        Returns:
            (x, y, z) position in enclosure coordinates.
        """
        ext = self.spec.exterior

        if side == WallSide.FRONT:
            return (position.x, -ext.depth_mm / 2, position.y + ext.height_mm / 2)
        if side == WallSide.BACK:
            return (position.x, ext.depth_mm / 2, position.y + ext.height_mm / 2)
        if side == WallSide.LEFT:
            return (-ext.width_mm / 2, position.x, position.y + ext.height_mm / 2)
        if side == WallSide.RIGHT:
            return (ext.width_mm / 2, position.x, position.y + ext.height_mm / 2)
        if side == WallSide.TOP:
            return (position.x, position.y, ext.height_mm / 2)
        if side == WallSide.BOTTOM:
            return (position.x, position.y, -ext.height_mm / 2)
        raise ValueError(f"Unknown wall side: {side}")

    def _get_wall_normal(self, side: WallSide) -> tuple[float, float, float]:
        """Get the outward normal vector for a wall.

        Args:
            side: Which wall.

        Returns:
            (x, y, z) normal vector.
        """
        normals = {
            WallSide.FRONT: (0, -1, 0),
            WallSide.BACK: (0, 1, 0),
            WallSide.LEFT: (-1, 0, 0),
            WallSide.RIGHT: (1, 0, 0),
            WallSide.TOP: (0, 0, 1),
            WallSide.BOTTOM: (0, 0, -1),
        }
        return normals[side]

    def _apply_cutout(self, body: Part, cutout: BaseCutout) -> Part:
        """Apply a generic cutout to the body."""
        wall = self.spec.walls.thickness.mm
        pos = self._get_wall_position(cutout.side, cutout.position)

        with BuildPart() as result:
            from build123d import add

            add(body)

            with BuildPart(mode=Mode.SUBTRACT), Location(pos):  # type: ignore[attr-defined]
                if isinstance(cutout.cutout, RectangleCutout):
                    rect = cutout.cutout
                    # Depth needs to go through wall
                    depth = (cutout.depth.mm if cutout.depth else wall) + 1
                    Box(rect.width.mm, depth, rect.height.mm)

                elif isinstance(cutout.cutout, CircleCutout):
                    circle = cutout.cutout
                    depth = (cutout.depth.mm if cutout.depth else wall) + 1
                    Cylinder(circle.diameter.mm / 2, depth)

                elif isinstance(cutout.cutout, SlotCutout):
                    slot = cutout.cutout
                    depth = (cutout.depth.mm if cutout.depth else wall) + 1
                    # Create slot as box with rounded ends
                    if slot.orientation == "horizontal":
                        Box(slot.length.mm, depth, slot.width.mm)
                    else:
                        Box(slot.width.mm, depth, slot.length.mm)

        return result.part  # type: ignore[no-any-return]

    def _apply_port_cutout(self, body: Part, port: PortCutout) -> Part:
        """Apply a standard port cutout."""
        wall = self.spec.walls.thickness.mm
        pos = self._get_wall_position(port.side, port.position)

        # Get standard port dimensions
        port_type = port.port_type.lower().replace(" ", "-")
        if port_type in PORT_DIMENSIONS:
            width, height = PORT_DIMENSIONS[port_type]
        else:
            # Default small port
            width, height = 10.0, 5.0

        # Add clearance
        clearance = port.clearance.mm
        width += 2 * clearance
        height += 2 * clearance

        with BuildPart() as result:
            from build123d import add

            add(body)

            with BuildPart(mode=Mode.SUBTRACT), Locations([pos]):
                depth = wall + 1
                Box(width, depth, height)

        return result.part  # type: ignore[no-any-return]

    def _apply_button_cutout(self, body: Part, button: ButtonCutout) -> Part:
        """Apply a button cutout (circular)."""
        wall = self.spec.walls.thickness.mm
        pos = self._get_wall_position(button.side, button.position)

        with BuildPart() as result:
            from build123d import add

            add(body)

            with BuildPart(mode=Mode.SUBTRACT), Locations([pos]):
                # Circular hole for button actuator
                Cylinder(button.diameter.mm / 2, wall + 1)

        return result.part  # type: ignore[no-any-return]

    def _apply_display_cutout(self, body: Part, display: DisplayCutout) -> Part:
        """Apply a display cutout."""
        wall = self.spec.walls.thickness.mm
        pos = self._get_wall_position(display.side, display.position)

        with BuildPart() as result:
            from build123d import add

            add(body)

            with BuildPart(mode=Mode.SUBTRACT), Locations([pos]):
                # Viewing area cutout
                Box(display.viewing_width.mm, wall + 1, display.viewing_height.mm)

        return result.part  # type: ignore[no-any-return]

    def _apply_vent_pattern(self, body: Part, _vent: VentPattern) -> Part:
        """Apply a ventilation pattern."""
        # This is handled by EnclosureCompiler._apply_ventilation
        # Individual VentPattern features would be compiled here
        return body

    def _apply_text_feature(self, body: Part, text_feature: TextFeature) -> Part:
        """Apply embossed or engraved text to a surface.

        Note: Build123d text support requires additional setup.
        This is a simplified implementation using Box approximation.
        For production, consider using build123d's Text() with proper fonts.

        Args:
            body: Current enclosure body.
            text_feature: Text feature specification.

        Returns:
            Modified body with text added.
        """
        from build123d import add

        pos = self._get_wall_position(text_feature.side, text_feature.position)

        # Calculate text dimensions (rough approximation)
        char_count = len(text_feature.text)
        char_width = text_feature.font_size.mm * 0.6  # Approximate
        text_width = char_count * char_width
        text_height = text_feature.font_size.mm
        depth = text_feature.depth.mm

        with BuildPart() as result:
            add(body)

            if text_feature.emboss:
                # Raised text - add geometry
                with Locations([pos]):
                    Box(
                        text_width,
                        depth,  # Into the wall direction
                        text_height,
                    )
            else:
                # Engraved text - subtract geometry
                with BuildPart(mode=Mode.SUBTRACT), Locations([pos]):
                    Box(
                        text_width,
                        depth + 0.5,  # Slightly deeper than surface
                        text_height,
                    )

        return result.part  # type: ignore[no-any-return]
