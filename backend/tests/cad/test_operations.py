"""
Tests for CAD boolean and transformation operations.
"""

from __future__ import annotations

import pytest
from build123d import Box, Cylinder, Part, Compound

from app.cad.primitives import create_box, create_cylinder, create_sphere
from app.cad.operations import (
    union,
    difference,
    intersection,
    translate,
    rotate,
    scale,
    mirror,
    fillet,
    chamfer,
    shell,
    add_hole,
)
from app.cad.exceptions import ValidationError, GeometryError


# =============================================================================
# Boolean Operation Tests
# =============================================================================

class TestUnion:
    """Tests for union operation."""
    
    def test_union_two_boxes(self):
        """Test unioning two overlapping boxes."""
        box1 = create_box(50, 50, 50)
        box2 = translate(create_box(50, 50, 50), x=25)
        
        result = union(box1, box2)
        
        # Combined volume should be less than sum (overlap)
        assert isinstance(result, (Part, Compound))
        combined_volume = result.volume
        individual_sum = box1.volume + box2.volume
        assert combined_volume < individual_sum
    
    def test_union_multiple_shapes(self):
        """Test unioning more than two shapes."""
        box = create_box(50, 50, 50)
        cyl = create_cylinder(radius=15, height=60)
        sphere = create_sphere(radius=20)
        
        result = union(box, cyl, sphere)
        
        assert isinstance(result, (Part, Compound))
    
    def test_union_single_shape_fails(self):
        """Test that union with single shape raises error."""
        box = create_box(50, 50, 50)
        
        with pytest.raises(ValidationError):
            union(box)


class TestDifference:
    """Tests for difference operation."""
    
    def test_difference_creates_hole(self):
        """Test subtracting cylinder from box creates hole."""
        box = create_box(100, 100, 50)
        hole = create_cylinder(radius=20, height=60)
        
        result = difference(box, hole)
        
        original_volume = box.volume
        result_volume = result.volume
        hole_volume = hole.volume
        
        # Result should be approximately box - hole (capped by box height)
        assert result_volume < original_volume
        assert result_volume > 0
    
    def test_difference_multiple_tools(self):
        """Test subtracting multiple shapes."""
        box = create_box(100, 100, 50)
        hole1 = translate(create_cylinder(radius=10, height=60), x=25, y=25)
        hole2 = translate(create_cylinder(radius=10, height=60), x=-25, y=-25)
        
        result = difference(box, hole1, hole2)
        
        original_volume = box.volume
        result_volume = result.volume
        assert result_volume < original_volume
    
    def test_difference_no_tools_returns_base(self):
        """Test that difference with no tools returns original."""
        box = create_box(50, 50, 50)
        
        result = difference(box)
        
        assert result.volume == box.volume


class TestIntersection:
    """Tests for intersection operation."""
    
    def test_intersection_overlapping_shapes(self):
        """Test intersection of overlapping box and sphere."""
        box = create_box(100, 100, 100)
        sphere = create_sphere(radius=60)
        
        result = intersection(box, sphere)
        
        # Intersection should be smaller than either shape
        result_volume = result.volume
        assert result_volume < box.volume
        assert result_volume < sphere.volume
        assert result_volume > 0
    
    def test_intersection_single_shape_fails(self):
        """Test that intersection with single shape fails."""
        box = create_box(50, 50, 50)
        
        with pytest.raises(ValidationError):
            intersection(box)


# =============================================================================
# Transformation Tests
# =============================================================================

class TestTranslate:
    """Tests for translate operation."""
    
    def test_translate_moves_shape(self):
        """Test that translate moves bounding box correctly."""
        box = create_box(50, 50, 50)
        original_bb = box.bounding_box()
        
        moved = translate(box, x=100, y=50, z=25)
        moved_bb = moved.bounding_box()
        
        assert abs(moved_bb.min.X - (original_bb.min.X + 100)) < 0.01
        assert abs(moved_bb.min.Y - (original_bb.min.Y + 50)) < 0.01
        assert abs(moved_bb.min.Z - (original_bb.min.Z + 25)) < 0.01
    
    def test_translate_preserves_volume(self):
        """Test that translation preserves volume."""
        box = create_box(50, 50, 50)
        original_volume = box.volume
        
        moved = translate(box, x=1000)
        moved_volume = moved.volume
        
        assert abs(original_volume - moved_volume) < 0.01


class TestRotate:
    """Tests for rotate operation."""
    
    def test_rotate_around_z_axis(self):
        """Test rotation around Z axis."""
        box = create_box(100, 50, 25, centered=False)
        
        # 90 degree rotation should swap X and Y extents
        rotated = rotate(box, 90, axis=(0, 0, 1))
        
        bb = rotated.bounding_box()
        # After 90° rotation, width (50) becomes extent in X direction
        x_extent = bb.max.X - bb.min.X
        y_extent = bb.max.Y - bb.min.Y
        
        assert abs(x_extent - 50) < 1  # Original width
        assert abs(y_extent - 100) < 1  # Original length
    
    def test_rotate_preserves_volume(self):
        """Test that rotation preserves volume."""
        box = create_box(100, 50, 25)
        original_volume = box.volume
        
        rotated = rotate(box, 45)
        rotated_volume = rotated.volume
        
        assert abs(original_volume - rotated_volume) < 0.1


class TestScale:
    """Tests for scale operation."""
    
    def test_scale_doubles_size(self):
        """Test that scale factor 2 increases volume by 8x."""
        box = create_box(10, 10, 10)
        original_volume = box.volume  # 1000
        
        scaled = scale(box, 2.0)
        scaled_volume = scaled.volume
        
        # Volume scales as factor³
        assert abs(scaled_volume - (original_volume * 8)) < 1
    
    def test_scale_halves_size(self):
        """Test that scale factor 0.5 reduces volume to 1/8."""
        box = create_box(100, 100, 100)
        original_volume = box.volume
        
        scaled = scale(box, 0.5)
        scaled_volume = scaled.volume
        
        assert abs(scaled_volume - (original_volume / 8)) < 10
    
    def test_scale_zero_fails(self):
        """Test that zero scale factor fails."""
        box = create_box(50, 50, 50)
        
        with pytest.raises(ValidationError):
            scale(box, 0)
    
    def test_scale_negative_fails(self):
        """Test that negative scale factor fails."""
        box = create_box(50, 50, 50)
        
        with pytest.raises(ValidationError):
            scale(box, -1)


class TestMirror:
    """Tests for mirror operation."""
    
    def test_mirror_xy_plane(self):
        """Test mirroring across XY plane."""
        box = translate(create_box(50, 50, 50), z=50)
        
        mirrored = mirror(box, "XY")
        bb = mirrored.bounding_box()
        
        # Should now be below Z=0
        assert bb.max.Z < 0.1
    
    def test_mirror_invalid_plane_fails(self):
        """Test that invalid plane raises error."""
        box = create_box(50, 50, 50)
        
        with pytest.raises(ValidationError):
            mirror(box, "invalid")


# =============================================================================
# Edge Modification Tests
# =============================================================================

class TestFillet:
    """Tests for fillet operation."""
    
    def test_fillet_all_edges(self):
        """Test filleting all edges of a box."""
        box = create_box(50, 50, 50)
        original_volume = box.volume
        
        filleted = fillet(box, 3)
        filleted_volume = filleted.volume
        
        # Fillet removes material
        assert filleted_volume < original_volume
    
    def test_fillet_zero_radius_fails(self):
        """Test that zero radius fails."""
        box = create_box(50, 50, 50)
        
        with pytest.raises(ValidationError):
            fillet(box, 0)
    
    def test_fillet_too_large_fails(self):
        """Test that oversized fillet raises GeometryError."""
        box = create_box(50, 50, 50)
        
        with pytest.raises(GeometryError):
            fillet(box, 25)  # Too large for 50mm box edges


class TestChamfer:
    """Tests for chamfer operation."""
    
    def test_chamfer_all_edges(self):
        """Test chamfering all edges of a box."""
        box = create_box(50, 50, 50)
        original_volume = box.volume
        
        chamfered = chamfer(box, 3)
        chamfered_volume = chamfered.volume
        
        # Chamfer removes material
        assert chamfered_volume < original_volume
    
    def test_chamfer_zero_distance_fails(self):
        """Test that zero distance fails."""
        box = create_box(50, 50, 50)
        
        with pytest.raises(ValidationError):
            chamfer(box, 0)


class TestShell:
    """Tests for shell operation."""
    
    def test_shell_creates_hollow(self):
        """Test that shell creates hollow shape."""
        box = create_box(50, 50, 50)
        original_volume = box.volume
        
        shelled = shell(box, 5, ">Z")
        shelled_volume = shelled.volume
        
        # Shell removes interior material
        assert shelled_volume < original_volume
        assert shelled_volume > 0
    
    def test_shell_zero_thickness_fails(self):
        """Test that zero thickness fails."""
        box = create_box(50, 50, 50)
        
        with pytest.raises(ValidationError):
            shell(box, 0)


# =============================================================================
# Hole Operation Tests
# =============================================================================

class TestAddHole:
    """Tests for add_hole operation."""
    
    def test_add_hole_removes_material(self):
        """Test that adding hole removes material."""
        box = create_box(50, 50, 20)
        original_volume = box.volume
        
        with_hole = add_hole(box, diameter=10, depth=15)
        hole_volume = with_hole.volume
        
        assert hole_volume < original_volume
    
    def test_add_through_hole(self):
        """Test adding a through hole."""
        box = create_box(50, 50, 20)
        original_volume = box.volume
        
        with_hole = add_hole(box, diameter=10)  # No depth = through all
        hole_volume = with_hole.volume
        
        # Through hole removes π * r² * height
        expected_removal = 3.14159 * 25 * 20  # π * 5² * 20
        actual_removal = original_volume - hole_volume
        
        assert abs(actual_removal - expected_removal) < 10
