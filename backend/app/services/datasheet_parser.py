"""
PDF Datasheet Parser Service

Extracts mechanical specifications from PDF datasheets using GPT-4 Vision.
Finds dimensions, mounting holes, connectors, and clearance zones.
"""

import asyncio
import base64
import io
import json
import re
from pathlib import Path
from typing import Any, cast

from pdf2image import convert_from_path
from PIL import Image

from app.core.config import settings
from app.schemas.component_specs import (
    ClearanceType,
    ClearanceZone,
    ComponentSpecifications,
    Connector,
    ConnectorType,
    DatasheetExtraction,
    Dimensions,
    Face,
    LengthUnit,
    MechanicalDrawing,
    MountingHole,
    Position3D,
    ThermalProperties,
    ThreadSize,
)

# =============================================================================
# Configuration
# =============================================================================

# Pages to analyze (datasheets often have dimensions on first few pages)
MAX_PAGES_TO_ANALYZE = 10

# Image settings for GPT-4V
TARGET_IMAGE_WIDTH = 1200  # pixels
IMAGE_QUALITY = 85  # JPEG quality

# Claude model for vision
VISION_MODEL = settings.ANTHROPIC_MODEL


# =============================================================================
# Prompts
# =============================================================================

DIMENSION_EXTRACTION_PROMPT = """You are an expert mechanical engineer analyzing a product datasheet page.

Extract all mechanical specifications you can find on this page. Look for:

1. **Overall Dimensions**: Length, width, height (with units - mm or inches)
2. **Mounting Holes**: Position (X, Y from a corner), diameter, thread size (M2, M2.5, M3, #4-40, etc.)
3. **Connectors/Ports**: Name (USB-C, HDMI, etc.), position, cutout dimensions
4. **Clearance Zones**: Areas needing clearance (heatsinks, components, cable bend radius)
5. **Thermal Properties**: Operating temperature range, heat dissipation

Focus on the mechanical drawing if present. Note the reference corner/edge for measurements.

Return your findings as JSON with this structure:
{
  "page_has_dimensions": true/false,
  "is_mechanical_drawing": true/false,
  "dimensions": {
    "length": number or null,
    "width": number or null,
    "height": number or null,
    "unit": "mm" or "in"
  },
  "mounting_holes": [
    {
      "x": number,
      "y": number,
      "diameter": number,
      "thread_size": "M2.5" or null,
      "from_corner": "bottom_left" | "bottom_right" | "top_left" | "top_right",
      "label": "optional label from drawing"
    }
  ],
  "connectors": [
    {
      "name": "USB-C",
      "type": "usb_c",
      "face": "left" | "right" | "front" | "back" | "top" | "bottom",
      "position_description": "description of position",
      "cutout_width": number or null,
      "cutout_height": number or null
    }
  ],
  "clearance_zones": [
    {
      "name": "CPU heatsink",
      "type": "heat_sink" | "airflow" | "component_height" | "cable_bend",
      "height": number,
      "description": "description"
    }
  ],
  "thermal": {
    "min_operating_temp": number or null,
    "max_operating_temp": number or null,
    "requires_heatsink": true/false,
    "requires_venting": true/false
  },
  "confidence": 0.0-1.0,
  "notes": "any additional observations"
}

If no dimensions are found on this page, set page_has_dimensions to false."""

COMPONENT_IDENTIFICATION_PROMPT = """Look at this product datasheet and identify:

1. The manufacturer name
2. The model number or part number
3. The product category (single board computer, display, sensor, connector, button, etc.)

Return as JSON:
{
  "manufacturer": "company name",
  "model_number": "model/part number",
  "category": "product category",
  "confidence": 0.0-1.0
}"""


# =============================================================================
# Helper Functions
# =============================================================================


def pdf_to_images(pdf_path: Path, max_pages: int = MAX_PAGES_TO_ANALYZE) -> list[Image.Image]:
    """Convert PDF pages to images for GPT-4V analysis."""
    images = convert_from_path(
        pdf_path,
        first_page=1,
        last_page=max_pages,
        dpi=150,  # Good balance of quality and size
    )
    return list(images)


def resize_image(image: Image.Image, target_width: int = TARGET_IMAGE_WIDTH) -> Image.Image:
    """Resize image while maintaining aspect ratio."""
    ratio = target_width / image.width
    new_height = int(image.height * ratio)
    return image.resize((target_width, new_height), Image.Resampling.LANCZOS)


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    # Convert to RGB if necessary
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(buffer, format="JPEG", quality=IMAGE_QUALITY)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def parse_thread_size(thread_str: str | None) -> ThreadSize | None:
    """Parse thread size string to enum."""
    if not thread_str:
        return None

    thread_str = thread_str.upper().strip()

    mapping = {
        "M2": ThreadSize.M2,
        "M2.5": ThreadSize.M2_5,
        "M3": ThreadSize.M3,
        "M4": ThreadSize.M4,
        "M5": ThreadSize.M5,
        "#4-40": ThreadSize.INCH_4_40,
        "#6-32": ThreadSize.INCH_6_32,
        "#8-32": ThreadSize.INCH_8_32,
    }

    return mapping.get(thread_str)


def parse_connector_type(type_str: str) -> ConnectorType:
    """Parse connector type string to enum."""
    type_str = type_str.lower().strip().replace("-", "_").replace(" ", "_")

    mapping = {
        "usb_a": ConnectorType.USB_A,
        "usb_b": ConnectorType.USB_B,
        "usb_c": ConnectorType.USB_C,
        "usb_micro": ConnectorType.USB_MICRO,
        "usb_mini": ConnectorType.USB_MINI,
        "hdmi": ConnectorType.HDMI,
        "hdmi_mini": ConnectorType.HDMI_MINI,
        "hdmi_micro": ConnectorType.HDMI_MICRO,
        "displayport": ConnectorType.DISPLAYPORT,
        "ethernet": ConnectorType.ETHERNET,
        "rj45": ConnectorType.ETHERNET,
        "power_barrel": ConnectorType.POWER_BARREL,
        "barrel_jack": ConnectorType.POWER_BARREL,
        "sd_card": ConnectorType.SD_CARD,
        "sd": ConnectorType.SD_CARD,
        "microsd": ConnectorType.MICROSD,
        "gpio": ConnectorType.GPIO_HEADER,
        "gpio_header": ConnectorType.GPIO_HEADER,
        "header": ConnectorType.GPIO_HEADER,
        "audio": ConnectorType.AUDIO_35MM,
        "audio_35mm": ConnectorType.AUDIO_35MM,
        "3.5mm": ConnectorType.AUDIO_35MM,
    }

    return mapping.get(type_str, ConnectorType.OTHER)


def parse_face(face_str: str) -> Face:
    """Parse face string to enum."""
    face_str = face_str.lower().strip()

    mapping = {
        "top": Face.TOP,
        "bottom": Face.BOTTOM,
        "front": Face.FRONT,
        "back": Face.BACK,
        "rear": Face.BACK,
        "left": Face.LEFT,
        "right": Face.RIGHT,
    }

    return mapping.get(face_str, Face.FRONT)


def parse_clearance_type(type_str: str) -> ClearanceType:
    """Parse clearance type string to enum."""
    type_str = type_str.lower().strip().replace("-", "_").replace(" ", "_")

    mapping = {
        "heat_sink": ClearanceType.HEAT_SINK,
        "heatsink": ClearanceType.HEAT_SINK,
        "airflow": ClearanceType.AIRFLOW,
        "cable_bend": ClearanceType.CABLE_BEND,
        "cable": ClearanceType.CABLE_BEND,
        "component_height": ClearanceType.COMPONENT_HEIGHT,
        "component": ClearanceType.COMPONENT_HEIGHT,
        "user_access": ClearanceType.USER_ACCESS,
        "access": ClearanceType.USER_ACCESS,
        "led": ClearanceType.LED_VISIBILITY,
        "led_visibility": ClearanceType.LED_VISIBILITY,
        "antenna": ClearanceType.ANTENNA,
    }

    return mapping.get(type_str, ClearanceType.OTHER)


# =============================================================================
# Datasheet Parser Service
# =============================================================================


class DatasheetParserService:
    """Service to extract mechanical specifications from PDF datasheets."""

    def __init__(self) -> None:
        if settings.ANTHROPIC_API_KEY:
            from anthropic import AsyncAnthropic

            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            self.client = None

    async def parse_datasheet(
        self,
        pdf_path: Path,
        max_pages: int = MAX_PAGES_TO_ANALYZE,
    ) -> DatasheetExtraction:
        """
        Parse a PDF datasheet and extract mechanical specifications.

        Steps:
        1. Convert PDF pages to images
        2. Send each page to GPT-4V for analysis
        3. Merge results from all pages
        4. Build ComponentSpecifications
        """
        # Convert PDF to images
        images = pdf_to_images(pdf_path, max_pages)
        page_count = len(images)

        # Analyze first page for component identification
        component_info = await self._identify_component(images[0])

        # Analyze all pages for dimensions
        page_results = await asyncio.gather(
            *[self._analyze_page(image, page_num + 1) for page_num, image in enumerate(images)]
        )

        # Merge results
        specs = self._merge_page_results(page_results)

        # Find pages with dimensions
        pages_with_dims = [
            i + 1 for i, result in enumerate(page_results) if result.get("page_has_dimensions")
        ]

        # Find mechanical drawings
        mechanical_drawings = [
            MechanicalDrawing(
                page_number=i + 1,
                view_type="mechanical" if result.get("is_mechanical_drawing") else "other",
            )
            for i, result in enumerate(page_results)
            if result.get("is_mechanical_drawing")
        ]

        # Calculate overall confidence
        confidences = [r.get("confidence", 0) for r in page_results if r.get("page_has_dimensions")]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return DatasheetExtraction(
            page_count=page_count,
            manufacturer=component_info.get("manufacturer"),
            model_number=component_info.get("model_number"),
            specifications=specs,
            mechanical_drawings=mechanical_drawings,
            pages_processed=page_count,
            pages_with_dimensions=pages_with_dims,
            extraction_confidence=overall_confidence,
        )

    async def _identify_component(self, image: Image.Image) -> dict[str, Any]:
        """Identify component manufacturer and model from first page."""
        resized = resize_image(image)
        image_b64 = image_to_base64(resized)

        try:
            response = await self.client.messages.create(
                model=VISION_MODEL,
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": COMPONENT_IDENTIFICATION_PROMPT},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64,
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
            )

            content = response.content[0].text

            # Parse JSON from response
            json_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return cast("dict[str, Any]", result)

        except Exception as e:
            print(f"Error identifying component: {e}")

        return {}

    async def _analyze_page(self, image: Image.Image, page_num: int) -> dict[str, Any]:
        """Analyze a single page for mechanical specifications."""
        resized = resize_image(image)
        image_b64 = image_to_base64(resized)

        try:
            response = await self.client.messages.create(
                model=VISION_MODEL,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": DIMENSION_EXTRACTION_PROMPT},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64,
                                },
                            },
                        ],
                    }
                ],
                temperature=0.1,
            )

            content = response.content[0].text

            # Parse JSON from response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result["page_number"] = page_num
                return cast("dict[str, Any]", result)

        except Exception as e:
            print(f"Error analyzing page {page_num}: {e}")

        return {"page_has_dimensions": False, "page_number": page_num}

    def _merge_page_results(self, page_results: list[dict[Any, Any]]) -> ComponentSpecifications:
        """Merge extraction results from multiple pages."""
        # Find best dimensions (highest confidence)
        dimensions = None
        best_dim_confidence = 0

        all_mounting_holes = []
        all_connectors = []
        all_clearance_zones = []
        thermal = None

        for result in page_results:
            confidence = result.get("confidence", 0)

            # Get dimensions from most confident source
            if result.get("dimensions") and confidence > best_dim_confidence:
                dim_data = result["dimensions"]
                if dim_data.get("length") and dim_data.get("width"):
                    dimensions = Dimensions(
                        length=dim_data["length"],
                        width=dim_data["width"],
                        height=dim_data.get("height") or 0,
                        unit=LengthUnit(dim_data.get("unit", "mm")),
                    )
                    best_dim_confidence = confidence

            # Collect mounting holes
            for hole in result.get("mounting_holes", []):
                all_mounting_holes.append(
                    MountingHole(
                        x=hole["x"],
                        y=hole["y"],
                        diameter=hole["diameter"],
                        thread_size=parse_thread_size(hole.get("thread_size")),
                        is_threaded=bool(hole.get("thread_size")),
                        label=hole.get("label"),
                        from_corner=hole.get("from_corner"),
                        confidence=confidence,
                    )
                )

            # Collect connectors
            for conn in result.get("connectors", []):
                if conn.get("name"):
                    all_connectors.append(
                        Connector(
                            name=conn["name"],
                            type=parse_connector_type(conn.get("type", "other")),
                            position=Position3D(x=0, y=0, z=0),  # Will be refined
                            face=parse_face(conn.get("face", "front")),
                            cutout_width=conn.get("cutout_width") or 15.0,
                            cutout_height=conn.get("cutout_height") or 10.0,
                            confidence=confidence,
                        )
                    )

            # Collect clearance zones
            for zone in result.get("clearance_zones", []):
                if zone.get("name"):
                    from app.schemas.component_specs import BoundingBox

                    all_clearance_zones.append(
                        ClearanceZone(
                            name=zone["name"],
                            type=parse_clearance_type(zone.get("type", "other")),
                            description=zone.get("description"),
                            bounds=BoundingBox(
                                min_x=0,
                                min_y=0,
                                min_z=0,
                                max_x=0,
                                max_y=0,
                                max_z=zone.get("height", 10),
                            ),
                            requires_venting=zone.get("type") in ("heat_sink", "airflow"),
                            confidence=confidence,
                        )
                    )

            # Get thermal properties
            if result.get("thermal") and not thermal:
                t = result["thermal"]
                thermal = ThermalProperties(
                    min_operating_temp=t.get("min_operating_temp"),
                    max_operating_temp=t.get("max_operating_temp"),
                    requires_heatsink=t.get("requires_heatsink", False),
                    requires_venting=t.get("requires_venting", False),
                )

        # Create default dimensions if none found
        if not dimensions:
            dimensions = Dimensions(length=0, width=0, height=0)

        # Calculate overall confidence
        confidences = [r.get("confidence", 0) for r in page_results if r.get("page_has_dimensions")]
        overall_confidence = max(confidences) if confidences else 0.0

        return ComponentSpecifications(
            dimensions=dimensions,
            mounting_holes=all_mounting_holes,
            connectors=all_connectors,
            clearance_zones=all_clearance_zones,
            thermal=thermal,
            extraction_method="datasheet",
            overall_confidence=overall_confidence,
        )

    async def extract_mechanical_drawing(
        self,
        pdf_path: Path,
    ) -> MechanicalDrawing | None:
        """Find and extract the mechanical drawing page."""
        images = pdf_to_images(pdf_path, MAX_PAGES_TO_ANALYZE)

        for i, image in enumerate(images):
            result = await self._analyze_page(image, i + 1)
            if result.get("is_mechanical_drawing"):
                # Save the drawing image
                resized = resize_image(image, 1600)
                image_b64 = image_to_base64(resized)

                return MechanicalDrawing(
                    page_number=i + 1,
                    image_data=image_b64,
                    view_type="mechanical",
                )

        return None


# =============================================================================
# Singleton Instance
# =============================================================================

datasheet_parser: DatasheetParserService = DatasheetParserService()
