"""
Tests for DesignService.

Tests design management operations: copy, move, delete with undo, and versioning.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.design import Design
from app.models.project import Project
from app.models.user import User
from app.services.design_service import (
    DesignNotFoundError,
    DesignPermissionError,
    DesignService,
    ProjectNotFoundError,
    UndoTokenExpiredError,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user: User) -> Project:
    """Create a test project."""
    project = Project(
        name="Test Project",
        description="Test project description",
        user_id=test_user.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def second_project(db_session: AsyncSession, test_user: User) -> Project:
    """Create a second test project for move/copy operations."""
    project = Project(
        name="Second Project",
        description="Second project description",
        user_id=test_user.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_design(db_session: AsyncSession, test_project: Project, test_user: User) -> Design:
    """Create a test design."""
    design = Design(
        name="Test Design",
        description="Test design description",
        project_id=test_project.id,
        user_id=test_user.id,
        source_type="ai_generated",
        status="completed",
        extra_data={"thumbnail_url": "https://example.com/thumb.png"},
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
def design_service(db_session: AsyncSession) -> DesignService:
    """Create a DesignService instance."""
    return DesignService(db_session)


# =============================================================================
# Copy Design Tests
# =============================================================================


class TestCopyDesign:
    """Tests for the copy_design method."""

    @pytest.mark.asyncio
    async def test_copy_design_same_project(
        self,
        design_service: DesignService,
        test_design: Design,
        test_project: Project,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test copying a design within the same project."""
        result = await design_service.copy_design(
            design_id=test_design.id,
            name="Copy of Test Design",
            user=test_user,
        )

        assert result.design.name == "Copy of Test Design"
        assert result.design.project_id == test_project.id
        assert result.design.copied_from_id == test_design.id
        assert result.design.id != test_design.id
        assert result.design.description == test_design.description
        assert result.design.source_type == "copied"  # Copies get source_type="copied"

    @pytest.mark.asyncio
    async def test_copy_design_different_project(
        self,
        design_service: DesignService,
        test_design: Design,
        second_project: Project,
        test_user: User,
    ):
        """Test copying a design to a different project."""
        result = await design_service.copy_design(
            design_id=test_design.id,
            name="Copied Design",
            user=test_user,
            target_project_id=second_project.id,
        )

        assert result.design.name == "Copied Design"
        assert result.design.project_id == second_project.id
        assert result.design.copied_from_id == test_design.id

    @pytest.mark.asyncio
    async def test_copy_design_not_found(
        self,
        design_service: DesignService,
        test_user: User,
    ):
        """Test copying a non-existent design raises error."""
        with pytest.raises(DesignNotFoundError):
            await design_service.copy_design(
                design_id=uuid4(),
                name="Copy",
                user=test_user,
            )

    @pytest.mark.asyncio
    async def test_copy_design_invalid_target_project(
        self,
        design_service: DesignService,
        test_design: Design,
        test_user: User,
    ):
        """Test copying to a non-existent project raises error."""
        with pytest.raises(ProjectNotFoundError):
            await design_service.copy_design(
                design_id=test_design.id,
                name="Copy",
                user=test_user,
                target_project_id=uuid4(),
            )


# =============================================================================
# Move Design Tests
# =============================================================================


class TestMoveDesign:
    """Tests for the move_design method."""

    @pytest.mark.asyncio
    async def test_move_design_to_another_project(
        self,
        design_service: DesignService,
        test_design: Design,
        second_project: Project,
        test_user: User,
    ):
        """Test moving a design to another project."""
        original_project_id = test_design.project_id

        result = await design_service.move_design(
            design_id=test_design.id,
            target_project_id=second_project.id,
            user=test_user,
        )

        assert result.project_id == second_project.id
        assert result.project_id != original_project_id
        assert result.id == test_design.id  # Same design, just moved

    @pytest.mark.asyncio
    async def test_move_design_to_same_project(
        self,
        design_service: DesignService,
        test_design: Design,
        test_project: Project,
        test_user: User,
    ):
        """Test moving to same project returns design without changes."""
        result = await design_service.move_design(
            design_id=test_design.id,
            target_project_id=test_project.id,
            user=test_user,
        )

        assert result.project_id == test_project.id

    @pytest.mark.asyncio
    async def test_move_design_not_found(
        self,
        design_service: DesignService,
        second_project: Project,
        test_user: User,
    ):
        """Test moving a non-existent design raises error."""
        with pytest.raises(DesignNotFoundError):
            await design_service.move_design(
                design_id=uuid4(),
                target_project_id=second_project.id,
                user=test_user,
            )


# =============================================================================
# Delete Design Tests
# =============================================================================


class TestDeleteDesign:
    """Tests for the delete_design and undo_delete methods."""

    @pytest.fixture(autouse=True)
    def mock_redis_for_undo(self):
        """Mock Redis for undo token operations."""
        with patch("app.core.undo_tokens.redis_client") as mock_redis:
            # Storage for tokens during test
            tokens = {}

            async def mock_set_json(key, data, ttl=None):
                tokens[key] = data

            async def mock_get_json(key):
                return tokens.get(key)

            async def mock_delete(key):
                if key in tokens:
                    del tokens[key]
                    return 1
                return 0

            mock_redis.set_json = AsyncMock(side_effect=mock_set_json)
            mock_redis.get_json = AsyncMock(side_effect=mock_get_json)
            mock_redis.delete = AsyncMock(side_effect=mock_delete)

            yield mock_redis

    @pytest.mark.asyncio
    async def test_delete_design_soft_delete(
        self,
        design_service: DesignService,
        test_design: Design,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that delete performs a soft delete."""
        result = await design_service.delete_design(
            design_id=test_design.id,
            user=test_user,
        )

        assert result.undo_token is not None
        assert len(result.undo_token) > 0

        # Verify design is soft-deleted
        await db_session.refresh(test_design)
        assert test_design.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_design_not_found(
        self,
        design_service: DesignService,
        test_user: User,
    ):
        """Test deleting a non-existent design raises error."""
        with pytest.raises(DesignNotFoundError):
            await design_service.delete_design(
                design_id=uuid4(),
                user=test_user,
            )

    @pytest.mark.asyncio
    async def test_undo_delete_restores_design(
        self,
        design_service: DesignService,
        test_design: Design,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that undo_delete restores a soft-deleted design."""
        result = await design_service.delete_design(
            design_id=test_design.id,
            user=test_user,
        )

        # Verify it's deleted
        await db_session.refresh(test_design)
        assert test_design.deleted_at is not None

        # Undo the delete
        restored = await design_service.undo_delete(
            undo_token=result.undo_token,
            user=test_user,
        )

        assert restored.id == test_design.id
        assert restored.deleted_at is None

    @pytest.mark.asyncio
    async def test_undo_delete_invalid_token(
        self,
        design_service: DesignService,
        test_user: User,
    ):
        """Test that invalid undo token raises error."""
        with pytest.raises(UndoTokenExpiredError):
            await design_service.undo_delete(
                undo_token="invalid-token",
                user=test_user,
            )


# =============================================================================
# Version Management Tests
# =============================================================================


class TestVersionManagement:
    """Tests for version listing, creation, and restoration."""

    @pytest.mark.asyncio
    async def test_list_versions_empty(
        self,
        design_service: DesignService,
        test_design: Design,
        test_user: User,
    ):
        """Test listing versions for a design with no versions."""
        versions, total = await design_service.list_versions(
            design_id=test_design.id,
            user=test_user,
        )

        assert total == 0
        assert versions == []

    @pytest.mark.asyncio
    async def test_list_versions_not_found(
        self,
        design_service: DesignService,
        test_user: User,
    ):
        """Test listing versions for non-existent design."""
        with pytest.raises(DesignNotFoundError):
            await design_service.list_versions(
                design_id=uuid4(),
                user=test_user,
            )


# =============================================================================
# Permission Tests
# =============================================================================


class TestPermissions:
    """Tests for permission checks."""

    @pytest_asyncio.fixture
    async def other_user(self, db_session: AsyncSession) -> User:
        """Create another user for permission testing."""
        from app.core.security import hash_password

        user = User(
            email="other@example.com",
            password_hash=hash_password("OtherPassword123!"),
            display_name="Other User",
            status="active",
            email_verified_at=datetime.now(UTC),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.mark.asyncio
    async def test_copy_design_other_users_design(
        self,
        design_service: DesignService,
        test_design: Design,
        other_user: User,
    ):
        """Test copying another user's design fails."""
        with pytest.raises(DesignPermissionError):
            await design_service.copy_design(
                design_id=test_design.id,
                name="Copy",
                user=other_user,
            )

    @pytest.mark.asyncio
    async def test_delete_design_other_users_design(
        self,
        design_service: DesignService,
        test_design: Design,
        other_user: User,
    ):
        """Test deleting another user's design fails."""
        with pytest.raises(DesignPermissionError):
            await design_service.delete_design(
                design_id=test_design.id,
                user=other_user,
            )


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_copy_deleted_design_fails(
        self,
        design_service: DesignService,
        test_design: Design,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that copying a deleted design fails."""
        # Soft delete the design
        await design_service.delete_design(
            design_id=test_design.id,
            user=test_user,
        )

        # Attempt to copy should fail
        with pytest.raises(DesignNotFoundError):
            await design_service.copy_design(
                design_id=test_design.id,
                name="Copy",
                user=test_user,
            )

    @pytest.mark.asyncio
    async def test_copy_preserves_extra_data(
        self,
        design_service: DesignService,
        test_design: Design,
        test_user: User,
    ):
        """Test that copying preserves extra_data."""
        result = await design_service.copy_design(
            design_id=test_design.id,
            name="Copy",
            user=test_user,
        )

        assert result.design.extra_data == test_design.extra_data
