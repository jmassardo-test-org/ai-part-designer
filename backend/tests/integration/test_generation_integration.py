"""
Integration tests for CAD generation workflows.

Tests end-to-end generation from templates and AI prompts.
"""

from __future__ import annotations

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from app.cad.primitives import create_box, create_cylinder
from app.cad.export import export_step, export_stl


# =============================================================================
# CAD Primitive Generation Integration Tests
# =============================================================================

class TestCADPrimitiveGenerationIntegration:
    """Integration tests for CAD primitive generation."""
    
    def test_create_box_generates_valid_geometry(self):
        """Test that box creation produces valid CAD geometry."""
        result = create_box(100, 50, 25)
        
        assert result is not None
        
        # Verify geometry properties
        bbox = result.bounding_box()
        assert round(bbox.size.X, 1) == 100.0
        assert round(bbox.size.Y, 1) == 50.0
        assert round(bbox.size.Z, 1) == 25.0
        
        # Verify volume
        volume = result.volume
        expected_volume = 100 * 50 * 25
        assert round(volume, 0) == expected_volume
    
    def test_create_cylinder_generates_valid_geometry(self):
        """Test that cylinder creation produces valid geometry."""
        result = create_cylinder(radius=25, height=100)
        
        assert result is not None
        
        # Verify height
        bbox = result.bounding_box()
        assert round(bbox.size.Z, 0) == 100
        
        # Diameter should be 50
        assert round(bbox.size.X, 0) == 50
        assert round(bbox.size.Y, 0) == 50
    
    def test_box_to_step_creates_valid_file(self, tmp_path):
        """Test that box export produces valid STEP file."""
        from app.cad.export import export_to_file
        
        # Generate shape
        box = create_box(50, 50, 50)
        
        # Export to STEP
        step_path = tmp_path / "test_output.step"
        export_to_file(box, step_path)
        
        assert step_path.exists()
        assert step_path.stat().st_size > 0
        
        # Verify it's valid STEP content
        content = step_path.read_bytes().decode("utf-8", errors="ignore")
        assert "ISO-10303" in content or "STEP" in content
    
    def test_cylinder_to_stl_creates_valid_file(self, tmp_path):
        """Test that cylinder export produces valid STL file."""
        from app.cad.export import export_to_file
        
        # Generate shape
        cylinder = create_cylinder(radius=25, height=100)
        
        # Export to STL
        stl_path = tmp_path / "test_output.stl"
        export_to_file(cylinder, stl_path)
        
        assert stl_path.exists()
        assert stl_path.stat().st_size > 0


# =============================================================================
# Job Creation Integration Tests
# =============================================================================

class TestJobCreationIntegration:
    """Integration tests for job creation and tracking."""
    
    @pytest.mark.asyncio
    async def test_create_job_with_valid_data(self, db_session, test_user):
        """Test creating a job record in database."""
        from app.models import Job
        from app.repositories import JobRepository
        
        job_id = uuid4()
        job = Job(
            id=job_id,
            job_type="cad_generation",
            status="pending",
            user_id=test_user.id,
            input_params={"template": "simple-box", "length": 100},
        )
        db_session.add(job)
        await db_session.commit()
        
        # Verify job was created
        job_repo = JobRepository(db_session)
        fetched_job = await job_repo.get_by_id(job_id)
        
        assert fetched_job is not None
        assert fetched_job.status == "pending"
        assert fetched_job.input_params["template"] == "simple-box"
    
    @pytest.mark.asyncio
    async def test_update_job_progress(self, db_session, test_user):
        """Test updating job progress."""
        from app.models import Job
        from app.repositories import JobRepository
        
        job_id = uuid4()
        job = Job(
            id=job_id,
            job_type="cad_generation",
            status="pending",
            user_id=test_user.id,
        )
        db_session.add(job)
        await db_session.commit()
        
        job_repo = JobRepository(db_session)
        
        # Update progress
        await job_repo.update(
            job_id,
            status="running",
            progress=50,
            progress_message="Generating CAD model",
        )
        await db_session.commit()
        
        # Verify update
        updated_job = await job_repo.get_by_id(job_id)
        assert updated_job.status == "running"
        assert updated_job.progress == 50
        assert updated_job.progress_message == "Generating CAD model"
    
    @pytest.mark.asyncio
    async def test_complete_job_with_result(self, db_session, test_user):
        """Test completing a job with result data."""
        from app.models import Job
        from app.repositories import JobRepository
        
        job_id = uuid4()
        job = Job(
            id=job_id,
            job_type="cad_generation",
            status="running",
            user_id=test_user.id,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(job)
        await db_session.commit()
        
        job_repo = JobRepository(db_session)
        
        result_data = {
            "files": {"step": "https://example.com/model.step"},
            "geometry_info": {"volume": 125000},
        }
        
        await job_repo.update(
            job_id,
            status="completed",
            progress=100,
            completed_at=datetime.now(timezone.utc),
            result=result_data,
        )
        await db_session.commit()
        
        # Verify completion
        completed_job = await job_repo.get_by_id(job_id)
        assert completed_job.status == "completed"
        assert completed_job.result["files"]["step"] == "https://example.com/model.step"


# =============================================================================
# Design Creation Integration Tests
# =============================================================================

class TestDesignCreationIntegration:
    """Integration tests for design creation flow."""
    
    @pytest.mark.asyncio
    async def test_job_creation_and_update(self, db_session, test_user):
        """Test creating and updating job records."""
        from app.models import Job
        from app.repositories import JobRepository
        
        job_id = uuid4()
        job = Job(
            id=job_id,
            job_type="cad_generation",
            status="pending",
            user_id=test_user.id,
        )
        db_session.add(job)
        await db_session.commit()
        
        job_repo = JobRepository(db_session)
        fetched_job = await job_repo.get_by_id(job_id)
        
        assert fetched_job is not None
        assert fetched_job.status == "pending"


# =============================================================================
# Export Flow Integration Tests
# =============================================================================

class TestExportFlowIntegration:
    """Integration tests for export workflows."""
    
    def test_export_step_and_stl_from_same_shape(self, tmp_path):
        """Test exporting both STEP and STL from same geometry."""
        from app.cad.export import export_to_file
        
        # Create a shape
        box = create_box(50, 50, 50)
        
        # Export to both formats
        step_path = tmp_path / "model.step"
        stl_path = tmp_path / "model.stl"
        
        export_to_file(box, step_path)
        export_to_file(box, stl_path)
        
        assert step_path.exists()
        assert stl_path.exists()
        
        # Both should have content
        assert step_path.stat().st_size > 0
        assert stl_path.stat().st_size > 0
    
    def test_format_conversion_preserves_geometry(self, tmp_path):
        """Test that format conversion maintains geometry accuracy."""
        from app.cad.export import export_to_file, convert_cad_format
        from build123d import Part, Compound, import_step
        
        # Create original shape
        original = create_box(100, 50, 25)
        original_volume = original.volume
        
        # Export to STEP
        step_path = tmp_path / "original.step"
        export_to_file(original, step_path)
        
        # Re-import and check volume
        reimported = import_step(str(step_path))
        reimported_volume = reimported.volume
        
        # STEP should preserve exact geometry
        assert abs(original_volume - reimported_volume) < 1.0
    
    def test_stl_quality_affects_file_size(self, tmp_path):
        """Test that STL quality settings affect output."""
        from app.cad.export import export_stl, ExportQuality
        
        # Create curved shape (sphere-like)
        cylinder = create_cylinder(radius=50, height=100)
        
        # Export at different qualities
        draft_data = export_stl(cylinder, quality=ExportQuality.DRAFT)
        high_data = export_stl(cylinder, quality=ExportQuality.HIGH)
        
        # Higher quality = more triangles = larger file
        assert len(high_data) > len(draft_data)
