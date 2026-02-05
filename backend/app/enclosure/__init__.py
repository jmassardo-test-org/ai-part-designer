"""
Enclosure Generation Module

AI-powered enclosure generation that creates custom enclosures
around reference components with proper mounting and cutouts.
"""

from app.enclosure.cutouts import CutoutGenerator
from app.enclosure.prompts import (
    ENCLOSURE_SYSTEM_PROMPT,
    EnclosurePromptBuilder,
    build_enclosure_prompt,
)
from app.enclosure.schemas import (
    Cutout,
    CutoutProfile,
    EnclosureOptions,
    EnclosureRequest,
    EnclosureResult,
    EnclosureStyle,
    EnclosureStyleType,
    LidClosureType,
    Standoff,
    StandoffOptions,
    VentilationPattern,
)
from app.enclosure.service import EnclosureGenerationService
from app.enclosure.standoffs import StandoffGenerator
from app.enclosure.templates import ENCLOSURE_STYLE_TEMPLATES

__all__ = [
    # Templates
    "ENCLOSURE_STYLE_TEMPLATES",
    # Prompts
    "ENCLOSURE_SYSTEM_PROMPT",
    "Cutout",
    "CutoutGenerator",
    "CutoutProfile",
    # Services
    "EnclosureGenerationService",
    "EnclosureOptions",
    "EnclosurePromptBuilder",
    "EnclosureRequest",
    "EnclosureResult",
    # Schemas
    "EnclosureStyle",
    "EnclosureStyleType",
    "LidClosureType",
    "Standoff",
    "StandoffGenerator",
    "StandoffOptions",
    "VentilationPattern",
    "build_enclosure_prompt",
]
