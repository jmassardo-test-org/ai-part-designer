"""
Tests for CAD primitive shape generation.

These tests verify that all primitive shapes are created correctly
with proper dimensions, validation, and Build123d integration.
"""

from __future__ import annotations

import pytest
from build123d import Compound, Part

from app.cad.exceptions import ValidationError
from app.cad.primitives import (
    create_box,
    create_cone,
    create_cylinder,
    create_sphere,
    create_torus,
    create_wedge,
)

# =============================================================================
# Box Tests
# =============================================================================


class TestCreateBox:
    """Tests for create_box function."""

    def test_create_box_basic(self):
        """Test creating a basic box with standard dimensions."""
        box = create_box(100, 50, 25)

        assert isinstance(box, (Part, Compound))
        # Verify volume (100 * 50 * 25 = 125000)
        volume = box.volume
        assert abs(volume - 125000) < 0.1

    def test_create_box_centered(self):
        """Test that box is centered by default on XY plane."""
        box = create_box(100, 100, 100, centered=True)

        bb = box.bounding_box()
        # Should be centered on X and Y
        assert abs(bb.min.X + 50) < 0.01
        assert abs(bb.max.X - 50) < 0.01
        assert abs(bb.min.Y + 50) < 0.01
        assert abs(bb.max.Y - 50) < 0.01
        # Z should start at 0
        assert abs(bb.min.Z) < 0.01
        assert abs(bb.max.Z - 100) < 0.01

    def test_create_box_not_centered(self):
        """Test box creation without centering."""
        box = create_box(100, 100, 100, centered=False)

        bb = box.bounding_box()
        assert abs(bb.min.X) < 0.01
        assert abs(bb.min.Y) < 0.01

    def test_create_box_small_dimensions(self):
        """Test box with very small but valid dimensions."""
        box = create_box(0.1, 0.1, 0.1)

        volume = box.volume
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

        assert isinstance(cyl, (Part, Compound))
        # Volume = π * r² * h = π * 625 * 100
        expected_volume = 3.14159 * 625 * 100
        actual_volume = cyl.volume
        assert abs(actual_volume - expected_volume) < 100

    def test_create_cylinder_with_radius_50mm(self):
        """Test cylinder creation with radius 50mm."""
        cyl = create_cylinder(radius=50, height=100)

        # Volume = π * r² * h = π * 2500 * 100
        expected_volume = 3.14159 * 2500 * 100
        actual_volume = cyl.volume
        assert abs(actual_volume - expected_volume) < 100

    def test_create_cylinder_centered(self):
        """Test that cylinder is centered on XY."""
        cyl = create_cylinder(radius=25, height=100, centered=True)

        bb = cyl.bounding_box()
        # Should be centered on X and Y
        assert abs(bb.min.X + 25) < 0.1
        assert abs(bb.max.X - 25) < 0.1
        assert abs(bb.min.Y + 25) < 0.1
        assert abs(bb.max.Y - 25) < 0.1

    def test_create_cylinder_zero_radius_fails(self):
        """Test that cylinder with zero radius fails."""
        with pytest.raises(ValidationError):
            create_cylinder(radius=0, height=100)

    def test_create_cylinder_negative_height_fails(self):
        """Test that providing negative height fails."""
        with pytest.raises(ValidationError):
            create_cylinder(radius=25, height=-100)


# =============================================================================
# Sphere Tests
# =============================================================================


class TestCreateSphere:
    """Tests for create_sphere function."""

    def test_create_sphere_with_radius(self):
        """Test sphere creation with radius."""
        sphere = create_sphere(radius=50)

        assert isinstance(sphere, (Part, Compound))
        # Volume = 4/3 * π * r³
        expected_volume = (4 / 3) * 3.14159 * (50**3)
        actual_volume = sphere.volume
        assert abs(actual_volume - expected_volume) < 1000

    def test_create_sphere_with_larger_radius(self):
        """Test sphere creation with larger radius."""
        sphere = create_sphere(radius=100)

        # Volume = 4/3 * π * r³
        expected_volume = (4 / 3) * 3.14159 * (100**3)
        actual_volume = sphere.volume
        assert abs(actual_volume - expected_volume) < 5000

    def test_create_sphere_centered_at_origin(self):
        """Test that sphere is centered at origin."""
        sphere = create_sphere(radius=50)

        bb = sphere.bounding_box()
        # Should be symmetric around origin
        assert abs(bb.min.X + 50) < 0.1
        assert abs(bb.max.X - 50) < 0.1
        assert abs(bb.min.Z + 50) < 0.1
        assert abs(bb.max.Z - 50) < 0.1

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
        cone = create_cone(radius_bottom=50, radius_top=0, height=100)

        assert isinstance(cone, (Part, Compound))
        # Volume = 1/3 * π * h * (r1² + r1*r2 + r2²) for truncated cone
        # For cone (r2=0): 1/3 * π * 100 * 50² = 261799
        volume = cone.volume
        assert volume > 200000
        assert volume < 300000

    def test_create_truncated_cone(self):
        """Test truncated cone (frustum) creation."""
        cone = create_cone(radius_bottom=50, radius_top=25, height=100)

        volume = cone.volume
        # Frustum volume should be larger than cone
        assert volume > 300000

    def test_create_inverted_cone(self):
        """Test inverted cone creation (narrow at bottom)."""
        cone = create_cone(radius_bottom=25, radius_top=50, height=100)

        # Same volume as normal truncated cone with same radii
        volume = cone.volume
        assert volume > 300000


# =============================================================================
# Torus Tests
# =============================================================================


class TestCreateTorus:
    """Tests for create_torus function."""

    def test_create_torus_basic(self):
        """Test basic torus creation."""
        torus = create_torus(major_radius=50, minor_radius=10)

        assert isinstance(torus, (Part, Compound))
        # Volume = 2 * π² * R * r² = 2 * π² * 50 * 100 = ~98696
        volume = torus.volume
        assert volume > 90000
        assert volume < 110000

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

        assert isinstance(wedge, (Part, Compound))
        # Wedge is like half a box
        volume = wedge.volume
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
        box_volume = box.volume
        result_volume = result.volume
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
