"""
Tests for component extraction Celery tasks.

Tests the extract_component_task and batch_extract_task.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.worker.tasks.extraction import (
    extract_component_task,
    batch_extract_task,
    _extract_from_datasheet,
    _extract_from_cad,
    _download_file,
    _update_component_specs,
)


# =============================================================================
# Task Registration Tests
# =============================================================================

class TestTaskRegistration:
    """Tests for task registration and configuration."""
    
    def test_extract_component_task_has_correct_name(self):
        """Verify task is registered with correct name."""
        assert extract_component_task.name == "extraction.extract_component"
    
    def test_batch_extract_task_has_correct_name(self):
        """Verify batch task is registered with correct name."""
        assert batch_extract_task.name == "extraction.batch_extract"
    
    def test_extract_task_has_retry_config(self):
        """Verify extraction task has retry configuration."""
        assert extract_component_task.max_retries == 3
        assert extract_component_task.default_retry_delay == 60


# =============================================================================
# Extraction Helper Tests
# =============================================================================

class TestExtractionHelpers:
    """Tests for extraction helper functions."""
    
    @pytest.mark.asyncio
    async def test_extract_from_datasheet_no_url(self):
        """Should return None when component has no datasheet URL."""
        component = MagicMock()
        component.datasheet_url = None
        component.id = uuid4()
        
        result = await _extract_from_datasheet(component)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_extract_from_cad_no_url(self):
        """Should return None when component has no CAD file URL."""
        component = MagicMock()
        component.cad_file_url = None
        component.id = uuid4()
        
        result = await _extract_from_cad(component)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_download_file_handles_invalid_url(self):
        """Should return None for invalid URLs."""
        result = await _download_file("invalid-url")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_component_specs_prefers_cad_dimensions(self):
        """Should prefer CAD dimensions over datasheet dimensions."""
        from sqlalchemy.ext.asyncio import AsyncSession
        
        db = AsyncMock(spec=AsyncSession)
        component = MagicMock()
        component.dimensions = None
        
        extracted_data = {
            "cad": {
                "dimensions": {"length": 100, "width": 50, "height": 25},
                "confidence": 0.95,
            },
            "datasheet": {
                "dimensions": {"length": 99, "width": 49, "height": 24},
                "confidence": 0.80,
            },
        }
        
        await _update_component_specs(db, component, extracted_data)
        
        # Should use CAD dimensions
        assert component.dimensions["length"] == 100
        assert component.dimensions["width"] == 50
    
    @pytest.mark.asyncio
    async def test_update_component_specs_falls_back_to_datasheet(self):
        """Should use datasheet dimensions when CAD is missing."""
        from sqlalchemy.ext.asyncio import AsyncSession
        
        db = AsyncMock(spec=AsyncSession)
        component = MagicMock()
        component.dimensions = None
        
        extracted_data = {
            "datasheet": {
                "dimensions": {"length": 99, "width": 49, "height": 24},
                "confidence": 0.80,
            },
        }
        
        await _update_component_specs(db, component, extracted_data)
        
        # Should use datasheet dimensions
        assert component.dimensions["length"] == 99
        assert component.dimensions["width"] == 49


# =============================================================================
# Datasheet Extraction Tests
# =============================================================================

class TestDatasheetExtraction:
    """Tests for datasheet extraction logic."""
    
    @pytest.mark.asyncio
    async def test_extract_from_datasheet_without_api_key(self):
        """Should return low confidence result when API key missing."""
        component = MagicMock()
        component.datasheet_url = "https://example.com/datasheet.pdf"
        component.id = uuid4()
        component.name = "Test Component"
        component.category = "sbc"
        
        with patch("app.worker.tasks.extraction._download_file") as mock_download:
            mock_download.return_value = b"fake pdf content"
            
            with patch("app.worker.tasks.extraction.pdf_processor") as mock_pdf:
                mock_pdf.convert_to_images = AsyncMock(return_value=[b"image data"])
                
                with patch("app.core.config.settings") as mock_settings:
                    mock_settings.ANTHROPIC_API_KEY = None
                    
                    result = await _extract_from_datasheet(component)
                    
                    assert result is not None
                    assert result.get("confidence") == 0.0
    
    @pytest.mark.asyncio
    async def test_extract_from_datasheet_handles_download_failure(self):
        """Should return None when download fails."""
        component = MagicMock()
        component.datasheet_url = "https://example.com/datasheet.pdf"
        component.id = uuid4()
        
        with patch("app.worker.tasks.extraction._download_file") as mock_download:
            mock_download.return_value = None
            
            result = await _extract_from_datasheet(component)
            
            assert result is None


# =============================================================================
# CAD Extraction Tests
# =============================================================================

class TestCADExtraction:
    """Tests for CAD file extraction logic."""
    
    @pytest.mark.asyncio
    async def test_extract_from_cad_unsupported_format(self):
        """Should return low confidence for unsupported CAD formats."""
        component = MagicMock()
        component.cad_file_url = "https://example.com/model.iges"
        component.id = uuid4()
        
        with patch("app.worker.tasks.extraction._download_file") as mock_download:
            mock_download.return_value = b"fake cad content"
            
            result = await _extract_from_cad(component)
            
            assert result is not None
            assert result.get("confidence") == 0.0
            assert "not fully supported" in result.get("message", "")
    
    @pytest.mark.asyncio
    async def test_extract_from_cad_handles_download_failure(self):
        """Should return None when CAD download fails."""
        component = MagicMock()
        component.cad_file_url = "https://example.com/model.step"
        component.id = uuid4()
        
        with patch("app.worker.tasks.extraction._download_file") as mock_download:
            mock_download.return_value = None
            
            result = await _extract_from_cad(component)
            
            assert result is None


# =============================================================================
# Task Execution Tests
# =============================================================================

class TestTaskExecution:
    """Tests for task execution flow."""
    
    def test_extract_component_task_accepts_job_id(self):
        """Verify task accepts job_id parameter."""
        # Just verify the task signature
        import inspect
        sig = inspect.signature(extract_component_task)
        params = list(sig.parameters.keys())
        
        # First param is self (bound task), second is job_id
        assert "job_id" in params
    
    def test_batch_extract_task_accepts_component_ids(self):
        """Verify batch task accepts component_ids list."""
        import inspect
        sig = inspect.signature(batch_extract_task)
        params = list(sig.parameters.keys())
        
        assert "component_ids" in params


# =============================================================================
# Integration-style Tests
# =============================================================================

class TestExtractionIntegration:
    """Integration-style tests for extraction workflow."""
    
    def test_extraction_task_is_callable(self):
        """Verify extraction task is properly registered and callable."""
        assert callable(extract_component_task)
        assert callable(extract_component_task.delay)
        assert callable(extract_component_task.apply_async)
    
    def test_batch_task_is_callable(self):
        """Verify batch task is properly registered and callable."""
        assert callable(batch_extract_task)
        assert callable(batch_extract_task.delay)
        assert callable(batch_extract_task.apply_async)
    
    @pytest.mark.asyncio
    async def test_component_specs_merge_logic(self):
        """Test that specs from multiple sources merge correctly."""
        from sqlalchemy.ext.asyncio import AsyncSession
        
        db = AsyncMock(spec=AsyncSession)
        component = MagicMock()
        component.dimensions = None
        component.mounting_holes = None
        component.connectors = None
        component.clearance_zones = None
        
        extracted_data = {
            "cad": {
                "dimensions": {"length": 100, "width": 50, "height": 25},
            },
            "datasheet": {
                "mounting_holes": [{"x": 5, "y": 5, "diameter": 3.2}],
                "connectors": [{"name": "USB-C", "type": "connector"}],
                "cutouts": [{"name": "Vent", "width": 20}],
            },
        }
        
        await _update_component_specs(db, component, extracted_data)
        
        # Verify all fields updated
        assert component.dimensions is not None
        assert component.mounting_holes is not None
        assert component.connectors is not None
        assert component.clearance_zones is not None
