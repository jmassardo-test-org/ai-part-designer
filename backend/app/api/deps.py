"""
API Dependencies

Re-exports common dependencies from core modules for API routes.
"""

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_role,
)
from app.core.database import get_db
from app.models.subscription import (
    SubscriptionTier,
    TierSlug,
    TransactionType,
)
from app.models.user import User
from app.services.credits import (
    CreditService,
    QuotaService,
)

# Re-export admin dependency (call the factory to get the actual dependency)
get_current_admin_user = require_admin()


async def get_credit_service(
    db: AsyncSession = Depends(get_db),
) -> CreditService:
    """Get credit service dependency."""
    return CreditService(db)


async def get_quota_service(
    db: AsyncSession = Depends(get_db),
) -> QuotaService:
    """Get quota service dependency."""
    return QuotaService(db)


async def get_user_tier(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionTier:
    """Get the current user's subscription tier."""
    tier_slug = current_user.tier

    result = await db.execute(select(SubscriptionTier).where(SubscriptionTier.slug == tier_slug))
    tier = result.scalar_one_or_none()

    if not tier:
        # Fall back to free tier
        result = await db.execute(
            select(SubscriptionTier).where(SubscriptionTier.slug == TierSlug.FREE.value)
        )
        tier = result.scalar_one_or_none()

    if not tier:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No subscription tiers configured",
        )

    return tier


def require_credits(operation: TransactionType) -> Callable[..., None]:
    """
    Dependency factory to require credits for an operation.

    Usage:
        @router.post("/generate")
        async def generate(
            _credits: None = Depends(require_credits(TransactionType.GENERATION)),
            ...
        ):
            ...
    """

    async def dependency(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> None:
        credit_service = CreditService(db)

        can_afford, cost, balance = await credit_service.can_afford(current_user.id, operation)

        if not can_afford:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "insufficient_credits",
                    "message": f"Insufficient credits for {operation.value}",
                    "required": cost,
                    "available": balance,
                },
            )

    return dependency  # type: ignore[return-value]  # FastAPI handles coroutines


def require_job_slot() -> Callable[..., None]:
    """
    Dependency to require an available job slot.

    Checks that user hasn't exceeded concurrent job limit.
    """

    async def dependency(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tier: SubscriptionTier = Depends(get_user_tier),
    ) -> None:
        quota_service = QuotaService(db)

        can_start, current, limit = await quota_service.check_job_limit(current_user.id, tier)

        if not can_start:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "concurrent_job_limit",
                    "message": f"Maximum concurrent jobs ({limit}) reached",
                    "current": current,
                    "limit": limit,
                },
            )

    return dependency  # type: ignore[return-value]  # FastAPI handles coroutines


def require_storage(bytes_needed: int = 0) -> Callable[..., None]:
    """
    Dependency to require available storage.

    Args:
        bytes_needed: Estimated bytes for the operation
    """

    async def dependency(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        tier: SubscriptionTier = Depends(get_user_tier),
    ) -> None:
        quota_service = QuotaService(db)

        has_space, current, limit = await quota_service.check_storage_limit(
            current_user.id, tier, bytes_needed
        )

        if not has_space:
            raise HTTPException(
                status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                detail={
                    "error": "storage_limit",
                    "message": f"Storage limit ({limit / (1024**3):.1f} GB) exceeded",
                    "current_bytes": current,
                    "limit_bytes": limit,
                },
            )

    return dependency  # type: ignore[return-value]  # FastAPI handles coroutines


def require_feature(feature_name: str) -> Callable[..., None]:
    """
    Dependency to require a specific feature.

    Args:
        feature_name: Name of the feature to require
    """

    async def dependency(
        tier: SubscriptionTier = Depends(get_user_tier),
    ) -> None:
        if not tier.has_feature(feature_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_not_available",
                    "message": f"Feature '{feature_name}' not available on {tier.name} tier",
                    "required_tier": "Pro or Enterprise",
                },
            )

    return dependency  # type: ignore[return-value]  # FastAPI handles coroutines


def require_org_feature(feature_name: str) -> Callable[..., None]:
    """
    Dependency to require an organization to have a specific feature enabled.

    This dependency checks if the organization has the specified feature enabled.
    It tries to get org_id from path parameters (org_id or organization_id).
    If the resource is personal (not org-scoped), the check is skipped.

    Args:
        feature_name: Name of the feature to require

    Usage:
        # For endpoints with organization_id in path
        @router.post("/organizations/{organization_id}/teams")
        async def create_team(
            _feature: None = Depends(require_org_feature("teams")),
            organization_id: UUID,
            ...
        ):
            ...

        # For endpoints with org_id in path
        @router.post("/orgs/{org_id}/something")
        async def do_something(
            _feature: None = Depends(require_org_feature("some_feature")),
            org_id: UUID,
            ...
        ):
            ...
    """

    async def dependency(
        organization_id: UUID | None = None,
        org_id: UUID | None = None,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ) -> None:
        from app.models.organization import Organization

        # Try to get org_id from either parameter name
        actual_org_id = organization_id or org_id

        # If no org_id provided, this is a personal resource - skip check
        if not actual_org_id:
            return

        # Get organization
        result = await db.execute(select(Organization).where(Organization.id == actual_org_id))
        org = result.scalar_one_or_none()

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        # Check if feature is enabled
        if not org.has_feature(feature_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_disabled",
                    "message": f"Feature '{feature_name}' is not enabled for this organization",
                    "feature": feature_name,
                },
            )

    return dependency  # type: ignore[return-value]  # FastAPI handles coroutines


def require_org_feature_for_project(feature_name: str) -> Callable[..., None]:
    """
    Dependency to require an organization feature for project-scoped operations.

    This checks if a project belongs to an organization and if so,
    verifies the feature is enabled. Personal projects (no org) skip the check.

    Args:
        feature_name: Name of the feature to require

    Usage:
        @router.post("/projects/{project_id}/designs")
        async def create_design(
            _feature: None = Depends(require_org_feature_for_project("ai_generation")),
            project_id: UUID,
            ...
        ):
            ...
    """

    async def dependency(
        project_id: UUID,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ) -> None:
        from app.models.organization import Organization
        from app.models.project import Project

        # Get project
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # If no organization, this is a personal project - skip check
        if not project.organization_id:
            return

        # Get organization
        result = await db.execute(
            select(Organization).where(Organization.id == project.organization_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            # Organization was deleted but project still references it
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        # Check if feature is enabled
        if not org.has_feature(feature_name):  # type: ignore[attr-defined]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_disabled",
                    "message": f"Feature '{feature_name}' is not enabled for this organization",
                    "feature": feature_name,
                },
            )

    return dependency  # type: ignore[return-value]  # FastAPI handles coroutines


def require_org_feature_for_design(feature_name: str) -> Callable[..., None]:
    """
    Dependency to require an organization feature for design-scoped operations.

    This checks if a design's project belongs to an organization and if so,
    verifies the feature is enabled. Personal designs (no org) skip the check.

    Args:
        feature_name: Name of the feature to require

    Usage:
        @router.post("/designs/{design_id}/share")
        async def share_design(
            _feature: None = Depends(require_org_feature_for_design("design_sharing")),
            design_id: UUID,
            ...
        ):
            ...
    """

    async def dependency(
        design_id: UUID,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ) -> None:
        from app.models.design import Design
        from app.models.organization import Organization
        from app.models.project import Project

        # Get design
        result = await db.execute(select(Design).where(Design.id == design_id))
        design = result.scalar_one_or_none()

        if not design:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Design not found",
            )

        # Get project
        result = await db.execute(select(Project).where(Project.id == design.project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # If no organization, this is a personal design - skip check
        if not project.organization_id:  # type: ignore[attr-defined]
            return

        # Get organization
        result = await db.execute(
            select(Organization).where(Organization.id == project.organization_id)  # type: ignore[arg-type, attr-defined]
        )
        org = result.scalar_one_or_none()

        if not org:
            # Organization was deleted but project still references it
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        # Check if feature is enabled
        if not org.has_feature(feature_name):  # type: ignore[attr-defined]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_disabled",
                    "message": f"Feature '{feature_name}' is not enabled for this organization",
                    "feature": feature_name,
                },
            )

    return dependency  # type: ignore[return-value]  # FastAPI handles coroutines


def require_org_feature_for_assembly(feature_name: str) -> Callable[..., None]:
    """
    Dependency to require an organization feature for assembly-scoped operations.

    This checks if an assembly's project belongs to an organization and if so,
    verifies the feature is enabled. Personal assemblies (no org) skip the check.

    Args:
        feature_name: Name of the feature to require

    Usage:
        @router.get("/assemblies/{assembly_id}/bom")
        async def get_bom(
            _feature: None = Depends(require_org_feature_for_assembly("bom")),
            assembly_id: UUID,
            ...
        ):
            ...
    """

    async def dependency(
        assembly_id: UUID,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ) -> None:
        from app.models.assembly import Assembly
        from app.models.organization import Organization
        from app.models.project import Project

        # Get assembly
        result = await db.execute(select(Assembly).where(Assembly.id == assembly_id))
        assembly = result.scalar_one_or_none()

        if not assembly:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assembly not found",
            )

        # Get project
        result = await db.execute(select(Project).where(Project.id == assembly.project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # If no organization, this is a personal assembly - skip check
        if not project.organization_id:  # type: ignore[attr-defined]
            return

        # Get organization
        result = await db.execute(
            select(Organization).where(Organization.id == project.organization_id)  # type: ignore[arg-type, attr-defined]
        )
        org = result.scalar_one_or_none()

        if not org:
            # Organization was deleted but project still references it
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        # Check if feature is enabled
        if not org.has_feature(feature_name):  # type: ignore[attr-defined]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_disabled",
                    "message": f"Feature '{feature_name}' is not enabled for this organization",
                    "feature": feature_name,
                },
            )

    return dependency  # type: ignore[return-value]  # FastAPI handles coroutines


def require_org_feature_for_conversation(feature_name: str) -> Callable[..., None]:
    """
    Dependency to require an organization feature for conversation-scoped operations.

    Resolution chain: conversation_id → conversation.design_id → design.project_id
    → project.organization_id → org.has_feature()

    If the conversation has no design_id, or the design's project has no org,
    this is a personal resource — the check is skipped.

    Args:
        feature_name: Name of the feature to require

    Usage:
        @router.post("/{conversation_id}/messages")
        async def send_message(
            _org_feature: None = Depends(
                require_org_feature_for_conversation("ai_chat")
            ),
            conversation_id: UUID,
            ...
        ):
            ...
    """

    async def dependency(
        conversation_id: UUID,
        db: AsyncSession = Depends(get_db),
        _user: User = Depends(get_current_user),
    ) -> None:
        from app.models.conversation import Conversation
        from app.models.design import Design
        from app.models.organization import Organization
        from app.models.project import Project

        # Get conversation
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        # If no design linked, this is a personal conversation - skip check
        if not conversation.design_id:
            return

        # Get design
        result = await db.execute(select(Design).where(Design.id == conversation.design_id))
        design = result.scalar_one_or_none()

        if not design:
            # Design was deleted - treat as personal
            return

        # Get project
        result = await db.execute(select(Project).where(Project.id == design.project_id))  # type: ignore[arg-type, attr-defined]
        project = result.scalar_one_or_none()

        if not project:
            # Project was deleted - treat as personal
            return

        # If no organization, this is a personal project - skip check
        if not project.organization_id:  # type: ignore[attr-defined]
            return

        # Get organization
        result = await db.execute(
            select(Organization).where(Organization.id == project.organization_id)  # type: ignore[arg-type, attr-defined]
        )
        org = result.scalar_one_or_none()

        if not org:
            # Organization was deleted but project still references it
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        # Check if feature is enabled
        if not org.has_feature(feature_name):  # type: ignore[attr-defined]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_disabled",
                    "message": f"Feature '{feature_name}' is not enabled for this organization",
                    "feature": feature_name,
                },
            )

    return dependency  # type: ignore[return-value]  # FastAPI handles coroutines


async def check_org_feature_for_design(
    db: AsyncSession,
    design_id: UUID,
    feature_name: str,
) -> None:
    """
    Check org feature enforcement through design → project → org chain.

    This is a utility function (not a FastAPI dependency) for use when
    the design_id comes from the request body rather than a path parameter.

    If the design belongs to a personal project (no org), the check is skipped.
    If the design or project is not found, the check is skipped (graceful degradation).

    Args:
        db: Database session.
        design_id: The design UUID to resolve org context from.
        feature_name: Name of the feature to require.

    Raises:
        HTTPException: 404 if org not found, 403 if feature disabled.
    """
    from app.models.design import Design
    from app.models.organization import Organization
    from app.models.project import Project

    # Get design
    result = await db.execute(select(Design).where(Design.id == design_id))
    design = result.scalar_one_or_none()

    if not design:
        # Design not found - skip check (graceful degradation)
        return

    # Get project
    result = await db.execute(select(Project).where(Project.id == design.project_id))
    project = result.scalar_one_or_none()

    if not project or not project.organization_id:  # type: ignore[attr-defined]
        # Personal project - skip check
        return

    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == project.organization_id)  # type: ignore[arg-type, attr-defined]
    )
    org = result.scalar_one_or_none()

    if not org:
        # Organization was deleted but project still references it
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check if feature is enabled
    if not org.has_feature(feature_name):  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_disabled",
                "message": f"Feature '{feature_name}' is not enabled for this organization",
                "feature": feature_name,
            },
        )


# Alias for convenience
get_optional_user = get_current_user_optional


__all__ = [
    # Utility functions
    "check_org_feature_for_design",
    # Credits & Quotas
    "get_credit_service",
    "get_current_admin_user",
    "get_current_user",
    "get_current_user_optional",
    "get_db",
    "get_optional_user",
    "get_quota_service",
    "get_user_tier",
    "require_admin",
    "require_credits",
    "require_feature",
    "require_job_slot",
    "require_org_feature",
    "require_org_feature_for_assembly",
    "require_org_feature_for_conversation",
    "require_org_feature_for_design",
    "require_org_feature_for_project",
    "require_role",
    "require_storage",
]
