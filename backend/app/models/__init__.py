"""
SQLAlchemy ORM Models for AI Part Designer

This module exports all database models for the application.
Models follow the schema defined in docs/database-schema.md
"""

from app.models.base import Base, TimestampMixin, SoftDeleteMixin
from app.models.user import User, UserSettings, Subscription
from app.models.project import Project
from app.models.template import Template
from app.models.design import Design, DesignVersion, DesignShare
from app.models.job import Job
from app.models.file import File
from app.models.moderation import ModerationLog
from app.models.api_key import APIKey
from app.models.audit import AuditLog
from app.models.assembly import (
    Assembly,
    AssemblyComponent,
    ComponentRelationship,
    Vendor,
    BOMItem,
)
from app.models.reference_component import (
    ReferenceComponent,
    ComponentLibrary,
    ComponentExtractionJob,
    UserComponent,
)
from app.models.spatial_layout import (
    SpatialLayout,
    ComponentPlacement,
)
from app.models.conversation import (
    Conversation,
    ConversationMessage,
    ConversationStatus,
    MessageRole,
    MessageType,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    # User domain
    "User",
    "UserSettings",
    "Subscription",
    # Project domain
    "Project",
    # Template domain
    "Template",
    # Design domain
    "Design",
    "DesignVersion",
    "DesignShare",
    # Job domain
    "Job",
    # File domain
    "File",
    # Assembly domain
    "Assembly",
    "AssemblyComponent",
    "ComponentRelationship",
    "Vendor",
    "BOMItem",
    # Reference Component domain
    "ReferenceComponent",
    "ComponentLibrary",
    "ComponentExtractionJob",
    "UserComponent",
    # Spatial Layout domain
    "SpatialLayout",
    "ComponentPlacement",
    # Moderation
    "ModerationLog",
    # API
    "APIKey",
    # Audit
    "AuditLog",
    # Conversation
    "Conversation",
    "ConversationMessage",
    "ConversationStatus",
    "MessageRole",
    "MessageType",
]
