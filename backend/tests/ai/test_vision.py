"""
Tests for AI Vision Module.

Tests extracted dimensions dataclass and vision extraction structures.
"""

from app.ai.vision import ExtractedDimensions

# =============================================================================
# ExtractedDimensions Tests
# =============================================================================


class TestExtractedDimensions:
    """Tests for ExtractedDimensions dataclass."""

    def test_default_creation(self):
        """Test creating with defaults."""
        dims = ExtractedDimensions()

        assert dims.overall_dimensions is None
        assert dims.mounting_holes is None
        assert dims.cutouts is None
        assert dims.connectors is None
        assert dims.tolerances is None
        assert dims.notes is None
        assert dims.raw_response is None
        assert dims.confidence == 0.0

    def test_with_overall_dimensions(self):
        """Test with overall dimensions."""
        dims = ExtractedDimensions(
            overall_dimensions={
                "length": 100,
                "width": 80,
                "height": 50,
                "unit": "mm",
            }
        )

        assert dims.overall_dimensions["length"] == 100
        assert dims.overall_dimensions["width"] == 80
        assert dims.overall_dimensions["height"] == 50
        assert dims.overall_dimensions["unit"] == "mm"

    def test_with_mounting_holes(self):
        """Test with mounting holes list."""
        holes = [
            {"x": 10, "y": 10, "diameter": 5, "type": "through"},
            {"x": 90, "y": 10, "diameter": 5, "type": "through"},
            {"x": 10, "y": 70, "diameter": 5, "type": "threaded"},
            {"x": 90, "y": 70, "diameter": 5, "type": "threaded"},
        ]
        dims = ExtractedDimensions(mounting_holes=holes)

        assert len(dims.mounting_holes) == 4
        assert dims.mounting_holes[0]["x"] == 10
        assert dims.mounting_holes[2]["type"] == "threaded"

    def test_with_cutouts(self):
        """Test with cutouts list."""
        cutouts = [
            {"type": "rectangular", "x": 30, "y": 20, "width": 40, "height": 30},
            {"type": "circular", "x": 50, "y": 50, "diameter": 25},
        ]
        dims = ExtractedDimensions(cutouts=cutouts)

        assert len(dims.cutouts) == 2
        assert dims.cutouts[0]["type"] == "rectangular"
        assert dims.cutouts[1]["type"] == "circular"

    def test_with_connectors(self):
        """Test with connectors list."""
        connectors = [
            {"type": "USB-C", "x": 45, "y": 5, "width": 10, "height": 3},
            {"type": "HDMI", "x": 60, "y": 5, "width": 15, "height": 6},
        ]
        dims = ExtractedDimensions(connectors=connectors)

        assert len(dims.connectors) == 2
        assert dims.connectors[0]["type"] == "USB-C"
        assert dims.connectors[1]["type"] == "HDMI"

    def test_with_tolerances(self):
        """Test with tolerances dictionary."""
        tolerances = {
            "general": "+/- 0.1",
            "hole_positions": "+/- 0.05",
            "length": "+0.2/-0.1",
        }
        dims = ExtractedDimensions(tolerances=tolerances)

        assert dims.tolerances["general"] == "+/- 0.1"
        assert dims.tolerances["hole_positions"] == "+/- 0.05"

    def test_with_notes(self):
        """Test with notes list."""
        notes = [
            "All dimensions in millimeters",
            "Material: Aluminum 6061-T6",
            "Deburr all edges",
        ]
        dims = ExtractedDimensions(notes=notes)

        assert len(dims.notes) == 3
        assert "millimeters" in dims.notes[0]

    def test_with_raw_response(self):
        """Test with raw response."""
        raw = '{"overall_dimensions": {"length": 100}}'
        dims = ExtractedDimensions(raw_response=raw)

        assert dims.raw_response == raw

    def test_with_confidence(self):
        """Test with confidence score."""
        dims = ExtractedDimensions(confidence=0.95)

        assert dims.confidence == 0.95

    def test_full_extraction(self):
        """Test with all fields populated."""
        dims = ExtractedDimensions(
            overall_dimensions={"length": 100, "width": 80, "height": 50},
            mounting_holes=[{"x": 10, "y": 10, "diameter": 5}],
            cutouts=[{"type": "rectangular", "width": 40, "height": 30}],
            connectors=[{"type": "USB-C", "x": 45, "y": 5}],
            tolerances={"general": "+/- 0.1"},
            notes=["Material: ABS"],
            raw_response='{"test": true}',
            confidence=0.92,
        )

        assert dims.overall_dimensions is not None
        assert dims.mounting_holes is not None
        assert dims.cutouts is not None
        assert dims.connectors is not None
        assert dims.tolerances is not None
        assert dims.notes is not None
        assert dims.raw_response is not None
        assert dims.confidence == 0.92


# =============================================================================
# to_dict Tests
# =============================================================================


class TestExtractedDimensionsToDict:
    """Tests for ExtractedDimensions to_dict method."""

    def test_empty_to_dict(self):
        """Test to_dict with defaults."""
        dims = ExtractedDimensions()
        result = dims.to_dict()

        assert "overall_dimensions" in result
        assert "mounting_holes" in result
        assert "cutouts" in result
        assert "connectors" in result
        assert "tolerances" in result
        assert "notes" in result
        assert "confidence" in result

        assert result["overall_dimensions"] is None
        assert result["confidence"] == 0.0

    def test_populated_to_dict(self):
        """Test to_dict with populated fields."""
        dims = ExtractedDimensions(
            overall_dimensions={"length": 100, "width": 80},
            mounting_holes=[{"x": 10, "y": 10, "diameter": 5}],
            confidence=0.85,
        )
        result = dims.to_dict()

        assert result["overall_dimensions"]["length"] == 100
        assert len(result["mounting_holes"]) == 1
        assert result["confidence"] == 0.85

    def test_to_dict_excludes_raw_response(self):
        """Test that to_dict excludes raw_response."""
        dims = ExtractedDimensions(
            raw_response='{"test": true}',
            confidence=0.9,
        )
        result = dims.to_dict()

        # raw_response should not be in the output dict
        assert "raw_response" not in result

    def test_to_dict_returns_new_dict(self):
        """Test that to_dict returns a new dictionary."""
        dims = ExtractedDimensions(
            overall_dimensions={"length": 100},
        )
        result1 = dims.to_dict()
        result2 = dims.to_dict()

        assert result1 is not result2


# =============================================================================
# Edge Cases
# =============================================================================


class TestVisionEdgeCases:
    """Tests for edge cases in vision module."""

    def test_zero_confidence(self):
        """Test zero confidence."""
        dims = ExtractedDimensions(confidence=0.0)

        assert dims.confidence == 0.0

    def test_full_confidence(self):
        """Test full confidence (1.0)."""
        dims = ExtractedDimensions(confidence=1.0)

        assert dims.confidence == 1.0

    def test_empty_lists(self):
        """Test with empty lists."""
        dims = ExtractedDimensions(
            mounting_holes=[],
            cutouts=[],
            connectors=[],
            notes=[],
        )

        assert dims.mounting_holes == []
        assert dims.cutouts == []
        assert dims.connectors == []
        assert dims.notes == []

    def test_empty_dicts(self):
        """Test with empty dictionaries."""
        dims = ExtractedDimensions(
            overall_dimensions={},
            tolerances={},
        )

        assert dims.overall_dimensions == {}
        assert dims.tolerances == {}

    def test_complex_nested_data(self):
        """Test with complex nested data structures."""
        holes = [
            {
                "x": 10,
                "y": 10,
                "diameter": 5,
                "type": "threaded",
                "metadata": {
                    "thread_pitch": 0.8,
                    "thread_depth": 10,
                },
            },
        ]
        dims = ExtractedDimensions(mounting_holes=holes)

        assert dims.mounting_holes[0]["metadata"]["thread_pitch"] == 0.8

    def test_very_small_dimensions(self):
        """Test with very small dimension values."""
        dims = ExtractedDimensions(
            overall_dimensions={
                "length": 0.1,
                "width": 0.05,
                "height": 0.01,
            }
        )

        assert dims.overall_dimensions["length"] == 0.1
        assert dims.overall_dimensions["height"] == 0.01

    def test_very_large_dimensions(self):
        """Test with very large dimension values."""
        dims = ExtractedDimensions(
            overall_dimensions={
                "length": 10000,
                "width": 5000,
                "height": 2000,
            }
        )

        assert dims.overall_dimensions["length"] == 10000

    def test_many_mounting_holes(self):
        """Test with many mounting holes."""
        holes = [{"x": i * 10, "y": 0, "diameter": 3} for i in range(100)]
        dims = ExtractedDimensions(mounting_holes=holes)

        assert len(dims.mounting_holes) == 100

    def test_unicode_in_notes(self):
        """Test with unicode characters in notes."""
        dims = ExtractedDimensions(
            notes=[
                "Tolerance: ±0.1mm",
                "Material: アルミニウム",
                "Surface: Ra 1.6μm",
            ]
        )

        assert "±" in dims.notes[0]
        assert "μm" in dims.notes[2]
