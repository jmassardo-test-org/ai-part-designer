"""
Tests for Files API endpoints.

Tests file upload, download, listing, deletion, and quota management.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File as FileModel


# =============================================================================
# Upload Tests
# =============================================================================

class TestFileUpload:
    """Tests for file upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_step_file_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        temp_dir,
    ):
        """Test successful STEP file upload."""
        # Create a mock STEP file
        file_content = b"ISO-10303-21; STEP file content here"
        
        with patch("app.api.v1.files.get_settings") as mock_settings:
            mock_settings.return_value.UPLOAD_DIR = str(temp_dir)
            
            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files={
                    "file": ("test_part.step", io.BytesIO(file_content), "application/step")
                },
            )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["filename"] == "test_part.step"
        assert data["original_filename"] == "test_part.step"
        assert data["mime_type"] == "application/step"
        assert data["size_bytes"] == len(file_content)
        assert data["file_type"] == "cad"
        assert data["cad_format"] == "step"
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_upload_stl_file_success(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
        temp_dir,
    ):
        """Test successful STL file upload."""
        file_content = b"solid test\nendsolid test"
        
        with patch("app.api.v1.files.get_settings") as mock_settings:
            mock_settings.return_value.UPLOAD_DIR = str(temp_dir)
            
            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files={
                    "file": ("model.stl", io.BytesIO(file_content), "application/sla")
                },
            )
        
        assert response.status_code == 201
        data = response.json()
        assert data["cad_format"] == "stl"

    @pytest.mark.asyncio
    async def test_upload_file_too_large(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test file upload exceeding size limit."""
        # Create a file larger than free tier limit (100MB)
        # For testing, we'll mock the size check
        large_content = b"x" * (101 * 1024 * 1024)  # 101 MB
        
        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={
                "file": ("large.step", io.BytesIO(large_content), "application/step")
            },
        )
        
        assert response.status_code == 413
        assert "exceeds limit" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test upload with unsupported file type."""
        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={
                "file": ("malware.exe", io.BytesIO(b"bad content"), "application/x-executable")
            },
        )
        
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test upload requires authentication."""
        response = await client.post(
            "/api/v1/files/upload",
            files={
                "file": ("test.step", io.BytesIO(b"content"), "application/step")
            },
        )
        
        assert response.status_code == 401


# =============================================================================
# List Tests
# =============================================================================

class TestFileList:
    """Tests for file listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_files_empty(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test listing files when user has none."""
        response = await client.get(
            "/api/v1/files/",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["files"] == []
        assert data["total"] == 0
        assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_files_with_files(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test listing files when user has uploaded files."""
        # Create test files
        await file_factory.create(db=db_session, user=test_user)
        await file_factory.create(db=db_session, user=test_user)
        await file_factory.create(db=db_session, user=test_user)
        
        response = await client.get(
            "/api/v1/files/",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["files"]) == 3
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_files_pagination(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test file listing pagination."""
        # Create 5 files
        for _ in range(5):
            await file_factory.create(db=db_session, user=test_user)
        
        # Get first page
        response = await client.get(
            "/api/v1/files/",
            headers=auth_headers,
            params={"skip": 0, "limit": 2},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["files"]) == 2
        assert data["total"] == 5
        assert data["has_more"] is True
        
        # Get second page
        response = await client.get(
            "/api/v1/files/",
            headers=auth_headers,
            params={"skip": 2, "limit": 2},
        )
        
        data = response.json()
        assert len(data["files"]) == 2
        assert data["has_more"] is True

    @pytest.mark.asyncio
    async def test_list_files_filter_by_type(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test filtering files by type."""
        # Create mixed files
        await file_factory.create(db=db_session, user=test_user, cad_format="step")
        await file_factory.create(db=db_session, user=test_user, cad_format="stl")
        await file_factory.create(db=db_session, user=test_user, cad_format="step")
        
        # Filter by STEP
        response = await client.get(
            "/api/v1/files/",
            headers=auth_headers,
            params={"cad_format": "step"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["files"]) == 2
        assert all(f["cad_format"] == "step" for f in data["files"])

    @pytest.mark.asyncio
    async def test_list_files_excludes_deleted(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test that deleted files are excluded from listing."""
        # Create files, one deleted
        await file_factory.create(db=db_session, user=test_user)
        deleted_file = await file_factory.create(db=db_session, user=test_user)
        
        # Soft delete one
        deleted_file.soft_delete()
        await db_session.commit()
        
        response = await client.get(
            "/api/v1/files/",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["files"]) == 1

    @pytest.mark.asyncio
    async def test_list_files_only_own_files(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        file_factory,
    ):
        """Test that users only see their own files."""
        # Create another user with files
        other_user = await user_factory.create(db=db_session)
        await file_factory.create(db=db_session, user=other_user)
        await file_factory.create(db=db_session, user=test_user)
        
        response = await client.get(
            "/api/v1/files/",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only see own file
        assert len(data["files"]) == 1


# =============================================================================
# Get File Tests
# =============================================================================

class TestGetFile:
    """Tests for getting individual file details."""

    @pytest.mark.asyncio
    async def test_get_file_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test getting file details."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        response = await client.get(
            f"/api/v1/files/{file.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(file.id)
        assert data["filename"] == file.filename
        assert data["status"] == file.status

    @pytest.mark.asyncio
    async def test_get_file_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test getting non-existent file."""
        response = await client.get(
            f"/api/v1/files/{uuid4()}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_file_other_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        file_factory,
    ):
        """Test getting another user's file returns 404."""
        other_user = await user_factory.create(db=db_session)
        other_file = await file_factory.create(db=db_session, user=other_user)
        
        response = await client.get(
            f"/api/v1/files/{other_file.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_deleted_file(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test getting a deleted file returns 404."""
        file = await file_factory.create(db=db_session, user=test_user)
        file.soft_delete()
        await db_session.commit()
        
        response = await client.get(
            f"/api/v1/files/{file.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


# =============================================================================
# Download Tests
# =============================================================================

class TestFileDownload:
    """Tests for file download endpoint."""

    @pytest.mark.asyncio
    async def test_download_file_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
        tmp_path,
    ):
        """Test successful file download."""
        from app.main import app
        from app.core.config import get_settings, Settings
        
        # Create file record using factory
        file = await file_factory.create(
            db=db_session,
            user=test_user,
            mime_type="text/plain",
            file_type="document",
            cad_format=None,
            status="ready",
        )
        
        # Create the actual file on disk using the factory's storage_path
        file_path = tmp_path / file.storage_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_content = b"Test file content for download"
        file_path.write_bytes(file_content)
        
        # Override the settings dependency
        original_settings = get_settings()
        
        def override_settings():
            # Create a copy of settings with overridden UPLOAD_DIR
            settings_dict = original_settings.model_dump()
            settings_dict["UPLOAD_DIR"] = str(tmp_path)
            return Settings(**settings_dict)
        
        app.dependency_overrides[get_settings] = override_settings
        try:
            response = await client.get(
                f"/api/v1/files/{file.id}/download",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            assert response.content == file_content
        finally:
            # Remove the override
            if get_settings in app.dependency_overrides:
                del app.dependency_overrides[get_settings]

    @pytest.mark.asyncio
    async def test_download_file_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test downloading non-existent file."""
        response = await client.get(
            f"/api/v1/files/{uuid4()}/download",
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_download_file_content_missing(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
        temp_dir,
    ):
        """Test download when file content is missing from storage."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        # Don't create the actual file on disk
        with patch("app.api.v1.files.get_settings") as mock_settings:
            mock_settings.return_value.UPLOAD_DIR = str(temp_dir)
            
            response = await client.get(
                f"/api/v1/files/{file.id}/download",
                headers=auth_headers,
            )
        
        assert response.status_code == 404
        assert "content not found" in response.json()["detail"]


# =============================================================================
# Delete Tests
# =============================================================================

class TestFileDelete:
    """Tests for file deletion endpoint."""

    @pytest.mark.asyncio
    async def test_delete_file_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test successful file deletion."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        response = await client.delete(
            f"/api/v1/files/{file.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(file.id)
        assert data["status"] == "deleted"
        
        # Verify file is soft-deleted
        await db_session.refresh(file)
        assert file.is_deleted is True

    @pytest.mark.asyncio
    async def test_delete_file_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test deleting non-existent file."""
        response = await client.delete(
            f"/api/v1/files/{uuid4()}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_other_user_file(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        file_factory,
    ):
        """Test deleting another user's file returns 404."""
        other_user = await user_factory.create(db=db_session)
        other_file = await file_factory.create(db=db_session, user=other_user)
        
        response = await client.delete(
            f"/api/v1/files/{other_file.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        
        # Verify file is not deleted
        await db_session.refresh(other_file)
        assert other_file.is_deleted is False

    @pytest.mark.asyncio
    async def test_delete_already_deleted(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test deleting an already deleted file returns 404."""
        file = await file_factory.create(db=db_session, user=test_user)
        file.soft_delete()
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/files/{file.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


# =============================================================================
# Quota Tests
# =============================================================================

class TestStorageQuota:
    """Tests for storage quota endpoint."""

    @pytest.mark.asyncio
    async def test_get_quota_empty(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test getting quota with no files."""
        response = await client.get(
            "/api/v1/files/quota",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["used_bytes"] == 0
        assert data["file_count"] == 0
        assert data["limit_bytes"] > 0
        assert data["remaining_bytes"] == data["limit_bytes"]
        assert data["usage_percent"] == 0

    @pytest.mark.asyncio
    async def test_get_quota_with_files(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test getting quota with uploaded files."""
        await file_factory.create(db=db_session, user=test_user, size_bytes=1000)
        await file_factory.create(db=db_session, user=test_user, size_bytes=2000)
        
        response = await client.get(
            "/api/v1/files/quota",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["used_bytes"] == 3000
        assert data["file_count"] == 2

    @pytest.mark.asyncio
    async def test_get_quota_excludes_deleted(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test that deleted files don't count toward quota."""
        await file_factory.create(db=db_session, user=test_user, size_bytes=1000)
        deleted_file = await file_factory.create(db=db_session, user=test_user, size_bytes=5000)
        
        deleted_file.soft_delete()
        await db_session.commit()
        
        response = await client.get(
            "/api/v1/files/quota",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["used_bytes"] == 1000
        assert data["file_count"] == 1
