"""
Tests for StorageService.

Tests S3/MinIO storage operations: copy, delete, list, and presigned URLs.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.services.storage_service import CopyError, StorageService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_s3_client():
    """Create a mock async S3 client."""
    client = AsyncMock()
    client.copy_object = AsyncMock()
    client.delete_object = AsyncMock()
    client.head_object = AsyncMock()
    client.list_objects_v2 = AsyncMock(return_value={"Contents": []})
    # generate_presigned_url is actually sync in boto3 but the service code awaits it
    # So we need to make it return an awaitable
    client.generate_presigned_url = AsyncMock(return_value="https://presigned.url")
    # Mock exceptions attribute
    client.exceptions = MagicMock()
    client.exceptions.ClientError = ClientError
    return client


@pytest.fixture
def storage_service(mock_s3_client):
    """Create a StorageService with mocked S3 client."""
    service = StorageService()
    
    @asynccontextmanager
    async def mock_get_client():
        yield mock_s3_client
    
    service._get_client = mock_get_client
    return service


# =============================================================================
# Copy File Tests
# =============================================================================


@pytest.mark.asyncio
class TestCopyFile:
    """Tests for the copy_file method."""

    async def test_copy_file_same_bucket(self, storage_service, mock_s3_client):
        """Test copying a file within the same bucket."""
        result = await storage_service.copy_file(
            source_url="s3://test-bucket/source/file.stl",
            target_prefix="dest",
        )

        assert result.endswith("dest/file.stl")
        mock_s3_client.head_object.assert_called_once()
        mock_s3_client.copy_object.assert_called_once()

    async def test_copy_file_different_bucket(self, storage_service, mock_s3_client):
        """Test copying a file from a different source bucket."""
        result = await storage_service.copy_file(
            source_url="s3://source-bucket/source/file.stl",
            target_prefix="dest",
            target_filename="new_file.stl",
        )

        assert result.endswith("dest/new_file.stl")
        mock_s3_client.copy_object.assert_called_once()

    async def test_copy_file_handles_error(self, storage_service, mock_s3_client):
        """Test that copy_file raises on S3 error."""
        mock_s3_client.copy_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
            "CopyObject",
        )

        with pytest.raises(CopyError):
            await storage_service.copy_file(
                source_url="s3://test-bucket/nonexistent/file.stl",
                target_prefix="dest",
            )


# =============================================================================
# Delete File Tests
# =============================================================================


@pytest.mark.asyncio
class TestDeleteFile:
    """Tests for the delete_file method."""

    async def test_delete_file(self, storage_service, mock_s3_client):
        """Test deleting a single file."""
        result = await storage_service.delete_file("s3://test-bucket/path/to/file.stl")

        assert result is True
        mock_s3_client.delete_object.assert_called_once()

    async def test_delete_file_custom_bucket(self, storage_service, mock_s3_client):
        """Test deleting from a custom bucket URL."""
        result = await storage_service.delete_file("s3://custom-bucket/path/to/file.stl")

        assert result is True
        mock_s3_client.delete_object.assert_called_once()


# =============================================================================
# List Files Tests
# =============================================================================


@pytest.mark.asyncio
class TestListFiles:
    """Tests for the list_files method."""

    async def test_list_files_empty(self, storage_service, mock_s3_client):
        """Test listing files when directory is empty."""
        mock_s3_client.list_objects_v2.return_value = {"Contents": []}

        result = await storage_service.list_files("some/prefix")

        assert result == []
        mock_s3_client.list_objects_v2.assert_called_once()

    async def test_list_files_with_contents(self, storage_service, mock_s3_client):
        """Test listing files with results."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "file1.stl", "Size": 1000, "LastModified": datetime.now(UTC)},
                {"Key": "file2.stl", "Size": 2000, "LastModified": datetime.now(UTC)},
            ]
        }

        result = await storage_service.list_files("prefix")

        assert len(result) == 2


# =============================================================================
# Presigned URL Tests
# =============================================================================


@pytest.mark.asyncio
class TestPresignedUrl:
    """Tests for the generate_presigned_url method."""

    async def test_generate_presigned_url_default_expiry(self, storage_service, mock_s3_client):
        """Test generating presigned URL with default expiry."""
        result = await storage_service.generate_presigned_url("path/to/file.stl")

        assert result == "https://presigned.url"
        mock_s3_client.generate_presigned_url.assert_called_once()

    async def test_generate_presigned_url_custom_expiry(self, storage_service, mock_s3_client):
        """Test generating presigned URL with custom expiry."""
        result = await storage_service.generate_presigned_url(
            "path/to/file.stl",
            expires_in=7200,
        )

        assert result == "https://presigned.url"


# =============================================================================
# Batch Operations Tests
# =============================================================================


@pytest.mark.asyncio
class TestBatchOperations:
    """Tests for batch file operations."""

    async def test_copy_multiple_files(self, storage_service, mock_s3_client):
        """Test copying multiple files."""
        # Copy first file
        await storage_service.copy_file(
            source_url="s3://test-bucket/file1.stl",
            target_prefix="backup",
        )
        await storage_service.copy_file(
            source_url="s3://test-bucket/file2.stl",
            target_prefix="backup",
        )

        assert mock_s3_client.copy_object.call_count == 2

    async def test_delete_multiple_files(self, storage_service, mock_s3_client):
        """Test deleting multiple files."""
        await storage_service.delete_file("s3://test-bucket/file1.stl")
        await storage_service.delete_file("s3://test-bucket/file2.stl")

        assert mock_s3_client.delete_object.call_count == 2


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for error handling in storage operations."""

    async def test_copy_nonexistent_source(self, storage_service, mock_s3_client):
        """Test that copying a nonexistent file raises an error."""
        mock_s3_client.copy_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "CopyObject",
        )

        with pytest.raises(CopyError):
            await storage_service.copy_file(
                source_url="s3://test-bucket/nonexistent/key",
                target_prefix="dest",
            )

    async def test_access_denied_error(self, storage_service, mock_s3_client):
        """Test that access denied errors are handled properly."""
        mock_s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "DeleteObject",
        )

        # The service catches ClientError and returns False
        result = await storage_service.delete_file("s3://test-bucket/restricted/file.stl")
        
        # The actual implementation returns False on error rather than raising
        assert result is False
