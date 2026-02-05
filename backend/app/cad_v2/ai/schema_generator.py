"""Schema generator for CAD v2.

Converts parsed intents into validated EnclosureSpec schemas.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.ai.exceptions import AIError
from app.ai.providers import get_ai_provider
from app.cad_v2.ai.intent import IntentParser, IntentType, ParsedIntent
from app.cad_v2.ai.prompts import ENCLOSURE_GENERATION
from app.cad_v2.components import get_registry
from app.cad_v2.schemas.enclosure import EnclosureSpec

logger = logging.getLogger(__name__)


class SchemaGenerationError(Exception):
    """Error during schema generation."""

    def __init__(
        self,
        message: str,
        details: list[str] | None = None,
        raw_response: str | None = None,
    ) -> None:
        self.details = details or []
        self.raw_response = raw_response
        super().__init__(message)


@dataclass
class GenerationResult:
    """Result of schema generation.

    Contains the generated schema and metadata about the generation process.
    """

    spec: EnclosureSpec | None
    """The generated enclosure specification."""

    success: bool
    """Whether generation succeeded."""

    raw_json: dict[str, Any] | None = None
    """Raw JSON before validation."""

    validation_errors: list[str] | None = None
    """Validation errors if spec is invalid."""

    warnings: list[str] | None = None
    """Non-fatal warnings about the generation."""

    clarification_needed: str | None = None
    """Question to ask user if more info needed."""


class SchemaGenerator:
    """Generates EnclosureSpec from natural language.

    Uses Claude to convert user descriptions into validated
    Pydantic schemas.

    Example:
        >>> generator = SchemaGenerator()
        >>> result = await generator.generate(
        ...     "A case for Raspberry Pi 5 with USB ports accessible"
        ... )
        >>> if result.success:
        ...     print(result.spec.exterior)
    """

    def __init__(self) -> None:
        """Initialize schema generator."""
        self._provider = None
        self._intent_parser = IntentParser()
        self._registry = get_registry()

    @property
    def provider(self) -> Any:
        """Lazy load AI provider."""
        if self._provider is None:
            self._provider = get_ai_provider()
        return self._provider

    async def generate(
        self,
        user_input: str,
        *,
        parse_intent: bool = True,
    ) -> GenerationResult:
        """Generate an EnclosureSpec from natural language.

        Args:
            user_input: Natural language description.
            parse_intent: Whether to parse intent first.

        Returns:
            GenerationResult with spec or errors.
        """
        # Step 1: Parse intent if requested
        intent: ParsedIntent | None = None
        if parse_intent:
            intent = await self._intent_parser.parse(user_input)

            if intent.intent_type == IntentType.UNCLEAR:
                return GenerationResult(
                    spec=None,
                    success=False,
                    clarification_needed=intent.clarification_needed
                    or "Could you provide more details about what you'd like to create?",
                )

            if intent.intent_type != IntentType.CREATE_ENCLOSURE:
                return GenerationResult(
                    spec=None,
                    success=False,
                    clarification_needed=f"I can help create enclosures. "
                    f"Your request seems to be about '{intent.intent_type.value}'. "
                    f"Would you like to create a new enclosure instead?",
                )

        # Step 2: Generate schema via AI
        try:
            raw_json = await self._call_ai(user_input, intent)
        except AIError as e:
            return GenerationResult(
                spec=None,
                success=False,
                validation_errors=[f"AI error: {e!s}"],
            )

        # Step 3: Validate against Pydantic schema
        try:
            spec = self._validate_and_build(raw_json)
            return GenerationResult(
                spec=spec,
                success=True,
                raw_json=raw_json,
                warnings=self._check_warnings(spec, intent),
            )
        except ValidationError as e:
            errors = [str(err) for err in e.errors()]
            return GenerationResult(
                spec=None,
                success=False,
                raw_json=raw_json,
                validation_errors=errors,
            )
        except Exception as e:
            return GenerationResult(
                spec=None,
                success=False,
                raw_json=raw_json,
                validation_errors=[f"Unexpected error: {e!s}"],
            )

    async def _call_ai(
        self,
        user_input: str,
        intent: ParsedIntent | None,
    ) -> dict[str, Any]:
        """Call Claude to generate JSON schema.

        Args:
            user_input: User's description.
            intent: Parsed intent (if available).

        Returns:
            Parsed JSON dict.
        """
        # Build enhanced prompt with component context
        enhanced_input = user_input

        if intent and intent.components:
            # Add component dimensions as context
            component_context = []
            for comp_id in intent.components:
                comp = self._registry.get(comp_id)
                if comp:
                    component_context.append(
                        f"- {comp.name}: {comp.dimensions.width_mm}x"
                        f"{comp.dimensions.depth_mm}x{comp.dimensions.height_mm}mm"
                    )

            if component_context:
                enhanced_input = (
                    f"{user_input}\n\n"
                    f"Component dimensions for reference:\n" + "\n".join(component_context)
                )

        messages = ENCLOSURE_GENERATION.format_messages(enhanced_input)

        response = await self.provider.complete(
            messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        # Clean and parse response
        response = response.strip()

        # Handle potential markdown wrapping
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first and last lines (```json and ```)
            response = "\n".join(lines[1:-1])

        try:
            return json.loads(response)  # type: ignore[no-any-return]
        except json.JSONDecodeError as e:
            raise SchemaGenerationError(
                f"Failed to parse AI response as JSON: {e}",
                raw_response=response,
            )

    def _validate_and_build(self, raw_json: dict[str, Any]) -> EnclosureSpec:
        """Validate JSON and build EnclosureSpec.

        Args:
            raw_json: Raw JSON from AI.

        Returns:
            Validated EnclosureSpec.
        """
        # The Pydantic model handles validation
        return EnclosureSpec.model_validate(raw_json)

    def _check_warnings(
        self,
        spec: EnclosureSpec,
        intent: ParsedIntent | None,
    ) -> list[str]:
        """Check for non-fatal warnings.

        Args:
            spec: Generated spec.
            intent: Original intent.

        Returns:
            List of warning messages.
        """
        warnings = []

        # Check wall thickness for FDM printing
        if spec.walls.thickness.mm < 1.5:
            warnings.append(
                f"Wall thickness {spec.walls.thickness.mm}mm may be too thin "
                f"for FDM printing (recommend >= 1.5mm)"
            )

        # Check overall size
        max_dim = max(
            spec.exterior.width_mm,
            spec.exterior.depth_mm,
            spec.exterior.height_mm,
        )
        if max_dim > 300:
            warnings.append(
                f"Maximum dimension {max_dim}mm may exceed typical 3D printer bed size (300mm)"
            )

        # Check component mentions vs actual references
        if intent and intent.components:
            # Note: We'd check components array here if it were typed
            pass

        return warnings


async def generate_enclosure(user_input: str) -> GenerationResult:
    """Convenience function to generate an enclosure.

    Args:
        user_input: Natural language description.

    Returns:
        GenerationResult with spec or errors.
    """
    generator = SchemaGenerator()
    return await generator.generate(user_input)
