"""
Organization feature flags.

Defines features that can be enabled/disabled at the organization level.
"""

from enum import StrEnum


class OrgFeature(StrEnum):
    """Features that can be toggled at the organization level."""

    # AI & Generation features
    AI_GENERATION = "ai_generation"  # AI-powered part generation
    AI_CHAT = "ai_chat"  # Conversational AI interface
    DIRECT_GENERATION = "direct_generation"  # Direct CAD generation without chat

    # Design features
    TEMPLATES = "templates"  # Access to design templates
    CUSTOM_TEMPLATES = "custom_templates"  # Create and manage custom templates
    ASSEMBLIES = "assemblies"  # Multi-part assemblies
    ADVANCED_CAD = "advanced_cad"  # Advanced CAD operations

    # Collaboration features
    DESIGN_SHARING = "design_sharing"  # Share designs with others
    TEAMS = "teams"  # Team collaboration features
    COMMENTS = "comments"  # Design comments and annotations
    VERSION_HISTORY = "version_history"  # Track design versions

    # Export features
    EXPORT_STEP = "export_step"  # Export to STEP format
    EXPORT_STL = "export_stl"  # Export to STL format
    EXPORT_DXF = "export_dxf"  # Export to DXF format
    EXPORT_DRAWINGS = "export_drawings"  # Generate technical drawings

    # Analysis features
    BOM = "bom"  # Bill of materials
    COST_ESTIMATION = "cost_estimation"  # Cost estimation

    # Storage features
    FILE_UPLOADS = "file_uploads"  # Upload reference files
    EXTERNAL_STORAGE = "external_storage"  # Integration with cloud storage


# Default enabled features for different tiers
DEFAULT_FEATURES = {
    "free": [
        OrgFeature.AI_GENERATION,
        OrgFeature.AI_CHAT,
        OrgFeature.TEMPLATES,
        OrgFeature.DESIGN_SHARING,
        OrgFeature.EXPORT_STL,
    ],
    "pro": [
        OrgFeature.AI_GENERATION,
        OrgFeature.AI_CHAT,
        OrgFeature.DIRECT_GENERATION,
        OrgFeature.TEMPLATES,
        OrgFeature.CUSTOM_TEMPLATES,
        OrgFeature.ASSEMBLIES,
        OrgFeature.DESIGN_SHARING,
        OrgFeature.TEAMS,
        OrgFeature.COMMENTS,
        OrgFeature.VERSION_HISTORY,
        OrgFeature.EXPORT_STEP,
        OrgFeature.EXPORT_STL,
        OrgFeature.EXPORT_DXF,
        OrgFeature.BOM,
        OrgFeature.FILE_UPLOADS,
    ],
    "enterprise": [
        OrgFeature.AI_GENERATION,
        OrgFeature.AI_CHAT,
        OrgFeature.DIRECT_GENERATION,
        OrgFeature.TEMPLATES,
        OrgFeature.CUSTOM_TEMPLATES,
        OrgFeature.ASSEMBLIES,
        OrgFeature.ADVANCED_CAD,
        OrgFeature.DESIGN_SHARING,
        OrgFeature.TEAMS,
        OrgFeature.COMMENTS,
        OrgFeature.VERSION_HISTORY,
        OrgFeature.EXPORT_STEP,
        OrgFeature.EXPORT_STL,
        OrgFeature.EXPORT_DXF,
        OrgFeature.EXPORT_DRAWINGS,
        OrgFeature.BOM,
        OrgFeature.COST_ESTIMATION,
        OrgFeature.FILE_UPLOADS,
        OrgFeature.EXTERNAL_STORAGE,
    ],
}


def get_default_features(tier: str = "free") -> list[str]:
    """Get default enabled features for a subscription tier."""
    features = DEFAULT_FEATURES.get(tier, DEFAULT_FEATURES["free"])
    return [f.value for f in features]


def get_all_features() -> list[str]:
    """Get list of all available features."""
    return [f.value for f in OrgFeature]
