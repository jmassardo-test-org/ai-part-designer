"""
Feature flag domain models.

Provides persistent storage for feature flag definitions and scoped overrides.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FlagTargetType(StrEnum):
    """Targets that feature flag overrides can apply to."""

    GLOBAL = "global"
    ORGANIZATION = "organization"
    USER = "user"


class FeatureFlag(Base, TimestampMixin):
    """Feature flag definition with optional rollout percentage."""

    __tablename__ = "feature_flags"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    rollout_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    overrides: Mapped[list[FeatureFlagOverride]] = relationship(
        "FeatureFlagOverride",
        back_populates="flag",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<FeatureFlag key={self.key} enabled={self.enabled}>"


class FeatureFlagOverride(Base, TimestampMixin):
    """Scoped override for a feature flag."""

    __tablename__ = "feature_flag_overrides"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    flag_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("feature_flags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[FlagTargetType] = mapped_column(
        String(20),
        nullable=False,
        default=FlagTargetType.GLOBAL.value,
    )
    target_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    environment: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="production",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    rollout_percentage: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    flag: Mapped[FeatureFlag] = relationship("FeatureFlag", back_populates="overrides")

    __table_args__ = (
        UniqueConstraint(
            "flag_id",
            "target_type",
            "target_id",
            "environment",
            name="uq_feature_flag_override_target",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FeatureFlagOverride flag_id={self.flag_id} "
            f"target_type={self.target_type} enabled={self.enabled}>"
        )
