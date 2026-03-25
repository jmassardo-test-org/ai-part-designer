"""
Tests for the require_feature_flag dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import (
    get_current_user_optional,
    get_feature_flag_service,
    require_feature_flag,
)
from app.models.feature_flag import FeatureFlag, FlagTargetType
from app.services.feature_flags import FeatureFlagService

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User


class InMemoryCache:
    """Minimal cache stub for dependency tests."""

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
async def feature_flag(db_session: AsyncSession) -> FeatureFlag:
    """Create a feature flag for dependency checks."""
    flag = FeatureFlag(key="beta-access", enabled=False, rollout_percentage=100)
    db_session.add(flag)
    await db_session.commit()
    await db_session.refresh(flag)
    return flag


@pytest_asyncio.fixture
async def test_app(
    db_session: AsyncSession,
    feature_flag: FeatureFlag,
    test_user: User,
) -> AsyncIterator[tuple[AsyncClient, FeatureFlagService, FeatureFlag, InMemoryCache]]:
    """Build a lightweight FastAPI app with dependency overrides."""
    app = FastAPI()
    cache = InMemoryCache()
    service = FeatureFlagService(db_session, cache=cache, cache_ttl_seconds=60)

    async def override_flag_service() -> FeatureFlagService:
        return service

    async def override_user() -> User:
        return test_user

    app.dependency_overrides[get_feature_flag_service] = override_flag_service
    app.dependency_overrides[get_current_user_optional] = override_user

    @app.get("/protected")
    async def protected_route(
        _flag: None = Depends(require_feature_flag(feature_flag.key)),
    ) -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/missing")
    async def missing_flag(
        _flag: None = Depends(require_feature_flag("nonexistent-flag")),
    ) -> dict[str, str]:
        return {"status": "missing"}

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, service, feature_flag, cache


@pytest.mark.asyncio
async def test_dependency_blocks_when_disabled(
    test_app: tuple[AsyncClient, FeatureFlagService, FeatureFlag, InMemoryCache],
) -> None:
    """Dependency should return 403 when flag is disabled."""
    client, _service, _flag, _cache = test_app

    response = await client.get("/protected")

    assert response.status_code == 403
    assert response.json()["detail"]["flag"] == "beta-access"


@pytest.mark.asyncio
async def test_dependency_allows_when_enabled(
    test_app: tuple[AsyncClient, FeatureFlagService, FeatureFlag, InMemoryCache],
    test_user: User,
) -> None:
    """Enabling an override should allow access."""
    client, service, flag, _cache = test_app

    await service.set_override(
        flag.key,
        target_type=FlagTargetType.USER,
        enabled=True,
        target_id=test_user.id,
    )

    response = await client.get("/protected")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_dependency_returns_404_for_missing_flag(
    test_app: tuple[AsyncClient, FeatureFlagService, FeatureFlag, InMemoryCache],
) -> None:
    """Missing flag should produce a 404 to signal misconfiguration."""
    client, _service, _flag, _cache = test_app

    response = await client.get("/missing")

    assert response.status_code == 404
