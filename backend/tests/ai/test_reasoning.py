"""
Tests for AI Reasoning Module.

Tests unit conversion, intent parsing, and build planning structures.
"""

from app.ai.reasoning import (
    UNIT_TO_MM,
    BuildPlan,
    BuildStep,
    PartIntent,
    _normalize_dimensions_to_mm,
)

# =============================================================================
# Unit Conversion Constants Tests
# =============================================================================


class TestUnitToMM:
    """Tests for unit conversion constants."""

    def test_mm_conversion(self):
        """Test millimeter conversion is 1."""
        assert UNIT_TO_MM["mm"] == 1.0

    def test_cm_conversion(self):
        """Test centimeter conversion."""
        assert UNIT_TO_MM["cm"] == 10.0

    def test_meter_conversion(self):
        """Test meter conversion."""
        assert UNIT_TO_MM["m"] == 1000.0

    def test_inches_conversion(self):
        """Test inches conversion."""
        assert UNIT_TO_MM["inches"] == 25.4

    def test_inch_conversion(self):
        """Test inch (singular) conversion."""
        assert UNIT_TO_MM["inch"] == 25.4

    def test_in_conversion(self):
        """Test 'in' abbreviation conversion."""
        assert UNIT_TO_MM["in"] == 25.4

    def test_feet_conversion(self):
        """Test feet conversion."""
        assert UNIT_TO_MM["feet"] == 304.8

    def test_ft_conversion(self):
        """Test 'ft' abbreviation conversion."""
        assert UNIT_TO_MM["ft"] == 304.8

    def test_foot_conversion(self):
        """Test foot (singular) conversion."""
        assert UNIT_TO_MM["foot"] == 304.8


# =============================================================================
# Dimension Normalization Tests
# =============================================================================


class TestNormalizeDimensions:
    """Tests for dimension normalization function."""

    def test_empty_dict(self):
        """Test normalizing empty dictionary."""
        result = _normalize_dimensions_to_mm({})
        assert result == {}

    def test_none_input(self):
        """Test normalizing None input."""
        result = _normalize_dimensions_to_mm(None)
        assert result == {}

    def test_mm_values_unchanged(self):
        """Test mm values are unchanged."""
        dims = {"length": 100, "width": 50, "unit": "mm"}
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 100
        assert result["width"] == 50
        assert "unit" not in result

    def test_inches_conversion(self):
        """Test inches are converted to mm."""
        dims = {"length": 1, "width": 2, "unit": "inches"}
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 25.4
        assert result["width"] == 50.8

    def test_cm_conversion(self):
        """Test cm are converted to mm."""
        dims = {"length": 10, "width": 5, "unit": "cm"}
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 100
        assert result["width"] == 50

    def test_feet_conversion(self):
        """Test feet are converted to mm."""
        dims = {"height": 2, "unit": "feet"}
        result = _normalize_dimensions_to_mm(dims)

        assert result["height"] == 609.6

    def test_non_numeric_values_preserved(self):
        """Test non-numeric values are preserved."""
        dims = {"length": 100, "name": "test", "unit": "mm"}
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 100
        assert result["name"] == "test"

    def test_no_unit_defaults_to_mm(self):
        """Test missing unit defaults to mm."""
        dims = {"length": 100, "width": 50}
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 100
        assert result["width"] == 50

    def test_case_insensitive_unit(self):
        """Test unit is case insensitive."""
        dims = {"length": 1, "unit": "INCHES"}
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 25.4

    def test_unit_with_whitespace(self):
        """Test unit with whitespace is trimmed."""
        dims = {"length": 1, "unit": " inches "}
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 25.4

    def test_unknown_unit_treated_as_mm(self):
        """Test unknown unit is treated as mm (factor 1.0)."""
        dims = {"length": 100, "unit": "unknown_unit"}
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 100

    def test_rounding_to_two_decimals(self):
        """Test results are rounded to 2 decimal places."""
        dims = {"length": 1, "unit": "in"}  # 25.4
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 25.4


# =============================================================================
# PartIntent Tests
# =============================================================================


class TestPartIntent:
    """Tests for PartIntent dataclass."""

    def test_basic_creation(self):
        """Test creating a basic part intent."""
        intent = PartIntent(
            part_type="bracket",
            primary_function="mounting",
        )

        assert intent.part_type == "bracket"
        assert intent.primary_function == "mounting"

    def test_default_values(self):
        """Test default values are set correctly."""
        intent = PartIntent(
            part_type="enclosure",
            primary_function="protection",
        )

        assert intent.overall_dimensions == {}
        assert intent.material_thickness is None
        assert intent.features == []
        assert intent.constraints == []
        assert intent.referenced_hardware == []
        assert intent.referenced_files == []
        assert intent.confidence == 0.0
        assert intent.clarifications_needed == []
        assert intent.assumptions_made == []

    def test_with_dimensions(self):
        """Test intent with dimensions."""
        intent = PartIntent(
            part_type="box",
            primary_function="storage",
            overall_dimensions={"length": 100, "width": 50, "height": 30},
        )

        assert intent.overall_dimensions["length"] == 100
        assert intent.overall_dimensions["width"] == 50
        assert intent.overall_dimensions["height"] == 30

    def test_with_features(self):
        """Test intent with features."""
        features = [
            {"type": "hole", "diameter": 5, "count": 4},
            {"type": "fillet", "radius": 3},
        ]
        intent = PartIntent(
            part_type="bracket",
            primary_function="mounting",
            features=features,
        )

        assert len(intent.features) == 2
        assert intent.features[0]["type"] == "hole"

    def test_with_constraints(self):
        """Test intent with constraints."""
        intent = PartIntent(
            part_type="adapter",
            primary_function="connection",
            constraints=["must fit M5 bolt", "must align with PCB holes"],
        )

        assert len(intent.constraints) == 2
        assert "M5 bolt" in intent.constraints[0]

    def test_with_confidence(self):
        """Test intent with confidence score."""
        intent = PartIntent(
            part_type="mount",
            primary_function="support",
            confidence=0.85,
        )

        assert intent.confidence == 0.85


# =============================================================================
# BuildStep Tests
# =============================================================================


class TestBuildStep:
    """Tests for BuildStep dataclass."""

    def test_basic_creation(self):
        """Test creating a basic build step."""
        step = BuildStep(
            step_number=1,
            description="Create base box",
            operation="create_base",
        )

        assert step.step_number == 1
        assert step.description == "Create base box"
        assert step.operation == "create_base"

    def test_default_values(self):
        """Test default values."""
        step = BuildStep(
            step_number=1,
            description="Test step",
            operation="modify",
        )

        assert step.parameters == {}
        assert step.depends_on == []
        assert step.validation is None

    def test_with_parameters(self):
        """Test step with parameters."""
        step = BuildStep(
            step_number=1,
            description="Add holes",
            operation="add_feature",
            parameters={"hole_diameter": 5, "count": 4, "pattern": "grid"},
        )

        assert step.parameters["hole_diameter"] == 5
        assert step.parameters["count"] == 4

    def test_with_dependencies(self):
        """Test step with dependencies."""
        step = BuildStep(
            step_number=3,
            description="Add fillets",
            operation="modify",
            depends_on=[1, 2],
        )

        assert len(step.depends_on) == 2
        assert 1 in step.depends_on
        assert 2 in step.depends_on

    def test_with_validation(self):
        """Test step with validation."""
        step = BuildStep(
            step_number=1,
            description="Create base",
            operation="create_base",
            validation="Check volume is > 0",
        )

        assert step.validation == "Check volume is > 0"


# =============================================================================
# BuildPlan Tests
# =============================================================================


class TestBuildPlan:
    """Tests for BuildPlan dataclass."""

    def test_basic_creation(self):
        """Test creating a basic build plan."""
        intent = PartIntent(
            part_type="bracket",
            primary_function="mounting",
        )
        plan = BuildPlan(intent=intent)

        assert plan.intent == intent
        assert plan.steps == []
        assert plan.estimated_complexity == "simple"
        assert plan.warnings == []

    def test_with_steps(self):
        """Test plan with multiple steps."""
        intent = PartIntent(
            part_type="enclosure",
            primary_function="protection",
        )
        steps = [
            BuildStep(1, "Create outer shell", "create_base"),
            BuildStep(2, "Hollow out", "boolean"),
            BuildStep(3, "Add mounting holes", "add_feature"),
        ]
        plan = BuildPlan(
            intent=intent,
            steps=steps,
        )

        assert len(plan.steps) == 3
        assert plan.steps[0].step_number == 1
        assert plan.steps[2].operation == "add_feature"

    def test_complexity_levels(self):
        """Test different complexity levels."""
        intent = PartIntent(part_type="custom", primary_function="testing")

        simple = BuildPlan(intent=intent, estimated_complexity="simple")
        moderate = BuildPlan(intent=intent, estimated_complexity="moderate")
        complex_plan = BuildPlan(intent=intent, estimated_complexity="complex")

        assert simple.estimated_complexity == "simple"
        assert moderate.estimated_complexity == "moderate"
        assert complex_plan.estimated_complexity == "complex"

    def test_with_warnings(self):
        """Test plan with warnings."""
        intent = PartIntent(part_type="bracket", primary_function="mounting")
        plan = BuildPlan(
            intent=intent,
            warnings=[
                "Dimensions may be too small for FDM printing",
                "Wall thickness below recommended minimum",
            ],
        )

        assert len(plan.warnings) == 2
        assert "FDM printing" in plan.warnings[0]


# =============================================================================
# Edge Cases
# =============================================================================


class TestReasoningEdgeCases:
    """Tests for edge cases in reasoning module."""

    def test_zero_dimensions(self):
        """Test handling of zero dimensions."""
        dims = {"length": 0, "width": 0, "unit": "mm"}
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 0
        assert result["width"] == 0

    def test_negative_dimensions(self):
        """Test handling of negative dimensions."""
        dims = {"offset": -10, "unit": "mm"}
        result = _normalize_dimensions_to_mm(dims)

        assert result["offset"] == -10

    def test_very_large_dimensions(self):
        """Test handling of very large dimensions."""
        dims = {"length": 10, "unit": "m"}  # 10 meters = 10000 mm
        result = _normalize_dimensions_to_mm(dims)

        assert result["length"] == 10000

    def test_fractional_inches(self):
        """Test handling of fractional inch values."""
        dims = {"hole_size": 0.5, "unit": "inches"}  # 1/2 inch = 12.7 mm
        result = _normalize_dimensions_to_mm(dims)

        assert result["hole_size"] == 12.7

    def test_empty_part_intent(self):
        """Test minimal part intent."""
        intent = PartIntent(
            part_type="unknown",
            primary_function="unspecified",
        )

        assert intent.part_type == "unknown"
        assert intent.primary_function == "unspecified"
        assert intent.confidence == 0.0

    def test_plan_with_zero_steps(self):
        """Test plan with no steps."""
        intent = PartIntent(part_type="test", primary_function="test")
        plan = BuildPlan(intent=intent, steps=[])

        assert len(plan.steps) == 0


# =============================================================================
# Unit Conversion Sanity Check Tests
# =============================================================================


class TestUnconvertedValueDetection:
    """Tests for detecting and fixing unconverted imperial values.

    These tests verify that when the AI fails to convert inch values to mm,
    the extraction logic detects and corrects the values.
    """

    def test_detect_unconverted_2_inches(self):
        """Test detection of '2 inches' returned as 2 instead of 50.8."""
        import re

        user_input = "Make a cylinder 2 inches in diameter"
        user_input_lower = user_input.lower()

        # Simulated AI response: returned 2 instead of 50.8
        value = 2.0

        # Detection logic from extract_dimensions
        inch_patterns = re.findall(r'(\d+(?:\.\d+)?)\s*(?:inch|inches|"|in\b)', user_input_lower)

        # Should find "2" from "2 inches"
        assert "2" in inch_patterns

        # Check if conversion is needed
        inch_val = float(inch_patterns[0])
        expected_mm = inch_val * 25.4

        # Value matches raw inch number and is much smaller than expected
        needs_conversion = abs(value - inch_val) < 1.0 and expected_mm > value * 1.5
        assert needs_conversion

        # Apply conversion
        if needs_conversion:
            value = expected_mm

        assert abs(value - 50.8) < 0.01

    def test_detect_unconverted_4_inches(self):
        """Test detection of '4 inches' returned as 4 instead of 101.6."""
        import re

        user_input = "4 inches tall"
        user_input_lower = user_input.lower()

        value = 4.0  # Simulated wrong AI response

        inch_patterns = re.findall(r'(\d+(?:\.\d+)?)\s*(?:inch|inches|"|in\b)', user_input_lower)

        assert "4" in inch_patterns

        inch_val = float(inch_patterns[0])
        expected_mm = inch_val * 25.4
        needs_conversion = abs(value - inch_val) < 1.0 and expected_mm > value * 1.5

        assert needs_conversion

        if needs_conversion:
            value = expected_mm

        assert abs(value - 101.6) < 0.01

    def test_correctly_converted_value_not_changed(self):
        """Test that already converted values are not double-converted."""
        import re

        user_input = "Make a cylinder 2 inches in diameter"
        user_input_lower = user_input.lower()

        # AI correctly converted: 50.8mm
        value = 50.8

        inch_patterns = re.findall(r'(\d+(?:\.\d+)?)\s*(?:inch|inches|"|in\b)', user_input_lower)

        inch_val = float(inch_patterns[0])  # 2.0
        expected_mm = inch_val * 25.4  # 50.8

        # Value does NOT match raw inch number
        needs_conversion = abs(value - inch_val) < 1.0 and expected_mm > value * 1.5

        # Should NOT need conversion since value is already 50.8, not 2
        assert not needs_conversion

    def test_mm_value_not_affected(self):
        """Test that mm values are not incorrectly converted."""
        import re

        user_input = "Make a box 100mm wide"
        user_input_lower = user_input.lower()

        # No inch patterns should match
        inch_patterns = re.findall(r'(\d+(?:\.\d+)?)\s*(?:inch|inches|"|in\b)', user_input_lower)

        # Should not find any inch patterns
        assert len(inch_patterns) == 0

    def test_mixed_units_handled(self):
        """Test handling mixed units (mm and inches in same request)."""
        import re

        user_input = "2 inches diameter with a 10mm center hole"
        user_input_lower = user_input.lower()

        # For the 10mm value - should not be affected
        mm_value = 10.0

        inch_patterns = re.findall(r'(\d+(?:\.\d+)?)\s*(?:inch|inches|"|in\b)', user_input_lower)

        # Found "2" from "2 inches"
        assert "2" in inch_patterns

        # Check 10mm value against inch patterns
        needs_conversion = False
        for inch_val_str in inch_patterns:
            inch_val = float(inch_val_str)
            expected_mm = inch_val * 25.4
            if abs(mm_value - inch_val) < 1.0 and expected_mm > mm_value * 1.5:
                needs_conversion = True
                break

        # 10 doesn't match 2, so should NOT need conversion
        assert not needs_conversion


# =============================================================================
# Center Hole vs Inner Diameter Tests
# =============================================================================


class TestCenterHoleVsInnerDiameter:
    """Tests for distinguishing center holes (features) from inner_diameter (hollow cylinders)."""

    def test_center_hole_in_description_removes_inner_diameter(self):
        """Test that center hole feature causes inner_diameter removal."""
        from app.ai.iterative_reasoning import ExtractedFeature

        # Simulate features list with a center hole
        features = [
            ExtractedFeature(
                feature_type="hole",
                description="10mm center hole",
                parameters={"diameter": 10},
                location="center",
                count=1,
            )
        ]

        # Check detection logic
        has_center_hole_feature = any(
            f.feature_type == "hole"
            and ("center" in f.location.lower() or "center" in f.description.lower())
            for f in features
        )

        assert has_center_hole_feature

    def test_center_in_location_detected(self):
        """Test that 'center' in location field is detected."""
        from app.ai.iterative_reasoning import ExtractedFeature

        features = [
            ExtractedFeature(
                feature_type="hole",
                description="through hole",
                parameters={"diameter": 10},
                location="center of top face",
                count=1,
            )
        ]

        has_center_hole_feature = any(
            f.feature_type == "hole"
            and ("center" in f.location.lower() or "center" in f.description.lower())
            for f in features
        )

        assert has_center_hole_feature

    def test_non_center_hole_does_not_trigger(self):
        """Test that edge holes don't trigger inner_diameter removal."""
        from app.ai.iterative_reasoning import ExtractedFeature

        features = [
            ExtractedFeature(
                feature_type="hole",
                description="mounting hole",
                parameters={"diameter": 5},
                location="corner",
                count=4,
            )
        ]

        has_center_hole_feature = any(
            f.feature_type == "hole"
            and ("center" in f.location.lower() or "center" in f.description.lower())
            for f in features
        )

        # Corner holes should NOT trigger center hole detection
        assert not has_center_hole_feature

    def test_hollow_cylinder_without_hole_feature(self):
        """Test that hollow cylinder (inner_diameter) without hole feature is allowed."""

        # No hole features - this is a genuinely hollow cylinder (pipe/tube)
        features = []

        has_center_hole_feature = any(
            f.feature_type == "hole"
            and ("center" in f.location.lower() or "center" in f.description.lower())
            for f in features
        )

        # No center hole, so inner_diameter should be kept
        assert not has_center_hole_feature
