"""Coupon and promotion models.

Provides models for managing promotional coupons and tracking
their redemption by users.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class CouponType(StrEnum):
    """Coupon discount type."""

    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_CREDITS = "free_credits"
    TIER_UPGRADE = "tier_upgrade"


class Coupon(Base, TimestampMixin, SoftDeleteMixin):
    """Promotional coupon model.

    Represents a promotional coupon with configurable discount types,
    validity periods, and usage limits.

    Attributes:
        id: Unique identifier.
        code: Unique coupon code string.
        description: Optional human-readable description.
        coupon_type: Type of discount (percentage, fixed_amount, free_credits, tier_upgrade).
        discount_percent: Percentage discount (for percentage type).
        discount_amount: Fixed amount discount in cents (for fixed_amount type).
        free_credits: Number of free credits to grant (for free_credits type).
        upgrade_tier: Target tier slug (for tier_upgrade type).
        valid_from: Start of validity period.
        valid_until: End of validity period.
        is_active: Whether the coupon is currently active.
        max_uses: Maximum total redemptions (null = unlimited).
        max_uses_per_user: Maximum redemptions per user.
        current_uses: Current total redemption count.
        restricted_to_tiers: JSON list of tier slugs that can use this coupon.
        new_users_only: Whether coupon is restricted to new users.
        created_by: ID of the admin who created the coupon.
    """

    __tablename__ = "coupons"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    coupon_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Value fields
    discount_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_amount: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # cents
    free_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upgrade_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Validity
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Usage limits
    max_uses: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # null = unlimited
    max_uses_per_user: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    current_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Restrictions
    restricted_to_tiers: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # ["free", "starter"]
    new_users_only: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Metadata
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    redemptions: Mapped[list["CouponRedemption"]] = relationship(
        "CouponRedemption",
        back_populates="coupon",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_coupons_code_active", "code", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Coupon(id={self.id}, code={self.code})>"


class CouponRedemption(Base, TimestampMixin):
    """Tracks coupon usage by users.

    Records each individual redemption of a coupon by a user,
    including when it was redeemed.

    Attributes:
        id: Unique identifier.
        coupon_id: Reference to the redeemed coupon.
        user_id: Reference to the user who redeemed.
    """

    __tablename__ = "coupon_redemptions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    coupon_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("coupons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    coupon: Mapped["Coupon"] = relationship(
        "Coupon",
        back_populates="redemptions",
    )

    __table_args__ = (
        Index("ix_coupon_redemptions_coupon_user", "coupon_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<CouponRedemption(id={self.id}, coupon_id={self.coupon_id}, user_id={self.user_id})>"
