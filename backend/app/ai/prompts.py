"""
Prompt templates for AI-powered CAD parameter extraction.

Provides structured prompts optimized for extracting dimensions,
features, and specifications from natural language descriptions.

Example:
    >>> from app.ai.prompts import DIMENSION_EXTRACTION_PROMPT
    >>> prompt = DIMENSION_EXTRACTION_PROMPT.format(user_input="Create a box 100x50x30mm")
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class PromptCategory(StrEnum):
    """Categories of prompt templates."""

    DIMENSION_EXTRACTION = "dimension_extraction"
    FEATURE_IDENTIFICATION = "feature_identification"
    TEMPLATE_SELECTION = "template_selection"
    MODIFICATION = "modification"
    VALIDATION = "validation"


@dataclass
class PromptTemplate:
    """
    Structured prompt template with metadata.

    Attributes:
        name: Unique template identifier
        category: Type of extraction/task
        system_prompt: System message for AI context
        user_template: Template for user message with {placeholders}
        output_schema: Expected JSON schema for response
        examples: Few-shot examples for better accuracy
    """

    name: str
    category: PromptCategory
    system_prompt: str
    user_template: str
    output_schema: dict[str, Any]
    examples: list[dict[str, str]] | None = None
    temperature: float = 0.2  # Low temp for more deterministic output

    def format_messages(self, **kwargs: Any) -> list[dict[str, str]]:
        """
        Format prompt into message list for API call.

        Args:
            **kwargs: Values to substitute in user_template

        Returns:
            List of message dicts for Claude API
        """
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add few-shot examples if available
        if self.examples:
            for example in self.examples:
                messages.append({"role": "user", "content": example["input"]})
                messages.append({"role": "assistant", "content": example["output"]})

        # Add actual user input
        user_content = self.user_template.format(**kwargs)
        messages.append({"role": "user", "content": user_content})

        return messages


# =============================================================================
# System Prompts
# =============================================================================

CAD_SYSTEM_PROMPT = """You are an expert CAD engineer assistant. Your role is to extract precise dimensions, shapes, and features from natural language descriptions of mechanical parts.

Key responsibilities:
1. Identify the primary shape type (box, cylinder, sphere, cone, enclosure, etc.)
2. Extract all dimensions with correct units
3. Identify features like holes, fillets, chamfers
4. Convert all measurements to millimeters
5. Validate that dimensions are realistic for manufacturing
6. Recognize multi-part assemblies (enclosures, box with lid, etc.)

Shape type selection:
- Use "enclosure" when user requests:
  - A box with a lid
  - A 2-part enclosure / two-part case
  - A housing with removable cover
  - Container with top/bottom pieces
- Use "box" for simple solid rectangular shapes without lids

Dimension naming conventions:
- For boxes and enclosures: ALWAYS use 'length', 'width', 'height' (not 'depth', 'tall', etc.)
  - If user says "tall" or "high", map to 'height'
  - If user says "deep" or "depth", map to 'length' or 'width' based on context
  - If dimensions are given as AxBxC, map to length x width x height
- For cylinders: use 'radius' or 'diameter' and 'height'
- For spheres: use 'radius' or 'diameter'

Assembly configuration (for enclosures):
- Extract wall_thickness if mentioned (default: 2.5mm)
- Extract screw_size if mentioned (default: "M3")
- Note if gasket/seal is requested
- Note if flanges/mounting tabs are requested

Always respond with valid JSON matching the requested schema. If information is ambiguous, make reasonable assumptions for typical manufacturing scenarios and note them.

Unit conversions:
- 1 inch = 25.4 mm
- 1 cm = 10 mm
- 1 m = 1000 mm
- If no unit specified, assume millimeters"""


# =============================================================================
# Dimension Extraction
# =============================================================================

DIMENSION_EXTRACTION_SCHEMA = {
    "type": "object",
    "required": ["shape", "dimensions", "units", "confidence"],
    "properties": {
        "shape": {
            "type": "string",
            "enum": ["box", "cylinder", "sphere", "cone", "torus", "wedge", "enclosure", "custom"],
            "description": "Primary shape type. Use 'enclosure' for box-with-lid, 2-part cases, housings.",
        },
        "dimensions": {
            "type": "object",
            "description": "Shape-specific dimensions in mm",
            "properties": {
                "length": {"type": "number"},
                "width": {"type": "number"},
                "height": {"type": "number"},
                "radius": {"type": "number"},
                "diameter": {"type": "number"},
                "inner_radius": {"type": "number"},
                "outer_radius": {"type": "number"},
                "wall_thickness": {"type": "number"},
            },
        },
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "hole",
                            "fillet",
                            "chamfer",
                            "slot",
                            "pocket",
                            "boss",
                            "gasket",
                            "flange",
                        ],
                    },
                    "parameters": {"type": "object"},
                },
            },
        },
        "units": {
            "type": "string",
            "enum": ["mm", "cm", "m", "inches"],
            "description": "Original units from description",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score for extraction accuracy",
        },
        "assumptions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of assumptions made during extraction",
        },
        "assembly_config": {
            "type": "object",
            "description": "Configuration for multi-part assemblies",
            "properties": {
                "wall_thickness": {"type": "number", "description": "Wall thickness in mm"},
                "screw_size": {
                    "type": "string",
                    "description": "Metric screw size (M2, M3, M4, etc.)",
                },
                "has_gasket": {
                    "type": "boolean",
                    "description": "Whether to include gasket groove",
                },
                "has_flanges": {
                    "type": "boolean",
                    "description": "Whether to include mounting flanges",
                },
                "lid_style": {"type": "string", "enum": ["top", "clamshell", "slide"]},
            },
        },
    },
}

DIMENSION_EXTRACTION_TEMPLATE = """Extract CAD parameters from this description:

"{user_input}"

Respond with JSON containing:
- shape: The primary shape type (use "enclosure" for box-with-lid designs)
- dimensions: All dimensions converted to millimeters
- features: Any additional features (holes, fillets, gasket, flange, etc.)
- units: The original units specified (or "mm" if none)
- confidence: Your confidence in the extraction (0-1)
- assumptions: Any assumptions you made
- assembly_config: For enclosures, include wall_thickness, screw_size, has_gasket, has_flanges"""

DIMENSION_EXTRACTION_EXAMPLES = [
    {
        "input": 'Extract CAD parameters from this description:\n\n"Create a box 100mm long, 50mm wide, and 30mm tall"',
        "output": '{"shape": "box", "dimensions": {"length": 100, "width": 50, "height": 30}, "features": [], "units": "mm", "confidence": 0.95, "assumptions": []}',
    },
    {
        "input": 'Extract CAD parameters from this description:\n\n"I need a cylinder that\'s 2 inches in diameter and 4 inches tall with a 0.5 inch hole through the center"',
        "output": '{"shape": "cylinder", "dimensions": {"diameter": 50.8, "height": 101.6, "radius": 25.4}, "features": [{"type": "hole", "parameters": {"diameter": 12.7, "through": true}}], "units": "inches", "confidence": 0.9, "assumptions": ["Hole is centered on cylinder axis", "Hole goes through entire height"]}',
    },
    {
        "input": 'Extract CAD parameters from this description:\n\n"Make a sphere with radius 25"',
        "output": '{"shape": "sphere", "dimensions": {"radius": 25, "diameter": 50}, "features": [], "units": "mm", "confidence": 0.85, "assumptions": ["No unit specified, assuming millimeters"]}',
    },
    {
        "input": 'Extract CAD parameters from this description:\n\n"Create a 2 part enclosure 150mm tall by 100mm wide by 50mm deep with a lid, gasket, and flanges for M4 screws"',
        "output": '{"shape": "enclosure", "dimensions": {"length": 50, "width": 100, "height": 150}, "features": [{"type": "gasket", "parameters": {}}, {"type": "flange", "parameters": {"screw_size": "M4"}}], "units": "mm", "confidence": 0.9, "assumptions": ["Interpreted deep as length", "Standard 2.5mm wall thickness assumed"], "assembly_config": {"wall_thickness": 2.5, "screw_size": "M4", "has_gasket": true, "has_flanges": true, "lid_style": "top"}}',
    },
]

DIMENSION_EXTRACTION_PROMPT = PromptTemplate(
    name="dimension_extraction",
    category=PromptCategory.DIMENSION_EXTRACTION,
    system_prompt=CAD_SYSTEM_PROMPT,
    user_template=DIMENSION_EXTRACTION_TEMPLATE,
    output_schema=DIMENSION_EXTRACTION_SCHEMA,
    examples=DIMENSION_EXTRACTION_EXAMPLES,
    temperature=0.2,
)


# =============================================================================
# Template Selection
# =============================================================================

TEMPLATE_SELECTION_SCHEMA = {
    "type": "object",
    "required": ["template_id", "parameters", "confidence"],
    "properties": {
        "template_id": {"type": "string", "description": "ID of the matching template"},
        "parameters": {"type": "object", "description": "Parameters to apply to the template"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string", "description": "Why this template was selected"},
    },
}

TEMPLATE_SELECTION_TEMPLATE = """Given the user's description and available templates, select the best matching template.

User description: "{user_input}"

Available templates:
{templates}

Respond with JSON containing:
- template_id: The ID of the best matching template
- parameters: Values for template parameters extracted from the description
- confidence: Your confidence in this match (0-1)
- reasoning: Brief explanation of why this template fits"""

TEMPLATE_SELECTION_PROMPT = PromptTemplate(
    name="template_selection",
    category=PromptCategory.TEMPLATE_SELECTION,
    system_prompt=CAD_SYSTEM_PROMPT,
    user_template=TEMPLATE_SELECTION_TEMPLATE,
    output_schema=TEMPLATE_SELECTION_SCHEMA,
    temperature=0.3,
)


# =============================================================================
# Modification Prompts
# =============================================================================

MODIFICATION_SCHEMA = {
    "type": "object",
    "required": ["modifications", "confidence"],
    "properties": {
        "modifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": [
                            "resize",
                            "add_feature",
                            "remove_feature",
                            "move",
                            "rotate",
                            "fillet",
                            "chamfer",
                        ],
                    },
                    "target": {"type": "string"},
                    "parameters": {"type": "object"},
                },
            },
        },
        "confidence": {"type": "number"},
    },
}

MODIFICATION_TEMPLATE = """The user wants to modify an existing part. Extract the modifications.

Current part: {current_part}
User request: "{user_input}"

Respond with JSON containing:
- modifications: List of modifications to apply
- confidence: Your confidence in understanding the request"""

MODIFICATION_PROMPT = PromptTemplate(
    name="modification",
    category=PromptCategory.MODIFICATION,
    system_prompt=CAD_SYSTEM_PROMPT,
    user_template=MODIFICATION_TEMPLATE,
    output_schema=MODIFICATION_SCHEMA,
    temperature=0.3,
)


# =============================================================================
# Validation Prompts
# =============================================================================

VALIDATION_SCHEMA = {
    "type": "object",
    "required": ["is_valid", "issues"],
    "properties": {
        "is_valid": {"type": "boolean"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                    "message": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
            },
        },
        "manufacturing_notes": {"type": "array", "items": {"type": "string"}},
    },
}

VALIDATION_TEMPLATE = """Validate these CAD parameters for manufacturability:

Parameters: {parameters}

Check for:
1. Realistic dimensions (not too small or too large)
2. Wall thickness if applicable
3. Feature sizes (holes not too small, fillets not too large)
4. General manufacturability

Respond with JSON containing:
- is_valid: Whether the parameters are valid
- issues: List of any problems found
- manufacturing_notes: Helpful notes for manufacturing"""

VALIDATION_PROMPT = PromptTemplate(
    name="validation",
    category=PromptCategory.VALIDATION,
    system_prompt=CAD_SYSTEM_PROMPT,
    user_template=VALIDATION_TEMPLATE,
    output_schema=VALIDATION_SCHEMA,
    temperature=0.2,
)


# =============================================================================
# Prompt Registry
# =============================================================================

PROMPTS = {
    "dimension_extraction": DIMENSION_EXTRACTION_PROMPT,
    "template_selection": TEMPLATE_SELECTION_PROMPT,
    "modification": MODIFICATION_PROMPT,
    "validation": VALIDATION_PROMPT,
}


def get_prompt(name: str) -> PromptTemplate:
    """
    Get a prompt template by name.

    Args:
        name: Template name

    Returns:
        PromptTemplate instance

    Raises:
        KeyError: If template not found
    """
    if name not in PROMPTS:
        raise KeyError(f"Unknown prompt template: {name}. Available: {list(PROMPTS.keys())}")
    return PROMPTS[name]
