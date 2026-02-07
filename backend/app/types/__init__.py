"""
Type definitions for AI Part Designer.

This module provides reusable type definitions including:
- Protocol types for generic patterns
- Type aliases for common types
- TypedDict definitions for structured data

Usage:
    from app.types import StandardEntity, SQLFilter, EntityID
"""

from app.types.aliases import (
    AsyncDB,
    BoundingBoxTuple,
    Coordinate,
    DesignID,
    EntityID,
    JSONDict,
    JSONList,
    JSONPrimitive,
    JSONValue,
    Limit,
    Offset,
    PageNumber,
    PageSize,
    ProjectID,
    SQLFilter,
    SQLFilters,
    UserID,
)
from app.types.protocols import (
    HasIdentity,
    HasSoftDelete,
    HasTimestamps,
    Identifiable,
    Nameable,
    Ownable,
    StandardEntity,
)

__all__ = [
    # Aliases
    "AsyncDB",
    "BoundingBoxTuple",
    "Coordinate",
    "DesignID",
    "EntityID",
    # Protocols
    "HasIdentity",
    "HasSoftDelete",
    "HasTimestamps",
    "Identifiable",
    "JSONDict",
    "JSONList",
    "JSONPrimitive",
    "JSONValue",
    "Limit",
    "Nameable",
    "Offset",
    "Ownable",
    "PageNumber",
    "PageSize",
    "ProjectID",
    "SQLFilter",
    "SQLFilters",
    "StandardEntity",
    "UserID",
]
