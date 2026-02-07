"""
Common type aliases used throughout the application.

Type aliases improve code readability and maintainability by:
- Providing semantic meaning to types
- Centralizing type definitions for easy updates
- Reducing repetition of complex type expressions

Usage:
    from app.types.aliases import SQLFilter, EntityID, JSONDict

    def apply_filters(filters: list[SQLFilter]) -> None:
        ...

    def get_entity(id: EntityID) -> Entity:
        ...
"""

from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# Database Types
# =============================================================================

type AsyncDB = AsyncSession
"""Async database session type alias."""

type SQLFilter = ColumnElement[bool]
"""Single SQLAlchemy filter condition."""

type SQLFilters = list[ColumnElement[bool]]
"""List of SQLAlchemy filter conditions for combining with and_/or_."""

# =============================================================================
# JSON Types
# =============================================================================

type JSONPrimitive = str | int | float | bool | None
"""Primitive JSON value types."""

type JSONValue = JSONPrimitive | list[Any] | dict[str, Any]
"""Any valid JSON value (primitive, array, or object)."""

type JSONDict = dict[str, Any]
"""JSON object type (dictionary with string keys)."""

type JSONList = list[Any]
"""JSON array type."""

# =============================================================================
# Entity ID Types
# =============================================================================

type EntityID = UUID
"""Generic entity identifier."""

type UserID = UUID
"""User entity identifier."""

type ProjectID = UUID
"""Project entity identifier."""

type DesignID = UUID
"""Design entity identifier."""

# =============================================================================
# Pagination Types
# =============================================================================

type PageNumber = int
"""1-based page number for pagination."""

type PageSize = int
"""Number of items per page."""

type Offset = int
"""Number of items to skip (0-based)."""

type Limit = int
"""Maximum number of items to return."""

# =============================================================================
# CAD/Geometry Types
# =============================================================================

type Coordinate = tuple[float, float, float]
"""3D coordinate as (x, y, z) tuple."""

type BoundingBoxTuple = tuple[Coordinate, Coordinate]
"""Bounding box as (min_corner, max_corner) coordinates."""
