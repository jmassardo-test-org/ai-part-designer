"""
Storage service for S3/MinIO file operations.

Provides async file storage operations including copy, delete, and URL generation.
Cloud-agnostic using boto3/aiobotocore for S3-compatible storage.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator
from urllib.parse import urlparse

import aioboto3
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class FileNotFoundError(StorageError):
    """File not found in storage."""
    pass


class CopyError(StorageError):
    """Error during file copy operation."""
    pass


class StorageService:
    """
    Service for S3-compatible file storage operations.
    
    Supports MinIO (development) and AWS S3 / compatible services (production).
    All operations are async for non-blocking I/O.
    """
    
    def __init__(
        self,
        endpoint_url: str | None = None,
        bucket: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
    ):
        """
        Initialize storage service.
        
        Args:
            endpoint_url: S3 endpoint URL (for MinIO/localstack)
            bucket: Default bucket name
            access_key: AWS access key ID
            secret_key: AWS secret access key
            region: AWS region
        """
        self.endpoint_url = endpoint_url or getattr(settings, "S3_ENDPOINT_URL", None)
        self.bucket = bucket or getattr(settings, "S3_BUCKET", "ai-part-designer-dev")
        self.access_key = access_key or getattr(settings, "AWS_ACCESS_KEY_ID", "minioadmin")
        self.secret_key = secret_key or getattr(settings, "AWS_SECRET_ACCESS_KEY", "minioadmin")
        self.region = region
        
        self._session = aioboto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        
        self._config = Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "adaptive"},
            connect_timeout=5,
            read_timeout=30,
        )
    
    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator:
        """Get an async S3 client."""
        async with self._session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=self._config,
        ) as client:
            yield client
    
    def _parse_url(self, url: str) -> tuple[str, str]:
        """
        Parse an S3 URL into bucket and key.
        
        Supports formats:
        - s3://bucket/key
        - https://bucket.s3.region.amazonaws.com/key
        - http://localhost:9000/bucket/key (MinIO)
        
        Args:
            url: S3 URL or path
            
        Returns:
            Tuple of (bucket, key)
        """
        if url.startswith("s3://"):
            parsed = urlparse(url)
            bucket = parsed.netloc
            key = parsed.path.lstrip("/")
            return bucket, key
        
        if url.startswith(("http://", "https://")):
            parsed = urlparse(url)
            path_parts = parsed.path.lstrip("/").split("/", 1)
            if len(path_parts) == 2:
                # MinIO style: /bucket/key
                return path_parts[0], path_parts[1]
            # AWS style: bucket is in hostname
            bucket = parsed.netloc.split(".")[0]
            return bucket, path_parts[0] if path_parts else ""
        
        # Assume it's just a key in the default bucket
        return self.bucket, url
    
    async def copy_file(
        self,
        source_url: str,
        target_prefix: str,
        target_filename: str | None = None,
    ) -> str:
        """
        Copy a file within S3 using server-side copy.
        
        This is efficient as it doesn't download/upload - S3 handles it internally.
        
        Args:
            source_url: Full S3 URL or path of source file
            target_prefix: Target path prefix (without filename)
            target_filename: Optional new filename (default: preserve original)
            
        Returns:
            URL of the copied file
            
        Raises:
            FileNotFoundError: Source file doesn't exist
            CopyError: Copy operation failed
            ValueError: Invalid path (path traversal attempt)
        """
        source_bucket, source_key = self._parse_url(source_url)
        
        # SECURITY: Validate inputs to prevent path traversal
        if ".." in target_prefix or ".." in (target_filename or ""):
            raise ValueError("Invalid path: path traversal not allowed")
        
        # Preserve original filename if not specified
        if target_filename is None:
            target_filename = source_key.split("/")[-1]
        
        # SECURITY: Sanitize filename to prevent injection
        target_filename = target_filename.replace("..", "").lstrip("/")
        target_prefix = target_prefix.replace("..", "").strip("/")
        
        target_key = f"{target_prefix}/{target_filename}"
        
        logger.debug(
            f"Copying file: {source_bucket}/{source_key} -> {self.bucket}/{target_key}"
        )
        
        try:
            async with self._get_client() as s3:
                # Check source exists
                try:
                    await s3.head_object(Bucket=source_bucket, Key=source_key)
                except s3.exceptions.ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        raise FileNotFoundError(f"Source file not found: {source_url}")
                    raise
                
                # Perform server-side copy
                await s3.copy_object(
                    CopySource={"Bucket": source_bucket, "Key": source_key},
                    Bucket=self.bucket,
                    Key=target_key,
                )
                
                logger.info(f"File copied successfully: {target_key}")
                return f"s3://{self.bucket}/{target_key}"
                
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            raise CopyError(f"Failed to copy file: {e}") from e
    
    async def delete_file(self, url: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            url: S3 URL or path of file to delete
            
        Returns:
            True if deleted, False if file didn't exist
        """
        bucket, key = self._parse_url(url)
        
        try:
            async with self._get_client() as s3:
                await s3.delete_object(Bucket=bucket, Key=key)
                logger.info(f"File deleted: {bucket}/{key}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete file {url}: {e}")
            return False
    
    async def file_exists(self, url: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            url: S3 URL or path
            
        Returns:
            True if file exists
        """
        bucket, key = self._parse_url(url)
        
        try:
            async with self._get_client() as s3:
                await s3.head_object(Bucket=bucket, Key=key)
                return True
        except Exception:
            return False
    
    async def generate_presigned_url(
        self,
        url: str,
        expires_in: int = 3600,
        method: str = "get_object",
    ) -> str:
        """
        Generate a presigned URL for temporary access.
        
        Args:
            url: S3 URL or path
            expires_in: URL expiration time in seconds (default: 1 hour)
            method: S3 method (get_object, put_object)
            
        Returns:
            Presigned URL
        """
        bucket, key = self._parse_url(url)
        
        async with self._get_client() as s3:
            presigned_url = await s3.generate_presigned_url(
                ClientMethod=method,
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return presigned_url
    
    async def list_files(
        self,
        prefix: str,
        max_keys: int = 1000,
    ) -> list[dict]:
        """
        List files with a given prefix.
        
        Args:
            prefix: Path prefix to search
            max_keys: Maximum number of results
            
        Returns:
            List of file info dicts with key, size, last_modified
        """
        async with self._get_client() as s3:
            response = await s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            
            files = []
            for obj in response.get("Contents", []):
                files.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                })
            
            return files


# Singleton instance for dependency injection
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get or create the storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
