"""
Design Annotations API endpoints.

Provides CRUD operations for 3D annotations on designs.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models import (
    AnnotationStatus,
    AnnotationType,
    Design,
    DesignAnnotation,
    User,
)

router = APIRouter(prefix="/designs/{design_id}/annotations", tags=["annotations"])


# --- Schemas ---


class Position3D(BaseModel):
    """3D position schema."""

    x: float
    y: float
    z: float


class AnnotationCreate(BaseModel):
    """Schema for creating an annotation."""

    position: Position3D
    normal: Position3D | None = None
    camera_position: Position3D | None = None
    camera_target: Position3D | None = None
    content: str = Field(..., min_length=1, max_length=10000)
    annotation_type: AnnotationType = AnnotationType.NOTE
    parent_id: UUID | None = None
    priority: int = Field(default=0, ge=0, le=3)
    tags: list[str] | None = None


class AnnotationUpdate(BaseModel):
    """Schema for updating an annotation."""

    content: str | None = Field(None, min_length=1, max_length=10000)
    annotation_type: AnnotationType | None = None
    priority: int | None = Field(None, ge=0, le=3)
    tags: list[str] | None = None


class AnnotationResolve(BaseModel):
    """Schema for resolving an annotation."""

    status: AnnotationStatus = AnnotationStatus.RESOLVED
    resolution_note: str | None = Field(None, max_length=2000)


class AnnotationResponse(BaseModel):
    """Schema for annotation response."""

    id: UUID
    design_id: UUID
    user_id: UUID
    parent_id: UUID | None
    position: dict
    normal: dict | None
    camera_position: dict | None
    camera_target: dict | None
    content: str
    annotation_type: str
    status: str
    priority: int
    tags: list[str]
    resolved_by_id: UUID | None
    resolved_at: str | None
    resolution_note: str | None
    created_at: str
    updated_at: str
    reply_count: int
    is_resolved: bool
    user_name: str | None = None

    class Config:
        from_attributes = True


class AnnotationListResponse(BaseModel):
    """Schema for annotation list response."""

    items: list[AnnotationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# --- Helper Functions ---


async def get_design_or_404(
    design_id: UUID,
    db: AsyncSession,
    user: User,
) -> Design:
    """Get design or raise 404, checking access permissions."""
    result = await db.execute(
        select(Design).where(Design.id == design_id).options(selectinload(Design.project))
    )
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    # Check access (owner or public or shared)
    if design.project.user_id != user.id and not design.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this design",
        )

    return design


async def get_annotation_or_404(
    annotation_id: UUID,
    db: AsyncSession,
) -> DesignAnnotation:
    """Get annotation or raise 404."""
    result = await db.execute(
        select(DesignAnnotation)
        .where(DesignAnnotation.id == annotation_id)
        .options(selectinload(DesignAnnotation.user))
    )
    annotation = result.scalar_one_or_none()

    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found",
        )

    return annotation


def annotation_to_response(annotation: DesignAnnotation) -> AnnotationResponse:
    """Convert annotation to response schema."""
    return AnnotationResponse(
        id=annotation.id,
        design_id=annotation.design_id,
        user_id=annotation.user_id,
        parent_id=annotation.parent_id,
        position=annotation.position,
        normal=annotation.normal,
        camera_position=annotation.camera_position,
        camera_target=annotation.camera_target,
        content=annotation.content,
        annotation_type=annotation.annotation_type.value,
        status=annotation.status.value,
        priority=annotation.priority,
        tags=annotation.tags or [],
        resolved_by_id=annotation.resolved_by_id,
        resolved_at=annotation.resolved_at.isoformat() if annotation.resolved_at else None,
        resolution_note=annotation.resolution_note,
        created_at=annotation.created_at.isoformat(),
        updated_at=annotation.updated_at.isoformat(),
        reply_count=annotation.reply_count,
        is_resolved=annotation.is_resolved,
        user_name=annotation.user.display_name if annotation.user else None,
    )


# --- Endpoints ---


@router.post("", response_model=AnnotationResponse, status_code=status.HTTP_201_CREATED)
async def create_annotation(
    design_id: UUID,
    data: AnnotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new annotation on a design."""
    await get_design_or_404(design_id, db, current_user)

    # If this is a reply, verify parent exists and belongs to same design
    if data.parent_id:
        parent = await get_annotation_or_404(data.parent_id, db)
        if parent.design_id != design_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent annotation belongs to a different design",
            )

    annotation = DesignAnnotation(
        design_id=design_id,
        user_id=current_user.id,
        parent_id=data.parent_id,
        position=data.position.dict(),
        normal=data.normal.dict() if data.normal else None,
        camera_position=data.camera_position.dict() if data.camera_position else None,
        camera_target=data.camera_target.dict() if data.camera_target else None,
        content=data.content,
        annotation_type=data.annotation_type,
        priority=data.priority,
        tags=data.tags,
    )

    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)

    # Load user relationship
    result = await db.execute(
        select(DesignAnnotation)
        .where(DesignAnnotation.id == annotation.id)
        .options(selectinload(DesignAnnotation.user))
    )
    annotation = result.scalar_one()

    return annotation_to_response(annotation)


@router.get("", response_model=AnnotationListResponse)
async def list_annotations(
    design_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    annotation_type: AnnotationType | None = None,
    status_filter: AnnotationStatus | None = Query(None, alias="status"),
    include_replies: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List annotations for a design."""
    await get_design_or_404(design_id, db, current_user)

    # Build query
    conditions = [DesignAnnotation.design_id == design_id]

    if not include_replies:
        conditions.append(DesignAnnotation.parent_id.is_(None))

    if annotation_type:
        conditions.append(DesignAnnotation.annotation_type == annotation_type)

    if status_filter:
        conditions.append(DesignAnnotation.status == status_filter)

    # Count total
    count_result = await db.execute(select(DesignAnnotation.id).where(and_(*conditions)))
    total = len(count_result.all())

    # Get page
    offset = (page - 1) * page_size
    result = await db.execute(
        select(DesignAnnotation)
        .where(and_(*conditions))
        .options(
            selectinload(DesignAnnotation.user),
            selectinload(DesignAnnotation.replies),
        )
        .order_by(DesignAnnotation.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    annotations = result.scalars().all()

    return AnnotationListResponse(
        items=[annotation_to_response(a) for a in annotations],
        total=total,
        page=page,
        page_size=page_size,
        has_more=offset + len(annotations) < total,
    )


@router.get("/{annotation_id}", response_model=AnnotationResponse)
async def get_annotation(
    design_id: UUID,
    annotation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific annotation."""
    await get_design_or_404(design_id, db, current_user)
    annotation = await get_annotation_or_404(annotation_id, db)

    if annotation.design_id != design_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found in this design",
        )

    return annotation_to_response(annotation)


@router.patch("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    design_id: UUID,
    annotation_id: UUID,
    data: AnnotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an annotation. Only the author can update."""
    await get_design_or_404(design_id, db, current_user)
    annotation = await get_annotation_or_404(annotation_id, db)

    if annotation.design_id != design_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found in this design",
        )

    # Only author can edit
    if annotation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the author can edit this annotation",
        )

    # Update fields
    if data.content is not None:
        annotation.content = data.content
    if data.annotation_type is not None:
        annotation.annotation_type = data.annotation_type
    if data.priority is not None:
        annotation.priority = data.priority
    if data.tags is not None:
        annotation.tags = data.tags

    await db.commit()
    await db.refresh(annotation)

    return annotation_to_response(annotation)


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_annotation(
    design_id: UUID,
    annotation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an annotation. Only the author can delete."""
    await get_design_or_404(design_id, db, current_user)
    annotation = await get_annotation_or_404(annotation_id, db)

    if annotation.design_id != design_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found in this design",
        )

    # Only author can delete
    if annotation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the author can delete this annotation",
        )

    await db.delete(annotation)
    await db.commit()


@router.post("/{annotation_id}/resolve", response_model=AnnotationResponse)
async def resolve_annotation(
    design_id: UUID,
    annotation_id: UUID,
    data: AnnotationResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve an annotation."""
    await get_design_or_404(design_id, db, current_user)
    annotation = await get_annotation_or_404(annotation_id, db)

    if annotation.design_id != design_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found in this design",
        )

    # Anyone with access can resolve (author or design owner)
    annotation.resolve(
        user_id=current_user.id,
        note=data.resolution_note,
        status=data.status,
    )

    await db.commit()
    await db.refresh(annotation)

    return annotation_to_response(annotation)


@router.post("/{annotation_id}/reopen", response_model=AnnotationResponse)
async def reopen_annotation(
    design_id: UUID,
    annotation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reopen a resolved annotation."""
    await get_design_or_404(design_id, db, current_user)
    annotation = await get_annotation_or_404(annotation_id, db)

    if annotation.design_id != design_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found in this design",
        )

    if not annotation.is_resolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Annotation is not resolved",
        )

    annotation.reopen()

    await db.commit()
    await db.refresh(annotation)

    return annotation_to_response(annotation)


@router.get("/{annotation_id}/replies", response_model=list[AnnotationResponse])
async def get_annotation_replies(
    design_id: UUID,
    annotation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get replies to an annotation."""
    await get_design_or_404(design_id, db, current_user)
    annotation = await get_annotation_or_404(annotation_id, db)

    if annotation.design_id != design_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found in this design",
        )

    # Get replies
    result = await db.execute(
        select(DesignAnnotation)
        .where(DesignAnnotation.parent_id == annotation_id)
        .options(selectinload(DesignAnnotation.user))
        .order_by(DesignAnnotation.created_at.asc())
    )
    replies = result.scalars().all()

    return [annotation_to_response(r) for r in replies]
