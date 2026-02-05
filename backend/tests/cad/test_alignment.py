"""
Tests for CAD Alignment Module.

Tests alignment modes, bounding box calculations, and transformation operations.
"""

import pytest

from app.cad.alignment import (
    AlignmentAxis,
    AlignmentMode,
    AlignmentResult,
    AlignmentService,
    BoundingBox,
    TransformationResult,
)

# =============================================================================
# AlignmentMode Tests
# =============================================================================


class TestAlignmentMode:
    """Tests for AlignmentMode enum."""

    def test_face_mode(self):
        """Test face alignment mode."""
        assert AlignmentMode.FACE == "face"

    def test_edge_mode(self):
        """Test edge alignment mode."""
        assert AlignmentMode.EDGE == "edge"

    def test_center_mode(self):
        """Test center alignment mode."""
        assert AlignmentMode.CENTER == "center"

    def test_origin_mode(self):
        """Test origin alignment mode."""
        assert AlignmentMode.ORIGIN == "origin"

    def test_stack_modes(self):
        """Test stacking alignment modes."""
        assert AlignmentMode.STACK_Z == "stack_z"
        assert AlignmentMode.STACK_X == "stack_x"
        assert AlignmentMode.STACK_Y == "stack_y"

    def test_all_modes_are_strings(self):
        """Test all modes are string values."""
        for mode in AlignmentMode:
            assert isinstance(mode.value, str)


# =============================================================================
# AlignmentAxis Tests
# =============================================================================


class TestAlignmentAxis:
    """Tests for AlignmentAxis enum."""

    def test_single_axes(self):
        """Test single axis values."""
        assert AlignmentAxis.X == "x"
        assert AlignmentAxis.Y == "y"
        assert AlignmentAxis.Z == "z"

    def test_dual_axes(self):
        """Test dual axis values."""
        assert AlignmentAxis.XY == "xy"
        assert AlignmentAxis.XZ == "xz"
        assert AlignmentAxis.YZ == "yz"

    def test_all_axes(self):
        """Test all axes value."""
        assert AlignmentAxis.XYZ == "xyz"

    def test_all_values_are_strings(self):
        """Test all axis values are strings."""
        for axis in AlignmentAxis:
            assert isinstance(axis.value, str)


# =============================================================================
# BoundingBox Tests
# =============================================================================


class TestBoundingBox:
    """Tests for BoundingBox dataclass."""

    def test_basic_creation(self):
        """Test creating a basic bounding box."""
        bbox = BoundingBox(
            x_min=0.0,
            y_min=0.0,
            z_min=0.0,
            x_max=10.0,
            y_max=20.0,
            z_max=30.0,
        )

        assert bbox.x_min == 0.0
        assert bbox.x_max == 10.0
        assert bbox.y_min == 0.0
        assert bbox.y_max == 20.0
        assert bbox.z_min == 0.0
        assert bbox.z_max == 30.0

    def test_center_property(self):
        """Test center calculation."""
        bbox = BoundingBox(
            x_min=0.0,
            y_min=0.0,
            z_min=0.0,
            x_max=10.0,
            y_max=20.0,
            z_max=30.0,
        )

        center = bbox.center
        assert center == (5.0, 10.0, 15.0)

    def test_center_with_negative_values(self):
        """Test center calculation with negative coords."""
        bbox = BoundingBox(
            x_min=-10.0,
            y_min=-20.0,
            z_min=-30.0,
            x_max=10.0,
            y_max=20.0,
            z_max=30.0,
        )

        center = bbox.center
        assert center == (0.0, 0.0, 0.0)

    def test_size_property(self):
        """Test size calculation."""
        bbox = BoundingBox(
            x_min=0.0,
            y_min=0.0,
            z_min=0.0,
            x_max=10.0,
            y_max=20.0,
            z_max=30.0,
        )

        size = bbox.size
        assert size == (10.0, 20.0, 30.0)

    def test_size_with_offset(self):
        """Test size calculation with offset origin."""
        bbox = BoundingBox(
            x_min=5.0,
            y_min=10.0,
            z_min=15.0,
            x_max=15.0,
            y_max=30.0,
            z_max=45.0,
        )

        size = bbox.size
        assert size == (10.0, 20.0, 30.0)

    def test_min_point_property(self):
        """Test min_point property."""
        bbox = BoundingBox(
            x_min=1.0,
            y_min=2.0,
            z_min=3.0,
            x_max=10.0,
            y_max=20.0,
            z_max=30.0,
        )

        assert bbox.min_point == (1.0, 2.0, 3.0)

    def test_max_point_property(self):
        """Test max_point property."""
        bbox = BoundingBox(
            x_min=0.0,
            y_min=0.0,
            z_min=0.0,
            x_max=10.0,
            y_max=20.0,
            z_max=30.0,
        )

        assert bbox.max_point == (10.0, 20.0, 30.0)

    def test_degenerate_bbox(self):
        """Test a zero-size bounding box."""
        bbox = BoundingBox(
            x_min=5.0,
            y_min=5.0,
            z_min=5.0,
            x_max=5.0,
            y_max=5.0,
            z_max=5.0,
        )

        assert bbox.size == (0.0, 0.0, 0.0)
        assert bbox.center == (5.0, 5.0, 5.0)


# =============================================================================
# TransformationResult Tests
# =============================================================================


class TestTransformationResult:
    """Tests for TransformationResult dataclass."""

    def test_basic_creation(self):
        """Test creating a transformation result."""
        result = TransformationResult(
            transformed_shape=None,  # Would be a CQ Workplane
            translation=(1.0, 2.0, 3.0),
        )

        assert result.translation == (1.0, 2.0, 3.0)
        assert result.rotation is None
        assert result.original_bbox is None
        assert result.final_bbox is None

    def test_with_rotation(self):
        """Test transformation result with rotation."""
        result = TransformationResult(
            transformed_shape=None,
            translation=(0.0, 0.0, 0.0),
            rotation=(90.0, 0.0, 0.0),
        )

        assert result.rotation == (90.0, 0.0, 0.0)

    def test_with_bounding_boxes(self):
        """Test transformation result with bounding boxes."""
        original = BoundingBox(0, 0, 0, 10, 10, 10)
        final = BoundingBox(-5, -5, -5, 5, 5, 5)

        result = TransformationResult(
            transformed_shape=None,
            translation=(-5.0, -5.0, -5.0),
            original_bbox=original,
            final_bbox=final,
        )

        assert result.original_bbox.center == (5.0, 5.0, 5.0)
        assert result.final_bbox.center == (0.0, 0.0, 0.0)


# =============================================================================
# AlignmentResult Tests
# =============================================================================


class TestAlignmentResult:
    """Tests for AlignmentResult dataclass."""

    def test_basic_creation(self):
        """Test creating an alignment result."""
        total_bbox = BoundingBox(0, 0, 0, 100, 100, 100)

        result = AlignmentResult(
            combined_shape=None,
            transformations=[],
            total_bbox=total_bbox,
        )

        assert result.total_bbox.size == (100.0, 100.0, 100.0)
        assert result.transformations == []


# =============================================================================
# AlignmentService Tests
# =============================================================================


class TestAlignmentService:
    """Tests for AlignmentService class."""

    def test_service_creation(self):
        """Test creating alignment service."""
        service = AlignmentService()
        assert service is not None
        assert service._tolerance == 1e-6

    def test_translate_shape_with_cadquery(self):
        """Test translating a shape."""
        from build123d import Box

        service = AlignmentService()
        shape = Box(10, 10, 10)

        # Get original bounding box
        original_bbox = service.get_bounding_box(shape)
        original_center = original_bbox.center

        # Translate
        translated = service.translate_shape(shape, x=50, y=0, z=0)

        # Check new center
        new_bbox = service.get_bounding_box(translated)
        new_center = new_bbox.center

        assert abs(new_center[0] - original_center[0] - 50) < 0.01

    def test_get_bounding_box(self):
        """Test getting bounding box for a shape."""
        from build123d import Box

        service = AlignmentService()
        shape = Box(20, 30, 40)

        bbox = service.get_bounding_box(shape)

        # Box is centered at origin by default
        assert abs(bbox.size[0] - 20) < 0.01
        assert abs(bbox.size[1] - 30) < 0.01
        assert abs(bbox.size[2] - 40) < 0.01

    def test_align_to_origin(self):
        """Test aligning a shape to the origin."""
        from build123d import Box, Pos

        service = AlignmentService()
        # Create offset shape
        shape = Pos(100, 100, 100) * Box(10, 10, 10)

        result = service.align_to_origin(shape)

        # Center should now be at origin
        final_center = result.final_bbox.center
        assert abs(final_center[0]) < 0.01
        assert abs(final_center[1]) < 0.01
        assert abs(final_center[2]) < 0.01

    def test_rotate_shape_around_z(self):
        """Test rotating shape around Z axis."""
        from build123d import Box

        service = AlignmentService()
        shape = Box(10, 20, 5)

        # Rotate 90 degrees around Z
        rotated = service.rotate_shape(shape, 90, AlignmentAxis.Z)

        bbox = service.get_bounding_box(rotated)

        # After 90° rotation, width and length should swap
        assert abs(bbox.size[0] - 20) < 0.1  # Was Y, now X
        assert abs(bbox.size[1] - 10) < 0.1  # Was X, now Y


# =============================================================================
# Edge Cases
# =============================================================================


class TestAlignmentEdgeCases:
    """Tests for edge cases."""

    def test_tiny_bounding_box(self):
        """Test with very small bounding box values."""
        bbox = BoundingBox(
            x_min=0.0001,
            y_min=0.0001,
            z_min=0.0001,
            x_max=0.0002,
            y_max=0.0002,
            z_max=0.0002,
        )

        size = bbox.size
        assert size[0] == pytest.approx(0.0001, abs=1e-6)

    def test_large_bounding_box(self):
        """Test with large bounding box values."""
        bbox = BoundingBox(
            x_min=-1e6,
            y_min=-1e6,
            z_min=-1e6,
            x_max=1e6,
            y_max=1e6,
            z_max=1e6,
        )

        center = bbox.center
        assert center == (0.0, 0.0, 0.0)

        size = bbox.size
        assert size[0] == 2e6
