"""
Subscription and Credits domain models.

Handles subscription tiers, credit balances, and usage tracking.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class TierSlug(str, Enum):
    """Subscription tier identifiers."""
    
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionTier(Base, TimestampMixin):
    """
    Subscription tier definition.
    
    Defines the limits, features, and pricing for each subscription level.
    """

    __tablename__ = "subscription_tiers"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Tier identification
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "Free", "Pro", "Enterprise"
    
    slug: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
    )  # "free", "pro", "enterprise"
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Credits
    monthly_credits: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )
    credit_rollover: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )  # Whether unused credits roll over

    # Limits
    max_concurrent_jobs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    max_storage_gb: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    max_projects: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
    )
    max_designs_per_project: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )
    max_file_size_mb: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=25,
    )

    # Feature flags (JSONB for flexibility)
    features: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    # Example: {
    #   "ai_generation": true,
    #   "export_2d": false,
    #   "hardware_library": true,
    #   "collaboration": false,
    #   "api_access": false,
    #   "priority_queue": false,
    #   "white_label": false
    # }

    # Pricing (in cents to avoid float issues)
    price_monthly_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    price_yearly_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Stripe
    stripe_price_id_monthly: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    stripe_price_id_yearly: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Order for display
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Active flag
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    def __repr__(self) -> str:
        return f"<SubscriptionTier(slug={self.slug}, name={self.name})>"

    def has_feature(self, feature_name: str) -> bool:
        """Check if tier has a specific feature."""
        return self.features.get(feature_name, False)

    @property
    def price_monthly(self) -> Decimal:
        """Monthly price in dollars."""
        return Decimal(self.price_monthly_cents) / 100

    @property
    def price_yearly(self) -> Decimal:
        """Yearly price in dollars."""
        return Decimal(self.price_yearly_cents) / 100


class TransactionType(str, Enum):
    """Credit transaction types."""
    
    MONTHLY_REFILL = "monthly_refill"
    GENERATION = "generation"
    REFINEMENT = "refinement"
    EXPORT_2D = "export_2d"
    PURCHASE = "purchase"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    BONUS = "bonus"


class CreditBalance(Base, TimestampMixin):
    """
    User's credit balance.
    
    Tracks current credits and refill timing.
    """

    __tablename__ = "credit_balances"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Current balance
    balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Lifetime tracking
    lifetime_earned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    lifetime_spent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Refill tracking
    last_refill_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_refill_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="credit_balance",
    )
    transactions: Mapped[list["CreditTransaction"]] = relationship(
        "CreditTransaction",
        back_populates="balance",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<CreditBalance(user_id={self.user_id}, balance={self.balance})>"

    def can_afford(self, cost: int) -> bool:
        """Check if user can afford an operation."""
        return self.balance >= cost

    def deduct(self, amount: int) -> None:
        """Deduct credits from balance."""
        if amount > self.balance:
            raise ValueError("Insufficient credits")
        self.balance -= amount
        self.lifetime_spent += amount

    def add(self, amount: int) -> None:
        """Add credits to balance."""
        self.balance += amount
        self.lifetime_earned += amount


class CreditTransaction(Base, TimestampMixin):
    """
    Credit transaction history.
    
    Records all credit additions and deductions.
    """

    __tablename__ = "credit_transactions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    balance_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("credit_balances.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Transaction details
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )  # Positive = add, Negative = spend
    
    transaction_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )  # TransactionType enum value
    
    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Balance snapshot
    balance_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    balance_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Reference (job, purchase, etc.)
    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # "job", "purchase", "subscription"
    reference_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Extra data (renamed from 'metadata' which is reserved by SQLAlchemy)
    extra_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    balance: Mapped["CreditBalance"] = relationship(
        "CreditBalance",
        back_populates="transactions",
    )

    # Indexes for querying
    __table_args__ = (
        Index("idx_credit_transactions_user_created", "user_id", "created_at"),
        Index("idx_credit_transactions_type", "transaction_type"),
    )

    def __repr__(self) -> str:
        return f"<CreditTransaction(id={self.id}, amount={self.amount}, type={self.transaction_type})>"


class UsageQuota(Base, TimestampMixin):
    """
    User's current usage against their tier quotas.
    
    Tracks storage used, active jobs, etc.
    """

    __tablename__ = "usage_quotas"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Current usage
    storage_used_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    active_jobs_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    projects_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Period usage (resets monthly)
    period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    period_generations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    period_refinements: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    period_exports: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="usage_quota",
    )

    def __repr__(self) -> str:
        return f"<UsageQuota(user_id={self.user_id})>"

    @property
    def storage_used_gb(self) -> float:
        """Storage used in GB."""
        return self.storage_used_bytes / (1024 * 1024 * 1024)


# Operation costs in credits
OPERATION_COSTS = {
    TransactionType.GENERATION: 1,
    TransactionType.REFINEMENT: 1,
    TransactionType.EXPORT_2D: 2,
}


def get_operation_cost(operation: TransactionType) -> int:
    """Get the credit cost for an operation."""
    return OPERATION_COSTS.get(operation, 0)
