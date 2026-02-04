"""Tests for CAD v2 feature schemas."""

import pytest
from pydantic import ValidationError

from app.cad_v2.schemas.base import Dimension, Point2D
from app.cad_v2.schemas.enclosure import WallSide
from app.cad_v2.schemas.features import (
    BaseCutout,
    ButtonCutout,
    CircleCutout,
    DisplayCutout,
    MountingHoleFeature,
    OvalCutout,
    PolygonCutout,
    PortCutout,
    RectangleCutout,
    SlotCutout,
    TextFeature,
    VentPattern,
)


class TestRectangleCutout:
    """Tests for RectangleCutout schema."""

    def test_rectangle_cutout_creation(self) -> None:
        """RectangleCutout should accept width and height."""
        cutout = RectangleCutout(
            width=Dimension(value=20),
            height=Dimension(value=10),
        )
        assert cutout.shape == "rectangle"
        assert cutout.width.mm == 20
        assert cutout.height.mm == 10

    def test_rectangle_cutout_with_radius(self) -> None:
        """RectangleCutout should accept corner radius."""
        cutout = RectangleCutout(
            width=Dimension(value=20),
            height=Dimension(value=10),
            corner_radius=Dimension(value=2),
        )
        assert cutout.corner_radius is not None
        assert cutout.corner_radius.mm == 2


class TestCircleCutout:
    """Tests for CircleCutout schema."""

    def test_circle_cutout_creation(self) -> None:
        """CircleCutout should accept diameter."""
        cutout = CircleCutout(diameter=Dimension(value=10))
        assert cutout.shape == "circle"
        assert cutout.diameter.mm == 10


class TestSlotCutout:
    """Tests for SlotCutout schema."""

    def test_slot_cutout_creation(self) -> None:
        """SlotCutout should accept length and width."""
        cutout = SlotCutout(
            length=Dimension(value=20),
            width=Dimension(value=5),
        )
        assert cutout.shape == "slot"
        assert cutout.length.mm == 20
        assert cutout.width.mm == 5

    def test_slot_cutout_orientation(self) -> None:
        """SlotCutout should accept orientation."""
        cutout = SlotCutout(
            length=Dimension(value=20),
            width=Dimension(value=5),
            orientation="vertical",
        )
        assert cutout.orientation == "vertical"


class TestOvalCutout:
    """Tests for OvalCutout schema."""

    def test_oval_cutout_creation(self) -> None:
        """OvalCutout should accept width and height."""
        cutout = OvalCutout(
            width=Dimension(value=15),
            height=Dimension(value=10),
        )
        assert cutout.shape == "oval"
        assert cutout.width.mm == 15
        assert cutout.height.mm == 10


class TestPolygonCutout:
    """Tests for PolygonCutout schema."""

    def test_polygon_cutout_creation(self) -> None:
        """PolygonCutout should accept list of points."""
        cutout = PolygonCutout(
            points=[
                Point2D(x=0, y=0),
                Point2D(x=10, y=0),
                Point2D(x=5, y=10),
            ],
        )
        assert cutout.shape == "polygon"
        assert len(cutout.points) == 3

    def test_polygon_requires_minimum_points(self) -> None:
        """PolygonCutout should require at least 3 points."""
        with pytest.raises(ValidationError):
            PolygonCutout(
                points=[
                    Point2D(x=0, y=0),
                    Point2D(x=10, y=0),
                ],
            )


class TestBaseCutout:
    """Tests for BaseCutout schema."""

    def test_base_cutout_creation(self) -> None:
        """BaseCutout should combine side, position, and cutout spec."""
        cutout = BaseCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=0),
            cutout=RectangleCutout(
                width=Dimension(value=20),
                height=Dimension(value=10),
            ),
        )
        assert cutout.type == "cutout"
        assert cutout.side == WallSide.FRONT
        assert cutout.position.x == 0

    def test_base_cutout_with_label(self) -> None:
        """BaseCutout should accept label."""
        cutout = BaseCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=0),
            cutout=CircleCutout(diameter=Dimension(value=6)),
            label="LED",
        )
        assert cutout.label == "LED"


class TestPortCutout:
    """Tests for PortCutout schema."""

    def test_port_cutout_creation(self) -> None:
        """PortCutout should accept port type."""
        cutout = PortCutout(
            side=WallSide.BACK,
            position=Point2D(x=0, y=5),
            port_type="usb-c",
        )
        assert cutout.type == "port"
        assert cutout.port_type == "usb-c"

    def test_port_cutout_clearance(self) -> None:
        """PortCutout should accept custom clearance."""
        cutout = PortCutout(
            side=WallSide.BACK,
            position=Point2D(x=0, y=5),
            port_type="hdmi",
            clearance=Dimension(value=1.0),
        )
        assert cutout.clearance.mm == 1.0


class TestButtonCutout:
    """Tests for ButtonCutout schema."""

    def test_button_cutout_defaults(self) -> None:
        """ButtonCutout should have default diameter."""
        button = ButtonCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=0),
        )
        assert button.type == "button"
        assert button.diameter.mm == 6.0
        assert button.bezel is False

    def test_button_cutout_with_bezel(self) -> None:
        """ButtonCutout should accept bezel options."""
        button = ButtonCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=0),
            diameter=Dimension(value=8),
            bezel=True,
            bezel_height=Dimension(value=2),
        )
        assert button.bezel is True
        assert button.bezel_height.mm == 2.0

    def test_button_cutout_with_label(self) -> None:
        """ButtonCutout should accept label."""
        button = ButtonCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=0),
            label="POWER",
        )
        assert button.label == "POWER"


class TestDisplayCutout:
    """Tests for DisplayCutout schema."""

    def test_display_cutout_creation(self) -> None:
        """DisplayCutout should accept viewing dimensions."""
        display = DisplayCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=10),
            viewing_width=Dimension(value=77),
            viewing_height=Dimension(value=26),
        )
        assert display.type == "display"
        assert display.viewing_width.mm == 77
        assert display.viewing_height.mm == 26

    def test_display_cutout_bezel_width(self) -> None:
        """DisplayCutout should have default bezel width."""
        display = DisplayCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=0),
            viewing_width=Dimension(value=77),
            viewing_height=Dimension(value=26),
        )
        assert display.bezel_width.mm == 2.0


class TestVentPattern:
    """Tests for VentPattern schema."""

    def test_vent_pattern_creation(self) -> None:
        """VentPattern should accept area dimensions."""
        vent = VentPattern(
            side=WallSide.LEFT,
            position=Point2D(x=0, y=0),
            area_width=Dimension(value=40),
            area_height=Dimension(value=20),
        )
        assert vent.type == "vent"
        assert vent.pattern == "slots"  # Default

    def test_vent_pattern_honeycomb(self) -> None:
        """VentPattern should accept pattern type."""
        vent = VentPattern(
            side=WallSide.LEFT,
            position=Point2D(x=0, y=0),
            area_width=Dimension(value=40),
            area_height=Dimension(value=20),
            pattern="honeycomb",
        )
        assert vent.pattern == "honeycomb"


class TestMountingHoleFeature:
    """Tests for MountingHoleFeature schema."""

    def test_mounting_hole_creation(self) -> None:
        """MountingHoleFeature should accept diameter."""
        hole = MountingHoleFeature(
            side=WallSide.BOTTOM,
            position=Point2D(x=10, y=10),
            diameter=Dimension(value=4),
        )
        assert hole.type == "mounting_hole"
        assert hole.diameter.mm == 4

    def test_mounting_hole_countersink(self) -> None:
        """MountingHoleFeature should accept countersink options."""
        hole = MountingHoleFeature(
            side=WallSide.BOTTOM,
            position=Point2D(x=10, y=10),
            diameter=Dimension(value=4),
            countersink=True,
            countersink_diameter=Dimension(value=8),
            countersink_depth=Dimension(value=2),
        )
        assert hole.countersink is True
        assert hole.countersink_diameter is not None


class TestTextFeature:
    """Tests for TextFeature schema."""

    def test_text_feature_creation(self) -> None:
        """TextFeature should accept text content."""
        text = TextFeature(
            side=WallSide.TOP,
            position=Point2D(x=0, y=0),
            text="AssemblematicAI",
        )
        assert text.type == "text"
        assert text.text == "AssemblematicAI"

    def test_text_feature_emboss(self) -> None:
        """TextFeature should accept emboss option."""
        text = TextFeature(
            side=WallSide.TOP,
            position=Point2D(x=0, y=0),
            text="v1.0",
            emboss=False,  # Engraved
            depth=Dimension(value=0.3),
        )
        assert text.emboss is False
        assert text.depth.mm == 0.3

    def test_text_feature_font_size(self) -> None:
        """TextFeature should accept font size."""
        text = TextFeature(
            side=WallSide.TOP,
            position=Point2D(x=0, y=0),
            text="Label",
            font_size=Dimension(value=8),
        )
        assert text.font_size.mm == 8
