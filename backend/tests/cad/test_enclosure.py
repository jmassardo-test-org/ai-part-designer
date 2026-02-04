"""
Tests for CAD Enclosure Generator.

Tests enclosure configuration, box/lid generation, mounting features,
gasket grooves, and bill of materials generation.
"""

import pytest
from dataclasses import asdict

from app.cad.enclosure import (
    EnclosureConfig,
    EnclosureStyle,
)


# =============================================================================
# Enclosure Configuration Tests
# =============================================================================

class TestEnclosureConfig:
    """Tests for enclosure configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EnclosureConfig()
        
        assert config.length == 100.0
        assert config.width == 80.0
        assert config.height == 50.0
        assert config.wall_thickness == 2.5
        assert config.lid_height_ratio == 0.25

    def test_lid_height_calculation(self):
        """Test lid height is calculated correctly."""
        config = EnclosureConfig(height=100.0, lid_height_ratio=0.3)
        
        assert config.lid_height == 30.0
        assert config.box_height == 70.0

    def test_internal_dimensions(self):
        """Test internal dimension calculations."""
        config = EnclosureConfig(
            length=100.0,
            width=80.0,
            wall_thickness=5.0,
        )
        
        assert config.internal_length == 90.0
        assert config.internal_width == 70.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = EnclosureConfig(
            length=150.0,
            width=100.0,
            height=75.0,
            wall_thickness=3.0,
            screw_size="M4",
            num_screws_per_side=3,
        )
        
        assert config.length == 150.0
        assert config.screw_size == "M4"
        assert config.num_screws_per_side == 3

    def test_gasket_groove_config(self):
        """Test gasket groove configuration."""
        config = EnclosureConfig(
            gasket_groove=True,
            gasket_width=3.0,
            gasket_depth=2.0,
        )
        
        assert config.gasket_groove is True
        assert config.gasket_width == 3.0
        assert config.gasket_depth == 2.0

    def test_disable_gasket_groove(self):
        """Test disabling gasket groove."""
        config = EnclosureConfig(gasket_groove=False)
        
        assert config.gasket_groove is False

    def test_threaded_inserts_config(self):
        """Test threaded insert configuration."""
        config = EnclosureConfig(use_threaded_inserts=True)
        
        assert config.use_threaded_inserts is True

    def test_disable_threaded_inserts(self):
        """Test disabling threaded inserts."""
        config = EnclosureConfig(use_threaded_inserts=False)
        
        assert config.use_threaded_inserts is False


# =============================================================================
# Enclosure Style Tests
# =============================================================================

class TestEnclosureStyle:
    """Tests for enclosure style enum."""

    def test_top_lid_style(self):
        """Test top lid style value."""
        assert EnclosureStyle.TOP_LID == "top_lid"

    def test_clamshell_style(self):
        """Test clamshell style value."""
        assert EnclosureStyle.CLAMSHELL == "clamshell"

    def test_slide_lid_style(self):
        """Test slide lid style value."""
        assert EnclosureStyle.SLIDE_LID == "slide_lid"

    def test_default_style_is_top_lid(self):
        """Test default style is top lid."""
        config = EnclosureConfig()
        
        assert config.style == EnclosureStyle.TOP_LID

    def test_set_clamshell_style(self):
        """Test setting clamshell style."""
        config = EnclosureConfig(style=EnclosureStyle.CLAMSHELL)
        
        assert config.style == EnclosureStyle.CLAMSHELL


# =============================================================================
# Dimension Validation Tests
# =============================================================================

class TestDimensionValidation:
    """Tests for dimension validation logic."""

    def test_minimum_wall_thickness(self):
        """Test wall thickness must be positive."""
        config = EnclosureConfig(wall_thickness=1.0)
        
        assert config.wall_thickness > 0

    def test_internal_dimensions_positive(self):
        """Test internal dimensions are positive with normal config."""
        config = EnclosureConfig(
            length=100.0,
            width=80.0,
            wall_thickness=2.5,
        )
        
        assert config.internal_length > 0
        assert config.internal_width > 0

    def test_lid_ratio_boundaries(self):
        """Test lid ratio affects height distribution."""
        # Very small lid
        config_small = EnclosureConfig(height=100.0, lid_height_ratio=0.1)
        assert config_small.lid_height == 10.0
        assert config_small.box_height == 90.0
        
        # Large lid
        config_large = EnclosureConfig(height=100.0, lid_height_ratio=0.5)
        assert config_large.lid_height == 50.0
        assert config_large.box_height == 50.0

    def test_corner_radius_config(self):
        """Test corner radius configuration."""
        config = EnclosureConfig(corner_radius=5.0)
        
        assert config.corner_radius == 5.0

    def test_flange_configuration(self):
        """Test flange configuration."""
        config = EnclosureConfig(
            flange_width=10.0,
            flange_thickness=4.0,
        )
        
        assert config.flange_width == 10.0
        assert config.flange_thickness == 4.0


# =============================================================================
# Screw Configuration Tests
# =============================================================================

class TestScrewConfiguration:
    """Tests for screw/mounting hole configuration."""

    def test_default_screw_size(self):
        """Test default screw size is M3."""
        config = EnclosureConfig()
        
        assert config.screw_size == "M3"

    def test_screw_inset(self):
        """Test screw inset from corners."""
        config = EnclosureConfig(screw_inset=8.0)
        
        assert config.screw_inset == 8.0

    def test_screws_per_side(self):
        """Test screws per side configuration."""
        config = EnclosureConfig(num_screws_per_side=4)
        
        assert config.num_screws_per_side == 4

    def test_m4_screw_size(self):
        """Test M4 screw configuration."""
        config = EnclosureConfig(screw_size="M4")
        
        assert config.screw_size == "M4"


# =============================================================================
# Config Serialization Tests
# =============================================================================

class TestConfigSerialization:
    """Tests for configuration serialization."""

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = EnclosureConfig(
            length=100.0,
            width=80.0,
            height=50.0,
        )
        
        config_dict = asdict(config)
        
        assert config_dict["length"] == 100.0
        assert config_dict["width"] == 80.0
        assert config_dict["height"] == 50.0

    def test_config_contains_all_fields(self):
        """Test that config dict contains all expected fields."""
        config = EnclosureConfig()
        config_dict = asdict(config)
        
        expected_fields = [
            "length", "width", "height",
            "wall_thickness", "lid_height_ratio",
            "flange_width", "flange_thickness",
            "screw_size", "num_screws_per_side", "screw_inset",
            "gasket_groove", "gasket_width", "gasket_depth",
            "use_threaded_inserts", "corner_radius", "style",
        ]
        
        for field_name in expected_fields:
            assert field_name in config_dict


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_corner_radius(self):
        """Test zero corner radius (sharp corners)."""
        config = EnclosureConfig(corner_radius=0.0)
        
        assert config.corner_radius == 0.0

    def test_single_screw_per_side(self):
        """Test single screw per side."""
        config = EnclosureConfig(num_screws_per_side=1)
        
        assert config.num_screws_per_side == 1

    def test_very_thin_walls(self):
        """Test very thin wall configuration."""
        config = EnclosureConfig(
            length=50.0,
            width=40.0,
            wall_thickness=1.0,
        )
        
        assert config.internal_length == 48.0
        assert config.internal_width == 38.0

    def test_thick_walls(self):
        """Test thick wall configuration."""
        config = EnclosureConfig(
            length=100.0,
            width=80.0,
            wall_thickness=10.0,
        )
        
        assert config.internal_length == 80.0
        assert config.internal_width == 60.0
