"""
Organization API endpoints.

Handles organization CRUD, membership management,
invitations, and settings.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.organization import (
    InviteStatus,
    Organization,
    OrganizationAuditLog,
    OrganizationCreditBalance,
    OrganizationInvite,
    OrganizationMember,
    OrganizationRole,
)
from app.models.user import User

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class OrganizationCreate(BaseModel):
    """Request to create an organization."""

    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    description: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v) and len(v) > 2:
            raise ValueError("Slug must start and end with alphanumeric characters")
        return v.lower()


class OrganizationUpdate(BaseModel):
    """Request to update organization."""

    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = None
    logo_url: str | None = None
    settings: dict[str, Any] | None = None


class OrganizationResponse(BaseModel):
    """Organization details response."""

    id: UUID
    name: str
    slug: str
    description: str | None
    logo_url: str | None
    owner_id: UUID
    subscription_tier: str
    max_members: int
    max_projects: int
    member_count: int
    settings: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    """Organization member details."""

    id: UUID
    user_id: UUID
    email: str
    display_name: str
    role: str
    joined_at: datetime
    invited_by_name: str | None = None


class InviteMemberRequest(BaseModel):
    """Request to invite a member."""

    email: EmailStr
    role: str = Field(default="member")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = [r.value for r in OrganizationRole if r != OrganizationRole.OWNER]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class InviteResponse(BaseModel):
    """Invitation details."""

    id: UUID
    email: str
    role: str
    status: str
    expires_at: datetime
    invited_by_name: str
    created_at: datetime


class ChangeRoleRequest(BaseModel):
    """Request to change member role."""

    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = [r.value for r in OrganizationRole if r != OrganizationRole.OWNER]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class TransferOwnershipRequest(BaseModel):
    """Request to transfer organization ownership."""

    new_owner_id: UUID


class AcceptInviteRequest(BaseModel):
    """Request to accept an invitation."""

    token: str


# =============================================================================
# Helper Functions
# =============================================================================


async def get_org_or_404(
    db: AsyncSession,
    org_id: UUID,
) -> Organization:
    """Get organization by ID or raise 404."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id, Organization.deleted_at.is_(None))
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return org


async def get_membership(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
) -> OrganizationMember | None:
    """Get user's membership in organization."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active,
        )
    )
    return result.scalar_one_or_none()


async def require_org_role(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    min_role: OrganizationRole,
) -> OrganizationMember:
    """Require user has at least the specified role."""
    membership = await get_membership(db, org_id, user_id)

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    if not membership.has_permission(min_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {min_role.value} role or higher",
        )

    return membership


async def log_org_action(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Log an organization action for audit."""
    log = OrganizationAuditLog(
        organization_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
    db.add(log)


# =============================================================================
# Organization CRUD
# =============================================================================


@router.post("/organizations", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    request: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """
    Create a new organization.

    The creating user becomes the owner.
    """
    # Check slug uniqueness
    result = await db.execute(select(Organization).where(Organization.slug == request.slug))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already taken",
        )

    # Create organization
    org = Organization(
        name=request.name,
        slug=request.slug,
        description=request.description,
        owner_id=current_user.id,
    )
    db.add(org)
    await db.flush()

    # Add owner as member
    owner_member = OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
        role=OrganizationRole.OWNER.value,
        joined_at=datetime.now(tz=UTC),
    )
    db.add(owner_member)

    # Create credit balance
    credit_balance = OrganizationCreditBalance(
        organization_id=org.id,
        balance=0,
    )
    db.add(credit_balance)

    # Log action
    await log_org_action(
        db,
        org.id,
        current_user.id,
        "organization_created",
        details={"name": org.name, "slug": org.slug},
    )

    await db.commit()
    await db.refresh(org)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        subscription_tier=org.subscription_tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        member_count=1,
        settings=org.settings,
        created_at=org.created_at,
    )


@router.get("/organizations", response_model=list[OrganizationResponse])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrganizationResponse]:
    """
    List organizations the user is a member of.
    """
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active,
            Organization.deleted_at.is_(None),
        )
        .order_by(Organization.name)
    )
    orgs = result.scalars().all()

    responses = []
    for org in orgs:
        # Get member count
        count_result = await db.execute(
            select(func.count())
            .select_from(OrganizationMember)
            .where(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.is_active,
            )
        )
        member_count = count_result.scalar() or 0

        responses.append(
            OrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                description=org.description,
                logo_url=org.logo_url,
                owner_id=org.owner_id,
                subscription_tier=org.subscription_tier,
                max_members=org.max_members,
                max_projects=org.max_projects,
                member_count=member_count,
                settings=org.settings,
                created_at=org.created_at,
            )
        )

    return responses


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """
    Get organization details.
    """
    org = await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.VIEWER)

    # Get member count
    count_result = await db.execute(
        select(func.count())
        .select_from(OrganizationMember)
        .where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active,
        )
    )
    member_count = count_result.scalar() or 0

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        subscription_tier=org.subscription_tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        member_count=member_count,
        settings=org.settings,
        created_at=org.created_at,
    )


@router.patch("/organizations/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    request: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """
    Update organization details.

    Requires admin role.
    """
    org = await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.ADMIN)

    # Update fields
    if request.name is not None:
        org.name = request.name
    if request.description is not None:
        org.description = request.description
    if request.logo_url is not None:
        org.logo_url = request.logo_url
    if request.settings is not None:
        org.settings = {**org.settings, **request.settings}

    await log_org_action(
        db,
        org_id,
        current_user.id,
        "organization_updated",
        details={"updates": request.model_dump(exclude_unset=True)},
    )

    await db.commit()
    await db.refresh(org)

    count_result = await db.execute(
        select(func.count())
        .select_from(OrganizationMember)
        .where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active,
        )
    )
    member_count = count_result.scalar() or 0

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        subscription_tier=org.subscription_tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        member_count=member_count,
        settings=org.settings,
        created_at=org.created_at,
    )


@router.delete("/organizations/{org_id}", status_code=204)
async def delete_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete an organization.

    Requires owner role.
    """
    org = await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.OWNER)

    # Soft delete
    org.deleted_at = datetime.now(tz=UTC)

    await log_org_action(
        db,
        org_id,
        current_user.id,
        "organization_deleted",
    )

    await db.commit()


# =============================================================================
# Feature Permissions
# =============================================================================


class UpdateFeaturesRequest(BaseModel):
    """Request to update enabled features."""

    enabled_features: list[str] = Field(
        description="List of feature identifiers to enable for this organization"
    )

    @field_validator("enabled_features")
    @classmethod
    def validate_features(cls, v: list[str]) -> list[str]:
        from app.core.features import get_all_features

        all_features = get_all_features()
        invalid = [f for f in v if f not in all_features]
        if invalid:
            raise ValueError(f"Invalid features: {', '.join(invalid)}")
        return v


class FeaturesResponse(BaseModel):
    """Response with organization features."""

    enabled_features: list[str]
    available_features: list[str]
    subscription_tier: str


@router.get("/organizations/{org_id}/features", response_model=FeaturesResponse)
async def get_organization_features(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeaturesResponse:
    """
    Get enabled and available features for an organization.
    
    Returns the list of currently enabled features and all features
    available for the organization's subscription tier.
    """
    from app.core.features import get_all_features, get_default_features

    org = await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.VIEWER)

    # Get available features for the tier
    available_features = get_default_features(org.subscription_tier)

    return FeaturesResponse(
        enabled_features=org.enabled_features,
        available_features=available_features,
        subscription_tier=org.subscription_tier,
    )


@router.put("/organizations/{org_id}/features", response_model=FeaturesResponse)
async def update_organization_features(
    org_id: UUID,
    request: UpdateFeaturesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeaturesResponse:
    """
    Update enabled features for an organization.
    
    Requires admin role. Can only enable features that are included
    in the organization's subscription tier.
    """
    from app.core.features import get_default_features

    org = await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.ADMIN)

    # Get features available for this tier
    available_features = get_default_features(org.subscription_tier)

    # Validate requested features are available for tier
    invalid_features = [f for f in request.enabled_features if f not in available_features]
    if invalid_features:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_features",
                "message": f"Features not available on {org.subscription_tier} tier: {', '.join(invalid_features)}",
                "invalid_features": invalid_features,
            },
        )

    # Update settings
    org.settings = {**org.settings, "enabled_features": request.enabled_features}

    await log_org_action(
        db,
        org_id,
        current_user.id,
        "features_updated",
        resource_type="settings",
        details={
            "enabled_features": request.enabled_features,
        },
    )

    await db.commit()
    await db.refresh(org)

    return FeaturesResponse(
        enabled_features=org.enabled_features,
        available_features=available_features,
        subscription_tier=org.subscription_tier,
    )


# =============================================================================
# Member Management
# =============================================================================


@router.get("/organizations/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MemberResponse]:
    """
    List organization members.
    """
    await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.VIEWER)

    result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .options(selectinload(OrganizationMember.invited_by))
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active,
        )
        .order_by(OrganizationMember.joined_at)
    )
    members = result.scalars().all()

    return [
        MemberResponse(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email,
            display_name=m.user.display_name,
            role=m.role,
            joined_at=m.joined_at,
            invited_by_name=m.invited_by.display_name if m.invited_by else None,
        )
        for m in members
    ]


@router.patch("/organizations/{org_id}/members/{member_id}/role")
async def change_member_role(
    org_id: UUID,
    member_id: UUID,
    request: ChangeRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberResponse:
    """
    Change a member's role.

    Requires admin role. Cannot change owner's role.
    """
    await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.ADMIN)

    result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == org_id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if member.role == OrganizationRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change owner's role. Use transfer ownership instead.",
        )

    old_role = member.role
    member.role = request.role

    await log_org_action(
        db,
        org_id,
        current_user.id,
        "member_role_changed",
        resource_type="member",
        resource_id=member_id,
        details={"old_role": old_role, "new_role": request.role},
    )

    await db.commit()

    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=member.user.email,
        display_name=member.user.display_name,
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/organizations/{org_id}/members/{member_id}", status_code=204)
async def remove_member(
    org_id: UUID,
    member_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Remove a member from organization.

    Requires admin role. Cannot remove owner.
    """
    await get_org_or_404(db, org_id)
    actor = await require_org_role(db, org_id, current_user.id, OrganizationRole.ADMIN)

    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == org_id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if member.role == OrganizationRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove organization owner",
        )

    # Members can remove themselves
    if member.user_id != current_user.id and not actor.has_permission(OrganizationRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove other members",
        )

    member.is_active = False

    await log_org_action(
        db,
        org_id,
        current_user.id,
        "member_removed",
        resource_type="member",
        resource_id=member_id,
    )

    await db.commit()


@router.post("/organizations/{org_id}/transfer-ownership")
async def transfer_ownership(
    org_id: UUID,
    request: TransferOwnershipRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """
    Transfer organization ownership to another member.

    Requires owner role.
    """
    org = await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.OWNER)

    # Find new owner's membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == request.new_owner_id,
            OrganizationMember.is_active,
        )
    )
    new_owner_member = result.scalar_one_or_none()

    if not new_owner_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New owner must be an existing member",
        )

    # Get current owner's membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    current_owner_member = result.scalar_one()

    # Transfer
    current_owner_member.role = OrganizationRole.ADMIN.value
    new_owner_member.role = OrganizationRole.OWNER.value
    org.owner_id = request.new_owner_id

    await log_org_action(
        db,
        org_id,
        current_user.id,
        "ownership_transferred",
        details={"new_owner_id": str(request.new_owner_id)},
    )

    await db.commit()
    await db.refresh(org)

    count_result = await db.execute(
        select(func.count())
        .select_from(OrganizationMember)
        .where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active,
        )
    )
    member_count = count_result.scalar() or 0

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        subscription_tier=org.subscription_tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        member_count=member_count,
        settings=org.settings,
        created_at=org.created_at,
    )


# =============================================================================
# Invitations
# =============================================================================


@router.post("/organizations/{org_id}/invites", response_model=InviteResponse, status_code=201)
async def invite_member(
    org_id: UUID,
    request: InviteMemberRequest,
    _background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InviteResponse:
    """
    Invite a new member by email.

    Requires admin role.
    """
    org = await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.ADMIN)

    # Check member limit
    count_result = await db.execute(
        select(func.count())
        .select_from(OrganizationMember)
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active,
        )
    )
    member_count = count_result.scalar() or 0

    if member_count >= org.max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization has reached member limit ({org.max_members})",
        )

    # Check if already a member
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        existing_member = await get_membership(db, org_id, existing_user.id)
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member",
            )

    # Check for pending invite
    result = await db.execute(
        select(OrganizationInvite).where(
            OrganizationInvite.organization_id == org_id,
            OrganizationInvite.email == request.email,
            OrganizationInvite.status == InviteStatus.PENDING.value,
        )
    )
    existing_invite = result.scalar_one_or_none()

    if existing_invite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pending invitation already exists for this email",
        )

    # Create invite
    invite = OrganizationInvite(
        organization_id=org_id,
        invited_by_id=current_user.id,
        email=request.email,
        role=request.role,
    )
    db.add(invite)

    await log_org_action(
        db,
        org_id,
        current_user.id,
        "member_invited",
        resource_type="invite",
        resource_id=invite.id,
        details={"email": request.email, "role": request.role},
    )

    await db.commit()
    await db.refresh(invite)

    # TODO: Implement background email sending for invitation notifications

    return InviteResponse(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        status=invite.status,
        expires_at=invite.expires_at,
        invited_by_name=current_user.display_name,
        created_at=invite.created_at,
    )


@router.get("/organizations/{org_id}/invites", response_model=list[InviteResponse])
async def list_invites(
    org_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InviteResponse]:
    """
    List pending invitations.
    """
    await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.ADMIN)

    result = await db.execute(
        select(OrganizationInvite)
        .options(selectinload(OrganizationInvite.invited_by))
        .where(
            OrganizationInvite.organization_id == org_id,
            OrganizationInvite.status == InviteStatus.PENDING.value,
        )
        .order_by(OrganizationInvite.created_at.desc())
    )
    invites = result.scalars().all()

    return [
        InviteResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            status=inv.status,
            expires_at=inv.expires_at,
            invited_by_name=inv.invited_by.display_name,
            created_at=inv.created_at,
        )
        for inv in invites
    ]


@router.delete("/organizations/{org_id}/invites/{invite_id}", status_code=204)
async def revoke_invite(
    org_id: UUID,
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Revoke a pending invitation.
    """
    await get_org_or_404(db, org_id)
    await require_org_role(db, org_id, current_user.id, OrganizationRole.ADMIN)

    result = await db.execute(
        select(OrganizationInvite).where(
            OrganizationInvite.id == invite_id,
            OrganizationInvite.organization_id == org_id,
        )
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    invite.revoke()

    await log_org_action(
        db,
        org_id,
        current_user.id,
        "invite_revoked",
        resource_type="invite",
        resource_id=invite_id,
    )

    await db.commit()


@router.post("/organizations/invites/accept")
async def accept_invite(
    request: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """
    Accept an organization invitation.
    """
    result = await db.execute(
        select(OrganizationInvite)
        .options(selectinload(OrganizationInvite.organization))
        .where(OrganizationInvite.token == request.token)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token",
        )

    if not invite.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is expired or already used",
        )

    # Verify email matches (optional - could allow any logged-in user)
    if invite.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address",
        )

    # Accept invite
    invite.accept(current_user)

    # Create membership
    member = OrganizationMember(
        organization_id=invite.organization_id,
        user_id=current_user.id,
        role=invite.role,
        invited_by_id=invite.invited_by_id,
        invited_at=invite.created_at,
        joined_at=datetime.now(tz=UTC),
    )
    db.add(member)

    await log_org_action(
        db,
        invite.organization_id,
        current_user.id,
        "invite_accepted",
        resource_type="invite",
        resource_id=invite.id,
    )

    await db.commit()

    org = invite.organization

    count_result = await db.execute(
        select(func.count())
        .select_from(OrganizationMember)
        .where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.is_active,
        )
    )
    member_count = count_result.scalar() or 0

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        subscription_tier=org.subscription_tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        member_count=member_count,
        settings=org.settings,
        created_at=org.created_at,
    )


@router.get("/users/me/invites", response_model=list[InviteResponse])
async def my_pending_invites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InviteResponse]:
    """
    List pending invitations for current user.
    """
    result = await db.execute(
        select(OrganizationInvite)
        .options(selectinload(OrganizationInvite.invited_by))
        .options(selectinload(OrganizationInvite.organization))
        .where(
            OrganizationInvite.email == current_user.email,
            OrganizationInvite.status == InviteStatus.PENDING.value,
        )
        .order_by(OrganizationInvite.created_at.desc())
    )
    invites = result.scalars().all()

    return [
        InviteResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            status=inv.status,
            expires_at=inv.expires_at,
            invited_by_name=inv.invited_by.display_name,
            created_at=inv.created_at,
        )
        for inv in invites
    ]
