"""
Seed subscription tiers.

This module creates the default subscription tiers:
- Free: Basic tier with limited features
- Starter: Entry-level paid tier
- Pro: Professional tier with advanced features
- Enterprise: Full-featured tier for large organizations

Usage:
    python -m app.seeds.tiers
"""

import asyncio
import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.subscription import SubscriptionTier

logger = logging.getLogger(__name__)

# =============================================================================
# Default Tier Definitions
# =============================================================================

TIERS = [
    {
        "id": uuid4(),
        "name": "Free",
        "slug": "free",
        "description": "Get started with AI-powered part design",
        "monthly_credits": 10,
        "credit_rollover": False,
        "max_concurrent_jobs": 1,
        "max_storage_gb": 1,
        "max_projects": 5,
        "max_designs_per_project": 10,
        "max_file_size_mb": 25,
        "features": {
            "ai_generation": True,
            "export_2d": False,
            "hardware_library": True,
            "collaboration": False,
            "api_access": False,
            "priority_queue": False,
            "custom_templates": False,
        },
        "price_monthly_cents": 0,
        "price_yearly_cents": 0,
        "display_order": 0,
        "is_active": True,
    },
    {
        "id": uuid4(),
        "name": "Starter",
        "slug": "starter",
        "description": "For hobbyists and small projects",
        "monthly_credits": 50,
        "credit_rollover": False,
        "max_concurrent_jobs": 2,
        "max_storage_gb": 5,
        "max_projects": 20,
        "max_designs_per_project": 50,
        "max_file_size_mb": 50,
        "features": {
            "ai_generation": True,
            "export_2d": True,
            "hardware_library": True,
            "collaboration": False,
            "api_access": False,
            "priority_queue": False,
            "custom_templates": True,
        },
        "price_monthly_cents": 999,
        "price_yearly_cents": 9990,
        "display_order": 1,
        "is_active": True,
    },
    {
        "id": uuid4(),
        "name": "Pro",
        "slug": "pro",
        "description": "For professionals and small teams",
        "monthly_credits": 200,
        "credit_rollover": True,
        "max_concurrent_jobs": 5,
        "max_storage_gb": 25,
        "max_projects": 100,
        "max_designs_per_project": 200,
        "max_file_size_mb": 100,
        "features": {
            "ai_generation": True,
            "export_2d": True,
            "hardware_library": True,
            "collaboration": True,
            "api_access": True,
            "priority_queue": True,
            "custom_templates": True,
        },
        "price_monthly_cents": 2999,
        "price_yearly_cents": 29990,
        "display_order": 2,
        "is_active": True,
    },
    {
        "id": uuid4(),
        "name": "Enterprise",
        "slug": "enterprise",
        "description": "For organizations needing full control",
        "monthly_credits": -1,  # Unlimited
        "credit_rollover": True,
        "max_concurrent_jobs": -1,  # Unlimited
        "max_storage_gb": -1,  # Unlimited
        "max_projects": -1,  # Unlimited
        "max_designs_per_project": -1,  # Unlimited
        "max_file_size_mb": 500,
        "features": {
            "ai_generation": True,
            "export_2d": True,
            "hardware_library": True,
            "collaboration": True,
            "api_access": True,
            "priority_queue": True,
            "custom_templates": True,
            "white_label": True,
            "sso": True,
            "audit_logs": True,
        },
        "price_monthly_cents": 9999,
        "price_yearly_cents": 99990,
        "display_order": 3,
        "is_active": True,
    },
]


async def seed_tiers(session: AsyncSession) -> int:
    """Seed subscription tiers.
    
    Args:
        session: Database session.
        
    Returns:
        Number of tiers created.
    """
    created = 0
    
    for tier_data in TIERS:
        # Check if tier already exists
        result = await session.execute(
            select(SubscriptionTier).where(SubscriptionTier.slug == tier_data["slug"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.info(f"Tier '{tier_data['slug']}' already exists, skipping...")
            continue
        
        tier = SubscriptionTier(**tier_data)
        session.add(tier)
        created += 1
        logger.info(f"Created tier: {tier_data['name']}")
    
    await session.commit()
    return created


async def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    
    async with async_session_maker() as session:
        count = await seed_tiers(session)
        print(f"\nSeeded {count} subscription tiers successfully!")


if __name__ == "__main__":
    asyncio.run(main())
