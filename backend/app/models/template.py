"""
Template model for pre-built CAD templates.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Float, Integer, String, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.rating import TemplateRating, TemplateFeedback, TemplateComment


class Template(Base, TimestampMixin):
    """
    Pre-built CAD template model.
    
    Templates define parameterized CAD parts that users can customize.
    Each template has a set of parameters with constraints.
    
    Parameter schema example:
    {
        "length": {
            "type": "number",
            "min": 1,
            "max": 1000,
            "default": 50,
            "unit": "mm",
            "label": "Length",
            "description": "Total length of the part"
        },
        "style": {
            "type": "enum",
            "options": ["rounded", "chamfered", "sharp"],
            "default": "rounded",
            "label": "Corner Style"
        }
    }
    """

    __tablename__ = "templates"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Template identity
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Content
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Classification
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # mechanical, enclosures, connectors, hardware, organizational, decorative, custom
    
    subcategory: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Parameter definitions (JSONB)
    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    # Default values for parameters
    default_values: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    
    # Build123d script for generating the part
    # Note: Database column is still 'cadquery_script' for backwards compatibility
    cadquery_script: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Media
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    preview_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    
    # Tags for searching
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )

    # Access control
    min_tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="free",
        index=True,
    )  # free, pro, enterprise
    
    # Featured flag
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    
    # User-created templates
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    source_design_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Analytics
    use_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    avg_rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    
    # Community relationships
    ratings: Mapped[list["TemplateRating"]] = relationship(
        "TemplateRating",
        back_populates="template",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    feedback: Mapped[list["TemplateFeedback"]] = relationship(
        "TemplateFeedback",
        back_populates="template",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["TemplateComment"]] = relationship(
        "TemplateComment",
        back_populates="template",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Template(id={self.id}, slug={self.slug})>"

    def get_parameter_defaults(self) -> dict:
        """Extract default values from parameter definitions."""
        defaults = {}
        for name, definition in self.parameters.items():
            if "default" in definition:
                defaults[name] = definition["default"]
        return defaults

    def validate_parameters(self, values: dict) -> list[str]:
        """
        Validate parameter values against definitions.
        
        Returns list of error messages (empty if valid).
        """
        errors = []
        
        for name, definition in self.parameters.items():
            required = definition.get("required", True)
            value = values.get(name)
            
            # Check required
            if required and value is None:
                errors.append(f"Parameter '{name}' is required")
                continue
            
            if value is None:
                continue
            
            param_type = definition.get("type", "string")
            
            # Type-specific validation
            if param_type == "number":
                if not isinstance(value, (int, float)):
                    errors.append(f"Parameter '{name}' must be a number")
                    continue
                if "min" in definition and value < definition["min"]:
                    errors.append(
                        f"Parameter '{name}' must be >= {definition['min']}"
                    )
                if "max" in definition and value > definition["max"]:
                    errors.append(
                        f"Parameter '{name}' must be <= {definition['max']}"
                    )
            
            elif param_type == "enum":
                options = definition.get("options", [])
                if value not in options:
                    errors.append(
                        f"Parameter '{name}' must be one of: {', '.join(options)}"
                    )
            
            elif param_type == "boolean":
                if not isinstance(value, bool):
                    errors.append(f"Parameter '{name}' must be a boolean")
        
        return errors

    def is_accessible_by_tier(self, user_tier: str) -> bool:
        """Check if template is accessible for a given subscription tier."""
        tier_hierarchy = {"free": 0, "pro": 1, "enterprise": 2}
        required_level = tier_hierarchy.get(self.min_tier, 0)
        user_level = tier_hierarchy.get(user_tier, 0)
        return user_level >= required_level
