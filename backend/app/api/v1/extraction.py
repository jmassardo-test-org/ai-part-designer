"""
Dimension extraction API endpoints.

Provides endpoints for extracting dimensions from PDFs and images
using GPT-4 Vision.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.ai.vision import vision_extractor
from app.core.auth import get_current_user
from app.services.pdf_processor import pdf_processor

if TYPE_CHECKING:
    from app.models import User

logger = logging.getLogger(__name__)

# Note: prefix is set in __init__.py when including this router
router = APIRouter(tags=["extraction"])


# =============================================================================
# Request/Response Models
# =============================================================================


class DimensionResponse(BaseModel):
    """Extracted dimension response."""

    overall_dimensions: dict[str, Any] | None = None
    mounting_holes: list[dict[str, Any]] | None = None
    cutouts: list[dict[str, Any]] | None = None
    connectors: list[dict[str, Any]] | None = None
    tolerances: dict[str, Any] | None = None
    notes: list[str] | None = None
    confidence: float = 0.0
    pages_analyzed: int = 1


class ExtractionStatusResponse(BaseModel):
    """Status of extraction capability."""

    vision_available: bool
    pdf_available: bool
    supported_formats: list[str]


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/status",
    response_model=ExtractionStatusResponse,
    summary="Check extraction status",
    description="Check if dimension extraction is available.",
)
async def extraction_status() -> ExtractionStatusResponse:
    """Check extraction service availability."""
    from app.core.config import settings

    # Check if PyMuPDF is available
    try:
        import fitz

        pdf_available = True
    except ImportError:
        pdf_available = False

    return ExtractionStatusResponse(
        vision_available=bool(settings.ANTHROPIC_API_KEY),
        pdf_available=pdf_available,
        supported_formats=["image/png", "image/jpeg", "image/webp", "application/pdf"],
    )


@router.post(
    "/dimensions",
    response_model=DimensionResponse,
    summary="Extract dimensions from file",
    description="Extract dimensions and specifications from an uploaded image or PDF.",
)
async def extract_dimensions(
    file: UploadFile = File(..., description="Image or PDF file"),
    context: str = Form(
        default="",
        description="Optional context about what's in the file",
    ),
    analyze_all_pages: bool = Form(
        default=False,
        description="For PDFs, analyze all pages instead of just detected drawing pages",
    ),
    _current_user: User = Depends(get_current_user),
) -> DimensionResponse:
    """
    Extract dimensions from an uploaded file.

    Supports:
    - Images: PNG, JPEG, WebP
    - Documents: PDF (multi-page)

    For PDFs, automatically detects and analyzes pages likely to contain
    mechanical drawings. Use `analyze_all_pages=true` to process all pages.
    """
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # Validate file type
    supported_types = [
        "image/png",
        "image/jpeg",
        "image/webp",
        "application/pdf",
    ]

    if content_type not in supported_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type}. Supported: {supported_types}",
        )

    try:
        if content_type == "application/pdf":
            return await _extract_from_pdf(content, context, analyze_all_pages)
        return await _extract_from_image(content, context, content_type)

    except Exception as e:
        logger.exception("Extraction failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {e!s}",
        )


async def _extract_from_image(
    image_data: bytes,
    context: str,
    image_type: str,
) -> DimensionResponse:
    """Extract dimensions from a single image."""
    result = await vision_extractor.extract_dimensions(
        image_data=image_data,
        context=context,
        image_type=image_type,
    )

    return DimensionResponse(
        overall_dimensions=result.overall_dimensions,
        mounting_holes=result.mounting_holes,
        cutouts=result.cutouts,
        connectors=result.connectors,
        tolerances=result.tolerances,
        notes=result.notes,
        confidence=result.confidence,
        pages_analyzed=1,
    )


async def _extract_from_pdf(
    pdf_data: bytes,
    context: str,
    analyze_all_pages: bool,
) -> DimensionResponse:
    """Extract dimensions from a PDF document."""
    # Process PDF
    pdf_doc = pdf_processor.process_pdf(pdf_data)

    if not pdf_doc.pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process PDF - file may be corrupt",
        )

    # Determine which pages to analyze
    if analyze_all_pages:
        pages_to_analyze = pdf_doc.pages
    elif pdf_doc.drawing_pages:
        pages_to_analyze = [
            pdf_doc.pages[i] for i in pdf_doc.drawing_pages if i < len(pdf_doc.pages)
        ]
    else:
        # If no drawing pages detected, analyze first page
        pages_to_analyze = [pdf_doc.pages[0]] if pdf_doc.pages else []

    if not pages_to_analyze:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pages to analyze in PDF",
        )

    # Extract from each page
    images = [(page.image_data, "image/png") for page in pages_to_analyze]

    # Build context with page text
    full_context = context
    for page in pages_to_analyze:
        if page.text_content:
            full_context += f"\n\nPage {page.page_number + 1} text: {page.text_content[:500]}"

    result = await vision_extractor.extract_from_multiple_images(
        images=images,
        context=full_context,
    )

    return DimensionResponse(
        overall_dimensions=result.overall_dimensions,
        mounting_holes=result.mounting_holes,
        cutouts=result.cutouts,
        connectors=result.connectors,
        tolerances=result.tolerances,
        notes=result.notes,
        confidence=result.confidence,
        pages_analyzed=len(pages_to_analyze),
    )


@router.post(
    "/url",
    response_model=DimensionResponse,
    summary="Extract dimensions from URL",
    description="Extract dimensions from an image or PDF at a URL.",
)
async def extract_from_url(
    url: str = Form(..., description="URL of the image or PDF"),
    context: str = Form(default="", description="Optional context"),
    _current_user: User = Depends(get_current_user),
) -> DimensionResponse:
    """
    Extract dimensions from a file at a URL.

    Downloads the file and processes it like an upload.
    Useful for processing datasheets from component manufacturer websites.
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()

            content = response.content
            content_type = response.headers.get("content-type", "").split(";")[0]

            # Infer content type from URL if not provided
            if not content_type or content_type == "application/octet-stream":
                if url.lower().endswith(".pdf"):
                    content_type = "application/pdf"
                elif url.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    ext = url.split(".")[-1].lower()
                    content_type = f"image/{ext.replace('jpg', 'jpeg')}"

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to download file: {e!s}",
        )

    # Process like regular upload
    if content_type == "application/pdf":
        return await _extract_from_pdf(content, context, analyze_all_pages=False)
    if content_type.startswith("image/"):
        return await _extract_from_image(content, context, content_type)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported content type: {content_type}",
    )
