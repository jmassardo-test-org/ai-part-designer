"""
Tier enforcement middleware and utilities.

Provides decorators and functions to enforce subscription tier limits
and feature access throughout the application.
"""

import logging
from functools import wraps
from typing import Callable, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import TierSlug
from app.models.user import User

logger = logging.getLogger(__name__)


# Type variable for decorator
F = TypeVar('F', bound=Callable)


# =============================
# Tier Limits Configuration
# =============================

TIER_LIMITS = {
    TierSlug.FREE: {
        "monthly_generations": 10,
        "monthly_refinements": 5,
        "max_projects": 5,
        "max_designs_per_project": 10,
        "max_storage_gb": 1,
        "max_file_size_mb": 25,
        "max_concurrent_jobs": 1,
        "export_formats": ["stl", "obj"],
        "features": {
            "ai_generation": True,
            "export_2d": False,
            "collaboration": False,
            "api_access": False,
            "priority_queue": False,
            "custom_templates": False,
        },
    },
    TierSlug.PRO: {
        "monthly_generations": 100,
        "monthly_refinements": 50,
        "max_projects": 50,
        "max_designs_per_project": 100,
        "max_storage_gb": 50,
        "max_file_size_mb": 100,
        "max_concurrent_jobs": 5,
        "export_formats": ["stl", "obj", "step", "iges", "3mf"],
        "features": {
            "ai_generation": True,
            "export_2d": True,
            "collaboration": True,
            "api_access": False,
            "priority_queue": True,
            "custom_templates": True,
        },
    },
    TierSlug.ENTERPRISE: {
        "monthly_generations": 1000,
        "monthly_refinements": 500,
        "max_projects": -1,  # Unlimited
        "max_designs_per_project": -1,  # Unlimited
        "max_storage_gb": 500,
        "max_file_size_mb": 500,
        "max_concurrent_jobs": 20,
        "export_formats": ["stl", "obj", "step", "iges", "3mf", "dxf", "dwg"],
        "features": {
            "ai_generation": True,
            "export_2d": True,
            "collaboration": True,
            "api_access": True,
            "priority_queue": True,
            "custom_templates": True,
        },
    },
}


def get_tier_limits(tier: str) -> dict:
    """Get limits for a tier."""
    try:
        tier_enum = TierSlug(tier)
        return TIER_LIMITS.get(tier_enum, TIER_LIMITS[TierSlug.FREE])
    except ValueError:
        return TIER_LIMITS[TierSlug.FREE]


def get_user_tier(user: User) -> str:
    """Get the user's current subscription tier."""
    if user.subscription and user.subscription.is_active:
        return user.subscription.tier
    return TierSlug.FREE.value


# =============================
# Tier Requirement Decorator
# =============================

class TierRequired:
    """
    Dependency class to require a minimum subscription tier.
    
    Usage:
        @router.post("/premium-feature")
        async def premium_feature(
            user: User = Depends(get_current_user),
            _: None = Depends(TierRequired("pro")),
        ):
            ...
    """
    
    TIER_ORDER = {
        TierSlug.FREE.value: 0,
        TierSlug.PRO.value: 1,
        TierSlug.ENTERPRISE.value: 2,
    }
    
    def __init__(self, minimum_tier: str):
        """
        Initialize tier requirement.
        
        Args:
            minimum_tier: Minimum tier required (free, pro, enterprise)
        """
        self.minimum_tier = minimum_tier
    
    async def __call__(self, user: User) -> None:
        """Check if user meets tier requirement."""
        user_tier = get_user_tier(user)
        user_level = self.TIER_ORDER.get(user_tier, 0)
        required_level = self.TIER_ORDER.get(self.minimum_tier, 0)
        
        if user_level < required_level:
            logger.warning(
                f"User {user.id} with tier {user_tier} "
                f"attempted to access {self.minimum_tier}+ feature"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "upgrade_required",
                    "message": f"This feature requires {self.minimum_tier.title()} tier or higher",
                    "current_tier": user_tier,
                    "required_tier": self.minimum_tier,
                },
            )


def require_tier(minimum_tier: str):
    """
    Decorator to require a minimum subscription tier.
    
    Usage:
        @require_tier("pro")
        async def premium_endpoint(user: User):
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, user: User | None = None, **kwargs):
            if user is None:
                # Try to get user from kwargs
                user = kwargs.get('current_user')
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            # Check tier
            tier_check = TierRequired(minimum_tier)
            await tier_check(user)
            
            return await func(*args, user=user, **kwargs)
        
        return wrapper  # type: ignore
    return decorator


# =============================
# Feature Check
# =============================

def has_feature(user: User, feature_name: str) -> bool:
    """
    Check if user's tier includes a feature.
    
    Args:
        user: The user to check
        feature_name: Name of the feature to check
        
    Returns:
        True if feature is available, False otherwise
    """
    tier = get_user_tier(user)
    limits = get_tier_limits(tier)
    features = limits.get("features", {})
    return features.get(feature_name, False)


class FeatureRequired:
    """
    Dependency class to require a specific feature.
    
    Usage:
        @router.post("/2d-export")
        async def export_2d(
            user: User = Depends(get_current_user),
            _: None = Depends(FeatureRequired("export_2d")),
        ):
            ...
    """
    
    def __init__(self, feature_name: str):
        self.feature_name = feature_name
    
    async def __call__(self, user: User) -> None:
        if not has_feature(user, self.feature_name):
            tier = get_user_tier(user)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_not_available",
                    "message": f"Feature '{self.feature_name}' is not available on your current plan",
                    "current_tier": tier,
                    "feature": self.feature_name,
                },
            )


# =============================
# Quota Checks
# =============================

async def check_generation_quota(
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Check if user has remaining generation quota.
    
    Args:
        user: The user to check
        db: Database session
        
    Returns:
        Dict with 'allowed', 'used', 'limit', and 'remaining'
        
    Raises:
        HTTPException if quota exceeded
    """
    tier = get_user_tier(user)
    limits = get_tier_limits(tier)
    monthly_limit = limits.get("monthly_generations", 10)
    
    # Get current period usage
    usage = user.usage_quota
    period_generations = usage.period_generations if usage else 0
    
    result = {
        "allowed": period_generations < monthly_limit or monthly_limit == -1,
        "used": period_generations,
        "limit": monthly_limit,
        "remaining": max(0, monthly_limit - period_generations) if monthly_limit != -1 else -1,
    }
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exceeded",
                "message": "Monthly generation limit reached",
                "current_tier": tier,
                "used": period_generations,
                "limit": monthly_limit,
                "reset_at": None,  # TODO: Add next_refill_at to UsageQuota model
            },
        )
    
    return result


async def check_storage_quota(
    user: User,
    additional_bytes: int,
    db: AsyncSession,
) -> dict:
    """
    Check if user has storage space for additional data.
    
    Args:
        user: The user to check
        additional_bytes: Size of new data to store
        db: Database session
        
    Returns:
        Dict with 'allowed', 'used_gb', 'limit_gb', and 'remaining_gb'
        
    Raises:
        HTTPException if storage quota exceeded
    """
    tier = get_user_tier(user)
    limits = get_tier_limits(tier)
    max_storage_gb = limits.get("max_storage_gb", 1)
    max_storage_bytes = max_storage_gb * 1024 * 1024 * 1024
    
    # Get current usage
    usage = user.usage_quota
    current_bytes = usage.storage_used_bytes if usage else 0
    new_total = current_bytes + additional_bytes
    
    result = {
        "allowed": new_total <= max_storage_bytes,
        "used_gb": round(current_bytes / (1024 * 1024 * 1024), 2),
        "limit_gb": max_storage_gb,
        "remaining_gb": round((max_storage_bytes - current_bytes) / (1024 * 1024 * 1024), 2),
    }
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "storage_quota_exceeded",
                "message": "Storage limit reached",
                "current_tier": tier,
                "used_gb": result["used_gb"],
                "limit_gb": max_storage_gb,
            },
        )
    
    return result


async def check_project_limit(
    user: User,
    db: AsyncSession,
) -> dict:
    """
    Check if user can create another project.
    
    Args:
        user: The user to check
        db: Database session
        
    Returns:
        Dict with 'allowed', 'count', and 'limit'
        
    Raises:
        HTTPException if project limit reached
    """
    from app.models.project import Project
    
    tier = get_user_tier(user)
    limits = get_tier_limits(tier)
    max_projects = limits.get("max_projects", 5)
    
    # Count user's projects
    result = await db.execute(
        select(func.count(Project.id))
        .where(Project.user_id == user.id)
        .where(Project.deleted_at.is_(None))
    )
    project_count = result.scalar() or 0
    
    allowed = max_projects == -1 or project_count < max_projects
    
    check_result = {
        "allowed": allowed,
        "count": project_count,
        "limit": max_projects,
    }
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "project_limit_reached",
                "message": "Maximum project limit reached",
                "current_tier": tier,
                "count": project_count,
                "limit": max_projects,
            },
        )
    
    return check_result


async def check_file_size_limit(
    user: User,
    file_size_mb: float,
) -> dict:
    """
    Check if file size is within tier limits.
    
    Args:
        user: The user to check
        file_size_mb: Size of file in megabytes
        
    Returns:
        Dict with 'allowed' and 'limit_mb'
        
    Raises:
        HTTPException if file too large
    """
    tier = get_user_tier(user)
    limits = get_tier_limits(tier)
    max_file_size_mb = limits.get("max_file_size_mb", 25)
    
    result = {
        "allowed": file_size_mb <= max_file_size_mb,
        "file_size_mb": file_size_mb,
        "limit_mb": max_file_size_mb,
    }
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "file_too_large",
                "message": f"File size exceeds {max_file_size_mb}MB limit for your plan",
                "current_tier": tier,
                "file_size_mb": file_size_mb,
                "limit_mb": max_file_size_mb,
            },
        )
    
    return result


def can_use_export_format(user: User, format: str) -> bool:
    """
    Check if user's tier allows a specific export format.
    
    Args:
        user: The user to check
        format: Export format (e.g., "step", "stl")
        
    Returns:
        True if format is allowed, False otherwise
    """
    tier = get_user_tier(user)
    limits = get_tier_limits(tier)
    allowed_formats = limits.get("export_formats", ["stl", "obj"])
    return format.lower() in allowed_formats


# =============================
# Usage Tracking
# =============================

async def increment_generation_count(
    user: User,
    db: AsyncSession,
) -> None:
    """Increment the user's generation count for the current period."""
    if user.usage_quota:
        user.usage_quota.period_generations += 1
        await db.commit()


async def increment_refinement_count(
    user: User,
    db: AsyncSession,
) -> None:
    """Increment the user's refinement count for the current period."""
    if user.usage_quota:
        user.usage_quota.period_refinements += 1
        await db.commit()


async def update_storage_usage(
    user: User,
    delta_bytes: int,
    db: AsyncSession,
) -> None:
    """
    Update user's storage usage.
    
    Args:
        user: The user
        delta_bytes: Bytes added (positive) or removed (negative)
        db: Database session
    """
    if user.usage_quota:
        user.usage_quota.storage_used_bytes = max(
            0,
            user.usage_quota.storage_used_bytes + delta_bytes
        )
        await db.commit()
