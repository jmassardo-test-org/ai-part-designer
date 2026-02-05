"""
Test factories for creating model instances.

Provides factory functions and classes for easily creating test data
with sensible defaults while allowing customization.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID, uuid4

from app.core.security import hash_password

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Counter for unique values
# =============================================================================


class Counter:
    """Simple counter for generating unique sequences."""

    _counters: ClassVar[dict[str, int]] = {}

    @classmethod
    def next(cls, name: str) -> int:
        """Get next value for named counter."""
        cls._counters[name] = cls._counters.get(name, 0) + 1
        return cls._counters[name]

    @classmethod
    def reset(cls) -> None:
        """Reset all counters."""
        cls._counters.clear()


# =============================================================================
# User Factory
# =============================================================================


class UserFactory:
    """Factory for creating User instances."""

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        email: str | None = None,
        password: str = "TestPassword123!",
        display_name: str | None = None,
        role: str = "user",
        status: str = "active",
        is_verified: bool = True,
        **kwargs: Any,
    ) -> User:
        """Create and persist a User instance."""
        from app.models.user import User

        n = Counter.next("user")

        user = User(
            id=kwargs.get("id", uuid4()),
            email=email or f"user{n}@test.com",
            password_hash=hash_password(password),
            display_name=display_name or f"Test User {n}",
            role=role,
            status=status,
            email_verified_at=datetime.now(UTC) if is_verified else None,
            **{k: v for k, v in kwargs.items() if k != "id"},
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def create_admin(
        db: AsyncSession,
        **kwargs: Any,
    ) -> User:
        """Create an admin user."""
        return await UserFactory.create(
            db,
            role="admin",
            email=kwargs.pop("email", None) or f"admin{Counter.next('admin')}@test.com",
            display_name=kwargs.pop("display_name", None) or "Admin User",
            **kwargs,
        )

    @staticmethod
    async def create_batch(
        db: AsyncSession,
        count: int,
        **kwargs: Any,
    ) -> list[User]:
        """Create multiple users."""
        return [await UserFactory.create(db, **kwargs) for _ in range(count)]


# =============================================================================
# Project Factory
# =============================================================================


class ProjectFactory:
    """Factory for creating Project instances."""

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        user: User | None = None,
        user_id: UUID | None = None,
        name: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> Project:
        """Create and persist a Project instance."""
        from app.models.project import Project

        # Create user if not provided
        if user is None and user_id is None:
            user = await UserFactory.create(db)
            user_id = user.id
        elif user is not None:
            user_id = user.id

        n = Counter.next("project")

        project = Project(
            id=kwargs.get("id", uuid4()),
            user_id=user_id,
            name=name or f"Test Project {n}",
            description=description,
            **{k: v for k, v in kwargs.items() if k != "id"},
        )

        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project


# =============================================================================
# Design Factory
# =============================================================================


class DesignFactory:
    """Factory for creating Design instances."""

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        project: Project | None = None,
        project_id: UUID | None = None,
        user: User | None = None,
        user_id: UUID | None = None,
        name: str | None = None,
        description: str | None = None,
        source_type: str = "ai_generated",
        status: str = "ready",
        extra_data: dict | None = None,
        **kwargs: Any,
    ) -> Design:
        """Create and persist a Design instance."""
        from app.models.design import Design

        # Create project if not provided
        if project is None and project_id is None:
            project = await ProjectFactory.create(db)
            project_id = project.id
        elif project is not None:
            project_id = project.id

        # Get user_id from project if not provided
        if user_id is None and user is not None:
            user_id = user.id
        elif user_id is None and project is not None:
            user_id = project.user_id

        n = Counter.next("design")

        design = Design(
            id=kwargs.get("id", uuid4()),
            project_id=project_id,
            user_id=user_id,
            name=name or f"Test Design {n}",
            description=description or f"Test design description {n}",
            source_type=source_type,
            status=status,
            extra_data=extra_data
            or {
                "dimensions": {"x": 100, "y": 50, "z": 25},
                "volume": 125000,
            },
            **{k: v for k, v in kwargs.items() if k != "id"},
        )

        db.add(design)
        await db.commit()
        await db.refresh(design)
        return design


# =============================================================================
# Job Factory
# =============================================================================


class JobFactory:
    """Factory for creating Job instances."""

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        user: User | None = None,
        user_id: UUID | None = None,
        design_id: UUID | None = None,
        job_type: str = "ai_generation",
        status: str = "pending",
        priority: int = 5,
        progress: int = 0,
        input_params: dict | None = None,
        result: dict | None = None,
        error: dict | None = None,
        **kwargs: Any,
    ) -> Job:
        """Create and persist a Job instance."""
        from app.models.job import Job

        # Create user if not provided
        if user is None and user_id is None:
            user = await UserFactory.create(db)
            user_id = user.id
        elif user is not None:
            user_id = user.id

        job = Job(
            id=kwargs.get("id", uuid4()),
            user_id=user_id,
            design_id=design_id,
            job_type=job_type,
            status=status,
            priority=priority,
            progress=progress,
            input_params=input_params or {"description": "test"},
            result=result,
            error=error,
            **{k: v for k, v in kwargs.items() if k != "id"},
        )

        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def create_completed(
        db: AsyncSession,
        **kwargs: Any,
    ) -> Job:
        """Create a completed job with results."""
        return await JobFactory.create(
            db,
            status="completed",
            progress=100,
            result=kwargs.pop("result", None)
            or {
                "file_url": "https://storage.test/output.step",
                "thumbnail_url": "https://storage.test/thumb.png",
            },
            **kwargs,
        )

    @staticmethod
    async def create_failed(
        db: AsyncSession,
        **kwargs: Any,
    ) -> Job:
        """Create a failed job with error."""
        return await JobFactory.create(
            db,
            status="failed",
            error=kwargs.pop("error", None)
            or {
                "code": "GENERATION_FAILED",
                "message": "Test failure",
            },
            error_message=kwargs.pop("error_message", "Test failure message"),
            **kwargs,
        )


# =============================================================================
# File Factory
# =============================================================================


class FileFactory:
    """Factory for creating File instances."""

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        user: User | None = None,
        user_id: UUID | None = None,
        filename: str | None = None,
        original_filename: str | None = None,
        mime_type: str = "application/step",
        size_bytes: int = 1024,
        file_type: str = "cad",
        cad_format: str | None = "step",
        status: str = "ready",
        **kwargs: Any,
    ) -> File:
        """Create and persist a File instance."""
        from app.models.file import File

        # Create user if not provided
        if user is None and user_id is None:
            user = await UserFactory.create(db)
            user_id = user.id
        elif user is not None:
            user_id = user.id

        n = Counter.next("file")

        file = File(
            id=kwargs.get("id", uuid4()),
            user_id=user_id,
            filename=filename or f"test_file_{n}.step",
            original_filename=original_filename or f"Original File {n}.step",
            mime_type=mime_type,
            size_bytes=size_bytes,
            storage_bucket="uploads",
            storage_path=f"users/{user_id}/files/{uuid4()}.step",
            file_type=file_type,
            cad_format=cad_format,
            status=status,
            **{k: v for k, v in kwargs.items() if k != "id"},
        )

        db.add(file)
        await db.commit()
        await db.refresh(file)
        return file

    @staticmethod
    async def create_stl(
        db: AsyncSession,
        **kwargs: Any,
    ) -> File:
        """Create an STL file."""
        return await FileFactory.create(
            db,
            mime_type="application/sla",
            cad_format="stl",
            filename=f"test_{Counter.next('stl')}.stl",
            **kwargs,
        )


# =============================================================================
# Template Factory
# =============================================================================


class TemplateFactory:
    """Factory for creating Template instances."""

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        name: str | None = None,
        slug: str | None = None,
        category: str = "mechanical",
        subcategory: str | None = None,
        description: str | None = None,
        parameters: dict | None = None,
        default_values: dict | None = None,
        cadquery_script: str = "# placeholder script",
        tags: list[str] | None = None,
        min_tier: str = "free",
        is_featured: bool = False,
        is_active: bool = True,
        **kwargs: Any,
    ) -> Template:
        """Create and persist a Template instance."""
        from app.models.template import Template

        n = Counter.next("template")

        template = Template(
            id=kwargs.get("id", uuid4()),
            name=name or f"Test Template {n}",
            slug=slug or f"test-template-{n}",
            category=category,
            subcategory=subcategory,
            description=description or f"Test template description {n}",
            parameters=parameters
            or {
                "length": {
                    "type": "number",
                    "min": 1,
                    "max": 1000,
                    "default": 100,
                    "unit": "mm",
                    "label": "Length",
                },
                "width": {
                    "type": "number",
                    "min": 1,
                    "max": 500,
                    "default": 50,
                    "unit": "mm",
                    "label": "Width",
                },
            },
            default_values=default_values or {"length": 100, "width": 50},
            cadquery_script=cadquery_script,
            tags=tags or [],
            min_tier=min_tier,
            is_featured=is_featured,
            is_active=is_active,
            **{k: v for k, v in kwargs.items() if k != "id"},
        )

        db.add(template)
        await db.commit()
        await db.refresh(template)
        return template

    @staticmethod
    async def create_batch(
        db: AsyncSession,
        count: int,
        **kwargs: Any,
    ) -> list[Template]:
        """Create multiple templates."""
        return [await TemplateFactory.create(db, **kwargs) for _ in range(count)]


# =============================================================================
# DesignVersion Factory
# =============================================================================


class DesignVersionFactory:
    """Factory for creating DesignVersion instances."""

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        design: Design | None = None,
        design_id: UUID | None = None,
        version_number: int = 1,
        file_url: str | None = None,
        change_description: str | None = None,
        geometry_info: dict | None = None,
        parameters: dict | None = None,
        file_formats: dict | None = None,
        **kwargs: Any,
    ) -> DesignVersion:
        """Create and persist a DesignVersion instance."""
        from app.models.design import DesignVersion

        # Create design if not provided
        if design is None and design_id is None:
            design = await DesignFactory.create(db)
            design_id = design.id
        elif design is not None:
            design_id = design.id

        version = DesignVersion(
            id=kwargs.get("id", uuid4()),
            design_id=design_id,
            version_number=version_number,
            file_url=file_url or f"s3://designs/{design_id}/v{version_number}/model.step",
            change_description=change_description or f"Version {version_number}",
            geometry_info=geometry_info
            or {
                "volume": 125000,
                "surfaceArea": 23000,
                "boundingBox": {"x": 100, "y": 50, "z": 25},
            },
            parameters=parameters or {},
            file_formats=file_formats
            or {"step": f"s3://designs/{design_id}/v{version_number}/model.step"},
            **{k: v for k, v in kwargs.items() if k != "id"},
        )

        db.add(version)
        await db.commit()
        await db.refresh(version)
        return version


# =============================================================================
# Conversation Factory
# =============================================================================


class ConversationFactory:
    """Factory for creating Conversation instances."""

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        user: User | None = None,
        user_id: UUID | None = None,
        title: str | None = None,
        status: str = "completed",
        result_job_id: str | None = None,
        result_data: dict[str, Any] | None = None,
        intent_data: dict[str, Any] | None = None,
        use_default_result: bool = True,
        **kwargs: Any,
    ) -> Conversation:
        """Create and persist a Conversation instance.

        Args:
            db: Database session
            user: User instance
            user_id: User ID (alternative to user)
            title: Conversation title
            status: Conversation status
            result_job_id: Result job ID
            result_data: Result data dict. Pass None explicitly to create conversation without result.
            intent_data: Intent data dict
            use_default_result: If True and result_data is not provided, use defaults.
                               Set to False when you want result_data=None.
            **kwargs: Additional fields
        """
        from app.models.conversation import Conversation

        # Create user if not provided
        if user is None and user_id is None:
            user = await UserFactory.create(db)
            user_id = user.id
        elif user is not None:
            user_id = user.id

        n = Counter.next("conversation")

        # Handle result_data - only use defaults if result_data is None AND use_default_result is True
        if result_data is None and use_default_result and "result_data" not in kwargs:
            result_data = {
                "shape": "box",
                "dimensions": {"length": 100, "width": 50, "height": 25},
                "downloads": {"step": "/path/to/file.step", "stl": "/path/to/file.stl"},
            }

        conversation = Conversation(
            id=kwargs.get("id", uuid4()),
            user_id=user_id,
            title=title or f"Test Conversation {n}",
            status=status,
            result_job_id=result_job_id or str(uuid4()),
            result_data=result_data,
            intent_data=intent_data
            or {
                "description": "A test design",
            },
            **{k: v for k, v in kwargs.items() if k != "id"},
        )

        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation


# =============================================================================
# Fixture for resetting counters
# =============================================================================


def reset_factories() -> None:
    """Reset all factory counters. Call in test setup."""
    Counter.reset()


# Type hints for imports
if TYPE_CHECKING:
    from app.models import Design, File, Job, Project, Template, User
    from app.models.conversation import Conversation
    from app.models.design import DesignVersion
