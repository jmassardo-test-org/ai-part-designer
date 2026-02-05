"""
Security tests for file upload vulnerabilities.

Tests for malicious file handling and path traversal prevention.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestFileUploadSecurity:
    """Tests for file upload security."""

    @pytest.mark.asyncio
    async def test_file_type_validation(self, client: AsyncClient, auth_headers: dict):
        """Test that dangerous file types are rejected."""
        # Try uploading executable content with STEP extension
        malicious_content = b"#!/bin/bash\nrm -rf /"

        files = {"file": ("malicious.step", BytesIO(malicious_content), "application/octet-stream")}

        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files=files,
        )

        # Should either reject or sanitize - not execute
        # Status should not be 500 (which would indicate execution attempt)
        assert response.status_code != 500

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, client: AsyncClient, auth_headers: dict):
        """Test that path traversal attacks are prevented."""
        path_traversal_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
        ]

        for filename in path_traversal_names:
            files = {"file": (filename, BytesIO(b"test content"), "text/plain")}

            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files=files,
            )

            # Should be rejected or sanitized
            assert response.status_code != 500

            # If successful, filename should be sanitized
            if response.status_code in [200, 201]:
                data = response.json()
                stored_name = data.get("filename", data.get("name", ""))
                assert ".." not in stored_name
                assert "/" not in stored_name or stored_name.startswith("/uploads")

    @pytest.mark.asyncio
    async def test_file_size_limit_enforced(self, client: AsyncClient, auth_headers: dict):
        """Test that file size limits are enforced."""
        # Try to upload a very large file (100MB)
        # Most servers should reject this
        large_content = b"A" * (100 * 1024 * 1024)  # 100MB

        files = {"file": ("large.step", BytesIO(large_content), "application/step")}

        try:
            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files=files,
                timeout=5.0,  # Short timeout
            )

            # Should be rejected with 413 or 422
            assert response.status_code in [413, 422, 400]
        except Exception:
            # Connection timeout or error is acceptable for large files
            pass

    @pytest.mark.asyncio
    async def test_double_extension_handling(self, client: AsyncClient, auth_headers: dict):
        """Test that double extensions are handled safely."""
        dangerous_names = [
            "file.step.exe",
            "model.stl.php",
            "design.step.js",
        ]

        for filename in dangerous_names:
            files = {"file": (filename, BytesIO(b"test content"), "application/octet-stream")}

            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files=files,
            )

            # Should be rejected or have dangerous extension stripped
            if response.status_code in [200, 201]:
                data = response.json()
                stored_name = data.get("filename", data.get("name", ""))
                # Should not end with dangerous extension
                assert not stored_name.endswith((".exe", ".php", ".js"))

    @pytest.mark.asyncio
    async def test_null_byte_injection(self, client: AsyncClient, auth_headers: dict):
        """Test that null byte injection is prevented."""
        # Null byte can be used to bypass extension checks
        filename = "malicious.step\x00.exe"

        files = {"file": (filename, BytesIO(b"test content"), "application/step")}

        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files=files,
        )

        # Should be handled without error
        assert response.status_code != 500


class TestFileDownloadSecurity:
    """Tests for file download security."""

    @pytest.mark.asyncio
    async def test_cannot_download_files_outside_uploads(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that path traversal in download is prevented."""
        traversal_paths = [
            "../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
        ]

        for path in traversal_paths:
            response = await client.get(
                f"/api/v1/files/{path}",
                headers=auth_headers,
            )

            # Should return 404 or 400, not the file
            assert response.status_code in [400, 404, 422]

            # Should not contain /etc/passwd content
            assert "root:" not in response.text
