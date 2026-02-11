"""
Service for extracting model context from designs.

Provides functions to extract metadata, dimensions, and features
from Design objects for use in AI conversations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.design import Design


class ModelContext:
    """
    Structured model context extracted from a Design.
    
    This provides all relevant information about a model that
    the AI needs to understand what the user is asking about.
    """

    def __init__(
        self,
        design_id: UUID,
        name: str,
        description: str | None,
        dimensions: dict[str, float],
        features: list[dict[str, Any]],
        parameters: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        """
        Initialize model context.

        Args:
            design_id: UUID of the design
            name: Design name
            description: Design description
            dimensions: Overall dimensions (x, y, z, unit, etc.)
            features: List of features (holes, fillets, etc.)
            parameters: Design parameters
            metadata: Additional metadata (volume, surface area, etc.)
        """
        self.design_id = design_id
        self.name = name
        self.description = description
        self.dimensions = dimensions
        self.features = features
        self.parameters = parameters
        self.metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "design_id": str(self.design_id),
            "name": self.name,
            "description": self.description,
            "dimensions": self.dimensions,
            "features": self.features,
            "parameters": self.parameters,
            "metadata": self.metadata,
        }

    def format_for_ai(self) -> str:
        """
        Format model context as a string for AI consumption.
        
        Returns:
            Formatted string describing the model.
        """
        parts = [f"Current Model: {self.name}"]
        
        if self.description:
            parts.append(f"Description: {self.description}")
        
        # Format dimensions
        if self.dimensions:
            dim_parts = []
            unit = self.dimensions.get("unit", "mm")
            for key, value in self.dimensions.items():
                if key != "unit" and isinstance(value, (int, float)):
                    dim_parts.append(f"{key}: {value}{unit}")
            if dim_parts:
                parts.append(f"Dimensions: {', '.join(dim_parts)}")
        
        # Format features
        if self.features:
            feature_descriptions = []
            for feature in self.features[:10]:  # Limit to first 10 features
                feature_type = feature.get("type", "unknown")
                description = feature.get("description", "")
                if description:
                    feature_descriptions.append(f"- {feature_type}: {description}")
                else:
                    feature_descriptions.append(f"- {feature_type}")
            if feature_descriptions:
                parts.append("Features:\n" + "\n".join(feature_descriptions))
        
        # Format parameters
        if self.parameters:
            param_parts = []
            for key, value in self.parameters.items():
                if isinstance(value, (str, int, float, bool)):
                    param_parts.append(f"{key}: {value}")
            if param_parts:
                parts.append(f"Parameters: {', '.join(param_parts[:10])}")  # Limit to 10
        
        # Format metadata
        if self.metadata:
            meta_parts = []
            for key in ["volume", "surfaceArea", "isPrintable"]:
                if key in self.metadata:
                    value = self.metadata[key]
                    if isinstance(value, bool):
                        meta_parts.append(f"{key}: {'yes' if value else 'no'}")
                    elif isinstance(value, (int, float)):
                        meta_parts.append(f"{key}: {value}")
            if meta_parts:
                parts.append(f"Metadata: {', '.join(meta_parts)}")
        
        return "\n\n".join(parts)


def extract_model_context(design: Design) -> ModelContext:
    """
    Extract model context from a Design entity.
    
    Extracts dimensions, features, parameters, and metadata from
    the design's extra_data field and current version.

    Args:
        design: The Design entity to extract context from

    Returns:
        ModelContext containing all relevant information
    """
    extra_data = design.extra_data or {}
    
    # Extract dimensions
    dimensions = extra_data.get("dimensions", {})
    if not dimensions and "parameters" in extra_data:
        # Try to extract dimensions from parameters
        params = extra_data.get("parameters", {})
        dimensions = {
            k: v
            for k, v in params.items()
            if k in ["length", "width", "height", "x", "y", "z", "diameter", "radius", "thickness"]
        }
        if dimensions and "unit" not in dimensions:
            dimensions["unit"] = "mm"  # Default unit
    
    # Extract features (from AI prompt analysis or stored features)
    features = extra_data.get("features", [])
    
    # Extract parameters
    parameters = extra_data.get("parameters", {})
    
    # Extract metadata
    metadata = {
        k: v
        for k, v in extra_data.items()
        if k in ["volume", "surfaceArea", "isPrintable", "printEstimate", "boundingBox"]
    }
    
    return ModelContext(
        design_id=design.id,
        name=design.name,
        description=design.description,
        dimensions=dimensions,
        features=features,
        parameters=parameters,
        metadata=metadata,
    )


async def get_design_by_id(
    design_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> Design | None:
    """
    Get a design by ID, ensuring user has access.

    Args:
        design_id: UUID of the design
        user_id: UUID of the user requesting access
        db: Database session

    Returns:
        Design entity if found and accessible, None otherwise
    """
    from sqlalchemy import select

    from app.models.design import Design

    result = await db.execute(
        select(Design).where(
            Design.id == design_id,
            Design.user_id == user_id,
            Design.deleted_at.is_(None),  # Exclude soft-deleted designs
        )
    )
    return result.scalar_one_or_none()
