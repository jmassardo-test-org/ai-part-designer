"""Tests for CAD v2 AI prompts."""

from app.cad_v2.ai.prompts import (
    CAD_V2_SYSTEM_PROMPT,
    DIMENSION_EXTRACTION_PROMPT,
    ENCLOSURE_GENERATION,
    FEATURE_EXTRACTION_PROMPT,
    INTENT_CLASSIFICATION,
    INTENT_CLASSIFICATION_PROMPT,
    PromptTemplate,
)


class TestSystemPrompt:
    """Tests for the main system prompt."""

    def test_prompt_not_empty(self) -> None:
        """System prompt should have content."""
        assert len(CAD_V2_SYSTEM_PROMPT) > 100

    def test_prompt_mentions_json(self) -> None:
        """System prompt should mention JSON output."""
        assert "JSON" in CAD_V2_SYSTEM_PROMPT

    def test_prompt_mentions_enclosure(self) -> None:
        """System prompt should mention enclosure."""
        assert "enclosure" in CAD_V2_SYSTEM_PROMPT.lower()

    def test_prompt_has_schema_structure(self) -> None:
        """System prompt should document schema structure."""
        assert "exterior" in CAD_V2_SYSTEM_PROMPT
        assert "walls" in CAD_V2_SYSTEM_PROMPT

    def test_prompt_lists_components(self) -> None:
        """System prompt should list available components."""
        assert "raspberry-pi-5" in CAD_V2_SYSTEM_PROMPT
        assert "arduino-uno" in CAD_V2_SYSTEM_PROMPT

    def test_prompt_explains_wall_sides(self) -> None:
        """System prompt should explain wall sides."""
        assert "front" in CAD_V2_SYSTEM_PROMPT.lower()
        assert "back" in CAD_V2_SYSTEM_PROMPT.lower()

    def test_prompt_has_example(self) -> None:
        """System prompt should include example."""
        assert "Example" in CAD_V2_SYSTEM_PROMPT or "example" in CAD_V2_SYSTEM_PROMPT


class TestIntentClassificationPrompt:
    """Tests for intent classification prompt."""

    def test_prompt_not_empty(self) -> None:
        """Intent prompt should have content."""
        assert len(INTENT_CLASSIFICATION_PROMPT) > 50

    def test_prompt_mentions_intent_types(self) -> None:
        """Prompt should list intent types."""
        assert "create_enclosure" in INTENT_CLASSIFICATION_PROMPT
        assert "modify_design" in INTENT_CLASSIFICATION_PROMPT

    def test_prompt_requests_json(self) -> None:
        """Prompt should request JSON output."""
        assert "JSON" in INTENT_CLASSIFICATION_PROMPT


class TestDimensionExtractionPrompt:
    """Tests for dimension extraction prompt."""

    def test_prompt_not_empty(self) -> None:
        """Dimension prompt should have content."""
        assert len(DIMENSION_EXTRACTION_PROMPT) > 50

    def test_prompt_mentions_dimensions(self) -> None:
        """Prompt should mention width, depth, height."""
        assert "width" in DIMENSION_EXTRACTION_PROMPT.lower()
        assert "depth" in DIMENSION_EXTRACTION_PROMPT.lower()
        assert "height" in DIMENSION_EXTRACTION_PROMPT.lower()


class TestFeatureExtractionPrompt:
    """Tests for feature extraction prompt."""

    def test_prompt_not_empty(self) -> None:
        """Feature prompt should have content."""
        assert len(FEATURE_EXTRACTION_PROMPT) > 50

    def test_prompt_lists_feature_types(self) -> None:
        """Prompt should list feature types."""
        assert "port" in FEATURE_EXTRACTION_PROMPT.lower()
        assert "button" in FEATURE_EXTRACTION_PROMPT.lower()


class TestPromptTemplate:
    """Tests for PromptTemplate dataclass."""

    def test_template_initialization(self) -> None:
        """Template should initialize correctly."""
        template = PromptTemplate(
            name="test",
            system_prompt="You are a helper.",
            user_template="Process: {user_input}",
        )
        assert template.name == "test"
        assert template.temperature == 0.2  # Default

    def test_template_custom_temperature(self) -> None:
        """Template should accept custom temperature."""
        template = PromptTemplate(
            name="test",
            system_prompt="System",
            user_template="{user_input}",
            temperature=0.5,
        )
        assert template.temperature == 0.5

    def test_format_messages(self) -> None:
        """format_messages should create proper structure."""
        template = PromptTemplate(
            name="test",
            system_prompt="You are a CAD expert.",
            user_template="Create: {user_input}",
        )
        messages = template.format_messages("a box")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a CAD expert."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Create: a box"


class TestPredefinedTemplates:
    """Tests for pre-built templates."""

    def test_enclosure_generation_template(self) -> None:
        """ENCLOSURE_GENERATION should be properly configured."""
        assert ENCLOSURE_GENERATION.name == "enclosure_generation"
        assert ENCLOSURE_GENERATION.system_prompt == CAD_V2_SYSTEM_PROMPT
        assert ENCLOSURE_GENERATION.temperature == 0.2

    def test_intent_classification_template(self) -> None:
        """INTENT_CLASSIFICATION should be properly configured."""
        assert INTENT_CLASSIFICATION.name == "intent_classification"
        assert INTENT_CLASSIFICATION.temperature == 0.1  # Lower for classification

    def test_enclosure_generation_formats(self) -> None:
        """ENCLOSURE_GENERATION should format correctly."""
        messages = ENCLOSURE_GENERATION.format_messages("Create a Pi 5 case")
        assert len(messages) == 2
        assert "Pi 5 case" in messages[1]["content"]

    def test_intent_classification_formats(self) -> None:
        """INTENT_CLASSIFICATION should format correctly."""
        messages = INTENT_CLASSIFICATION.format_messages("Make a box")
        assert len(messages) == 2
        assert "Classify" in messages[1]["content"]
        assert "Make a box" in messages[1]["content"]
