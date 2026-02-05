"""
Tests for AI Iterative Reasoning Module.

Tests reasoning states, data structures, and classification.
"""

from app.ai.iterative_reasoning import (
    ClarificationQuestion,
    ExtractedDimension,
    ExtractedFeature,
    PartClassification,
    ReasoningState,
)

# =============================================================================
# ReasoningState Tests
# =============================================================================


class TestReasoningState:
    """Tests for ReasoningState enum."""

    def test_classifying_state(self):
        """Test classifying state."""
        assert ReasoningState.CLASSIFYING == "classifying"

    def test_extracting_state(self):
        """Test extracting state."""
        assert ReasoningState.EXTRACTING == "extracting"

    def test_validating_state(self):
        """Test validating state."""
        assert ReasoningState.VALIDATING == "validating"

    def test_needs_clarification_state(self):
        """Test needs clarification state."""
        assert ReasoningState.NEEDS_CLARIFICATION == "needs_clarification"

    def test_ready_to_plan_state(self):
        """Test ready to plan state."""
        assert ReasoningState.READY_TO_PLAN == "ready_to_plan"

    def test_planning_state(self):
        """Test planning state."""
        assert ReasoningState.PLANNING == "planning"

    def test_ready_to_generate_state(self):
        """Test ready to generate state."""
        assert ReasoningState.READY_TO_GENERATE == "ready_to_generate"

    def test_generating_state(self):
        """Test generating state."""
        assert ReasoningState.GENERATING == "generating"

    def test_validating_result_state(self):
        """Test validating result state."""
        assert ReasoningState.VALIDATING_RESULT == "validating_result"

    def test_complete_state(self):
        """Test complete state."""
        assert ReasoningState.COMPLETE == "complete"

    def test_failed_state(self):
        """Test failed state."""
        assert ReasoningState.FAILED == "failed"

    def test_all_states_are_strings(self):
        """Test all states are strings."""
        for state in ReasoningState:
            assert isinstance(state.value, str)


# =============================================================================
# PartClassification Tests
# =============================================================================


class TestPartClassification:
    """Tests for PartClassification dataclass."""

    def test_basic_creation(self):
        """Test creating a basic classification."""
        classification = PartClassification(
            category="bracket",
        )

        assert classification.category == "bracket"
        assert classification.subcategory is None
        assert classification.confidence == 0.0
        assert classification.reasoning == ""

    def test_full_classification(self):
        """Test classification with all fields."""
        classification = PartClassification(
            category="bracket",
            subcategory="L-bracket",
            confidence=0.95,
            reasoning="Two perpendicular flanges forming an L shape",
        )

        assert classification.category == "bracket"
        assert classification.subcategory == "L-bracket"
        assert classification.confidence == 0.95
        assert "L shape" in classification.reasoning

    def test_enclosure_classification(self):
        """Test enclosure classification."""
        classification = PartClassification(
            category="enclosure",
            subcategory="project box",
            confidence=0.88,
        )

        assert classification.category == "enclosure"
        assert classification.subcategory == "project box"


# =============================================================================
# ExtractedDimension Tests
# =============================================================================


class TestExtractedDimension:
    """Tests for ExtractedDimension dataclass."""

    def test_basic_creation(self):
        """Test creating a basic dimension."""
        dim = ExtractedDimension(
            name="length",
            value=100.0,
        )

        assert dim.name == "length"
        assert dim.value == 100.0
        assert dim.unit == "mm"
        assert dim.confidence == 1.0
        assert dim.source == "explicit"

    def test_with_unit(self):
        """Test dimension with different unit."""
        dim = ExtractedDimension(
            name="diameter",
            value=2.0,
            unit="inches",
        )

        assert dim.value == 2.0
        assert dim.unit == "inches"

    def test_inferred_dimension(self):
        """Test inferred dimension."""
        dim = ExtractedDimension(
            name="thickness",
            value=3.0,
            source="inferred",
            confidence=0.7,
        )

        assert dim.source == "inferred"
        assert dim.confidence == 0.7

    def test_default_dimension(self):
        """Test default dimension."""
        dim = ExtractedDimension(
            name="corner_radius",
            value=2.0,
            source="default",
            confidence=0.5,
        )

        assert dim.source == "default"


# =============================================================================
# ExtractedFeature Tests
# =============================================================================


class TestExtractedFeature:
    """Tests for ExtractedFeature dataclass."""

    def test_hole_feature(self):
        """Test hole feature extraction."""
        feature = ExtractedFeature(
            feature_type="hole",
            description="M5 mounting holes",
            parameters={"diameter": 5.2, "depth": 10},
            location="corners",
            count=4,
        )

        assert feature.feature_type == "hole"
        assert feature.count == 4
        assert feature.parameters["diameter"] == 5.2

    def test_fillet_feature(self):
        """Test fillet feature extraction."""
        feature = ExtractedFeature(
            feature_type="fillet",
            description="Edge rounding",
            parameters={"radius": 3.0},
            location="outer edges",
        )

        assert feature.feature_type == "fillet"
        assert feature.parameters["radius"] == 3.0

    def test_default_values(self):
        """Test feature default values."""
        feature = ExtractedFeature(
            feature_type="slot",
            description="Slot for adjustment",
        )

        assert feature.parameters == {}
        assert feature.location == ""
        assert feature.count == 1
        assert feature.confidence == 1.0


# =============================================================================
# ClarificationQuestion Tests
# =============================================================================


class TestClarificationQuestion:
    """Tests for ClarificationQuestion dataclass."""

    def test_basic_question(self):
        """Test creating a basic question."""
        question = ClarificationQuestion(
            question="What is the material thickness?",
            context="Need thickness to create proper geometry",
        )

        assert "thickness" in question.question
        assert question.context != ""

    def test_question_with_options(self):
        """Test question with options."""
        question = ClarificationQuestion(
            question="What corner style do you prefer?",
            context="Affects the appearance",
            options=["rounded", "chamfered", "sharp"],
            default="rounded",
        )

        assert len(question.options) == 3
        assert "rounded" in question.options
        assert question.default == "rounded"

    def test_question_priority(self):
        """Test question priority levels."""
        critical = ClarificationQuestion(
            question="What are the main dimensions?",
            context="Required for generation",
            priority=1,
        )

        important = ClarificationQuestion(
            question="What hole size?",
            context="For mounting",
            priority=2,
        )

        optional = ClarificationQuestion(
            question="Prefer any specific fillet radius?",
            context="Aesthetic choice",
            priority=3,
        )

        assert critical.priority == 1
        assert important.priority == 2
        assert optional.priority == 3

    def test_question_with_dimension_key(self):
        """Test question linked to dimension."""
        question = ClarificationQuestion(
            question="What is the flange length?",
            context="L-bracket dimension needed",
            dimension_key="flange_length",
        )

        assert question.dimension_key == "flange_length"


# =============================================================================
# Edge Cases
# =============================================================================


class TestIterativeReasoningEdgeCases:
    """Tests for edge cases."""

    def test_zero_confidence(self):
        """Test zero confidence classification."""
        classification = PartClassification(
            category="unknown",
            confidence=0.0,
        )

        assert classification.confidence == 0.0

    def test_full_confidence(self):
        """Test full confidence classification."""
        classification = PartClassification(
            category="box",
            confidence=1.0,
        )

        assert classification.confidence == 1.0

    def test_negative_dimension_value(self):
        """Test negative dimension value (offset)."""
        dim = ExtractedDimension(
            name="offset",
            value=-5.0,
        )

        assert dim.value == -5.0

    def test_zero_dimension_value(self):
        """Test zero dimension value."""
        dim = ExtractedDimension(
            name="gap",
            value=0.0,
        )

        assert dim.value == 0.0

    def test_empty_feature_parameters(self):
        """Test feature with no parameters."""
        feature = ExtractedFeature(
            feature_type="chamfer",
            description="Simple edge chamfer",
        )

        assert feature.parameters == {}

    def test_empty_question_options(self):
        """Test question with no options."""
        question = ClarificationQuestion(
            question="Any specific requirements?",
            context="Open-ended question",
        )

        assert question.options == []
        assert question.default is None
