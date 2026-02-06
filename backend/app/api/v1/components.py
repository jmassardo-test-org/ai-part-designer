"""
Reference Component API

CRUD operations for reference components and component library.
"""

from typing import Any, cast

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.storage import StorageBucket, storage_client
from app.models.reference_component import (
    ComponentExtractionJob,
    ComponentLibrary,
    ReferenceComponent,
    UserComponent,
)
from app.models.user import User

logger = logging.getLogger(__name__)

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
    thread_size: str | None = None
    depth: float | None = None
    label: str | None = None


class ConnectorSchema(BaseModel):
    name: str
    type: str
    position: dict[str, Any]
    face: str
    cutout_width: float
    cutout_height: float
    cutout_depth: float = 0
    cable_clearance: float = 15.0


class ClearanceZoneSchema(BaseModel):
    name: str
    type: str
    bounds: dict[str, Any]
    minimum_clearance: float = 5.0
    requires_venting: bool = False


class ThermalPropertiesSchema(BaseModel):
    max_operating_temp: float | None = None
    heat_dissipation: float | None = None
    requires_heatsink: bool = False
    requires_venting: bool = False


class ComponentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(..., min_length=1, max_length=100)
    subcategory: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    tags: list[str] = []


class ComponentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    subcategory: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    tags: list[str] | None = None


class SpecificationsUpdate(BaseModel):
    dimensions: DimensionsSchema | None = None
    mounting_holes: list[MountingHoleSchema] | None = None
    connectors: list[ConnectorSchema] | None = None
    clearance_zones: list[ClearanceZoneSchema] | None = None
    thermal_properties: ThermalPropertiesSchema | None = None


class ComponentResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    name: str
    description: str | None
    category: str
    subcategory: str | None
    manufacturer: str | None
    model_number: str | None
    source_type: str
    thumbnail_url: str | None
    dimensions: dict[str, Any] | None
    mounting_holes: list[Any] | None
    connectors: list[Any] | None
    clearance_zones: list[Any] | None
    thermal_properties: dict[str, Any] | None
    extraction_status: str
    confidence_score: float | None
    is_verified: bool
    tags: list[Any]
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
    description: str | None
    category: str
    subcategory: str | None
    manufacturer: str | None
    model_number: str | None
    thumbnail_url: str | None
    dimensions: dict[str, Any] | None
    popularity_score: int
    usage_count: int
    is_featured: bool
    tags: list[Any]

    class Config:
        from_attributes = True


class ExtractionJobResponse(BaseModel):
    id: UUID
    component_id: UUID
    job_type: str
    status: str
    progress: int
    current_step: str | None
    confidence_score: float | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


# =============================================================================
# Component CRUD Endpoints
# =============================================================================


@router.post("", response_model=ComponentResponse, status_code=201)
async def create_component(
    data: ComponentCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ComponentResponse:
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


class ComponentUploadResponse(BaseModel):
    """Response from component file upload."""

    id: UUID
    name: str | None
    manufacturer: str | None
    model_number: str | None
    category: str
    specifications: dict[str, Any]
    extraction_status: str
    file_type: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/upload", response_model=ComponentUploadResponse, status_code=201)
async def upload_component(
    file: UploadFile = File(..., description="Component file (CAD, datasheet, image)"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ComponentUploadResponse:
    """
    Upload a component file for extraction.

    Accepts CAD files (STEP, STL, etc.), datasheets (PDF), or images.
    Automatically triggers specification extraction.
    """
    settings = get_settings()

    # Determine file type
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    cad_extensions = {".step", ".stp", ".stl", ".iges", ".igs", ".obj", ".3mf"}
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}

    if ext in cad_extensions:
        file_type = "cad"
    elif ext == ".pdf":
        file_type = "datasheet"
    elif ext in image_extensions:
        file_type = "image"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: CAD files, PDFs, images",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Check file size (50MB limit)
    max_size = 50 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB")

    checksum = hashlib.sha256(content).hexdigest()

    # Create component record
    component_id = uuid4()
    component = ReferenceComponent(
        id=component_id,
        user_id=current_user.id,
        name=Path(filename).stem,  # Use filename as initial name
        category="uncategorized",
        source_type=file_type,
        extraction_status="pending",
        tags=[],
    )

    db.add(component)
    await db.flush()

    # Upload file
    storage_prefix = f"components/{component_id}"
    storage_key = f"{storage_prefix}/{filename}"
    local_path = Path(settings.UPLOAD_DIR) / "components" / str(component_id) / filename

    try:
        await storage_client.upload_file(
            bucket=StorageBucket.UPLOADS,
            key=storage_key,
            file=content,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as e:
        logger.warning(f"MinIO upload failed, falling back to local: {e}")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open("wb") as f:
            f.write(content)

    # Store file metadata
    component.files_metadata = {
        f"{file_type}_file": {
            "filename": filename,
            "storage_key": storage_key,
            "size": file_size,
            "checksum": checksum,
            "format": ext.lstrip(".").upper(),
            "uploaded_at": datetime.now(tz=datetime.UTC).isoformat(),
        }
    }

    # Create extraction job
    extraction_job = ComponentExtractionJob(
        id=uuid4(),
        component_id=component_id,
        job_type=file_type,
        status="pending",
        progress=0,
    )
    db.add(extraction_job)

    await db.commit()
    await db.refresh(component)

    # Queue extraction task (async)
    try:
        from app.worker.tasks import extract_component_task

        extract_component_task.delay(str(extraction_job.id))
    except Exception as e:
        logger.warning(f"Failed to queue extraction task: {e}")

    return ComponentUploadResponse(
        id=component.id,
        name=component.name,
        manufacturer=component.manufacturer,
        model_number=component.model_number,
        category=component.category,
        specifications={},
        extraction_status=component.extraction_status,
        file_type=file_type,
        created_at=component.created_at,
    )


@router.get("", response_model=ComponentListResponse)
async def list_components(
    category: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ComponentListResponse:
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
    _current_user: User = Depends(get_current_user),
) -> ComponentResponse:
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
    _current_user: User = Depends(get_current_user),
) -> ComponentResponse:
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

    component.updated_at = datetime.now(tz=datetime.UTC)

    await db.commit()
    await db.refresh(component)

    return component


@router.put("/{component_id}/specifications", response_model=ComponentResponse)
async def update_specifications(
    component_id: UUID,
    data: SpecificationsUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ComponentResponse:
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
    component.updated_at = datetime.now(tz=datetime.UTC)

    await db.commit()
    await db.refresh(component)

    return component


class FileUpdateResponse(BaseModel):
    """Response after updating component files."""

    component_id: UUID
    message: str
    files_updated: int
    extraction_triggered: bool
    extraction_job_id: UUID | None = None


@router.put("/{component_id}/files", response_model=FileUpdateResponse)
async def update_component_files(
    component_id: UUID,
    cad_file: UploadFile | None = File(None, description="New CAD file (STEP, STL, IGES)"),
    datasheet: UploadFile | None = File(None, description="New datasheet PDF"),
    thumbnail: UploadFile | None = File(None, description="New thumbnail image"),
    trigger_extraction: bool = Query(True, description="Re-trigger AI extraction after upload"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> FileUpdateResponse:
    """
    Update CAD files for an existing component.

    Replaces existing files and optionally re-triggers AI extraction
    to update dimensions, mounting holes, and other specifications.
    """
    settings = get_settings()

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

    if not cad_file and not datasheet and not thumbnail:
        raise HTTPException(status_code=400, detail="At least one file must be provided")

    files_updated = 0
    storage_prefix = f"components/{component_id}"

    # Allowed extensions
    cad_extensions = {".step", ".stp", ".stl", ".iges", ".igs", ".obj", ".3mf"}
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}

    # Helper function to upload to storage with fallback
    async def upload_to_storage(
        key: str, content: bytes, content_type: str, local_path: Path
    ) -> str:
        """Upload to MinIO with local filesystem fallback."""
        try:
            await storage_client.upload_file(
                bucket=StorageBucket.UPLOADS,
                key=key,
                file=content,
                content_type=content_type,
            )
            logger.debug(f"Uploaded {key} to MinIO")
            return key
        except Exception as e:
            logger.warning(f"MinIO upload failed, falling back to local: {e}")
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with local_path.open("wb") as f:
                f.write(content)
            return str(local_path)

    # Process CAD file
    if cad_file:
        ext = Path(cad_file.filename or "").suffix.lower()
        if ext not in cad_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid CAD file type. Supported: {', '.join(cad_extensions)}",
            )

        content = await cad_file.read()
        checksum = hashlib.sha256(content).hexdigest()

        # Upload to storage
        storage_key = f"{storage_prefix}/model{ext}"
        local_path = Path(settings.UPLOAD_DIR) / "components" / str(component_id) / f"model{ext}"
        stored_path = await upload_to_storage(
            storage_key, content, cad_file.content_type or "application/octet-stream", local_path
        )

        # Update component metadata
        if not component.files_metadata:
            component.files_metadata = {}
        component.files_metadata["cad_file"] = {
            "filename": cad_file.filename,
            "storage_key": storage_key,
            "path": stored_path,
            "size": len(content),
            "checksum": checksum,
            "format": ext.lstrip(".").upper(),
            "updated_at": datetime.now(tz=datetime.UTC).isoformat(),
        }
        files_updated += 1

    # Process datasheet
    if datasheet:
        ext = Path(datasheet.filename or "").suffix.lower()
        if ext != ".pdf":
            raise HTTPException(status_code=400, detail="Datasheet must be a PDF file")

        content = await datasheet.read()
        checksum = hashlib.sha256(content).hexdigest()

        # Upload to storage
        storage_key = f"{storage_prefix}/datasheet.pdf"
        local_path = Path(settings.UPLOAD_DIR) / "components" / str(component_id) / "datasheet.pdf"
        stored_path = await upload_to_storage(storage_key, content, "application/pdf", local_path)

        if not component.files_metadata:
            component.files_metadata = {}
        component.files_metadata["datasheet"] = {
            "filename": datasheet.filename,
            "storage_key": storage_key,
            "path": stored_path,
            "size": len(content),
            "checksum": checksum,
            "updated_at": datetime.now(tz=datetime.UTC).isoformat(),
        }
        files_updated += 1

    # Process thumbnail
    if thumbnail:
        ext = Path(thumbnail.filename or "").suffix.lower()
        if ext not in image_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image type. Supported: {', '.join(image_extensions)}",
            )

        content = await thumbnail.read()
        content_type = thumbnail.content_type or f"image/{ext.lstrip('.')}"

        # Upload to storage
        storage_key = f"{storage_prefix}/thumbnail{ext}"
        local_path = (
            Path(settings.UPLOAD_DIR) / "components" / str(component_id) / f"thumbnail{ext}"
        )
        await upload_to_storage(storage_key, content, content_type, local_path)

        # Update thumbnail URL - use presigned URL or local path
        try:
            thumbnail_url = await storage_client.generate_presigned_download_url(
                bucket=StorageBucket.UPLOADS,
                key=storage_key,
                expires_in=86400 * 7,  # 7 days
            )
            component.thumbnail_url = thumbnail_url
        except Exception:
            component.thumbnail_url = f"/uploads/components/{component_id}/thumbnail{ext}"
        files_updated += 1

    component.updated_at = datetime.now(tz=datetime.UTC)

    # Trigger extraction if requested and CAD file or datasheet was updated
    extraction_job_id = None
    if trigger_extraction and (cad_file or datasheet):
        # Create extraction job
        extraction_job = ComponentExtractionJob(
            id=uuid4(),
            component_id=component_id,
            job_type="full" if (cad_file and datasheet) else ("cad" if cad_file else "datasheet"),
            status="pending",
            progress=0,
        )
        db.add(extraction_job)
        component.extraction_status = "pending"
        extraction_job_id = extraction_job.id

        # Queue Celery task for extraction
        from app.worker.tasks import extract_component_task

        extract_component_task.delay(str(extraction_job.id))

    await db.commit()

    return FileUpdateResponse(
        component_id=component_id,
        message=f"Successfully updated {files_updated} file(s)",
        files_updated=files_updated,
        extraction_triggered=trigger_extraction and (cad_file or datasheet) is not None,
        extraction_job_id=extraction_job_id,
    )


@router.delete("/{component_id}", status_code=204)
async def delete_component(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
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

    component.deleted_at = datetime.now(tz=datetime.UTC)
    await db.commit()


# =============================================================================
# Extraction Endpoints
# =============================================================================


@router.post("/{component_id}/extract", response_model=ExtractionJobResponse)
async def trigger_extraction(
    component_id: UUID,
    job_type: str = Query("full", regex="^(datasheet|cad|full)$"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ExtractionJobResponse:
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

    # Queue background task for extraction
    from app.worker.tasks import extract_component_task

    extract_component_task.delay(str(job.id))

    return job


@router.get("/{component_id}/extraction-status", response_model=ExtractionJobResponse)
async def get_extraction_status(
    component_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ExtractionJobResponse | None:
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
    category: str | None = None,
    subcategory: str | None = None,
    manufacturer: str | None = None,
    search: str | None = None,
    featured: bool | None = None,
    sort_by: str = Query("popularity", regex="^(popularity|name|newest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> LibrarySearchResponse:
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
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
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
    _current_user: User = Depends(get_current_user),
) -> ComponentResponse:
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

    # Cast to ComponentResponse as it matches the schema via from_attributes
    return cast(ComponentResponse, entry.component)


@library_router.post("/{library_id}/add")
async def add_library_component_to_project(
    library_id: UUID,
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
    """Seed the component library with popular components. Admin only."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    from uuid import uuid4

    from app.db.seeds.component_library import CATEGORIES, COMPONENT_LIBRARY

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
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
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
