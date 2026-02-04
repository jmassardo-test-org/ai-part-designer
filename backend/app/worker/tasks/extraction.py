"""
Component extraction Celery tasks.

Tasks for extracting specifications from component datasheets and CAD files.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.celery import celery_app
from app.core.database import async_session_maker
from app.models.reference_component import ComponentExtractionJob, ReferenceComponent
from app.ai.vision import vision_extractor, ExtractedDimensions
from app.services.pdf_processor import pdf_processor
from app.core.storage import storage_client, StorageBucket

logger = logging.getLogger(__name__)


# =============================================================================
# Extraction Task
# =============================================================================

@celery_app.task(
    name="extraction.extract_component",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def extract_component_task(self, job_id: str) -> dict[str, Any]:
    """
    Extract specifications from component datasheet or CAD file.
    
    This task:
    1. Downloads the component files from storage
    2. Processes PDF/image files using vision AI
    3. Extracts dimensions, mounting holes, connectors, etc.
    4. Updates the component with extracted specs
    
    Args:
        job_id: UUID of the ComponentExtractionJob
        
    Returns:
        Dict containing extraction results and confidence scores
    """
    import asyncio
    
    return asyncio.get_event_loop().run_until_complete(
        _extract_component_async(self, job_id)
    )


async def _extract_component_async(task, job_id: str) -> dict[str, Any]:
    """Async implementation of component extraction."""
    async with async_session_maker() as db:
        # Get the extraction job
        job = await _get_extraction_job(db, UUID(job_id))
        if not job:
            return {"error": "Extraction job not found", "job_id": job_id}
        
        # Update job status
        job.status = "processing"
        job.started_at = datetime.utcnow()
        job.current_step = "Initializing extraction"
        await db.commit()
        
        try:
            # Get the component
            component = await _get_component(db, job.component_id)
            if not component:
                raise ValueError(f"Component {job.component_id} not found")
            
            extracted_data = {}
            confidence_scores = []
            
            # Process based on job type
            if job.job_type in ("datasheet", "full"):
                job.current_step = "Extracting from datasheet"
                job.progress = 20
                await db.commit()
                
                datasheet_result = await _extract_from_datasheet(component)
                if datasheet_result:
                    extracted_data["datasheet"] = datasheet_result
                    confidence_scores.append(datasheet_result.get("confidence", 0.5))
                    job.progress = 50
                    await db.commit()
            
            if job.job_type in ("cad", "full"):
                job.current_step = "Extracting from CAD file"
                job.progress = 60
                await db.commit()
                
                cad_result = await _extract_from_cad(component)
                if cad_result:
                    extracted_data["cad"] = cad_result
                    confidence_scores.append(cad_result.get("confidence", 0.5))
                    job.progress = 80
                    await db.commit()
            
            # Merge extracted data into component
            job.current_step = "Updating component specifications"
            job.progress = 90
            await db.commit()
            
            await _update_component_specs(db, component, extracted_data)
            
            # Calculate overall confidence
            overall_confidence = (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0.0
            )
            
            # Complete the job
            job.status = "complete"
            job.progress = 100
            job.current_step = "Extraction complete"
            job.completed_at = datetime.utcnow()
            job.extracted_data = extracted_data
            job.confidence_score = overall_confidence
            component.extraction_status = "complete"
            component.confidence_score = overall_confidence
            
            await db.commit()
            
            logger.info(
                f"Extraction complete for component {component.id}, "
                f"confidence: {overall_confidence:.2f}"
            )
            
            return {
                "job_id": job_id,
                "status": "complete",
                "confidence": overall_confidence,
                "extracted_data": extracted_data,
            }
            
        except Exception as e:
            logger.exception(f"Extraction failed for job {job_id}: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job.retry_count += 1
            component = await _get_component(db, job.component_id)
            if component:
                component.extraction_status = "failed"
            await db.commit()
            raise


async def _get_extraction_job(db: AsyncSession, job_id: UUID) -> ComponentExtractionJob | None:
    """Fetch extraction job by ID."""
    result = await db.execute(
        select(ComponentExtractionJob).where(ComponentExtractionJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def _get_component(db: AsyncSession, component_id: UUID) -> ReferenceComponent | None:
    """Fetch component by ID."""
    result = await db.execute(
        select(ReferenceComponent).where(ReferenceComponent.id == component_id)
    )
    return result.scalar_one_or_none()


async def _extract_from_datasheet(component: ReferenceComponent) -> dict[str, Any] | None:
    """
    Extract specifications from component datasheet PDF.
    
    Uses GPT-4 Vision to analyze the datasheet and extract:
    - Overall dimensions
    - Mounting hole positions
    - Connector locations
    - Clearance zones
    - Thermal properties
    """
    from app.core.config import settings
    
    if not component.datasheet_url:
        logger.info(f"No datasheet URL for component {component.id}")
        return None
    
    try:
        # Download the datasheet from storage
        datasheet_content = await _download_file(component.datasheet_url)
        if not datasheet_content:
            return None
        
        # Convert PDF to images if needed
        if component.datasheet_url.lower().endswith(".pdf"):
            images = await pdf_processor.convert_to_images(datasheet_content)
            if not images:
                return None
            
            # Use first page or find mechanical drawing page
            image_data = images[0]
        else:
            image_data = datasheet_content
        
        # Extract dimensions using vision AI
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("Anthropic API key not configured for vision extraction")
            return {"confidence": 0.0, "message": "Vision AI not configured"}
        
        result = await vision_extractor.extract_dimensions(
            image_data,
            context=f"Component: {component.name}, Category: {component.category}"
        )
        
        return {
            "dimensions": result.overall_dimensions,
            "mounting_holes": result.mounting_holes,
            "connectors": result.connectors,
            "cutouts": result.cutouts,
            "tolerances": result.tolerances,
            "notes": result.notes,
            "confidence": result.confidence,
        }
        
    except Exception as e:
        logger.exception(f"Error extracting from datasheet: {e}")
        return {"error": str(e), "confidence": 0.0}


async def _extract_from_cad(component: ReferenceComponent) -> dict[str, Any] | None:
    """
    Extract specifications from component CAD file.
    
    Analyzes STEP/IGES/STL files to extract:
    - Precise dimensions
    - Mounting hole diameters and positions
    - Connector cutout sizes
    """
    if not component.cad_file_url:
        logger.info(f"No CAD file URL for component {component.id}")
        return None
    
    try:
        # Download the CAD file from storage
        cad_content = await _download_file(component.cad_file_url)
        if not cad_content:
            return None
        
        # For now, return basic geometry extraction
        # Full CAD parsing would require OCP/CadQuery
        file_ext = component.cad_file_url.split(".")[-1].lower()
        
        if file_ext in ("step", "stp"):
            # Parse STEP file
            try:
                from build123d import import_step
                import tempfile
                import os
                
                # Write to temp file and import
                with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
                    f.write(cad_content)
                    temp_path = f.name
                
                try:
                    shape = import_step(temp_path)
                    bbox = shape.bounding_box()
                    
                    return {
                        "dimensions": {
                            "length": round(bbox.max.X - bbox.min.X, 2),
                            "width": round(bbox.max.Y - bbox.min.Y, 2),
                            "height": round(bbox.max.Z - bbox.min.Z, 2),
                            "unit": "mm",
                        },
                        "confidence": 0.95,
                        "source": "cad_geometry",
                    }
                finally:
                    os.unlink(temp_path)
                    
            except Exception as e:
                logger.warning(f"Failed to parse STEP file: {e}")
                return {"error": str(e), "confidence": 0.0}
        
        elif file_ext == "stl":
            # Parse STL file for bounding box
            try:
                from build123d import import_stl
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
                    f.write(cad_content)
                    temp_path = f.name
                
                try:
                    shape = import_stl(temp_path)
                    bbox = shape.bounding_box()
                    
                    return {
                        "dimensions": {
                            "length": round(bbox.max.X - bbox.min.X, 2),
                            "width": round(bbox.max.Y - bbox.min.Y, 2),
                            "height": round(bbox.max.Z - bbox.min.Z, 2),
                            "unit": "mm",
                        },
                        "confidence": 0.85,  # Lower confidence for STL
                        "source": "cad_geometry",
                    }
                finally:
                    os.unlink(temp_path)
                    
            except Exception as e:
                logger.warning(f"Failed to parse STL file: {e}")
                return {"error": str(e), "confidence": 0.0}
        
        return {
            "message": f"CAD format {file_ext} not fully supported",
            "confidence": 0.0,
        }
        
    except Exception as e:
        logger.exception(f"Error extracting from CAD file: {e}")
        return {"error": str(e), "confidence": 0.0}


async def _download_file(url: str) -> bytes | None:
    """Download file from storage or URL."""
    try:
        if url.startswith("http"):
            # External URL - use httpx
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True)
                if response.status_code == 200:
                    return response.content
        else:
            # Storage path - extract key and download
            key = url.split("/", 3)[-1] if "/" in url else url
            return await storage_client.download(
                bucket=StorageBucket.UPLOADS,
                key=key,
            )
    except Exception as e:
        logger.warning(f"Failed to download file from {url}: {e}")
    return None


async def _update_component_specs(
    db: AsyncSession,
    component: ReferenceComponent,
    extracted_data: dict[str, Any],
) -> None:
    """
    Update component with extracted specifications.
    
    Merges extracted data from multiple sources (datasheet + CAD),
    preferring higher-confidence values.
    """
    # Get datasheet and CAD results
    datasheet = extracted_data.get("datasheet", {})
    cad = extracted_data.get("cad", {})
    
    # Prefer CAD dimensions if available (higher precision)
    if cad.get("dimensions"):
        component.dimensions = cad["dimensions"]
    elif datasheet.get("dimensions"):
        component.dimensions = datasheet["dimensions"]
    
    # Merge mounting holes (datasheet often has more detail)
    if datasheet.get("mounting_holes"):
        component.mounting_holes = datasheet["mounting_holes"]
    
    # Merge connectors
    if datasheet.get("connectors"):
        component.connectors = datasheet["connectors"]
    
    # Merge clearance zones
    if datasheet.get("cutouts"):
        component.clearance_zones = datasheet["cutouts"]
    
    component.updated_at = datetime.utcnow()


# =============================================================================
# Batch Extraction Task
# =============================================================================

@celery_app.task(
    name="extraction.batch_extract",
    bind=True,
)
def batch_extract_task(self, component_ids: list[str]) -> dict[str, Any]:
    """
    Batch extract specifications for multiple components.
    
    Creates individual extraction jobs for each component and queues them.
    
    Args:
        component_ids: List of component UUIDs to process
        
    Returns:
        Dict with job IDs and counts
    """
    import asyncio
    
    return asyncio.get_event_loop().run_until_complete(
        _batch_extract_async(component_ids)
    )


async def _batch_extract_async(component_ids: list[str]) -> dict[str, Any]:
    """Async implementation of batch extraction."""
    async with async_session_maker() as db:
        jobs_created = []
        
        for component_id in component_ids:
            try:
                component = await _get_component(db, UUID(component_id))
                if not component:
                    continue
                
                # Create extraction job
                from uuid import uuid4
                job = ComponentExtractionJob(
                    id=uuid4(),
                    component_id=UUID(component_id),
                    job_type="full",
                    status="pending",
                    progress=0,
                )
                db.add(job)
                jobs_created.append(str(job.id))
                
                # Update component status
                component.extraction_status = "pending"
                
            except Exception as e:
                logger.warning(f"Failed to create job for {component_id}: {e}")
        
        await db.commit()
        
        # Queue individual extraction tasks
        for job_id in jobs_created:
            extract_component_task.delay(job_id)
        
        return {
            "total_requested": len(component_ids),
            "jobs_created": len(jobs_created),
            "job_ids": jobs_created,
        }
