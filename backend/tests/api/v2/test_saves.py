"""
Tests for v2 saves API endpoints.

Tests save/unsave designs and checking save status.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.design import Design
from app.models.marketplace import DesignList
from app.models.project import Project

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user) -> Project:
    """Create a test project for the test user."""
    project = Project(
        user_id=test_user.id,
        name="Saves Test Project",
        description="A project for saves tests",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def public_design(db_session: AsyncSession, test_project) -> Design:
    """Create a public design to save."""
    design = Design(
        project_id=test_project.id,
        user_id=test_project.user_id,
        name="Saveable Design",
        description="A public design that can be saved",
        source_type="v2_generated",
        status="ready",
        is_public=True,
        published_at=datetime.now(UTC),
        save_count=5,
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
async def other_user_design(db_session: AsyncSession) -> Design:
    """Create a public design from another user."""
    from tests.factories import UserFactory

    # Create an actual user in the database
    other_user = await UserFactory.create(db_session)

    project = Project(
        user_id=other_user.id,
        name="Other Project",
    )
    db_session.add(project)
    await db_session.flush()

    design = Design(
        project_id=project.id,
        user_id=other_user.id,
        name="Other User's Design",
        description="A public design from another user",
        source_type="v2_generated",
        status="ready",
        is_public=True,
        published_at=datetime.now(UTC),
        save_count=10,
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)
    return design


@pytest_asyncio.fixture
async def user_lists(db_session: AsyncSession, test_user) -> list[DesignList]:
    """Create test lists for the user."""
    lists = []
    for name in ["Favorites", "Electronics"]:
        list_obj = DesignList(
            user_id=test_user.id,
            name=name,
            is_public=False,
        )
        db_session.add(list_obj)
        lists.append(list_obj)

    await db_session.commit()
    for list_obj in lists:
        await db_session.refresh(list_obj)

    return lists


class TestSaveDesign:
    """Tests for saving designs."""

    @pytest.mark.asyncio
    async def test_save_design_creates_default_list(
        self,
        auth_client: AsyncClient,
        other_user_design: Design,
        db_session: AsyncSession,
        test_user,
    ):
        """Test saving a design creates default list if needed."""
        response = await auth_client.post(
            f"/api/v2/saves/{other_user_design.id}",
            json={},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["design_id"] == str(other_user_design.id)
        assert len(data["lists"]) == 1
        assert data["lists"][0]["name"] == "Saved Designs"  # Default list

    @pytest.mark.asyncio
    async def test_save_design_to_specific_lists(
        self, auth_client: AsyncClient, other_user_design: Design, user_lists: list[DesignList]
    ):
        """Test saving a design to specific lists."""
        list_ids = [str(lst.id) for lst in user_lists]

        response = await auth_client.post(
            f"/api/v2/saves/{other_user_design.id}",
            json={"list_ids": list_ids},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["lists"]) == 2
        list_names = [lst["name"] for lst in data["lists"]]
        assert "Favorites" in list_names
        assert "Electronics" in list_names

    @pytest.mark.asyncio
    async def test_save_design_increments_save_count(
        self, auth_client: AsyncClient, other_user_design: Design, db_session: AsyncSession
    ):
        """Test that saving increments the design's save count."""
        original_count = other_user_design.save_count

        await auth_client.post(
            f"/api/v2/saves/{other_user_design.id}",
            json={},
        )

        # Refresh to get updated count
        await db_session.refresh(other_user_design)
        assert other_user_design.save_count == original_count + 1

    @pytest.mark.asyncio
    async def test_save_already_saved_design_adds_to_new_lists(
        self,
        auth_client: AsyncClient,
        other_user_design: Design,
        user_lists: list[DesignList],
        db_session: AsyncSession,
        test_user,
    ):
        """Test saving an already-saved design to additional lists."""
        # First save
        await auth_client.post(
            f"/api/v2/saves/{other_user_design.id}",
            json={},
        )

        # Second save to specific lists
        response = await auth_client.post(
            f"/api/v2/saves/{other_user_design.id}",
            json={"list_ids": [str(user_lists[0].id)]},
        )

        assert response.status_code == 200
        data = response.json()

        # Should be in the new list
        assert len(data["lists"]) >= 1

    @pytest.mark.asyncio
    async def test_save_nonexistent_design_returns_404(self, auth_client: AsyncClient):
        """Test saving nonexistent design returns 404."""
        fake_id = uuid4()
        response = await auth_client.post(
            f"/api/v2/saves/{fake_id}",
            json={},
        )

        assert response.status_code == 404


class TestUnsaveDesign:
    """Tests for unsaving designs."""

    @pytest.mark.asyncio
    async def test_unsave_design_removes_from_all_lists(
        self,
        auth_client: AsyncClient,
        other_user_design: Design,
        user_lists: list[DesignList],
        db_session: AsyncSession,
        test_user,
    ):
        """Test unsaving removes from all lists."""
        # Save first
        await auth_client.post(
            f"/api/v2/saves/{other_user_design.id}",
            json={"list_ids": [str(lst.id) for lst in user_lists]},
        )

        # Unsave
        response = await auth_client.delete(f"/api/v2/saves/{other_user_design.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["design_id"] == str(other_user_design.id)
        assert data["removed_from_lists"] == 2

    @pytest.mark.asyncio
    async def test_unsave_decrements_save_count(
        self, auth_client: AsyncClient, other_user_design: Design, db_session: AsyncSession
    ):
        """Test that unsaving decrements the design's save count."""
        # Save first
        await auth_client.post(
            f"/api/v2/saves/{other_user_design.id}",
            json={},
        )

        await db_session.refresh(other_user_design)
        count_after_save = other_user_design.save_count

        # Unsave
        await auth_client.delete(f"/api/v2/saves/{other_user_design.id}")

        await db_session.refresh(other_user_design)
        assert other_user_design.save_count == count_after_save - 1

    @pytest.mark.asyncio
    async def test_unsave_not_saved_design(
        self, auth_client: AsyncClient, other_user_design: Design
    ):
        """Test unsaving a design that wasn't saved."""
        response = await auth_client.delete(f"/api/v2/saves/{other_user_design.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["removed_from_lists"] == 0


class TestGetMySaves:
    """Tests for getting saved designs."""

    @pytest.mark.asyncio
    async def test_get_saves_empty(self, auth_client: AsyncClient):
        """Test getting saves when none exist."""
        response = await auth_client.get("/api/v2/saves/")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_saves_with_designs(
        self, auth_client: AsyncClient, other_user_design: Design, db_session: AsyncSession
    ):
        """Test getting saved designs."""
        # Save a design
        await auth_client.post(
            f"/api/v2/saves/{other_user_design.id}",
            json={},
        )

        response = await auth_client.get("/api/v2/saves/")

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["design_id"] == str(other_user_design.id)
        assert "design" in data["items"][0]

    @pytest.mark.asyncio
    async def test_get_saves_pagination(
        self, auth_client: AsyncClient, db_session: AsyncSession, test_project: Project
    ):
        """Test pagination of saved designs."""
        # Create and save multiple designs
        for i in range(5):
            design = Design(
                project_id=test_project.id,
                user_id=test_project.user_id,
                name=f"Design {i}",
                source_type="v2_generated",
                status="ready",
                is_public=True,
                published_at=datetime.now(UTC),
            )
            db_session.add(design)
            await db_session.flush()

            await auth_client.post(f"/api/v2/saves/{design.id}", json={})

        await db_session.commit()

        response = await auth_client.get(
            "/api/v2/saves/",
            params={"page": 1, "page_size": 2},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2


class TestCheckSaveStatus:
    """Tests for checking save status."""

    @pytest.mark.asyncio
    async def test_check_unsaved_design(self, auth_client: AsyncClient, other_user_design: Design):
        """Test checking status of unsaved design."""
        response = await auth_client.get(f"/api/v2/saves/{other_user_design.id}/check")

        assert response.status_code == 200
        data = response.json()

        assert data["design_id"] == str(other_user_design.id)
        assert data["is_saved"] is False
        assert data["in_lists"] == []

    @pytest.mark.asyncio
    async def test_check_saved_design(
        self, auth_client: AsyncClient, other_user_design: Design, user_lists: list[DesignList]
    ):
        """Test checking status of saved design."""
        # Save to lists
        list_ids = [str(lst.id) for lst in user_lists]
        await auth_client.post(
            f"/api/v2/saves/{other_user_design.id}",
            json={"list_ids": list_ids},
        )

        response = await auth_client.get(f"/api/v2/saves/{other_user_design.id}/check")

        assert response.status_code == 200
        data = response.json()

        assert data["design_id"] == str(other_user_design.id)
        assert data["is_saved"] is True
        assert len(data["in_lists"]) == 2


class TestSaveAccessControl:
    """Tests for save access control."""

    @pytest.mark.asyncio
    async def test_cannot_save_private_design(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that private designs from others cannot be saved."""
        from tests.factories import UserFactory

        # Create an actual user in the database
        other_user = await UserFactory.create(db_session)

        project = Project(
            user_id=other_user.id,
            name="Private Project",
        )
        db_session.add(project)
        await db_session.flush()

        private_design = Design(
            project_id=project.id,
            user_id=other_user.id,
            name="Private Design",
            source_type="v2_generated",
            status="ready",
            is_public=False,
        )
        db_session.add(private_design)
        await db_session.commit()
        await db_session.refresh(private_design)

        response = await auth_client.post(
            f"/api/v2/saves/{private_design.id}",
            json={},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_can_save_own_private_design(
        self, auth_client: AsyncClient, test_project: Project, db_session: AsyncSession
    ):
        """Test that users can save their own private designs."""
        private_design = Design(
            project_id=test_project.id,
            user_id=test_project.user_id,
            name="My Private Design",
            source_type="v2_generated",
            status="draft",
            is_public=False,
        )
        db_session.add(private_design)
        await db_session.commit()
        await db_session.refresh(private_design)

        response = await auth_client.post(
            f"/api/v2/saves/{private_design.id}",
            json={},
        )

        assert response.status_code == 200
