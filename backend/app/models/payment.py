"""
Payment history model.

Tracks all payment transactions for audit and billing purposes.
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PaymentStatus(StrEnum):
    """Payment transaction status."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class PaymentType(StrEnum):
    """Payment transaction type."""

    SUBSCRIPTION = "subscription"  # Recurring subscription payment
    ONE_TIME = "one_time"  # One-time purchase
    CREDIT_PURCHASE = "credit_purchase"  # Credit pack purchase
    REFUND = "refund"  # Refund issued


class PaymentHistory(Base, TimestampMixin):
    """
    Payment transaction history.

    Records all payment events from Stripe for auditing,
    invoice generation, and customer support.
    """

    __tablename__ = "payment_history"

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
        nullable=False,
        index=True,
    )

    # Stripe identifiers
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stripe_invoice_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stripe_charge_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Payment details
    payment_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PaymentStatus.PENDING.value,
    )

    # Amount (in cents to avoid float issues)
    amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="usd",
    )

    # Description
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Payment method info (for display)
    payment_method_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # card, bank_transfer, etc.
    payment_method_last4: Mapped[str | None] = mapped_column(
        String(4),
        nullable=True,
    )  # Last 4 digits of card

    # Timestamps from Stripe
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Billing period (for subscription payments)
    period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Invoice URL for customer
    invoice_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    invoice_pdf_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Receipt URL
    receipt_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Failure details
    failure_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    failure_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Extra data (renamed from 'metadata' which is reserved by SQLAlchemy)
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="payment_history",
    )

    # Indexes
    __table_args__ = (
        Index("idx_payment_history_user_created", "user_id", "created_at"),
        Index("idx_payment_history_status", "status"),
        Index("idx_payment_history_type", "payment_type"),
    )

    def __repr__(self) -> str:
        return f"<PaymentHistory(id={self.id}, amount={self.amount_cents}, status={self.status})>"

    @property
    def amount(self) -> float:
        """Amount in dollars."""
        return self.amount_cents / 100

    @property
    def is_successful(self) -> bool:
        """Check if payment was successful."""
        return self.status == PaymentStatus.SUCCEEDED.value
