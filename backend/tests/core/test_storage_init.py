"""
Tests for storage initialization module.

Tests bucket creation, versioning configuration, lifecycle policies,
and idempotent behavior with fully mocked S3/MinIO clients.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError


# =============================================================================
# Helpers
# =============================================================================


def _make_client_error(code: str, message: str = "Error") -> ClientError:
    """Create a botocore ClientError with the given error code."""
    return ClientError(
        {"Error": {"Code": code, "Message": message}},
        "HeadBucket",
    )


def _build_mock_client() -> AsyncMock:
    """Build a fully-stubbed async S3 client mock for storage init tests."""
    client = AsyncMock()
    client.head_bucket = AsyncMock()
    client.create_bucket = AsyncMock()
    client.put_bucket_versioning = AsyncMock()
    client.put_bucket_lifecycle_configuration = AsyncMock()
    return client


def _mock_session(client: AsyncMock) -> MagicMock:
    """Wrap an async mock client in an aioboto3 session mock."""
    session = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session.client.return_value = ctx
    return session


# =============================================================================
# initialize_storage Tests
# =============================================================================


class TestInitializeStorage:
    """Tests for the initialize_storage top-level function."""

    @pytest.mark.asyncio
    async def test_initialize_storage_creates_missing_buckets(self) -> None:
        """Test that missing buckets are created during initialization."""
        client = _build_mock_client()
        # All buckets are missing (head_bucket raises 404)
        client.head_bucket = AsyncMock(
            side_effect=_make_client_error("404")
        )

        with patch("app.core.storage_init.aioboto3") as mock_aio:
            mock_aio.Session.return_value = _mock_session(client)

            from app.core.storage_init import initialize_storage

            result = await initialize_storage()

        assert len(result["buckets_created"]) > 0
        assert client.create_bucket.call_count == len(result["buckets_created"])
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_initialize_storage_enables_versioning_on_critical_buckets(
        self,
    ) -> None:
        """Test that versioning is enabled on DESIGNS, UPLOADS, EXPORTS buckets."""
        client = _build_mock_client()
        # All buckets already exist
        client.head_bucket = AsyncMock()

        with patch("app.core.storage_init.aioboto3") as mock_aio:
            mock_aio.Session.return_value = _mock_session(client)

            from app.core.storage_init import initialize_storage

            result = await initialize_storage()

        assert len(result["versioning_enabled"]) == 3
        assert client.put_bucket_versioning.call_count == 3
        # Verify all versioning calls used Status=Enabled
        for call in client.put_bucket_versioning.call_args_list:
            assert call.kwargs["VersioningConfiguration"]["Status"] == "Enabled"
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_initialize_storage_sets_temp_lifecycle_expiry(self) -> None:
        """Test that temp bucket gets a 7-day expiration lifecycle rule."""
        client = _build_mock_client()
        client.head_bucket = AsyncMock()

        with patch("app.core.storage_init.aioboto3") as mock_aio:
            mock_aio.Session.return_value = _mock_session(client)

            from app.core.storage_init import initialize_storage

            result = await initialize_storage()

        # Find the temp lifecycle config in put_bucket_lifecycle_configuration calls
        temp_calls = [
            c
            for c in client.put_bucket_lifecycle_configuration.call_args_list
            if "temp" in c.kwargs["Bucket"]
        ]
        assert len(temp_calls) == 1
        rules = temp_calls[0].kwargs["LifecycleConfiguration"]["Rules"]
        assert rules[0]["Expiration"]["Days"] == 7
        assert rules[0]["Status"] == "Enabled"

    @pytest.mark.asyncio
    async def test_initialize_storage_sets_designs_lifecycle_transition(
        self,
    ) -> None:
        """Test that designs bucket gets a 180-day GLACIER transition rule."""
        client = _build_mock_client()
        client.head_bucket = AsyncMock()

        with patch("app.core.storage_init.aioboto3") as mock_aio:
            mock_aio.Session.return_value = _mock_session(client)

            from app.core.storage_init import initialize_storage

            result = await initialize_storage()

        designs_calls = [
            c
            for c in client.put_bucket_lifecycle_configuration.call_args_list
            if "designs" in c.kwargs["Bucket"]
        ]
        assert len(designs_calls) == 1
        rules = designs_calls[0].kwargs["LifecycleConfiguration"]["Rules"]
        transitions = rules[0]["Transitions"]
        assert transitions[0]["Days"] == 180
        assert transitions[0]["StorageClass"] == "GLACIER"

    @pytest.mark.asyncio
    async def test_initialize_storage_is_idempotent(self) -> None:
        """Test that running initialize_storage twice produces same result."""
        client = _build_mock_client()
        # First call: all buckets missing
        call_count = 0
        original_head = AsyncMock(side_effect=_make_client_error("404"))

        async def head_bucket_effect(**kwargs: Any) -> None:
            nonlocal call_count
            call_count += 1
            # Simulate buckets existing on second full pass
            if call_count > 6:
                return None
            raise _make_client_error("404")

        client.head_bucket = AsyncMock(side_effect=head_bucket_effect)

        with patch("app.core.storage_init.aioboto3") as mock_aio:
            mock_aio.Session.return_value = _mock_session(client)

            from app.core.storage_init import initialize_storage

            result1 = await initialize_storage()
            result2 = await initialize_storage()

        # Second run should report buckets as already existing
        assert len(result2["buckets_existed"]) > 0
        assert result2["errors"] == []

    @pytest.mark.asyncio
    async def test_initialize_storage_handles_bucket_already_exists(
        self,
    ) -> None:
        """Test that existing buckets are skipped without error."""
        client = _build_mock_client()
        # All buckets already exist (head_bucket succeeds)
        client.head_bucket = AsyncMock()

        with patch("app.core.storage_init.aioboto3") as mock_aio:
            mock_aio.Session.return_value = _mock_session(client)

            from app.core.storage_init import initialize_storage

            result = await initialize_storage()

        assert result["buckets_created"] == []
        assert len(result["buckets_existed"]) > 0
        client.create_bucket.assert_not_called()
        assert result["errors"] == []


# =============================================================================
# _enable_versioning Tests
# =============================================================================


class TestEnableVersioning:
    """Tests for the _enable_versioning helper."""

    @pytest.mark.asyncio
    async def test_enable_versioning_calls_correct_api(self) -> None:
        """Test that _enable_versioning calls put_bucket_versioning with Enabled."""
        client = _build_mock_client()

        from app.core.storage_init import _enable_versioning

        await _enable_versioning(client, "test-bucket")

        client.put_bucket_versioning.assert_called_once_with(
            Bucket="test-bucket",
            VersioningConfiguration={"Status": "Enabled"},
        )


# =============================================================================
# _configure_temp_lifecycle Tests
# =============================================================================


class TestConfigureTempLifecycle:
    """Tests for the _configure_temp_lifecycle helper."""

    @pytest.mark.asyncio
    async def test_configure_temp_lifecycle_7_day_expiry(self) -> None:
        """Test that temp lifecycle sets a 7-day expiration rule."""
        client = _build_mock_client()

        from app.core.storage_init import _configure_temp_lifecycle

        await _configure_temp_lifecycle(client, "test-temp-bucket")

        client.put_bucket_lifecycle_configuration.assert_called_once()
        call_kwargs = client.put_bucket_lifecycle_configuration.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-temp-bucket"
        rules = call_kwargs["LifecycleConfiguration"]["Rules"]
        assert len(rules) == 1
        assert rules[0]["ID"] == "expire-temp-objects"
        assert rules[0]["Expiration"]["Days"] == 7
        assert rules[0]["Status"] == "Enabled"


# =============================================================================
# _configure_designs_lifecycle Tests
# =============================================================================


class TestConfigureDesignsLifecycle:
    """Tests for the _configure_designs_lifecycle helper."""

    @pytest.mark.asyncio
    async def test_configure_designs_lifecycle_180_day_glacier_transition(
        self,
    ) -> None:
        """Test that designs lifecycle sets a 180-day GLACIER transition rule."""
        client = _build_mock_client()

        from app.core.storage_init import _configure_designs_lifecycle

        await _configure_designs_lifecycle(client, "test-designs-bucket")

        client.put_bucket_lifecycle_configuration.assert_called_once()
        call_kwargs = client.put_bucket_lifecycle_configuration.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-designs-bucket"
        rules = call_kwargs["LifecycleConfiguration"]["Rules"]
        assert len(rules) == 1
        assert rules[0]["ID"] == "transition-designs-to-glacier"
        assert rules[0]["Transitions"][0]["Days"] == 180
        assert rules[0]["Transitions"][0]["StorageClass"] == "GLACIER"


# =============================================================================
# _ensure_bucket_exists Tests
# =============================================================================


class TestEnsureBucketExists:
    """Tests for the _ensure_bucket_exists helper."""

    @pytest.mark.asyncio
    async def test_ensure_bucket_exists_creates_when_missing(self) -> None:
        """Test that a missing bucket is created and True is returned."""
        client = _build_mock_client()
        client.head_bucket = AsyncMock(
            side_effect=_make_client_error("404")
        )

        from app.core.storage_init import _ensure_bucket_exists

        created = await _ensure_bucket_exists(client, "new-bucket")

        assert created is True
        client.create_bucket.assert_called_once_with(Bucket="new-bucket")

    @pytest.mark.asyncio
    async def test_ensure_bucket_exists_skips_when_present(self) -> None:
        """Test that an existing bucket is not recreated and False is returned."""
        client = _build_mock_client()
        client.head_bucket = AsyncMock()

        from app.core.storage_init import _ensure_bucket_exists

        created = await _ensure_bucket_exists(client, "existing-bucket")

        assert created is False
        client.create_bucket.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_bucket_exists_raises_on_unexpected_error(
        self,
    ) -> None:
        """Test that unexpected ClientErrors are re-raised."""
        client = _build_mock_client()
        client.head_bucket = AsyncMock(
            side_effect=_make_client_error("403", "Forbidden")
        )

        from app.core.storage_init import _ensure_bucket_exists

        with pytest.raises(ClientError):
            await _ensure_bucket_exists(client, "forbidden-bucket")
