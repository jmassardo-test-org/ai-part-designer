"""
Tests for the archive_old_designs Celery task.

Tests task execution, return values, and edge cases
with mocked dependencies following backup task test patterns.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


class TestArchiveOldDesignsTask:
    """Tests for the archive_old_designs Celery task."""

    def test_archive_old_designs_task_processes_eligible_designs(self) -> None:
        """Test that archive_old_designs processes eligible designs."""
        mock_design_1 = MagicMock()
        mock_design_1.id = "design-1"
        mock_design_1.archived_at = None

        mock_design_2 = MagicMock()
        mock_design_2.id = "design-2"
        mock_design_2.archived_at = None

        mock_service = MagicMock()
        mock_service.find_archivable_designs = AsyncMock(
            return_value=[mock_design_1, mock_design_2]
        )
        mock_service.archive_design = AsyncMock(return_value="designs/test/archive")

        with (
            patch(
                "app.services.design_archive.DesignArchiveService",
                return_value=mock_service,
            ),
            patch("app.core.database.async_session_maker") as mock_session_maker,
        ):
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.worker.tasks.maintenance import archive_old_designs

            result = archive_old_designs()

            assert result["designs_found"] == 2
            assert result["designs_archived"] == 2
            assert len(result["errors"]) == 0

    def test_archive_old_designs_task_returns_summary(self) -> None:
        """Test that archive_old_designs returns expected summary keys."""
        mock_service = MagicMock()
        mock_service.find_archivable_designs = AsyncMock(return_value=[])

        with (
            patch(
                "app.services.design_archive.DesignArchiveService",
                return_value=mock_service,
            ),
            patch("app.core.database.async_session_maker") as mock_session_maker,
        ):
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.worker.tasks.maintenance import archive_old_designs

            result = archive_old_designs()

            assert isinstance(result, dict)
            assert "designs_found" in result
            assert "designs_archived" in result
            assert "errors" in result

    def test_archive_old_designs_task_handles_empty_result(self) -> None:
        """Test that archive_old_designs handles no eligible designs gracefully."""
        mock_service = MagicMock()
        mock_service.find_archivable_designs = AsyncMock(return_value=[])

        with (
            patch(
                "app.services.design_archive.DesignArchiveService",
                return_value=mock_service,
            ),
            patch("app.core.database.async_session_maker") as mock_session_maker,
        ):
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.worker.tasks.maintenance import archive_old_designs

            result = archive_old_designs()

            assert result["designs_found"] == 0
            assert result["designs_archived"] == 0
            assert len(result["errors"]) == 0

    def test_archive_old_designs_task_handles_archive_errors(self) -> None:
        """Test that errors during individual design archival are captured."""
        mock_design = MagicMock()
        mock_design.id = "design-fail"

        mock_service = MagicMock()
        mock_service.find_archivable_designs = AsyncMock(return_value=[mock_design])
        mock_service.archive_design = AsyncMock(side_effect=RuntimeError("Storage failure"))

        with (
            patch(
                "app.services.design_archive.DesignArchiveService",
                return_value=mock_service,
            ),
            patch("app.core.database.async_session_maker") as mock_session_maker,
        ):
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.worker.tasks.maintenance import archive_old_designs

            result = archive_old_designs()

            assert result["designs_found"] == 1
            assert result["designs_archived"] == 0
            assert len(result["errors"]) == 1
            assert "Storage failure" in result["errors"][0]
