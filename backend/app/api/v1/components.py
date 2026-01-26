"""
Reference Component API

CRUD operations for reference components and component library.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.reference_component import (
    ComponentExtractionJob,
    ComponentLibrary,
    ReferenceComponent,
    UserComponent,
)
from app.models.user import User

router = APIRouter(prefix="/components", tags=["components"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class DimensionsSchema(BaseModel):
    length: float
    width: float
    height: float
    unit: str = "mm"


class MountingHoleSchema(BaseModel):
    x: float
    y: float
    diameter: float
    thread_size: Optional[str] = None
    depth: Optional[float] = None
    label: Optional[str] = None


class ConnectorSchema(BaseModel):
    name: str
    type: str
    position: dict
    face: str
    cutout_width: float
    cutout_height: float
    cutout_depth: float = 0
    cable_clearance: float = 15.0


class ClearanceZoneSchema(BaseModel):
    name: str
    type: str
    bounds: dict
    minimum_clearance: float = 5.0
    requires_venting: bool = False


class ThermalPropertiesSchema(BaseModel):
    max_operating_temp: Optional[float] = None
    heat_dissipation: Optional[float] = None
    requires_heatsink: bool = False
    requires_venting: bool = False


class ComponentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    tags: list[str] = []


class ComponentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    tags: Optional[list[str]] = None


class SpecificationsUpdate(BaseModel):
    dimensions: Optional[DimensionsSchema] = None
    mounting_holes: Optional[list[MountingHoleSchema]] = None
    connectors: Optional[list[ConnectorSchema]] = None
    clearance_zones: Optional[list[ClearanceZoneSchema]] = None
    thermal_properties: Optional[ThermalPropertiesSchema] = None


class ComponentResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    name: str
    description: Optional[str]
    category: str
    subcategory: Optional[str]
    manufacturer: Optional[str]
    model_number: Optional[str]
    source_type: str
    thumbnail_url: Optional[str]
    dimensions: Optional[dict]
    mounting_holes: Optional[list]
    connectors: Optional[list]
    clearance_zones: Optional[list]
    thermal_properties: Optional[dict]
    extraction_status: str
    confidence_score: Optional[float]
    is_verified: bool
    tags: list
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComponentListResponse(BaseModel):
    items: list[ComponentResponse]
    total: int
    page: int
    page_size: int


class LibraryComponentResponse(BaseModel):
    id: UUID
    component_id: UUID
    name: str
    description: Optional[str]
    category: str
    subcategory: Optional[str]
    manufacturer: Optional[str]
    model_number: Optional[str]
    thumbnail_url: Optional[str]
    dimensions: Optional[dict]
    popularity_score: int
    usage_count: int
    is_featured: bool
    tags: list

    class Config:
        from_attributes = True


class ExtractionJobResponse(BaseModel):
    id: UUID
    component_id: UUID
    job_type: str
    status: str
    progress: int
    current_step: Optional[str]
    confidence_score: Optional[float]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# =============================================================================
# Component CRUD Endpoints
# =============================================================================

@router.post("", response_model=ComponentResponse, status_code=201)
async def create_component(
    data: ComponentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new reference component."""
    component = ReferenceComponent(
        id=uuid4(),
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        category=data.category,
        subcategory=data.subcategory,
        manufacturer=data.manufacturer,
        model_number=data.model_number,
        source_type="uploaded",
        tags=data.tags,
        extraction_status="pending",
    )
    
    db.add(component)
    await db.commit()
    await db.refresh(component)
    
    return component


@router.get("", response_model=ComponentListResponse)
async def list_components(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's reference components."""
    query = select(ReferenceComponent).where(
        and_(
            ReferenceComponent.user_id == current_user.id,
            ReferenceComponent.deleted_at.is_(None),
        )
    )
    
    # Filters
    if category:
        query = query.where(ReferenceComponent.category == category)
    
    if search:
        search_filter = or_(
            ReferenceComponent.name.ilike(f"%{search}%"),
            ReferenceComponent.manufacturer.ilike(f"%{search}%"),
            ReferenceComponent.model_number.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(ReferenceComponent.created_at.desc())
    
    result = await db.execute(query)
    components = result.scalars().all()
    
    return ComponentListResponse(
        items=components,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{component_id}", response_model=ComponentResponse)
async def get_component(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a reference component by ID."""
    query = select(ReferenceComponent).where(
        and_(
            ReferenceComponent.id == component_id,
            ReferenceComponent.deleted_at.is_(None),
            or_(
                ReferenceComponent.user_id == current_user.id,
                ReferenceComponent.source_type == "library",
            ),
        )
    )
    
    result = await db.execute(query)
    component = result.scalar_one_or_none()
    
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    return component


@router.put("/{component_id}", response_model=ComponentResponse)
async def update_component(
    component_id: UUID,
    data: ComponentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a reference component."""
    query = select(ReferenceComponent).where(
        and_(
            ReferenceComponent.id == component_id,
            ReferenceComponent.user_id == current_user.id,
            ReferenceComponent.deleted_at.is_(None),
        )
    )
    
    result = await db.execute(query)
    component = result.scalar_one_or_none()
    
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(component, field, value)
    
    component.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(component)
    
    return component


@router.put("/{component_id}/specifications", response_model=ComponentResponse)
async def update_specifications(
    component_id: UUID,
    data: SpecificationsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update component specifications manually."""
    query = select(ReferenceComponent).where(
        and_(
            ReferenceComponent.id == component_id,
            ReferenceComponent.user_id == current_user.id,
            ReferenceComponent.deleted_at.is_(None),
        )
    )
    
    result = await db.execute(query)
    component = result.scalar_one_or_none()
    
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    # Update specifications
    if data.dimensions:
        component.dimensions = data.dimensions.model_dump()
    if data.mounting_holes is not None:
        component.mounting_holes = [h.model_dump() for h in data.mounting_holes]
    if data.connectors is not None:
        component.connectors = [c.model_dump() for c in data.connectors]
    if data.clearance_zones is not None:
        component.clearance_zones = [z.model_dump() for z in data.clearance_zones]
    if data.thermal_properties:
        component.thermal_properties = data.thermal_properties.model_dump()
    
    # Mark as manually edited
    component.extraction_status = "manual"
    component.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(component)
    
    return component


@router.delete("/{component_id}", status_code=204)
async def delete_component(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a reference component."""
    query = select(ReferenceComponent).where(
        and_(
            ReferenceComponent.id == component_id,
            ReferenceComponent.user_id == current_user.id,
            ReferenceComponent.deleted_at.is_(None),
        )
    )
    
    result = await db.execute(query)
    component = result.scalar_one_or_none()
    
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    component.deleted_at = datetime.utcnow()
    await db.commit()


# =============================================================================
# Extraction Endpoints
# =============================================================================

@router.post("/{component_id}/extract", response_model=ExtractionJobResponse)
async def trigger_extraction(
    component_id: UUID,
    job_type: str = Query("full", regex="^(datasheet|cad|full)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger AI extraction for a component."""
    # Verify component exists and user owns it
    query = select(ReferenceComponent).where(
        and_(
            ReferenceComponent.id == component_id,
            ReferenceComponent.user_id == current_user.id,
            ReferenceComponent.deleted_at.is_(None),
        )
    )
    
    result = await db.execute(query)
    component = result.scalar_one_or_none()
    
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    # Check for existing pending job
    existing_query = select(ComponentExtractionJob).where(
        and_(
            ComponentExtractionJob.component_id == component_id,
            ComponentExtractionJob.status.in_(["pending", "processing"]),
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Extraction already in progress",
        )
    
    # Create extraction job
    job = ComponentExtractionJob(
        id=uuid4(),
        component_id=component_id,
        job_type=job_type,
        status="pending",
        progress=0,
    )
    
    db.add(job)
    
    # Update component status
    component.extraction_status = "processing"
    
    await db.commit()
    await db.refresh(job)
    
    # TODO: Queue background task for extraction
    
    return job


@router.get("/{component_id}/extraction-status", response_model=ExtractionJobResponse)
async def get_extraction_status(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get latest extraction job status."""
    query = (
        select(ComponentExtractionJob)
        .where(ComponentExtractionJob.component_id == component_id)
        .order_by(ComponentExtractionJob.created_at.desc())
        .limit(1)
    )
    
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="No extraction job found")
    
    return job


# =============================================================================
# Library Endpoints
# =============================================================================

library_router = APIRouter(prefix="/library", tags=["component-library"])


class LibrarySearchResponse(BaseModel):
    """Response with pagination metadata."""
    items: list[LibraryComponentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@library_router.get("", response_model=LibrarySearchResponse)
async def browse_library(
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    manufacturer: Optional[str] = None,
    search: Optional[str] = None,
    featured: Optional[bool] = None,
    sort_by: str = Query("popularity", regex="^(popularity|name|newest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Browse the component library with search and filters."""
    # Base query
    query = (
        select(ComponentLibrary)
        .join(ReferenceComponent)
        .where(ReferenceComponent.deleted_at.is_(None))
    )
    
    # Filters
    if category:
        query = query.where(ComponentLibrary.category == category)
    if subcategory:
        query = query.where(ComponentLibrary.subcategory == subcategory)
    if manufacturer:
        query = query.where(ComponentLibrary.manufacturer.ilike(f"%{manufacturer}%"))
    if featured is not None:
        query = query.where(ComponentLibrary.is_featured == featured)
    
    if search:
        search_filter = or_(
            ReferenceComponent.name.ilike(f"%{search}%"),
            ReferenceComponent.manufacturer.ilike(f"%{search}%"),
            ReferenceComponent.model_number.ilike(f"%{search}%"),
            ComponentLibrary.tags.contains([search]),
        )
        query = query.where(search_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Sorting
    if sort_by == "popularity":
        query = query.order_by(
            ComponentLibrary.is_featured.desc(),
            ComponentLibrary.popularity_score.desc(),
        )
    elif sort_by == "name":
        query = query.order_by(ReferenceComponent.name.asc())
    elif sort_by == "newest":
        query = query.order_by(ReferenceComponent.created_at.desc())
    
    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.options(selectinload(ComponentLibrary.component))
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    # Build response with component data
    items = []
    for entry in entries:
        comp = entry.component
        items.append(
            LibraryComponentResponse(
                id=entry.id,
                component_id=entry.component_id,
                name=comp.name,
                description=comp.description,
                category=entry.category,
                subcategory=entry.subcategory,
                manufacturer=entry.manufacturer,
                model_number=entry.model_number,
                thumbnail_url=comp.thumbnail_url,
                dimensions=comp.dimensions,
                popularity_score=entry.popularity_score,
                usage_count=entry.usage_count,
                is_featured=entry.is_featured,
                tags=entry.tags or [],
            )
        )
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return LibrarySearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@library_router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all component categories."""
    query = (
        select(
            ComponentLibrary.category,
            ComponentLibrary.subcategory,
            func.count(ComponentLibrary.id).label("count"),
        )
        .group_by(ComponentLibrary.category, ComponentLibrary.subcategory)
        .order_by(ComponentLibrary.category, ComponentLibrary.subcategory)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    # Group by category
    categories = {}
    for row in rows:
        cat = row.category
        subcat = row.subcategory
        count = row.count
        
        if cat not in categories:
            categories[cat] = {"name": cat, "subcategories": [], "total": 0}
        
        if subcat:
            categories[cat]["subcategories"].append({"name": subcat, "count": count})
        categories[cat]["total"] += count
    
    return list(categories.values())


@library_router.get("/{library_id}", response_model=ComponentResponse)
async def get_library_component(
    library_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a library component."""
    query = (
        select(ComponentLibrary)
        .where(ComponentLibrary.id == library_id)
        .options(selectinload(ComponentLibrary.component))
    )
    
    result = await db.execute(query)
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Component not found")
    
    return entry.component


@library_router.post("/{library_id}/add")
async def add_library_component_to_project(
    library_id: UUID,
    project_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a library component to user's collection or project."""
    # Get library entry
    query = (
        select(ComponentLibrary)
        .where(ComponentLibrary.id == library_id)
        .options(selectinload(ComponentLibrary.component))
    )
    
    result = await db.execute(query)
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Component not found")
    
    # Create user component
    user_component = UserComponent(
        id=uuid4(),
        user_id=current_user.id,
        source_component_id=entry.component_id,
        project_id=project_id,
    )
    
    db.add(user_component)
    
    # Increment usage count
    entry.usage_count += 1
    
    await db.commit()
    await db.refresh(user_component)
    
    return {
        "id": user_component.id,
        "component_id": entry.component_id,
        "project_id": project_id,
        "message": "Component added successfully",
    }


@library_router.post("/seed", include_in_schema=False)
async def seed_library(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed the component library with popular components. Admin only."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from app.db.seeds.component_library import COMPONENT_LIBRARY, CATEGORIES
    from uuid import uuid4
    
    count = 0
    
    for component_data in COMPONENT_LIBRARY:
        # Check if component already exists
        result = await db.execute(
            select(ComponentLibrary).where(
                ComponentLibrary.model_number == component_data["model_number"]
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            continue
        
        # Create the base reference component
        ref_component = ReferenceComponent(
            id=uuid4(),
            user_id=current_user.id,
            name=component_data["name"],
            source_type="library_seed",
            category=CATEGORIES.get(component_data["category"], component_data["category"]),
            manufacturer=component_data["manufacturer"],
            model_number=component_data["model_number"],
            description=component_data.get("description", ""),
            dimensions=component_data["dimensions"],
            mounting_holes=component_data.get("mounting_holes", []),
            connectors=component_data.get("connectors", []),
            clearance_zones=component_data.get("clearance_zones", []),
            thermal_properties=component_data.get("thermal", {}),
            weight_grams=component_data.get("weight_g"),
            is_verified=True,
        )
        db.add(ref_component)
        
        # Create library entry
        library_entry = ComponentLibrary(
            id=uuid4(),
            component_id=ref_component.id,
            category=component_data["category"],
            subcategory=None,
            manufacturer=component_data["manufacturer"],
            model_number=component_data["model_number"],
            popularity_score=100,
            is_featured=component_data["category"] in ["sbc", "mcu"],
            tags=[component_data["category"], component_data["manufacturer"].lower()],
        )
        db.add(library_entry)
        count += 1
    
    await db.commit()
    
    return {
        "message": f"Seeded {count} components to library",
        "total_available": len(COMPONENT_LIBRARY),
    }


@library_router.get("/manufacturers")
async def list_manufacturers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all manufacturers in the library."""
    query = (
        select(
            ComponentLibrary.manufacturer,
            func.count(ComponentLibrary.id).label("count"),
        )
        .where(ComponentLibrary.manufacturer.isnot(None))
        .group_by(ComponentLibrary.manufacturer)
        .order_by(func.count(ComponentLibrary.id).desc())
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    return [{"name": row.manufacturer, "count": row.count} for row in rows]
