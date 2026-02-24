"""
CAD v2 generation Celery tasks.

Async tasks for generating enclosures using the v2 declarative schema pipeline.
"""

from __future__ import annotations

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


@shared_task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.worker.tasks.cad_v2.compile_enclosure_v2",
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=300,  # 5 minutes
    time_limit=360,  # 6 minutes hard limit
)
def compile_enclosure_v2(
    _self: Any,
    job_id: str,
    enclosure_schema: dict[str, Any],
    export_format: str = "step",
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Compile an enclosure schema to CAD files asynchronously.

    This task takes a validated EnclosureSpec schema and:
    1. Validates the schema
    2. Compiles to Build123d geometry
    3. Exports to requested format(s)
    4. Updates job status and sends WebSocket updates

    Args:
        job_id: Job ID for status tracking
        enclosure_schema: EnclosureSpec as dict
        export_format: Export format (step or stl)
        user_id: User ID for WebSocket updates

    Returns:
        Dict with success status, parts, and download URLs
    """
    import asyncio

    from app.core.database import async_session_maker
    from app.repositories import JobRepository

    # Send job started notification
    if user_id:
        send_job_started(user_id, job_id, "cad_v2_compile")

    async def run_compile() -> dict[str, Any]:
        async with async_session_maker() as session:
            job_repo = JobRepository(session)

            try:
                # Update job status to running
                await job_repo.update(
                    UUID(job_id),
                    status="running",
                    started_at=datetime.now(UTC),
                    progress=10,
                    progress_message="Validating schema",
                )
                await session.commit()

                if user_id:
                    send_job_progress(user_id, job_id, 10, "running", "Validating schema")

                # Step 1: Validate schema
                from pydantic import ValidationError

                from app.cad_v2.schemas.enclosure import EnclosureSpec

                try:
                    spec = EnclosureSpec.model_validate(enclosure_schema)
                except ValidationError as e:
                    errors = [str(err) for err in e.errors()]
                    await _fail_job(
                        job_repo,
                        session,
                        job_id,
                        user_id,
                        f"Schema validation failed: {'; '.join(errors)}",
                    )
                    return {"success": False, "errors": errors}

                # Update progress
                await job_repo.update(
                    UUID(job_id),
                    progress=30,
                    progress_message="Compiling geometry",
                )
                await session.commit()

                if user_id:
                    send_job_progress(user_id, job_id, 30, "running", "Compiling geometry")

                # Step 2: Compile to geometry
                from app.cad_v2.compiler import CompilationEngine

                engine = CompilationEngine()

                try:
                    compilation = engine.compile_enclosure(spec)
                except Exception as e:
                    logger.exception("Compilation failed")
                    await _fail_job(
                        job_repo, session, job_id, user_id, f"Compilation failed: {e!s}"
                    )
                    return {"success": False, "errors": [str(e)]}

                if not compilation.success:
                    await _fail_job(
                        job_repo,
                        session,
                        job_id,
                        user_id,
                        f"Compilation errors: {'; '.join(compilation.errors)}",
                    )
                    return {"success": False, "errors": compilation.errors}

                # Update progress
                await job_repo.update(
                    UUID(job_id),
                    progress=70,
                    progress_message="Exporting CAD files",
                )
                await session.commit()

                if user_id:
                    send_job_progress(user_id, job_id, 70, "running", "Exporting CAD files")

                # Step 3: Export files
                from app.api.v2.downloads import get_job_dir
                from app.cad_v2.compiler.engine import ExportFormat

                fmt = ExportFormat.STL if export_format.lower() == "stl" else ExportFormat.STEP

                job_dir = get_job_dir(job_id)
                job_dir.mkdir(parents=True, exist_ok=True)

                try:
                    paths = compilation.export(str(job_dir), fmt)
                except Exception as e:
                    logger.exception("Export failed")
                    await _fail_job(job_repo, session, job_id, user_id, f"Export failed: {e!s}")
                    return {"success": False, "errors": [f"Export failed: {e!s}"]}

                downloads = {p.stem: f"/api/v2/downloads/{job_id}/{p.name}" for p in paths}
                parts = list(compilation.parts.keys())

                # Update progress
                await job_repo.update(
                    UUID(job_id),
                    progress=90,
                    progress_message="Finalizing",
                )
                await session.commit()

                if user_id:
                    send_job_progress(user_id, job_id, 90, "running", "Finalizing")

                # Complete the job
                result = {
                    "success": True,
                    "parts": parts,
                    "downloads": downloads,
                    "generated_schema": enclosure_schema,
                    "warnings": [],
                }

                await job_repo.update(
                    UUID(job_id),
                    status="completed",
                    completed_at=datetime.now(UTC),
                    progress=100,
                    progress_message="Complete",
                    result=result,
                )
                await session.commit()

                if user_id:
                    send_job_complete(user_id, job_id, result)

                    # Persist notification for offline users
                    from app.services.notification_service import notify_job_completed

                    await notify_job_completed(
                        db=session,
                        user_id=UUID(user_id),
                        job_id=UUID(job_id),
                        job_type="enclosure compile",
                        design_name="enclosure",
                    )

                logger.info(f"CAD v2 job {job_id} completed successfully")
                return result

            except Exception as e:
                logger.exception(f"Unexpected error in CAD v2 job {job_id}")
                await _fail_job(job_repo, session, job_id, user_id, f"Unexpected error: {e!s}")
                return {"success": False, "errors": [str(e)]}

    # Run the async function
    return asyncio.get_event_loop().run_until_complete(run_compile())


async def _fail_job(
    job_repo: Any,
    session: Any,
    job_id: str,
    user_id: str | None,
    error_message: str,
) -> None:
    """Helper to mark job as failed and send notification."""
    await job_repo.update(
        UUID(job_id),
        status="failed",
        completed_at=datetime.now(UTC),
        error_message=error_message,
    )
    await session.commit()

    if user_id:
        send_job_failed(user_id, job_id, error_message)

        # Persist notification for offline users
        from app.services.notification_service import notify_job_failed

        await notify_job_failed(
            db=session,
            user_id=UUID(user_id),
            job_id=UUID(job_id),
            job_type="CAD v2",
            design_name="design",
            error_message=error_message,
        )

    logger.error(f"CAD v2 job {job_id} failed: {error_message}")


@shared_task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.worker.tasks.cad_v2.generate_from_description_v2",
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=600,  # 10 minutes (includes AI)
    time_limit=720,  # 12 minutes hard limit
)
def generate_from_description_v2(
    _self: Any,
    job_id: str,
    description: str,
    export_format: str = "step",
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate CAD from natural language description asynchronously.

    Full v2 pipeline:
    1. Parse intent with AI
    2. Generate EnclosureSpec schema
    3. Compile to Build123d geometry
    4. Export to requested format(s)

    Args:
        job_id: Job ID for status tracking
        description: Natural language description
        export_format: Export format (step or stl)
        user_id: User ID for WebSocket updates

    Returns:
        Dict with success status, schema, parts, and download URLs
    """
    import asyncio

    from app.core.database import async_session_maker
    from app.repositories import JobRepository

    # Send job started notification
    if user_id:
        send_job_started(user_id, job_id, "cad_v2_generate")

    async def run_generate() -> dict[str, Any]:
        async with async_session_maker() as session:
            job_repo = JobRepository(session)

            try:
                # Update job status
                await job_repo.update(
                    UUID(job_id),
                    status="running",
                    started_at=datetime.now(UTC),
                    progress=5,
                    progress_message="Analyzing description",
                )
                await session.commit()

                if user_id:
                    send_job_progress(user_id, job_id, 5, "running", "Analyzing description")

                # Step 1: Generate schema from description
                from app.cad_v2.ai import SchemaGenerator

                generator = SchemaGenerator()

                await job_repo.update(
                    UUID(job_id),
                    progress=15,
                    progress_message="Generating schema with AI",
                )
                await session.commit()

                if user_id:
                    send_job_progress(user_id, job_id, 15, "running", "Generating schema with AI")

                try:
                    result = await generator.generate(description)
                except Exception as e:
                    logger.exception("Schema generation failed")
                    await _fail_job(
                        job_repo, session, job_id, user_id, f"AI schema generation failed: {e!s}"
                    )
                    return {"success": False, "errors": [str(e)]}

                # Check for clarification needed
                if result.clarification_needed:
                    await job_repo.update(
                        UUID(job_id),
                        status="needs_clarification",
                        progress=20,
                        progress_message="Clarification needed",
                        result={"clarification_needed": result.clarification_needed},
                    )
                    await session.commit()

                    if user_id:
                        send_job_progress(
                            user_id, job_id, 20, "needs_clarification", result.clarification_needed
                        )

                    return {
                        "success": False,
                        "clarification_needed": result.clarification_needed,
                    }

                # Check for validation errors
                if not result.success or result.spec is None:
                    errors = result.validation_errors or ["Unknown schema error"]
                    await _fail_job(
                        job_repo,
                        session,
                        job_id,
                        user_id,
                        f"Schema validation failed: {'; '.join(errors)}",
                    )
                    return {
                        "success": False,
                        "errors": errors,
                        "generated_schema": result.raw_json,
                    }

                # Update progress
                await job_repo.update(
                    UUID(job_id),
                    progress=40,
                    progress_message="Compiling geometry",
                )
                await session.commit()

                if user_id:
                    send_job_progress(user_id, job_id, 40, "running", "Compiling geometry")

                # Step 2: Compile to geometry
                from app.cad_v2.compiler import CompilationEngine

                engine = CompilationEngine()

                try:
                    compilation = engine.compile_enclosure(result.spec)
                except Exception as e:
                    logger.exception("Compilation failed")
                    await _fail_job(
                        job_repo, session, job_id, user_id, f"Compilation failed: {e!s}"
                    )
                    return {
                        "success": False,
                        "errors": [str(e)],
                        "generated_schema": result.raw_json,
                    }

                if not compilation.success:
                    await _fail_job(
                        job_repo,
                        session,
                        job_id,
                        user_id,
                        f"Compilation errors: {'; '.join(compilation.errors)}",
                    )
                    return {
                        "success": False,
                        "errors": compilation.errors,
                        "generated_schema": result.raw_json,
                    }

                # Update progress
                await job_repo.update(
                    UUID(job_id),
                    progress=75,
                    progress_message="Exporting CAD files",
                )
                await session.commit()

                if user_id:
                    send_job_progress(user_id, job_id, 75, "running", "Exporting CAD files")

                # Step 3: Export files
                from app.api.v2.downloads import get_job_dir
                from app.cad_v2.compiler.engine import ExportFormat

                fmt = ExportFormat.STL if export_format.lower() == "stl" else ExportFormat.STEP

                job_dir = get_job_dir(job_id)
                job_dir.mkdir(parents=True, exist_ok=True)

                try:
                    paths = compilation.export(str(job_dir), fmt)
                except Exception as e:
                    logger.exception("Export failed")
                    await _fail_job(job_repo, session, job_id, user_id, f"Export failed: {e!s}")
                    return {
                        "success": False,
                        "errors": [f"Export failed: {e!s}"],
                        "generated_schema": result.raw_json,
                    }

                downloads = {p.stem: f"/api/v2/downloads/{job_id}/{p.name}" for p in paths}
                parts = list(compilation.parts.keys())

                # Complete the job
                job_result = {
                    "success": True,
                    "parts": parts,
                    "downloads": downloads,
                    "generated_schema": result.raw_json,
                    "warnings": result.warnings or [],
                }

                await job_repo.update(
                    UUID(job_id),
                    status="completed",
                    completed_at=datetime.now(UTC),
                    progress=100,
                    progress_message="Complete",
                    result=job_result,
                )
                await session.commit()

                if user_id:
                    send_job_complete(user_id, job_id, job_result)

                    # Persist notification for offline users
                    from app.services.notification_service import notify_job_completed

                    await notify_job_completed(
                        db=session,
                        user_id=UUID(user_id),
                        job_id=UUID(job_id),
                        job_type="AI enclosure generation",
                        design_name=description[:50] if description else "design",
                    )

                logger.info(f"CAD v2 generate job {job_id} completed successfully")
                return job_result

            except Exception as e:
                logger.exception(f"Unexpected error in CAD v2 generate job {job_id}")
                await _fail_job(job_repo, session, job_id, user_id, f"Unexpected error: {e!s}")
                return {"success": False, "errors": [str(e)]}

    # Run the async function
    return asyncio.get_event_loop().run_until_complete(run_generate())
