"""
Tests for end-to-end CAD generation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from build123d import Box, Compound, Cylinder, Part, Sphere

from app.ai.generator import (
    CADGenerator,
    GenerationResult,
    generate_from_description,
)
from app.ai.parser import CADParameters, Feature, FeatureType, ShapeType

# =============================================================================
# CADGenerator Tests
# =============================================================================


class TestCADGenerator:
    """Tests for CADGenerator class."""

    def test_generate_box(self):
        """Test generating a box from parameters."""
        params = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 100, "width": 50, "height": 30},
            confidence=0.9,
        )

        generator = CADGenerator()
        shape = generator.generate(params)

        assert isinstance(shape, (Part, Compound))

        # Verify volume
        volume = shape.volume
        expected = 100 * 50 * 30
        assert abs(volume - expected) < 1

    def test_generate_cylinder(self):
        """Test generating a cylinder from parameters."""
        params = CADParameters(
            shape=ShapeType.CYLINDER,
            dimensions={"radius": 25, "height": 100},
            confidence=0.9,
        )

        generator = CADGenerator()
        shape = generator.generate(params)

        assert isinstance(shape, (Part, Compound))

        # Verify approximate volume (π * r² * h)
        volume = shape.volume
        expected = 3.14159 * 25 * 25 * 100
        assert abs(volume - expected) < 100

    def test_generate_sphere(self):
        """Test generating a sphere from parameters."""
        params = CADParameters(
            shape=ShapeType.SPHERE,
            dimensions={"radius": 50},
            confidence=0.9,
        )

        generator = CADGenerator()
        shape = generator.generate(params)

        assert isinstance(shape, (Part, Compound))

    def test_generate_with_fillet_feature(self):
        """Test generating shape with fillet feature."""
        params = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 50, "width": 50, "height": 50},
            features=[Feature(type=FeatureType.FILLET, parameters={"radius": 3})],
            confidence=0.9,
        )

        generator = CADGenerator()
        shape = generator.generate(params)

        # Fillet reduces volume slightly
        volume = shape.volume
        box_volume = 50 * 50 * 50
        assert volume < box_volume

    def test_generate_with_hole_feature(self):
        """Test generating shape with hole feature."""
        params = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 50, "width": 50, "height": 20},
            features=[Feature(type=FeatureType.HOLE, parameters={"diameter": 10, "depth": 15})],
            confidence=0.9,
        )

        generator = CADGenerator()
        shape = generator.generate(params)

        # Hole reduces volume
        volume = shape.volume
        box_volume = 50 * 50 * 20
        assert volume < box_volume


# =============================================================================
# GenerationResult Tests
# =============================================================================


class TestGenerationResult:
    """Tests for GenerationResult class."""

    def test_is_successful_true(self):
        """Test is_successful when generation succeeded."""
        result = GenerationResult(
            description="test",
            shape=MagicMock(),
            step_data=b"step data",
            shape_type="box",
            confidence=0.9,
        )

        assert result.is_successful

    def test_is_successful_false_no_export(self):
        """Test is_successful when no export data."""
        result = GenerationResult(
            description="test",
            shape=MagicMock(),
            step_data=None,
            stl_data=None,
            shape_type="box",
            confidence=0.9,
        )

        assert not result.is_successful

    def test_get_stats(self):
        """Test get_stats returns expected data."""
        result = GenerationResult(
            description="test",
            shape=MagicMock(),
            step_data=b"data",
            shape_type="box",
            confidence=0.85,
            reasoning_time_ms=50,
            generation_time_ms=50,
            execution_time_ms=50,
            export_time_ms=200,
            total_time_ms=350,
        )

        stats = result.get_stats()

        assert stats["shape"] == "box"
        assert stats["confidence"] == 0.85
        assert stats["reasoning_time_ms"] == 50
        assert stats["has_step"] is True


# =============================================================================
# End-to-End Generation Tests
# =============================================================================


@pytest.mark.cad
class TestGenerateFromDescription:
    """Tests for generate_from_description function."""

    @pytest.mark.asyncio
    async def test_generate_box_e2e(self, tmp_path):
        """Test end-to-end box generation."""
        from app.ai.codegen import CodeGenerationResult
        from app.ai.reasoning import BuildPlan, BuildStep, PartIntent

        mock_intent = PartIntent(
            part_type="box",
            primary_function="storage",
            overall_dimensions={"length": 100, "width": 50, "height": 30},
            confidence=0.9,
            assumptions_made=["Assumed centered"],
            clarifications_needed=[],
        )

        mock_plan = BuildPlan(
            intent=mock_intent,
            steps=[
                BuildStep(
                    step_number=1,
                    operation="create_base",
                    description="Create base box",
                )
            ],
        )

        mock_shape = Box(100, 50, 30)

        mock_code_result = CodeGenerationResult(
            code="result = Box(100, 50, 30)",
            shape=mock_shape,
            generation_time_ms=100,
            execution_time_ms=50,
            adjustments=[],
            error=None,
        )

        with patch("app.ai.generator.reason_and_plan", new_callable=AsyncMock) as mock_reason:
            mock_reason.return_value = (mock_intent, mock_plan)

            with patch(
                "app.ai.generator.generate_cadquery_code", new_callable=AsyncMock
            ) as mock_codegen:
                mock_codegen.return_value = mock_code_result

                with patch(
                    "app.ai.generator.validate_result", new_callable=AsyncMock
                ) as mock_validate:
                    mock_validate.return_value = {"is_valid": True, "confidence": 0.9}

                    result = await generate_from_description(
                        "Create a box 100x50x30",
                        output_dir=tmp_path,
                    )

                    assert result.is_successful
                    assert result.shape_type == "box"
                    assert result.step_path.exists()
                    assert result.stl_path.exists()
                    assert result.total_time_ms > 0

    @pytest.mark.asyncio
    async def test_generate_adds_warnings_for_assumptions(self, tmp_path):
        """Test warnings are added for assumptions."""
        from app.ai.codegen import CodeGenerationResult
        from app.ai.reasoning import BuildPlan, PartIntent

        mock_intent = PartIntent(
            part_type="box",
            primary_function="storage",
            overall_dimensions={"length": 100, "width": 50, "height": 30},
            confidence=0.9,
            assumptions_made=["Assumed centered", "No units given"],
            clarifications_needed=[],
        )

        mock_plan = BuildPlan(intent=mock_intent, steps=[])
        mock_shape = Box(100, 50, 30)

        mock_code_result = CodeGenerationResult(
            code="result = Box(100, 50, 30)",
            shape=mock_shape,
            generation_time_ms=50,
            execution_time_ms=25,
            adjustments=[],
            error=None,
        )

        with patch("app.ai.generator.reason_and_plan", new_callable=AsyncMock) as mock_reason:
            mock_reason.return_value = (mock_intent, mock_plan)

            with patch(
                "app.ai.generator.generate_cadquery_code", new_callable=AsyncMock
            ) as mock_codegen:
                mock_codegen.return_value = mock_code_result

                with patch(
                    "app.ai.generator.validate_result", new_callable=AsyncMock
                ) as mock_validate:
                    mock_validate.return_value = {"is_valid": True}

                    result = await generate_from_description(
                        "Create a box",
                        output_dir=tmp_path,
                    )

                    assert len(result.warnings) >= 2
                    assert any("Assumed" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_generate_step_only(self, tmp_path):
        """Test generating only STEP file."""
        from app.ai.codegen import CodeGenerationResult
        from app.ai.reasoning import BuildPlan, PartIntent

        mock_intent = PartIntent(
            part_type="sphere",
            primary_function="decorative",
            overall_dimensions={"radius": 50},
            confidence=0.9,
            assumptions_made=[],
            clarifications_needed=[],
        )

        mock_plan = BuildPlan(intent=mock_intent, steps=[])
        mock_shape = Sphere(50)

        mock_code_result = CodeGenerationResult(
            code="result = Sphere(50)",
            shape=mock_shape,
            generation_time_ms=50,
            execution_time_ms=25,
            adjustments=[],
            error=None,
        )

        with patch("app.ai.generator.reason_and_plan", new_callable=AsyncMock) as mock_reason:
            mock_reason.return_value = (mock_intent, mock_plan)

            with patch(
                "app.ai.generator.generate_cadquery_code", new_callable=AsyncMock
            ) as mock_codegen:
                mock_codegen.return_value = mock_code_result

                with patch(
                    "app.ai.generator.validate_result", new_callable=AsyncMock
                ) as mock_validate:
                    mock_validate.return_value = {"is_valid": True}

                    result = await generate_from_description(
                        "Create a sphere",
                        output_dir=tmp_path,
                        export_step=True,
                        export_stl=False,
                    )

                    assert result.step_data is not None
                    assert result.stl_data is None

    @pytest.mark.asyncio
    async def test_generate_with_custom_job_id(self, tmp_path):
        """Test custom job ID is used."""
        from app.ai.codegen import CodeGenerationResult
        from app.ai.reasoning import BuildPlan, PartIntent

        mock_intent = PartIntent(
            part_type="box",
            primary_function="storage",
            overall_dimensions={"length": 100, "width": 50, "height": 30},
            confidence=0.9,
            assumptions_made=[],
            clarifications_needed=[],
        )

        mock_plan = BuildPlan(intent=mock_intent, steps=[])
        mock_shape = Box(100, 50, 30)

        mock_code_result = CodeGenerationResult(
            code="result = Box(100, 50, 30)",
            shape=mock_shape,
            generation_time_ms=50,
            execution_time_ms=25,
            adjustments=[],
            error=None,
        )

        with patch("app.ai.generator.reason_and_plan", new_callable=AsyncMock) as mock_reason:
            mock_reason.return_value = (mock_intent, mock_plan)

            with patch(
                "app.ai.generator.generate_cadquery_code", new_callable=AsyncMock
            ) as mock_codegen:
                mock_codegen.return_value = mock_code_result

                with patch(
                    "app.ai.generator.validate_result", new_callable=AsyncMock
                ) as mock_validate:
                    mock_validate.return_value = {"is_valid": True}

                    result = await generate_from_description(
                        "Create a box",
                        output_dir=tmp_path,
                        job_id="custom-job-123",
                    )

                    assert result.job_id == "custom-job-123"

    @pytest.mark.asyncio
    async def test_generate_with_precomputed_intent(self, tmp_path):
        """Test that precomputed intent skips reasoning and is used directly."""
        from app.ai.codegen import CodeGenerationResult
        from app.ai.reasoning import PartIntent

        # Create a precomputed intent for a cylinder
        precomputed_intent = PartIntent(
            part_type="cylinder",
            primary_function="Standard Cylinder",
            overall_dimensions={"diameter": 50.8, "height": 101.6},
            confidence=0.95,
            assumptions_made=["User wanted metric dimensions"],
            clarifications_needed=[],
        )

        mock_shape = Cylinder(25.4, 101.6)

        mock_code_result = CodeGenerationResult(
            code="result = Cylinder(25.4, 101.6)",
            shape=mock_shape,
            generation_time_ms=50,
            execution_time_ms=25,
            adjustments=[],
            error=None,
        )

        # reason_and_plan should NOT be called when precomputed_intent is provided
        with patch("app.ai.generator.reason_and_plan", new_callable=AsyncMock) as mock_reason:
            mock_reason.return_value = (None, None)  # Should never be used

            with patch(
                "app.ai.generator.generate_cadquery_code", new_callable=AsyncMock
            ) as mock_codegen:
                mock_codegen.return_value = mock_code_result

                with patch(
                    "app.ai.generator.validate_result", new_callable=AsyncMock
                ) as mock_validate:
                    mock_validate.return_value = {"is_valid": True}

                    result = await generate_from_description(
                        "Make a cylinder 2 inches diameter",
                        output_dir=tmp_path,
                        precomputed_intent=precomputed_intent,
                    )

                    # Verify reason_and_plan was NOT called
                    mock_reason.assert_not_called()

                    # Verify code generation was called with the precomputed intent
                    mock_codegen.assert_called_once()
                    call_args = mock_codegen.call_args
                    passed_intent = call_args.kwargs.get("intent")
                    assert passed_intent is not None
                    assert passed_intent.part_type == "cylinder"
                    assert passed_intent.overall_dimensions["diameter"] == 50.8

                    # Verify result
                    assert result.is_successful
                    # The warning is prefixed with "Assumption: " by the generator
                    assert any("User wanted metric dimensions" in w for w in result.warnings)
