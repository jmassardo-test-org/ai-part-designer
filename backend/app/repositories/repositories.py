"""
Domain-specific repositories.

Each repository extends BaseRepository with domain-specific
query methods and business logic.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload

from app.models import (
    AuditLog,
    Design,
    Job,
    Project,
    Template,
    User,
)
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""

    model = User

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        query = select(User).where(User.email == email).where(User.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_with_settings(self, user_id: UUID) -> User | None:
        """Get user with settings eagerly loaded."""
        query = (
            select(User)
            .where(User.id == user_id)
            .where(User.deleted_at.is_(None))
            .options(selectinload(User.settings))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_users_count(self) -> int:
        """Count active, verified users."""
        query = (
            select(func.count())
            .select_from(User)
            .where(User.is_active.is_(True))
            .where(User.is_verified.is_(True))
            .where(User.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_users_by_tier(self, tier: str) -> Sequence[User]:
        """Get all users with a specific subscription tier."""
        query = (
            select(User)
            .where(User.tier == tier)
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalars().all()


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project operations."""

    model = Project

    async def get_user_projects(
        self,
        user_id: UUID,
        *,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Project]:
        """Get all projects for a user."""
        query = (
            select(Project).where(Project.user_id == user_id).where(Project.deleted_at.is_(None))
        )

        if not include_archived:
            query = query.where(Project.is_archived.is_(False))

        query = query.order_by(desc(Project.updated_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_with_designs(self, project_id: UUID) -> Project | None:
        """Get project with designs eagerly loaded."""
        query = (
            select(Project)
            .where(Project.id == project_id)
            .where(Project.deleted_at.is_(None))
            .options(selectinload(Project.designs))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class TemplateRepository(BaseRepository[Template]):
    """Repository for Template operations."""

    model = Template

    async def get_by_slug(self, slug: str) -> Template | None:
        """Get template by slug."""
        query = select(Template).where(Template.slug == slug).where(Template.is_active.is_(True))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_category(
        self,
        category: str,
        *,
        tier: str | None = None,
        limit: int = 50,
    ) -> Sequence[Template]:
        """Get templates by category, optionally filtered by tier."""
        query = (
            select(Template)
            .where(Template.category == category)
            .where(Template.is_active.is_(True))
        )

        if tier:
            # Filter to templates accessible by this tier
            tier_order = {"free": 0, "hobby": 1, "pro": 2, "enterprise": 3}
            accessible_tiers = [t for t, v in tier_order.items() if v <= tier_order.get(tier, 0)]
            query = query.where(Template.min_tier.in_(accessible_tiers))

        query = query.order_by(desc(Template.use_count)).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_featured(self, limit: int = 10) -> Sequence[Template]:
        """Get featured templates."""
        query = (
            select(Template)
            .where(Template.is_featured.is_(True))
            .where(Template.is_active.is_(True))
            .order_by(desc(Template.use_count))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def increment_use_count(self, template_id: UUID) -> None:
        """Increment the use count for a template."""
        template = await self.get_by_id(template_id)
        if template:
            template.use_count += 1
            await self.session.flush()


class DesignRepository(BaseRepository[Design]):
    """Repository for Design operations."""

    model = Design

    async def get_project_designs(
        self,
        project_id: UUID,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Design]:
        """Get all designs in a project."""
        query = (
            select(Design).where(Design.project_id == project_id).where(Design.deleted_at.is_(None))
        )

        if status:
            query = query.where(Design.status == status)

        query = query.order_by(desc(Design.updated_at)).offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_public_designs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Design]:
        """Get public designs for gallery."""
        query = (
            select(Design)
            .where(Design.is_public.is_(True))
            .where(Design.status == "ready")
            .where(Design.deleted_at.is_(None))
            .order_by(desc(Design.view_count))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_with_versions(self, design_id: UUID) -> Design | None:
        """Get design with all versions."""
        query = (
            select(Design)
            .where(Design.id == design_id)
            .where(Design.deleted_at.is_(None))
            .options(selectinload(Design.versions))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def increment_view_count(self, design_id: UUID) -> None:
        """Increment view count for a design."""
        design = await self.get_by_id(design_id)
        if design:
            design.view_count += 1
            await self.session.flush()

    async def search_designs(
        self,
        search_term: str,
        *,
        public_only: bool = True,
        limit: int = 20,
    ) -> Sequence[Design]:
        """Full-text search on designs."""
        # Use PostgreSQL full-text search if search_vector exists

        query = select(Design).where(Design.deleted_at.is_(None))

        if public_only:
            query = query.where(Design.is_public.is_(True))

        # Search in name and description
        query = query.where(
            Design.name.ilike(f"%{search_term}%") | Design.description.ilike(f"%{search_term}%")
        )

        query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()


class JobRepository(BaseRepository[Job]):
    """Repository for Job operations."""

    model = Job

    async def get_user_jobs(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> Sequence[Job]:
        """Get jobs for a user."""
        query = select(Job).where(Job.user_id == user_id)

        if status:
            query = query.where(Job.status == status)

        query = query.order_by(desc(Job.created_at)).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_pending_jobs(self, limit: int = 100) -> Sequence[Job]:
        """Get pending jobs ordered by priority."""
        query = (
            select(Job)
            .where(Job.status.in_(["pending", "queued"]))
            .order_by(Job.priority.asc(), Job.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_running_jobs_count(self) -> int:
        """Count currently running jobs."""
        query = select(func.count()).select_from(Job).where(Job.status == "running")
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_stale_jobs(self, stale_after_minutes: int = 30) -> Sequence[Job]:
        """Get jobs that have been running too long."""
        threshold = datetime.now(tz=UTC) - timedelta(minutes=stale_after_minutes)
        query = select(Job).where(Job.status == "running").where(Job.started_at < threshold)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_job_stats(self, since: datetime | None = None) -> dict[str, Any]:
        """Get job statistics."""
        base_query = select(Job)

        if since:
            base_query = base_query.where(Job.created_at >= since)

        # Count by status
        status_query = select(Job.status, func.count().label("count")).group_by(Job.status)
        if since:
            status_query = status_query.where(Job.created_at >= since)

        status_result = await self.session.execute(status_query)
        status_counts = {row.status: row.count for row in status_result}

        # Average execution time
        avg_time_query = select(func.avg(Job.execution_time_ms)).where(Job.status == "completed")
        if since:
            avg_time_query = avg_time_query.where(Job.created_at >= since)

        avg_result = await self.session.execute(avg_time_query)
        avg_execution_time = avg_result.scalar()

        return {
            "status_counts": status_counts,
            "avg_execution_time_ms": avg_execution_time,
            "total_jobs": sum(status_counts.values()),
        }


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog operations."""

    model = AuditLog

    async def log_action(
        self,
        action: str,
        resource_type: str,
        *,
        resource_id: UUID | None = None,
        user_id: UUID | None = None,
        actor_type: str = "user",
        context: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        return await self.create(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            actor_type=actor_type,
            context=context or {},
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
        )

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: UUID,
        *,
        limit: int = 100,
    ) -> Sequence[AuditLog]:
        """Get audit history for a specific resource."""
        query = (
            select(AuditLog)
            .where(AuditLog.resource_type == resource_type)
            .where(AuditLog.resource_id == resource_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_activity(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> Sequence[AuditLog]:
        """Get audit history for a user."""
        query = select(AuditLog).where(AuditLog.user_id == user_id)

        if since:
            query = query.where(AuditLog.created_at >= since)

        query = query.order_by(desc(AuditLog.created_at)).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()
