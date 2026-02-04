"""
SQLAlchemy ORM Models for AI Part Designer

This module exports all database models for the application.
Models follow the schema defined in docs/database-schema.md
"""

from app.models.base import Base, TimestampMixin, SoftDeleteMixin
from app.models.user import User, UserSettings, Subscription
from app.models.subscription import (
    SubscriptionTier,
    CreditBalance,
    CreditTransaction,
    UsageQuota,
    TransactionType,
    TierSlug,
    OPERATION_COSTS,
    get_operation_cost,
)
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
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrganizationInvite,
    OrganizationCreditBalance,
    OrganizationAuditLog,
    OrganizationRole,
    InviteStatus,
)
from app.models.annotation import (
    DesignAnnotation,
    AnnotationType,
    AnnotationStatus,
)
from app.models.notification import (
    Notification,
    NotificationPreference,
    NotificationType,
    NotificationPriority,
    DEFAULT_PREFERENCES,
)
from app.models.design_context import (
    DesignContext,
    DesignRefinementJob,
)
from app.models.payment import (
    PaymentHistory,
    PaymentStatus,
    PaymentType,
)
from app.models.oauth import OAuthConnection
from app.models.team import (
    Team,
    TeamMember,
    TeamRole,
    ProjectTeam,
)
from app.models.rating import (
    TemplateRating,
    TemplateFeedback,
    TemplateComment,
    ContentReport,
    UserBan,
    FeedbackType,
    ReportReason,
    ReportStatus,
    ReportTargetType,
)
from app.models.marketplace import (
    DesignList,
    DesignListItem,
    DesignSave,
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
    # Subscription & Credits
    "SubscriptionTier",
    "CreditBalance",
    "CreditTransaction",
    "UsageQuota",
    "TransactionType",
    "TierSlug",
    "OPERATION_COSTS",
    "get_operation_cost",
    # Organization
    "Organization",
    "OrganizationMember",
    "OrganizationInvite",
    "OrganizationCreditBalance",
    "OrganizationAuditLog",
    "OrganizationRole",
    "InviteStatus",
    # Annotations
    "DesignAnnotation",
    "AnnotationType",
    "AnnotationStatus",
    # Notifications
    "Notification",
    "NotificationPreference",
    "NotificationType",
    "NotificationPriority",
    "DEFAULT_PREFERENCES",
    # Design Context
    "DesignContext",
    "DesignRefinementJob",
    # Payment
    "PaymentHistory",
    "PaymentStatus",
    "PaymentType",
    # OAuth
    "OAuthConnection",
    # Teams
    "Team",
    "TeamMember",
    "TeamRole",
    "ProjectTeam",
    # Ratings & Community
    "TemplateRating",
    "TemplateFeedback",
    "TemplateComment",
    "ContentReport",
    "UserBan",
    "FeedbackType",
    "ReportReason",
    "ReportStatus",
    "ReportTargetType",
    # Marketplace
    "DesignList",
    "DesignListItem",
    "DesignSave",
]
