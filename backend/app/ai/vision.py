"""
Claude Vision integration for dimension extraction.

Uses Claude's vision capabilities to extract dimensions and specifications
from mechanical drawings, datasheets, and images.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class ExtractedDimensions:
    """Extracted dimension data from an image."""

    overall_dimensions: dict[str, Any] | None = None
    mounting_holes: list[dict[str, Any]] | None = None
    cutouts: list[dict[str, Any]] | None = None
    connectors: list[dict[str, Any]] | None = None
    tolerances: dict[str, Any] | None = None
    notes: list[str] | None = None
    raw_response: str | None = None
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_dimensions": self.overall_dimensions,
            "mounting_holes": self.mounting_holes,
            "cutouts": self.cutouts,
            "connectors": self.connectors,
            "tolerances": self.tolerances,
            "notes": self.notes,
            "confidence": self.confidence,
        }


# =============================================================================
# Vision Extractor
# =============================================================================


class VisionExtractor:
    """
    Extracts dimensions and specifications from images using GPT-4 Vision.

    Features:
    - Overall dimensions (length, width, height)
    - Mounting hole positions and sizes
    - Cutout specifications
    - Connector positions
    - Tolerances and notes
    """

    SYSTEM_PROMPT = """You are an expert at reading mechanical drawings and datasheets.
Your task is to extract precise dimensional information from images.

When analyzing an image, identify and extract:
1. Overall dimensions (length, width, height/depth) with units
2. Mounting holes (position X, Y, diameter, type)
3. Cutouts and openings (type, position, dimensions)
4. Connectors and ports (type, position, dimensions)
5. Tolerances (general and specific)
6. Any important notes or specifications

Always return a valid JSON object with this structure:
{
    "overall_dimensions": {
        "length": number,
        "width": number,
        "height": number,
        "unit": "mm" | "inch"
    },
    "mounting_holes": [
        {"x": number, "y": number, "diameter": number, "type": "through" | "threaded", "note": string}
    ],
    "cutouts": [
        {"type": "rectangular" | "circular" | "slot", "x": number, "y": number, "width": number, "height": number, "note": string}
    ],
    "connectors": [
        {"type": string, "x": number, "y": number, "width": number, "height": number, "note": string}
    ],
    "tolerances": {
        "general": string,
        "specific": [{"feature": string, "tolerance": string}]
    },
    "notes": ["string"],
    "confidence": number (0-1, how confident you are in the extraction)
}

If a field cannot be determined, set it to null.
If dimensions are ambiguous, note this and provide best estimate with lower confidence.
Positions should be relative to bottom-left corner unless otherwise specified."""

    def __init__(self):
        if settings.ANTHROPIC_API_KEY:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            self.client = None
        self.model = settings.ANTHROPIC_MODEL

    async def extract_dimensions(
        self,
        image_data: bytes,
        context: str = "",
        image_type: str = "image/png",
    ) -> ExtractedDimensions:
        """
        Extract dimensions from an image.

        Args:
            image_data: Raw image bytes
            context: Optional context about what's in the image
            image_type: MIME type of the image

        Returns:
            ExtractedDimensions with parsed data
        """
        if not self.client:
            logger.warning("Anthropic API key not configured")
            return ExtractedDimensions(
                notes=["Vision extraction not available - API key not configured"],
                confidence=0.0,
            )

        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_data).decode("utf-8")

            # Build the user message
            user_content = []
            if context:
                user_content.append({
                    "type": "text",
                    "text": f"Context: {context}\n\nExtract all dimensions from this image:",
                })
            else:
                user_content.append({
                    "type": "text",
                    "text": "Extract all dimensions and specifications from this mechanical drawing or datasheet image:",
                })

            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_type};base64,{base64_image}",
                    "detail": "high",  # Use high detail for better accuracy
                },
            })

            # Call Claude Vision
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,  # Low temperature for more consistent extraction
            )

            # Parse response
            content = response.content[0].text
            return self._parse_response(content)

        except Exception as e:
            logger.exception("Vision extraction failed")
            return ExtractedDimensions(
                notes=[f"Extraction failed: {str(e)}"],
                raw_response=str(e),
                confidence=0.0,
            )

    async def extract_from_multiple_images(
        self,
        images: list[tuple[bytes, str]],
        context: str = "",
    ) -> ExtractedDimensions:
        """
        Extract and merge dimensions from multiple images.

        Args:
            images: List of (image_data, image_type) tuples
            context: Optional context

        Returns:
            Merged ExtractedDimensions
        """
        results = []
        for image_data, image_type in images:
            result = await self.extract_dimensions(image_data, context, image_type)
            if result.confidence > 0:
                results.append(result)

        if not results:
            return ExtractedDimensions(
                notes=["No valid extractions from images"],
                confidence=0.0,
            )

        return self._merge_results(results)

    def _parse_response(self, content: str) -> ExtractedDimensions:
        """Parse GPT response into ExtractedDimensions."""
        try:
            # Try to find JSON in the response
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    json_str = json_match.group()
                else:
                    return ExtractedDimensions(
                        notes=["Could not parse JSON from response"],
                        raw_response=content,
                        confidence=0.0,
                    )

            data = json.loads(json_str)

            return ExtractedDimensions(
                overall_dimensions=data.get("overall_dimensions"),
                mounting_holes=data.get("mounting_holes"),
                cutouts=data.get("cutouts"),
                connectors=data.get("connectors"),
                tolerances=data.get("tolerances"),
                notes=data.get("notes"),
                confidence=float(data.get("confidence", 0.7)),
                raw_response=content,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return ExtractedDimensions(
                notes=[f"JSON parse error: {str(e)}"],
                raw_response=content,
                confidence=0.0,
            )

    def _merge_results(self, results: list[ExtractedDimensions]) -> ExtractedDimensions:
        """Merge multiple extraction results."""
        # Use the result with highest confidence as base
        results.sort(key=lambda r: r.confidence, reverse=True)
        merged = results[0]

        # Merge data from other results
        all_notes = set()
        all_holes = []
        all_cutouts = []
        all_connectors = []

        for result in results:
            if result.notes:
                all_notes.update(result.notes)
            if result.mounting_holes:
                all_holes.extend(result.mounting_holes)
            if result.cutouts:
                all_cutouts.extend(result.cutouts)
            if result.connectors:
                all_connectors.extend(result.connectors)

        # Deduplicate and update
        merged.notes = list(all_notes) if all_notes else None
        merged.mounting_holes = self._deduplicate_features(all_holes) if all_holes else None
        merged.cutouts = self._deduplicate_features(all_cutouts) if all_cutouts else None
        merged.connectors = self._deduplicate_features(all_connectors) if all_connectors else None

        # Average confidence
        merged.confidence = sum(r.confidence for r in results) / len(results)

        return merged

    def _deduplicate_features(
        self,
        features: list[dict[str, Any]],
        tolerance: float = 1.0,
    ) -> list[dict[str, Any]]:
        """Remove duplicate features based on position."""
        if not features:
            return []

        unique = []
        for feature in features:
            is_duplicate = False
            for existing in unique:
                # Check if positions are close
                if "x" in feature and "x" in existing:
                    dx = abs(feature.get("x", 0) - existing.get("x", 0))
                    dy = abs(feature.get("y", 0) - existing.get("y", 0))
                    if dx < tolerance and dy < tolerance:
                        is_duplicate = True
                        break
            if not is_duplicate:
                unique.append(feature)

        return unique


# =============================================================================
# Singleton
# =============================================================================

vision_extractor = VisionExtractor()
