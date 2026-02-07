"""
Tests for AI-powered CadQuery code generation.

Tests the code sanitization, execution, and modification generation functions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from build123d import Box, Compound, Part

from app.ai.codegen import (
    MODIFICATION_CONTEXT_PROMPT,
    execute_cadquery_code,
    generate_modification,
    sanitize_code,
)
from app.ai.exceptions import AIValidationError

# =============================================================================
# sanitize_code Tests
# =============================================================================


class TestSanitizeCode:
    """Tests for code sanitization."""

    def test_removes_markdown_code_blocks(self):
        """Test that markdown code blocks are removed."""
        code = "```python\nresult = cq.Workplane('XY').box(10, 10, 10)\n```"
        sanitized = sanitize_code(code)
        assert "```" not in sanitized
        assert "result = cq.Workplane" in sanitized

    def test_removes_cadquery_imports(self):
        """Test that cadquery imports are commented out."""
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
        sanitized = sanitize_code(code)
        assert "# import cadquery" in sanitized or "import cadquery" not in sanitized.split("\n")[0]

    def test_fixes_push_points_snake_case(self):
        """Test that push_points is converted to pushPoints."""
        code = "result = cq.Workplane('XY').push_points([(0, 0)]).hole(5)"
        sanitized = sanitize_code(code)
        assert ".pushPoints(" in sanitized
        assert ".push_points(" not in sanitized

    def test_removes_invalid_fillet_zero(self):
        """Test that .fillet(0) is removed."""
        code = "result = cq.Workplane('XY').box(10, 10, 10).fillet(0)"
        sanitized = sanitize_code(code)
        assert ".fillet(0)" not in sanitized

    def test_raises_on_dangerous_imports(self):
        """Test that dangerous imports raise an error."""
        dangerous_codes = [
            "import os\nresult = cq.Workplane('XY').box(10, 10, 10)",
            "import subprocess\nresult = cq.Workplane('XY').box(10, 10, 10)",
            "import sys\nresult = cq.Workplane('XY').box(10, 10, 10)",
        ]
        for code in dangerous_codes:
            with pytest.raises(AIValidationError):
                sanitize_code(code)

    def test_raises_on_missing_result(self):
        """Test that code without result variable raises an error."""
        code = "shape = cq.Workplane('XY').box(10, 10, 10)"
        with pytest.raises(AIValidationError):
            sanitize_code(code)

    def test_valid_code_passes_through(self):
        """Test that valid code passes through unchanged."""
        code = "result = cq.Workplane('XY').box(10, 10, 10)"
        sanitized = sanitize_code(code)
        assert "result = cq.Workplane" in sanitized


# =============================================================================
# execute_cadquery_code Tests
# =============================================================================


class TestExecuteCadQueryCode:
    """Tests for Build123d code execution (legacy function name)."""

    def test_executes_simple_box(self):
        """Test executing code that creates a simple box."""
        code = """
with BuildPart() as p:
    Box(10, 10, 10)
result = p.part
"""
        shape = execute_cadquery_code(code)

        assert isinstance(shape, (Part, Compound))
        assert hasattr(shape, "volume")
        volume = shape.volume
        assert abs(volume - 1000) < 1

    def test_executes_cylinder(self):
        """Test executing code that creates a cylinder."""
        # Cylinder(radius, height) - 25mm radius, 100mm tall
        code = """
with BuildPart() as p:
    Cylinder(25, 100)
result = p.part
"""
        shape = execute_cadquery_code(code)

        assert isinstance(shape, (Part, Compound))
        assert hasattr(shape, "volume")
        volume = shape.volume
        # Expected volume: π * r² * h = π * 25² * 100 ≈ 196350
        import math

        expected = math.pi * 25 * 25 * 100
        assert abs(volume - expected) < 100

    def test_executes_cylinder_with_hole(self):
        """Test executing cylinder with center hole."""
        code = """
with BuildPart() as p:
    Cylinder(25, 100)
    Hole(5, 100)
result = p.part
"""
        shape = execute_cadquery_code(code)

        assert isinstance(shape, (Part, Compound))
        assert hasattr(shape, "volume")
        volume = shape.volume
        # Volume should be cylinder volume minus hole volume
        import math

        cylinder_vol = math.pi * 25 * 25 * 100
        hole_vol = math.pi * 5 * 5 * 100  # 10mm diameter = 5mm radius
        expected = cylinder_vol - hole_vol
        assert abs(volume - expected) < 100

    def test_executes_with_base_shape(self):
        """Test executing code that modifies a base shape."""
        base = Box(20, 20, 20)
        code = """
with BuildPart() as p:
    add(base_shape)
    Hole(2.5, 20)
result = p.part
"""
        shape = execute_cadquery_code(code, base)

        assert isinstance(shape, (Part, Compound))
        # Volume should be less than original box minus hole
        assert hasattr(shape, "volume")
        volume = shape.volume
        assert volume < 8000

    def test_raises_on_syntax_error(self):
        """Test that syntax errors raise AIValidationError."""
        code = """
with BuildPart() as p:
    Box(10, 10, 10
result = p.part
"""  # Missing closing paren
        with pytest.raises(AIValidationError):
            execute_cadquery_code(code)

    def test_raises_on_execution_error(self):
        """Test that execution errors raise AIValidationError."""
        code = """
with BuildPart() as p:
    UndefinedShape(10, 10, 10)
result = p.part
"""
        with pytest.raises(AIValidationError):
            execute_cadquery_code(code)

    def test_raises_on_non_workplane_result(self):
        """Test that non-Part results raise AIValidationError."""
        code = "result = 'not a part'"
        with pytest.raises(AIValidationError):
            execute_cadquery_code(code)


# =============================================================================
# MODIFICATION_CONTEXT_PROMPT Tests
# =============================================================================


class TestModificationContextPrompt:
    """Tests for the modification context prompt template."""

    def test_prompt_has_required_placeholders(self):
        """Test that the prompt has all required placeholders."""
        assert "{original_code}" in MODIFICATION_CONTEXT_PROMPT
        assert "{original_description}" in MODIFICATION_CONTEXT_PROMPT
        assert "{existing_dimensions}" in MODIFICATION_CONTEXT_PROMPT
        assert "{modification_request}" in MODIFICATION_CONTEXT_PROMPT

    def test_prompt_formats_correctly(self):
        """Test that the prompt formats without errors."""
        formatted = MODIFICATION_CONTEXT_PROMPT.format(
            original_code="result = cq.Workplane('XY').box(100, 50, 30)",
            original_description="A box 100mm x 50mm x 30mm",
            existing_dimensions="length: 100mm, width: 50mm, height: 30mm",
            modification_request="add a 10mm hole in the center",
        )
        assert "A box 100mm x 50mm x 30mm" in formatted
        assert "add a 10mm hole in the center" in formatted


# =============================================================================
# generate_modification Tests
# =============================================================================


class TestGenerateModification:
    """Tests for modification generation."""

    @pytest.mark.asyncio
    async def test_generate_modification_calls_ai_client(self):
        """Test that generate_modification calls the AI client."""
        with patch("app.ai.codegen.get_ai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete.return_value = """
with BuildPart() as p:
    Box(100, 50, 30)
    Hole(5, 30)
result = p.part
"""
            mock_get_client.return_value = mock_client

            result = await generate_modification(
                original_description="A box 100mm x 50mm x 30mm",
                modification_request="add a 10mm hole in the center",
                existing_dimensions={"length": 100, "width": 50, "height": 30},
            )

            assert mock_client.complete.called
            assert result.code is not None

    @pytest.mark.asyncio
    async def test_generate_modification_success(self):
        """Test successful modification generation."""
        with patch("app.ai.codegen.get_ai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete.return_value = """
with BuildPart() as p:
    Box(100, 50, 30)
    Hole(5, 30)
result = p.part
"""
            mock_get_client.return_value = mock_client

            result = await generate_modification(
                original_description="A box 100mm x 50mm x 30mm",
                modification_request="add a 10mm hole in the center",
            )

            assert result.is_successful
            assert result.shape is not None
            assert "Applied modification" in result.adjustments[0]

    @pytest.mark.asyncio
    async def test_generate_modification_with_dimensions(self):
        """Test modification generation with existing dimensions."""
        with patch("app.ai.codegen.get_ai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete.return_value = """
with BuildPart() as p:
    Box(100, 50, 30)
    fillet(p.edges(), radius=3)
    with Locations((0, 0, 30)):
        Box(25, 25, 25)
result = p.part
"""
            mock_get_client.return_value = mock_client

            await generate_modification(
                original_description="A box 100mm x 50mm x 30mm with 3mm fillets",
                modification_request="add a 25mm cube on top",
                existing_dimensions={"length": 100, "width": 50, "height": 30},
            )

            # Check that the prompt was called with existing dimensions
            call_args = mock_client.complete.call_args
            prompt_content = call_args[0][0][0]["content"]
            assert "length: 100mm" in prompt_content

    @pytest.mark.asyncio
    async def test_generate_modification_handles_error(self):
        """Test that modification errors are handled gracefully."""
        with patch("app.ai.codegen.get_ai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete.return_value = "result = invalid_syntax("  # Invalid code
            mock_get_client.return_value = mock_client

            result = await generate_modification(
                original_description="A box",
                modification_request="add a hole",
            )

            assert not result.is_successful
            assert result.error is not None
