"""
Base repository pattern for data access.

Provides generic CRUD operations with proper async handling,
pagination, and filtering support.
"""

from typing import Any, Generic, TypeVar, Sequence
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.
    
    All repositories should inherit from this class
    and specify their model type.
    
    Example:
        class UserRepository(BaseRepository[User]):
            model = User
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self,
        id: UUID,
        *,
        include_deleted: bool = False,
        load_relations: list[str] | None = None,
    ) -> ModelType | None:
        """
        Get a single record by ID.
        
        Args:
            id: Record UUID
            include_deleted: Include soft-deleted records
            load_relations: List of relationship names to eager load
        """
        query = select(self.model).where(self.model.id == id)
        
        # Handle soft deletes
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        
        # Eager load relationships
        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_many(
        self,
        *,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        order_desc: bool = True,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        load_relations: list[str] | None = None,
    ) -> Sequence[ModelType]:
        """
        Get multiple records with filtering and pagination.
        
        Args:
            filters: Dict of field=value filters
            order_by: Field name to order by
            order_desc: Order descending if True
            offset: Number of records to skip
            limit: Maximum records to return
            include_deleted: Include soft-deleted records
            load_relations: Relationship names to eager load
        """
        query = select(self.model)
        
        # Apply filters
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    if isinstance(value, list):
                        conditions.append(column.in_(value))
                    else:
                        conditions.append(column == value)
            if conditions:
                query = query.where(and_(*conditions))
        
        # Handle soft deletes
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        
        # Ordering
        if order_by and hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            query = query.order_by(order_column.desc() if order_desc else order_column.asc())
        elif hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())
        
        # Pagination
        query = query.offset(offset).limit(limit)
        
        # Eager load relationships
        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(
        self,
        *,
        filters: dict[str, Any] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count records matching filters."""
        query = select(func.count()).select_from(self.model)
        
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    if isinstance(value, list):
                        conditions.append(column.in_(value))
                    else:
                        conditions.append(column == value)
            if conditions:
                query = query.where(and_(*conditions))
        
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(
        self,
        id: UUID,
        **kwargs,
    ) -> ModelType | None:
        """Update an existing record."""
        instance = await self.get_by_id(id)
        if not instance:
            return None
        
        for field, value in kwargs.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(
        self,
        id: UUID,
        *,
        soft: bool = True,
    ) -> bool:
        """
        Delete a record.
        
        Args:
            id: Record UUID
            soft: Use soft delete if True and model supports it
        """
        instance = await self.get_by_id(id)
        if not instance:
            return False
        
        if soft and hasattr(instance, "deleted_at"):
            from datetime import datetime
            instance.deleted_at = datetime.utcnow()
        else:
            await self.session.delete(instance)
        
        await self.session.flush()
        return True

    async def exists(
        self,
        id: UUID,
        *,
        include_deleted: bool = False,
    ) -> bool:
        """Check if a record exists."""
        query = select(func.count()).select_from(self.model).where(self.model.id == id)
        
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        
        result = await self.session.execute(query)
        return (result.scalar() or 0) > 0

    async def bulk_create(self, items: list[dict]) -> list[ModelType]:
        """Create multiple records at once."""
        instances = [self.model(**item) for item in items]
        self.session.add_all(instances)
        await self.session.flush()
        return instances

    async def search(
        self,
        search_term: str,
        search_fields: list[str],
        *,
        limit: int = 20,
    ) -> Sequence[ModelType]:
        """
        Search records by text fields.
        
        Uses ILIKE for case-insensitive matching.
        """
        query = select(self.model)
        
        conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                column = getattr(self.model, field)
                conditions.append(column.ilike(f"%{search_term}%"))
        
        if conditions:
            query = query.where(or_(*conditions))
        
        if hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        
        query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
