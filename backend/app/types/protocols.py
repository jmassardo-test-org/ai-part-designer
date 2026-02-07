"""
Type protocols for generic typing patterns.

These protocols enable proper type checking for generic
repository and service patterns by expressing the requirements
for TypeVars.

Example:
    from app.types.protocols import StandardEntity

    ModelType = TypeVar("ModelType", bound=StandardEntity)

    class BaseRepository(Generic[ModelType]):
        model: type[ModelType]

        async def get_by_id(self, id: UUID) -> ModelType | None:
            # Now mypy knows self.model has .id, .deleted_at, etc.
            query = select(self.model).where(self.model.id == id)
            ...
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Mapped


@runtime_checkable
class HasIdentity(Protocol):
    """
    Protocol for entities with UUID primary key.

    Models implementing this protocol have a unique identifier
    that can be used for lookups and references.
    """

    id: "Mapped[UUID]"


@runtime_checkable
class HasTimestamps(Protocol):
    """
    Protocol for entities with audit timestamps.

    Models implementing this protocol track when they were
    created and last updated.
    """

    created_at: "Mapped[datetime]"
    updated_at: "Mapped[datetime]"


@runtime_checkable
class HasSoftDelete(Protocol):
    """
    Protocol for entities with soft-delete support.

    Models implementing this protocol can be logically deleted
    without being removed from the database.
    """

    deleted_at: "Mapped[datetime | None]"

    @property
    def is_deleted(self) -> bool:
        """Check if the record has been soft deleted."""
        ...


@runtime_checkable
class StandardEntity(HasIdentity, HasTimestamps, HasSoftDelete, Protocol):
    """
    Combined protocol for standard entity with all mixins.

    This is the most common protocol for ORM models that include:
    - UUID primary key (id)
    - Audit timestamps (created_at, updated_at)
    - Soft delete support (deleted_at, is_deleted)

    Use this as a bound for TypeVars in generic repositories:

        ModelType = TypeVar("ModelType", bound=StandardEntity)
    """


class Identifiable(Protocol):
    """
    Protocol for any object with an id attribute.

    Unlike HasIdentity, this does not require SQLAlchemy Mapped type,
    making it suitable for Pydantic schemas and other non-ORM objects.
    """

    @property
    def id(self) -> UUID:
        """Unique identifier for the object."""
        ...


class Nameable(Protocol):
    """
    Protocol for objects with name/display attributes.

    Useful for generic functions that display or sort by name.
    """

    @property
    def name(self) -> str:
        """Display name of the object."""
        ...


class Ownable(Protocol):
    """
    Protocol for objects with user ownership.

    Models implementing this protocol track which user
    owns or created the object.
    """

    @property
    def user_id(self) -> UUID:
        """ID of the owning user."""
        ...
