"""
Tests for the check_storage_health Celery task.

Tests health check accessibility, versioning verification, degraded
bucket reporting, and empty bucket handling, all with mocked storage.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_mock_storage_client(
    *,
    failing_buckets: set[str] | None = None,
    versioning_responses: dict[str, dict[str, str]] | None = None,
) -> MagicMock:
    """Build a mock StorageClient for health-check tests.

    Args:
        failing_buckets: Set of bucket values whose list_files should fail.
        versioning_responses: Map of bucket name → get_bucket_versioning response.

    Returns:
        A configured MagicMock mimicking StorageClient.
    """
    failing = failing_buckets or set()
    versioning = versioning_responses or {}

    mock_client = MagicMock()
    mock_client._get_bucket_name = MagicMock(
        side_effect=lambda b: f"ai-part-designer-test-{b.value}"
    )

    async def list_files_side_effect(
        bucket: Any, *, max_keys: int = 1000
    ) -> list[dict[str, Any]]:
        if bucket.value in failing:
            raise ConnectionError(f"Cannot reach bucket {bucket.value}")
        return []

    mock_client.list_files = AsyncMock(side_effect=list_files_side_effect)

    # Build an async context manager for _get_client
    inner_client = AsyncMock()

    async def get_bucket_versioning_side_effect(
        **kwargs: Any,
    ) -> dict[str, str]:
        bucket_name = kwargs.get("Bucket", "")
        return versioning.get(bucket_name, {"Status": "Enabled"})

    inner_client.get_bucket_versioning = AsyncMock(
        side_effect=get_bucket_versioning_side_effect,
    )

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=inner_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_client._get_client = MagicMock(return_value=ctx)

    return mock_client


# =============================================================================
# check_storage_health Tests
# =============================================================================


class TestCheckStorageHealth:
    """Tests for the check_storage_health Celery task."""

    def test_check_storage_health_all_healthy(self) -> None:
        """Test that all-healthy buckets produce 'healthy' overall status."""
        mock_client = _make_mock_storage_client()

        with (
            patch(
                "app.worker.tasks.maintenance.STORAGE_HEALTH_GAUGE", None
            ),
            patch(
                "app.core.storage.storage_client", mock_client
            ),
        ):
            from app.worker.tasks.maintenance import check_storage_health

            result = check_storage_health()

        assert result["overall_status"] == "healthy"
        assert "checked_at" in result
        for bucket_info in result["buckets"].values():
            assert bucket_info["accessible"] is True

    def test_check_storage_health_degraded_bucket(self) -> None:
        """Test that an inaccessible bucket degrades overall status."""
        mock_client = _make_mock_storage_client(failing_buckets={"exports"})

        with (
            patch(
                "app.worker.tasks.maintenance.STORAGE_HEALTH_GAUGE", None
            ),
            patch(
                "app.core.storage.storage_client", mock_client
            ),
        ):
            from app.worker.tasks.maintenance import check_storage_health

            result = check_storage_health()

        assert result["overall_status"] == "degraded"
        assert result["buckets"]["exports"]["accessible"] is False
        assert result["buckets"]["exports"]["status"] == "error"
        assert "error" in result["buckets"]["exports"]

    def test_check_storage_health_versioning_disabled_flagged(self) -> None:
        """Test that disabled versioning on a critical bucket is flagged as warning."""
        designs_bucket = "ai-part-designer-test-designs"
        mock_client = _make_mock_storage_client(
            versioning_responses={designs_bucket: {"Status": "Suspended"}}
        )

        with (
            patch(
                "app.worker.tasks.maintenance.STORAGE_HEALTH_GAUGE", None
            ),
            patch(
                "app.core.storage.storage_client", mock_client
            ),
        ):
            from app.worker.tasks.maintenance import check_storage_health

            result = check_storage_health()

        assert result["overall_status"] == "degraded"
        designs = result["buckets"]["designs"]
        assert designs["versioning_status"] == "Suspended"
        assert designs["status"] == "warning"

    def test_check_storage_health_empty_bucket_still_healthy(self) -> None:
        """Test that an empty bucket (no objects) is still reported healthy."""
        mock_client = _make_mock_storage_client()
        # list_files returns empty list by default — that's "empty but healthy"

        with (
            patch(
                "app.worker.tasks.maintenance.STORAGE_HEALTH_GAUGE", None
            ),
            patch(
                "app.core.storage.storage_client", mock_client
            ),
        ):
            from app.worker.tasks.maintenance import check_storage_health

            result = check_storage_health()

        assert result["overall_status"] == "healthy"
        for bucket_info in result["buckets"].values():
            assert bucket_info["accessible"] is True
            assert bucket_info["status"] == "healthy"

    def test_check_storage_health_emits_prometheus_gauge(self) -> None:
        """Test that the Prometheus gauge is set when available."""
        mock_client = _make_mock_storage_client()
        mock_gauge = MagicMock()

        with (
            patch(
                "app.worker.tasks.maintenance.STORAGE_HEALTH_GAUGE", mock_gauge
            ),
            patch(
                "app.core.storage.storage_client", mock_client
            ),
        ):
            from app.worker.tasks.maintenance import check_storage_health

            result = check_storage_health()

        mock_gauge.set.assert_called_once_with(1.0)
