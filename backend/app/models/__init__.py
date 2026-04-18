"""
SQLAlchemy ORM Models for AI Part Designer

This module exports all database models for the application.
Models follow the schema defined in docs/database-schema.md
"""

from app.models.annotation import (
    AnnotationStatus,
    AnnotationType,
    DesignAnnotation,
)
from app.models.api_key import APIKey
from app.models.assembly import (
    Assembly,
    AssemblyComponent,
    BOMItem,
    ComponentRelationship,
    Vendor,
)
from app.models.audit import AuditLog
from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.content import ContentCategory, ContentItem, ContentStatus, ContentType
from app.models.conversation import (
    Conversation,
    ConversationMessage,
    ConversationStatus,
    MessageRole,
    MessageType,
)
from app.models.coupon import (
    Coupon,
    CouponRedemption,
    CouponType,
)
from app.models.design import Design, DesignShare, DesignVersion
from app.models.design_context import (
    DesignContext,
    DesignRefinementJob,
)
from app.models.file import File
from app.models.job import Job
from app.models.marketplace import (
    DesignList,
    DesignListItem,
    DesignSave,
)
from app.models.moderation import ModerationLog
from app.models.notification import (
    DEFAULT_PREFERENCES,
    Notification,
    NotificationPreference,
    NotificationPriority,
    NotificationType,
)
from app.models.oauth import OAuthConnection
from app.models.organization import (
    InviteStatus,
    Organization,
    OrganizationAuditLog,
    OrganizationCreditBalance,
    OrganizationInvite,
    OrganizationMember,
    OrganizationRole,
)
from app.models.payment import (
    PaymentHistory,
    PaymentStatus,
    PaymentType,
)
from app.models.project import Project
from app.models.rating import (
    ContentReport,
    DesignComment,
    DesignRating,
    FeedbackType,
    LicenseViolationType,
    ReportReason,
    ReportStatus,
    ReportTargetType,
    TemplateComment,
    TemplateFeedback,
    TemplateRating,
    UserBan,
)
from app.models.reference_component import (
    ComponentExtractionJob,
    ComponentLibrary,
    ReferenceComponent,
    UserComponent,
)
from app.models.spatial_layout import (
    ComponentPlacement,
    SpatialLayout,
)
from app.models.subscription import (
    OPERATION_COSTS,
    CreditBalance,
    CreditTransaction,
    SubscriptionTier,
    TierSlug,
    TransactionType,
    UsageQuota,
    get_operation_cost,
)
from app.models.team import (
    ProjectTeam,
    Team,
    TeamMember,
    TeamRole,
)
from app.models.template import Template
from app.models.user import Subscription, User, UserSettings

__all__ = [
    "DEFAULT_PREFERENCES",
    "OPERATION_COSTS",
    # API
    "APIKey",
    "AnnotationStatus",
    "AnnotationType",
    # Assembly domain
    "Assembly",
    "AssemblyComponent",
    # Audit
    "AuditLog",
    "BOMItem",
    # Base
    "Base",
    "ComponentExtractionJob",
    "ComponentLibrary",
    "ComponentPlacement",
    "ComponentRelationship",
    "ContentCategory",
    "ContentItem",
    "ContentReport",
    "ContentStatus",
    "ContentType",
    # Conversation
    "Conversation",
    # Coupon
    "Coupon",
    "CouponRedemption",
    "CouponType",
    "ConversationMessage",
    "ConversationStatus",
    "CreditBalance",
    "CreditTransaction",
    # Design domain
    "Design",
    # Annotations
    "DesignAnnotation",
    # Design Comments
    "DesignComment",
    # Design Context
    "DesignContext",
    # Marketplace
    "DesignList",
    "DesignListItem",
    # Design Ratings
    "DesignRating",
    "DesignRefinementJob",
    "DesignSave",
    "DesignShare",
    "DesignVersion",
    "FeedbackType",
    # File domain
    "File",
    "InviteStatus",
    # Job domain
    "Job",
    "LicenseViolationType",
    "MessageRole",
    "MessageType",
    # Moderation
    "ModerationLog",
    # Notifications
    "Notification",
    "NotificationPreference",
    "NotificationPriority",
    "NotificationType",
    # OAuth
    "OAuthConnection",
    # Organization
    "Organization",
    "OrganizationAuditLog",
    "OrganizationCreditBalance",
    "OrganizationInvite",
    "OrganizationMember",
    "OrganizationRole",
    # Payment
    "PaymentHistory",
    "PaymentStatus",
    "PaymentType",
    # Project domain
    "Project",
    "ProjectTeam",
    # Reference Component domain
    "ReferenceComponent",
    "ReportReason",
    "ReportStatus",
    "ReportTargetType",
    "SoftDeleteMixin",
    # Spatial Layout domain
    "SpatialLayout",
    "Subscription",
    # Subscription & Credits
    "SubscriptionTier",
    # Teams
    "Team",
    "TeamMember",
    "TeamRole",
    # Template domain
    "Template",
    "TemplateComment",
    "TemplateFeedback",
    # Ratings & Community
    "TemplateRating",
    "TierSlug",
    "TimestampMixin",
    "TransactionType",
    "UsageQuota",
    # User domain
    "User",
    "UserBan",
    "UserComponent",
    "UserSettings",
    "Vendor",
    "get_operation_cost",
]
