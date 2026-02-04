"""
Tests for Gridfinity pattern generators.
"""

import pytest
from build123d import Box, Cylinder, Part, Compound

from app.cad.gridfinity import (
    GRID_UNIT,
    HEIGHT_UNIT,
    BASE_HEIGHT,
    STACKING_LIP_HEIGHT,
    TOLERANCE,
    GridfinityBaseParams,
    GridfinityBinParams,
    GridfinityDividerParams,
    generate_gridfinity_baseplate,
    generate_gridfinity_bin,
    generate_gridfinity_divider,
    calculate_gridfinity_dimensions,
    get_gridfinity_templates,
)
from app.cad.templates import generate_from_template, TEMPLATE_REGISTRY


# =============================================================================
# Constants Tests
# =============================================================================

class TestGridfinityConstants:
    """Test Gridfinity standard dimensions."""
    
    def test_grid_unit_is_42mm(self):
        """Gridfinity standard grid is 42mm."""
        assert GRID_UNIT == 42.0
    
    def test_height_unit_is_7mm(self):
        """Gridfinity standard height unit is 7mm."""
        assert HEIGHT_UNIT == 7.0
    
    def test_base_height_is_5mm(self):
        """Base profile height is 5mm."""
        assert BASE_HEIGHT == 5.0
    
    def test_stacking_lip_height(self):
        """Stacking lip is about 4.2mm."""
        assert STACKING_LIP_HEIGHT == 4.2
    
    def test_tolerance_for_fit(self):
        """Standard tolerance for fit."""
        assert TOLERANCE == 0.25


# =============================================================================
# Data Class Tests
# =============================================================================

class TestGridfinityDataClasses:
    """Test Gridfinity parameter data classes."""
    
    def test_base_params_defaults(self):
        """Test default base plate parameters."""
        params = GridfinityBaseParams()
        assert params.grid_x == 3
        assert params.grid_y == 2
        assert params.magnet_holes is True
        assert params.screw_holes is False
    
    def test_bin_params_defaults(self):
        """Test default bin parameters."""
        params = GridfinityBinParams()
        assert params.grid_x == 1
        assert params.grid_y == 1
        assert params.height_units == 3
        assert params.stacking_lip is True
        assert params.scoop is False
    
    def test_divider_params_defaults(self):
        """Test default divider parameters."""
        params = GridfinityDividerParams()
        assert params.cells_x == 2
        assert params.cells_y == 2


# =============================================================================
# Base Plate Generator Tests
# =============================================================================

class TestGridfinityBaseplate:
    """Test Gridfinity base plate generator."""
    
    def test_generates_solid(self):
        """Generator produces a solid."""
        result = generate_gridfinity_baseplate()
        assert isinstance(result, (Part, Compound))
        assert result is not None
    
    def test_default_dimensions(self):
        """Default 3x2 baseplate has correct dimensions."""
        result = generate_gridfinity_baseplate(grid_x=3, grid_y=2)
        bb = result.bounding_box()
        
        # Should be approximately 3*42 x 2*42
        assert abs(bb.size.X - 3 * GRID_UNIT) < 1.0
        assert abs(bb.size.Y - 2 * GRID_UNIT) < 1.0
    
    def test_1x1_baseplate(self):
        """Single unit baseplate works."""
        result = generate_gridfinity_baseplate(grid_x=1, grid_y=1)
        bb = result.bounding_box()
        
        assert abs(bb.size.X - GRID_UNIT) < 1.0
        assert abs(bb.size.Y - GRID_UNIT) < 1.0
    
    def test_large_baseplate(self):
        """Large baseplate (6x4) works."""
        result = generate_gridfinity_baseplate(grid_x=6, grid_y=4)
        bb = result.bounding_box()
        
        assert abs(bb.size.X - 6 * GRID_UNIT) < 1.0
        assert abs(bb.size.Y - 4 * GRID_UNIT) < 1.0
    
    def test_with_magnet_holes(self):
        """Baseplate with magnet holes."""
        result = generate_gridfinity_baseplate(magnet_holes=True)
        assert result is not None
    
    def test_without_magnet_holes(self):
        """Baseplate without magnet holes."""
        result = generate_gridfinity_baseplate(magnet_holes=False)
        assert result is not None
    
    def test_with_screw_holes(self):
        """Baseplate with screw holes."""
        result = generate_gridfinity_baseplate(screw_holes=True)
        assert result is not None
    
    def test_custom_wall_thickness(self):
        """Custom wall thickness."""
        result = generate_gridfinity_baseplate(wall_thickness=3.0)
        assert result is not None


# =============================================================================
# Storage Bin Generator Tests
# =============================================================================

class TestGridfinityBin:
    """Test Gridfinity storage bin generator."""
    
    def test_generates_solid(self):
        """Generator produces a solid."""
        result = generate_gridfinity_bin()
        assert isinstance(result, (Part, Compound))
        assert result is not None
    
    def test_default_1x1x3_bin(self):
        """Default 1x1x3 bin has correct dimensions."""
        result = generate_gridfinity_bin()
        bb = result.bounding_box()
        
        # Width and depth should be just under 42mm (with tolerance)
        assert bb.size.X < GRID_UNIT
        assert bb.size.X > GRID_UNIT - 2
        assert bb.size.Y < GRID_UNIT
        assert bb.size.Y > GRID_UNIT - 2
    
    def test_bin_height_scaling(self):
        """Bin height scales with height units."""
        bin_3 = generate_gridfinity_bin(height_units=3)
        bin_6 = generate_gridfinity_bin(height_units=6)
        
        bb_3 = bin_3.bounding_box()
        bb_6 = bin_6.bounding_box()
        
        # 6-unit bin should be taller than 3-unit
        assert bb_6.size.Z > bb_3.size.Z
    
    def test_2x2_bin(self):
        """2x2 bin has correct footprint."""
        result = generate_gridfinity_bin(grid_x=2, grid_y=2)
        bb = result.bounding_box()
        
        # Should be approximately 2*42 - tolerance
        assert bb.size.X > 2 * GRID_UNIT - 2
        assert bb.size.Y > 2 * GRID_UNIT - 2
    
    def test_with_stacking_lip(self):
        """Bin with stacking lip is taller."""
        with_lip = generate_gridfinity_bin(stacking_lip=True)
        without_lip = generate_gridfinity_bin(stacking_lip=False)
        
        bb_with = with_lip.bounding_box()
        bb_without = without_lip.bounding_box()
        
        assert bb_with.size.Z > bb_without.size.Z
    
    def test_with_dividers_x(self):
        """Bin with X dividers."""
        result = generate_gridfinity_bin(grid_x=2, dividers_x=1)
        assert result is not None
    
    def test_with_dividers_y(self):
        """Bin with Y dividers."""
        result = generate_gridfinity_bin(grid_y=2, dividers_y=1)
        assert result is not None
    
    def test_with_multiple_dividers(self):
        """Bin with multiple dividers in both directions."""
        result = generate_gridfinity_bin(
            grid_x=3, 
            grid_y=2, 
            dividers_x=2, 
            dividers_y=1
        )
        assert result is not None
    
    def test_with_label_tab(self):
        """Bin with label tab."""
        result = generate_gridfinity_bin(label_tab=True)
        assert result is not None
    
    def test_with_scoop(self):
        """Bin with finger scoop."""
        result = generate_gridfinity_bin(scoop=True)
        assert result is not None
    
    def test_all_features_combined(self):
        """Bin with all features enabled."""
        result = generate_gridfinity_bin(
            grid_x=2,
            grid_y=2,
            height_units=4,
            dividers_x=1,
            dividers_y=1,
            label_tab=True,
            stacking_lip=True,
            scoop=True,
        )
        assert result is not None
    
    def test_custom_wall_thickness(self):
        """Custom wall thickness."""
        result = generate_gridfinity_bin(wall_thickness=2.0)
        assert result is not None
    
    def test_custom_floor_thickness(self):
        """Custom floor thickness."""
        result = generate_gridfinity_bin(floor_thickness=2.0)
        assert result is not None


# =============================================================================
# Divider Insert Generator Tests
# =============================================================================

class TestGridfinityDivider:
    """Test Gridfinity divider insert generator."""
    
    def test_generates_solid(self):
        """Generator produces a solid."""
        result = generate_gridfinity_divider()
        assert isinstance(result, (Part, Compound))
        assert result is not None
    
    def test_default_2x2_cells(self):
        """Default divider has 2x2 cells."""
        result = generate_gridfinity_divider(cells_x=2, cells_y=2)
        assert result is not None
    
    def test_3x3_cells(self):
        """3x3 cell divider."""
        result = generate_gridfinity_divider(cells_x=3, cells_y=3)
        assert result is not None
    
    def test_asymmetric_cells(self):
        """Asymmetric cell layout."""
        result = generate_gridfinity_divider(cells_x=4, cells_y=2)
        assert result is not None
    
    def test_larger_footprint(self):
        """Divider with larger footprint."""
        result = generate_gridfinity_divider(
            grid_x=2, 
            grid_y=2, 
            cells_x=4, 
            cells_y=4
        )
        assert result is not None


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestGridfinityUtilities:
    """Test utility functions."""
    
    def test_calculate_dimensions_1x1x3(self):
        """Calculate dimensions for 1x1x3 bin."""
        dims = calculate_gridfinity_dimensions(1, 1, 3)
        
        assert dims["outer_width"] == 42.0
        assert dims["outer_depth"] == 42.0
        assert dims["outer_height"] == 21.0  # 3 * 7mm
        assert dims["grid_unit"] == 42.0
        assert dims["height_unit"] == 7.0
    
    def test_calculate_dimensions_3x2x6(self):
        """Calculate dimensions for 3x2x6 bin."""
        dims = calculate_gridfinity_dimensions(3, 2, 6)
        
        assert dims["outer_width"] == 126.0  # 3 * 42mm
        assert dims["outer_depth"] == 84.0   # 2 * 42mm
        assert dims["outer_height"] == 42.0  # 6 * 7mm
    
    def test_get_templates_list(self):
        """Get list of available templates."""
        templates = get_gridfinity_templates()
        
        assert len(templates) == 3
        slugs = [t["slug"] for t in templates]
        assert "gridfinity-baseplate" in slugs
        assert "gridfinity-bin" in slugs
        assert "gridfinity-divider" in slugs
    
    def test_template_has_parameters(self):
        """Each template has parameters defined."""
        templates = get_gridfinity_templates()
        
        for template in templates:
            assert "parameters" in template
            assert len(template["parameters"]) > 0


# =============================================================================
# Template Registry Integration Tests
# =============================================================================

class TestGridfinityRegistration:
    """Test Gridfinity templates are registered correctly."""
    
    def test_baseplate_registered(self):
        """Baseplate template is registered."""
        assert "gridfinity-baseplate" in TEMPLATE_REGISTRY
    
    def test_bin_registered(self):
        """Bin template is registered."""
        assert "gridfinity-bin" in TEMPLATE_REGISTRY
    
    def test_divider_registered(self):
        """Divider template is registered."""
        assert "gridfinity-divider" in TEMPLATE_REGISTRY
    
    def test_generate_via_registry_baseplate(self):
        """Generate baseplate via template registry."""
        result = generate_from_template(
            "gridfinity-baseplate",
            {"grid_x": 2, "grid_y": 2}
        )
        assert result is not None
    
    def test_generate_via_registry_bin(self):
        """Generate bin via template registry."""
        result = generate_from_template(
            "gridfinity-bin",
            {"grid_x": 1, "grid_y": 1, "height_units": 3}
        )
        assert result is not None
    
    def test_generate_via_registry_divider(self):
        """Generate divider via template registry."""
        result = generate_from_template(
            "gridfinity-divider",
            {"cells_x": 3, "cells_y": 3}
        )
        assert result is not None


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestGridfinityEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_minimum_size_bin(self):
        """Smallest possible bin (1x1x1)."""
        result = generate_gridfinity_bin(
            grid_x=1, 
            grid_y=1, 
            height_units=1
        )
        assert result is not None
    
    def test_very_tall_bin(self):
        """Very tall bin (10 height units)."""
        result = generate_gridfinity_bin(height_units=10)
        bb = result.bounding_box()
        
        # Should be approximately 10 * 7mm + lip
        assert bb.size.Z >= 10 * HEIGHT_UNIT
    
    def test_many_dividers(self):
        """Bin with many dividers."""
        result = generate_gridfinity_bin(
            grid_x=4,
            grid_y=4,
            dividers_x=3,
            dividers_y=3,
        )
        assert result is not None
    
    def test_thin_walls(self):
        """Bin with thin walls (0.8mm)."""
        result = generate_gridfinity_bin(wall_thickness=0.8)
        assert result is not None
    
    def test_thick_walls(self):
        """Bin with thick walls (3mm)."""
        result = generate_gridfinity_bin(wall_thickness=3.0)
        assert result is not None
