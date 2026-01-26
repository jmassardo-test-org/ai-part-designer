"""
Services package.
"""

from app.services.email import (
    EmailService,
    EmailMessage,
    EmailTemplate,
    get_email_service,
)
from app.services.security_audit import (
    SecurityAuditService,
    SecurityEventType,
    SecuritySeverity,
    get_security_audit_service,
)
from app.services.component_storage import component_file_storage
from app.services.datasheet_parser import datasheet_parser
from app.services.cad_extractor import cad_extractor
from app.services.abuse_detection import (
    AbuseDetectionService,
    ViolationType,
    ViolationEvent,
    BanDuration,
)
from app.services.content_moderation import (
    ContentModerationService,
    content_moderation,
    ModerationDecision,
    ProhibitedCategory,
)
from app.services.integrity import (
    DataIntegrityService,
    IntegrityCheckType,
    IntegritySeverity,
    IntegrityIssue,
    IntegrityReport,
    run_integrity_check,
)

__all__ = [
    # Email
    "EmailService",
    "EmailMessage",
    "EmailTemplate",
    "get_email_service",
    # Security Audit
    "SecurityAuditService",
    "SecurityEventType",
    "SecuritySeverity",
    "get_security_audit_service",
    # Component Services
    "component_file_storage",
    "datasheet_parser",
    "cad_extractor",
    # Abuse Detection
    "AbuseDetectionService",
    "ViolationType",
    "ViolationEvent",
    "BanDuration",
    # Content Moderation
    "ContentModerationService",
    "content_moderation",
    "ModerationDecision",
    "ProhibitedCategory",
    # Data Integrity
    "DataIntegrityService",
    "IntegrityCheckType",
    "IntegritySeverity",
    "IntegrityIssue",
    "IntegrityReport",
    "run_integrity_check",
]
