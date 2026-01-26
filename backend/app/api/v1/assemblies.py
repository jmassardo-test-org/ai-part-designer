"""
Assembly API endpoints.

CRUD operations for assemblies, components, and relationships.
"""

from uuid import UUID
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.design import Design
from app.models.assembly import (
    Assembly,
    AssemblyComponent,
    ComponentRelationship,
    BOMItem,
    Vendor,
)


router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class Position(BaseModel):
    """3D position."""
    x: float = 0
    y: float = 0
    z: float = 0


class Rotation(BaseModel):
    """3D rotation (Euler angles in degrees)."""
    rx: float = 0
    ry: float = 0
    rz: float = 0


class Scale(BaseModel):
    """3D scale."""
    sx: float = 1
    sy: float = 1
    sz: float = 1


class AssemblyCreate(BaseModel):
    """Request to create an assembly."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    project_id: UUID
    root_design_id: Optional[UUID] = None


class AssemblyUpdate(BaseModel):
    """Request to update an assembly."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[str] = None


class ComponentCreate(BaseModel):
    """Request to add a component."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    design_id: Optional[UUID] = None
    quantity: int = Field(1, ge=1)
    position: Position = Field(default_factory=Position)
    rotation: Rotation = Field(default_factory=Rotation)
    is_cots: bool = False
    part_number: Optional[str] = None
    color: Optional[str] = None


class ComponentUpdate(BaseModel):
    """Request to update a component."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=1)
    position: Optional[Position] = None
    rotation: Optional[Rotation] = None
    scale: Optional[Scale] = None
    color: Optional[str] = None


class RelationshipCreate(BaseModel):
    """Request to create a relationship."""
    parent_component_id: UUID
    child_component_id: UUID
    relationship_type: str = Field(..., min_length=1, max_length=50)
    name: Optional[str] = None
    constraint_data: dict = Field(default_factory=dict)
    assembly_order: Optional[int] = None


class ComponentResponse(BaseModel):
    """Response for a component."""
    id: UUID
    name: str
    description: Optional[str]
    design_id: Optional[UUID]
    design_name: Optional[str]
    quantity: int
    position: dict
    rotation: dict
    scale: dict
    is_cots: bool
    part_number: Optional[str]
    color: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class RelationshipResponse(BaseModel):
    """Response for a relationship."""
    id: UUID
    parent_component_id: UUID
    child_component_id: UUID
    relationship_type: str
    name: Optional[str]
    constraint_data: dict
    assembly_order: Optional[int]

    class Config:
        from_attributes = True


class AssemblyResponse(BaseModel):
    """Response for an assembly."""
    id: UUID
    name: str
    description: Optional[str]
    project_id: UUID
    project_name: str
    root_design_id: Optional[UUID]
    status: str
    thumbnail_url: Optional[str]
    component_count: int
    total_quantity: int
    version: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AssemblyDetailResponse(AssemblyResponse):
    """Response for assembly with components and relationships."""
    components: list[ComponentResponse]
    relationships: list[RelationshipResponse]


class AssemblyListResponse(BaseModel):
    """Response for listing assemblies."""
    assemblies: list[AssemblyResponse]
    total: int
    page: int
    per_page: int


# ============================================================================
# Assembly CRUD Endpoints
# ============================================================================

@router.post("/assemblies", response_model=AssemblyResponse, status_code=status.HTTP_201_CREATED)
async def create_assembly(
    request: AssemblyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssemblyResponse:
    """Create a new assembly."""
    # Verify project ownership
    project_query = select(Project).where(
        Project.id == request.project_id,
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None),
    )
    project_result = await db.execute(project_query)
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Verify root design if provided
    if request.root_design_id:
        design_query = select(Design).where(
            Design.id == request.root_design_id,
            Design.deleted_at.is_(None),
        )
        design_result = await db.execute(design_query)
        design = design_result.scalar_one_or_none()
        if not design:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Root design not found",
            )
    
    assembly = Assembly(
        user_id=current_user.id,
        project_id=request.project_id,
        root_design_id=request.root_design_id,
        name=request.name,
        description=request.description,
    )
    
    db.add(assembly)
    await db.commit()
    await db.refresh(assembly)
    
    return AssemblyResponse(
        id=assembly.id,
        name=assembly.name,
        description=assembly.description,
        project_id=assembly.project_id,
        project_name=project.name,
        root_design_id=assembly.root_design_id,
        status=assembly.status,
        thumbnail_url=assembly.thumbnail_url,
        component_count=0,
        total_quantity=0,
        version=assembly.version,
        created_at=assembly.created_at.isoformat(),
        updated_at=assembly.updated_at.isoformat(),
    )


@router.get("/assemblies", response_model=AssemblyListResponse)
async def list_assemblies(
    project_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssemblyListResponse:
    """List assemblies for the current user."""
    query = (
        select(Assembly)
        .join(Project, Assembly.project_id == Project.id)
        .where(Assembly.user_id == current_user.id)
        .where(Assembly.deleted_at.is_(None))
    )
    
    if project_id:
        query = query.where(Assembly.project_id == project_id)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Get page
    offset = (page - 1) * per_page
    query = query.order_by(Assembly.updated_at.desc()).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    assemblies = result.scalars().all()
    
    assembly_responses = []
    for assembly in assemblies:
        # Get component count
        comp_count_query = select(func.count()).where(
            AssemblyComponent.assembly_id == assembly.id
        )
        comp_count_result = await db.execute(comp_count_query)
        component_count = comp_count_result.scalar() or 0
        
        # Get total quantity
        qty_query = select(func.coalesce(func.sum(AssemblyComponent.quantity), 0)).where(
            AssemblyComponent.assembly_id == assembly.id
        )
        qty_result = await db.execute(qty_query)
        total_quantity = qty_result.scalar() or 0
        
        assembly_responses.append(AssemblyResponse(
            id=assembly.id,
            name=assembly.name,
            description=assembly.description,
            project_id=assembly.project_id,
            project_name=assembly.project.name,
            root_design_id=assembly.root_design_id,
            status=assembly.status,
            thumbnail_url=assembly.thumbnail_url,
            component_count=component_count,
            total_quantity=total_quantity,
            version=assembly.version,
            created_at=assembly.created_at.isoformat(),
            updated_at=assembly.updated_at.isoformat(),
        ))
    
    return AssemblyListResponse(
        assemblies=assembly_responses,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/assemblies/{assembly_id}", response_model=AssemblyDetailResponse)
async def get_assembly(
    assembly_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssemblyDetailResponse:
    """Get an assembly with its components and relationships."""
    query = (
        select(Assembly)
        .options(
            selectinload(Assembly.components).selectinload(AssemblyComponent.design),
            selectinload(Assembly.component_relationships),
        )
        .where(Assembly.id == assembly_id)
        .where(Assembly.deleted_at.is_(None))
    )
    result = await db.execute(query)
    assembly = result.scalar_one_or_none()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )
    
    if assembly.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    components = [
        ComponentResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            design_id=c.design_id,
            design_name=c.design.name if c.design else None,
            quantity=c.quantity,
            position=c.position,
            rotation=c.rotation,
            scale=c.scale,
            is_cots=c.is_cots,
            part_number=c.part_number,
            color=c.color,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in assembly.components
    ]
    
    relationships = [
        RelationshipResponse(
            id=r.id,
            parent_component_id=r.parent_component_id,
            child_component_id=r.child_component_id,
            relationship_type=r.relationship_type,
            name=r.name,
            constraint_data=r.constraint_data,
            assembly_order=r.assembly_order,
        )
        for r in assembly.component_relationships
    ]
    
    return AssemblyDetailResponse(
        id=assembly.id,
        name=assembly.name,
        description=assembly.description,
        project_id=assembly.project_id,
        project_name=assembly.project.name,
        root_design_id=assembly.root_design_id,
        status=assembly.status,
        thumbnail_url=assembly.thumbnail_url,
        component_count=len(components),
        total_quantity=sum(c.quantity for c in assembly.components),
        version=assembly.version,
        created_at=assembly.created_at.isoformat(),
        updated_at=assembly.updated_at.isoformat(),
        components=components,
        relationships=relationships,
    )


@router.put("/assemblies/{assembly_id}", response_model=AssemblyResponse)
async def update_assembly(
    assembly_id: UUID,
    request: AssemblyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssemblyResponse:
    """Update an assembly."""
    query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.deleted_at.is_(None),
    )
    result = await db.execute(query)
    assembly = result.scalar_one_or_none()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )
    
    if assembly.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    if request.name is not None:
        assembly.name = request.name
    if request.description is not None:
        assembly.description = request.description
    if request.status is not None:
        assembly.status = request.status
    
    assembly.version += 1
    
    await db.commit()
    await db.refresh(assembly)
    
    # Get counts
    comp_count_query = select(func.count()).where(
        AssemblyComponent.assembly_id == assembly.id
    )
    comp_count_result = await db.execute(comp_count_query)
    component_count = comp_count_result.scalar() or 0
    
    qty_query = select(func.coalesce(func.sum(AssemblyComponent.quantity), 0)).where(
        AssemblyComponent.assembly_id == assembly.id
    )
    qty_result = await db.execute(qty_query)
    total_quantity = qty_result.scalar() or 0
    
    return AssemblyResponse(
        id=assembly.id,
        name=assembly.name,
        description=assembly.description,
        project_id=assembly.project_id,
        project_name=assembly.project.name,
        root_design_id=assembly.root_design_id,
        status=assembly.status,
        thumbnail_url=assembly.thumbnail_url,
        component_count=component_count,
        total_quantity=total_quantity,
        version=assembly.version,
        created_at=assembly.created_at.isoformat(),
        updated_at=assembly.updated_at.isoformat(),
    )


@router.delete("/assemblies/{assembly_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assembly(
    assembly_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete an assembly."""
    query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.deleted_at.is_(None),
    )
    result = await db.execute(query)
    assembly = result.scalar_one_or_none()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )
    
    if assembly.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    from datetime import datetime, timezone
    assembly.deleted_at = datetime.now(timezone.utc)
    
    await db.commit()


# ============================================================================
# Component CRUD Endpoints
# ============================================================================

@router.post("/assemblies/{assembly_id}/components", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
async def add_component(
    assembly_id: UUID,
    request: ComponentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComponentResponse:
    """Add a component to an assembly."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )
    
    # Verify design if provided
    design = None
    if request.design_id:
        design_query = select(Design).where(
            Design.id == request.design_id,
            Design.deleted_at.is_(None),
        )
        design_result = await db.execute(design_query)
        design = design_result.scalar_one_or_none()
        if not design:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Design not found",
            )
    
    component = AssemblyComponent(
        assembly_id=assembly_id,
        design_id=request.design_id,
        name=request.name,
        description=request.description,
        quantity=request.quantity,
        position=request.position.model_dump(),
        rotation=request.rotation.model_dump(),
        is_cots=request.is_cots,
        part_number=request.part_number,
        color=request.color,
    )
    
    db.add(component)
    assembly.version += 1
    
    await db.commit()
    await db.refresh(component)
    
    return ComponentResponse(
        id=component.id,
        name=component.name,
        description=component.description,
        design_id=component.design_id,
        design_name=design.name if design else None,
        quantity=component.quantity,
        position=component.position,
        rotation=component.rotation,
        scale=component.scale,
        is_cots=component.is_cots,
        part_number=component.part_number,
        color=component.color,
        created_at=component.created_at.isoformat(),
        updated_at=component.updated_at.isoformat(),
    )


@router.put("/assemblies/{assembly_id}/components/{component_id}", response_model=ComponentResponse)
async def update_component(
    assembly_id: UUID,
    component_id: UUID,
    request: ComponentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComponentResponse:
    """Update a component."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )
    
    # Get component
    component_query = (
        select(AssemblyComponent)
        .options(selectinload(AssemblyComponent.design))
        .where(
            AssemblyComponent.id == component_id,
            AssemblyComponent.assembly_id == assembly_id,
        )
    )
    component_result = await db.execute(component_query)
    component = component_result.scalar_one_or_none()
    
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )
    
    # Update fields
    if request.name is not None:
        component.name = request.name
    if request.description is not None:
        component.description = request.description
    if request.quantity is not None:
        component.quantity = request.quantity
    if request.position is not None:
        component.position = request.position.model_dump()
    if request.rotation is not None:
        component.rotation = request.rotation.model_dump()
    if request.scale is not None:
        component.scale = request.scale.model_dump()
    if request.color is not None:
        component.color = request.color
    
    assembly.version += 1
    
    await db.commit()
    await db.refresh(component)
    
    return ComponentResponse(
        id=component.id,
        name=component.name,
        description=component.description,
        design_id=component.design_id,
        design_name=component.design.name if component.design else None,
        quantity=component.quantity,
        position=component.position,
        rotation=component.rotation,
        scale=component.scale,
        is_cots=component.is_cots,
        part_number=component.part_number,
        color=component.color,
        created_at=component.created_at.isoformat(),
        updated_at=component.updated_at.isoformat(),
    )


@router.delete("/assemblies/{assembly_id}/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_component(
    assembly_id: UUID,
    component_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a component from an assembly."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )
    
    # Get component
    component_query = select(AssemblyComponent).where(
        AssemblyComponent.id == component_id,
        AssemblyComponent.assembly_id == assembly_id,
    )
    component_result = await db.execute(component_query)
    component = component_result.scalar_one_or_none()
    
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )
    
    await db.delete(component)
    assembly.version += 1
    
    await db.commit()


# ============================================================================
# Relationship CRUD Endpoints
# ============================================================================

@router.post("/assemblies/{assembly_id}/relationships", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    assembly_id: UUID,
    request: RelationshipCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RelationshipResponse:
    """Create a relationship between components."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )
    
    # Verify both components exist in assembly
    for comp_id in [request.parent_component_id, request.child_component_id]:
        comp_query = select(AssemblyComponent).where(
            AssemblyComponent.id == comp_id,
            AssemblyComponent.assembly_id == assembly_id,
        )
        comp_result = await db.execute(comp_query)
        if not comp_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Component {comp_id} not found in assembly",
            )
    
    relationship = ComponentRelationship(
        assembly_id=assembly_id,
        parent_component_id=request.parent_component_id,
        child_component_id=request.child_component_id,
        relationship_type=request.relationship_type,
        name=request.name,
        constraint_data=request.constraint_data,
        assembly_order=request.assembly_order,
    )
    
    db.add(relationship)
    assembly.version += 1
    
    await db.commit()
    await db.refresh(relationship)
    
    return RelationshipResponse(
        id=relationship.id,
        parent_component_id=relationship.parent_component_id,
        child_component_id=relationship.child_component_id,
        relationship_type=relationship.relationship_type,
        name=relationship.name,
        constraint_data=relationship.constraint_data,
        assembly_order=relationship.assembly_order,
    )


@router.delete("/assemblies/{assembly_id}/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relationship(
    assembly_id: UUID,
    relationship_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a relationship."""
    # Verify assembly ownership
    assembly_query = select(Assembly).where(
        Assembly.id == assembly_id,
        Assembly.user_id == current_user.id,
        Assembly.deleted_at.is_(None),
    )
    assembly_result = await db.execute(assembly_query)
    assembly = assembly_result.scalar_one_or_none()
    
    if not assembly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assembly not found",
        )
    
    # Get relationship
    rel_query = select(ComponentRelationship).where(
        ComponentRelationship.id == relationship_id,
        ComponentRelationship.assembly_id == assembly_id,
    )
    rel_result = await db.execute(rel_query)
    relationship = rel_result.scalar_one_or_none()
    
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found",
        )
    
    await db.delete(relationship)
    assembly.version += 1
    
    await db.commit()
