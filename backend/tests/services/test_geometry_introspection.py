"""
Tests for Geometry Introspection Service.

Validates query detection, dimension extraction from result_data and
design_extra_data, and correct formatting of measurement answers.
"""

from __future__ import annotations

import pytest

from app.services.geometry_introspection import (
    GeometryAnswer,
    answer_geometry_query,
    is_geometry_query,
)

# =============================================================================
# Fixtures / helpers
# =============================================================================


def _result_data(
    *,
    dims: dict | None = None,
    stats: dict | None = None,
    shape: str = "box",
) -> dict:
    """Build a minimal ``conversation.result_data`` dict."""
    return {
        "dimensions": dims
        if dims is not None
        else {"length": 100, "width": 50, "height": 30, "unit": "mm"},
        "stats": stats if stats is not None else {"volume": 150000.0, "surfaceArea": 31000.0},
        "shape": shape,
        "status": "completed",
    }


def _design_extra(*, dims: dict | None = None) -> dict:
    """Build a minimal ``design.extra_data`` dict."""
    return {
        "dimensions": dims
        if dims is not None
        else {"length": 80, "width": 40, "height": 20, "unit": "mm"},
    }


# =============================================================================
# is_geometry_query tests
# =============================================================================


class TestIsGeometryQuery:
    """Verify pattern matching for geometry-related user messages."""

    @pytest.mark.parametrize(
        "message",
        [
            "What is the height?",
            "how tall is it?",
            "what is the width of the model?",
            "How wide is it?",
            "What is the length?",
            "how long is the part?",
            "What are the dimensions?",
            "Show me the measurements",
            "What is the diameter?",
            "How thick is it?",
            "what is the volume?",
            "How much does it weigh?",
            "What is the surface area?",
            "Tell me the dimensions",
            "how big is it?",
            "what is the overall size?",
            "what is the bounding box?",
            "is it 100 mm tall?",
        ],
    )
    def test_detects_geometry_queries(self, message: str) -> None:
        """Known geometry questions must be detected."""
        assert is_geometry_query(message) is True

    @pytest.mark.parametrize(
        "message",
        [
            "Create a box 100x50x30mm",
            "Add a hole on the top face",
            "make it taller",
            "fillet the edges",
            "remove the slot",
            "hello",
            "what material should I use?",
            "can you change the colour?",
        ],
    )
    def test_rejects_non_geometry_queries(self, message: str) -> None:
        """Non-geometry messages should not match."""
        assert is_geometry_query(message) is False


# =============================================================================
# answer_geometry_query — specific dimension tests
# =============================================================================


class TestAnswerSpecificDimension:
    """Answers to questions about a single dimension."""

    def test_answer_height_from_result_data(self) -> None:
        """'What is the height?' should return the height value."""
        answer = answer_geometry_query(
            "What is the height?",
            result_data=_result_data(),
        )
        assert answer.answered is True
        assert "30" in answer.response_text
        assert "height" in answer.response_text.lower()
        assert answer.source == "result_data"

    def test_answer_width_from_result_data(self) -> None:
        """'How wide is it?' should return the width value."""
        answer = answer_geometry_query(
            "How wide is it?",
            result_data=_result_data(),
        )
        assert answer.answered is True
        assert "50" in answer.response_text

    def test_answer_length_from_result_data(self) -> None:
        """'What is the length?' should return the length value."""
        answer = answer_geometry_query(
            "What is the length?",
            result_data=_result_data(),
        )
        assert answer.answered is True
        assert "100" in answer.response_text

    def test_answer_diameter_when_present(self) -> None:
        """Diameter questions should return diameter if available."""
        answer = answer_geometry_query(
            "What is the diameter?",
            result_data=_result_data(
                dims={"diameter": 25, "height": 50, "unit": "mm"},
                shape="cylinder",
            ),
        )
        assert answer.answered is True
        assert "25" in answer.response_text

    def test_answer_thickness_when_present(self) -> None:
        """Thickness questions should return thickness if available."""
        answer = answer_geometry_query(
            "How thick is it?",
            result_data=_result_data(
                dims={"thickness": 3, "length": 100, "width": 50, "unit": "mm"},
            ),
        )
        assert answer.answered is True
        assert "3" in answer.response_text

    def test_dimension_not_found_lists_available(self) -> None:
        """If the requested dim is missing, list what is available."""
        answer = answer_geometry_query(
            "What is the radius?",
            result_data=_result_data(
                dims={"length": 100, "width": 50, "height": 30, "unit": "mm"},
            ),
        )
        assert answer.answered is False
        assert "length" in answer.response_text.lower()
        assert "width" in answer.response_text.lower()

    def test_colloquial_tall_maps_to_height(self) -> None:
        """'How tall' should map to height."""
        answer = answer_geometry_query(
            "How tall is the part?",
            result_data=_result_data(),
        )
        assert answer.answered is True
        assert "30" in answer.response_text

    def test_colloquial_deep_maps_to_length(self) -> None:
        """'How deep' should map to length."""
        answer = answer_geometry_query(
            "How deep is it?",
            result_data=_result_data(),
        )
        assert answer.answered is True
        assert "100" in answer.response_text


# =============================================================================
# answer_geometry_query — all dimensions
# =============================================================================


class TestAnswerAllDimensions:
    """Answers to general 'what are the dimensions?' queries."""

    def test_returns_all_dimensions(self) -> None:
        """General dimension query should list all available dims."""
        answer = answer_geometry_query(
            "What are the dimensions?",
            result_data=_result_data(),
        )
        assert answer.answered is True
        assert "100" in answer.response_text
        assert "50" in answer.response_text
        assert "30" in answer.response_text
        assert "box" in answer.response_text.lower()

    def test_includes_volume_in_summary(self) -> None:
        """All-dimensions answer should include volume from stats."""
        answer = answer_geometry_query(
            "List the dimensions",
            result_data=_result_data(
                stats={"volume": 150000.0},
            ),
        )
        assert "volume" in answer.response_text.lower()

    def test_includes_surface_area_in_summary(self) -> None:
        """All-dimensions answer should include surface area from stats."""
        answer = answer_geometry_query(
            "Tell me the dimensions",
            result_data=_result_data(
                stats={"surfaceArea": 31000.0},
            ),
        )
        assert "surface area" in answer.response_text.lower()


# =============================================================================
# answer_geometry_query — volume, surface area, weight
# =============================================================================


class TestAnswerVolumeAndWeight:
    """Answers to volume, surface area, and weight queries."""

    def test_volume_returns_value(self) -> None:
        """Volume query should return the volume."""
        answer = answer_geometry_query(
            "What is the volume?",
            result_data=_result_data(stats={"volume": 150000.0}),
        )
        assert answer.answered is True
        assert "150000" in answer.response_text

    def test_volume_unavailable(self) -> None:
        """Volume query with no stats returns unavailable message."""
        answer = answer_geometry_query(
            "What is the volume?",
            result_data=_result_data(stats={}),
        )
        assert answer.answered is False
        assert "not available" in answer.response_text.lower()

    def test_surface_area_returns_value(self) -> None:
        """Surface area query should return the value."""
        answer = answer_geometry_query(
            "What is the surface area?",
            result_data=_result_data(stats={"surfaceArea": 31000.0}),
        )
        assert answer.answered is True
        assert "31000" in answer.response_text

    def test_weight_estimate_returns_materials(self) -> None:
        """Weight query should give estimates for common materials."""
        answer = answer_geometry_query(
            "How much does it weigh?",
            result_data=_result_data(stats={"volume": 150000.0}),
        )
        assert answer.answered is True
        assert "PLA" in answer.response_text
        assert "ABS" in answer.response_text
        assert "Aluminum" in answer.response_text
        assert "Steel" in answer.response_text

    def test_weight_unavailable_without_volume(self) -> None:
        """Weight query without volume data returns unavailable message."""
        answer = answer_geometry_query(
            "What does it weigh?",
            result_data=_result_data(stats={}),
        )
        assert answer.answered is False


# =============================================================================
# answer_geometry_query — data source fallback
# =============================================================================


class TestDataSourceFallback:
    """Verify fallback from result_data to design_extra_data."""

    def test_prefers_result_data_over_design(self) -> None:
        """result_data should be preferred when both are available."""
        answer = answer_geometry_query(
            "What is the height?",
            result_data=_result_data(
                dims={"height": 30, "unit": "mm"},
            ),
            design_extra_data=_design_extra(
                dims={"height": 20, "unit": "mm"},
            ),
        )
        assert "30" in answer.response_text
        assert answer.source == "result_data"

    def test_falls_back_to_design_extra_data(self) -> None:
        """design_extra_data should be used when result_data has no dims."""
        answer = answer_geometry_query(
            "What is the height?",
            result_data=None,
            design_extra_data=_design_extra(),
        )
        assert answer.answered is True
        assert "20" in answer.response_text
        assert answer.source == "design_extra_data"

    def test_design_params_fallback(self) -> None:
        """If design has no dims but has params, extract from params."""
        answer = answer_geometry_query(
            "What are the dimensions?",
            result_data=None,
            design_extra_data={
                "parameters": {"length": 60, "width": 30, "height": 15},
            },
        )
        assert answer.answered is True
        assert "60" in answer.response_text
        assert answer.source == "design_extra_data"

    def test_no_data_returns_unavailable(self) -> None:
        """Both sources empty → unavailable response."""
        answer = answer_geometry_query(
            "What is the height?",
            result_data=None,
            design_extra_data=None,
        )
        assert answer.answered is False
        assert "generate the part first" in answer.response_text.lower()


# =============================================================================
# GeometryAnswer dataclass
# =============================================================================


class TestGeometryAnswerDataclass:
    """Basic dataclass contract tests."""

    def test_defaults(self) -> None:
        """Default values should be sensible."""
        ga = GeometryAnswer(answered=False, response_text="test")
        assert ga.dimensions == {}
        assert ga.source == "unavailable"

    def test_custom_values(self) -> None:
        """Custom initialisation should be captured."""
        ga = GeometryAnswer(
            answered=True,
            response_text="ok",
            dimensions={"h": 10},
            source="result_data",
        )
        assert ga.answered is True
        assert ga.dimensions == {"h": 10}
