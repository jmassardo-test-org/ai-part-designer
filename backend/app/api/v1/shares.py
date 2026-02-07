"""
Sharing API endpoints.

Handles design sharing, permission management, and shared design access.

DEPRECATED: This module is deprecated as of v2.0.
Use the new Marketplace (/api/v2/marketplace), Lists (/api/v2/lists),
and Saves (/api/v2/saves) endpoints instead.

Migration guide:
- Share publicly → Publish to Marketplace (POST /api/v2/marketplace/designs/{id}/publish)
- Share with users → Use Design Lists (POST /api/v2/lists/{list_id}/items)
- Save designs → Use Saves (POST /api/v2/saves/{design_id})

These endpoints will be removed in a future version.
"""

import warnings
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit_log
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Design, DesignShare, User
from app.models.audit import AuditActions

# Emit deprecation warning when this module is imported
warnings.warn(
    "The shares API (v1) is deprecated. Use marketplace, lists, and saves APIs (v2) instead.",
    DeprecationWarning,
    stacklevel=2,
)

router = APIRouter(
    prefix="/shares",
    tags=["shares (deprecated)"],
    deprecated=True,
)


# =============================================================================
# Schemas
# =============================================================================


class ShareRequest(BaseModel):
    """Request to share a design."""

    email: EmailStr
    permission: str = Field(
        default="view",
        pattern="^(view|comment|edit)$",
        description="Permission level: view, comment, or edit",
    )
    message: str | None = Field(None, max_length=500)


class ShareResponse(BaseModel):
    """Share response."""

    id: UUID
    design_id: UUID
    shared_with_id: UUID
    shared_with_email: str
    shared_with_name: str
    permission: str
    shared_at: datetime

    class Config:
        from_attributes = True


class SharedDesignResponse(BaseModel):
    """Design shared with the current user."""

    id: UUID
    design_id: UUID
    design_name: str
    design_thumbnail_url: str | None
    shared_by_id: UUID
    shared_by_name: str
    shared_by_email: str
    permission: str
    shared_at: datetime


class ShareLinkRequest(BaseModel):
    """Request to create a share link."""

    permission: str = Field(
        default="view",
        pattern="^(view|comment)$",
        description="Permission for link: view or comment (not edit)",
    )
    expires_in_days: int | None = Field(None, ge=1, le=30)


class ShareLinkResponse(BaseModel):
    """Share link response."""

    link: str
    token: str
    permission: str
    expires_at: datetime | None


class UpdateShareRequest(BaseModel):
    """Request to update share permission."""

    permission: str = Field(pattern="^(view|comment|edit)$", description="New permission level")


class PaginatedSharesResponse(BaseModel):
    """Paginated list of shares."""

    items: list[ShareResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class PaginatedSharedWithMeResponse(BaseModel):
    """Paginated list of designs shared with user."""

    items: list[SharedDesignResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/designs/{design_id}", response_model=ShareResponse, status_code=status.HTTP_201_CREATED
)
@audit_log(
    action=AuditActions.SHARE,
    resource_type="design",
    resource_id_param="design_id",
    context_builder=lambda **kwargs: {
        "shared_with_email": kwargs["request"].email,
        "permission": kwargs["request"].permission,
    },
)
async def share_design(
    design_id: UUID,
    request: ShareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareResponse:
    """
    Share a design with another user by email.

    - **email**: Email of user to share with
    - **permission**: view, comment, or edit
    - **message**: Optional message to include in notification
    """
    # Get the design
    result = await db.execute(
        select(Design).where(
            and_(
                Design.id == design_id,
                Design.deleted_at.is_(None),
            )
        )
    )
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    # Check ownership via project
    from app.models import Project

    result = await db.execute(select(Project).where(Project.id == design.project_id))
    project = result.scalar_one_or_none()

    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to share this design",
        )

    # Find user to share with
    result = await db.execute(select(User).where(User.email == request.email))
    share_with_user = result.scalar_one_or_none()

    if not share_with_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with that email not found",
        )

    if share_with_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share a design with yourself",
        )

    # Check if already shared
    result = await db.execute(
        select(DesignShare).where(
            and_(
                DesignShare.design_id == design_id,
                DesignShare.shared_with_user_id == share_with_user.id,
            )
        )
    )
    existing_share = result.scalar_one_or_none()

    if existing_share:
        # Update permission
        existing_share.permission = request.permission # type: ignore[attr-defined]
        existing_share.updated_at = datetime.now(tz=UTC)
        await db.commit()
        await db.refresh(existing_share)

        return ShareResponse(
            id=existing_share.id,
            design_id=existing_share.design_id, # type: ignore[attr-defined]
            shared_with_id=share_with_user.id,
            shared_with_email=share_with_user.email, # type: ignore[attr-defined]
            shared_with_name=share_with_user.display_name or share_with_user.email, # type: ignore[attr-defined]
            permission=existing_share.permission, # type: ignore[attr-defined]
            shared_at=existing_share.created_at,
        )

    # Create new share
    share = DesignShare(
        design_id=design_id,
        shared_by_user_id=current_user.id,
        shared_with_user_id=share_with_user.id,
        permission=request.permission,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    # TODO: Send notification email with request.message

    return ShareResponse(
        id=share.id,
        design_id=share.design_id,
        shared_with_id=share_with_user.id,
        shared_with_email=share_with_user.email, # type: ignore[attr-defined]
        shared_with_name=share_with_user.display_name or share_with_user.email, # type: ignore[attr-defined]
        permission=share.permission,
        shared_at=share.created_at,
    )


@router.get("/designs/{design_id}", response_model=PaginatedSharesResponse)
async def list_design_shares(
    design_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedSharesResponse:
    """List all shares for a design."""
    # Get design and verify ownership via project
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    from app.models import Project

    result = await db.execute(select(Project).where(Project.id == design.project_id))
    project = result.scalar_one_or_none()

    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view shares for this design",
        )

    # Get shares with user info
    offset = (page - 1) * page_size

    result = await db.execute(
        select(DesignShare, User)
        .join(User, DesignShare.shared_with_user_id == User.id)
        .where(DesignShare.design_id == design_id)
        .order_by(DesignShare.created_at.desc())
        .offset(offset)
        .limit(page_size + 1)
    )
    rows = result.all()

    has_more = len(rows) > page_size
    rows = rows[:page_size]

    # Get total count
    count_result = await db.execute(select(DesignShare).where(DesignShare.design_id == design_id))
    total = len(count_result.scalars().all())

    items = [
        ShareResponse(
            id=share.id,
            design_id=share.design_id,
            shared_with_id=user.id,
            shared_with_email=user.email,
            shared_with_name=user.display_name or user.email,
            permission=share.permission,
            shared_at=share.created_at,
        )
        for share, user in rows
    ]

    return PaginatedSharesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/shared-with-me", response_model=PaginatedSharedWithMeResponse)
async def get_shared_with_me(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    permission: str | None = Query(None, pattern="^(view|comment|edit)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedSharedWithMeResponse:
    """Get designs shared with the current user."""
    offset = (page - 1) * page_size

    # Build query - use deleted_at.is_(None) for soft delete check
    query = (
        select(DesignShare, Design, User)
        .join(Design, DesignShare.design_id == Design.id)
        .join(User, DesignShare.shared_by_user_id == User.id)
        .where(
            and_(
                DesignShare.shared_with_user_id == current_user.id,
                Design.deleted_at.is_(None),
            )
        )
    )

    if permission:
        query = query.where(DesignShare.permission == permission)

    query = query.order_by(DesignShare.created_at.desc()).offset(offset).limit(page_size + 1)

    result = await db.execute(query)
    rows = result.all()

    has_more = len(rows) > page_size
    rows = rows[:page_size]

    # Get total count
    count_query = (
        select(DesignShare)
        .join(Design, DesignShare.design_id == Design.id)
        .where(
            and_(
                DesignShare.shared_with_user_id == current_user.id,
                Design.deleted_at.is_(None),
            )
        )
    )
    if permission:
        count_query = count_query.where(DesignShare.permission == permission)

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    # Get thumbnails from current version
    items = []
    for share, design, user in rows:
        thumbnail_url = None
        if design.current_version_id:
            from app.models import DesignVersion

            version_result = await db.execute(
                select(DesignVersion).where(DesignVersion.id == design.current_version_id)
            )
            version = version_result.scalar_one_or_none()
            if version:
                thumbnail_url = version.thumbnail_url

        items.append(
            SharedDesignResponse(
                id=share.id,
                design_id=design.id,
                design_name=design.name,
                design_thumbnail_url=thumbnail_url,
                shared_by_id=user.id,
                shared_by_name=user.display_name or user.email,
                shared_by_email=user.email,
                permission=share.permission,
                shared_at=share.created_at,
            )
        )

    return PaginatedSharedWithMeResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.patch("/{share_id}", response_model=ShareResponse)
@audit_log(
    action=AuditActions.UPDATE,
    resource_type="share",
    resource_id_param="share_id",
    context_builder=lambda **kwargs: {
        "permission": kwargs["request"].permission,
    },
)
async def update_share(
    share_id: UUID,
    request: UpdateShareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareResponse:
    """Update a share's permission level."""
    # Get share with design info
    result = await db.execute(
        select(DesignShare, Design, User)
        .join(Design, DesignShare.design_id == Design.id)
        .join(User, DesignShare.shared_with_user_id == User.id)
        .where(DesignShare.id == share_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )

    share, design, shared_with_user = row

    # Check ownership via project
    from app.models import Project

    result = await db.execute(select(Project).where(Project.id == design.project_id))
    project = result.scalar_one_or_none()

    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this share",
        )

    # Update permission
    share.permission = request.permission
    share.updated_at = datetime.now(tz=UTC)
    await db.commit()
    await db.refresh(share)

    return ShareResponse(
        id=share.id,
        design_id=share.design_id,
        shared_with_id=shared_with_user.id,
        shared_with_email=shared_with_user.email,
        shared_with_name=shared_with_user.display_name or shared_with_user.email,
        permission=share.permission,
        shared_at=share.created_at,
    )


@router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
@audit_log(
    action=AuditActions.UNSHARE,
    resource_type="share",
    resource_id_param="share_id",
)
async def revoke_share(
    share_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke a share (remove access)."""
    # Get share with design info
    result = await db.execute(
        select(DesignShare, Design)
        .join(Design, DesignShare.design_id == Design.id)
        .where(DesignShare.id == share_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )

    share, design = row

    # Check ownership via project or if user is removing their own access
    from app.models import Project

    result = await db.execute(select(Project).where(Project.id == design.project_id))
    project = result.scalar_one_or_none()

    is_owner = project and project.user_id == current_user.id
    is_shared_with = share.shared_with_user_id == current_user.id

    if not is_owner and not is_shared_with:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to revoke this share",
        )

    await db.delete(share)
    await db.commit()


@router.post("/designs/{design_id}/link", response_model=ShareLinkResponse)
async def create_share_link(
    design_id: UUID,
    request: ShareLinkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ShareLinkResponse:
    """
    Create a shareable link for a design.

    Anyone with the link can access the design with the specified permission.
    """
    import secrets
    from datetime import timedelta

    # Get design and verify ownership
    result = await db.execute(
        select(Design).where(
            and_(
                Design.id == design_id,
                Design.deleted_at.is_(None),
            )
        )
    )
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    from app.models import Project

    result = await db.execute(select(Project).where(Project.id == design.project_id))
    project = result.scalar_one_or_none()

    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create a share link for this design",
        )

    # Generate token
    token = secrets.token_urlsafe(32)

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(tz=UTC) + timedelta(days=request.expires_in_days)

    # Create link share record
    link_share = DesignShare(
        design_id=design_id,
        shared_by_user_id=current_user.id,
        shared_with_user_id=None,  # Link share, no specific user
        permission=request.permission,
        share_token=token,
        is_link_share=True,
        expires_at=expires_at,
    )
    db.add(link_share)
    await db.commit()

    # Build link
    base_url = "https://app.aipartdesigner.com"  # TODO: Get from config
    link = f"{base_url}/shared/{design_id}?token={token}"

    return ShareLinkResponse(
        link=link,
        token=token,
        permission=request.permission,
        expires_at=expires_at,
    )


@router.delete("/designs/{design_id}/link", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share_link(
    design_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke all share links for a design."""
    # Get design and verify ownership
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()

    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design not found",
        )

    from app.models import Project

    result = await db.execute(select(Project).where(Project.id == design.project_id))
    project = result.scalar_one_or_none()

    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to revoke share links for this design",
        )

    # Delete all link shares
    result = await db.execute(
        select(DesignShare).where(
            and_(
                DesignShare.design_id == design_id,
                DesignShare.is_link_share,
            )
        )
    )
    link_shares = result.scalars().all()

    for share in link_shares:
        await db.delete(share)

    await db.commit()
