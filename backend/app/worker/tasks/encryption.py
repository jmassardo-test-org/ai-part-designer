"""
Encryption maintenance tasks.

Background tasks for managing file encryption:
- Migrating existing unencrypted files to encrypted format
- Re-encrypting files during key rotation
"""

import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.encryption.migrate_unencrypted_files",
    max_retries=0,
)
def migrate_unencrypted_files() -> dict[str, Any]:
    """Migrate existing unencrypted files to encrypted format.

    Scans all file storage directories and encrypts any files
    that don't have encryption markers.

    Returns:
        Dictionary with migration statistics per directory.
    """
    import asyncio
    from pathlib import Path

    from app.core.config import settings
    from app.core.file_encryption import migrate_file_to_encrypted

    async def run() -> dict[str, Any]:
        results: dict[str, Any] = {}
        directories = {
            "datasheets": Path(settings.UPLOAD_DIR) / "components" / "datasheets",
            "cad_files": Path(settings.UPLOAD_DIR) / "components" / "cad",
            "cad_exports": Path(settings.UPLOAD_DIR) / "cad_exports",
        }

        for name, directory in directories.items():
            if not directory.exists():
                results[name] = {"skipped": True, "reason": "directory not found"}
                continue

            encrypted = 0
            skipped = 0
            failed = 0
            errors: list[str] = []

            for file_path in directory.rglob("*"):
                if file_path.is_dir():
                    continue
                if file_path.suffix == ".enc":
                    continue  # Skip marker files

                try:
                    if await migrate_file_to_encrypted(file_path):
                        encrypted += 1
                    else:
                        skipped += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"{file_path.name}: {e}")
                    logger.error(f"Failed to encrypt {file_path}: {e}")

            results[name] = {
                "encrypted": encrypted,
                "skipped": skipped,
                "failed": failed,
                "errors": errors,
            }
            logger.info(
                f"Encryption migration for {name}: "
                f"encrypted={encrypted}, "
                f"skipped={skipped}, "
                f"failed={failed}"
            )

        return results

    return asyncio.get_event_loop().run_until_complete(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.encryption.rotate_encryption_keys",
    max_retries=0,
)
def rotate_encryption_keys(
    previous_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Re-encrypt all files with the current encryption key.

    Used during key rotation to ensure all files are encrypted
    with the latest key.

    Args:
        previous_keys: List of previous SECRET_KEY values.

    Returns:
        Dictionary with rotation statistics.
    """
    import asyncio

    from app.services.key_rotation import get_key_rotation_service

    async def run() -> dict[str, Any]:
        service = get_key_rotation_service(previous_keys=previous_keys)
        return await service.rotate_all_cad_files()

    return asyncio.get_event_loop().run_until_complete(run())
