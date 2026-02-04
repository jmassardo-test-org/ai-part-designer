"""Tests for feature compilation."""

import pytest
from build123d import Box, Part

from app.cad_v2.compiler.features import (
    PORT_DIMENSIONS,
    FeatureCompiler,
)
from app.cad_v2.schemas.base import BoundingBox, Dimension, Point2D
from app.cad_v2.schemas.enclosure import EnclosureSpec, WallSide, WallSpec
from app.cad_v2.schemas.features import (
    ButtonCutout,
    CircleCutout,
    DisplayCutout,
    PortCutout,
    RectangleCutout,
)


def create_test_body() -> Part:
    """Create a simple enclosure body for testing feature cutouts.
    
    Returns:
        A Box Part representing a simplified enclosure body.
    """
    # Create a simple box matching the test enclosure dimensions
    return Box(120, 100, 50)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def base_enclosure() -> EnclosureSpec:
    """Create a base enclosure for feature testing."""
    return EnclosureSpec(
        exterior=BoundingBox(
            width=Dimension(value=120),
            depth=Dimension(value=100),
            height=Dimension(value=50),
        ),
        walls=WallSpec(thickness=Dimension(value=3)),
    )


@pytest.fixture
def feature_compiler(base_enclosure: EnclosureSpec) -> FeatureCompiler:
    """Create a feature compiler instance."""
    return FeatureCompiler(base_enclosure)


# ============================================================================
# Port Dimensions Tests
# ============================================================================


class TestPortDimensions:
    """Tests for standard port dimensions."""

    def test_usb_c_dimensions(self) -> None:
        """USB-C should have correct dimensions."""
        width, height = PORT_DIMENSIONS["usb-c"]
        assert width == 9.0
        assert height == 3.5

    def test_usb_a_dimensions(self) -> None:
        """USB-A should have correct dimensions."""
        width, height = PORT_DIMENSIONS["usb-a"]
        assert width == 13.0
        assert height == 6.0

    def test_hdmi_dimensions(self) -> None:
        """HDMI should have correct dimensions."""
        width, height = PORT_DIMENSIONS["hdmi"]
        assert width == 15.0
        assert height == 6.0

    def test_ethernet_dimensions(self) -> None:
        """Ethernet should have correct dimensions."""
        width, height = PORT_DIMENSIONS["ethernet"]
        assert width == 16.0
        assert height == 13.5

    def test_all_port_types_defined(self) -> None:
        """All common port types should be defined."""
        expected_ports = [
            "usb-c",
            "usb-a",
            "micro-usb",
            "hdmi",
            "micro-hdmi",
            "ethernet",
            "audio-jack",
            "sd-card",
        ]
        for port in expected_ports:
            assert port in PORT_DIMENSIONS


# ============================================================================
# Wall Position Calculation Tests
# ============================================================================


class TestWallPositionCalculation:
    """Tests for wall position calculations."""

    def test_front_wall_position(self, feature_compiler: FeatureCompiler) -> None:
        """Front wall position should be at -depth/2."""
        pos = feature_compiler._get_wall_position(
            WallSide.FRONT, Point2D(x=10, y=5)
        )
        assert pos[0] == 10  # x passed through
        assert pos[1] == -50  # -depth/2 = -100/2
        assert pos[2] == 5 + 25  # y + height/2

    def test_back_wall_position(self, feature_compiler: FeatureCompiler) -> None:
        """Back wall position should be at +depth/2."""
        pos = feature_compiler._get_wall_position(
            WallSide.BACK, Point2D(x=10, y=5)
        )
        assert pos[0] == 10
        assert pos[1] == 50  # +depth/2

    def test_left_wall_position(self, feature_compiler: FeatureCompiler) -> None:
        """Left wall position should be at -width/2."""
        pos = feature_compiler._get_wall_position(
            WallSide.LEFT, Point2D(x=10, y=5)
        )
        assert pos[0] == -60  # -width/2 = -120/2
        assert pos[1] == 10  # x becomes y

    def test_right_wall_position(self, feature_compiler: FeatureCompiler) -> None:
        """Right wall position should be at +width/2."""
        pos = feature_compiler._get_wall_position(
            WallSide.RIGHT, Point2D(x=10, y=5)
        )
        assert pos[0] == 60  # +width/2

    def test_top_wall_position(self, feature_compiler: FeatureCompiler) -> None:
        """Top wall position should be at +height/2."""
        pos = feature_compiler._get_wall_position(
            WallSide.TOP, Point2D(x=10, y=5)
        )
        assert pos[2] == 25  # +height/2

    def test_bottom_wall_position(self, feature_compiler: FeatureCompiler) -> None:
        """Bottom wall position should be at -height/2."""
        pos = feature_compiler._get_wall_position(
            WallSide.BOTTOM, Point2D(x=10, y=5)
        )
        assert pos[2] == -25  # -height/2


class TestWallNormalCalculation:
    """Tests for wall normal vector calculations."""

    def test_front_wall_normal(self, feature_compiler: FeatureCompiler) -> None:
        """Front wall normal should point -Y."""
        normal = feature_compiler._get_wall_normal(WallSide.FRONT)
        assert normal == (0, -1, 0)

    def test_back_wall_normal(self, feature_compiler: FeatureCompiler) -> None:
        """Back wall normal should point +Y."""
        normal = feature_compiler._get_wall_normal(WallSide.BACK)
        assert normal == (0, 1, 0)

    def test_left_wall_normal(self, feature_compiler: FeatureCompiler) -> None:
        """Left wall normal should point -X."""
        normal = feature_compiler._get_wall_normal(WallSide.LEFT)
        assert normal == (-1, 0, 0)

    def test_right_wall_normal(self, feature_compiler: FeatureCompiler) -> None:
        """Right wall normal should point +X."""
        normal = feature_compiler._get_wall_normal(WallSide.RIGHT)
        assert normal == (1, 0, 0)

    def test_top_wall_normal(self, feature_compiler: FeatureCompiler) -> None:
        """Top wall normal should point +Z."""
        normal = feature_compiler._get_wall_normal(WallSide.TOP)
        assert normal == (0, 0, 1)

    def test_bottom_wall_normal(self, feature_compiler: FeatureCompiler) -> None:
        """Bottom wall normal should point -Z."""
        normal = feature_compiler._get_wall_normal(WallSide.BOTTOM)
        assert normal == (0, 0, -1)


# ============================================================================
# Feature Schema Creation Tests
# ============================================================================


class TestFeatureSchemaCreation:
    """Tests for creating feature schemas."""

    def test_create_port_cutout(self) -> None:
        """Should create valid port cutout schema."""
        port = PortCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=10),
            port_type="usb-c",
            clearance=Dimension(value=0.5),
        )
        assert port.port_type == "usb-c"
        assert port.clearance.mm == 0.5

    def test_create_button_cutout(self) -> None:
        """Should create valid button cutout schema."""
        button = ButtonCutout(
            side=WallSide.TOP,
            position=Point2D(x=20, y=-10),
            diameter=Dimension(value=6),
        )
        assert button.diameter.mm == 6

    def test_create_display_cutout(self) -> None:
        """Should create valid display cutout schema."""
        display = DisplayCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=0),
            viewing_width=Dimension(value=72),
            viewing_height=Dimension(value=24),
        )
        assert display.viewing_width.mm == 72
        assert display.viewing_height.mm == 24


# ============================================================================
# Feature Application Tests
# ============================================================================


class TestFeatureApplication:
    """Tests for applying features to geometry."""

    def test_apply_feature_returns_part(
        self, feature_compiler: FeatureCompiler
    ) -> None:
        """apply_feature should return a modified part."""
        port = PortCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=10),
            port_type="usb-c",
        )
        body = create_test_body()
        result = feature_compiler.apply_feature(body, port)
        # Result should be a Part (with cutout applied)
        assert isinstance(result, Part)

    def test_apply_button_cutout(self, feature_compiler: FeatureCompiler) -> None:
        """Should handle button cutout application."""
        button = ButtonCutout(
            side=WallSide.TOP,
            position=Point2D(x=0, y=0),
            diameter=Dimension(value=6),
        )
        body = create_test_body()
        result = feature_compiler.apply_feature(body, button)
        assert isinstance(result, Part)

    def test_apply_display_cutout(self, feature_compiler: FeatureCompiler) -> None:
        """Should handle display cutout application."""
        display = DisplayCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=0),
            viewing_width=Dimension(value=72),
            viewing_height=Dimension(value=24),
        )
        body = create_test_body()
        result = feature_compiler.apply_feature(body, display)
        assert isinstance(result, Part)


# ============================================================================
# Port Type Normalization Tests
# ============================================================================


class TestPortTypeNormalization:
    """Tests for port type name handling."""

    def test_port_type_lowercase(self) -> None:
        """Port types should use lowercase."""
        for port_type in PORT_DIMENSIONS.keys():
            assert port_type == port_type.lower()

    def test_port_type_hyphenated(self) -> None:
        """Port types with spaces should use hyphens."""
        # USB-C, USB-A, etc should be hyphenated
        assert "usb-c" in PORT_DIMENSIONS
        assert "usb-a" in PORT_DIMENSIONS
        assert "micro-usb" in PORT_DIMENSIONS


# ============================================================================
# Text Feature Tests
# ============================================================================


class TestTextFeature:
    """Tests for text embossing/engraving."""

    def test_apply_embossed_text(self, feature_compiler: FeatureCompiler) -> None:
        """Should handle embossed text application."""
        from app.cad_v2.schemas.features import TextFeature

        text = TextFeature(
            side=WallSide.TOP,
            position=Point2D(x=0, y=0),
            text="HELLO",
            font_size=Dimension(value=8),
            depth=Dimension(value=0.5),
            emboss=True,
        )
        body = create_test_body()
        result = feature_compiler.apply_feature(body, text)
        assert isinstance(result, Part)

    def test_apply_engraved_text(self, feature_compiler: FeatureCompiler) -> None:
        """Should handle engraved text application."""
        from app.cad_v2.schemas.features import TextFeature

        text = TextFeature(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=10),
            text="v1.0",
            font_size=Dimension(value=5),
            depth=Dimension(value=0.3),
            emboss=False,
        )
        body = create_test_body()
        result = feature_compiler.apply_feature(body, text)
        assert isinstance(result, Part)

    def test_text_on_different_sides(self, feature_compiler: FeatureCompiler) -> None:
        """Should handle text on different wall sides."""
        from app.cad_v2.schemas.features import TextFeature

        for side in [WallSide.TOP, WallSide.FRONT, WallSide.LEFT]:
            text = TextFeature(
                side=side,
                position=Point2D(x=0, y=0),
                text="TEST",
                font_size=Dimension(value=6),
            )
            body = create_test_body()
            result = feature_compiler.apply_feature(body, text)
            assert isinstance(result, Part)
