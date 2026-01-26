"""
Tests for natural language parser.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.ai.parser import (
    CADParameters,
    Feature,
    FeatureType,
    ShapeType,
    ParseResult,
    DescriptionParser,
    parse_description,
    convert_to_mm,
    UNIT_TO_MM,
)
from app.ai.exceptions import AIParseError, AIValidationError


# =============================================================================
# Unit Conversion Tests
# =============================================================================

class TestUnitConversion:
    """Tests for unit conversion utilities."""
    
    def test_mm_no_conversion(self):
        """Test mm values stay the same."""
        assert convert_to_mm(100, "mm") == 100
    
    def test_cm_to_mm(self):
        """Test cm to mm conversion."""
        assert convert_to_mm(10, "cm") == 100
    
    def test_m_to_mm(self):
        """Test m to mm conversion."""
        assert convert_to_mm(1, "m") == 1000
    
    def test_inches_to_mm(self):
        """Test inches to mm conversion."""
        result = convert_to_mm(1, "inches")
        assert abs(result - 25.4) < 0.01
    
    def test_in_shorthand(self):
        """Test 'in' shorthand for inches."""
        result = convert_to_mm(2, "in")
        assert abs(result - 50.8) < 0.01
    
    def test_feet_to_mm(self):
        """Test feet to mm conversion."""
        result = convert_to_mm(1, "feet")
        assert abs(result - 304.8) < 0.01
    
    def test_unknown_unit_raises_error(self):
        """Test unknown unit raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            convert_to_mm(100, "cubits")
        
        assert "cubits" in str(exc_info.value).lower()


# =============================================================================
# CADParameters Model Tests
# =============================================================================

class TestCADParameters:
    """Tests for CADParameters model."""
    
    def test_valid_box_parameters(self):
        """Test valid box parameters are accepted."""
        params = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 100, "width": 50, "height": 30},
            confidence=0.9,
        )
        
        assert params.shape == ShapeType.BOX
        assert params.dimensions["length"] == 100
    
    def test_box_missing_dimension_fails(self):
        """Test box without required dimension fails."""
        with pytest.raises(ValueError) as exc_info:
            CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50},  # Missing height
                confidence=0.9,
            )
        
        assert "height" in str(exc_info.value)
    
    def test_cylinder_with_radius(self):
        """Test cylinder with radius is valid."""
        params = CADParameters(
            shape=ShapeType.CYLINDER,
            dimensions={"radius": 25, "height": 100},
            confidence=0.9,
        )
        
        assert params.shape == ShapeType.CYLINDER
    
    def test_cylinder_with_diameter(self):
        """Test cylinder with diameter is valid."""
        params = CADParameters(
            shape=ShapeType.CYLINDER,
            dimensions={"diameter": 50, "height": 100},
            confidence=0.9,
        )
        
        assert params.shape == ShapeType.CYLINDER
    
    def test_cylinder_without_size_fails(self):
        """Test cylinder without radius or diameter fails."""
        with pytest.raises(ValueError) as exc_info:
            CADParameters(
                shape=ShapeType.CYLINDER,
                dimensions={"height": 100},  # Missing radius/diameter
                confidence=0.9,
            )
        
        assert "radius" in str(exc_info.value).lower() or "diameter" in str(exc_info.value).lower()
    
    def test_negative_dimension_fails(self):
        """Test negative dimensions are rejected."""
        with pytest.raises(ValueError) as exc_info:
            CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": -100, "width": 50, "height": 30},
                confidence=0.9,
            )
        
        assert "positive" in str(exc_info.value)
    
    def test_get_dimension_returns_value(self):
        """Test get_dimension returns dimension value."""
        params = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 100, "width": 50, "height": 30},
            confidence=0.9,
        )
        
        assert params.get_dimension("length") == 100
    
    def test_get_dimension_with_default(self):
        """Test get_dimension returns default for missing."""
        params = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 100, "width": 50, "height": 30},
            confidence=0.9,
        )
        
        assert params.get_dimension("radius", default=10) == 10
    
    def test_has_features(self):
        """Test has_features property."""
        params_without = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 100, "width": 50, "height": 30},
            confidence=0.9,
        )
        assert not params_without.has_features
        
        params_with = CADParameters(
            shape=ShapeType.BOX,
            dimensions={"length": 100, "width": 50, "height": 30},
            features=[Feature(type=FeatureType.FILLET, parameters={"radius": 3})],
            confidence=0.9,
        )
        assert params_with.has_features


# =============================================================================
# Feature Model Tests
# =============================================================================

class TestFeature:
    """Tests for Feature model."""
    
    def test_valid_hole_feature(self):
        """Test valid hole feature."""
        feature = Feature(
            type=FeatureType.HOLE,
            parameters={"diameter": 10, "depth": 20}
        )
        
        assert feature.type == FeatureType.HOLE
        assert feature.parameters["diameter"] == 10
    
    def test_valid_fillet_feature(self):
        """Test valid fillet feature."""
        feature = Feature(
            type=FeatureType.FILLET,
            parameters={"radius": 3}
        )
        
        assert feature.type == FeatureType.FILLET


# =============================================================================
# Parser Tests
# =============================================================================

class TestDescriptionParser:
    """Tests for DescriptionParser class."""
    
    @pytest.mark.asyncio
    async def test_parse_empty_description_fails(self):
        """Test parsing empty description raises error."""
        parser = DescriptionParser()
        
        with pytest.raises(AIValidationError):
            await parser.parse("")
    
    @pytest.mark.asyncio
    async def test_parse_box_description(self):
        """Test parsing a box description."""
        parser = DescriptionParser()
        
        # Mock AI response
        mock_response = json.dumps({
            "shape": "box",
            "dimensions": {"length": 100, "width": 50, "height": 30},
            "features": [],
            "units": "mm",
            "confidence": 0.95,
            "assumptions": []
        })
        
        with patch.object(parser.client, "complete_json", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response
            
            result = await parser.parse("Create a box 100x50x30mm")
            
            assert result.parameters.shape == ShapeType.BOX
            assert result.parameters.dimensions["length"] == 100
            assert result.parameters.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_parse_converts_units(self):
        """Test parser converts units to mm."""
        parser = DescriptionParser()
        
        # AI returns inches
        mock_response = json.dumps({
            "shape": "box",
            "dimensions": {"length": 4, "width": 2, "height": 1},
            "features": [],
            "units": "inches",
            "confidence": 0.9,
            "assumptions": []
        })
        
        with patch.object(parser.client, "complete_json", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response
            
            result = await parser.parse("Create a box 4x2x1 inches")
            
            # Should be converted to mm
            assert abs(result.parameters.dimensions["length"] - 101.6) < 0.1
            assert abs(result.parameters.dimensions["width"] - 50.8) < 0.1
    
    @pytest.mark.asyncio
    async def test_parse_invalid_json_raises_error(self):
        """Test invalid JSON from AI raises ParseError."""
        parser = DescriptionParser()
        
        with patch.object(parser.client, "complete_json", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = "not valid json {"
            
            with pytest.raises(AIParseError):
                await parser.parse("Create a box")
    
    @pytest.mark.asyncio
    async def test_parse_result_timing(self):
        """Test parse result includes timing info."""
        parser = DescriptionParser()
        
        mock_response = json.dumps({
            "shape": "sphere",
            "dimensions": {"radius": 50},
            "features": [],
            "units": "mm",
            "confidence": 0.9,
            "assumptions": []
        })
        
        with patch.object(parser.client, "complete_json", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response
            
            result = await parser.parse("Create a sphere with 50mm radius")
            
            assert result.parse_time_ms > 0
            assert result.raw_response == mock_response


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestParseDescriptionFunction:
    """Tests for parse_description convenience function."""
    
    @pytest.mark.asyncio
    async def test_parse_description_works(self):
        """Test parse_description function."""
        mock_response = json.dumps({
            "shape": "cylinder",
            "dimensions": {"radius": 25, "height": 100},
            "features": [],
            "units": "mm",
            "confidence": 0.85,
            "assumptions": []
        })
        
        with patch("app.ai.parser.DescriptionParser.parse", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = ParseResult(
                parameters=CADParameters(
                    shape=ShapeType.CYLINDER,
                    dimensions={"radius": 25, "height": 100},
                    confidence=0.85,
                ),
                raw_response=mock_response,
                parse_time_ms=50.0,
            )
            
            result = await parse_description("Create a cylinder")
            
            assert result.parameters.shape == ShapeType.CYLINDER


# =============================================================================
# ParseResult Tests
# =============================================================================

class TestParseResult:
    """Tests for ParseResult class."""
    
    def test_is_high_confidence_true(self):
        """Test is_high_confidence for high confidence."""
        result = ParseResult(
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.9,
            ),
            raw_response="{}",
            parse_time_ms=50.0,
        )
        
        assert result.is_high_confidence
    
    def test_is_high_confidence_false(self):
        """Test is_high_confidence for low confidence."""
        result = ParseResult(
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.6,
            ),
            raw_response="{}",
            parse_time_ms=50.0,
        )
        
        assert not result.is_high_confidence
