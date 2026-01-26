"""
Tests for end-to-end CAD generation.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import cadquery as cq

from app.ai.generator import (
    GenerationResult,
    CADGenerator,
    generate_from_description,
)
from app.ai.parser import CADParameters, ShapeType, Feature, FeatureType, ParseResult


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
        
        assert isinstance(shape, cq.Workplane)
        
        # Verify volume
        volume = shape.val().Volume()
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
        
        assert isinstance(shape, cq.Workplane)
        
        # Verify approximate volume (π * r² * h)
        volume = shape.val().Volume()
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
        
        assert isinstance(shape, cq.Workplane)
    
    def test_generate_with_fillet_feature(self):
        """Test generating shape with fillet feature."""
        params = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 50, "width": 50, "height": 50},
            features=[
                Feature(type=FeatureType.FILLET, parameters={"radius": 3})
            ],
            confidence=0.9,
        )
        
        generator = CADGenerator()
        shape = generator.generate(params)
        
        # Fillet reduces volume slightly
        volume = shape.val().Volume()
        box_volume = 50 * 50 * 50
        assert volume < box_volume
    
    def test_generate_with_hole_feature(self):
        """Test generating shape with hole feature."""
        params = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 50, "width": 50, "height": 20},
            features=[
                Feature(type=FeatureType.HOLE, parameters={"diameter": 10, "depth": 15})
            ],
            confidence=0.9,
        )
        
        generator = CADGenerator()
        shape = generator.generate(params)
        
        # Hole reduces volume
        volume = shape.val().Volume()
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
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.9,
            ),
            shape=MagicMock(),
            step_data=b"step data",
        )
        
        assert result.is_successful
    
    def test_is_successful_false_no_export(self):
        """Test is_successful when no export data."""
        result = GenerationResult(
            description="test",
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.9,
            ),
            shape=MagicMock(),
            step_data=None,
            stl_data=None,
        )
        
        assert not result.is_successful
    
    def test_get_stats(self):
        """Test get_stats returns expected data."""
        result = GenerationResult(
            description="test",
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.85,
            ),
            shape=MagicMock(),
            step_data=b"data",
            parse_time_ms=100,
            generate_time_ms=50,
            export_time_ms=200,
            total_time_ms=350,
        )
        
        stats = result.get_stats()
        
        assert stats["shape"] == "box"
        assert stats["confidence"] == 0.85
        assert stats["parse_time_ms"] == 100
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
        mock_parse_result = ParseResult(
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.9,
                assumptions=["No unit specified, assuming millimeters"],
            ),
            raw_response="{}",
            parse_time_ms=100,
        )
        
        with patch("app.ai.generator.parse_description", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_parse_result
            
            result = await generate_from_description(
                "Create a box 100x50x30",
                output_dir=tmp_path,
            )
            
            assert result.is_successful
            assert result.parameters.shape == ShapeType.BOX
            assert result.step_path.exists()
            assert result.stl_path.exists()
            assert result.total_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_generate_cylinder_e2e(self, tmp_path):
        """Test end-to-end cylinder generation."""
        mock_parse_result = ParseResult(
            parameters=CADParameters(
                shape=ShapeType.CYLINDER,
                dimensions={"radius": 25, "height": 100},
                confidence=0.85,
            ),
            raw_response="{}",
            parse_time_ms=80,
        )
        
        with patch("app.ai.generator.parse_description", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_parse_result
            
            result = await generate_from_description(
                "Make a cylinder 50mm diameter, 100mm tall",
                output_dir=tmp_path,
            )
            
            assert result.is_successful
            assert result.parameters.shape == ShapeType.CYLINDER
    
    @pytest.mark.asyncio
    async def test_generate_adds_warnings_for_assumptions(self, tmp_path):
        """Test warnings are added for assumptions."""
        mock_parse_result = ParseResult(
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.9,
                assumptions=["Assumed centered", "No units given"],
            ),
            raw_response="{}",
            parse_time_ms=50,
        )
        
        with patch("app.ai.generator.parse_description", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_parse_result
            
            result = await generate_from_description(
                "Create a box",
                output_dir=tmp_path,
            )
            
            assert len(result.warnings) >= 2
            assert any("Assumed" in w for w in result.warnings)
    
    @pytest.mark.asyncio
    async def test_generate_warns_on_low_confidence(self, tmp_path):
        """Test warning is added for low confidence."""
        mock_parse_result = ParseResult(
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.5,  # Low confidence
            ),
            raw_response="{}",
            parse_time_ms=50,
        )
        
        with patch("app.ai.generator.parse_description", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_parse_result
            
            result = await generate_from_description(
                "Create something",
                output_dir=tmp_path,
            )
            
            assert any("confidence" in w.lower() for w in result.warnings)
    
    @pytest.mark.asyncio
    async def test_generate_step_only(self, tmp_path):
        """Test generating only STEP file."""
        mock_parse_result = ParseResult(
            parameters=CADParameters(
                shape=ShapeType.SPHERE,
                dimensions={"radius": 50},
                confidence=0.9,
            ),
            raw_response="{}",
            parse_time_ms=50,
        )
        
        with patch("app.ai.generator.parse_description", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_parse_result
            
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
        mock_parse_result = ParseResult(
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.9,
            ),
            raw_response="{}",
            parse_time_ms=50,
        )
        
        with patch("app.ai.generator.parse_description", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_parse_result
            
            result = await generate_from_description(
                "Create a box",
                output_dir=tmp_path,
                job_id="custom-job-123",
            )
            
            assert result.job_id == "custom-job-123"
