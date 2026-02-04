"""
Seed data for CAD v2 components.

This script syncs the in-memory component registry with the database,
enabling admin management of components through the API.

Usage:
    python -m app.seeds.components_v2

Or via Makefile:
    make db-seed
"""

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.reference_component import ReferenceComponent
from app.cad_v2.components import get_registry
from app.cad_v2.schemas.components import ComponentDefinition

logger = logging.getLogger(__name__)


def component_to_dict(comp: ComponentDefinition) -> dict[str, Any]:
    """Convert a ComponentDefinition to a database-friendly dict.
    
    Args:
        comp: The component definition from the registry.
        
    Returns:
        Dictionary with fields for ReferenceComponent model.
    """
    return {
        "name": comp.name,
        "category": comp.category.value,
        "description": comp.notes,  # ComponentDefinition uses 'notes' for description
        "dimensions": {
            "width": comp.dimensions.width.value,
            "depth": comp.dimensions.depth.value,
            "height": comp.dimensions.height.value,
            "unit": comp.dimensions.width.unit.value if hasattr(comp.dimensions.width, "unit") else "mm",
        },
        "mounting_holes": [
            {
                "x": h.x,
                "y": h.y,
                "diameter": h.diameter.value if hasattr(h.diameter, "value") else h.diameter,
                "type": h.type,
            }
            for h in (comp.mounting_holes or [])
        ],
        "connectors": [
            {
                "name": p.name,
                "side": p.side.value if hasattr(p.side, "value") else str(p.side),
                "position": {
                    "x": p.position.x,
                    "y": p.position.y,
                    "z": p.position.z,
                } if p.position else None,
                "cutout_width": p.width.value if p.width and hasattr(p.width, "value") else None,
                "cutout_height": p.height.value if p.height and hasattr(p.height, "value") else None,
            }
            for p in (comp.ports or [])
        ],
        "tags": list(comp.aliases) if comp.aliases else [],
        "source_type": "library",
    }


async def seed_components_v2(db: AsyncSession) -> tuple[int, int]:
    """Sync CAD v2 component registry with the database.
    
    Creates or updates ReferenceComponent records for each
    component in the registry.
    
    Args:
        db: Async database session.
        
    Returns:
        Tuple of (created_count, updated_count).
    """
    registry = get_registry()
    components = registry.list_all()
    
    created = 0
    updated = 0
    
    for comp in components:
        comp_data = component_to_dict(comp)
        
        # Check if component already exists by name and category (using as slug)
        existing = await db.execute(
            select(ReferenceComponent).where(
                ReferenceComponent.name == comp.name,
                ReferenceComponent.source_type == "library",
            )
        )
        existing_comp = existing.scalar_one_or_none()
        
        if existing_comp:
            # Update existing component
            existing_comp.category = comp_data["category"]
            existing_comp.description = comp_data["description"]
            existing_comp.dimensions = comp_data["dimensions"]
            existing_comp.mounting_holes = comp_data["mounting_holes"]
            existing_comp.connectors = comp_data["connectors"]
            existing_comp.tags = comp_data["tags"]
            existing_comp.notes = comp.id  # Store the registry ID in notes for lookup
            updated += 1
            logger.debug(f"Updated component: {comp.id}")
        else:
            # Create new component
            new_comp = ReferenceComponent(
                id=uuid4(),
                name=comp_data["name"],
                category=comp_data["category"],
                description=comp_data["description"],
                dimensions=comp_data["dimensions"],
                mounting_holes=comp_data["mounting_holes"],
                connectors=comp_data["connectors"],
                tags=comp_data["tags"],
                notes=comp.id,  # Store the registry ID in notes for lookup
                source_type="library",
                extraction_status="complete",
                is_verified=True,
                user_id=None,  # Library components have no owner
            )
            db.add(new_comp)
            created += 1
            logger.debug(f"Created component: {comp.id}")
    
    await db.commit()
    return created, updated


async def main() -> None:
    """Run component seeding."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Seeding CAD v2 components from registry...")
    
    async with async_session_maker() as db:
        created, updated = await seed_components_v2(db)
        logger.info(f"Component seeding complete: {created} created, {updated} updated")
        
        # Log summary
        registry = get_registry()
        logger.info(f"Total components in registry: {registry.count}")


if __name__ == "__main__":
    asyncio.run(main())
