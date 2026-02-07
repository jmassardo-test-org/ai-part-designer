"""
AI processing tasks.
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


@shared_task(  # type: ignore[untyped-decorator]
    bind=True,
    name="app.worker.tasks.ai.generate_from_prompt",
    max_retries=2,
    default_retry_delay=30,
)
def generate_from_prompt(
    self: Any,
    job_id: str,
    prompt: str,
    _context: dict[str, Any] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate CAD model from natural language prompt.

    Uses AI to interpret the prompt and generate CadQuery code,
    then executes the code to create the model.

    Args:
        job_id: Job ID to update with progress
        prompt: User's natural language description
        context: Additional context (user preferences, constraints, etc.)
        user_id: User ID for WebSocket updates

    Returns:
        Dict with generated model info
    """
    import asyncio

    from app.core.database import async_session_maker
    from app.repositories import JobRepository

    # Send job started notification
    if user_id:
        send_job_started(user_id, job_id, "ai_generation")

    async def run() -> dict[str, Any]:
        async with async_session_maker() as session:
            job_repo = JobRepository(session)

            # Update job status
            await job_repo.update(
                UUID(job_id),
                status="running",
                started_at=datetime.now(tz=UTC),
                progress=10,
                progress_message="Analyzing prompt",
            )
            await session.commit()

            if user_id:
                send_job_progress(user_id, job_id, 10, "running", "Analyzing prompt")

            # Step 1: Content moderation
            await job_repo.update(
                UUID(job_id),
                progress=20,
                progress_message="Checking content policy",
            )
            await session.commit()

            if user_id:
                send_job_progress(user_id, job_id, 20, "running", "Checking content policy")

            # Call moderation check
            moderation_result = await _check_content_moderation(prompt)

            if moderation_result.get("flagged"):
                error_msg = "Content policy violation"
                await job_repo.update(
                    UUID(job_id),
                    status="failed",
                    completed_at=datetime.now(tz=UTC),
                    error_message=error_msg,
                    error=moderation_result,
                )
                await session.commit()

                if user_id:
                    send_job_failed(user_id, job_id, error_msg, "ContentPolicyViolation")

                raise ValueError(error_msg)

            # Step 2: Generate CAD using AI pipeline
            await job_repo.update(
                UUID(job_id),
                progress=40,
                progress_message="Generating CAD code",
            )
            await session.commit()

            if user_id:
                send_job_progress(user_id, job_id, 40, "running", "Generating CAD code")

            # Use the AI generator to create CAD from description
            from app.ai.generator import generate_from_description
            from app.cad.export import ExportQuality

            try:
                generation_result = await generate_from_description(
                    prompt,
                    export_step=True,
                    export_stl=True,
                    stl_quality=ExportQuality.STANDARD,
                    job_id=job_id,
                    use_reasoning=True,
                )
            except Exception as gen_error:
                logger.error(f"CAD generation failed: {gen_error}")
                await job_repo.update(
                    UUID(job_id),
                    status="failed",
                    completed_at=datetime.now(tz=UTC),
                    error_message=str(gen_error),
                )
                await session.commit()

                if user_id:
                    send_job_failed(user_id, job_id, str(gen_error), "GenerationError")

                raise ValueError(f"CAD generation failed: {gen_error}")

            # Step 3: Upload generated files to storage
            await job_repo.update(
                UUID(job_id),
                progress=80,
                progress_message="Uploading generated files",
            )
            await session.commit()

            if user_id:
                send_job_progress(user_id, job_id, 80, "running", "Uploading generated files")

            from app.core.storage import StorageBucket, storage_client

            file_urls = {}

            # Upload STEP file if generated
            if generation_result.step_data:
                step_key = f"designs/{job_id}/model.step"
                await storage_client.upload_file(
                    bucket=StorageBucket.EXPORTS,
                    key=step_key,
                    file=generation_result.step_data,
                    content_type="application/step",
                )
                file_urls["step"] = await storage_client.generate_presigned_download_url(
                    bucket=StorageBucket.EXPORTS,
                    key=step_key,
                    expires_in=86400,
                )

            # Upload STL file if generated
            if generation_result.stl_data:
                stl_key = f"designs/{job_id}/model.stl"
                await storage_client.upload_file(
                    bucket=StorageBucket.EXPORTS,
                    key=stl_key,
                    file=generation_result.stl_data,
                    content_type="model/stl",
                )
                file_urls["stl"] = await storage_client.generate_presigned_download_url(
                    bucket=StorageBucket.EXPORTS,
                    key=stl_key,
                    expires_in=86400,
                )

            # Build result with generation info
            result = {
                "files": file_urls,
                "generated_code": generation_result.generated_code,
                "interpretation": {
                    "understood_as": generation_result.intent.part_type
                    if generation_result.intent
                    else "Unknown",
                    "confidence": generation_result.intent.confidence
                    if generation_result.intent
                    else 0.0,
                    "assumptions": generation_result.intent.assumptions_made
                    if generation_result.intent
                    else [],
                },
                "geometry_info": {
                    "bounding_box": generation_result.geometry_info.get("bounding_box")
                    if generation_result.geometry_info
                    else None,
                    "volume": generation_result.geometry_info.get("volume")
                    if generation_result.geometry_info
                    else None,
                },
                "warnings": generation_result.warnings,
                "timing": {
                    "reasoning_ms": generation_result.reasoning_time_ms,
                    "generation_ms": generation_result.generation_time_ms,
                    "total_ms": generation_result.total_time_ms,
                },
            }

            # Mark complete
            await job_repo.update(
                UUID(job_id),
                status="completed",
                completed_at=datetime.now(tz=UTC),
                progress=100,
                result=result,
            )
            await session.commit()

            if user_id:
                send_job_complete(user_id, job_id, result)

            logger.info(f"AI generation complete for job {job_id}")
            return result

    try:
        return asyncio.run(run())
    except Exception as e:
        logger.error(f"AI generation failed: {e}")

        if user_id:
            send_job_failed(user_id, job_id, str(e), type(e).__name__)

        raise self.retry(exc=e) if self.request.retries < self.max_retries else e


async def _check_content_moderation(content: str) -> dict[str, Any]:
    """
    Check content against moderation policies.

    Uses AI provider to check for prohibited content categories.

    Args:
        content: The text content to moderate

    Returns:
        Dict with flagged status, categories, and decision
    """
    # Define prohibited content patterns
    prohibited_patterns = [
        r"\b(weapon|gun|firearm|bomb|explosive)\b",
        r"\b(drug|narcotic|cocaine|heroin)\b",
        r"\b(harm|kill|attack|destroy)\b",
    ]

    import re

    content_lower = content.lower()

    categories = {
        "weapons": {"score": 0.0, "flagged": False},
        "drugs": {"score": 0.0, "flagged": False},
        "violence": {"score": 0.0, "flagged": False},
    }

    # Check for prohibited patterns
    for pattern in prohibited_patterns:
        if re.search(pattern, content_lower):
            if "weapon" in pattern or "gun" in pattern:
                categories["weapons"]["score"] = 0.9
                categories["weapons"]["flagged"] = True
            elif "drug" in pattern or "narcotic" in pattern:
                categories["drugs"]["score"] = 0.9
                categories["drugs"]["flagged"] = True
            elif "harm" in pattern or "kill" in pattern:
                categories["violence"]["score"] = 0.9
                categories["violence"]["flagged"] = True

    flagged = any(cat["flagged"] for cat in categories.values())

    return {
        "flagged": flagged,
        "categories": categories,
        "decision": "rejected" if flagged else "approved",
    }


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.ai.suggest_modifications",
)
def suggest_modifications(
    design_id: str,
    user_request: str,
) -> dict[str, Any]:
    """
    Suggest modifications to a design based on user request.

    Uses AI to understand the request and propose parameter changes.

    Args:
        design_id: ID of the design to modify
        user_request: User's natural language modification request

    Returns:
        Dict with suggested modifications and confidence scores
    """
    import asyncio

    from app.core.database import async_session_maker
    from app.repositories import DesignRepository

    logger.info(f"Suggesting modifications for design {design_id}")

    async def run() -> dict[str, Any]:
        async with async_session_maker() as session:
            design_repo = DesignRepository(session)
            design = await design_repo.get_by_id(UUID(design_id))

            if not design:
                raise ValueError(f"Design not found: {design_id}")

            # Get current parameters from design
            current_params = design.parameters or {}

            # Use AI to analyze the modification request
            from app.ai.client import get_ai_client

            ai_client = get_ai_client()

            prompt = f"""Analyze this modification request for a CAD design:

Current parameters: {current_params}

User request: "{user_request}"

Respond with a JSON object containing suggested parameter changes:
{{
  "suggestions": [
    {{
      "description": "Brief description of the change",
      "parameter": "parameter_name",
      "current_value": <current value>,
      "new_value": <suggested new value>,
      "confidence": <0.0 to 1.0>
    }}
  ],
  "reasoning": "Brief explanation of why these changes were suggested"
}}

Only output the JSON. No markdown."""

            try:
                response = await ai_client.generate(
                    prompt=prompt,
                    system_prompt="You are a CAD design assistant that suggests parameter modifications.",
                    temperature=0.3,
                )

                # Parse the response
                import json
                import re

                # Extract JSON from response
                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    result: dict[str, Any] = json.loads(json_match.group())
                    return result
                logger.warning("Failed to parse AI response, returning default")

            except Exception as e:
                logger.error(f"AI suggestion failed: {e}")

            # Fallback response if AI fails
            return {
                "suggestions": [],
                "reasoning": "Could not analyze the modification request",
            }

    return asyncio.run(run())


@shared_task(  # type: ignore[untyped-decorator]
    name="app.worker.tasks.ai.moderate_content",
)
def moderate_content(
    content: str,
    content_type: str = "prompt",
) -> dict[str, Any]:
    """
    Check content against moderation policies.

    Returns moderation decision and category scores.

    Args:
        content: The content to moderate
        content_type: Type of content (prompt, code, description)

    Returns:
        Dict with flagged status, categories, and decision
    """
    import asyncio

    logger.info(f"Moderating {content_type}")

    return asyncio.run(_check_content_moderation(content))
