"""Tests for CAD v2 intent parser."""

import pytest

from app.cad_v2.ai.intent import IntentParser, IntentType, ParsedIntent


class TestIntentType:
    """Tests for IntentType enum."""

    def test_create_enclosure_value(self) -> None:
        """CREATE_ENCLOSURE should have correct value."""
        assert IntentType.CREATE_ENCLOSURE.value == "create_enclosure"

    def test_modify_design_value(self) -> None:
        """MODIFY_DESIGN should have correct value."""
        assert IntentType.MODIFY_DESIGN.value == "modify_design"

    def test_query_info_value(self) -> None:
        """QUERY_INFO should have correct value."""
        assert IntentType.QUERY_INFO.value == "query_info"

    def test_unclear_value(self) -> None:
        """UNCLEAR should have correct value."""
        assert IntentType.UNCLEAR.value == "unclear"


class TestParsedIntent:
    """Tests for ParsedIntent dataclass."""

    def test_default_values(self) -> None:
        """ParsedIntent should have sensible defaults."""
        intent = ParsedIntent(intent_type=IntentType.CREATE_ENCLOSURE)
        assert intent.components == []
        assert intent.dimensions_explicit is False
        assert intent.features_mentioned == []
        assert intent.raw_input == ""
        assert intent.clarification_needed is None
        assert intent.confidence == 0.0

    def test_full_initialization(self) -> None:
        """ParsedIntent should accept all parameters."""
        intent = ParsedIntent(
            intent_type=IntentType.CREATE_ENCLOSURE,
            components=["raspberry-pi-5"],
            dimensions_explicit=True,
            features_mentioned=["usb", "hdmi"],
            raw_input="Create a case for Pi 5",
            clarification_needed=None,
            confidence=0.95,
        )
        assert intent.intent_type == IntentType.CREATE_ENCLOSURE
        assert "raspberry-pi-5" in intent.components
        assert intent.dimensions_explicit is True
        assert intent.confidence == 0.95


class TestIntentParserQuickClassify:
    """Tests for IntentParser quick classification."""

    @pytest.fixture
    def parser(self) -> IntentParser:
        """Create intent parser."""
        return IntentParser()

    def test_create_enclosure_with_pi5(self, parser: IntentParser) -> None:
        """Should classify Pi 5 case request as CREATE_ENCLOSURE."""
        result = parser._quick_classify("Create a case for Raspberry Pi 5")
        assert result.intent_type == IntentType.CREATE_ENCLOSURE
        assert "raspberry-pi-5" in result.components
        assert result.confidence >= 0.9

    def test_create_enclosure_with_dimensions(self, parser: IntentParser) -> None:
        """Should classify dimensioned box as CREATE_ENCLOSURE."""
        result = parser._quick_classify("Make a box 100mm x 50mm x 30mm")
        assert result.intent_type == IntentType.CREATE_ENCLOSURE
        assert result.dimensions_explicit is True

    def test_create_with_arduino(self, parser: IntentParser) -> None:
        """Should recognize Arduino components."""
        result = parser._quick_classify("Build an enclosure for Arduino Uno")
        assert result.intent_type == IntentType.CREATE_ENCLOSURE
        assert "arduino-uno" in result.components

    def test_create_with_esp32(self, parser: IntentParser) -> None:
        """Should recognize ESP32."""
        result = parser._quick_classify("Design a housing for ESP32")
        assert result.intent_type == IntentType.CREATE_ENCLOSURE
        assert "esp32-devkit" in result.components

    def test_features_extraction(self, parser: IntentParser) -> None:
        """Should extract feature mentions."""
        result = parser._quick_classify("Create a case with USB port and ventilation")
        assert "usb" in result.features_mentioned
        assert "vent" in result.features_mentioned

    def test_button_feature(self, parser: IntentParser) -> None:
        """Should recognize button mentions."""
        result = parser._quick_classify("Case with power button on top")
        assert "button" in result.features_mentioned

    def test_display_feature(self, parser: IntentParser) -> None:
        """Should recognize display mentions."""
        result = parser._quick_classify("Enclosure with LCD display")
        assert "display" in result.features_mentioned

    def test_modify_intent(self, parser: IntentParser) -> None:
        """Should classify modification requests."""
        result = parser._quick_classify("Modify the wall thickness to 3mm")
        assert result.intent_type == IntentType.MODIFY_DESIGN

    def test_query_intent(self, parser: IntentParser) -> None:
        """Should classify questions."""
        result = parser._quick_classify("What size is the Pi 5?")
        assert result.intent_type == IntentType.QUERY_INFO

    def test_unclear_intent(self, parser: IntentParser) -> None:
        """Should mark unclear requests."""
        result = parser._quick_classify("hello there")
        assert result.intent_type == IntentType.UNCLEAR
        assert result.confidence < 0.5

    def test_preserves_raw_input(self, parser: IntentParser) -> None:
        """Should preserve original input."""
        original = "Create a Pi 5 enclosure"
        result = parser._quick_classify(original)
        assert result.raw_input == original


class TestIntentParserComponentPatterns:
    """Tests for component pattern matching."""

    @pytest.fixture
    def parser(self) -> IntentParser:
        """Create intent parser."""
        return IntentParser()

    def test_pi_5_variations(self, parser: IntentParser) -> None:
        """Should match various Pi 5 phrasings."""
        variations = [
            "raspberry pi 5",
            "Raspberry Pi 5",
            "pi 5",
            "Pi 5",
        ]
        for text in variations:
            result = parser._quick_classify(f"Case for {text}")
            assert "raspberry-pi-5" in result.components, f"Failed for: {text}"

    def test_pi_4_variations(self, parser: IntentParser) -> None:
        """Should match Pi 4 variations."""
        result = parser._quick_classify("Case for Raspberry Pi 4")
        assert "raspberry-pi-4" in result.components

    def test_pi_zero_variations(self, parser: IntentParser) -> None:
        """Should match Pi Zero variations."""
        result = parser._quick_classify("Housing for Pi Zero")
        assert "raspberry-pi-zero-2w" in result.components

    def test_multiple_components(self, parser: IntentParser) -> None:
        """Should find multiple components."""
        result = parser._quick_classify("Case for Raspberry Pi 5 with LCD display")
        assert "raspberry-pi-5" in result.components
        # LCD is matched as a feature, not component in quick classify


class TestIntentParserDimensionDetection:
    """Tests for dimension pattern detection."""

    @pytest.fixture
    def parser(self) -> IntentParser:
        """Create intent parser."""
        return IntentParser()

    def test_mm_dimensions(self, parser: IntentParser) -> None:
        """Should detect mm dimensions."""
        result = parser._quick_classify("Box 100mm wide")
        assert result.dimensions_explicit is True

    def test_cm_dimensions(self, parser: IntentParser) -> None:
        """Should detect cm dimensions."""
        result = parser._quick_classify("Case 10cm x 5cm")
        assert result.dimensions_explicit is True

    def test_inch_dimensions(self, parser: IntentParser) -> None:
        """Should detect inch dimensions."""
        result = parser._quick_classify("Box 4 inches wide")
        assert result.dimensions_explicit is True

    def test_no_dimensions(self, parser: IntentParser) -> None:
        """Should detect when no dimensions given."""
        result = parser._quick_classify("Case for Raspberry Pi 5")
        assert result.dimensions_explicit is False
