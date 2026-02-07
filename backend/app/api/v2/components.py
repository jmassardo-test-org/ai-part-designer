"""
CAD v2 components endpoint.

Browse and search the component library.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.cad_v2.components import get_registry
from app.cad_v2.components.registry import ComponentNotFoundError
from app.cad_v2.schemas.components import ComponentCategory

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class ComponentSummary(BaseModel):
    """Summary of a component."""

    id: str = Field(description="Unique component ID")
    name: str = Field(description="Display name")
    category: str = Field(description="Component category")
    dimensions_mm: tuple[float, float, float] = Field(description="Dimensions (W, D, H) in mm")


class ComponentDetail(BaseModel):
    """Detailed component information."""

    id: str
    name: str
    category: str
    dimensions_mm: tuple[float, float, float]
    aliases: list[str] = Field(default_factory=list)
    mounting_holes: list[dict[str, Any]] = Field(default_factory=list)
    ports: list[dict[str, Any]] = Field(default_factory=list)
    description: str | None = None


class SearchResult(BaseModel):
    """Search result."""

    results: list[ComponentSummary]
    total: int
    query: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/",
    response_model=list[ComponentSummary],
    summary="List all components",
)
async def list_components(
    category: str | None = Query(default=None, description="Filter by category"),
) -> list[ComponentSummary]:
    """List all available components.

    Optionally filter by category (board, display, input, connector).
    """
    registry = get_registry()

    if category:
        try:
            cat_enum = ComponentCategory(category)
            components = registry.list_category(cat_enum)
        except ValueError:
            components = []  # Invalid category returns empty list
    else:
        components = registry.list_all()

    return [
        ComponentSummary(
            id=c.id,
            name=c.name,
            category=c.category.value,
            dimensions_mm=c.dimensions.to_tuple_mm(),
        )
        for c in components
    ]


@router.get(
    "/categories",
    summary="List component categories",
)
async def list_categories() -> dict[str, Any]:
    """List available component categories with their component IDs."""
    registry = get_registry()

    categories: dict[str, list[str]] = {}
    for comp in registry.list_all():
        cat_name = comp.category.value  # Get string value from enum
        if cat_name not in categories:
            categories[cat_name] = []
        categories[cat_name].append(comp.id)

    return {"categories": categories}


@router.get(
    "/search",
    response_model=SearchResult,
    summary="Search components",
)
async def search_components(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
) -> SearchResult:
    """Search for components by name or alias.

    Uses fuzzy matching to find similar component names.
    """
    registry = get_registry()

    matches = registry.search(q, max_results=limit)

    return SearchResult(
        results=[
            ComponentSummary(
                id=m.component.id,
                name=m.component.name,
                category=m.component.category.value,
                dimensions_mm=m.component.dimensions.to_tuple_mm(),
            )
            for m in matches
        ],
        total=len(matches),
        query=q,
    )


@router.get(
    "/{component_id}",
    response_model=ComponentDetail,
    summary="Get component details",
)
async def get_component(component_id: str) -> ComponentDetail:
    """Get detailed information about a specific component.

    Includes dimensions, mounting holes, ports, and aliases.
    """
    registry = get_registry()

    try:
        comp = registry.lookup(component_id)
    except ComponentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return ComponentDetail(
        id=comp.id,
        name=comp.name,
        category=comp.category.value,
        dimensions_mm=comp.dimensions.to_tuple_mm(),
        aliases=list(comp.aliases),
        mounting_holes=[
            {"position": (h.x, h.y), "diameter_mm": h.diameter.mm} for h in comp.mounting_holes
        ],
        ports=[{"name": p.name, "side": p.side.value} for p in comp.ports],
        description=comp.notes,
    )


@router.get(
    "/{component_id}/enclosure-suggestion",
    summary="Get enclosure suggestion for component",
)
async def suggest_enclosure(component_id: str) -> dict[str, Any]:
    """Get suggested enclosure dimensions for a component.

    Returns recommended dimensions with appropriate clearances
    for 3D printing.
    """
    registry = get_registry()

    try:
        comp = registry.lookup(component_id)
    except ComponentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    dims = comp.dimensions

    # Calculate suggested dimensions with clearances
    suggestion = {
        "component": {
            "id": comp.id,
            "name": comp.name,
            "dimensions_mm": dims.to_tuple_mm(),
        },
        "suggested_enclosure": {
            "exterior": {
                "width_mm": dims.width_mm + 10,  # 5mm clearance each side
                "depth_mm": dims.depth_mm + 10,
                "height_mm": dims.height_mm + 20,  # Room for standoffs + lid
            },
            "wall_thickness_mm": 2.5,
            "corner_radius_mm": 3,
            "standoff_height_mm": 5,
        },
        "notes": [
            "5mm horizontal clearance on each side",
            "20mm vertical clearance for standoffs and lid",
            "2.5mm wall thickness suitable for FDM printing",
        ],
    }

    # Add port suggestions if component has ports
    if comp.ports:
        port_sides = list({p.side.value for p in comp.ports if p.side})
        suggestion["port_cutouts"] = {
            "sides_with_ports": port_sides,
            "ports": [{"name": p.name, "side": p.side.value} for p in comp.ports],
        }

    return suggestion
