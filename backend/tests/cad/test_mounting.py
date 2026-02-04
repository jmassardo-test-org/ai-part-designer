"""
Tests for CAD Mounting Module.

Tests mounting types, configurations, and generator classes.
"""

import pytest

from app.cad.mounting import (
    MountingType,
    SnapFitStyle,
    DINRailSize,
    SnapFitConfig,
    SnapFitResult,
    DINRailConfig,
    DINRailResult,
    WallMountConfig,
    WallMountResult,
    PCBStandoffConfig,
    PCBStandoffResult,
)


# =============================================================================
# MountingType Tests
# =============================================================================

class TestMountingType:
    """Tests for MountingType enum."""

    def test_snap_fit_type(self):
        """Test snap fit mounting type."""
        assert MountingType.SNAP_FIT == "snap_fit"

    def test_din_rail_type(self):
        """Test DIN rail mounting type."""
        assert MountingType.DIN_RAIL == "din_rail"

    def test_wall_mount_type(self):
        """Test wall mount type."""
        assert MountingType.WALL_MOUNT == "wall_mount"

    def test_pcb_standoff_type(self):
        """Test PCB standoff type."""
        assert MountingType.PCB_STANDOFF == "pcb_standoff"

    def test_all_types_are_strings(self):
        """Test all mounting types are strings."""
        for mount_type in MountingType:
            assert isinstance(mount_type.value, str)


# =============================================================================
# SnapFitStyle Tests
# =============================================================================

class TestSnapFitStyle:
    """Tests for SnapFitStyle enum."""

    def test_cantilever_style(self):
        """Test cantilever snap fit style."""
        assert SnapFitStyle.CANTILEVER == "cantilever"

    def test_annular_style(self):
        """Test annular snap fit style."""
        assert SnapFitStyle.ANNULAR == "annular"

    def test_torsional_style(self):
        """Test torsional snap fit style."""
        assert SnapFitStyle.TORSIONAL == "torsional"


# =============================================================================
# DINRailSize Tests
# =============================================================================

class TestDINRailSize:
    """Tests for DINRailSize enum."""

    def test_ts35_size(self):
        """Test TS35 DIN rail size."""
        assert DINRailSize.TS35 == "ts35"

    def test_ts32_size(self):
        """Test TS32 DIN rail size."""
        assert DINRailSize.TS32 == "ts32"

    def test_g32_size(self):
        """Test G32 DIN rail size."""
        assert DINRailSize.G32 == "g32"


# =============================================================================
# SnapFitConfig Tests
# =============================================================================

class TestSnapFitConfig:
    """Tests for SnapFitConfig dataclass."""

    def test_default_config(self):
        """Test default snap fit configuration."""
        config = SnapFitConfig()
        
        assert config.length == 15.0
        assert config.width == 8.0
        assert config.thickness == 2.0

    def test_hook_defaults(self):
        """Test hook dimension defaults."""
        config = SnapFitConfig()
        
        assert config.hook_height == 2.5
        assert config.hook_angle == 30.0
        assert config.hook_undercut == 1.0

    def test_cantilever_defaults(self):
        """Test cantilever property defaults."""
        config = SnapFitConfig()
        
        assert config.taper == 0.8
        assert config.deflection == 2.0

    def test_default_material(self):
        """Test default material is ABS."""
        config = SnapFitConfig()
        
        assert config.material == "ABS"

    def test_default_style(self):
        """Test default style is cantilever."""
        config = SnapFitConfig()
        
        assert config.style == SnapFitStyle.CANTILEVER

    def test_custom_config(self):
        """Test custom snap fit configuration."""
        config = SnapFitConfig(
            length=20.0,
            width=10.0,
            hook_height=3.0,
            material="PETG",
            style=SnapFitStyle.ANNULAR,
        )
        
        assert config.length == 20.0
        assert config.width == 10.0
        assert config.hook_height == 3.0
        assert config.material == "PETG"
        assert config.style == SnapFitStyle.ANNULAR


# =============================================================================
# SnapFitResult Tests
# =============================================================================

class TestSnapFitResult:
    """Tests for SnapFitResult dataclass."""

    def test_basic_result(self):
        """Test basic snap fit result."""
        result = SnapFitResult(clip=None)
        
        assert result.clip is None
        assert result.receptacle is None
        assert result.estimated_retention_force == 0.0
        assert result.max_deflection == 0.0
        assert result.metadata == {}

    def test_result_with_engineering_data(self):
        """Test result with engineering data."""
        result = SnapFitResult(
            clip=None,
            estimated_retention_force=5.5,
            max_deflection=2.0,
        )
        
        assert result.estimated_retention_force == 5.5
        assert result.max_deflection == 2.0


# =============================================================================
# DINRailConfig Tests
# =============================================================================

class TestDINRailConfig:
    """Tests for DINRailConfig dataclass."""

    def test_default_config(self):
        """Test default DIN rail configuration."""
        config = DINRailConfig()
        
        assert config.rail_size == DINRailSize.TS35
        assert config.mount_width == 50.0
        assert config.mount_height == 30.0
        assert config.mount_thickness == 3.0

    def test_clip_defaults(self):
        """Test clip configuration defaults."""
        config = DINRailConfig()
        
        assert config.clip_spring_tension == 2.0
        assert config.clip_style == "spring"

    def test_corner_radius_default(self):
        """Test corner radius default."""
        config = DINRailConfig()
        
        assert config.corner_radius == 2.0

    def test_custom_config(self):
        """Test custom DIN rail configuration."""
        config = DINRailConfig(
            rail_size=DINRailSize.TS32,
            mount_width=70.0,
            clip_style="latch",
        )
        
        assert config.rail_size == DINRailSize.TS32
        assert config.mount_width == 70.0
        assert config.clip_style == "latch"


# =============================================================================
# DINRailResult Tests
# =============================================================================

class TestDINRailResult:
    """Tests for DINRailResult dataclass."""

    def test_basic_result(self):
        """Test basic DIN rail result."""
        result = DINRailResult(mount=None)
        
        assert result.mount is None
        assert result.rail_compatibility == "TS35"
        assert result.metadata == {}


# =============================================================================
# WallMountConfig Tests
# =============================================================================

class TestWallMountConfig:
    """Tests for WallMountConfig dataclass."""

    def test_default_config(self):
        """Test default wall mount configuration."""
        config = WallMountConfig()
        
        assert config.bracket_width == 40.0
        assert config.bracket_height == 25.0
        assert config.bracket_depth == 20.0
        assert config.bracket_thickness == 3.0

    def test_keyhole_defaults(self):
        """Test keyhole pattern defaults."""
        config = WallMountConfig()
        
        assert config.keyhole_count == 2
        assert config.keyhole_spacing == 30.0
        assert config.keyhole_large_dia == 8.0
        assert config.keyhole_small_dia == 4.5
        assert config.keyhole_slot_length == 6.0

    def test_screw_default(self):
        """Test default screw size."""
        config = WallMountConfig()
        
        assert config.screw_size == "M4"

    def test_rib_defaults(self):
        """Test rib/stiffener defaults."""
        config = WallMountConfig()
        
        assert config.add_ribs is True
        assert config.rib_count == 2
        assert config.rib_thickness == 2.0

    def test_custom_config(self):
        """Test custom wall mount configuration."""
        config = WallMountConfig(
            bracket_width=60.0,
            keyhole_count=4,
            add_ribs=False,
        )
        
        assert config.bracket_width == 60.0
        assert config.keyhole_count == 4
        assert config.add_ribs is False


# =============================================================================
# WallMountResult Tests
# =============================================================================

class TestWallMountResult:
    """Tests for WallMountResult dataclass."""

    def test_basic_result(self):
        """Test basic wall mount result."""
        result = WallMountResult(bracket=None)
        
        assert result.bracket is None
        assert result.recommended_screws == "M4x25 pan head"
        assert result.recommended_anchors == "Wall anchors for M4"
        assert result.metadata == {}


# =============================================================================
# PCBStandoffConfig Tests
# =============================================================================

class TestPCBStandoffConfig:
    """Tests for PCBStandoffConfig dataclass."""

    def test_default_config(self):
        """Test default PCB standoff configuration."""
        config = PCBStandoffConfig()
        
        assert config.height == 10.0
        assert config.outer_diameter == 6.0
        assert config.inner_diameter == 3.2

    def test_base_defaults(self):
        """Test base dimension defaults."""
        config = PCBStandoffConfig()
        
        assert config.base_diameter == 8.0
        assert config.base_height == 2.0

    def test_screw_defaults(self):
        """Test screw configuration defaults."""
        config = PCBStandoffConfig()
        
        assert config.screw_size == "M3"
        assert config.threaded is True

    def test_hex_outer_default(self):
        """Test hex outer default is False."""
        config = PCBStandoffConfig()
        
        assert config.hex_outer is False

    def test_custom_config(self):
        """Test custom PCB standoff configuration."""
        config = PCBStandoffConfig(
            height=15.0,
            outer_diameter=8.0,
            screw_size="M4",
            hex_outer=True,
        )
        
        assert config.height == 15.0
        assert config.outer_diameter == 8.0
        assert config.screw_size == "M4"
        assert config.hex_outer is True


# =============================================================================
# PCBStandoffResult Tests
# =============================================================================

class TestPCBStandoffResult:
    """Tests for PCBStandoffResult dataclass."""

    def test_basic_result(self):
        """Test basic PCB standoff result."""
        result = PCBStandoffResult(standoff=None)
        
        assert result.standoff is None
        assert result.positions == []
        assert result.metadata == {}

    def test_result_with_positions(self):
        """Test result with standoff positions."""
        positions = [(0, 0), (50, 0), (0, 30), (50, 30)]
        result = PCBStandoffResult(
            standoff=None,
            positions=positions,
        )
        
        assert len(result.positions) == 4
        assert (50, 30) in result.positions


# =============================================================================
# Edge Cases
# =============================================================================

class TestMountingEdgeCases:
    """Tests for edge cases in mounting module."""

    def test_zero_dimensions_config(self):
        """Test configuration with zero dimensions."""
        config = SnapFitConfig(length=0, width=0, thickness=0)
        
        assert config.length == 0
        assert config.width == 0
        assert config.thickness == 0

    def test_negative_dimensions_allowed(self):
        """Test that negative dimensions are allowed (no validation)."""
        config = PCBStandoffConfig(height=-5.0)
        
        assert config.height == -5.0

    def test_very_large_dimensions(self):
        """Test configuration with very large dimensions."""
        config = WallMountConfig(bracket_width=1000.0)
        
        assert config.bracket_width == 1000.0

    def test_empty_metadata(self):
        """Test default empty metadata."""
        snap_result = SnapFitResult(clip=None)
        din_result = DINRailResult(mount=None)
        wall_result = WallMountResult(bracket=None)
        pcb_result = PCBStandoffResult(standoff=None)
        
        assert snap_result.metadata == {}
        assert din_result.metadata == {}
        assert wall_result.metadata == {}
        assert pcb_result.metadata == {}
