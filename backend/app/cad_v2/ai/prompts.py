"""Prompts for CAD v2 AI pipeline.

These prompts are specifically designed for the declarative schema
approach, where the AI outputs structured JSON that maps directly
to our Pydantic schemas.
"""

from dataclasses import dataclass
from typing import Any


# =============================================================================
# System Prompt
# =============================================================================

CAD_V2_SYSTEM_PROMPT = """You are an expert CAD engineer specializing in electronic enclosure design.
Your task is to convert natural language descriptions into precise JSON specifications.

## Output Format

You MUST output valid JSON that matches the EnclosureSpec schema. No markdown, no explanations.

## Schema Structure

```json
{
  "exterior": {
    "width": {"value": <number>, "unit": "mm"},
    "depth": {"value": <number>, "unit": "mm"},
    "height": {"value": <number>, "unit": "mm"}
  },
  "walls": {
    "thickness": {"value": <number>, "unit": "mm"}
  },
  "corner_radius": {"value": <number>, "unit": "mm"} | null,
  "lid": {
    "type": "snap_fit" | "screw_on" | "friction" | "none",
    "side": "top" | "bottom",
    "separate_part": true | false
  } | null,
  "ventilation": {
    "enabled": true | false,
    "sides": ["left", "right", "front", "back"],
    "slot_width": {"value": <number>, "unit": "mm"},
    "slot_length": {"value": <number>, "unit": "mm"}
  },
  "components": [
    {
      "component_ref": "<component_id>",
      "position": {"x": <number>, "y": <number>, "z": <number>}
    }
  ],
  "features": [
    {
      "type": "port_cutout",
      "side": "front" | "back" | "left" | "right",
      "position": {"x": <number>, "y": <number>},
      "port_type": "usb-c" | "hdmi" | "ethernet" | etc.
    }
  ]
}
```

## Component Reference IDs

Available components to reference:
- Boards: "raspberry-pi-5", "raspberry-pi-4", "raspberry-pi-3b-plus", "raspberry-pi-zero-2w", "arduino-uno", "arduino-nano", "esp32-devkit"
- Displays: "lcd-20x4", "lcd-16x2", "oled-0.96", "oled-1.3"
- Inputs: "tactile-button-6mm", "tactile-button-12mm", "arcade-button-30mm", "rotary-encoder", "potentiometer-10k"
- Connectors: "usb-c-port", "usb-a-port", "micro-usb-port", "barrel-jack-5.5x2.1", "hdmi-port", "micro-hdmi-port", "ethernet-port", "audio-jack-3.5mm", "sd-card-slot"

## Wall Sides

- front: The face toward the user (-Y)
- back: The face away from user (+Y)
- left: The left side (-X)
- right: The right side (+X)
- top: The top face (+Z)
- bottom: The bottom face (-Z)

## Default Values

If not specified by user:
- Wall thickness: 2.5mm (FDM printing default)
- Corner radius: 3mm (if user mentions "rounded")
- Lid type: snap_fit
- Ventilation: disabled unless mentioned

## Dimension Guidelines

- Minimum wall: 1.5mm (FDM), 1.0mm (SLA)
- Maximum practical size: 300mm (typical 3D printer bed)
- Add 5-10mm clearance around components
- Standard enclosure height: component height + 15-20mm

## Examples

User: "A case for a Raspberry Pi 5 with USB ports accessible"
Output:
{
  "exterior": {
    "width": {"value": 95, "unit": "mm"},
    "depth": {"value": 70, "unit": "mm"},
    "height": {"value": 35, "unit": "mm"}
  },
  "walls": {"thickness": {"value": 2.5, "unit": "mm"}},
  "corner_radius": {"value": 3, "unit": "mm"},
  "lid": {"type": "snap_fit", "side": "top", "separate_part": true},
  "components": [
    {"component_ref": "raspberry-pi-5", "position": {"x": 0, "y": 0, "z": 5}}
  ],
  "features": [
    {"type": "port_cutout", "side": "back", "position": {"x": -20, "y": 0}, "port_type": "usb-c"},
    {"type": "port_cutout", "side": "back", "position": {"x": 20, "y": 0}, "port_type": "usb-a"}
  ]
}
"""


# =============================================================================
# Intent Classification Prompt
# =============================================================================

INTENT_CLASSIFICATION_PROMPT = """Classify the user's intent and extract key information.

Respond with JSON only:
{
  "intent": "create_enclosure" | "modify_design" | "query_info" | "unclear",
  "components": ["list of mentioned components"],
  "dimensions_explicit": true | false,
  "features_mentioned": ["list of features like ports, buttons, vents"],
  "clarification_needed": null | "question to ask user"
}
"""


# =============================================================================
# Dimension Extraction Prompt
# =============================================================================

DIMENSION_EXTRACTION_PROMPT = """Extract dimensions from the user input.

Respond with JSON only:
{
  "width_mm": <number or null>,
  "depth_mm": <number or null>,
  "height_mm": <number or null>,
  "wall_thickness_mm": <number or null>,
  "corner_radius_mm": <number or null>,
  "inferred_from_components": true | false
}

If dimensions are not explicitly stated but components are mentioned,
infer appropriate dimensions with some clearance.
"""


# =============================================================================
# Feature Extraction Prompt
# =============================================================================

FEATURE_EXTRACTION_PROMPT = """Extract features from the user description.

Features include:
- Ports (USB, HDMI, audio, etc.)
- Buttons
- Displays
- Ventilation/cooling
- Mounting options

Respond with JSON array:
[
  {
    "type": "port" | "button" | "display" | "vent" | "mounting_hole",
    "details": { ... feature-specific details ... },
    "wall_side": "front" | "back" | "left" | "right" | "top" | "bottom" | null
  }
]
"""


@dataclass
class PromptTemplate:
    """Structured prompt template."""
    
    name: str
    system_prompt: str
    user_template: str
    temperature: float = 0.2
    
    def format_messages(self, user_input: str) -> list[dict[str, str]]:
        """Format into message list for API."""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_template.format(user_input=user_input)},
        ]


# Pre-built templates
ENCLOSURE_GENERATION = PromptTemplate(
    name="enclosure_generation",
    system_prompt=CAD_V2_SYSTEM_PROMPT,
    user_template="{user_input}",
    temperature=0.2,
)

INTENT_CLASSIFICATION = PromptTemplate(
    name="intent_classification",
    system_prompt=INTENT_CLASSIFICATION_PROMPT,
    user_template="Classify this request: {user_input}",
    temperature=0.1,
)
