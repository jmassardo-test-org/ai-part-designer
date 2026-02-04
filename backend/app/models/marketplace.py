"""
Marketplace domain models: DesignList, DesignListItem, DesignSave.

Enables the community marketplace where users can browse public designs,
save them to organized lists, and track popularity.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.design import Design
    from app.models.user import User


class DesignList(Base, TimestampMixin, SoftDeleteMixin):
    """
    User-created list for organizing saved designs.
    
    Examples: "Electronics enclosures", "Favorites", "Project A components"
    """
    __tablename__ = "design_lists"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # List metadata
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    icon: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="folder",
    )  # emoji or icon name
    color: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="#6366f1",
    )  # hex color
    
    # Visibility
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    
    # Ordering
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="design_lists",
    )
    items: Mapped[list["DesignListItem"]] = relationship(
        "DesignListItem",
        back_populates="list",
        cascade="all, delete-orphan",
        order_by="DesignListItem.position",
    )
    
    @property
    def item_count(self) -> int:
        """Get number of items in list."""
        return len(self.items)

    def __repr__(self) -> str:
        return f"<DesignList {self.name} (user={self.user_id})>"


class DesignListItem(Base, TimestampMixin):
    """
    A design saved to a list.
    """
    __tablename__ = "design_list_items"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    list_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("design_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    design_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # User note for this saved design
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Position in list
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Relationships
    list: Mapped["DesignList"] = relationship(
        "DesignList",
        back_populates="items",
    )
    design: Mapped["Design"] = relationship(
        "Design",
        lazy="joined",
    )
    
    __table_args__ = (
        # Prevent duplicate saves to same list
        UniqueConstraint("list_id", "design_id", name="uq_list_design"),
        Index("idx_list_items_list_id", "list_id"),
        Index("idx_list_items_design_id", "design_id"),
    )

    def __repr__(self) -> str:
        return f"<DesignListItem list={self.list_id} design={self.design_id}>"


class DesignSave(Base, TimestampMixin):
    """
    Track when a user saves someone else's design.
    
    This is separate from list items - it tracks the "save" action itself.
    A design can be saved to multiple lists.
    Used for popularity metrics and "saved" state.
    """
    __tablename__ = "design_saves"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    design_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    design: Mapped["Design"] = relationship(
        "Design",
        back_populates="saves",
    )
    
    __table_args__ = (
        UniqueConstraint("user_id", "design_id", name="uq_user_design_save"),
        Index("idx_design_saves_design", "design_id"),
        Index("idx_design_saves_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<DesignSave user={self.user_id} design={self.design_id}>"
