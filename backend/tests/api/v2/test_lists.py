"""
Tests for v2 lists API endpoints.

Tests CRUD for lists, items, and reordering.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design import Design
from app.models.marketplace import DesignList, DesignListItem
from app.models.project import Project


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user) -> Project:
    """Create a test project for the test user."""
    project = Project(
        user_id=test_user.id,
        name="Lists Test Project",
        description="A project for lists tests",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_designs(db_session: AsyncSession, test_project) -> list[Design]:
    """Create test designs to add to lists."""
    designs = []
    for i in range(3):
        design = Design(
            project_id=test_project.id,
            user_id=test_project.user_id,
            name=f"Test Design {i + 1}",
            description=f"Design {i + 1} for testing lists",
            is_public=True,
        )
        db_session.add(design)
        designs.append(design)
    
    await db_session.commit()
    for design in designs:
        await db_session.refresh(design)
    
    return designs


@pytest_asyncio.fixture
async def user_lists(db_session: AsyncSession, test_user) -> list[DesignList]:
    """Create test lists for the user."""
    lists = []
    for i, (name, color) in enumerate([
        ("Favorites", "#ef4444"),
        ("Arduino Projects", "#3b82f6"),
        ("To Review", "#22c55e"),
    ]):
        list_obj = DesignList(
            user_id=test_user.id,
            name=name,
            description=f"Description for {name}",
            icon="folder",
            color=color,
            is_public=False,
            position=i,
        )
        db_session.add(list_obj)
        lists.append(list_obj)
    
    await db_session.commit()
    for list_obj in lists:
        await db_session.refresh(list_obj)
    
    return lists


class TestListCRUD:
    """Tests for list CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_get_my_lists_empty(self, auth_client: AsyncClient):
        """Test getting lists when none exist."""
        response = await auth_client.get("/api/v2/lists/")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    @pytest.mark.asyncio
    async def test_get_my_lists(
        self, auth_client: AsyncClient, user_lists: list[DesignList]
    ):
        """Test getting all user's lists."""
        response = await auth_client.get("/api/v2/lists/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3
        names = [lst["name"] for lst in data]
        assert "Favorites" in names
        assert "Arduino Projects" in names
    
    @pytest.mark.asyncio
    async def test_create_list_success(self, auth_client: AsyncClient):
        """Test creating a new list."""
        response = await auth_client.post(
            "/api/v2/lists/",
            json={
                "name": "My New List",
                "description": "A brand new list",
                "icon": "star",
                "color": "#8b5cf6",
                "is_public": False,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "My New List"
        assert data["description"] == "A brand new list"
        assert data["icon"] == "star"
        assert data["color"] == "#8b5cf6"
        assert data["item_count"] == 0
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_list_minimal(self, auth_client: AsyncClient):
        """Test creating a list with minimal data."""
        response = await auth_client.post(
            "/api/v2/lists/",
            json={"name": "Minimal List"},
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "Minimal List"
        assert data["icon"] == "folder"  # Default
        assert data["color"] == "#6366f1"  # Default
    
    @pytest.mark.asyncio
    async def test_get_list_with_items(
        self, auth_client: AsyncClient, user_lists: list[DesignList], test_designs: list[Design], db_session: AsyncSession
    ):
        """Test getting a list with its items."""
        # Add items to the list
        list_obj = user_lists[0]  # Favorites
        for i, design in enumerate(test_designs):
            item = DesignListItem(
                list_id=list_obj.id,
                design_id=design.id,
                position=i,
            )
            db_session.add(item)
        await db_session.commit()
        
        response = await auth_client.get(f"/api/v2/lists/{list_obj.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(list_obj.id)
        assert data["name"] == "Favorites"
        assert len(data["items"]) == 3
    
    @pytest.mark.asyncio
    async def test_update_list(
        self, auth_client: AsyncClient, user_lists: list[DesignList]
    ):
        """Test updating a list."""
        list_obj = user_lists[0]
        response = await auth_client.put(
            f"/api/v2/lists/{list_obj.id}",
            json={
                "name": "Updated Favorites",
                "color": "#f59e0b",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Updated Favorites"
        assert data["color"] == "#f59e0b"
        assert data["description"] == list_obj.description  # Unchanged
    
    @pytest.mark.asyncio
    async def test_delete_list(
        self, auth_client: AsyncClient, user_lists: list[DesignList]
    ):
        """Test deleting a list."""
        list_obj = user_lists[0]
        response = await auth_client.delete(f"/api/v2/lists/{list_obj.id}")
        
        assert response.status_code == 204
        
        # Verify it's deleted
        response = await auth_client.get(f"/api/v2/lists/{list_obj.id}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_list_returns_404(self, auth_client: AsyncClient):
        """Test getting a nonexistent list."""
        fake_id = uuid4()
        response = await auth_client.get(f"/api/v2/lists/{fake_id}")
        
        assert response.status_code == 404


class TestListItems:
    """Tests for list item operations."""
    
    @pytest.mark.asyncio
    async def test_add_design_to_list(
        self, auth_client: AsyncClient, user_lists: list[DesignList], test_designs: list[Design]
    ):
        """Test adding a design to a list."""
        list_obj = user_lists[0]
        design = test_designs[0]
        
        response = await auth_client.post(
            f"/api/v2/lists/{list_obj.id}/items",
            json={
                "design_id": str(design.id),
                "note": "Great design!",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["list_id"] == str(list_obj.id)
        assert data["design_id"] == str(design.id)
        assert data["note"] == "Great design!"
        assert data["design_name"] == design.name
    
    @pytest.mark.asyncio
    async def test_add_duplicate_design_returns_409(
        self, auth_client: AsyncClient, user_lists: list[DesignList], test_designs: list[Design]
    ):
        """Test that adding duplicate design returns conflict."""
        list_obj = user_lists[0]
        design = test_designs[0]
        
        # Add first time
        await auth_client.post(
            f"/api/v2/lists/{list_obj.id}/items",
            json={"design_id": str(design.id)},
        )
        
        # Add second time
        response = await auth_client.post(
            f"/api/v2/lists/{list_obj.id}/items",
            json={"design_id": str(design.id)},
        )
        
        assert response.status_code == 409
    
    @pytest.mark.asyncio
    async def test_remove_design_from_list(
        self, auth_client: AsyncClient, user_lists: list[DesignList], test_designs: list[Design], db_session: AsyncSession
    ):
        """Test removing a design from a list."""
        list_obj = user_lists[0]
        design = test_designs[0]
        
        # Add item first
        item = DesignListItem(
            list_id=list_obj.id,
            design_id=design.id,
            position=0,
        )
        db_session.add(item)
        await db_session.commit()
        
        # Remove it
        response = await auth_client.delete(
            f"/api/v2/lists/{list_obj.id}/items/{design.id}"
        )
        
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_item_returns_404(
        self, auth_client: AsyncClient, user_lists: list[DesignList]
    ):
        """Test removing nonexistent item returns 404."""
        list_obj = user_lists[0]
        fake_id = uuid4()
        
        response = await auth_client.delete(
            f"/api/v2/lists/{list_obj.id}/items/{fake_id}"
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_list_items_with_design_info(
        self, auth_client: AsyncClient, user_lists: list[DesignList], test_designs: list[Design], db_session: AsyncSession
    ):
        """Test getting list items includes full design info."""
        list_obj = user_lists[0]
        
        for i, design in enumerate(test_designs):
            item = DesignListItem(
                list_id=list_obj.id,
                design_id=design.id,
                position=i,
            )
            db_session.add(item)
        await db_session.commit()
        
        response = await auth_client.get(f"/api/v2/lists/{list_obj.id}/items")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3
        # Each item should have design info
        assert "design" in data[0]
        assert "id" in data[0]["design"]
        assert "name" in data[0]["design"]
    
    @pytest.mark.asyncio
    async def test_update_list_item_note(
        self, auth_client: AsyncClient, user_lists: list[DesignList], test_designs: list[Design], db_session: AsyncSession
    ):
        """Test updating a list item's note."""
        list_obj = user_lists[0]
        design = test_designs[0]
        
        item = DesignListItem(
            list_id=list_obj.id,
            design_id=design.id,
            position=0,
            note="Original note",
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)
        
        response = await auth_client.put(
            f"/api/v2/lists/{list_obj.id}/items/{item.id}",
            json={"note": "Updated note"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["note"] == "Updated note"


class TestListReordering:
    """Tests for reordering list items."""
    
    @pytest.mark.asyncio
    async def test_reorder_items(
        self, auth_client: AsyncClient, user_lists: list[DesignList], test_designs: list[Design], db_session: AsyncSession
    ):
        """Test reordering items in a list."""
        list_obj = user_lists[0]
        items = []
        
        for i, design in enumerate(test_designs):
            item = DesignListItem(
                list_id=list_obj.id,
                design_id=design.id,
                position=i,
            )
            db_session.add(item)
            items.append(item)
        await db_session.commit()
        
        for item in items:
            await db_session.refresh(item)
        
        # Reverse the order
        new_order = [str(items[2].id), str(items[1].id), str(items[0].id)]
        
        response = await auth_client.patch(
            f"/api/v2/lists/{list_obj.id}/items/reorder",
            json={"item_ids": new_order},
        )
        
        assert response.status_code == 204
        
        # Verify new order
        response = await auth_client.get(f"/api/v2/lists/{list_obj.id}")
        data = response.json()
        
        # Items should be in new order
        assert data["items"][0]["id"] == new_order[0]
        assert data["items"][1]["id"] == new_order[1]
        assert data["items"][2]["id"] == new_order[2]


class TestListAccessControl:
    """Tests for list access control."""
    
    @pytest.mark.asyncio
    async def test_cannot_access_other_users_list(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that users cannot access other users' lists."""
        # Create a list for a different user
        other_user_id = uuid4()
        other_list = DesignList(
            user_id=other_user_id,
            name="Other User's List",
            description="Not yours",
        )
        db_session.add(other_list)
        await db_session.commit()
        await db_session.refresh(other_list)
        
        response = await auth_client.get(f"/api/v2/lists/{other_list.id}")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_cannot_add_private_design_to_list(
        self, auth_client: AsyncClient, user_lists: list[DesignList], db_session: AsyncSession
    ):
        """Test that private designs from others cannot be added."""
        # Create a private design from another user
        other_user_id = uuid4()
        other_project = Project(
            user_id=other_user_id,
            name="Other Project",
        )
        db_session.add(other_project)
        await db_session.flush()
        
        private_design = Design(
            project_id=other_project.id,
            user_id=other_user_id,
            name="Private Design",
            is_public=False,
        )
        db_session.add(private_design)
        await db_session.commit()
        await db_session.refresh(private_design)
        
        list_obj = user_lists[0]
        response = await auth_client.post(
            f"/api/v2/lists/{list_obj.id}/items",
            json={"design_id": str(private_design.id)},
        )
        
        assert response.status_code == 403
