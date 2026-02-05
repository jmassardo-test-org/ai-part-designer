"""Intent parser for CAD v2.

Parses natural language into structured intents before schema generation.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from app.ai.exceptions import AIError
from app.ai.providers import get_ai_provider


class IntentType(StrEnum):
    """Types of user intent."""

    CREATE_ENCLOSURE = "create_enclosure"
    MODIFY_DESIGN = "modify_design"
    QUERY_INFO = "query_info"
    UNCLEAR = "unclear"


@dataclass
class ParsedIntent:
    """Result of intent parsing.

    Contains structured information extracted from user input
    before full schema generation.
    """

    intent_type: IntentType
    """The classified intent type."""

    components: list[str] = field(default_factory=list)
    """Component IDs mentioned (e.g., 'raspberry-pi-5')."""

    dimensions_explicit: bool = False
    """Whether user provided explicit dimensions."""

    features_mentioned: list[str] = field(default_factory=list)
    """Features like 'usb port', 'buttons', 'vents'."""

    raw_input: str = ""
    """Original user input."""

    clarification_needed: str | None = None
    """Question to ask user if intent is unclear."""

    confidence: float = 0.0
    """Confidence score 0-1."""


class IntentParser:
    """Parses user input into structured intents.

    Uses Claude to classify intent and extract key information
    before detailed schema generation.
    """

    def __init__(self) -> None:
        """Initialize intent parser."""
        self._provider = None

    @property
    def provider(self) -> Any:
        """Lazy load AI provider."""
        if self._provider is None:
            self._provider = get_ai_provider()
        return self._provider

    async def parse(self, user_input: str) -> ParsedIntent:
        """Parse user input into structured intent.

        Args:
            user_input: Natural language description.

        Returns:
            ParsedIntent with classified type and extracted info.
        """
        # Quick heuristic checks first
        intent = self._quick_classify(user_input)

        if intent.confidence >= 0.9:
            return intent

        # Use AI for complex cases
        try:
            return await self._ai_classify(user_input)
        except AIError:
            # Fallback to heuristic result
            return intent

    def _quick_classify(self, user_input: str) -> ParsedIntent:
        """Quick heuristic classification without AI.

        Args:
            user_input: User's text.

        Returns:
            ParsedIntent with confidence score.
        """
        text = user_input.lower()

        # Check for creation keywords
        create_keywords = [
            "create",
            "make",
            "design",
            "build",
            "generate",
            "case for",
            "enclosure for",
            "box for",
            "housing for",
        ]

        is_create = any(kw in text for kw in create_keywords)

        # Check for components
        components = []
        component_patterns = {
            "raspberry pi 5": "raspberry-pi-5",
            "pi 5": "raspberry-pi-5",
            "raspberry pi 4": "raspberry-pi-4",
            "pi 4": "raspberry-pi-4",
            "raspberry pi 3": "raspberry-pi-3b-plus",
            "raspberry pi zero": "raspberry-pi-zero-2w",
            "pi zero": "raspberry-pi-zero-2w",
            "arduino uno": "arduino-uno",
            "arduino nano": "arduino-nano",
            "esp32": "esp32-devkit",
            "lcd": "lcd-20x4",
            "oled": "oled-0.96",
        }

        for pattern, comp_id in component_patterns.items():
            if pattern in text:
                components.append(comp_id)

        # Check for features
        features = []
        feature_patterns = [
            "usb",
            "hdmi",
            "ethernet",
            "port",
            "button",
            "display",
            "screen",
            "vent",
            "cooling",
            "fan",
            "mount",
            "screw",
            "sd card",
        ]

        for pattern in feature_patterns:
            if pattern in text:
                features.append(pattern)

        # Check for explicit dimensions
        import re

        dim_pattern = r"\d+\s*(mm|cm|in|inch)"
        has_dimensions = bool(re.search(dim_pattern, text))

        # Determine intent type
        if is_create and (components or has_dimensions):
            intent_type = IntentType.CREATE_ENCLOSURE
            confidence = 0.95 if components else 0.8
        elif is_create:
            intent_type = IntentType.CREATE_ENCLOSURE
            confidence = 0.6
        elif "modify" in text or "change" in text or "adjust" in text:
            intent_type = IntentType.MODIFY_DESIGN
            confidence = 0.7
        elif "what" in text or "how" in text or "?" in text:
            intent_type = IntentType.QUERY_INFO
            confidence = 0.6
        else:
            intent_type = IntentType.UNCLEAR
            confidence = 0.3

        return ParsedIntent(
            intent_type=intent_type,
            components=components,
            dimensions_explicit=has_dimensions,
            features_mentioned=features,
            raw_input=user_input,
            confidence=confidence,
        )

    async def _ai_classify(self, user_input: str) -> ParsedIntent:
        """Use AI to classify intent.

        Args:
            user_input: User's text.

        Returns:
            ParsedIntent from AI analysis.
        """
        import json

        from app.cad_v2.ai.prompts import INTENT_CLASSIFICATION

        messages = INTENT_CLASSIFICATION.format_messages(user_input)

        response = await self.provider.complete(
            messages,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Fallback
            return self._quick_classify(user_input)

        intent_map = {
            "create_enclosure": IntentType.CREATE_ENCLOSURE,
            "modify_design": IntentType.MODIFY_DESIGN,
            "query_info": IntentType.QUERY_INFO,
            "unclear": IntentType.UNCLEAR,
        }

        intent_type = intent_map.get(
            data.get("intent", "unclear"),
            IntentType.UNCLEAR,
        )

        return ParsedIntent(
            intent_type=intent_type,
            components=data.get("components", []),
            dimensions_explicit=data.get("dimensions_explicit", False),
            features_mentioned=data.get("features_mentioned", []),
            raw_input=user_input,
            clarification_needed=data.get("clarification_needed"),
            confidence=0.9 if intent_type != IntentType.UNCLEAR else 0.5,
        )
