"""
Component File Storage Service

Handles storage and retrieval of component source files:
- PDF datasheets
- CAD files (STEP, STL)
- Thumbnail generation
"""

import hashlib
import io
from pathlib import Path
from uuid import UUID, uuid4

import aiofiles
from fastapi import UploadFile
from PIL import Image

from app.core.config import settings

# =============================================================================
# Configuration
# =============================================================================

COMPONENT_FILES_DIR = Path(settings.UPLOAD_DIR) / "components"
DATASHEET_DIR = COMPONENT_FILES_DIR / "datasheets"
CAD_DIR = COMPONENT_FILES_DIR / "cad"
THUMBNAIL_DIR = COMPONENT_FILES_DIR / "thumbnails"

ALLOWED_DATASHEET_TYPES = {".pdf"}
ALLOWED_CAD_TYPES = {".step", ".stp", ".stl", ".iges", ".igs"}
ALLOWED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}

MAX_DATASHEET_SIZE = 50 * 1024 * 1024  # 50MB
MAX_CAD_SIZE = 100 * 1024 * 1024  # 100MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

THUMBNAIL_SIZES = {
    "small": (64, 64),
    "medium": (128, 128),
    "large": (256, 256),
}


# =============================================================================
# Directory Setup
# =============================================================================


def ensure_directories():
    """Ensure all required directories exist."""
    for directory in [DATASHEET_DIR, CAD_DIR, THUMBNAIL_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# =============================================================================
# File Hash
# =============================================================================


async def compute_file_hash(file: UploadFile) -> str:
    """Compute SHA-256 hash of file contents."""
    hasher = hashlib.sha256()

    # Reset file position
    await file.seek(0)

    while chunk := await file.read(8192):
        hasher.update(chunk)

    # Reset for later use
    await file.seek(0)

    return hasher.hexdigest()


# =============================================================================
# Storage Service
# =============================================================================


class ComponentFileStorage:
    """Service for storing component-related files."""

    def __init__(self):
        ensure_directories()

    # =========================================================================
    # Validation
    # =========================================================================

    def validate_datasheet(self, file: UploadFile) -> tuple[bool, str]:
        """Validate a datasheet file."""
        if not file.filename:
            return False, "No filename provided"

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_DATASHEET_TYPES:
            return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_DATASHEET_TYPES)}"

        return True, ""

    def validate_cad_file(self, file: UploadFile) -> tuple[bool, str]:
        """Validate a CAD file."""
        if not file.filename:
            return False, "No filename provided"

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_CAD_TYPES:
            return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_CAD_TYPES)}"

        return True, ""

    def validate_image(self, file: UploadFile) -> tuple[bool, str]:
        """Validate an image file."""
        if not file.filename:
            return False, "No filename provided"

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_TYPES:
            return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"

        return True, ""

    # =========================================================================
    # Storage
    # =========================================================================

    async def store_datasheet(
        self,
        file: UploadFile,
        component_id: UUID,
    ) -> dict:
        """
        Store a PDF datasheet.

        Returns:
            dict with file_id, path, size, hash
        """
        valid, error = self.validate_datasheet(file)
        if not valid:
            raise ValueError(error)

        file_id = uuid4()
        ext = Path(file.filename).suffix.lower()
        filename = f"{component_id}_{file_id}{ext}"
        file_path = DATASHEET_DIR / filename

        # Read content
        content = await file.read()

        if len(content) > MAX_DATASHEET_SIZE:
            raise ValueError(
                f"File too large. Maximum size: {MAX_DATASHEET_SIZE // (1024 * 1024)}MB"
            )

        # Compute hash
        file_hash = hashlib.sha256(content).hexdigest()

        # Write to disk
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return {
            "file_id": str(file_id),
            "path": str(file_path),
            "filename": file.filename,
            "size": len(content),
            "hash": file_hash,
            "content_type": "application/pdf",
        }

    async def store_cad_file(
        self,
        file: UploadFile,
        component_id: UUID,
    ) -> dict:
        """
        Store a CAD file (STEP, STL).

        Returns:
            dict with file_id, path, size, hash, format
        """
        valid, error = self.validate_cad_file(file)
        if not valid:
            raise ValueError(error)

        file_id = uuid4()
        ext = Path(file.filename).suffix.lower()
        filename = f"{component_id}_{file_id}{ext}"
        file_path = CAD_DIR / filename

        # Normalize extension
        if ext in {".stp"}:
            ext = ".step"
        elif ext in {".igs"}:
            ext = ".iges"

        # Read content
        content = await file.read()

        if len(content) > MAX_CAD_SIZE:
            raise ValueError(f"File too large. Maximum size: {MAX_CAD_SIZE // (1024 * 1024)}MB")

        # Compute hash
        file_hash = hashlib.sha256(content).hexdigest()

        # Determine content type
        content_types = {
            ".step": "application/step",
            ".stp": "application/step",
            ".stl": "application/sla",
            ".iges": "application/iges",
            ".igs": "application/iges",
        }

        # Write to disk
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return {
            "file_id": str(file_id),
            "path": str(file_path),
            "filename": file.filename,
            "size": len(content),
            "hash": file_hash,
            "format": ext.lstrip("."),
            "content_type": content_types.get(ext, "application/octet-stream"),
        }

    async def store_thumbnail(
        self,
        file: UploadFile,
        component_id: UUID,
    ) -> dict:
        """
        Store and process a thumbnail image.

        Generates multiple sizes for responsive display.

        Returns:
            dict with urls for each size
        """
        valid, error = self.validate_image(file)
        if not valid:
            raise ValueError(error)

        # Read image
        content = await file.read()

        if len(content) > MAX_IMAGE_SIZE:
            raise ValueError(f"Image too large. Maximum size: {MAX_IMAGE_SIZE // (1024 * 1024)}MB")

        # Open with PIL
        image = Image.open(io.BytesIO(content))

        # Convert to RGB if needed
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        thumbnails = {}

        for size_name, dimensions in THUMBNAIL_SIZES.items():
            # Create thumbnail
            thumb = image.copy()
            thumb.thumbnail(dimensions, Image.Resampling.LANCZOS)

            # Save
            filename = f"{component_id}_{size_name}.jpg"
            file_path = THUMBNAIL_DIR / filename

            thumb.save(file_path, "JPEG", quality=85, optimize=True)

            thumbnails[size_name] = {
                "path": str(file_path),
                "url": f"/api/v1/components/{component_id}/thumbnail/{size_name}",
                "width": thumb.width,
                "height": thumb.height,
            }

        return thumbnails

    # =========================================================================
    # Retrieval
    # =========================================================================

    async def get_datasheet(self, component_id: UUID, file_id: UUID) -> Path | None:
        """Get path to a datasheet file."""
        # Search for file with this ID
        pattern = f"{component_id}_{file_id}*.pdf"
        matches = list(DATASHEET_DIR.glob(pattern))

        if matches:
            return matches[0]

        return None

    async def get_cad_file(self, component_id: UUID, file_id: UUID) -> Path | None:
        """Get path to a CAD file."""
        # Search for file with this ID
        for ext in ALLOWED_CAD_TYPES:
            pattern = f"{component_id}_{file_id}*{ext}"
            matches = list(CAD_DIR.glob(pattern))
            if matches:
                return matches[0]

        return None

    async def get_thumbnail(self, component_id: UUID, size: str = "medium") -> Path | None:
        """Get path to a thumbnail."""
        if size not in THUMBNAIL_SIZES:
            size = "medium"

        file_path = THUMBNAIL_DIR / f"{component_id}_{size}.jpg"

        if file_path.exists():
            return file_path

        return None

    # =========================================================================
    # Deletion
    # =========================================================================

    async def delete_component_files(self, component_id: UUID) -> int:
        """
        Delete all files associated with a component.

        Returns:
            Number of files deleted
        """
        deleted = 0

        # Delete datasheets
        for file_path in DATASHEET_DIR.glob(f"{component_id}_*"):
            file_path.unlink()
            deleted += 1

        # Delete CAD files
        for file_path in CAD_DIR.glob(f"{component_id}_*"):
            file_path.unlink()
            deleted += 1

        # Delete thumbnails
        for file_path in THUMBNAIL_DIR.glob(f"{component_id}_*"):
            file_path.unlink()
            deleted += 1

        return deleted

    async def delete_file(self, file_path: str) -> bool:
        """Delete a specific file by path."""
        path = Path(file_path)

        if path.exists():
            path.unlink()
            return True

        return False


# =============================================================================
# Singleton Instance
# =============================================================================

component_file_storage = ComponentFileStorage()
