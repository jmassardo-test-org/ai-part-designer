"""
API test fixtures.

Provides fixtures specifically for API endpoint tests including
subscription tiers and organization setup.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import SubscriptionTier


@pytest_asyncio.fixture(autouse=True)
async def seed_subscription_tiers_api(db_session: AsyncSession) -> None:
    """Seed subscription tiers with all features enabled.

    API tests need tier-level feature checks to pass so that
    org-level and endpoint-level tests can work properly.
    This fixture creates a free tier with every feature enabled.
    """
    # Check if already seeded (avoid duplicates)
    from sqlalchemy import select

    result = await db_session.execute(
        select(SubscriptionTier).where(SubscriptionTier.slug == "free")
    )
    existing = result.scalar_one_or_none()
    if existing:
        return

    tier = SubscriptionTier(
        slug="free",
        name="Free",
        description="Free tier for all users",
        price_monthly_cents=0,
        price_yearly_cents=0,
        monthly_credits=100,
        max_projects=5,
        max_designs_per_project=10,
        max_concurrent_jobs=1,
        max_storage_gb=1,
        max_file_size_mb=25,
        features={
            "basic_generation": True,
            "ai_chat": True,
            "ai_generation": True,
            "file_uploads": True,
            "design_sharing": True,
            "teams": True,
            "assemblies": True,
            "bom": True,
        },
        is_active=True,
    )
    db_session.add(tier)
    await db_session.commit()
