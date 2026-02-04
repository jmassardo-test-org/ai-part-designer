"""
Usage and Billing API endpoints.

Provides endpoints for viewing credit balance, usage statistics,
subscription tiers, and managing subscriptions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.subscription import (
    SubscriptionTier,
    CreditBalance,
    CreditTransaction,
    UsageQuota,
    TransactionType,
)
from app.api.deps import (
    get_current_user,
    get_credit_service,
    get_quota_service,
    get_user_tier,
)
from app.services.credits import CreditService, QuotaService

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class TierFeatures(BaseModel):
    """Features available on a tier."""
    
    ai_generation: bool = True
    export_2d: bool = False
    hardware_library: bool = True
    collaboration: bool = False
    api_access: bool = False
    priority_queue: bool = False
    white_label: bool = False


class SubscriptionTierResponse(BaseModel):
    """Subscription tier details."""
    
    id: UUID
    name: str
    slug: str
    description: str | None
    monthly_credits: int
    max_concurrent_jobs: int
    max_storage_gb: int
    max_projects: int
    max_file_size_mb: int
    features: dict[str, Any]
    price_monthly: float
    price_yearly: float
    is_current: bool = False


class CreditBalanceResponse(BaseModel):
    """Credit balance information."""
    
    balance: int
    lifetime_earned: int
    lifetime_spent: int
    next_refill_at: datetime | None = None
    credits_per_month: int


class TransactionResponse(BaseModel):
    """Credit transaction details."""
    
    id: UUID
    amount: int
    transaction_type: str
    description: str
    balance_after: int
    created_at: datetime
    reference_type: str | None = None


class UsageByTypeResponse(BaseModel):
    """Usage breakdown by type."""
    
    transaction_type: str
    credits_spent: int
    operation_count: int


class UsageSummaryResponse(BaseModel):
    """Usage summary for a period."""
    
    current_balance: int
    lifetime_earned: int
    lifetime_spent: int
    period_days: int
    usage_by_type: list[UsageByTypeResponse]
    next_refill_at: datetime | None = None


class QuotaUsageResponse(BaseModel):
    """Current quota usage."""
    
    storage_used_bytes: int
    storage_limit_bytes: int
    storage_used_percent: float
    active_jobs_count: int
    max_concurrent_jobs: int
    projects_count: int
    max_projects: int
    period_generations: int
    period_exports: int


class DashboardResponse(BaseModel):
    """Complete usage dashboard."""
    
    credits: CreditBalanceResponse
    quota: QuotaUsageResponse
    current_tier: SubscriptionTierResponse
    recent_transactions: list[TransactionResponse]


# =============================================================================
# Tier Endpoints
# =============================================================================

@router.get("/tiers", response_model=list[SubscriptionTierResponse])
async def list_tiers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SubscriptionTierResponse]:
    """
    List all available subscription tiers.
    
    Returns tiers sorted by display order, with current tier marked.
    """
    result = await db.execute(
        select(SubscriptionTier)
        .where(SubscriptionTier.is_active == True)
        .order_by(SubscriptionTier.display_order)
    )
    tiers = result.scalars().all()
    
    current_tier_slug = current_user.tier
    
    return [
        SubscriptionTierResponse(
            id=tier.id,
            name=tier.name,
            slug=tier.slug,
            description=tier.description,
            monthly_credits=tier.monthly_credits,
            max_concurrent_jobs=tier.max_concurrent_jobs,
            max_storage_gb=tier.max_storage_gb,
            max_projects=tier.max_projects,
            max_file_size_mb=tier.max_file_size_mb,
            features=tier.features,
            price_monthly=float(tier.price_monthly),
            price_yearly=float(tier.price_yearly),
            is_current=tier.slug == current_tier_slug,
        )
        for tier in tiers
    ]


@router.get("/tiers/{tier_slug}", response_model=SubscriptionTierResponse)
async def get_tier(
    tier_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionTierResponse:
    """
    Get details for a specific tier.
    """
    result = await db.execute(
        select(SubscriptionTier).where(SubscriptionTier.slug == tier_slug)
    )
    tier = result.scalar_one_or_none()
    
    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tier '{tier_slug}' not found",
        )
    
    return SubscriptionTierResponse(
        id=tier.id,
        name=tier.name,
        slug=tier.slug,
        description=tier.description,
        monthly_credits=tier.monthly_credits,
        max_concurrent_jobs=tier.max_concurrent_jobs,
        max_storage_gb=tier.max_storage_gb,
        max_projects=tier.max_projects,
        max_file_size_mb=tier.max_file_size_mb,
        features=tier.features,
        price_monthly=float(tier.price_monthly),
        price_yearly=float(tier.price_yearly),
        is_current=tier.slug == current_user.tier,
    )


# =============================================================================
# Credits Endpoints
# =============================================================================

@router.get("/credits/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    credit_service: CreditService = Depends(get_credit_service),
    tier: SubscriptionTier = Depends(get_user_tier),
) -> CreditBalanceResponse:
    """
    Get current credit balance.
    """
    balance = await credit_service.get_balance(current_user.id)
    
    return CreditBalanceResponse(
        balance=balance.balance,
        lifetime_earned=balance.lifetime_earned,
        lifetime_spent=balance.lifetime_spent,
        next_refill_at=balance.next_refill_at,
        credits_per_month=tier.monthly_credits,
    )


@router.get("/credits/transactions", response_model=list[TransactionResponse])
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    transaction_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    credit_service: CreditService = Depends(get_credit_service),
) -> list[TransactionResponse]:
    """
    Get credit transaction history.
    """
    type_filter = None
    if transaction_type:
        try:
            type_filter = TransactionType(transaction_type)
        except ValueError:
            pass
    
    transactions = await credit_service.get_transactions(
        current_user.id,
        limit=limit,
        offset=offset,
        transaction_type=type_filter,
    )
    
    return [
        TransactionResponse(
            id=t.id,
            amount=t.amount,
            transaction_type=t.transaction_type,
            description=t.description,
            balance_after=t.balance_after,
            created_at=t.created_at,
            reference_type=t.reference_type,
        )
        for t in transactions
    ]


@router.get("/credits/usage", response_model=UsageSummaryResponse)
async def get_usage_summary(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    credit_service: CreditService = Depends(get_credit_service),
) -> UsageSummaryResponse:
    """
    Get usage summary for a period.
    """
    summary = await credit_service.get_usage_summary(current_user.id, days=days)
    
    usage_list = [
        UsageByTypeResponse(
            transaction_type=t_type,
            credits_spent=data["credits_spent"],
            operation_count=data["operation_count"],
        )
        for t_type, data in summary["usage_by_type"].items()
    ]
    
    return UsageSummaryResponse(
        current_balance=summary["current_balance"],
        lifetime_earned=summary["lifetime_earned"],
        lifetime_spent=summary["lifetime_spent"],
        period_days=summary["period_days"],
        usage_by_type=usage_list,
        next_refill_at=datetime.fromisoformat(summary["next_refill_at"]) if summary["next_refill_at"] else None,
    )


# =============================================================================
# Quota Endpoints
# =============================================================================

@router.get("/quota", response_model=QuotaUsageResponse)
async def get_quota_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    quota_service: QuotaService = Depends(get_quota_service),
    tier: SubscriptionTier = Depends(get_user_tier),
) -> QuotaUsageResponse:
    """
    Get current quota usage.
    """
    quota = await quota_service.get_quota(current_user.id)
    
    storage_limit = tier.max_storage_gb * 1024 * 1024 * 1024
    storage_percent = (quota.storage_used_bytes / storage_limit * 100) if storage_limit > 0 else 0
    
    return QuotaUsageResponse(
        storage_used_bytes=quota.storage_used_bytes,
        storage_limit_bytes=storage_limit,
        storage_used_percent=round(storage_percent, 1),
        active_jobs_count=quota.active_jobs_count,
        max_concurrent_jobs=tier.max_concurrent_jobs,
        projects_count=quota.projects_count,
        max_projects=tier.max_projects,
        period_generations=quota.period_generations,
        period_exports=quota.period_exports,
    )


# =============================================================================
# Dashboard Endpoint
# =============================================================================

@router.get("/dashboard", response_model=DashboardResponse)
async def get_usage_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    credit_service: CreditService = Depends(get_credit_service),
    quota_service: QuotaService = Depends(get_quota_service),
    tier: SubscriptionTier = Depends(get_user_tier),
) -> DashboardResponse:
    """
    Get complete usage dashboard.
    
    Combines credits, quota, tier info, and recent transactions.
    """
    # Get balance
    balance = await credit_service.get_balance(current_user.id)
    
    # Get quota
    quota = await quota_service.get_quota(current_user.id)
    
    # Get recent transactions
    transactions = await credit_service.get_transactions(
        current_user.id,
        limit=10,
    )
    
    storage_limit = tier.max_storage_gb * 1024 * 1024 * 1024
    storage_percent = (quota.storage_used_bytes / storage_limit * 100) if storage_limit > 0 else 0
    
    return DashboardResponse(
        credits=CreditBalanceResponse(
            balance=balance.balance,
            lifetime_earned=balance.lifetime_earned,
            lifetime_spent=balance.lifetime_spent,
            next_refill_at=balance.next_refill_at,
            credits_per_month=tier.monthly_credits,
        ),
        quota=QuotaUsageResponse(
            storage_used_bytes=quota.storage_used_bytes,
            storage_limit_bytes=storage_limit,
            storage_used_percent=round(storage_percent, 1),
            active_jobs_count=quota.active_jobs_count,
            max_concurrent_jobs=tier.max_concurrent_jobs,
            projects_count=quota.projects_count,
            max_projects=tier.max_projects,
            period_generations=quota.period_generations,
            period_exports=quota.period_exports,
        ),
        current_tier=SubscriptionTierResponse(
            id=tier.id,
            name=tier.name,
            slug=tier.slug,
            description=tier.description,
            monthly_credits=tier.monthly_credits,
            max_concurrent_jobs=tier.max_concurrent_jobs,
            max_storage_gb=tier.max_storage_gb,
            max_projects=tier.max_projects,
            max_file_size_mb=tier.max_file_size_mb,
            features=tier.features,
            price_monthly=float(tier.price_monthly),
            price_yearly=float(tier.price_yearly),
            is_current=True,
        ),
        recent_transactions=[
            TransactionResponse(
                id=t.id,
                amount=t.amount,
                transaction_type=t.transaction_type,
                description=t.description,
                balance_after=t.balance_after,
                created_at=t.created_at,
                reference_type=t.reference_type,
            )
            for t in transactions
        ],
    )
