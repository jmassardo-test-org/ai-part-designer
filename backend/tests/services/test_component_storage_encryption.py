"""
Tests for component storage encryption integration.

Verifies that ComponentFileStorage encrypts files on store
and can provide decrypted content on retrieval.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.core.file_encryption import ENCRYPTED_MARKER_SUFFIX
from app.services.component_storage import ComponentFileStorage


class TestComponentStorageEncryption:
    """Tests for encryption integration in ComponentFileStorage."""

    @pytest.fixture
    def storage(self, tmp_path: Path) -> ComponentFileStorage:
        """Create a ComponentFileStorage with temp directories."""
        with patch("app.services.component_storage.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            # Re-patch the directory constants
            with (
                patch(
                    "app.services.component_storage.COMPONENT_FILES_DIR",
                    tmp_path / "components",
                ),
                patch(
                    "app.services.component_storage.DATASHEET_DIR",
                    tmp_path / "components" / "datasheets",
                ),
                patch(
                    "app.services.component_storage.CAD_DIR",
                    tmp_path / "components" / "cad",
                ),
                patch(
                    "app.services.component_storage.THUMBNAIL_DIR",
                    tmp_path / "components" / "thumbnails",
                ),
            ):
                return ComponentFileStorage()

    def _make_upload_file(
        self, content: bytes, filename: str, content_type: str = "application/octet-stream"
    ) -> UploadFile:
        """Create a mock UploadFile."""
        return UploadFile(
            file=io.BytesIO(content),
            filename=filename,
            size=len(content),
            headers={"content-type": content_type},
        )

    @pytest.mark.asyncio
    async def test_store_datasheet_encrypts_file(
        self, storage: ComponentFileStorage, tmp_path: Path
    ) -> None:
        """Test that storing a datasheet encrypts the file on disk."""
        component_id = uuid4()
        content = b"%PDF-1.4 test datasheet content"

        with (
            patch(
                "app.services.component_storage.DATASHEET_DIR",
                tmp_path / "components" / "datasheets",
            ),
        ):
            (tmp_path / "components" / "datasheets").mkdir(parents=True, exist_ok=True)
            file = self._make_upload_file(content, "test.pdf", "application/pdf")
            result = await storage.store_datasheet(file, component_id)

        # Verify file is encrypted
        file_path = Path(result["path"])
        assert file_path.exists()
        assert file_path.read_bytes() != content  # Encrypted

        # Verify marker exists
        marker = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        assert marker.exists()

        # Verify hash is of plaintext
        import hashlib

        expected_hash = hashlib.sha256(content).hexdigest()
        assert result["hash"] == expected_hash

    @pytest.mark.asyncio
    async def test_store_cad_file_encrypts_file(
        self, storage: ComponentFileStorage, tmp_path: Path
    ) -> None:
        """Test that storing a CAD file encrypts the file on disk."""
        component_id = uuid4()
        content = b"ISO-10303-21; STEP file content"

        with (
            patch(
                "app.services.component_storage.CAD_DIR",
                tmp_path / "components" / "cad",
            ),
        ):
            (tmp_path / "components" / "cad").mkdir(parents=True, exist_ok=True)
            file = self._make_upload_file(content, "part.step")
            result = await storage.store_cad_file(file, component_id)

        # Verify file is encrypted
        file_path = Path(result["path"])
        assert file_path.exists()
        assert file_path.read_bytes() != content

    @pytest.mark.asyncio
    async def test_delete_component_files_removes_markers(
        self, storage: ComponentFileStorage, tmp_path: Path
    ) -> None:
        """Test that deleting component files also removes encryption markers."""
        component_id = uuid4()
        cad_dir = tmp_path / "components" / "cad"
        cad_dir.mkdir(parents=True, exist_ok=True)

        # Create a fake encrypted file + marker
        file_path = cad_dir / f"{component_id}_test.step"
        file_path.write_bytes(b"encrypted content")
        marker = Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX)
        marker.write_text("1")

        with (
            patch("app.services.component_storage.CAD_DIR", cad_dir),
            patch(
                "app.services.component_storage.DATASHEET_DIR",
                tmp_path / "components" / "datasheets",
            ),
            patch(
                "app.services.component_storage.THUMBNAIL_DIR",
                tmp_path / "components" / "thumbnails",
            ),
        ):
            (tmp_path / "components" / "datasheets").mkdir(parents=True, exist_ok=True)
            (tmp_path / "components" / "thumbnails").mkdir(parents=True, exist_ok=True)
            deleted = await storage.delete_component_files(component_id)

        assert deleted == 1
        assert not file_path.exists()
        assert not marker.exists()
