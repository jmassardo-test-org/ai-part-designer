"""Tests for CAD v2 enclosure schemas."""

import pytest
from pydantic import ValidationError

from app.cad_v2.schemas.base import BoundingBox, Dimension
from app.cad_v2.schemas.enclosure import (
    EnclosureSpec,
    LidSpec,
    LidType,
    MountingTabSpec,
    ScrewSpec,
    SnapFitSpec,
    VentilationSpec,
    WallSide,
    WallSpec,
)


class TestWallSpec:
    """Tests for WallSpec schema."""

    def test_wallspec_defaults(self) -> None:
        """WallSpec should have default thickness."""
        wall = WallSpec()
        assert wall.thickness.mm == 2.0

    def test_wallspec_custom_thickness(self) -> None:
        """WallSpec should accept custom thickness."""
        wall = WallSpec(thickness=Dimension(value=3.0))
        assert wall.thickness.mm == 3.0

    def test_wallspec_per_side_override(self) -> None:
        """WallSpec should allow per-side overrides."""
        wall = WallSpec(
            thickness=Dimension(value=2.0),
            front=Dimension(value=3.0),
            bottom=Dimension(value=4.0),
        )
        assert wall.get_thickness(WallSide.FRONT).mm == 3.0
        assert wall.get_thickness(WallSide.BOTTOM).mm == 4.0
        assert wall.get_thickness(WallSide.BACK).mm == 2.0  # Default


class TestLidSpec:
    """Tests for LidSpec schema."""

    def test_lidspec_defaults(self) -> None:
        """LidSpec should have default type and side."""
        lid = LidSpec()
        assert lid.type == LidType.SNAP_FIT
        assert lid.side == WallSide.TOP

    def test_lidspec_snap_fit_auto_params(self) -> None:
        """LidSpec with snap_fit should auto-create snap_fit params."""
        lid = LidSpec(type=LidType.SNAP_FIT)
        assert lid.snap_fit is not None
        assert isinstance(lid.snap_fit, SnapFitSpec)

    def test_lidspec_screw_on_auto_params(self) -> None:
        """LidSpec with screw_on should auto-create screw params."""
        lid = LidSpec(type=LidType.SCREW_ON)
        assert lid.screws is not None
        assert isinstance(lid.screws, ScrewSpec)

    def test_lidspec_custom_snap_fit(self) -> None:
        """LidSpec should accept custom snap_fit params."""
        lid = LidSpec(
            type=LidType.SNAP_FIT,
            snap_fit=SnapFitSpec(lip_height=Dimension(value=3.0)),
        )
        assert lid.snap_fit is not None
        assert lid.snap_fit.lip_height.mm == 3.0


class TestScrewSpec:
    """Tests for ScrewSpec schema."""

    def test_screwspec_m2(self) -> None:
        """ScrewSpec.m2 should return M2 dimensions."""
        spec = ScrewSpec.m2()
        assert spec.hole_diameter.mm == 2.0
        assert spec.head_diameter.mm == 4.0

    def test_screwspec_m3(self) -> None:
        """ScrewSpec.m3 should return M3 dimensions."""
        spec = ScrewSpec.m3()
        assert spec.hole_diameter.mm == 3.0
        assert spec.head_diameter.mm == 6.0

    def test_screwspec_m4(self) -> None:
        """ScrewSpec.m4 should return M4 dimensions."""
        spec = ScrewSpec.m4()
        assert spec.hole_diameter.mm == 4.0
        assert spec.head_diameter.mm == 8.0


class TestVentilationSpec:
    """Tests for VentilationSpec schema."""

    def test_ventilation_disabled_by_default(self) -> None:
        """VentilationSpec should be disabled by default."""
        vent = VentilationSpec()
        assert vent.enabled is False

    def test_ventilation_default_sides(self) -> None:
        """VentilationSpec should default to left/right sides."""
        vent = VentilationSpec(enabled=True)
        assert WallSide.LEFT in vent.sides
        assert WallSide.RIGHT in vent.sides

    def test_ventilation_custom_pattern(self) -> None:
        """VentilationSpec should accept custom pattern."""
        vent = VentilationSpec(
            enabled=True,
            pattern="honeycomb",
            slot_width=Dimension(value=3.0),
        )
        assert vent.pattern == "honeycomb"
        assert vent.slot_width.mm == 3.0


class TestMountingTabSpec:
    """Tests for MountingTabSpec schema."""

    def test_mounting_tabs_disabled_by_default(self) -> None:
        """MountingTabSpec should be disabled by default."""
        tabs = MountingTabSpec()
        assert tabs.enabled is False

    def test_mounting_tabs_default_bottom(self) -> None:
        """MountingTabSpec should default to bottom side."""
        tabs = MountingTabSpec(enabled=True)
        assert WallSide.BOTTOM in tabs.sides

    def test_mounting_tabs_count_validation(self) -> None:
        """MountingTabSpec should validate count range."""
        # Valid
        MountingTabSpec(count_per_side=1)
        MountingTabSpec(count_per_side=6)

        # Invalid
        with pytest.raises(ValidationError):
            MountingTabSpec(count_per_side=0)
        with pytest.raises(ValidationError):
            MountingTabSpec(count_per_side=7)


class TestEnclosureSpec:
    """Tests for EnclosureSpec schema."""

    def test_enclosure_minimal(self) -> None:
        """EnclosureSpec should work with minimal params."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
        )
        assert spec.exterior.width_mm == 100
        assert spec.exterior.depth_mm == 80
        assert spec.exterior.height_mm == 40

    def test_enclosure_interior_calculation(self) -> None:
        """EnclosureSpec.interior should calculate interior dimensions."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            walls=WallSpec(thickness=Dimension(value=2.0)),
        )
        interior = spec.interior
        # Interior = exterior - 2*wall (for width/depth), - wall (for height/open top)
        assert interior.width_mm == 96  # 100 - 2*2
        assert interior.depth_mm == 76  # 80 - 2*2
        assert interior.height_mm == 38  # 40 - 2 (open top)

    def test_enclosure_rejects_too_thick_walls(self) -> None:
        """EnclosureSpec should reject walls thicker than half exterior."""
        with pytest.raises(ValidationError) as exc_info:
            EnclosureSpec(
                exterior=BoundingBox(
                    width=Dimension(value=10),
                    depth=Dimension(value=80),
                    height=Dimension(value=40),
                ),
                walls=WallSpec(thickness=Dimension(value=6.0)),  # Too thick
            )
        # Error comes from Dimension validator when interior calc produces negative
        assert "greater than 0" in str(exc_info.value) or "must be positive" in str(exc_info.value)

    def test_enclosure_with_lid(self) -> None:
        """EnclosureSpec should accept lid configuration."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            lid=LidSpec(type=LidType.SCREW_ON),
        )
        assert spec.lid is not None
        assert spec.lid.type == LidType.SCREW_ON

    def test_enclosure_with_corner_radius(self) -> None:
        """EnclosureSpec should accept corner radius."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            corner_radius=Dimension(value=5.0),
        )
        assert spec.corner_radius is not None
        assert spec.corner_radius.mm == 5.0

    def test_enclosure_with_ventilation(self) -> None:
        """EnclosureSpec should accept ventilation config."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            ventilation=VentilationSpec(enabled=True),
        )
        assert spec.ventilation.enabled is True

    def test_enclosure_with_mounting_tabs(self) -> None:
        """EnclosureSpec should accept mounting tabs config."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            mounting_tabs=MountingTabSpec(enabled=True),
        )
        assert spec.mounting_tabs.enabled is True

    def test_enclosure_with_metadata(self) -> None:
        """EnclosureSpec should accept name and description."""
        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            name="Pi 5 Enclosure",
            description="Enclosure for Raspberry Pi 5 with LCD",
        )
        assert spec.name == "Pi 5 Enclosure"
        assert spec.description is not None


class TestWallSide:
    """Tests for WallSide enum."""

    def test_wall_side_values(self) -> None:
        """WallSide enum should have all six sides."""
        assert WallSide.FRONT.value == "front"
        assert WallSide.BACK.value == "back"
        assert WallSide.LEFT.value == "left"
        assert WallSide.RIGHT.value == "right"
        assert WallSide.TOP.value == "top"
        assert WallSide.BOTTOM.value == "bottom"


class TestLidType:
    """Tests for LidType enum."""

    def test_lid_type_values(self) -> None:
        """LidType enum should have expected values."""
        assert LidType.SNAP_FIT.value == "snap_fit"
        assert LidType.SCREW_ON.value == "screw_on"
        assert LidType.SLIDE_ON.value == "slide_on"
        assert LidType.FRICTION.value == "friction"
        assert LidType.HINGE.value == "hinge"
        assert LidType.NONE.value == "none"
