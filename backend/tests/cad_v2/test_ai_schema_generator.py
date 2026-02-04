"""Tests for CAD v2 schema generator."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.cad_v2.ai.schema_generator import (
    SchemaGenerator,
    GenerationResult,
    SchemaGenerationError,
    generate_enclosure,
)
from app.cad_v2.ai.intent import IntentType, ParsedIntent
from app.cad_v2.schemas.enclosure import EnclosureSpec


class TestGenerationResult:
    """Tests for GenerationResult dataclass."""

    def test_success_result(self) -> None:
        """Successful result should have spec."""
        result = GenerationResult(
            spec=MagicMock(spec=EnclosureSpec),
            success=True,
        )
        assert result.success is True
        assert result.spec is not None
        assert result.validation_errors is None

    def test_failed_result(self) -> None:
        """Failed result should have errors."""
        result = GenerationResult(
            spec=None,
            success=False,
            validation_errors=["Missing required field"],
        )
        assert result.success is False
        assert result.spec is None
        assert len(result.validation_errors) == 1

    def test_result_with_clarification(self) -> None:
        """Result may request clarification."""
        result = GenerationResult(
            spec=None,
            success=False,
            clarification_needed="What size should the enclosure be?",
        )
        assert result.clarification_needed is not None

    def test_result_with_warnings(self) -> None:
        """Successful result may have warnings."""
        result = GenerationResult(
            spec=MagicMock(spec=EnclosureSpec),
            success=True,
            warnings=["Wall thickness may be too thin"],
        )
        assert result.success is True
        assert len(result.warnings) == 1

    def test_result_with_raw_json(self) -> None:
        """Result can include raw JSON for debugging."""
        raw = {"exterior": {"width": 100}}
        result = GenerationResult(
            spec=MagicMock(spec=EnclosureSpec),
            success=True,
            raw_json=raw,
        )
        assert result.raw_json == raw


class TestSchemaGenerationError:
    """Tests for SchemaGenerationError exception."""

    def test_error_with_message(self) -> None:
        """Error should have message."""
        error = SchemaGenerationError("Failed to generate")
        assert "Failed to generate" in str(error)

    def test_error_with_details(self) -> None:
        """Error can include details list."""
        error = SchemaGenerationError(
            "Failed",
            details=["Detail 1", "Detail 2"],
        )
        assert len(error.details) == 2

    def test_error_with_raw_response(self) -> None:
        """Error can include raw AI response."""
        error = SchemaGenerationError(
            "Parse failed",
            raw_response='{"invalid json',
        )
        assert error.raw_response == '{"invalid json'


class TestSchemaGeneratorInit:
    """Tests for SchemaGenerator initialization."""

    def test_initialization(self) -> None:
        """Generator should initialize without errors."""
        generator = SchemaGenerator()
        assert generator._provider is None  # Lazy loaded
        assert generator._intent_parser is not None
        assert generator._registry is not None

    def test_provider_lazy_loading(self) -> None:
        """Provider should be lazy loaded."""
        generator = SchemaGenerator()
        # Provider attribute access would trigger loading
        # We just verify internal state for now
        assert generator._provider is None


class TestSchemaGeneratorValidation:
    """Tests for schema validation logic."""

    @pytest.fixture
    def generator(self) -> SchemaGenerator:
        """Create schema generator."""
        return SchemaGenerator()

    def test_validate_valid_json(self, generator: SchemaGenerator) -> None:
        """Should validate correct JSON structure."""
        valid_json = {
            "exterior": {
                "width": {"value": 100, "unit": "mm"},
                "depth": {"value": 80, "unit": "mm"},
                "height": {"value": 40, "unit": "mm"},
            },
            "walls": {
                "thickness": {"value": 2.5, "unit": "mm"},
            },
        }
        spec = generator._validate_and_build(valid_json)
        assert spec is not None
        assert spec.exterior.width_mm == 100

    def test_validate_missing_exterior(self, generator: SchemaGenerator) -> None:
        """Should reject JSON without exterior."""
        invalid_json = {
            "walls": {"thickness": {"value": 2.5, "unit": "mm"}},
        }
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            generator._validate_and_build(invalid_json)

    def test_validate_invalid_dimensions(self, generator: SchemaGenerator) -> None:
        """Should reject invalid dimensions."""
        invalid_json = {
            "exterior": {
                "width": {"value": -100, "unit": "mm"},  # Negative!
                "depth": {"value": 80, "unit": "mm"},
                "height": {"value": 40, "unit": "mm"},
            },
        }
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            generator._validate_and_build(invalid_json)


class TestSchemaGeneratorWarnings:
    """Tests for warning generation."""

    @pytest.fixture
    def generator(self) -> SchemaGenerator:
        """Create schema generator."""
        return SchemaGenerator()

    def test_thin_wall_warning(self, generator: SchemaGenerator) -> None:
        """Should warn about thin walls."""
        # Create spec with thin walls
        from app.cad_v2.schemas.base import BoundingBox, Dimension
        from app.cad_v2.schemas.enclosure import EnclosureSpec, WallSpec

        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            walls=WallSpec(thickness=Dimension(value=1.0)),  # Too thin
        )
        warnings = generator._check_warnings(spec, None)
        assert any("thin" in w.lower() for w in warnings)

    def test_large_dimension_warning(self, generator: SchemaGenerator) -> None:
        """Should warn about large dimensions."""
        from app.cad_v2.schemas.base import BoundingBox, Dimension
        from app.cad_v2.schemas.enclosure import EnclosureSpec, WallSpec

        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=400),  # Too large
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            walls=WallSpec(thickness=Dimension(value=2.5)),
        )
        warnings = generator._check_warnings(spec, None)
        assert any("bed" in w.lower() or "300" in w for w in warnings)

    def test_no_warnings_for_valid_spec(self, generator: SchemaGenerator) -> None:
        """Should not warn for valid spec."""
        from app.cad_v2.schemas.base import BoundingBox, Dimension
        from app.cad_v2.schemas.enclosure import EnclosureSpec, WallSpec

        spec = EnclosureSpec(
            exterior=BoundingBox(
                width=Dimension(value=100),
                depth=Dimension(value=80),
                height=Dimension(value=40),
            ),
            walls=WallSpec(thickness=Dimension(value=2.5)),
        )
        warnings = generator._check_warnings(spec, None)
        assert len(warnings) == 0


class TestSchemaGeneratorIntentHandling:
    """Tests for intent handling in generation."""

    @pytest.fixture
    def generator(self) -> SchemaGenerator:
        """Create schema generator."""
        return SchemaGenerator()

    @pytest.mark.asyncio
    async def test_unclear_intent_returns_clarification(
        self, generator: SchemaGenerator
    ) -> None:
        """Unclear intent should request clarification."""
        # Mock intent parser to return unclear
        with patch.object(
            generator._intent_parser,
            "parse",
            new_callable=AsyncMock,
        ) as mock_parse:
            mock_parse.return_value = ParsedIntent(
                intent_type=IntentType.UNCLEAR,
                raw_input="hello",
                clarification_needed="What would you like to create?",
            )

            result = await generator.generate("hello")

        assert result.success is False
        assert result.clarification_needed is not None

    @pytest.mark.asyncio
    async def test_non_create_intent_returns_clarification(
        self, generator: SchemaGenerator
    ) -> None:
        """Non-create intent should suggest creation."""
        with patch.object(
            generator._intent_parser,
            "parse",
            new_callable=AsyncMock,
        ) as mock_parse:
            mock_parse.return_value = ParsedIntent(
                intent_type=IntentType.QUERY_INFO,
                raw_input="What is a Pi 5?",
            )

            result = await generator.generate("What is a Pi 5?")

        assert result.success is False
        assert result.clarification_needed is not None
        assert "create" in result.clarification_needed.lower()
