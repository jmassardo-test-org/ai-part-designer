"""
Tests for CAD Modifier Service.

Tests modification operations, transformations, boolean operations,
and operation validation.
"""

from app.cad.modifier import (
    ModifyOperation,
    OperationType,
)

# =============================================================================
# Operation Type Tests
# =============================================================================


class TestOperationType:
    """Tests for operation type enum."""

    def test_transformation_types(self):
        """Test transformation operation types."""
        assert OperationType.TRANSLATE == "translate"
        assert OperationType.ROTATE == "rotate"
        assert OperationType.SCALE == "scale"
        assert OperationType.SCALE_AXIS == "scale_axis"
        assert OperationType.MIRROR == "mirror"

    def test_feature_types(self):
        """Test feature operation types."""
        assert OperationType.FILLET == "fillet"
        assert OperationType.CHAMFER == "chamfer"
        assert OperationType.SHELL == "shell"
        assert OperationType.ADD_HOLE == "add_hole"
        assert OperationType.ADD_POCKET == "add_pocket"
        assert OperationType.ADD_BOSS == "add_boss"

    def test_boolean_types(self):
        """Test boolean operation types."""
        assert OperationType.UNION == "union"
        assert OperationType.DIFFERENCE == "difference"
        assert OperationType.INTERSECTION == "intersection"


# =============================================================================
# Modify Operation Tests
# =============================================================================


class TestModifyOperation:
    """Tests for modification operation dataclass."""

    def test_create_translate_operation(self):
        """Test creating translate operation."""
        op = ModifyOperation(
            type=OperationType.TRANSLATE,
            params={"x": 10.0, "y": 20.0, "z": 0.0},
        )

        assert op.type == OperationType.TRANSLATE
        assert op.params["x"] == 10.0
        assert op.params["y"] == 20.0

    def test_create_rotate_operation(self):
        """Test creating rotate operation."""
        op = ModifyOperation(
            type=OperationType.ROTATE,
            params={"angle": 45.0, "axis": "z"},
        )

        assert op.type == OperationType.ROTATE
        assert op.params["angle"] == 45.0

    def test_create_scale_operation(self):
        """Test creating scale operation."""
        op = ModifyOperation(
            type=OperationType.SCALE,
            params={"factor": 2.0},
        )

        assert op.type == OperationType.SCALE
        assert op.params["factor"] == 2.0

    def test_create_fillet_operation(self):
        """Test creating fillet operation."""
        op = ModifyOperation(
            type=OperationType.FILLET,
            params={"radius": 3.0, "edges": "all"},
        )

        assert op.type == OperationType.FILLET
        assert op.params["radius"] == 3.0

    def test_create_shell_operation(self):
        """Test creating shell operation."""
        op = ModifyOperation(
            type=OperationType.SHELL,
            params={"thickness": 2.0, "faces_to_remove": ["top"]},
        )

        assert op.type == OperationType.SHELL
        assert op.params["thickness"] == 2.0


# =============================================================================
# Operation Validation Tests
# =============================================================================


class TestOperationValidation:
    """Tests for operation parameter validation."""

    def test_validate_translate_with_axis(self):
        """Test translate validation with axis specified."""
        op = ModifyOperation(
            type=OperationType.TRANSLATE,
            params={"x": 10.0},
        )

        errors = op.validate()
        assert len(errors) == 0

    def test_validate_translate_without_axis(self):
        """Test translate validation without axis raises error."""
        op = ModifyOperation(
            type=OperationType.TRANSLATE,
            params={},  # No axis specified
        )

        errors = op.validate()
        assert len(errors) > 0
        assert "axis" in errors[0].lower()

    def test_validate_rotate_with_angle(self):
        """Test rotate validation with angle specified."""
        op = ModifyOperation(
            type=OperationType.ROTATE,
            params={"angle": 90.0},
        )

        errors = op.validate()
        assert len(errors) == 0

    def test_validate_rotate_without_angle(self):
        """Test rotate validation without angle raises error."""
        op = ModifyOperation(
            type=OperationType.ROTATE,
            params={},  # No angle
        )

        errors = op.validate()
        assert len(errors) > 0
        assert "angle" in errors[0].lower()

    def test_validate_scale_with_factor(self):
        """Test scale validation with factor specified."""
        op = ModifyOperation(
            type=OperationType.SCALE,
            params={"factor": 1.5},
        )

        errors = op.validate()
        assert len(errors) == 0

    def test_validate_scale_without_factor(self):
        """Test scale validation without factor raises error."""
        op = ModifyOperation(
            type=OperationType.SCALE,
            params={},  # No factor
        )

        errors = op.validate()
        assert len(errors) > 0
        assert "factor" in errors[0].lower()

    def test_validate_scale_with_zero_factor(self):
        """Test scale validation with zero factor raises error."""
        op = ModifyOperation(
            type=OperationType.SCALE,
            params={"factor": 0},
        )

        errors = op.validate()
        assert len(errors) > 0

    def test_validate_scale_with_negative_factor(self):
        """Test scale validation with negative factor raises error."""
        op = ModifyOperation(
            type=OperationType.SCALE,
            params={"factor": -1.0},
        )

        errors = op.validate()
        assert len(errors) > 0


# =============================================================================
# Boolean Operation Tests
# =============================================================================


class TestBooleanOperations:
    """Tests for boolean operation configuration."""

    def test_union_operation(self):
        """Test creating union operation."""
        op = ModifyOperation(
            type=OperationType.UNION,
            params={"with_solid": "other_part.step"},
        )

        assert op.type == OperationType.UNION

    def test_difference_operation(self):
        """Test creating difference operation."""
        op = ModifyOperation(
            type=OperationType.DIFFERENCE,
            params={"subtract_solid": "cutout.step"},
        )

        assert op.type == OperationType.DIFFERENCE

    def test_intersection_operation(self):
        """Test creating intersection operation."""
        op = ModifyOperation(
            type=OperationType.INTERSECTION,
            params={"with_solid": "intersector.step"},
        )

        assert op.type == OperationType.INTERSECTION


# =============================================================================
# Feature Operation Tests
# =============================================================================


class TestFeatureOperations:
    """Tests for feature operation configuration."""

    def test_chamfer_operation(self):
        """Test creating chamfer operation."""
        op = ModifyOperation(
            type=OperationType.CHAMFER,
            params={"distance": 2.0},
        )

        assert op.type == OperationType.CHAMFER
        assert op.params["distance"] == 2.0

    def test_add_hole_operation(self):
        """Test creating add hole operation."""
        op = ModifyOperation(
            type=OperationType.ADD_HOLE,
            params={
                "diameter": 5.0,
                "depth": 10.0,
                "position": {"x": 25.0, "y": 25.0},
            },
        )

        assert op.type == OperationType.ADD_HOLE
        assert op.params["diameter"] == 5.0

    def test_add_pocket_operation(self):
        """Test creating pocket operation."""
        op = ModifyOperation(
            type=OperationType.ADD_POCKET,
            params={
                "width": 20.0,
                "length": 30.0,
                "depth": 5.0,
            },
        )

        assert op.type == OperationType.ADD_POCKET

    def test_add_boss_operation(self):
        """Test creating boss operation."""
        op = ModifyOperation(
            type=OperationType.ADD_BOSS,
            params={
                "diameter": 10.0,
                "height": 15.0,
            },
        )

        assert op.type == OperationType.ADD_BOSS


# =============================================================================
# Mirror Operation Tests
# =============================================================================


class TestMirrorOperation:
    """Tests for mirror operation."""

    def test_mirror_x_plane(self):
        """Test mirroring on X plane."""
        op = ModifyOperation(
            type=OperationType.MIRROR,
            params={"plane": "YZ"},  # Mirror across YZ plane (flip X)
        )

        assert op.type == OperationType.MIRROR
        assert op.params["plane"] == "YZ"

    def test_mirror_y_plane(self):
        """Test mirroring on Y plane."""
        op = ModifyOperation(
            type=OperationType.MIRROR,
            params={"plane": "XZ"},
        )

        assert op.params["plane"] == "XZ"

    def test_mirror_z_plane(self):
        """Test mirroring on Z plane."""
        op = ModifyOperation(
            type=OperationType.MIRROR,
            params={"plane": "XY"},
        )

        assert op.params["plane"] == "XY"


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in modifier operations."""

    def test_translate_single_axis(self):
        """Test translate with only one axis."""
        op = ModifyOperation(
            type=OperationType.TRANSLATE,
            params={"z": 50.0},
        )

        errors = op.validate()
        assert len(errors) == 0

    def test_large_scale_factor(self):
        """Test large scale factor."""
        op = ModifyOperation(
            type=OperationType.SCALE,
            params={"factor": 100.0},
        )

        errors = op.validate()
        assert len(errors) == 0

    def test_small_scale_factor(self):
        """Test very small (but positive) scale factor."""
        op = ModifyOperation(
            type=OperationType.SCALE,
            params={"factor": 0.001},
        )

        errors = op.validate()
        assert len(errors) == 0

    def test_360_degree_rotation(self):
        """Test 360 degree rotation."""
        op = ModifyOperation(
            type=OperationType.ROTATE,
            params={"angle": 360.0, "axis": "z"},
        )

        errors = op.validate()
        assert len(errors) == 0

    def test_negative_rotation(self):
        """Test negative rotation angle."""
        op = ModifyOperation(
            type=OperationType.ROTATE,
            params={"angle": -45.0, "axis": "y"},
        )

        errors = op.validate()
        assert len(errors) == 0


# =============================================================================
# Operation Chaining Tests
# =============================================================================


class TestOperationChaining:
    """Tests for multiple operation scenarios."""

    def test_multiple_operations_list(self):
        """Test creating list of operations."""
        operations = [
            ModifyOperation(
                type=OperationType.TRANSLATE,
                params={"x": 10.0, "y": 10.0},
            ),
            ModifyOperation(
                type=OperationType.ROTATE,
                params={"angle": 45.0, "axis": "z"},
            ),
            ModifyOperation(
                type=OperationType.FILLET,
                params={"radius": 2.0},
            ),
        ]

        assert len(operations) == 3

        # Validate all operations
        for op in operations:
            errors = op.validate()
            assert len(errors) == 0, f"Validation failed for {op.type}"
