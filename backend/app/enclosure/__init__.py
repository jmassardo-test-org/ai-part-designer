"""
Enclosure Generation Module

AI-powered enclosure generation that creates custom enclosures
around reference components with proper mounting and cutouts.
"""

from app.enclosure.prompts import (
    ENCLOSURE_SYSTEM_PROMPT,
    build_enclosure_prompt,
    EnclosurePromptBuilder,
)
from app.enclosure.schemas import (
    EnclosureStyle,
    EnclosureStyleType,
    EnclosureOptions,
    Standoff,
    StandoffOptions,
    Cutout,
    CutoutProfile,
    EnclosureRequest,
    EnclosureResult,
    LidClosureType,
    VentilationPattern,
)
from app.enclosure.service import EnclosureGenerationService
from app.enclosure.standoffs import StandoffGenerator
from app.enclosure.cutouts import CutoutGenerator
from app.enclosure.templates import ENCLOSURE_STYLE_TEMPLATES

__all__ = [
    # Prompts
    "ENCLOSURE_SYSTEM_PROMPT",
    "build_enclosure_prompt",
    "EnclosurePromptBuilder",
    # Schemas
    "EnclosureStyle",
    "EnclosureStyleType",
    "EnclosureOptions",
    "Standoff",
    "StandoffOptions",
    "Cutout",
    "CutoutProfile",
    "EnclosureRequest",
    "EnclosureResult",
    "LidClosureType",
    "VentilationPattern",
    # Services
    "EnclosureGenerationService",
    "StandoffGenerator",
    "CutoutGenerator",
    # Templates
    "ENCLOSURE_STYLE_TEMPLATES",
]
