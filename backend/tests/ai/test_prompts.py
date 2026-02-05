"""
Tests for prompt templates.
"""

from __future__ import annotations

import pytest

from app.ai.prompts import (
    DIMENSION_EXTRACTION_PROMPT,
    MODIFICATION_PROMPT,
    PROMPTS,
    TEMPLATE_SELECTION_PROMPT,
    VALIDATION_PROMPT,
    PromptCategory,
    PromptTemplate,
    get_prompt,
)

# =============================================================================
# PromptTemplate Tests
# =============================================================================


class TestPromptTemplate:
    """Tests for PromptTemplate class."""

    def test_format_messages_basic(self):
        """Test basic message formatting."""
        template = PromptTemplate(
            name="test",
            category=PromptCategory.DIMENSION_EXTRACTION,
            system_prompt="You are a test assistant.",
            user_template="Process this: {input}",
            output_schema={},
        )

        messages = template.format_messages(input="test data")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a test assistant."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Process this: test data"

    def test_format_messages_with_examples(self):
        """Test message formatting includes few-shot examples."""
        template = PromptTemplate(
            name="test",
            category=PromptCategory.DIMENSION_EXTRACTION,
            system_prompt="System prompt",
            user_template="Input: {text}",
            output_schema={},
            examples=[
                {"input": "Example input 1", "output": "Example output 1"},
                {"input": "Example input 2", "output": "Example output 2"},
            ],
        )

        messages = template.format_messages(text="actual input")

        # system + 2 examples (2 messages each) + user = 6 messages
        assert len(messages) == 6

        # Check system message
        assert messages[0]["role"] == "system"

        # Check first example
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Example input 1"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Example output 1"

        # Check second example
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "Example input 2"

        # Check actual user input is last
        assert messages[5]["role"] == "user"
        assert "actual input" in messages[5]["content"]


# =============================================================================
# Dimension Extraction Prompt Tests
# =============================================================================


class TestDimensionExtractionPrompt:
    """Tests for dimension extraction prompt."""

    def test_prompt_has_required_fields(self):
        """Test prompt has all required fields."""
        assert DIMENSION_EXTRACTION_PROMPT.name == "dimension_extraction"
        assert DIMENSION_EXTRACTION_PROMPT.category == PromptCategory.DIMENSION_EXTRACTION
        assert DIMENSION_EXTRACTION_PROMPT.system_prompt
        assert DIMENSION_EXTRACTION_PROMPT.user_template
        assert DIMENSION_EXTRACTION_PROMPT.output_schema
        assert DIMENSION_EXTRACTION_PROMPT.examples

    def test_prompt_includes_examples(self):
        """Test prompt has few-shot examples."""
        assert len(DIMENSION_EXTRACTION_PROMPT.examples) >= 2

        for example in DIMENSION_EXTRACTION_PROMPT.examples:
            assert "input" in example
            assert "output" in example

    def test_format_with_user_input(self):
        """Test formatting with actual user input."""
        messages = DIMENSION_EXTRACTION_PROMPT.format_messages(
            user_input="Create a box 100mm x 50mm x 30mm"
        )

        # Should have system + examples + user
        assert len(messages) >= 4

        # Last message should contain the user input
        assert "100mm" in messages[-1]["content"]
        assert "50mm" in messages[-1]["content"]

    def test_system_prompt_mentions_cad(self):
        """Test system prompt establishes CAD context."""
        system = DIMENSION_EXTRACTION_PROMPT.system_prompt.lower()
        assert "cad" in system

    def test_system_prompt_mentions_units(self):
        """Test system prompt covers unit handling."""
        system = DIMENSION_EXTRACTION_PROMPT.system_prompt.lower()
        assert "mm" in system or "millimeter" in system

    def test_output_schema_has_required_fields(self):
        """Test output schema defines required fields."""
        schema = DIMENSION_EXTRACTION_PROMPT.output_schema

        assert "properties" in schema
        assert "shape" in schema["properties"]
        assert "dimensions" in schema["properties"]
        assert "confidence" in schema["properties"]


# =============================================================================
# Other Prompt Tests
# =============================================================================


class TestTemplateSelectionPrompt:
    """Tests for template selection prompt."""

    def test_prompt_exists(self):
        """Test template selection prompt is defined."""
        assert TEMPLATE_SELECTION_PROMPT.name == "template_selection"
        assert TEMPLATE_SELECTION_PROMPT.category == PromptCategory.TEMPLATE_SELECTION

    def test_format_with_templates(self):
        """Test formatting with template list."""
        templates_json = '[{"id": "box", "name": "Simple Box"}]'

        messages = TEMPLATE_SELECTION_PROMPT.format_messages(
            user_input="I need an enclosure",
            templates=templates_json,
        )

        assert any("enclosure" in m["content"] for m in messages)


class TestModificationPrompt:
    """Tests for modification prompt."""

    def test_prompt_exists(self):
        """Test modification prompt is defined."""
        assert MODIFICATION_PROMPT.name == "modification"
        assert MODIFICATION_PROMPT.category == PromptCategory.MODIFICATION

    def test_format_with_current_part(self):
        """Test formatting with current part info."""
        messages = MODIFICATION_PROMPT.format_messages(
            current_part='{"shape": "box", "dimensions": {"length": 100}}',
            user_input="Make it taller",
        )

        assert any("taller" in m["content"] for m in messages)


class TestValidationPrompt:
    """Tests for validation prompt."""

    def test_prompt_exists(self):
        """Test validation prompt is defined."""
        assert VALIDATION_PROMPT.name == "validation"
        assert VALIDATION_PROMPT.category == PromptCategory.VALIDATION

    def test_format_with_parameters(self):
        """Test formatting with parameters."""
        messages = VALIDATION_PROMPT.format_messages(parameters='{"wall_thickness": 0.1}')

        assert any("wall_thickness" in m["content"] for m in messages)


# =============================================================================
# Registry Tests
# =============================================================================


class TestPromptRegistry:
    """Tests for prompt registry."""

    def test_all_prompts_registered(self):
        """Test all prompts are in registry."""
        assert "dimension_extraction" in PROMPTS
        assert "template_selection" in PROMPTS
        assert "modification" in PROMPTS
        assert "validation" in PROMPTS

    def test_get_prompt_returns_correct_template(self):
        """Test get_prompt returns the right template."""
        prompt = get_prompt("dimension_extraction")
        assert prompt is DIMENSION_EXTRACTION_PROMPT

    def test_get_prompt_unknown_raises_error(self):
        """Test get_prompt raises error for unknown template."""
        with pytest.raises(KeyError) as exc_info:
            get_prompt("nonexistent_prompt")

        assert "nonexistent_prompt" in str(exc_info.value)
