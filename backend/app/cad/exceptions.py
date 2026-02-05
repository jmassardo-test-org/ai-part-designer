"""
CAD-specific exceptions.

Provides a hierarchy of exceptions for CAD operations,
enabling precise error handling and user-friendly messages.
"""

from typing import Any


class CADError(Exception):
    """
    Base exception for all CAD operations.

    Attributes:
        message: Human-readable error description
        details: Optional additional context
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class GeometryError(CADError):
    """
    Invalid geometry or operation result.

    Raised when:
    - Boolean operation results in empty geometry
    - Fillet/chamfer radius is too large
    - Invalid shape topology
    - Geometry validation fails
    """


class ExportError(CADError):
    """
    File export operation failed.

    Raised when:
    - Cannot write to file path
    - Invalid export format
    - Tessellation/conversion fails
    - File system errors
    """


class ValidationError(CADError):
    """
    Parameter validation failed.

    Raised when:
    - Invalid dimensions (zero, negative)
    - Parameters out of range
    - Incompatible parameter combinations
    """


class TemplateError(CADError):
    """
    Template execution failed.

    Raised when:
    - Template not found
    - Invalid template parameters
    - Template script execution error
    """


class TimeoutError(CADError):
    """
    CAD operation timed out.

    Raised when:
    - Generation takes too long
    - Complex boolean operations hang
    """


class ImportError(CADError):
    """
    CAD import operation failed.

    Raised when:
    - Invalid file format
    - Corrupted file data
    - Unsupported features
    """
