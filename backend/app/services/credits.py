"""
Credit Service for managing user credits.

Provides credit balance checking, deduction, refilling,
and transaction logging.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.models.subscription import (
    CreditBalance,
    CreditTransaction,
    SubscriptionTier,
    TransactionType,
    UsageQuota,
    get_operation_cost,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits."""

    def __init__(self, required: int, available: int, operation: str):
        self.required = required
        self.available = available
        self.operation = operation
        super().__init__(
            f"Insufficient credits for {operation}: requires {required}, available {available}"
        )


class QuotaExceededError(Exception):
    """Raised when user exceeds a quota limit."""

    def __init__(self, quota_type: str, limit: int, current: int):
        self.quota_type = quota_type
        self.limit = limit
        self.current = current
        super().__init__(f"Quota exceeded for {quota_type}: limit {limit}, current {current}")


class CreditService:
    """
    Service for managing user credits.

    Handles credit balance operations, transactions, and quota enforcement.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Balance Operations
    # =========================================================================

    async def get_balance(self, user_id: UUID) -> CreditBalance:
        """
        Get user's credit balance, creating if needed.

        Args:
            user_id: User ID

        Returns:
            CreditBalance record
        """
        result = await self.db.execute(
            select(CreditBalance).where(CreditBalance.user_id == user_id)
        )
        balance = result.scalar_one_or_none()

        if not balance:
            # Create initial balance
            balance = CreditBalance(
                user_id=user_id,
                balance=0,
                lifetime_earned=0,
                lifetime_spent=0,
            )
            self.db.add(balance)
            await self.db.flush()

        return balance

    async def get_balance_amount(self, user_id: UUID) -> int:
        """Get just the balance amount."""
        balance = await self.get_balance(user_id)
        return balance.balance

    async def can_afford(
        self,
        user_id: UUID,
        operation: TransactionType,
    ) -> tuple[bool, int, int]:
        """
        Check if user can afford an operation.

        Args:
            user_id: User ID
            operation: Operation type

        Returns:
            Tuple of (can_afford, cost, current_balance)
        """
        cost = get_operation_cost(operation)
        balance = await self.get_balance(user_id)
        return (balance.balance >= cost, cost, balance.balance)

    async def check_and_deduct(
        self,
        user_id: UUID,
        operation: TransactionType,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        description: str | None = None,
    ) -> CreditTransaction | None:
        """
        Check balance and deduct credits for an operation.

        Raises InsufficientCreditsError if balance is too low.

        Args:
            user_id: User ID
            operation: Operation type
            reference_type: Type of reference (e.g., "job")
            reference_id: ID of the reference
            description: Transaction description

        Returns:
            CreditTransaction record, or None for free operations
        """
        cost = get_operation_cost(operation)

        if cost == 0:
            # Free operation, no transaction needed
            return None

        balance = await self.get_balance(user_id)

        if balance.balance < cost:
            raise InsufficientCreditsError(
                required=cost,
                available=balance.balance,
                operation=operation.value,
            )

        # Deduct credits
        balance_before = balance.balance
        balance.balance -= cost
        balance.lifetime_spent += cost

        # Record transaction
        transaction = CreditTransaction(
            user_id=user_id,
            balance_id=balance.id,
            amount=-cost,
            transaction_type=operation.value,
            description=description or f"Deducted {cost} credit(s) for {operation.value}",
            balance_before=balance_before,
            balance_after=balance.balance,
            reference_type=reference_type,
            reference_id=reference_id,
        )

        self.db.add(transaction)
        await self.db.flush()

        logger.info(
            f"Deducted {cost} credits from user {user_id}: {balance_before} -> {balance.balance}"
        )

        return transaction

    async def add_credits(
        self,
        user_id: UUID,
        amount: int,
        transaction_type: TransactionType,
        description: str,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
    ) -> CreditTransaction:
        """
        Add credits to user's balance.

        Args:
            user_id: User ID
            amount: Credits to add (positive)
            transaction_type: Type of addition
            description: Transaction description
            reference_type: Optional reference type
            reference_id: Optional reference ID

        Returns:
            CreditTransaction record
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        balance = await self.get_balance(user_id)

        balance_before = balance.balance
        balance.balance += amount
        balance.lifetime_earned += amount

        transaction = CreditTransaction(
            user_id=user_id,
            balance_id=balance.id,
            amount=amount,
            transaction_type=transaction_type.value,
            description=description,
            balance_before=balance_before,
            balance_after=balance.balance,
            reference_type=reference_type,
            reference_id=reference_id,
        )

        self.db.add(transaction)
        await self.db.flush()

        logger.info(
            f"Added {amount} credits to user {user_id}: {balance_before} -> {balance.balance}"
        )

        return transaction

    async def refill_monthly_credits(
        self,
        user_id: UUID,
        tier: SubscriptionTier,
    ) -> CreditTransaction | None:
        """
        Refill user's monthly credits based on tier.

        Args:
            user_id: User ID
            tier: User's subscription tier

        Returns:
            CreditTransaction if refill occurred, None otherwise
        """
        balance = await self.get_balance(user_id)

        now = datetime.now(tz=UTC)

        # Check if refill is due
        if balance.next_refill_at and balance.next_refill_at > now:
            logger.debug(f"User {user_id} not due for refill until {balance.next_refill_at}")
            return None

        # Calculate credits to add
        credits_to_add = tier.monthly_credits

        # If rollover disabled, reset to tier amount
        if not tier.credit_rollover:
            balance_before = balance.balance
            balance.balance = credits_to_add
            balance.lifetime_earned += credits_to_add
        else:
            # Rollover - just add to existing
            balance_before = balance.balance
            balance.balance += credits_to_add
            balance.lifetime_earned += credits_to_add

        # Update refill timestamps
        balance.last_refill_at = now
        balance.next_refill_at = now + timedelta(days=30)

        # Record transaction
        transaction = CreditTransaction(
            user_id=user_id,
            balance_id=balance.id,
            amount=credits_to_add,
            transaction_type=TransactionType.MONTHLY_REFILL.value,
            description=f"Monthly credit refill for {tier.name} tier",
            balance_before=balance_before,
            balance_after=balance.balance,
            reference_type="subscription",
        )

        self.db.add(transaction)
        await self.db.flush()

        logger.info(
            f"Refilled {credits_to_add} credits for user {user_id}: "
            f"{balance_before} -> {balance.balance}"
        )

        return transaction

    # =========================================================================
    # Transaction History
    # =========================================================================

    async def get_transactions(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        transaction_type: TransactionType | None = None,
    ) -> list[CreditTransaction]:
        """
        Get user's credit transaction history.

        Args:
            user_id: User ID
            limit: Max transactions to return
            offset: Pagination offset
            transaction_type: Filter by type

        Returns:
            List of CreditTransaction records
        """
        query = (
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if transaction_type:
            query = query.where(CreditTransaction.transaction_type == transaction_type.value)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_usage_summary(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get usage summary for a period.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Summary dict with usage breakdown
        """
        from sqlalchemy import func

        since = datetime.now(tz=UTC) - timedelta(days=days)

        # Get total spent by type
        result = await self.db.execute(
            select(
                CreditTransaction.transaction_type,
                func.sum(CreditTransaction.amount).label("total"),
                func.count().label("count"),
            )
            .where(
                CreditTransaction.user_id == user_id,
                CreditTransaction.created_at >= since,
                CreditTransaction.amount < 0,  # Only spending
            )
            .group_by(CreditTransaction.transaction_type)
        )

        usage_by_type = {}
        for row in result:
            usage_by_type[row.transaction_type] = {
                "credits_spent": abs(row.total),
                "operation_count": row.count,
            }

        # Get balance
        balance = await self.get_balance(user_id)

        return {
            "current_balance": balance.balance,
            "lifetime_earned": balance.lifetime_earned,
            "lifetime_spent": balance.lifetime_spent,
            "period_days": days,
            "usage_by_type": usage_by_type,
            "next_refill_at": balance.next_refill_at.isoformat()
            if balance.next_refill_at
            else None,
        }


class QuotaService:
    """
    Service for managing user quotas.

    Tracks and enforces limits on storage, concurrent jobs, etc.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_quota(self, user_id: UUID) -> UsageQuota:
        """
        Get user's usage quota, creating if needed.

        Args:
            user_id: User ID

        Returns:
            UsageQuota record
        """
        result = await self.db.execute(select(UsageQuota).where(UsageQuota.user_id == user_id))
        quota = result.scalar_one_or_none()

        if not quota:
            quota = UsageQuota(
                user_id=user_id,
                storage_used_bytes=0,
                active_jobs_count=0,
                projects_count=0,
                period_start=datetime.now(tz=UTC),
            )
            self.db.add(quota)
            await self.db.flush()

        return quota

    async def check_job_limit(
        self,
        user_id: UUID,
        tier: SubscriptionTier,
    ) -> tuple[bool, int, int]:
        """
        Check if user can start a new job.

        Args:
            user_id: User ID
            tier: User's subscription tier

        Returns:
            Tuple of (can_start, current_count, limit)
        """
        quota = await self.get_quota(user_id)
        limit = tier.max_concurrent_jobs
        return (quota.active_jobs_count < limit, quota.active_jobs_count, limit)

    async def increment_active_jobs(self, user_id: UUID) -> None:
        """Increment active jobs count."""
        quota = await self.get_quota(user_id)
        quota.active_jobs_count += 1
        await self.db.flush()

    async def decrement_active_jobs(self, user_id: UUID) -> None:
        """Decrement active jobs count."""
        quota = await self.get_quota(user_id)
        if quota.active_jobs_count > 0:
            quota.active_jobs_count -= 1
            await self.db.flush()

    async def check_storage_limit(
        self,
        user_id: UUID,
        tier: SubscriptionTier,
        additional_bytes: int = 0,
    ) -> tuple[bool, int, int]:
        """
        Check if user has storage space.

        Args:
            user_id: User ID
            tier: User's subscription tier
            additional_bytes: Additional bytes to add

        Returns:
            Tuple of (has_space, current_bytes, limit_bytes)
        """
        quota = await self.get_quota(user_id)
        limit_bytes = tier.max_storage_gb * 1024 * 1024 * 1024
        new_total = quota.storage_used_bytes + additional_bytes
        return (new_total <= limit_bytes, quota.storage_used_bytes, limit_bytes)

    async def add_storage_usage(
        self,
        user_id: UUID,
        bytes_added: int,
    ) -> None:
        """Add to user's storage usage."""
        quota = await self.get_quota(user_id)
        quota.storage_used_bytes += bytes_added
        await self.db.flush()

    async def remove_storage_usage(
        self,
        user_id: UUID,
        bytes_removed: int,
    ) -> None:
        """Remove from user's storage usage."""
        quota = await self.get_quota(user_id)
        quota.storage_used_bytes = max(0, quota.storage_used_bytes - bytes_removed)
        await self.db.flush()

    async def check_project_limit(
        self,
        user_id: UUID,
        tier: SubscriptionTier,
    ) -> tuple[bool, int, int]:
        """
        Check if user can create a new project.

        Args:
            user_id: User ID
            tier: User's subscription tier

        Returns:
            Tuple of (can_create, current_count, limit)
        """
        quota = await self.get_quota(user_id)
        limit = tier.max_projects
        return (quota.projects_count < limit, quota.projects_count, limit)

    async def increment_projects(self, user_id: UUID) -> None:
        """Increment projects count."""
        quota = await self.get_quota(user_id)
        quota.projects_count += 1
        await self.db.flush()

    async def decrement_projects(self, user_id: UUID) -> None:
        """Decrement projects count."""
        quota = await self.get_quota(user_id)
        if quota.projects_count > 0:
            quota.projects_count -= 1
            await self.db.flush()

    async def record_generation(self, user_id: UUID) -> None:
        """Record a generation operation for the period."""
        quota = await self.get_quota(user_id)
        quota.period_generations += 1
        await self.db.flush()

    async def record_export(self, user_id: UUID) -> None:
        """Record an export operation for the period."""
        quota = await self.get_quota(user_id)
        quota.period_exports += 1
        await self.db.flush()


async def get_credit_service(db: AsyncSession) -> CreditService:
    """Dependency for credit service."""
    return CreditService(db)


async def get_quota_service(db: AsyncSession) -> QuotaService:
    """Dependency for quota service."""
    return QuotaService(db)
