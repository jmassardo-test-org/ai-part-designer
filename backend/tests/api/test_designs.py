"""
Tests for Designs API endpoints.

Tests design CRUD operations and saving designs from jobs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

# =============================================================================
# List Designs Tests
# =============================================================================


class TestListDesigns:
    """Tests for listing designs endpoint."""

    @pytest.mark.asyncio
    async def test_list_designs_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that listing designs requires authentication."""
        response = await client.get("/api/v1/designs")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_designs_empty(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test listing designs when none exist."""
        response = await client.get(
            "/api/v1/designs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["designs"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_designs_with_designs(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test listing designs."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        await DesignFactory.create(db=db_session, project=project, name="Design 1")
        await DesignFactory.create(db=db_session, project=project, name="Design 2")
        await DesignFactory.create(db=db_session, project=project, name="Design 3")

        response = await client.get(
            "/api/v1/designs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["designs"]) == 3
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_designs_only_own_designs(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that users only see their own designs."""
        from tests.factories import DesignFactory, ProjectFactory, UserFactory

        # Create designs for test user
        my_project = await ProjectFactory.create(db=db_session, user=test_user)
        await DesignFactory.create(db=db_session, project=my_project, name="My Design")

        # Create designs for another user
        other_user = await UserFactory.create(db=db_session)
        other_project = await ProjectFactory.create(db=db_session, user=other_user)
        await DesignFactory.create(db=db_session, project=other_project, name="Other Design")

        response = await client.get(
            "/api/v1/designs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["designs"]) == 1
        assert data["designs"][0]["name"] == "My Design"


# =============================================================================
# Create Design Tests
# =============================================================================


class TestCreateDesign:
    """Tests for creating designs."""

    @pytest.mark.asyncio
    async def test_create_design_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test creating a new design."""
        from tests.factories import ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)

        response = await client.post(
            "/api/v1/designs",
            headers=auth_headers,
            json={
                "name": "New Design",
                "description": "A test design",
                "project_id": str(project.id),
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "New Design"
        assert data["description"] == "A test design"
        assert data["project_id"] == str(project.id)

    @pytest.mark.asyncio
    async def test_create_design_default_project(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test creating a design without project creates default project."""
        response = await client.post(
            "/api/v1/designs",
            headers=auth_headers,
            json={
                "name": "Design Without Project",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Design Without Project"
        assert data["project_name"] == "My Designs"

    @pytest.mark.asyncio
    async def test_create_design_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that creating designs requires authentication."""
        response = await client.post(
            "/api/v1/designs",
            json={"name": "Test Design"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_design_name_required(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test that design name is required."""
        response = await client.post(
            "/api/v1/designs",
            headers=auth_headers,
            json={
                "description": "A design without name",
            },
        )

        assert response.status_code == 422


# =============================================================================
# Create Design From Job Tests
# =============================================================================


class TestCreateDesignFromJob:
    """Tests for creating designs from completed jobs."""

    @pytest.mark.asyncio
    async def test_create_from_job_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test creating a design from a completed job."""
        from tests.factories import JobFactory

        job = await JobFactory.create(
            db=db_session,
            user=test_user,
            status="completed",
            result={
                "shape": "box",
                "dimensions": {"length": 100, "width": 50, "height": 25},
                "downloads": {"step": "/path/to/file.step"},
            },
        )

        response = await client.post(
            "/api/v1/designs/from-job",
            headers=auth_headers,
            json={
                "job_id": str(job.id),
                "name": "Design From AI",
                "description": "Generated by AI",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Design From AI"
        assert data["source_type"] == "ai_generated"
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_create_from_job_to_specific_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test creating a design from job to a specific project."""
        from tests.factories import JobFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user, name="My CAD Projects")
        job = await JobFactory.create(
            db=db_session,
            user=test_user,
            status="completed",
            result={"shape": "cylinder"},
        )

        response = await client.post(
            "/api/v1/designs/from-job",
            headers=auth_headers,
            json={
                "job_id": str(job.id),
                "name": "Cylinder Design",
                "project_id": str(project.id),
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["project_id"] == str(project.id)
        assert data["project_name"] == "My CAD Projects"

    @pytest.mark.asyncio
    async def test_create_from_job_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test creating design from non-existent job."""
        response = await client.post(
            "/api/v1/designs/from-job",
            headers=auth_headers,
            json={
                "job_id": str(uuid4()),
                "name": "Design",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_from_job_not_completed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test creating design from incomplete job."""
        from tests.factories import JobFactory

        job = await JobFactory.create(
            db=db_session,
            user=test_user,
            status="pending",
        )

        response = await client.post(
            "/api/v1/designs/from-job",
            headers=auth_headers,
            json={
                "job_id": str(job.id),
                "name": "Design",
            },
        )

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_from_job_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test creating design from another user's job."""
        from tests.factories import JobFactory, UserFactory

        other_user = await UserFactory.create(db=db_session)
        other_job = await JobFactory.create(
            db=db_session,
            user=other_user,
            status="completed",
        )

        response = await client.post(
            "/api/v1/designs/from-job",
            headers=auth_headers,
            json={
                "job_id": str(other_job.id),
                "name": "Stolen Design",
            },
        )

        assert response.status_code == 404  # Returns 404 for security

    @pytest.mark.asyncio
    async def test_create_from_job_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that creating from job requires authentication."""
        response = await client.post(
            "/api/v1/designs/from-job",
            json={
                "job_id": str(uuid4()),
                "name": "Design",
            },
        )

        assert response.status_code == 401


# =============================================================================
# Create Design From Conversation Tests
# =============================================================================


class TestCreateDesignFromConversation:
    """Tests for creating designs from conversations."""

    @pytest.mark.asyncio
    async def test_create_from_conversation_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test creating a design from a completed conversation."""
        from tests.factories import ConversationFactory

        conversation = await ConversationFactory.create(
            db=db_session,
            user=test_user,
            status="completed",
            result_data={
                "shape": "box",
                "dimensions": {"length": 100, "width": 50, "height": 25},
                "downloads": {"step": "/path/to/file.step"},
            },
        )

        response = await client.post(
            "/api/v1/designs/from-conversation",
            headers=auth_headers,
            json={
                "conversation_id": str(conversation.id),
                "name": "Design From Chat",
                "description": "Generated via chat",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Design From Chat"
        assert data["source_type"] == "ai_generated"
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_create_from_conversation_to_specific_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test creating a design from conversation to a specific project."""
        from tests.factories import ConversationFactory, ProjectFactory

        project = await ProjectFactory.create(
            db=db_session, user=test_user, name="My Chat Projects"
        )
        conversation = await ConversationFactory.create(
            db=db_session,
            user=test_user,
            status="completed",
            result_data={"shape": "cylinder"},
        )

        response = await client.post(
            "/api/v1/designs/from-conversation",
            headers=auth_headers,
            json={
                "conversation_id": str(conversation.id),
                "name": "Cylinder Design",
                "project_id": str(project.id),
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["project_id"] == str(project.id)
        assert data["project_name"] == "My Chat Projects"

    @pytest.mark.asyncio
    async def test_create_from_conversation_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test creating design from non-existent conversation."""
        response = await client.post(
            "/api/v1/designs/from-conversation",
            headers=auth_headers,
            json={
                "conversation_id": str(uuid4()),
                "name": "Design",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_from_conversation_no_result(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test creating design from conversation with no result data."""
        from tests.factories import ConversationFactory

        conversation = await ConversationFactory.create(
            db=db_session,
            user=test_user,
            status="active",
            result_data=None,
            use_default_result=False,  # Explicitly want None
        )

        response = await client.post(
            "/api/v1/designs/from-conversation",
            headers=auth_headers,
            json={
                "conversation_id": str(conversation.id),
                "name": "Design",
            },
        )

        assert response.status_code == 400
        assert "no result data" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_from_conversation_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test creating design from another user's conversation."""
        from tests.factories import ConversationFactory, UserFactory

        other_user = await UserFactory.create(db=db_session)
        other_conversation = await ConversationFactory.create(
            db=db_session,
            user=other_user,
            status="completed",
        )

        response = await client.post(
            "/api/v1/designs/from-conversation",
            headers=auth_headers,
            json={
                "conversation_id": str(other_conversation.id),
                "name": "Stolen Design",
            },
        )

        assert response.status_code == 404  # Returns 404 for security

    @pytest.mark.asyncio
    async def test_create_from_conversation_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that creating from conversation requires authentication."""
        response = await client.post(
            "/api/v1/designs/from-conversation",
            json={
                "conversation_id": str(uuid4()),
                "name": "Design",
            },
        )

        assert response.status_code == 401


# =============================================================================
# Get Design Tests
# =============================================================================


class TestGetDesign:
    """Tests for getting design details."""

    @pytest.mark.asyncio
    async def test_get_design_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test getting a design by ID."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(
            db=db_session,
            project=project,
            name="Test Design",
            description="Test description",
        )

        response = await client.get(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Test Design"
        assert data["description"] == "Test description"

    @pytest.mark.asyncio
    async def test_get_design_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test getting non-existent design."""
        response = await client.get(
            f"/api/v1/designs/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_design_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test getting another user's design."""
        from tests.factories import DesignFactory, ProjectFactory, UserFactory

        other_user = await UserFactory.create(db=db_session)
        other_project = await ProjectFactory.create(db=db_session, user=other_user)
        other_design = await DesignFactory.create(db=db_session, project=other_project)

        response = await client.get(
            f"/api/v1/designs/{other_design.id}",
            headers=auth_headers,
        )

        assert response.status_code == 404  # Returns 404 for security


# =============================================================================
# Update Design Tests
# =============================================================================


class TestUpdateDesign:
    """Tests for updating designs."""

    @pytest.mark.asyncio
    async def test_update_design_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test updating a design."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(
            db=db_session,
            project=project,
            name="Original Name",
        )

        response = await client.patch(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
            json={"name": "Updated Name", "description": "New description"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"

    @pytest.mark.asyncio
    async def test_update_design_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test updating another user's design."""
        from tests.factories import DesignFactory, ProjectFactory, UserFactory

        other_user = await UserFactory.create(db=db_session)
        other_project = await ProjectFactory.create(db=db_session, user=other_user)
        other_design = await DesignFactory.create(db=db_session, project=other_project)

        response = await client.patch(
            f"/api/v1/designs/{other_design.id}",
            headers=auth_headers,
            json={"name": "Hacked Name"},
        )

        assert response.status_code == 404


# =============================================================================
# Delete Design Tests
# =============================================================================


class TestDeleteDesign:
    """Tests for deleting designs (soft delete)."""

    @pytest.mark.asyncio
    async def test_delete_design_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test soft deleting a design."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(db=db_session, project=project)

        response = await client.delete(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        # Now returns 200 with undo token
        assert response.status_code == 200
        data = response.json()
        assert "undo_token" in data

        # Verify it's soft deleted (shouldn't appear in list)
        list_response = await client.get(
            "/api/v1/designs",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["designs"]) == 0

    @pytest.mark.asyncio
    async def test_delete_design_not_owner(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test deleting another user's design."""
        from tests.factories import DesignFactory, ProjectFactory, UserFactory

        other_user = await UserFactory.create(db=db_session)
        other_project = await ProjectFactory.create(db=db_session, user=other_user)
        other_design = await DesignFactory.create(db=db_session, project=other_project)

        response = await client.delete(
            f"/api/v1/designs/{other_design.id}",
            headers=auth_headers,
        )

        assert response.status_code == 404


# =============================================================================
# Notification Trigger Tests
# =============================================================================


class TestDesignNotifications:
    """Tests for notification triggers when saving designs."""

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Pre-existing issue: JOB_COMPLETED notification type not in DB enum")
    async def test_create_from_conversation_creates_notification(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that saving a design from conversation creates a notification."""
        from sqlalchemy import select

        from app.models.notification import Notification
        from tests.factories import ConversationFactory

        conversation = await ConversationFactory.create(
            db=db_session,
            user=test_user,
            status="completed",
            result_data={
                "shape": "box",
                "dimensions": {"length": 100},
                "downloads": {"stl": "/path/to/file.stl"},
            },
        )

        response = await client.post(
            "/api/v1/designs/from-conversation",
            headers=auth_headers,
            json={
                "conversation_id": str(conversation.id),
                "name": "My Saved Design",
            },
        )

        assert response.status_code == 201

        # Check that a notification was created
        result = await db_session.execute(
            select(Notification)
            .where(Notification.user_id == test_user.id)
            .where(Notification.title == "Design Saved")
        )
        notification = result.scalar_one_or_none()

        assert notification is not None
        assert "My Saved Design" in notification.message

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Pre-existing issue: JOB_COMPLETED notification type not in DB enum")
    async def test_create_from_job_creates_notification(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that saving a design from job creates a notification."""
        from sqlalchemy import select

        from app.models.notification import Notification
        from tests.factories import JobFactory

        job = await JobFactory.create(
            db=db_session,
            user=test_user,
            status="completed",
            result={
                "shape": "cylinder",
                "dimensions": {"radius": 25, "height": 100},
                "downloads": {"step": "/path/to/file.step"},
            },
        )

        response = await client.post(
            "/api/v1/designs/from-job",
            headers=auth_headers,
            json={
                "job_id": str(job.id),
                "name": "Cylinder Part",
            },
        )

        assert response.status_code == 201

        # Check that a notification was created
        result = await db_session.execute(
            select(Notification)
            .where(Notification.user_id == test_user.id)
            .where(Notification.title == "Design Saved")
        )
        notification = result.scalar_one_or_none()

        assert notification is not None
        assert "Cylinder Part" in notification.message


# =============================================================================
# Copy Design Tests
# =============================================================================


class TestCopyDesign:
    """Tests for copying designs endpoint."""

    @pytest.mark.asyncio
    async def test_copy_design_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that copying a design requires authentication."""
        response = await client.post(
            f"/api/v1/designs/{uuid4()}/copy",
            json={"name": "Copy"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_copy_design_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test copying a design."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(
            db=db_session,
            project=project,
            name="Original",
            description="Original design",
        )

        response = await client.post(
            f"/api/v1/designs/{design.id}/copy",
            headers=auth_headers,
            json={"name": "Copy of Original"},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Copy of Original"
        assert data["copied_from_id"] == str(design.id)
        assert data["project_id"] == str(project.id)

    @pytest.mark.asyncio
    async def test_copy_design_to_different_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test copying a design to a different project."""
        from tests.factories import DesignFactory, ProjectFactory

        project1 = await ProjectFactory.create(db=db_session, user=test_user, name="Project 1")
        project2 = await ProjectFactory.create(db=db_session, user=test_user, name="Project 2")
        design = await DesignFactory.create(db=db_session, project=project1, name="Original")

        response = await client.post(
            f"/api/v1/designs/{design.id}/copy",
            headers=auth_headers,
            json={
                "name": "Copy in Project 2",
                "target_project_id": str(project2.id),
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert data["project_id"] == str(project2.id)
        assert data["project_name"] == "Project 2"

    @pytest.mark.asyncio
    async def test_copy_design_not_found(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test copying a non-existent design returns 404."""
        response = await client.post(
            f"/api/v1/designs/{uuid4()}/copy",
            headers=auth_headers,
            json={"name": "Copy"},
        )

        assert response.status_code == 404


# =============================================================================
# Delete Design with Undo Tests
# =============================================================================


class TestDeleteDesignWithUndo:
    """Tests for delete design with undo capability."""

    @pytest.mark.asyncio
    async def test_delete_design_returns_undo_token(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that deleting a design returns an undo token."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(db=db_session, project=project, name="To Delete")

        response = await client.delete(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "undo_token" in data
        assert "expires_at" in data
        assert "Design deleted" in data["message"]

    @pytest.mark.asyncio
    async def test_delete_design_soft_delete(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that delete performs soft delete."""
        from sqlalchemy import select

        from app.models.design import Design
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(db=db_session, project=project, name="To Delete")
        design_id = design.id

        await client.delete(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        # Design should still exist but with deleted_at set
        result = await db_session.execute(select(Design).where(Design.id == design_id))
        deleted_design = result.scalar_one_or_none()

        assert deleted_design is not None
        assert deleted_design.deleted_at is not None

    @pytest.mark.asyncio
    async def test_undo_delete_restores_design(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that undo restores a deleted design."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(db=db_session, project=project, name="To Restore")

        # Delete the design
        delete_response = await client.delete(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        undo_token = delete_response.json()["undo_token"]

        # Undo the delete
        undo_response = await client.post(
            f"/api/v1/designs/undo/{undo_token}",
            headers=auth_headers,
        )

        assert undo_response.status_code == 200
        data = undo_response.json()

        # Response has message and design fields
        assert "restored" in data["message"].lower()
        assert data["design"]["name"] == "To Restore"
        assert data["design"]["id"] == str(design.id)

    @pytest.mark.asyncio
    async def test_undo_delete_invalid_token(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test that invalid undo token returns generic error (prevents enumeration)."""
        response = await client.post(
            "/api/v1/designs/undo/invalid-token",
            headers=auth_headers,
        )

        # SECURITY: Should return 400 with generic message
        # to prevent token enumeration attacks
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]


# =============================================================================
# Update Design (Move) Tests
# =============================================================================


class TestMoveDesign:
    """Tests for moving designs between projects."""

    @pytest.mark.asyncio
    async def test_move_design_to_different_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test moving a design to another project via PATCH."""
        from tests.factories import DesignFactory, ProjectFactory

        project1 = await ProjectFactory.create(db=db_session, user=test_user, name="Source Project")
        project2 = await ProjectFactory.create(db=db_session, user=test_user, name="Target Project")
        design = await DesignFactory.create(db=db_session, project=project1, name="To Move")

        response = await client.patch(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
            json={"project_id": str(project2.id)},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["project_id"] == str(project2.id)
        assert data["project_name"] == "Target Project"

    @pytest.mark.asyncio
    async def test_move_to_nonexistent_project_fails(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that moving to non-existent project returns 404."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(db=db_session, project=project)

        response = await client.patch(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
            json={"project_id": str(uuid4())},
        )

        assert response.status_code == 404


# =============================================================================
# Version Endpoints Tests
# =============================================================================


class TestDesignVersions:
    """Tests for design version endpoints."""

    @pytest.mark.asyncio
    async def test_list_versions_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that listing versions requires authentication."""
        response = await client.get(f"/api/v1/designs/{uuid4()}/versions")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_versions_empty(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test listing versions when none exist."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(db=db_session, project=project)

        response = await client.get(
            f"/api/v1/designs/{design.id}/versions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["versions"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_versions_design_not_found(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test listing versions for non-existent design."""
        response = await client.get(
            f"/api/v1/designs/{uuid4()}/versions",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_version_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that creating a version requires authentication."""
        response = await client.post(
            f"/api/v1/designs/{uuid4()}/versions",
            json={"name": "v1.0"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_version_design_not_found(
        self,
        client: AsyncClient,
        auth_headers,
    ):
        """Test creating version for non-existent design."""
        response = await client.post(
            f"/api/v1/designs/{uuid4()}/versions",
            headers=auth_headers,
            json={"name": "v1.0"},
        )

        assert response.status_code == 404


# =============================================================================
# Security Tests
# =============================================================================


class TestDesignSecurity:
    """Security-focused tests for design endpoints."""

    @pytest.mark.asyncio
    async def test_cannot_undo_other_users_delete(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that users cannot undo another user's delete even with valid token format."""
        from tests.factories import DesignFactory, ProjectFactory, UserFactory

        # Create another user's design
        other_user = await UserFactory.create(db=db_session)
        other_project = await ProjectFactory.create(db=db_session, user=other_user)
        await DesignFactory.create(db=db_session, project=other_project)

        # Try to undo with a fake token (simulating intercepted token)
        response = await client.post(
            "/api/v1/designs/undo/some-fake-token",
            headers=auth_headers,
        )

        # Should get generic error, not "wrong user" (prevents enumeration)
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]
        # Should NOT reveal that token exists but belongs to another user

    @pytest.mark.asyncio
    async def test_cannot_copy_other_users_design(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that users cannot copy another user's private design."""
        from tests.factories import DesignFactory, ProjectFactory, UserFactory

        other_user = await UserFactory.create(db=db_session)
        other_project = await ProjectFactory.create(db=db_session, user=other_user)
        other_design = await DesignFactory.create(db=db_session, project=other_project)

        response = await client.post(
            f"/api/v1/designs/{other_design.id}/copy",
            headers=auth_headers,
            json={"name": "Stolen Copy"},
        )

        assert response.status_code == 404  # Should not reveal design exists

    @pytest.mark.asyncio
    async def test_cannot_move_to_other_users_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that users cannot move designs to another user's project."""
        from tests.factories import DesignFactory, ProjectFactory, UserFactory

        # User's own design
        my_project = await ProjectFactory.create(db=db_session, user=test_user)
        my_design = await DesignFactory.create(db=db_session, project=my_project)

        # Other user's project
        other_user = await UserFactory.create(db=db_session)
        other_project = await ProjectFactory.create(db=db_session, user=other_user)

        response = await client.patch(
            f"/api/v1/designs/{my_design.id}",
            headers=auth_headers,
            json={"project_id": str(other_project.id)},
        )

        assert response.status_code == 404  # Target project "not found"

    @pytest.mark.asyncio
    async def test_delete_response_does_not_leak_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
    ):
        """Test that delete response only contains necessary information."""
        from tests.factories import DesignFactory, ProjectFactory

        project = await ProjectFactory.create(db=db_session, user=test_user)
        design = await DesignFactory.create(
            db=db_session,
            project=project,
            name="Secret Design",
            description="Sensitive description",
        )

        response = await client.delete(
            f"/api/v1/designs/{design.id}",
            headers=auth_headers,
        )

        data = response.json()

        # Response should only contain undo info, not full design details
        assert "undo_token" in data
        assert "design_id" in data
        assert "description" not in data
        assert "extra_data" not in data
