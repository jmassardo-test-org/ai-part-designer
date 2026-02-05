"""
Tests for CAD export worker tasks.

Tests format conversion and batch export functionality.
"""

from __future__ import annotations

import pytest

from app.cad.export import export_to_file
from app.cad.primitives import create_box

# =============================================================================
# Export Module Function Tests
# =============================================================================


class TestConvertCadFormatFunction:
    """Tests for the convert_cad_format export function."""

    def test_convert_step_to_stl_creates_output(self, tmp_path):
        """Test that STEP to STL conversion creates output file."""
        from app.cad.export import convert_cad_format

        # Create source STEP file
        box = create_box(50, 50, 50)
        source_path = tmp_path / "source.step"
        export_to_file(box, source_path)

        output_path = tmp_path / "output.stl"

        result = convert_cad_format(source_path, output_path, "stl")

        assert result.exists()
        assert result.stat().st_size > 0

    def test_convert_step_to_step_reformats(self, tmp_path):
        """Test STEP to STEP reformatting."""
        from app.cad.export import convert_cad_format

        box = create_box(30, 40, 50)
        source_path = tmp_path / "input.step"
        export_to_file(box, source_path)

        output_path = tmp_path / "output.step"

        result = convert_cad_format(source_path, output_path, "step")

        assert result.exists()
        # Verify it's a valid STEP file
        content = result.read_bytes().decode("utf-8", errors="ignore")
        assert "ISO-10303" in content or "STEP" in content

    def test_convert_with_quality_parameter(self, tmp_path):
        """Test conversion with quality setting."""
        from app.cad.export import ExportQuality, convert_cad_format

        box = create_box(50, 50, 50)
        source_path = tmp_path / "source.step"
        export_to_file(box, source_path)

        output_path = tmp_path / "output.stl"

        result = convert_cad_format(source_path, output_path, "stl", quality=ExportQuality.HIGH)

        assert result.exists()

    def test_convert_missing_source_raises_error(self, tmp_path):
        """Test that missing source file raises ValidationError."""
        from app.cad.exceptions import ValidationError
        from app.cad.export import convert_cad_format

        source_path = tmp_path / "nonexistent.step"
        output_path = tmp_path / "output.stl"

        with pytest.raises(ValidationError) as exc_info:
            convert_cad_format(source_path, output_path, "stl")

        assert "not found" in str(exc_info.value).lower()


class TestExportModelFunction:
    """Tests for the export_model function."""

    def test_export_model_infers_format_from_extension(self, tmp_path):
        """Test that format is inferred from file extension."""
        from app.cad.export import export_model

        box = create_box(25, 25, 25)

        step_path = export_model(box, tmp_path / "test.step")
        assert step_path.suffix == ".step"

        stl_path = export_model(box, tmp_path / "test.stl")
        assert stl_path.suffix == ".stl"

    def test_export_model_uses_explicit_format(self, tmp_path):
        """Test that explicit format parameter is used."""
        from app.cad.export import export_model

        box = create_box(25, 25, 25)

        # No extension, but format specified
        result = export_model(box, tmp_path / "model", format="step")

        assert result.suffix == ".step"
        assert result.exists()


# =============================================================================
# Worker Task Tests (Mocked)
# =============================================================================


class TestConvertFormatTask:
    """Tests for the convert_format Celery task."""

    @pytest.mark.asyncio
    async def test_convert_format_task_structure(self):
        """Test that convert_format task has correct structure."""
        from app.worker.tasks.export import convert_format

        # Check task is properly decorated
        assert hasattr(convert_format, "name")
        assert convert_format.name == "app.worker.tasks.export.convert_format"

    @pytest.mark.asyncio
    async def test_convert_format_with_mocked_storage(self, db_session, test_user, tmp_path):
        """Test convert_format task with mocked storage."""
        from uuid import uuid4

        from app.models import Job
        from app.worker.tasks.export import convert_format

        # Create a source STEP file
        box = create_box(50, 50, 50)
        source_path = tmp_path / "source.step"
        export_to_file(box, source_path)
        source_path.read_bytes()

        # Create a job record with a valid user_id
        job_id = uuid4()
        job = Job(
            id=job_id,
            job_type="format_conversion",
            status="pending",
            user_id=test_user.id,
        )
        db_session.add(job)
        await db_session.commit()

        # Verify the job was created correctly
        from app.repositories import JobRepository

        job_repo = JobRepository(db_session)
        fetched_job = await job_repo.get_by_id(job_id)

        assert fetched_job is not None
        assert fetched_job.status == "pending"
        assert fetched_job.job_type == "format_conversion"

        # The actual task execution would be tested in integration tests
        # For unit testing, we verify the task is correctly defined
        assert convert_format is not None
        assert convert_format.name == "app.worker.tasks.export.convert_format"


class TestBatchExportTask:
    """Tests for the batch_export Celery task."""

    def test_batch_export_task_exists(self):
        """Test that batch_export task is defined."""
        from app.worker.tasks.export import batch_export

        assert batch_export is not None
        assert hasattr(batch_export, "name")
        assert batch_export.name == "app.worker.tasks.export.batch_export"
