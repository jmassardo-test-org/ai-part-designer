"""
API Dependencies

Re-exports common dependencies from core modules for API routes.
"""

from collections.abc import Callable

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


# Alias for convenience
get_optional_user = get_current_user_optional


__all__ = [
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
    "require_role",
    "require_storage",
]
