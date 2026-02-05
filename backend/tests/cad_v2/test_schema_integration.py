"""Integration tests for CAD v2 schemas.

These tests verify that composite schemas work together
and can represent the target use case (enclosure with Pi 5, LCD, buttons).
"""

import json

import pytest

from app.cad_v2.schemas.base import BoundingBox, Dimension, Point2D, Point3D
from app.cad_v2.schemas.components import (
    ComponentMount,
    ComponentRef,
    MountingType,
    PortExposure,
    StandoffSpec,
)
from app.cad_v2.schemas.enclosure import (
    EnclosureSpec,
    LidSpec,
    LidType,
    MountingTabSpec,
    VentilationSpec,
    WallSide,
    WallSpec,
)
from app.cad_v2.schemas.features import (
    ButtonCutout,
    DisplayCutout,
    PortCutout,
    VentPattern,
)
from app.cad_v2.schemas.patterns import CustomPattern, PatternPresets


class TestFullEnclosureSpec:
    """Tests for complete enclosure specifications."""

    def test_minimal_enclosure_serialization(self) -> None:
        """Minimal enclosure should serialize to JSON."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
        )

        # Should serialize without error
        json_str = spec.model_dump_json()
        assert "100" in json_str
        assert "exterior" in json_str

    def test_enclosure_from_json(self) -> None:
        """Enclosure should deserialize from JSON."""
        json_data = {
            "exterior": {
                "width": {"value": 100},
                "depth": {"value": 80},
                "height": {"value": 40},
            },
            "walls": {"thickness": {"value": 2.5}},
            "name": "Test Enclosure",
        }

        spec = EnclosureSpec.model_validate(json_data)
        assert spec.exterior.width_mm == 100
        assert spec.walls.thickness.mm == 2.5
        assert spec.name == "Test Enclosure"


class TestPi5EnclosureSpec:
    """Tests for the target use case: Pi 5 enclosure with LCD and buttons."""

    @pytest.fixture
    def pi5_enclosure_spec(self) -> EnclosureSpec:
        """Create a complete Pi 5 enclosure specification."""
        return EnclosureSpec(
            name="Pi 5 Enclosure with LCD",
            description="Enclosure for Raspberry Pi 5 with 20x4 LCD and navigation buttons",
            exterior=BoundingBox(
                width=Dimension(value=120),
                depth=Dimension(value=90),
                height=Dimension(value=45),
            ),
            walls=WallSpec(thickness=Dimension(value=2.5)),
            corner_radius=Dimension(value=3),
            lid=LidSpec(
                type=LidType.SNAP_FIT,
                side=WallSide.TOP,
                separate_part=True,
            ),
            ventilation=VentilationSpec(
                enabled=True,
                sides=[WallSide.LEFT, WallSide.RIGHT],
                pattern="slots",
                slot_width=Dimension(value=2),
                slot_length=Dimension(value=15),
            ),
            mounting_tabs=MountingTabSpec(
                enabled=True,
                sides=[WallSide.BOTTOM],
                count_per_side=2,
                hole_diameter=Dimension(value=4),
            ),
            components=[],  # Would contain ComponentMount objects
            features=[],  # Would contain Feature objects
        )

    def test_pi5_enclosure_basic_properties(self, pi5_enclosure_spec: EnclosureSpec) -> None:
        """Pi 5 enclosure should have correct basic properties."""
        spec = pi5_enclosure_spec
        assert spec.exterior.width_mm == 120
        assert spec.exterior.depth_mm == 90
        assert spec.exterior.height_mm == 45
        assert spec.name == "Pi 5 Enclosure with LCD"

    def test_pi5_enclosure_interior_dimensions(self, pi5_enclosure_spec: EnclosureSpec) -> None:
        """Pi 5 enclosure interior should account for wall thickness."""
        spec = pi5_enclosure_spec
        interior = spec.interior
        # 120 - 2*2.5 = 115mm
        assert interior.width_mm == 115
        # 90 - 2*2.5 = 85mm
        assert interior.depth_mm == 85
        # 45 - 2.5 = 42.5mm (open top)
        assert interior.height_mm == 42.5

    def test_pi5_enclosure_lid_config(self, pi5_enclosure_spec: EnclosureSpec) -> None:
        """Pi 5 enclosure lid should be configured correctly."""
        spec = pi5_enclosure_spec
        assert spec.lid is not None
        assert spec.lid.type == LidType.SNAP_FIT
        assert spec.lid.side == WallSide.TOP
        assert spec.lid.separate_part is True

    def test_pi5_enclosure_ventilation(self, pi5_enclosure_spec: EnclosureSpec) -> None:
        """Pi 5 enclosure should have ventilation configured."""
        spec = pi5_enclosure_spec
        assert spec.ventilation.enabled is True
        assert WallSide.LEFT in spec.ventilation.sides
        assert WallSide.RIGHT in spec.ventilation.sides
        assert spec.ventilation.pattern == "slots"

    def test_pi5_enclosure_mounting_tabs(self, pi5_enclosure_spec: EnclosureSpec) -> None:
        """Pi 5 enclosure should have mounting tabs configured."""
        spec = pi5_enclosure_spec
        assert spec.mounting_tabs.enabled is True
        assert WallSide.BOTTOM in spec.mounting_tabs.sides

    def test_pi5_enclosure_serialization_roundtrip(self, pi5_enclosure_spec: EnclosureSpec) -> None:
        """Pi 5 enclosure should survive JSON roundtrip."""
        # Serialize to JSON
        json_str = pi5_enclosure_spec.model_dump_json()

        # Parse JSON
        json_data = json.loads(json_str)

        # Deserialize back to model
        restored = EnclosureSpec.model_validate(json_data)

        # Verify key properties preserved
        assert restored.exterior.width_mm == pi5_enclosure_spec.exterior.width_mm
        assert restored.name == pi5_enclosure_spec.name
        assert restored.lid is not None
        assert restored.lid.type == pi5_enclosure_spec.lid.type


class TestComponentMountIntegration:
    """Tests for component mounting in enclosures."""

    def test_pi5_component_mount(self) -> None:
        """ComponentMount for Pi 5 should validate correctly."""
        mount = ComponentMount(
            component=ComponentRef(
                component_id="raspberry-pi-5",
                alias="Pi 5",
            ),
            position=Point3D(x=10, y=15, z=0),
            mount_side=WallSide.BOTTOM,
            mounting_type=MountingType.STANDOFF,
            standoffs=StandoffSpec.for_pi(),
            expose_ports=[
                PortExposure(
                    port_name="usb-c-power",
                    side=WallSide.BACK,
                    clearance=Dimension(value=0.5),
                ),
                PortExposure(
                    port_name="micro-hdmi-0",
                    side=WallSide.BACK,
                    clearance=Dimension(value=0.5),
                ),
            ],
        )

        assert mount.component.component_id == "raspberry-pi-5"
        assert mount.mounting_type == MountingType.STANDOFF
        assert mount.standoffs is not None
        assert len(mount.expose_ports) == 2

    def test_lcd_component_mount(self) -> None:
        """ComponentMount for LCD should validate correctly."""
        mount = ComponentMount(
            component=ComponentRef(
                component_id="lcd-20x4-hd44780",
                alias="20x4 LCD",
            ),
            position=Point3D(x=0, y=0, z=0),
            mount_side=WallSide.FRONT,
            mounting_type=MountingType.STANDOFF,
            standoffs=StandoffSpec.for_lcd(),
            label="Main Display",
        )

        assert mount.component.component_id == "lcd-20x4-hd44780"
        assert mount.mount_side == WallSide.FRONT
        assert mount.label == "Main Display"


class TestFeatureIntegration:
    """Tests for features in enclosures."""

    def test_display_cutout(self) -> None:
        """DisplayCutout for LCD should validate correctly."""
        cutout = DisplayCutout(
            side=WallSide.FRONT,
            position=Point2D(x=0, y=10),
            viewing_width=Dimension(value=77),
            viewing_height=Dimension(value=26),
            corner_radius=Dimension(value=1),
            bezel_width=Dimension(value=2),
        )

        assert cutout.viewing_width.mm == 77
        assert cutout.viewing_height.mm == 26
        assert cutout.side == WallSide.FRONT

    def test_button_cluster(self) -> None:
        """Button cluster using pattern should validate correctly."""
        # Create D-pad pattern for 5 buttons
        pattern = PatternPresets.nav_cluster_dpad()

        # Create button cutouts at each position
        buttons = []
        for i, pos in enumerate(pattern.positions):
            button = ButtonCutout(
                side=WallSide.FRONT,
                position=pos,
                diameter=Dimension(value=6),
                label=pattern.labels[i] if pattern.labels else None,
            )
            buttons.append(button)

        assert len(buttons) == 5
        assert buttons[0].label == "up"
        assert buttons[4].label == "select"

    def test_port_cutouts(self) -> None:
        """Port cutouts for Pi 5 should validate correctly."""
        usb_c = PortCutout(
            side=WallSide.BACK,
            position=Point2D(x=-30, y=0),
            port_type="usb-c",
            clearance=Dimension(value=0.5),
        )

        hdmi = PortCutout(
            side=WallSide.BACK,
            position=Point2D(x=0, y=0),
            port_type="micro-hdmi",
            clearance=Dimension(value=0.5),
        )

        assert usb_c.port_type == "usb-c"
        assert hdmi.port_type == "micro-hdmi"

    def test_ventilation_pattern(self) -> None:
        """Ventilation pattern should validate correctly."""
        vent = VentPattern(
            side=WallSide.LEFT,
            position=Point2D(x=0, y=0),
            pattern="slots",
            area_width=Dimension(value=30),
            area_height=Dimension(value=20),
            slot_width=Dimension(value=2),
            slot_length=Dimension(value=15),
            spacing=Dimension(value=3),
        )

        assert vent.pattern == "slots"
        assert vent.area_width.mm == 30


class TestSchemaValidationErrors:
    """Tests for schema validation error messages."""

    def test_enclosure_wall_too_thick_error_message(self) -> None:
        """Error message should explain wall thickness issue."""
        with pytest.raises(Exception) as exc_info:
            EnclosureSpec(
                exterior=BoundingBox(
                    width=Dimension(value=20),
                    depth=Dimension(value=80),
                    height=Dimension(value=40),
                ),
                walls=WallSpec(thickness=Dimension(value=15)),
            )

        error_message = str(exc_info.value)
        # Error comes from Dimension validator when interior calc produces negative
        assert "greater than 0" in error_message or "must be positive" in error_message

    def test_missing_required_field_error(self) -> None:
        """Missing required field should give clear error."""
        with pytest.raises(Exception) as exc_info:
            EnclosureSpec()  # Missing exterior

        error_message = str(exc_info.value)
        assert "exterior" in error_message.lower()


class TestPatternIntegration:
    """Tests for pattern usage in features."""

    def test_custom_pattern_for_buttons(self) -> None:
        """Custom pattern should work for button arrangement."""
        # Create a custom arrangement for action buttons (A, B, X, Y)
        pattern = CustomPattern(
            positions=[
                Point2D(x=20, y=0),  # A - right
                Point2D(x=10, y=-10),  # B - bottom right
                Point2D(x=10, y=10),  # X - top right
                Point2D(x=0, y=0),  # Y - left
            ],
            labels=["A", "B", "X", "Y"],
        )

        assert len(pattern.positions) == 4
        assert pattern.labels[0] == "A"

    def test_grid_pattern_for_vents(self) -> None:
        """Grid pattern should work for honeycomb vents."""
        pattern = PatternPresets.honeycomb(rows=5, cols=7, spacing_mm=4)

        assert pattern.rows == 5
        assert pattern.columns == 7
        assert pattern.stagger is True
