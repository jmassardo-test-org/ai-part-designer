"""
Spatial Layout API

API endpoints for managing component spatial arrangements.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.project import Project
from app.models.reference_component import ReferenceComponent
from app.models.spatial_layout import ComponentPlacement, SpatialLayout

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/layouts", tags=["layouts"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class LayoutCreateRequest(BaseModel):
    """Request to create a new layout."""

    project_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    enclosure_length: float = Field(default=100.0, gt=0)
    enclosure_width: float = Field(default=100.0, gt=0)
    enclosure_height: float = Field(default=50.0, gt=0)
    auto_arrange: bool = True
    min_spacing_x: float = Field(default=5.0, gt=0)
    min_spacing_y: float = Field(default=5.0, ge=0)


class LayoutUpdateRequest(BaseModel):
    """Request to update a layout."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    enclosure_length: float | None = Field(default=None, gt=0)
    enclosure_width: float | None = Field(default=None, gt=0)
    enclosure_height: float | None = Field(default=None, gt=0)
    auto_arrange: bool | None = None
    min_spacing_x: float | None = Field(default=None, gt=0)
    min_spacing_y: float | None = Field(default=None, ge=0)
    status: str | None = None


class PlacementCreateRequest(BaseModel):
    """Request to add a component to a layout."""

    component_id: UUID
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation_z: float = Field(default=0.0, ge=0, lt=360)
    face_direction: str = Field(default="front", pattern="^(front|back|left|right)$")
    locked: bool = False
    color_override: str | None = None
    notes: str | None = None


class PlacementUpdateRequest(BaseModel):
    """Request to update a component placement."""

    x: float | None = None
    y: float | None = None
    z: float | None = None
    rotation_z: float | None = Field(default=None, ge=0, lt=360)
    face_direction: str | None = Field(default=None, pattern="^(front|back|left|right)$")
    locked: bool | None = None
    color_override: str | None = None
    notes: str | None = None


class PlacementResponse(BaseModel):
    """Response for a component placement."""

    id: UUID
    layout_id: UUID
    component_id: UUID
    component_name: str | None = None
    x: float
    y: float
    z: float
    rotation_z: float
    width: float | None = None
    depth: float | None = None
    height: float | None = None
    face_direction: str
    locked: bool
    color_override: str | None = None
    notes: str | None = None

    class Config:
        from_attributes = True


class LayoutResponse(BaseModel):
    """Response for a layout."""

    id: UUID
    project_id: UUID
    name: str
    description: str | None = None
    status: str
    enclosure_length: float
    enclosure_width: float
    enclosure_height: float
    auto_arrange: bool
    min_spacing_x: float
    min_spacing_y: float
    component_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class LayoutDetailResponse(LayoutResponse):
    """Detailed response including placements."""

    placements: list[PlacementResponse] = []


class LayoutListResponse(BaseModel):
    """Response for listing layouts."""

    layouts: list[LayoutResponse]
    total: int


class ValidationResult(BaseModel):
    """Result of layout validation."""

    valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    collisions: list[dict] = []


class AutoLayoutRequest(BaseModel):
    """Request to auto-arrange components."""

    component_ids: list[UUID]
    algorithm: str = Field(default="packed", pattern="^(packed|grid|thermal)$")
    prioritize_connector_access: bool = True


class AutoLayoutResponse(BaseModel):
    """Response from auto-layout."""

    placements: list[PlacementResponse]
    suggested_dimensions: dict


# =============================================================================
# Layout CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=LayoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create layout",
)
async def create_layout(
    request: LayoutCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LayoutResponse:
    """Create a new spatial layout for a project."""

    # Verify project access
    project = await db.get(Project, request.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Create layout
    layout = SpatialLayout(
        project_id=request.project_id,
        name=request.name,
        description=request.description,
        enclosure_length=request.enclosure_length,
        enclosure_width=request.enclosure_width,
        enclosure_height=request.enclosure_height,
        auto_arrange=request.auto_arrange,
        min_spacing_x=request.min_spacing_x,
        min_spacing_y=request.min_spacing_y,
    )

    db.add(layout)
    await db.commit()
    await db.refresh(layout)

    return LayoutResponse(
        id=layout.id,
        project_id=layout.project_id,
        name=layout.name,
        description=layout.description,
        status=layout.status,
        enclosure_length=layout.enclosure_length,
        enclosure_width=layout.enclosure_width,
        enclosure_height=layout.enclosure_height,
        auto_arrange=layout.auto_arrange,
        min_spacing_x=layout.min_spacing_x,
        min_spacing_y=layout.min_spacing_y,
        component_count=0,
        created_at=layout.created_at.isoformat(),
        updated_at=layout.updated_at.isoformat(),
    )


@router.get(
    "",
    response_model=LayoutListResponse,
    summary="List layouts",
)
async def list_layouts(
    project_id: UUID = Query(..., description="Filter by project"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LayoutListResponse:
    """List layouts for a project."""

    # Verify project access
    project = await db.get(Project, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Query layouts
    query = (
        select(SpatialLayout)
        .where(SpatialLayout.project_id == project_id)
        .order_by(SpatialLayout.created_at.desc())
    )
    result = await db.execute(query)
    layouts = result.scalars().all()

    # Get component counts
    layout_responses = []
    for layout in layouts:
        count_query = select(func.count()).where(ComponentPlacement.layout_id == layout.id)
        count_result = await db.execute(count_query)
        count = count_result.scalar() or 0

        layout_responses.append(
            LayoutResponse(
                id=layout.id,
                project_id=layout.project_id,
                name=layout.name,
                description=layout.description,
                status=layout.status,
                enclosure_length=layout.enclosure_length,
                enclosure_width=layout.enclosure_width,
                enclosure_height=layout.enclosure_height,
                auto_arrange=layout.auto_arrange,
                min_spacing_x=layout.min_spacing_x,
                min_spacing_y=layout.min_spacing_y,
                component_count=count,
                created_at=layout.created_at.isoformat(),
                updated_at=layout.updated_at.isoformat(),
            )
        )

    return LayoutListResponse(
        layouts=layout_responses,
        total=len(layout_responses),
    )


@router.get(
    "/{layout_id}",
    response_model=LayoutDetailResponse,
    summary="Get layout",
)
async def get_layout(
    layout_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LayoutDetailResponse:
    """Get a layout with all placements."""

    # Query layout with placements
    query = (
        select(SpatialLayout)
        .options(selectinload(SpatialLayout.placements))
        .where(SpatialLayout.id == layout_id)
    )
    result = await db.execute(query)
    layout = result.scalar_one_or_none()

    if not layout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    # Verify access through project
    project = await db.get(Project, layout.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    # Build placement responses
    placement_responses = []
    for p in layout.placements:
        component_name = None
        if p.component:
            component_name = p.component.name

        placement_responses.append(
            PlacementResponse(
                id=p.id,
                layout_id=p.layout_id,
                component_id=p.component_id,
                component_name=component_name,
                x=p.x,
                y=p.y,
                z=p.z,
                rotation_z=p.rotation_z,
                width=p.width,
                depth=p.depth,
                height=p.height,
                face_direction=p.face_direction,
                locked=p.locked,
                color_override=p.color_override,
                notes=p.notes,
            )
        )

    return LayoutDetailResponse(
        id=layout.id,
        project_id=layout.project_id,
        name=layout.name,
        description=layout.description,
        status=layout.status,
        enclosure_length=layout.enclosure_length,
        enclosure_width=layout.enclosure_width,
        enclosure_height=layout.enclosure_height,
        auto_arrange=layout.auto_arrange,
        min_spacing_x=layout.min_spacing_x,
        min_spacing_y=layout.min_spacing_y,
        component_count=len(placement_responses),
        created_at=layout.created_at.isoformat(),
        updated_at=layout.updated_at.isoformat(),
        placements=placement_responses,
    )


@router.patch(
    "/{layout_id}",
    response_model=LayoutResponse,
    summary="Update layout",
)
async def update_layout(
    layout_id: UUID,
    request: LayoutUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LayoutResponse:
    """Update a layout's settings."""

    layout = await db.get(SpatialLayout, layout_id)
    if not layout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    # Verify access
    project = await db.get(Project, layout.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(layout, field, value)

    await db.commit()
    await db.refresh(layout)

    # Get component count
    count_query = select(func.count()).where(ComponentPlacement.layout_id == layout.id)
    count_result = await db.execute(count_query)
    count = count_result.scalar() or 0

    return LayoutResponse(
        id=layout.id,
        project_id=layout.project_id,
        name=layout.name,
        description=layout.description,
        status=layout.status,
        enclosure_length=layout.enclosure_length,
        enclosure_width=layout.enclosure_width,
        enclosure_height=layout.enclosure_height,
        auto_arrange=layout.auto_arrange,
        min_spacing_x=layout.min_spacing_x,
        min_spacing_y=layout.min_spacing_y,
        component_count=count,
        created_at=layout.created_at.isoformat(),
        updated_at=layout.updated_at.isoformat(),
    )


@router.delete(
    "/{layout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete layout",
)
async def delete_layout(
    layout_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a layout and all its placements."""

    layout = await db.get(SpatialLayout, layout_id)
    if not layout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    # Verify access
    project = await db.get(Project, layout.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    await db.delete(layout)
    await db.commit()


# =============================================================================
# Placement Endpoints
# =============================================================================


@router.post(
    "/{layout_id}/placements",
    response_model=PlacementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add component to layout",
)
async def add_placement(
    layout_id: UUID,
    request: PlacementCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlacementResponse:
    """Add a component placement to a layout."""

    # Get and verify layout
    layout = await db.get(SpatialLayout, layout_id)
    if not layout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    project = await db.get(Project, layout.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    # Verify component exists
    component = await db.get(ReferenceComponent, request.component_id)
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )

    # Check if component already in layout
    existing_query = select(ComponentPlacement).where(
        ComponentPlacement.layout_id == layout_id,
        ComponentPlacement.component_id == request.component_id,
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Component already in layout",
        )

    # Get component dimensions from specifications
    width = depth = height = None
    if component.specifications:
        dims = component.specifications.get("dimensions", {})
        width = dims.get("length") or dims.get("width")
        depth = dims.get("width") or dims.get("depth")
        height = dims.get("height")

    # Create placement
    placement = ComponentPlacement(
        layout_id=layout_id,
        component_id=request.component_id,
        x=request.x,
        y=request.y,
        z=request.z,
        rotation_z=request.rotation_z,
        width=width,
        depth=depth,
        height=height,
        face_direction=request.face_direction,
        locked=request.locked,
        color_override=request.color_override,
        notes=request.notes,
    )

    db.add(placement)
    await db.commit()
    await db.refresh(placement)

    return PlacementResponse(
        id=placement.id,
        layout_id=placement.layout_id,
        component_id=placement.component_id,
        component_name=component.name,
        x=placement.x,
        y=placement.y,
        z=placement.z,
        rotation_z=placement.rotation_z,
        width=placement.width,
        depth=placement.depth,
        height=placement.height,
        face_direction=placement.face_direction,
        locked=placement.locked,
        color_override=placement.color_override,
        notes=placement.notes,
    )


@router.patch(
    "/{layout_id}/placements/{placement_id}",
    response_model=PlacementResponse,
    summary="Update placement",
)
async def update_placement(
    layout_id: UUID,
    placement_id: UUID,
    request: PlacementUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlacementResponse:
    """Update a component placement."""

    # Get placement with layout verification
    query = (
        select(ComponentPlacement)
        .options(selectinload(ComponentPlacement.component))
        .where(
            ComponentPlacement.id == placement_id,
            ComponentPlacement.layout_id == layout_id,
        )
    )
    result = await db.execute(query)
    placement = result.scalar_one_or_none()

    if not placement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Placement not found",
        )

    # Verify access through layout/project
    layout = await db.get(SpatialLayout, layout_id)
    project = await db.get(Project, layout.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Placement not found",
        )

    # Check if locked
    if placement.locked and not request.locked:
        # Allow unlocking
        pass
    elif placement.locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Placement is locked. Unlock first to modify.",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)

    # Handle rotation - swap dimensions if needed
    if "rotation_z" in update_data:
        new_rotation = round(update_data["rotation_z"] / 90) * 90 % 360
        old_rotation = round(placement.rotation_z / 90) * 90 % 360

        # If rotation changes by 90 or 270 degrees, swap width/depth
        rotation_diff = abs(new_rotation - old_rotation)
        if rotation_diff in (90, 270):
            placement.width, placement.depth = placement.depth, placement.width

        update_data["rotation_z"] = new_rotation

    for field, value in update_data.items():
        setattr(placement, field, value)

    await db.commit()
    await db.refresh(placement)

    component_name = placement.component.name if placement.component else None

    return PlacementResponse(
        id=placement.id,
        layout_id=placement.layout_id,
        component_id=placement.component_id,
        component_name=component_name,
        x=placement.x,
        y=placement.y,
        z=placement.z,
        rotation_z=placement.rotation_z,
        width=placement.width,
        depth=placement.depth,
        height=placement.height,
        face_direction=placement.face_direction,
        locked=placement.locked,
        color_override=placement.color_override,
        notes=placement.notes,
    )


@router.delete(
    "/{layout_id}/placements/{placement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove component from layout",
)
async def remove_placement(
    layout_id: UUID,
    placement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a component from a layout."""

    # Get placement
    query = select(ComponentPlacement).where(
        ComponentPlacement.id == placement_id,
        ComponentPlacement.layout_id == layout_id,
    )
    result = await db.execute(query)
    placement = result.scalar_one_or_none()

    if not placement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Placement not found",
        )

    # Verify access
    layout = await db.get(SpatialLayout, layout_id)
    project = await db.get(Project, layout.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Placement not found",
        )

    await db.delete(placement)
    await db.commit()


# =============================================================================
# Validation & Auto-Layout
# =============================================================================


@router.post(
    "/{layout_id}/validate",
    response_model=ValidationResult,
    summary="Validate layout",
)
async def validate_layout(
    layout_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidationResult:
    """Validate layout for collisions and boundary violations."""

    # Get layout with placements
    query = (
        select(SpatialLayout)
        .options(selectinload(SpatialLayout.placements))
        .where(SpatialLayout.id == layout_id)
    )
    result = await db.execute(query)
    layout = result.scalar_one_or_none()

    if not layout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    # Verify access
    project = await db.get(Project, layout.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    errors = []
    warnings = []
    collisions = []

    placements = list(layout.placements)

    # Check each placement
    for i, p in enumerate(placements):
        # Check boundary violations
        if p.x < 0:
            errors.append(f"Component at placement {p.id} extends past left boundary")
        if p.y < 0:
            errors.append(f"Component at placement {p.id} extends past front boundary")
        if p.z < 0:
            errors.append(f"Component at placement {p.id} is below floor")

        max_x = p.x + (p.width or 0)
        max_y = p.y + (p.depth or 0)
        max_z = p.z + (p.height or 0)

        if max_x > layout.enclosure_length:
            errors.append(f"Component at placement {p.id} extends past right boundary")
        if max_y > layout.enclosure_width:
            errors.append(f"Component at placement {p.id} extends past back boundary")
        if max_z > layout.enclosure_height:
            warnings.append(f"Component at placement {p.id} exceeds enclosure height")

        # Check collisions with other placements
        for j, other in enumerate(placements):
            if i >= j:
                continue

            if p.intersects(other, margin=layout.min_spacing_x):
                collisions.append(
                    {
                        "placement_1": str(p.id),
                        "placement_2": str(other.id),
                        "margin_violated": layout.min_spacing_x,
                    }
                )
                errors.append(f"Components at placements {p.id} and {other.id} collide")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        collisions=collisions,
    )


@router.post(
    "/{layout_id}/auto-layout",
    response_model=AutoLayoutResponse,
    summary="Auto-arrange components",
)
async def auto_layout(
    layout_id: UUID,
    request: AutoLayoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AutoLayoutResponse:
    """
    Automatically arrange components in a layout.

    Does not modify existing placements - returns suggested positions.
    """

    # Get layout
    layout = await db.get(SpatialLayout, layout_id)
    if not layout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    # Verify access
    project = await db.get(Project, layout.project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Layout not found",
        )

    # Get components
    components = []
    for cid in request.component_ids:
        component = await db.get(ReferenceComponent, cid)
        if component:
            components.append(component)

    if not components:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid components provided",
        )

    # Simple packed layout algorithm
    placements = []
    current_x = layout.min_spacing_x
    current_y = layout.min_spacing_y
    row_height = 0
    max_x = 0
    max_y = 0
    max_z = 0

    for component in components:
        # Get dimensions
        dims = component.specifications.get("dimensions", {}) if component.specifications else {}
        width = dims.get("length") or dims.get("width") or 50
        depth = dims.get("width") or dims.get("depth") or 50
        height = dims.get("height") or 20

        # Check if fits in current row
        if current_x + width + layout.min_spacing_x > layout.enclosure_length:
            # Start new row
            current_x = layout.min_spacing_x
            current_y += row_height + layout.min_spacing_y
            row_height = 0

        # Place component
        placements.append(
            PlacementResponse(
                id=component.id,  # Temporary - would be new UUID
                layout_id=layout_id,
                component_id=component.id,
                component_name=component.name,
                x=current_x,
                y=current_y,
                z=0,  # Floor level
                rotation_z=0,
                width=width,
                depth=depth,
                height=height,
                face_direction="front",
                locked=False,
            )
        )

        # Update position for next component
        current_x += width + layout.min_spacing_x
        row_height = max(row_height, depth)

        # Track max dimensions
        max_x = max(max_x, current_x)
        max_y = max(max_y, current_y + depth)
        max_z = max(max_z, height)

    # Suggested dimensions
    suggested_dimensions = {
        "width": max_x + layout.min_spacing_x,
        "depth": max_y + layout.min_spacing_y,
        "height": max_z + 10,  # Add some headroom
    }

    return AutoLayoutResponse(
        placements=placements,
        suggested_dimensions=suggested_dimensions,
    )
