"""
Export and file conversion tasks.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="app.worker.tasks.export.convert_format",
    max_retries=3,
)
def convert_format(
    self,
    job_id: str,
    source_url: str,
    target_format: str,
) -> dict:
    """
    Convert CAD model to different format.

    Supported formats: STEP, STL, 3MF, OBJ, IGES

    Args:
        job_id: Job ID for tracking
        source_url: URL of source file
        target_format: Target format extension

    Returns:
        Dict with converted file URL
    """
    import asyncio

    from app.core.database import async_session_maker
    from app.repositories import JobRepository

    async def run():
        async with async_session_maker() as session:
            job_repo = JobRepository(session)

            await job_repo.update(
                UUID(job_id),
                status="running",
                started_at=datetime.utcnow(),
                progress=20,
                progress_message=f"Converting to {target_format.upper()}",
            )
            await session.commit()

            # Actual format conversion using CadQuery
            import tempfile
            from pathlib import Path

            from app.cad.export import convert_cad_format
            from app.core.storage import StorageBucket, storage_client

            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    # Download source file from storage
                    source_key = source_url.replace("s3://exports/", "")
                    source_content = await storage_client.download_file(
                        bucket=StorageBucket.EXPORTS,
                        key=source_key,
                    )

                    # Determine source format from URL
                    source_format = source_url.split(".")[-1].lower()
                    source_file = temp_path / f"source.{source_format}"
                    source_file.write_bytes(source_content)

                    # Convert to target format
                    output_file = temp_path / f"model.{target_format}"
                    convert_cad_format(source_file, output_file, target_format)

                    if not output_file.exists():
                        raise ValueError("Conversion failed: output file not created")

                    # Upload converted file
                    output_key = f"exports/{job_id}/model.{target_format}"
                    content_type = {
                        "step": "application/step",
                        "stl": "model/stl",
                        "obj": "model/obj",
                        "3mf": "model/3mf",
                        "iges": "application/iges",
                    }.get(target_format.lower(), "application/octet-stream")

                    await storage_client.upload_file(
                        bucket=StorageBucket.EXPORTS,
                        key=output_key,
                        file=output_file.read_bytes(),
                        content_type=content_type,
                    )

                    # Generate download URL
                    download_url = await storage_client.generate_presigned_download_url(
                        bucket=StorageBucket.EXPORTS,
                        key=output_key,
                        expires_in=86400,
                    )

                result = {
                    "output_url": download_url,
                    "output_key": output_key,
                    "format": target_format,
                    "source_url": source_url,
                }
            except Exception as conv_error:
                logger.error(f"Format conversion error: {conv_error}")
                raise ValueError(f"Format conversion failed: {conv_error}")

            await job_repo.update(
                UUID(job_id),
                status="completed",
                completed_at=datetime.utcnow(),
                progress=100,
                result=result,
            )
            await session.commit()

            return result

    try:
        return asyncio.run(run())
    except Exception as e:
        logger.error(f"Format conversion failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    name="app.worker.tasks.export.batch_export",
)
def batch_export(
    design_ids: list[str],
    formats: list[str],
    user_id: str,
) -> dict:
    """
    Export multiple designs in multiple formats.

    Creates a ZIP archive with all exported files.
    """
    logger.info(f"Batch export: {len(design_ids)} designs, formats: {formats}")

    # Placeholder implementation
    results = []
    for design_id in design_ids:
        for fmt in formats:
            results.append(
                {
                    "design_id": design_id,
                    "format": fmt,
                    "url": f"s3://exports/batch/{user_id}/{design_id}.{fmt}",
                }
            )

    return {
        "archive_url": f"s3://exports/batch/{user_id}/export.zip",
        "files": results,
        "count": len(results),
    }


@shared_task(
    name="app.worker.tasks.export.generate_print_file",
)
def generate_print_file(
    design_id: str,
    printer_settings: dict[str, Any],
) -> dict:
    """
    Generate printer-ready file with specific settings.

    Applies:
    - Scale/unit conversion
    - Orientation optimization
    - Support generation hints
    """
    logger.info(f"Generating print file for design {design_id}")

    # Placeholder implementation
    return {
        "print_file_url": f"s3://exports/{design_id}/print_ready.stl",
        "settings_applied": printer_settings,
        "estimated_print_time": 7200,  # seconds
        "estimated_material": 25.5,  # grams
    }
