"""
Feature flag service with Redis caching.

Provides evaluation logic with scoped overrides, rollout support, and cache
invalidation helpers for API dependencies.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.feature_flag import FeatureFlag, FeatureFlagOverride, FlagTargetType

if TYPE_CHECKING:
    from uuid import UUID
    from app.core.cache import RedisClient

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

GLOBAL_ENVIRONMENT = "all"


class FeatureFlagNotFoundError(Exception):
    """Raised when a requested feature flag does not exist."""


class FeatureFlagService:
    """Service for evaluating and managing feature flags."""

    def __init__(
        self,
        db: AsyncSession,
        cache: RedisClient | None = None,
        cache_ttl_seconds: int = 300,
    ):
        self.db = db
        self.cache = cache
        self.cache_ttl_seconds = cache_ttl_seconds

    async def evaluate_flag(
        self,
        key: str,
        *,
        user_id: UUID | None = None,
        organization_id: UUID | None = None,
        environment: str = "production",
    ) -> bool:
        """
        Evaluate whether a flag is enabled for the given context.

        Resolution order:
        1. Cached value (if available)
        2. User-specific override
        3. Organization override
        4. Global override for environment (or \"all\")
        5. Flag default state

        Rollout percentages apply to the selected state using a deterministic
        hash of user → organization → flag key to keep behavior stable.
        """
        cache_key = self._cache_key(key, environment, organization_id, user_id)
        cached = await self._get_cached_value(cache_key)
        if cached is not None:
            return cached

        flag = await self._get_flag_by_key(key)
        if not flag:
            raise FeatureFlagNotFoundError(f"Feature flag '{key}' not found")

        overrides = await self._get_overrides(flag.id, environment)
        override = self._select_override(overrides, user_id, organization_id)

        enabled_state, rollout = self._resolve_state(flag, override)
        rollout_target = self._rollout_target(user_id, organization_id, flag.key)
        result = self._apply_rollout(enabled_state, rollout, rollout_target)

        await self._set_cached_value(cache_key, result)
        return result

    async def set_override(
        self,
        key: str,
        *,
        target_type: FlagTargetType,
        enabled: bool,
        environment: str = "production",
        target_id: UUID | None = None,
        rollout_percentage: int | None = None,
        notes: str | None = None,
        expires_at: datetime | None = None,
    ) -> FeatureFlagOverride:
        """
        Create or update an override for a feature flag.

        Cache entries are invalidated for the flag to avoid stale evaluations.
        """
        flag = await self._get_flag_by_key(key)
        if not flag:
            raise FeatureFlagNotFoundError(f"Feature flag '{key}' not found")

        existing = await self._get_existing_override(
            flag.id, target_type, target_id, environment
        )

        if existing:
            override = existing
            override.enabled = enabled
            override.rollout_percentage = rollout_percentage
            override.notes = notes
            override.expires_at = expires_at
        else:
            override = FeatureFlagOverride(
                flag_id=flag.id,
                target_type=target_type,
                target_id=target_id,
                environment=environment,
                enabled=enabled,
                rollout_percentage=rollout_percentage,
                notes=notes,
                expires_at=expires_at,
            )
            self.db.add(override)

        await self.db.flush()
        await self._invalidate_cache(key)
        return override

    async def _get_flag_by_key(self, key: str) -> FeatureFlag | None:
        result = await self.db.execute(select(FeatureFlag).where(FeatureFlag.key == key))
        return result.scalar_one_or_none()

    async def _get_existing_override(
        self,
        flag_id: UUID,
        target_type: FlagTargetType,
        target_id: UUID | None,
        environment: str,
    ) -> FeatureFlagOverride | None:
        result = await self.db.execute(
            select(FeatureFlagOverride).where(
                FeatureFlagOverride.flag_id == flag_id,
                FeatureFlagOverride.target_type == target_type.value,
                FeatureFlagOverride.target_id.is_(target_id)
                if target_id is None
                else FeatureFlagOverride.target_id == target_id,
                FeatureFlagOverride.environment == environment,
            )
        )
        return result.scalar_one_or_none()

    async def _get_overrides(
        self,
        flag_id: UUID,
        environment: str,
    ) -> list[FeatureFlagOverride]:
        result = await self.db.execute(
            select(FeatureFlagOverride).where(
                FeatureFlagOverride.flag_id == flag_id,
                FeatureFlagOverride.environment.in_([environment, GLOBAL_ENVIRONMENT]),
            )
        )
        return list(result.scalars().all())

    def _select_override(
        self,
        overrides: list[FeatureFlagOverride],
        user_id: UUID | None,
        organization_id: UUID | None,
    ) -> FeatureFlagOverride | None:
        now = datetime.now(tz=UTC)

        def _valid(override: FeatureFlagOverride) -> bool:
            return not override.expires_at or override.expires_at > now

        for override in overrides:
            if (
                override.target_type == FlagTargetType.USER.value
                and user_id
                and override.target_id == user_id
                and _valid(override)
            ):
                return override

        for override in overrides:
            if (
                override.target_type == FlagTargetType.ORGANIZATION.value
                and organization_id
                and override.target_id == organization_id
                and _valid(override)
            ):
                return override

        for override in overrides:
            if (
                override.target_type == FlagTargetType.GLOBAL.value
                and _valid(override)
            ):
                return override

        return None

    @staticmethod
    def _resolve_state(
        flag: FeatureFlag,
        override: FeatureFlagOverride | None,
    ) -> tuple[bool, int | None]:
        if override:
            rollout = override.rollout_percentage or flag.rollout_percentage
            return override.enabled, rollout

        return flag.enabled, flag.rollout_percentage

    @staticmethod
    def _rollout_target(
        user_id: UUID | None,
        organization_id: UUID | None,
        flag_key: str,
    ) -> str:
        if user_id:
            return str(user_id)
        if organization_id:
            return str(organization_id)
        return flag_key

    @staticmethod
    def _apply_rollout(enabled: bool, rollout_percentage: int | None, target: str) -> bool:
        if not enabled:
            return False

        percentage = 100 if rollout_percentage is None else max(min(rollout_percentage, 100), 0)
        if percentage >= 100:
            return True
        if percentage <= 0:
            return False

        return FeatureFlagService._passes_rollout(target, percentage)

    @staticmethod
    def _passes_rollout(target: str, percentage: int) -> bool:
        digest = hashlib.sha256(target.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 100
        return bucket < percentage

    @staticmethod
    def _cache_key(
        key: str,
        environment: str,
        organization_id: UUID | None,
        user_id: UUID | None,
    ) -> str:
        org_part = str(organization_id) if organization_id else "none"
        user_part = str(user_id) if user_id else "none"
        return f"feature_flag:{key}:env:{environment}:org:{org_part}:user:{user_part}"

    async def _get_cached_value(self, cache_key: str) -> bool | None:
        if not self.cache:
            return None

        cached = await self.cache.get_json(cache_key)
        if cached is None:
            return None

        if isinstance(cached, dict) and "enabled" in cached:
            return bool(cached["enabled"])

        if isinstance(cached, bool):
            return cached

        return None

    async def _set_cached_value(self, cache_key: str, value: bool) -> None:
        if not self.cache:
            return
        await self.cache.set_json(cache_key, {"enabled": value}, ttl=self.cache_ttl_seconds)

    async def _invalidate_cache(self, key: str) -> None:
        if not self.cache:
            return
        await self.cache.invalidate_pattern(f"feature_flag:{key}:*")
