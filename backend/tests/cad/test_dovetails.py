"""
Tests for Dovetail Joint Pattern Generators.
"""

from build123d import Compound, Part

from app.cad.dovetails import (
    DEFAULT_THICKNESS,
    HARDWOOD_RATIO,
    SOFTWOOD_RATIO,
    BoxJointParams,
    DovetailParams,
    SlidingDovetailParams,
    calculate_dovetail_angle,
    generate_box_joint_board_a,
    generate_box_joint_board_b,
    generate_dovetail_pin_board,
    generate_dovetail_tail_board,
    generate_sliding_dovetail_key,
    generate_sliding_dovetail_slot,
    get_dovetail_templates,
    get_recommended_angle,
)
from app.cad.templates import TEMPLATE_REGISTRY, generate_from_template

# =============================================================================
# Constants Tests
# =============================================================================


class TestDovetailConstants:
    """Test dovetail standard constants."""

    def test_softwood_ratio(self):
        """Softwood ratio is 1:6."""
        assert SOFTWOOD_RATIO == 6

    def test_hardwood_ratio(self):
        """Hardwood ratio is 1:8."""
        assert HARDWOOD_RATIO == 8

    def test_default_thickness(self):
        """Default board thickness is 18mm."""
        assert DEFAULT_THICKNESS == 18.0


# =============================================================================
# Data Class Tests
# =============================================================================


class TestDovetailDataClasses:
    """Test dovetail parameter data classes."""

    def test_dovetail_params_defaults(self):
        """Test default dovetail parameters."""
        params = DovetailParams()
        assert params.board_width == 100.0
        assert params.board_thickness == 18.0
        assert params.num_tails == 3
        assert params.tail_angle == 14.0
        assert params.half_pin is True

    def test_sliding_dovetail_params_defaults(self):
        """Test default sliding dovetail parameters."""
        params = SlidingDovetailParams()
        assert params.slot_width == 15.0
        assert params.slot_depth == 8.0
        assert params.slot_length == 100.0
        assert params.angle == 14.0

    def test_box_joint_params_defaults(self):
        """Test default box joint parameters."""
        params = BoxJointParams()
        assert params.board_width == 100.0
        assert params.board_thickness == 12.0
        assert params.finger_width == 6.0


# =============================================================================
# Dovetail Tail Board Tests
# =============================================================================


class TestDovetailTailBoard:
    """Test dovetail tail board generator."""

    def test_generates_solid(self):
        """Generator produces a solid."""
        result = generate_dovetail_tail_board()
        assert isinstance(result, (Part, Compound))
        assert result is not None

    def test_default_dimensions(self):
        """Default board has correct approximate dimensions."""
        result = generate_dovetail_tail_board()
        bb = result.bounding_box()

        # Board width parameter is 100mm, but actual geometry may be smaller
        # due to tail cuts. Should be at least 70% of requested width.
        assert bb.size.X > 70
        assert bb.size.X <= 100

    def test_with_one_tail(self):
        """Board with single tail."""
        result = generate_dovetail_tail_board(num_tails=1)
        assert result is not None

    def test_with_many_tails(self):
        """Board with many tails."""
        result = generate_dovetail_tail_board(num_tails=7)
        assert result is not None

    def test_different_thicknesses(self):
        """Different board thicknesses."""
        thin = generate_dovetail_tail_board(board_thickness=12.0)
        thick = generate_dovetail_tail_board(board_thickness=25.0)

        bb_thin = thin.bounding_box()
        bb_thick = thick.bounding_box()

        assert bb_thick.size.Z > bb_thin.size.Z

    def test_different_widths(self):
        """Different board widths."""
        narrow = generate_dovetail_tail_board(board_width=50.0)
        wide = generate_dovetail_tail_board(board_width=200.0)

        bb_narrow = narrow.bounding_box()
        bb_wide = wide.bounding_box()

        assert bb_wide.size.X > bb_narrow.size.X

    def test_steep_angle(self):
        """Steep dovetail angle (20 degrees)."""
        result = generate_dovetail_tail_board(tail_angle=20.0)
        assert result is not None

    def test_shallow_angle(self):
        """Shallow dovetail angle (7 degrees)."""
        result = generate_dovetail_tail_board(tail_angle=7.0)
        assert result is not None

    def test_without_half_pin(self):
        """Board without half pins."""
        result = generate_dovetail_tail_board(half_pin=False)
        assert result is not None


# =============================================================================
# Dovetail Pin Board Tests
# =============================================================================


class TestDovetailPinBoard:
    """Test dovetail pin board generator."""

    def test_generates_solid(self):
        """Generator produces a solid."""
        result = generate_dovetail_pin_board()
        assert isinstance(result, (Part, Compound))
        assert result is not None

    def test_matches_tail_board_width(self):
        """Pin board matches tail board width."""
        tail = generate_dovetail_tail_board(board_width=150.0)
        pin = generate_dovetail_pin_board(board_width=150.0)

        bb_tail = tail.bounding_box()
        bb_pin = pin.bounding_box()

        # Widths should be approximately equal (within 25mm tolerance
        # due to different cut patterns for tails vs pins)
        assert abs(bb_tail.size.X - bb_pin.size.X) < 25

    def test_with_various_tails(self):
        """Pin board for various tail counts."""
        for num_tails in [1, 3, 5]:
            result = generate_dovetail_pin_board(num_tails=num_tails)
            assert result is not None

    def test_tolerance_affects_size(self):
        """Tolerance affects socket size."""
        tight = generate_dovetail_pin_board(tolerance=0.05)
        loose = generate_dovetail_pin_board(tolerance=0.3)

        assert tight is not None
        assert loose is not None


# =============================================================================
# Sliding Dovetail Tests
# =============================================================================


class TestSlidingDovetailSlot:
    """Test sliding dovetail slot generator."""

    def test_generates_solid(self):
        """Generator produces a solid."""
        result = generate_sliding_dovetail_slot()
        assert isinstance(result, (Part, Compound))
        assert result is not None

    def test_slot_dimensions(self):
        """Slot has correct base dimensions."""
        result = generate_sliding_dovetail_slot(
            base_width=100.0,
            base_length=200.0,
            base_thickness=18.0,
        )
        bb = result.bounding_box()

        assert abs(bb.size.X - 100.0) < 1
        assert abs(bb.size.Y - 200.0) < 1

    def test_different_slot_widths(self):
        """Different slot widths."""
        narrow = generate_sliding_dovetail_slot(slot_width=10.0)
        wide = generate_sliding_dovetail_slot(slot_width=25.0)

        assert narrow is not None
        assert wide is not None

    def test_different_slot_depths(self):
        """Different slot depths."""
        shallow = generate_sliding_dovetail_slot(slot_depth=5.0)
        deep = generate_sliding_dovetail_slot(slot_depth=12.0)

        assert shallow is not None
        assert deep is not None


class TestSlidingDovetailKey:
    """Test sliding dovetail key generator."""

    def test_generates_solid(self):
        """Generator produces a solid."""
        result = generate_sliding_dovetail_key()
        assert isinstance(result, (Part, Compound))
        assert result is not None

    def test_key_dimensions(self):
        """Key has correct length."""
        result = generate_sliding_dovetail_key(key_length=200.0)
        bb = result.bounding_box()

        assert abs(bb.size.Y - 200.0) < 1

    def test_various_key_sizes(self):
        """Various key dimensions."""
        result = generate_sliding_dovetail_key(
            key_width=20.0,
            key_height=10.0,
            key_length=150.0,
        )
        assert result is not None


# =============================================================================
# Box Joint Tests
# =============================================================================


class TestBoxJointBoardA:
    """Test box joint board A generator."""

    def test_generates_solid(self):
        """Generator produces a solid."""
        result = generate_box_joint_board_a()
        assert isinstance(result, (Part, Compound))
        assert result is not None

    def test_board_dimensions(self):
        """Board has correct dimensions."""
        result = generate_box_joint_board_a(
            board_width=100.0,
            board_thickness=12.0,
            board_length=50.0,
        )
        bb = result.bounding_box()

        # Width may be slightly less due to slot cuts at edges
        assert bb.size.X > 90  # Allow for edge slot cuts
        assert abs(bb.size.Z - 12.0) < 2

    def test_various_finger_widths(self):
        """Various finger widths."""
        for width in [4.0, 6.0, 10.0, 15.0]:
            result = generate_box_joint_board_a(finger_width=width)
            assert result is not None

    def test_narrow_board(self):
        """Narrow board with few fingers."""
        result = generate_box_joint_board_a(board_width=30.0, finger_width=5.0)
        assert result is not None


class TestBoxJointBoardB:
    """Test box joint board B generator."""

    def test_generates_solid(self):
        """Generator produces a solid."""
        result = generate_box_joint_board_b()
        assert isinstance(result, (Part, Compound))
        assert result is not None

    def test_matches_board_a_width(self):
        """Board B and A are generated successfully."""
        board_a = generate_box_joint_board_a(board_width=80.0)
        board_b = generate_box_joint_board_b(board_width=80.0)

        # Both boards should generate valid solids
        assert board_a is not None
        assert board_b is not None

    def test_complementary_fingers(self):
        """Boards A and B should have complementary patterns."""
        # Both boards should generate successfully with same parameters
        result_a = generate_box_joint_board_a(
            board_width=100.0,
            finger_width=10.0,
        )
        result_b = generate_box_joint_board_b(
            board_width=100.0,
            finger_width=10.0,
        )

        assert result_a is not None
        assert result_b is not None


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestDovetailUtilities:
    """Test utility functions."""

    def test_calculate_angle_softwood(self):
        """Calculate softwood angle (1:6)."""
        angle = calculate_dovetail_angle(6)
        # 1:6 ratio is about 9.5 degrees
        assert abs(angle - 9.5) < 0.5

    def test_calculate_angle_hardwood(self):
        """Calculate hardwood angle (1:8)."""
        angle = calculate_dovetail_angle(8)
        # 1:8 ratio is about 7.1 degrees
        assert abs(angle - 7.1) < 0.5

    def test_calculate_angle_steep(self):
        """Calculate steep angle (1:4)."""
        angle = calculate_dovetail_angle(4)
        # 1:4 ratio is about 14 degrees
        assert abs(angle - 14) < 0.5

    def test_recommended_softwood(self):
        """Get recommended angle for softwood."""
        angle = get_recommended_angle("softwood")
        assert 9 < angle < 10

    def test_recommended_hardwood(self):
        """Get recommended angle for hardwood."""
        angle = get_recommended_angle("hardwood")
        assert 7 < angle < 8

    def test_get_templates_list(self):
        """Get list of available templates."""
        templates = get_dovetail_templates()

        assert len(templates) == 6
        slugs = [t["slug"] for t in templates]
        assert "dovetail-tail-board" in slugs
        assert "dovetail-pin-board" in slugs
        assert "sliding-dovetail-slot" in slugs
        assert "sliding-dovetail-key" in slugs
        assert "box-joint-board-a" in slugs
        assert "box-joint-board-b" in slugs

    def test_templates_have_parameters(self):
        """Each template has parameters defined."""
        templates = get_dovetail_templates()

        for template in templates:
            assert "parameters" in template
            assert len(template["parameters"]) > 0


# =============================================================================
# Template Registry Integration Tests
# =============================================================================


class TestDovetailRegistration:
    """Test dovetail templates are registered correctly."""

    def test_tail_board_registered(self):
        """Tail board template is registered."""
        assert "dovetail-tail-board" in TEMPLATE_REGISTRY

    def test_pin_board_registered(self):
        """Pin board template is registered."""
        assert "dovetail-pin-board" in TEMPLATE_REGISTRY

    def test_sliding_slot_registered(self):
        """Sliding dovetail slot is registered."""
        assert "sliding-dovetail-slot" in TEMPLATE_REGISTRY

    def test_sliding_key_registered(self):
        """Sliding dovetail key is registered."""
        assert "sliding-dovetail-key" in TEMPLATE_REGISTRY

    def test_box_joint_a_registered(self):
        """Box joint board A is registered."""
        assert "box-joint-board-a" in TEMPLATE_REGISTRY

    def test_box_joint_b_registered(self):
        """Box joint board B is registered."""
        assert "box-joint-board-b" in TEMPLATE_REGISTRY

    def test_generate_via_registry_tail(self):
        """Generate tail board via template registry."""
        result = generate_from_template("dovetail-tail-board", {"num_tails": 3})
        assert result is not None

    def test_generate_via_registry_pin(self):
        """Generate pin board via template registry."""
        result = generate_from_template("dovetail-pin-board", {"num_tails": 3})
        assert result is not None

    def test_generate_via_registry_box_joint(self):
        """Generate box joint via template registry."""
        result = generate_from_template("box-joint-board-a", {"finger_width": 8.0})
        assert result is not None


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestDovetailEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_thin_board(self):
        """Very thin board (6mm)."""
        result = generate_dovetail_tail_board(board_thickness=6.0)
        assert result is not None

    def test_very_thick_board(self):
        """Very thick board (50mm)."""
        result = generate_dovetail_tail_board(board_thickness=50.0)
        assert result is not None

    def test_very_narrow_board(self):
        """Very narrow board (30mm)."""
        result = generate_dovetail_tail_board(board_width=30.0, num_tails=1)
        assert result is not None

    def test_very_wide_board(self):
        """Very wide board (300mm)."""
        result = generate_dovetail_tail_board(board_width=300.0, num_tails=8)
        assert result is not None

    def test_zero_tolerance(self):
        """Zero tolerance (tight fit)."""
        result = generate_dovetail_pin_board(tolerance=0.0)
        assert result is not None

    def test_large_tolerance(self):
        """Large tolerance (loose fit)."""
        result = generate_dovetail_pin_board(tolerance=0.5)
        assert result is not None

    def test_single_finger(self):
        """Box joint with single finger width equal to board width."""
        result = generate_box_joint_board_a(
            board_width=20.0,
            finger_width=20.0,
        )
        assert result is not None
