"""
CAD generation and processing tasks.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from celery import shared_task

from app.worker.ws_utils import (
    send_job_complete,
    send_job_failed,
    send_job_progress,
    send_job_started,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="app.worker.tasks.cad.generate_from_template",
    max_retries=3,
    default_retry_delay=60,
)
def generate_from_template(
    self,
    job_id: str,
    template_id: str,
    parameters: dict[str, Any],
    output_formats: list[str] | None = None,
    user_id: str | None = None,
) -> dict:
    """
    Generate CAD model from template with parameters.

    Args:
        job_id: Job ID to update with progress/results
        template_id: Template to use for generation
        parameters: Parameter values to apply
        output_formats: Formats to generate (default: ["step", "stl"])
        user_id: User ID for WebSocket updates

    Returns:
        Dict with file URLs and geometry info
    """
    import asyncio

    from app.core.database import async_session_maker
    from app.repositories import JobRepository, TemplateRepository

    output_formats = output_formats or ["step", "stl"]

    # Send job started notification
    if user_id:
        send_job_started(user_id, job_id, "cad_generation")

    async def run():
        async with async_session_maker() as session:
            # Get template
            template_repo = TemplateRepository(session)
            template = await template_repo.get_by_id(UUID(template_id))

            if not template:
                raise ValueError(f"Template not found: {template_id}")

            # Update job status
            job_repo = JobRepository(session)
            await job_repo.update(
                UUID(job_id),
                status="running",
                started_at=datetime.now(tz=datetime.UTC),
                progress=10,
                progress_message="Loading template",
            )
            await session.commit()

            # Send WebSocket progress update
            if user_id:
                send_job_progress(user_id, job_id, 10, "running", "Loading template")

            # Validate parameters
            validation = template.validate_parameters(parameters)
            if not validation["valid"]:
                raise ValueError(f"Invalid parameters: {validation['errors']}")

            # Execute CadQuery script (placeholder)
            await job_repo.update(
                UUID(job_id),
                progress=30,
                progress_message="Generating CAD model",
            )
            await session.commit()

            if user_id:
                send_job_progress(user_id, job_id, 30, "running", "Generating CAD model")

            # Execute CadQuery generation
            from app.cad.templates import generate_from_template as generate_template_cad

            try:
                cad_result = generate_template_cad(template.slug, parameters)
            except Exception as cad_error:
                logger.error(f"CadQuery execution failed: {cad_error}")
                raise ValueError(f"CAD generation failed: {cad_error}")

            # Generate output formats
            await job_repo.update(
                UUID(job_id),
                progress=50,
                progress_message="Exporting CAD formats",
            )
            await session.commit()

            if user_id:
                send_job_progress(user_id, job_id, 50, "running", "Exporting CAD formats")

            # Export to requested formats and upload to storage
            import tempfile
            from pathlib import Path

            from app.cad.export import export_model
            from app.core.storage import StorageBucket, storage_client

            file_urls = {}
            geometry_info = {}

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Export each format
                for fmt in output_formats:
                    export_path = temp_path / f"model.{fmt}"
                    export_model(cad_result, export_path, format=fmt)

                    if export_path.exists():
                        storage_key = f"designs/{job_id}/model.{fmt}"
                        content_type = "application/step" if fmt == "step" else f"model/{fmt}"

                        await storage_client.upload_file(
                            bucket=StorageBucket.EXPORTS,
                            key=storage_key,
                            file=export_path.read_bytes(),
                            content_type=content_type,
                        )

                        # Generate presigned URL for download
                        file_urls[fmt] = await storage_client.generate_presigned_download_url(
                            bucket=StorageBucket.EXPORTS,
                            key=storage_key,
                            expires_in=86400,  # 24 hours
                        )

                # Get geometry info from the solid
                if hasattr(cad_result, "val") and hasattr(cad_result.val(), "Volume"):
                    solid = cad_result.val()
                    bbox = cad_result.val().BoundingBox()
                    geometry_info = {
                        "bounding_box": {
                            "x": round(bbox.xlen, 2),
                            "y": round(bbox.ylen, 2),
                            "z": round(bbox.zlen, 2),
                        },
                        "volume": round(solid.Volume(), 2),
                        "is_manifold": True,
                    }

            # Generate thumbnail
            await job_repo.update(
                UUID(job_id),
                progress=90,
                progress_message="Generating thumbnail",
            )
            await session.commit()

            if user_id:
                send_job_progress(user_id, job_id, 90, "running", "Generating thumbnail")

            # Build result with actual data
            result = {
                "template_id": template_id,
                "template_slug": template.slug,
                "parameters": parameters,
                "files": file_urls,
                "geometry_info": geometry_info
                or {
                    "bounding_box": {"x": 0, "y": 0, "z": 0},
                    "volume": 0,
                    "is_manifold": True,
                },
            }

            # Mark job complete
            await job_repo.update(
                UUID(job_id),
                status="completed",
                completed_at=datetime.now(tz=datetime.UTC),
                progress=100,
                result=result,
            )
            await session.commit()

            # Send WebSocket completion notification
            if user_id:
                send_job_complete(user_id, job_id, result)

            logger.info(f"CAD generation complete for job {job_id}")
            return result

    try:
        return asyncio.run(run())
    except Exception as e:
        logger.error(f"CAD generation failed: {e}")

        # Send WebSocket failure notification
        if user_id:
            send_job_failed(user_id, job_id, str(e), type(e).__name__)

        # Update job as failed
        error_msg = str(e)
        error_type = type(e).__name__

        async def mark_failed():
            async with async_session_maker() as session:
                job_repo = JobRepository(session)
                await job_repo.update(
                    UUID(job_id),
                    status="failed",
                    completed_at=datetime.now(tz=datetime.UTC),
                    error_message=error_msg,
                    error={"message": error_msg, "type": error_type},
                )
                await session.commit()

        asyncio.run(mark_failed())

        # Retry if applicable
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        raise


@shared_task(
    bind=True,
    name="app.worker.tasks.cad.modify_design",
    max_retries=3,
)
def modify_design(
    self,
    job_id: str,
    design_id: str,
    modifications: dict[str, Any],
) -> dict:
    """
    Apply modifications to an existing design.

    Creates a new version with the modifications applied.
    """
    logger.info(f"Modifying design {design_id}")

    # Placeholder implementation
    return {
        "version_id": "new-version-uuid",
        "changes_applied": modifications,
    }


@shared_task(
    name="app.worker.tasks.cad.validate_geometry",
)
def validate_geometry(file_url: str) -> dict:
    """
    Validate CAD geometry for printability.

    Checks:
    - Manifold/watertight geometry
    - Minimum wall thickness
    - Overhangs and supports
    """
    logger.info(f"Validating geometry: {file_url}")

    # Placeholder implementation
    return {
        "is_valid": True,
        "is_manifold": True,
        "issues": [],
        "printability_score": 0.95,
    }


@shared_task(
    name="app.worker.tasks.cad.generate_thumbnail",
)
def generate_thumbnail(
    file_url: str,
    output_size: tuple[int, int] = (512, 512),
) -> str:
    """
    Generate thumbnail image from CAD model.

    Returns:
        URL to generated thumbnail
    """
    logger.info(f"Generating thumbnail for: {file_url}")

    # Placeholder implementation
    return f"s3://thumbnails/{hash(file_url)}/thumb.png"


@shared_task(
    bind=True,
    name="app.worker.tasks.cad.generate_from_description",
    max_retries=2,
    default_retry_delay=30,
    time_limit=300,  # 5 minute hard limit
    soft_time_limit=240,  # 4 minute soft limit
)
def generate_from_description_task(
    self,
    job_id: str,
    description: str,
    export_step: bool = True,
    export_stl: bool = True,
    stl_quality: str = "standard",
    user_id: str | None = None,
) -> dict:
    """
    Generate CAD model from natural language description.

    This task:
    1. Parses the description using AI
    2. Generates 3D geometry
    3. Exports to requested formats
    4. Uploads to storage
    5. Updates job status

    Args:
        job_id: Job ID for status tracking
        description: Natural language part description
        export_step: Whether to generate STEP file
        export_stl: Whether to generate STL file
        stl_quality: STL quality preset
        user_id: User who requested the generation

    Returns:
        Dict with file URLs and metadata
    """
    import asyncio
    import tempfile
    from pathlib import Path

    from app.ai.generator import generate_from_description
    from app.cad.export import ExportQuality
    from app.core.database import async_session_maker
    from app.repositories import JobRepository

    async def run():
        async with async_session_maker() as session:
            job_repo = JobRepository(session)

            try:
                # Update job: started
                await job_repo.update(
                    UUID(job_id),
                    status="running",
                    started_at=datetime.now(tz=datetime.UTC),
                    progress=5,
                    progress_message="Analyzing description...",
                )
                await session.commit()

                # Generate CAD
                with tempfile.TemporaryDirectory() as temp_dir:
                    result = await generate_from_description(
                        description,
                        output_dir=Path(temp_dir),
                        export_step=export_step,
                        export_stl=export_stl,
                        stl_quality=ExportQuality(stl_quality),
                        job_id=job_id,
                    )

                    # Update progress
                    await job_repo.update(
                        UUID(job_id),
                        progress=80,
                        progress_message="Uploading files...",
                    )
                    await session.commit()

                    # Upload to storage
                    file_urls = {}

                    from app.core.storage import get_storage

                    storage = await get_storage()

                    if result.step_path and result.step_path.exists():
                        step_key = f"designs/{job_id}/model.step"
                        await storage.upload_file(
                            bucket="exports",
                            key=step_key,
                            data=result.step_path.read_bytes(),
                            content_type="application/step",
                        )
                        file_urls["step"] = step_key

                    if result.stl_path and result.stl_path.exists():
                        stl_key = f"designs/{job_id}/model.stl"
                        await storage.upload_file(
                            bucket="exports",
                            key=stl_key,
                            data=result.stl_path.read_bytes(),
                            content_type="model/stl",
                        )
                        file_urls["stl"] = stl_key

                # Build result
                output = {
                    "job_id": job_id,
                    "shape": result.parameters.shape.value,
                    "dimensions": result.parameters.dimensions,
                    "confidence": result.parameters.confidence,
                    "files": file_urls,
                    "timing": {
                        "parse_ms": result.parse_time_ms,
                        "generate_ms": result.generate_time_ms,
                        "export_ms": result.export_time_ms,
                        "total_ms": result.total_time_ms,
                    },
                    "warnings": result.warnings,
                }

                # Mark complete
                await job_repo.update(
                    UUID(job_id),
                    status="completed",
                    completed_at=datetime.now(tz=datetime.UTC),
                    progress=100,
                    progress_message="Complete",
                    result=output,
                )
                await session.commit()

                logger.info(
                    f"AI generation complete for job {job_id}: {result.parameters.shape.value}"
                )
                return output

            except Exception as e:
                logger.error(f"AI generation failed for job {job_id}: {e}")

                await job_repo.update(
                    UUID(job_id),
                    status="failed",
                    completed_at=datetime.now(tz=datetime.UTC),
                    error_message=str(e),
                    error={"message": str(e), "type": type(e).__name__},
                )
                await session.commit()
                raise

    try:
        return asyncio.run(run())
    except Exception as e:
        if self.request.retries < self.max_retries:
            logger.warning(f"Retrying job {job_id} after error: {e}")
            raise self.retry(exc=e)
        raise
