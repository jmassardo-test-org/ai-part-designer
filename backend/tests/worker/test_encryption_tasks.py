"""
Tests for encryption worker tasks.

Tests the Celery background tasks for file migration and key rotation.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestMigrateUnencryptedFilesTask:
    """Tests for the migrate_unencrypted_files task."""

    @pytest.mark.asyncio
    async def test_migrate_encrypts_unencrypted_files(self, tmp_path: Path) -> None:
        """Test that the migration task encrypts unencrypted files."""
        from app.core.file_encryption import (
            is_file_encrypted,
            migrate_file_to_encrypted,
        )

        # Create unencrypted files
        cad_dir = tmp_path / "components" / "cad"
        cad_dir.mkdir(parents=True, exist_ok=True)

        file1 = cad_dir / "test1.step"
        file1.write_bytes(b"plaintext step content 1")

        file2 = cad_dir / "test2.stl"
        file2.write_bytes(b"plaintext stl content 2")

        # Migrate them
        results = {"encrypted": 0, "failed": 0}
        for f in cad_dir.iterdir():
            if f.suffix == ".enc":
                continue
            if await migrate_file_to_encrypted(f):
                results["encrypted"] += 1

        assert results["encrypted"] == 2
        assert is_file_encrypted(file1)
        assert is_file_encrypted(file2)

    @pytest.mark.asyncio
    async def test_migrate_skips_already_encrypted(self, tmp_path: Path) -> None:
        """Test that migration skips files with encryption markers."""
        from app.core.file_encryption import (
            ENCRYPTED_MARKER_SUFFIX,
            migrate_file_to_encrypted,
        )

        cad_dir = tmp_path / "components" / "cad"
        cad_dir.mkdir(parents=True, exist_ok=True)

        file1 = cad_dir / "already_encrypted.step"
        file1.write_bytes(b"some encrypted content")

        # Create marker
        marker = Path(str(file1) + ENCRYPTED_MARKER_SUFFIX)
        marker.write_text("1")

        result = await migrate_file_to_encrypted(file1)
        assert result is False


class TestRotateEncryptionKeysTask:
    """Tests for the rotate_encryption_keys task logic."""

    @pytest.mark.asyncio
    async def test_rotation_processes_directories(self, tmp_path: Path) -> None:
        """Test that rotation processes all configured directories."""
        from app.core.security import EncryptionService
        from app.services.key_rotation import KeyRotationService

        old_key = "old-rotation-test-key-minimum-32-characters"
        new_key = "new-rotation-test-key-minimum-32-characters"

        # Create files encrypted with old key
        cad_dir = tmp_path / "cad"
        cad_dir.mkdir(parents=True, exist_ok=True)

        old_service = EncryptionService(key=old_key)
        original = b"test cad data for rotation"
        encrypted = old_service.encrypt_bytes(original)

        file_path = cad_dir / "test.step"
        file_path.write_bytes(encrypted)
        from app.core.file_encryption import ENCRYPTED_MARKER_SUFFIX

        Path(str(file_path) + ENCRYPTED_MARKER_SUFFIX).write_text("1")

        # Rotate
        rotation_service = KeyRotationService(current_key=new_key, previous_keys=[old_key])
        result = await rotation_service.rotate_directory(cad_dir, "*.step")

        assert result.files_processed == 1
        assert result.files_re_encrypted == 1

        # Verify new key can decrypt
        new_service = EncryptionService(key=new_key)
        decrypted = new_service.decrypt_bytes(file_path.read_bytes())
        assert decrypted == original
