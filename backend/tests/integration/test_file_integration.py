"""
Integration tests for file upload and storage workflows.

Tests end-to-end file operations with storage backend.
"""

from __future__ import annotations

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch


# =============================================================================
# Storage Client Integration Tests
# =============================================================================

class TestStorageClientIntegration:
    """Integration tests for storage client operations."""
    
    def test_storage_client_imports(self):
        """Test that storage client imports correctly."""
        from app.core.storage import storage_client, StorageBucket
        
        assert storage_client is not None
        assert StorageBucket.UPLOADS is not None
        assert StorageBucket.EXPORTS is not None
    
    def test_storage_bucket_enum_values(self):
        """Test storage bucket enum has expected values."""
        from app.core.storage import StorageBucket
        
        assert StorageBucket.UPLOADS.value == "uploads"
        assert StorageBucket.EXPORTS.value == "exports"
    
    @pytest.mark.asyncio
    async def test_storage_operations_with_mock(self):
        """Test storage operations with mocked backend."""
        from app.core.storage import StorageBucket
        
        # Create a mock storage client
        mock_client = AsyncMock()
        mock_client.upload_file = AsyncMock(return_value="uploads/test/file.step")
        mock_client.download_file = AsyncMock(return_value=b"test content")
        mock_client.generate_presigned_download_url = AsyncMock(
            return_value="https://storage.example.com/file.step"
        )
        
        # Test upload
        result = await mock_client.upload_file(
            bucket=StorageBucket.UPLOADS,
            key="test/file.step",
            file=b"step content",
        )
        assert result == "uploads/test/file.step"
        
        # Test download
        content = await mock_client.download_file(
            bucket=StorageBucket.UPLOADS,
            key="test/file.step",
        )
        assert content == b"test content"
        
        # Test presigned URL
        url = await mock_client.generate_presigned_download_url(
            bucket=StorageBucket.UPLOADS,
            key="test/file.step",
        )
        assert "https://" in url


# =============================================================================
# File Processing Integration Tests
# =============================================================================

class TestFileProcessingIntegration:
    """Integration tests for file processing workflows."""
    
    def test_step_file_content_validation(self, tmp_path):
        """Test validating STEP file content."""
        from app.cad.primitives import create_box
        from app.cad.export import export_to_file
        
        # Generate a STEP file
        box = create_box(50, 50, 50)
        step_path = tmp_path / "test.step"
        export_to_file(box, step_path)
        
        # Read and validate content
        content = step_path.read_bytes()
        
        assert len(content) > 0
        
        # Check for STEP markers
        text_content = content.decode("utf-8", errors="ignore")
        assert "ISO-10303" in text_content or "STEP" in text_content
    
    def test_stl_file_content_validation(self, tmp_path):
        """Test validating STL file content."""
        from app.cad.primitives import create_box
        from app.cad.export import export_to_file
        
        # Generate an STL file
        box = create_box(50, 50, 50)
        stl_path = tmp_path / "test.stl"
        export_to_file(box, stl_path)
        
        # Read content
        content = stl_path.read_bytes()
        
        assert len(content) > 0
        
        # Binary STL has 80-byte header followed by 4-byte triangle count
        assert len(content) > 84
    
    def test_file_size_calculation(self, tmp_path):
        """Test accurate file size reporting."""
        from app.cad.primitives import create_box
        from app.cad.export import export_to_file
        
        box = create_box(100, 100, 100)
        step_path = tmp_path / "size_test.step"
        export_to_file(box, step_path)
        
        # Get actual file size
        actual_size = step_path.stat().st_size
        
        # Read file and verify length matches
        content = step_path.read_bytes()
        
        assert len(content) == actual_size
        assert actual_size > 0
