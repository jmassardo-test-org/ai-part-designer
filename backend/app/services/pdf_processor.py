"""
PDF processing service.

Converts PDF pages to images for vision analysis and
identifies pages likely containing mechanical drawings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import BinaryIO, cast

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class PDFPage:
    """Represents a processed PDF page."""

    page_number: int
    image_data: bytes
    width: int
    height: int
    has_text: bool = False
    is_drawing: bool = False
    text_content: str = ""


@dataclass
class PDFDocument:
    """Represents a processed PDF document."""

    pages: list[PDFPage]
    page_count: int
    title: str = ""
    author: str = ""
    drawing_pages: list[int] | None = None


# =============================================================================
# PDF Processor
# =============================================================================


class PDFProcessor:
    """
    Processes PDF documents for dimension extraction.

    Features:
    - Convert PDF pages to high-resolution images
    - Detect pages likely containing mechanical drawings
    - Extract text for context
    - Memory-efficient streaming
    """

    # Keywords that indicate a drawing page
    DRAWING_KEYWORDS = [
        "dimension",
        "dimensions",
        "mm",
        "inch",
        "in.",
        "scale",
        "mechanical",
        "drawing",
        "outline",
        "specification",
        "spec",
        "tolerance",
        "mounting",
        "hole",
        "cutout",
        "datasheet",
        "technical",
        "diagram",
        "schematic",
    ]

    def __init__(self, dpi: int = 300):
        """
        Initialize PDF processor.

        Args:
            dpi: Resolution for rendering pages (higher = better quality but larger)
        """
        self.dpi = dpi

    def pdf_to_images(self, pdf_data: bytes | BinaryIO) -> list[bytes]:
        """
        Convert all PDF pages to PNG images.

        Args:
            pdf_data: PDF file bytes or file-like object

        Returns:
            List of PNG image bytes for each page
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF not installed. Run: pip install PyMuPDF")
            return []

        try:
            # Handle both bytes and file-like objects
            if isinstance(pdf_data, bytes):
                doc = fitz.open(stream=pdf_data, filetype="pdf")
            else:
                pdf_bytes = pdf_data.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            images = []
            zoom = self.dpi / 72  # 72 is PDF default DPI

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Render at higher resolution
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                # Convert to PNG bytes
                img_bytes = pix.tobytes("png")
                images.append(img_bytes)

            doc.close()
            return images

        except Exception as e:
            logger.exception(f"Failed to process PDF: {e}")
            return []

    def process_pdf(self, pdf_data: bytes | BinaryIO) -> PDFDocument:
        """
        Process a PDF document completely.

        Args:
            pdf_data: PDF file bytes or file-like object

        Returns:
            PDFDocument with all pages processed
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF not installed")
            return PDFDocument(pages=[], page_count=0)

        try:
            if isinstance(pdf_data, bytes):
                doc = fitz.open(stream=pdf_data, filetype="pdf")
            else:
                pdf_bytes = pdf_data.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            pages = []
            drawing_pages = []
            zoom = self.dpi / 72

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Extract text
                text = page.get_text()

                # Check if this looks like a drawing page
                is_drawing = self._is_drawing_page(text)
                if is_drawing:
                    drawing_pages.append(page_num)

                # Render to image
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")

                pages.append(
                    PDFPage(
                        page_number=page_num,
                        image_data=img_bytes,
                        width=pix.width,
                        height=pix.height,
                        has_text=len(text.strip()) > 0,
                        is_drawing=is_drawing,
                        text_content=text[:1000],  # Limit stored text
                    )
                )

            # Get metadata
            metadata = doc.metadata
            doc.close()

            return PDFDocument(
                pages=pages,
                page_count=len(pages),
                title=metadata.get("title", ""),
                author=metadata.get("author", ""),
                drawing_pages=drawing_pages if drawing_pages else None,
            )

        except Exception as e:
            logger.exception(f"Failed to process PDF: {e}")
            return PDFDocument(pages=[], page_count=0)

    def find_drawing_pages(self, pdf_data: bytes | BinaryIO) -> list[int]:
        """
        Find pages that likely contain mechanical drawings.

        Args:
            pdf_data: PDF file bytes

        Returns:
            List of page numbers (0-indexed) that appear to be drawings
        """
        try:
            import fitz
        except ImportError:
            return []

        try:
            if isinstance(pdf_data, bytes):
                doc = fitz.open(stream=pdf_data, filetype="pdf")
            else:
                pdf_bytes = pdf_data.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            drawing_pages = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text().lower()

                if self._is_drawing_page(text):
                    drawing_pages.append(page_num)

            doc.close()
            return drawing_pages

        except Exception as e:
            logger.exception(f"Failed to find drawing pages: {e}")
            return []

    def get_page_image(
        self,
        pdf_data: bytes | BinaryIO,
        page_number: int,
    ) -> bytes | None:
        """
        Get a single page as an image.

        Args:
            pdf_data: PDF file bytes
            page_number: Page number (0-indexed)

        Returns:
            PNG image bytes or None if failed
        """
        try:
            import fitz
        except ImportError:
            return None

        try:
            if isinstance(pdf_data, bytes):
                doc = fitz.open(stream=pdf_data, filetype="pdf")
            else:
                pdf_bytes = pdf_data.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            if page_number < 0 or page_number >= len(doc):
                doc.close()
                return None

            page = doc.load_page(page_number)
            zoom = self.dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            doc.close()
            return cast("bytes", img_bytes)

        except Exception as e:
            logger.exception(f"Failed to get page image: {e}")
            return None

    def _is_drawing_page(self, text: str) -> bool:
        """Check if page text indicates a mechanical drawing."""
        text_lower = text.lower()

        # Count keyword matches
        matches = sum(1 for kw in self.DRAWING_KEYWORDS if kw in text_lower)

        # Require at least 2 keyword matches
        return matches >= 2


# =============================================================================
# Singleton
# =============================================================================

pdf_processor = PDFProcessor()
