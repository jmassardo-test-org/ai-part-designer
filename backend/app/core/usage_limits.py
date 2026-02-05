"""
Usage Limits and Quota Management

Comprehensive usage tracking and enforcement for:
- Daily/monthly generation limits per user tier
- Concurrent request limits
- Storage quotas
- API call budgets
"""

from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    and_,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

# =============================================================================
# Tier Limits Configuration
# =============================================================================


class UserTier(StrEnum):
    """User subscription tiers."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"


# Limits by tier
TIER_LIMITS = {
    UserTier.FREE: {
        # Generation limits
        "generations_per_day": 5,
        "generations_per_month": 50,
        "concurrent_generations": 1,
        # Modification limits
        "modifications_per_day": 10,
        "modifications_per_month": 100,
        # Storage limits
        "storage_bytes": 500 * 1024 * 1024,  # 500 MB
        "max_file_size_bytes": 25 * 1024 * 1024,  # 25 MB
        "max_files": 50,
        # Project limits
        "max_projects": 5,
        "max_designs_per_project": 20,
        # Component limits
        "max_components": 25,
        "component_extractions_per_day": 5,
        # Assembly limits
        "max_assemblies": 5,
        "max_components_per_assembly": 10,
        # Export limits
        "exports_per_day": 10,
        "exports_per_month": 100,
        # API limits
        "api_calls_per_minute": 60,
        "api_calls_per_day": 1000,
    },
    UserTier.PRO: {
        "generations_per_day": 50,
        "generations_per_month": 500,
        "concurrent_generations": 3,
        "modifications_per_day": 100,
        "modifications_per_month": 1000,
        "storage_bytes": 10 * 1024 * 1024 * 1024,  # 10 GB
        "max_file_size_bytes": 100 * 1024 * 1024,  # 100 MB
        "max_files": 500,
        "max_projects": 50,
        "max_designs_per_project": 100,
        "max_components": 250,
        "component_extractions_per_day": 50,
        "max_assemblies": 50,
        "max_components_per_assembly": 50,
        "exports_per_day": 100,
        "exports_per_month": 1000,
        "api_calls_per_minute": 300,
        "api_calls_per_day": 10000,
    },
    UserTier.ENTERPRISE: {
        "generations_per_day": 500,
        "generations_per_month": 10000,
        "concurrent_generations": 10,
        "modifications_per_day": 1000,
        "modifications_per_month": 20000,
        "storage_bytes": 100 * 1024 * 1024 * 1024,  # 100 GB
        "max_file_size_bytes": 500 * 1024 * 1024,  # 500 MB
        "max_files": 5000,
        "max_projects": 500,
        "max_designs_per_project": 500,
        "max_components": 2500,
        "component_extractions_per_day": 500,
        "max_assemblies": 500,
        "max_components_per_assembly": 200,
        "exports_per_day": 1000,
        "exports_per_month": 20000,
        "api_calls_per_minute": 1000,
        "api_calls_per_day": 100000,
    },
    UserTier.ADMIN: {
        # Admins have very high limits but not unlimited
        "generations_per_day": 1000,
        "generations_per_month": 50000,
        "concurrent_generations": 20,
        "modifications_per_day": 5000,
        "modifications_per_month": 100000,
        "storage_bytes": 1024 * 1024 * 1024 * 1024,  # 1 TB
        "max_file_size_bytes": 1024 * 1024 * 1024,  # 1 GB
        "max_files": 50000,
        "max_projects": 5000,
        "max_designs_per_project": 1000,
        "max_components": 25000,
        "component_extractions_per_day": 5000,
        "max_assemblies": 5000,
        "max_components_per_assembly": 500,
        "exports_per_day": 10000,
        "exports_per_month": 200000,
        "api_calls_per_minute": 5000,
        "api_calls_per_day": 500000,
    },
}


# =============================================================================
# Database Models
# =============================================================================


class UsageRecord(Base):
    """
    Tracks usage of rate-limited resources.

    Records are aggregated by user, resource type, and time period.
    """

    __tablename__ = "usage_records"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What was used
    resource_type = Column(
        String(50),
        nullable=False,
        index=True,
    )  # "generation", "modification", "export", "extraction", "api_call"

    # Time period
    period_type = Column(
        String(20),
        nullable=False,
    )  # "minute", "hour", "day", "month"
    period_start = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Usage count
    count = Column(Integer, default=0, nullable=False)

    # Extra data
    extra_data = Column(JSONB, default=dict)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_usage_user_resource_period",
            "user_id",
            "resource_type",
            "period_type",
            "period_start",
            unique=True,
        ),
    )


class ConcurrentOperation(Base):
    """
    Tracks currently active operations for concurrency limiting.
    """

    __tablename__ = "concurrent_operations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    operation_type = Column(
        String(50),
        nullable=False,
    )  # "generation", "extraction"

    job_id = Column(PGUUID(as_uuid=True), nullable=True)

    started_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Auto-expire after this time (cleanup stale records)
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (Index("ix_concurrent_user_type", "user_id", "operation_type"),)


# UserBan is now defined in app.models.rating to avoid duplicate table definitions
# Import it from there instead of defining here


class AbuseReport(Base):
    """
    Records of detected abuse and moderation flags.
    """

    __tablename__ = "abuse_reports"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ip_address = Column(String(50), nullable=True)

    # What triggered the report
    trigger_type = Column(
        String(50),
        nullable=False,
    )  # "content_moderation", "rate_limit", "suspicious_pattern", "manual"

    # Severity
    severity = Column(
        String(20),
        nullable=False,
    )  # "low", "medium", "high", "critical"

    # Details
    description = Column(Text, nullable=False)
    evidence = Column(JSONB, default=dict)

    # Related resources
    file_id = Column(PGUUID(as_uuid=True), nullable=True)
    job_id = Column(PGUUID(as_uuid=True), nullable=True)
    prompt = Column(Text, nullable=True)

    # Resolution
    status = Column(
        String(50),
        default="pending",
        nullable=False,
    )  # "pending", "reviewing", "resolved", "dismissed", "escalated"

    resolution = Column(Text, nullable=True)
    resolved_by = Column(PGUUID(as_uuid=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Action taken
    action_taken = Column(
        String(50),
        nullable=True,
    )  # "none", "warning", "temp_ban", "perm_ban", "content_removed"

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )


# =============================================================================
# Usage Tracking Service
# =============================================================================


class UsageLimitService:
    """
    Service for tracking and enforcing usage limits.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def get_tier_limits(self, tier: UserTier) -> dict:
        """Get limits for a user tier."""
        return TIER_LIMITS.get(tier, TIER_LIMITS[UserTier.FREE])

    def _get_period_start(self, period: str) -> datetime:
        """Get the start of the current period."""
        now = datetime.utcnow()

        if period == "minute":
            return now.replace(second=0, microsecond=0)
        if period == "hour":
            return now.replace(minute=0, second=0, microsecond=0)
        if period == "day":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "month":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return now

    async def get_usage(
        self,
        user_id: UUID,
        resource_type: str,
        period: str,
    ) -> int:
        """Get current usage count for a resource."""
        period_start = self._get_period_start(period)

        query = select(UsageRecord.count).where(
            and_(
                UsageRecord.user_id == user_id,
                UsageRecord.resource_type == resource_type,
                UsageRecord.period_type == period,
                UsageRecord.period_start == period_start,
            )
        )

        result = await self.db.execute(query)
        count = result.scalar_one_or_none()

        return count or 0

    async def increment_usage(
        self,
        user_id: UUID,
        resource_type: str,
        period: str,
        amount: int = 1,
        metadata: dict | None = None,
    ) -> int:
        """Increment usage count, returns new count."""
        period_start = self._get_period_start(period)

        # Try to update existing record
        query = select(UsageRecord).where(
            and_(
                UsageRecord.user_id == user_id,
                UsageRecord.resource_type == resource_type,
                UsageRecord.period_type == period,
                UsageRecord.period_start == period_start,
            )
        )

        result = await self.db.execute(query)
        record = result.scalar_one_or_none()

        if record:
            record.count += amount
            if metadata:
                record.extra_data = {**record.extra_data, **metadata}
            new_count = record.count
        else:
            record = UsageRecord(
                user_id=user_id,
                resource_type=resource_type,
                period_type=period,
                period_start=period_start,
                count=amount,
                extra_data=metadata or {},
            )
            self.db.add(record)
            new_count = amount

        await self.db.flush()
        return new_count

    async def check_limit(
        self,
        user_id: UUID,
        resource_type: str,
        tier: UserTier,
    ) -> tuple[bool, dict]:
        """
        Check if user is within limits for a resource.

        Returns:
            Tuple of (allowed, details dict)
        """
        limits = self.get_tier_limits(tier)

        # Map resource types to their limit keys and periods
        limit_map = {
            "generation": [
                ("generations_per_day", "day"),
                ("generations_per_month", "month"),
            ],
            "modification": [
                ("modifications_per_day", "day"),
                ("modifications_per_month", "month"),
            ],
            "export": [
                ("exports_per_day", "day"),
                ("exports_per_month", "month"),
            ],
            "extraction": [
                ("component_extractions_per_day", "day"),
            ],
            "api_call": [
                ("api_calls_per_minute", "minute"),
                ("api_calls_per_day", "day"),
            ],
        }

        checks = limit_map.get(resource_type, [])

        for limit_key, period in checks:
            limit = limits.get(limit_key, 0)
            if limit == 0:
                continue

            current = await self.get_usage(user_id, resource_type, period)

            if current >= limit:
                return False, {
                    "allowed": False,
                    "reason": f"{resource_type} limit exceeded",
                    "limit_key": limit_key,
                    "limit": limit,
                    "current": current,
                    "period": period,
                    "resets_at": self._get_period_start(period) + self._get_period_duration(period),
                }

        return True, {"allowed": True}

    def _get_period_duration(self, period: str) -> timedelta:
        """Get duration of a period."""
        durations = {
            "minute": timedelta(minutes=1),
            "hour": timedelta(hours=1),
            "day": timedelta(days=1),
            "month": timedelta(days=30),
        }
        return durations.get(period, timedelta(days=1))

    async def check_concurrent_limit(
        self,
        user_id: UUID,
        operation_type: str,
        tier: UserTier,
    ) -> tuple[bool, int]:
        """
        Check concurrent operation limit.

        Returns:
            Tuple of (allowed, current_count)
        """
        limits = self.get_tier_limits(tier)

        limit_key = f"concurrent_{operation_type}s"
        limit = limits.get(limit_key, 1)

        # Cleanup expired operations
        await self._cleanup_expired_operations()

        # Count current operations
        query = select(func.count(ConcurrentOperation.id)).where(
            and_(
                ConcurrentOperation.user_id == user_id,
                ConcurrentOperation.operation_type == operation_type,
                ConcurrentOperation.expires_at > datetime.utcnow(),
            )
        )

        result = await self.db.execute(query)
        current = result.scalar() or 0

        return current < limit, current

    async def start_concurrent_operation(
        self,
        user_id: UUID,
        operation_type: str,
        job_id: UUID | None = None,
        duration_minutes: int = 30,
    ) -> UUID:
        """Register a concurrent operation."""
        operation = ConcurrentOperation(
            user_id=user_id,
            operation_type=operation_type,
            job_id=job_id,
            expires_at=datetime.utcnow() + timedelta(minutes=duration_minutes),
        )

        self.db.add(operation)
        await self.db.flush()

        return operation.id

    async def end_concurrent_operation(
        self,
        operation_id: UUID,
    ) -> None:
        """Mark a concurrent operation as complete."""
        query = select(ConcurrentOperation).where(ConcurrentOperation.id == operation_id)
        result = await self.db.execute(query)
        operation = result.scalar_one_or_none()

        if operation:
            await self.db.delete(operation)

    async def _cleanup_expired_operations(self) -> int:
        """Remove expired concurrent operation records."""
        from sqlalchemy import delete

        stmt = delete(ConcurrentOperation).where(ConcurrentOperation.expires_at < datetime.utcnow())
        result = await self.db.execute(stmt)
        return result.rowcount

    async def get_usage_summary(
        self,
        user_id: UUID,
        tier: UserTier,
    ) -> dict:
        """Get complete usage summary for a user."""
        limits = self.get_tier_limits(tier)

        summary = {
            "tier": tier.value,
            "limits": limits,
            "usage": {},
        }

        # Get current usage for each resource
        resources = ["generation", "modification", "export", "extraction"]
        periods = ["day", "month"]

        for resource in resources:
            summary["usage"][resource] = {}
            for period in periods:
                count = await self.get_usage(user_id, resource, period)
                summary["usage"][resource][period] = count

        return summary


# =============================================================================
# Pydantic Schemas
# =============================================================================


class UsageLimitCheck(BaseModel):
    """Result of a usage limit check."""

    allowed: bool
    reason: str | None = None
    limit_key: str | None = None
    limit: int | None = None
    current: int | None = None
    period: str | None = None
    resets_at: datetime | None = None


class UsageSummary(BaseModel):
    """User's current usage summary."""

    tier: str
    generations: dict = Field(default_factory=dict)
    modifications: dict = Field(default_factory=dict)
    storage_used_bytes: int = 0
    storage_limit_bytes: int = 0
    concurrent_generations: int = 0
    concurrent_limit: int = 1
