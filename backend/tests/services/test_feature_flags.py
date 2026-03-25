"""
Tests for the feature flag service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.feature_flag import FeatureFlag, FeatureFlagOverride, FlagTargetType
from app.services.feature_flags import FeatureFlagService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User


class InMemoryCache:
    """Minimal in-memory cache stub for RedisClient behavior."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.invalidated: list[str] = []

    async def get_json(self, key: str) -> Any | None:
        return self.store.get(key)

    async def set_json(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        self.store[key] = value

    async def invalidate_pattern(self, pattern: str) -> int:
        self.invalidated.append(pattern)
        prefix = pattern.rstrip("*")
        to_delete = [k for k in self.store if k.startswith(prefix)]
        for key in to_delete:
            self.store.pop(key, None)
        return len(to_delete)


@pytest_asyncio.fixture
async def flag(db_session: AsyncSession) -> FeatureFlag:
    """Create a basic feature flag for tests."""
    feature_flag = FeatureFlag(
        key=f"flag-{uuid4().hex[:8]}",
        enabled=True,
        rollout_percentage=100,
    )
    db_session.add(feature_flag)
    await db_session.commit()
    await db_session.refresh(feature_flag)
    return feature_flag


@pytest.mark.asyncio
async def test_evaluate_flag_returns_default(db_session: AsyncSession, flag: FeatureFlag) -> None:
    """Default flag state is returned when no overrides exist."""
    service = FeatureFlagService(db_session, cache=None)

    result = await service.evaluate_flag(flag.key)

    assert result is True


@pytest.mark.asyncio
async def test_user_override_precedence(
    db_session: AsyncSession,
    flag: FeatureFlag,
    test_user: User,
) -> None:
    """User overrides should win over organization or global overrides."""
    # Organization override disabled
    org_id = uuid4()
    org_override = FeatureFlagOverride(
        flag_id=flag.id,
        target_type=FlagTargetType.ORGANIZATION.value,
        target_id=org_id,
        enabled=False,
    )
    db_session.add(org_override)

    # User override enabled
    user_override = FeatureFlagOverride(
        flag_id=flag.id,
        target_type=FlagTargetType.USER.value,
        target_id=test_user.id,
        enabled=True,
    )
    db_session.add(user_override)
    await db_session.commit()

    service = FeatureFlagService(db_session, cache=None)
    result = await service.evaluate_flag(
        flag.key,
        user_id=test_user.id,
        organization_id=org_id,
    )

    assert result is True


@pytest.mark.asyncio
async def test_rollout_percentage_applied(
    db_session: AsyncSession,
    flag: FeatureFlag,
    test_user: User,
) -> None:
    """Rollout percentage should deterministically gate access."""
    flag.rollout_percentage = 50
    await db_session.commit()

    service = FeatureFlagService(db_session, cache=None)
    expected = service._passes_rollout(str(test_user.id), 50)

    result = await service.evaluate_flag(flag.key, user_id=test_user.id)

    assert result == expected


@pytest.mark.asyncio
async def test_cache_short_circuits_lookup(flag: FeatureFlag, test_user: User) -> None:
    """Cached value should be returned without hitting the database."""
    cache = InMemoryCache()
    cache_key = FeatureFlagService._cache_key(
        flag.key,
        "production",
        None,
        test_user.id,
    )
    cache.store[cache_key] = {"enabled": False}

    # Deliberately pass a broken session to ensure cache is used
    service = FeatureFlagService(db=None, cache=cache)  # type: ignore[arg-type]
    result = await service.evaluate_flag(flag.key, user_id=test_user.id)

    assert result is False


@pytest.mark.asyncio
async def test_set_override_invalidates_cache(
    db_session: AsyncSession,
    flag: FeatureFlag,
    test_user: User,
) -> None:
    """Setting an override should invalidate cached evaluations."""
    cache = InMemoryCache()
    service = FeatureFlagService(db_session, cache=cache)

    override = await service.set_override(
        flag.key,
        target_type=FlagTargetType.USER,
        enabled=True,
        target_id=test_user.id,
    )

    assert override.enabled is True
    assert cache.invalidated == [f"feature_flag:{flag.key}:*"]
