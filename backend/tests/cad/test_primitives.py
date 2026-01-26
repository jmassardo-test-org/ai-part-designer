"""
Tests for CAD primitive shape generation.

These tests verify that all primitive shapes are created correctly
with proper dimensions, validation, and CadQuery integration.
"""

from __future__ import annotations

import pytest
import cadquery as cq

from app.cad.primitives import (
    create_box,
    create_cylinder,
    create_sphere,
    create_cone,
    create_torus,
    create_wedge,
)
from app.cad.exceptions import ValidationError


# =============================================================================
# Box Tests
# =============================================================================

class TestCreateBox:
    """Tests for create_box function."""
    
    def test_create_box_basic(self):
        """Test creating a basic box with standard dimensions."""
        box = create_box(100, 50, 25)
        
        assert isinstance(box, cq.Workplane)
        # Verify volume (100 * 50 * 25 = 125000)
        volume = box.val().Volume()
        assert abs(volume - 125000) < 0.1
    
    def test_create_box_centered(self):
        """Test that box is centered by default on XY plane."""
        box = create_box(100, 100, 100, centered=True)
        
        bb = box.val().BoundingBox()
        # Should be centered on X and Y
        assert abs(bb.xmin + 50) < 0.01
        assert abs(bb.xmax - 50) < 0.01
        assert abs(bb.ymin + 50) < 0.01
        assert abs(bb.ymax - 50) < 0.01
        # Z should start at 0
        assert abs(bb.zmin) < 0.01
        assert abs(bb.zmax - 100) < 0.01
    
    def test_create_box_not_centered(self):
        """Test box creation without centering."""
        box = create_box(100, 100, 100, centered=False)
        
        bb = box.val().BoundingBox()
        assert abs(bb.xmin) < 0.01
        assert abs(bb.ymin) < 0.01
    
    def test_create_box_small_dimensions(self):
        """Test box with very small but valid dimensions."""
        box = create_box(0.1, 0.1, 0.1)
        
        volume = box.val().Volume()
        assert abs(volume - 0.001) < 0.0001
    
    def test_create_box_zero_dimension_fails(self):
        """Test that zero dimensions raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            create_box(0, 50, 25)
        
        assert "positive" in str(exc_info.value).lower()
    
    def test_create_box_negative_dimension_fails(self):
        """Test that negative dimensions raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            create_box(100, -50, 25)
        
        assert "positive" in str(exc_info.value).lower()


# =============================================================================
# Cylinder Tests
# =============================================================================

class TestCreateCylinder:
    """Tests for create_cylinder function."""
    
    def test_create_cylinder_with_radius(self):
        """Test cylinder creation with radius."""
        cyl = create_cylinder(radius=25, height=100)
        
        assert isinstance(cyl, cq.Workplane)
        # Volume = π * r² * h = π * 625 * 100
        expected_volume = 3.14159 * 625 * 100
        actual_volume = cyl.val().Volume()
        assert abs(actual_volume - expected_volume) < 100
    
    def test_create_cylinder_with_diameter(self):
        """Test cylinder creation with diameter."""
        cyl = create_cylinder(diameter=50, height=100)
        
        # Same as radius=25
        expected_volume = 3.14159 * 625 * 100
        actual_volume = cyl.val().Volume()
        assert abs(actual_volume - expected_volume) < 100
    
    def test_create_cylinder_centered(self):
        """Test that cylinder is centered on XY."""
        cyl = create_cylinder(radius=25, height=100, centered=True)
        
        bb = cyl.val().BoundingBox()
        # Should be centered on X and Y
        assert abs(bb.xmin + 25) < 0.1
        assert abs(bb.xmax - 25) < 0.1
        assert abs(bb.ymin + 25) < 0.1
        assert abs(bb.ymax - 25) < 0.1
    
    def test_create_cylinder_no_size_fails(self):
        """Test that cylinder without radius or diameter fails."""
        with pytest.raises(ValidationError) as exc_info:
            create_cylinder(height=100)
        
        assert "radius" in str(exc_info.value).lower() or "diameter" in str(exc_info.value).lower()
    
    def test_create_cylinder_both_sizes_fails(self):
        """Test that providing both radius and diameter fails."""
        with pytest.raises(ValidationError):
            create_cylinder(radius=25, diameter=50, height=100)


# =============================================================================
# Sphere Tests
# =============================================================================

class TestCreateSphere:
    """Tests for create_sphere function."""
    
    def test_create_sphere_with_radius(self):
        """Test sphere creation with radius."""
        sphere = create_sphere(radius=50)
        
        assert isinstance(sphere, cq.Workplane)
        # Volume = 4/3 * π * r³
        expected_volume = (4/3) * 3.14159 * (50 ** 3)
        actual_volume = sphere.val().Volume()
        assert abs(actual_volume - expected_volume) < 1000
    
    def test_create_sphere_with_diameter(self):
        """Test sphere creation with diameter."""
        sphere = create_sphere(diameter=100)
        
        # Same as radius=50
        expected_volume = (4/3) * 3.14159 * (50 ** 3)
        actual_volume = sphere.val().Volume()
        assert abs(actual_volume - expected_volume) < 1000
    
    def test_create_sphere_centered_at_origin(self):
        """Test that sphere is centered at origin."""
        sphere = create_sphere(radius=50)
        
        bb = sphere.val().BoundingBox()
        # Should be symmetric around origin
        assert abs(bb.xmin + 50) < 0.1
        assert abs(bb.xmax - 50) < 0.1
        assert abs(bb.zmin + 50) < 0.1
        assert abs(bb.zmax - 50) < 0.1
    
    def test_create_sphere_zero_radius_fails(self):
        """Test that zero radius fails."""
        with pytest.raises(ValidationError):
            create_sphere(radius=0)


# =============================================================================
# Cone Tests
# =============================================================================

class TestCreateCone:
    """Tests for create_cone function."""
    
    def test_create_cone_basic(self):
        """Test basic cone creation."""
        cone = create_cone(radius1=50, radius2=0, height=100)
        
        assert isinstance(cone, cq.Workplane)
        # Volume = 1/3 * π * h * (r1² + r1*r2 + r2²) for truncated cone
        # For cone (r2=0): 1/3 * π * 100 * 50² = 261799
        volume = cone.val().Volume()
        assert volume > 200000 and volume < 300000
    
    def test_create_truncated_cone(self):
        """Test truncated cone (frustum) creation."""
        cone = create_cone(radius1=50, radius2=25, height=100)
        
        volume = cone.val().Volume()
        # Frustum volume should be larger than cone
        assert volume > 300000
    
    def test_create_cone_using_diameter(self):
        """Test cone creation using diameter parameters."""
        cone = create_cone(diameter1=100, diameter2=50, height=100)
        
        # Same as radius1=50, radius2=25
        volume = cone.val().Volume()
        assert volume > 300000


# =============================================================================
# Torus Tests
# =============================================================================

class TestCreateTorus:
    """Tests for create_torus function."""
    
    def test_create_torus_basic(self):
        """Test basic torus creation."""
        torus = create_torus(major_radius=50, minor_radius=10)
        
        assert isinstance(torus, cq.Workplane)
        # Volume = 2 * π² * R * r² = 2 * π² * 50 * 100 = ~98696
        volume = torus.val().Volume()
        assert volume > 90000 and volume < 110000
    
    def test_create_torus_minor_equals_major_fails(self):
        """Test that minor radius >= major radius fails."""
        with pytest.raises(ValidationError):
            create_torus(major_radius=50, minor_radius=50)


# =============================================================================
# Wedge Tests
# =============================================================================

class TestCreateWedge:
    """Tests for create_wedge function."""
    
    def test_create_wedge_basic(self):
        """Test basic wedge creation."""
        wedge = create_wedge(length=100, width=50, height=30)
        
        assert isinstance(wedge, cq.Workplane)
        # Wedge is like half a box
        volume = wedge.val().Volume()
        assert volume > 0
    
    def test_create_wedge_negative_dimension_fails(self):
        """Test that negative dimensions fail."""
        with pytest.raises(ValidationError):
            create_wedge(length=-100, width=50, height=30)


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.cad
class TestPrimitiveIntegration:
    """Integration tests for combining primitives."""
    
    def test_primitives_can_be_combined(self):
        """Test that primitives work together in boolean operations."""
        from app.cad.operations import difference
        
        box = create_box(100, 100, 50)
        hole = create_cylinder(radius=10, height=60)
        
        result = difference(box, hole)
        
        # Volume should be less than original box
        box_volume = box.val().Volume()
        result_volume = result.val().Volume()
        assert result_volume < box_volume
    
    def test_primitives_can_be_exported(self):
        """Test that primitives can be exported to STEP and STL."""
        from app.cad.export import export_step, export_stl
        
        box = create_box(50, 50, 50)
        
        step_data = export_step(box)
        assert len(step_data) > 0
        assert b"ISO-10303" in step_data or b"STEP" in step_data
        
        stl_data = export_stl(box)
        assert len(stl_data) > 0
