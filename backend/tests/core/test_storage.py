"""
Tests for Object Storage (S3/MinIO) integration.

Tests file upload, download, presigned URLs, and bucket operations.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.storage import StorageClient, StorageBucket


# =============================================================================
# StorageClient Tests
# =============================================================================

class TestStorageClient:
    """Tests for StorageClient class."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def storage_client(self):
        """Create a storage client instance."""
        with patch("app.core.storage.settings") as mock_settings:
            mock_settings.storage_endpoint = "http://localhost:9000"
            mock_settings.storage_access_key = "minioadmin"
            mock_settings.storage_secret_key = "minioadmin"
            mock_settings.storage_region = "us-east-1"
            mock_settings.ENVIRONMENT = "test"
            return StorageClient()

    def test_get_bucket_name_with_environment_prefix(self, storage_client):
        """Test bucket name includes environment prefix."""
        bucket_name = storage_client._get_bucket_name(StorageBucket.UPLOADS)
        assert bucket_name == "ai-part-designer-test-uploads"

    def test_get_bucket_name_for_all_buckets(self, storage_client):
        """Test bucket name generation for all bucket types."""
        expected_buckets = {
            StorageBucket.DESIGNS: "ai-part-designer-test-designs",
            StorageBucket.EXPORTS: "ai-part-designer-test-exports",
            StorageBucket.THUMBNAILS: "ai-part-designer-test-thumbnails",
            StorageBucket.UPLOADS: "ai-part-designer-test-uploads",
            StorageBucket.TEMP: "ai-part-designer-test-temp",
        }
        
        for bucket, expected_name in expected_buckets.items():
            assert storage_client._get_bucket_name(bucket) == expected_name

    @pytest.mark.asyncio
    async def test_upload_file_bytes(self, storage_client, mock_s3_client):
        """Test uploading file as bytes."""
        file_content = b"test file content"
        
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            await storage_client.upload_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                file=file_content,
                content_type="text/plain",
            )
            
            mock_s3_client.put_object.assert_called_once()
            call_kwargs = mock_s3_client.put_object.call_args.kwargs
            assert call_kwargs["Bucket"] == "ai-part-designer-test-uploads"
            assert call_kwargs["Key"] == "test/file.txt"
            assert call_kwargs["Body"] == file_content
            assert call_kwargs["ContentType"] == "text/plain"

    @pytest.mark.asyncio
    async def test_upload_file_with_metadata(self, storage_client, mock_s3_client):
        """Test uploading file with custom metadata."""
        file_content = b"test content"
        metadata = {"user_id": "123", "checksum": "abc123"}
        
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            await storage_client.upload_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                file=file_content,
                metadata=metadata,
            )
            
            call_kwargs = mock_s3_client.put_object.call_args.kwargs
            assert call_kwargs["Metadata"] == metadata

    @pytest.mark.asyncio
    async def test_download_file(self, storage_client, mock_s3_client):
        """Test downloading file."""
        expected_content = b"downloaded content"
        
        # Mock the response body
        mock_body = AsyncMock()
        mock_body.read.return_value = expected_content
        mock_s3_client.get_object.return_value = {"Body": mock_body}
        
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            content = await storage_client.download_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
            )
            
            assert content == expected_content
            mock_s3_client.get_object.assert_called_once_with(
                Bucket="ai-part-designer-test-uploads",
                Key="test/file.txt",
            )

    @pytest.mark.asyncio
    async def test_delete_file_success(self, storage_client, mock_s3_client):
        """Test deleting a file successfully."""
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            result = await storage_client.delete_file(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
            )
            
            assert result is True
            mock_s3_client.delete_object.assert_called_once_with(
                Bucket="ai-part-designer-test-uploads",
                Key="test/file.txt",
            )

    @pytest.mark.asyncio
    async def test_file_exists_true(self, storage_client, mock_s3_client):
        """Test checking if file exists (true case)."""
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            result = await storage_client.file_exists(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
            )
            
            assert result is True
            mock_s3_client.head_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_exists_false(self, storage_client, mock_s3_client):
        """Test checking if file exists (false case)."""
        from botocore.exceptions import ClientError
        
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            result = await storage_client.file_exists(
                bucket=StorageBucket.UPLOADS,
                key="nonexistent/file.txt",
            )
            
            assert result is False

    @pytest.mark.asyncio
    async def test_get_file_info(self, storage_client, mock_s3_client):
        """Test getting file metadata."""
        from datetime import datetime
        
        mock_s3_client.head_object.return_value = {
            "ContentLength": 1024,
            "ContentType": "application/pdf",
            "LastModified": datetime(2024, 1, 15, 12, 0, 0),
            "ETag": '"abc123"',
            "Metadata": {"user_id": "456"},
        }
        
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            info = await storage_client.get_file_info(
                bucket=StorageBucket.UPLOADS,
                key="test/file.pdf",
            )
            
            assert info["size"] == 1024
            assert info["content_type"] == "application/pdf"
            assert info["etag"] == '"abc123"'
            assert info["metadata"] == {"user_id": "456"}

    @pytest.mark.asyncio
    async def test_generate_presigned_download_url(self, storage_client, mock_s3_client):
        """Test generating presigned download URL."""
        expected_url = "https://minio:9000/bucket/key?signature=abc"
        mock_s3_client.generate_presigned_url.return_value = expected_url
        
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            url = await storage_client.generate_presigned_download_url(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                expires_in=3600,
            )
            
            assert url == expected_url
            mock_s3_client.generate_presigned_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_presigned_download_url_with_filename(
        self, storage_client, mock_s3_client
    ):
        """Test generating presigned download URL with custom filename."""
        expected_url = "https://minio:9000/bucket/key?signature=abc"
        mock_s3_client.generate_presigned_url.return_value = expected_url
        
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            await storage_client.generate_presigned_download_url(
                bucket=StorageBucket.UPLOADS,
                key="test/uuid-file",
                expires_in=3600,
                filename="download.pdf",
            )
            
            call_kwargs = mock_s3_client.generate_presigned_url.call_args.kwargs
            params = call_kwargs["Params"]
            assert 'attachment; filename="download.pdf"' in params["ResponseContentDisposition"]

    @pytest.mark.asyncio
    async def test_generate_presigned_upload_url(self, storage_client, mock_s3_client):
        """Test generating presigned upload URL."""
        expected_response = {
            "url": "https://minio:9000/bucket",
            "fields": {"key": "test/file.txt", "signature": "xyz"},
        }
        mock_s3_client.generate_presigned_post.return_value = expected_response
        
        with patch.object(storage_client, "_get_client") as mock_get_client:
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_s3_client
            mock_get_client.return_value = mock_client_ctx
            
            result = await storage_client.generate_presigned_upload_url(
                bucket=StorageBucket.UPLOADS,
                key="test/file.txt",
                expires_in=3600,
            )
            
            assert result == expected_response
            mock_s3_client.generate_presigned_post.assert_called_once()


# =============================================================================
# StorageBucket Enum Tests
# =============================================================================

class TestStorageBucket:
    """Tests for StorageBucket enum."""

    def test_all_buckets_defined(self):
        """Test all expected buckets are defined."""
        expected_buckets = {"designs", "exports", "thumbnails", "uploads", "temp"}
        actual_buckets = {bucket.value for bucket in StorageBucket}
        assert actual_buckets == expected_buckets

    def test_bucket_values_are_strings(self):
        """Test bucket values are proper strings."""
        for bucket in StorageBucket:
            assert isinstance(bucket.value, str)
            assert bucket.value.islower()
            assert "-" not in bucket.value  # No hyphens in bucket names
