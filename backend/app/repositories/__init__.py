"""
Repository package for data access layer.

Provides domain-specific repositories following the repository pattern
for clean separation of data access from business logic.
"""

from app.repositories.base import BaseRepository
from app.repositories.repositories import (
    UserRepository,
    ProjectRepository,
    TemplateRepository,
    DesignRepository,
    JobRepository,
    AuditLogRepository,
)

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ProjectRepository",
    "TemplateRepository",
    "DesignRepository",
    "JobRepository",
    "AuditLogRepository",
]
