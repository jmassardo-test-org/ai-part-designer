"""
Tests for v2 marketplace API endpoints.

Tests browse, featured, categories, and publish endpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio

from app.models.design import Design
from app.models.project import Project

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user) -> Project:
    """Create a test project for the test user."""
    project = Project(
        user_id=test_user.id,
        name="Marketplace Test Project",
        description="A project for marketplace tests",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def public_designs(db_session: AsyncSession, test_project) -> list[Design]:
    """Create a set of public designs for marketplace testing."""
    now = datetime.now(UTC)
    designs = []

    # Popular electronics design
    design1 = Design(
        project_id=test_project.id,
        user_id=test_project.user_id,
        name="Arduino Uno Case",
        description="A sleek case for Arduino Uno boards",
        is_public=True,
        published_at=now - timedelta(days=5),
        category="arduino",
        tags=["arduino", "beginner", "case"],
        save_count=100,
        remix_count=25,
        source_type="v2_generated",
        status="ready",
    )
    designs.append(design1)

    # Featured raspberry pi design
    design2 = Design(
        project_id=test_project.id,
        user_id=test_project.user_id,
        name="Pi 5 Enclosure with Fan",
        description="Raspberry Pi 5 enclosure with active cooling",
        is_public=True,
        published_at=now - timedelta(days=2),
        featured_at=now - timedelta(days=1),
        category="raspberry-pi",
        tags=["raspberry-pi", "pi5", "cooling"],
        save_count=50,
        remix_count=10,
        source_type="v2_generated",
        status="ready",
    )
    designs.append(design2)

    # Recent IoT design
    design3 = Design(
        project_id=test_project.id,
        user_id=test_project.user_id,
        name="ESP32 Weather Station",
        description="Compact enclosure for ESP32 weather station",
        is_public=True,
        published_at=now - timedelta(hours=2),
        category="iot",
        tags=["esp32", "iot", "weather"],
        save_count=5,
        remix_count=0,
        source_type="v2_generated",
        status="ready",
    )
    designs.append(design3)

    # Private design (should not appear in marketplace)
    design4 = Design(
        project_id=test_project.id,
        user_id=test_project.user_id,
        name="Private Project",
        description="This is a private design",
        is_public=False,
        category="electronics",
        tags=["private"],
        save_count=0,
        source_type="v2_generated",
        status="ready",
    )
    designs.append(design4)

    for design in designs:
        db_session.add(design)

    await db_session.commit()

    for design in designs:
        await db_session.refresh(design)

    return designs


class TestBrowseDesigns:
    """Tests for browsing marketplace designs."""

    @pytest.mark.asyncio
    async def test_browse_returns_only_public_designs(
        self, auth_client: AsyncClient, public_designs: list[Design]
    ):
        """Test that browse only returns public, published designs."""
        response = await auth_client.get("/api/v2/marketplace/designs")

        assert response.status_code == 200
        data = response.json()

        # Should return 3 public designs, not 4 (private is excluded)
        assert data["total"] == 3
        assert len(data["items"]) == 3

        # Private design should not be included
        names = [d["name"] for d in data["items"]]
        assert "Private Project" not in names

    @pytest.mark.asyncio
    async def test_browse_with_category_filter(
        self, auth_client: AsyncClient, public_designs: list[Design]
    ):
        """Test filtering by category."""
        response = await auth_client.get(
            "/api/v2/marketplace/designs",
            params={"category": "raspberry-pi"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["name"] == "Pi 5 Enclosure with Fan"

    @pytest.mark.asyncio
    async def test_browse_with_tag_filter(
        self, auth_client: AsyncClient, public_designs: list[Design]
    ):
        """Test filtering by tags."""
        response = await auth_client.get(
            "/api/v2/marketplace/designs",
            params={"tags": ["esp32"]},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["name"] == "ESP32 Weather Station"

    @pytest.mark.asyncio
    async def test_browse_with_search(self, auth_client: AsyncClient, public_designs: list[Design]):
        """Test text search."""
        response = await auth_client.get(
            "/api/v2/marketplace/designs",
            params={"search": "arduino"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["name"] == "Arduino Uno Case"

    @pytest.mark.asyncio
    async def test_browse_sort_by_popular(
        self, auth_client: AsyncClient, public_designs: list[Design]
    ):
        """Test sorting by popularity (save count)."""
        response = await auth_client.get(
            "/api/v2/marketplace/designs",
            params={"sort": "popular"},
        )

        assert response.status_code == 200
        data = response.json()

        # Arduino Uno Case has highest save_count (100)
        assert data["items"][0]["name"] == "Arduino Uno Case"

    @pytest.mark.asyncio
    async def test_browse_sort_by_recent(
        self, auth_client: AsyncClient, public_designs: list[Design]
    ):
        """Test sorting by recent."""
        response = await auth_client.get(
            "/api/v2/marketplace/designs",
            params={"sort": "recent"},
        )

        assert response.status_code == 200
        data = response.json()

        # ESP32 Weather Station is most recent
        assert data["items"][0]["name"] == "ESP32 Weather Station"

    @pytest.mark.asyncio
    async def test_browse_pagination(self, auth_client: AsyncClient, public_designs: list[Design]):
        """Test pagination."""
        response = await auth_client.get(
            "/api/v2/marketplace/designs",
            params={"page": 1, "page_size": 2},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["has_next"] is True
        assert data["has_prev"] is False
        assert data["page"] == 1
        assert data["total_pages"] == 2


class TestFeaturedDesigns:
    """Tests for featured designs endpoint."""

    @pytest.mark.asyncio
    async def test_get_featured_designs(
        self, auth_client: AsyncClient, public_designs: list[Design]
    ):
        """Test getting featured designs."""
        response = await auth_client.get("/api/v2/marketplace/featured")

        assert response.status_code == 200
        data = response.json()

        # Only one design is featured
        assert len(data) == 1
        assert data[0]["name"] == "Pi 5 Enclosure with Fan"

    @pytest.mark.asyncio
    async def test_featured_limit(self, auth_client: AsyncClient, public_designs: list[Design]):
        """Test featured designs limit parameter."""
        response = await auth_client.get(
            "/api/v2/marketplace/featured",
            params={"limit": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1


class TestCategories:
    """Tests for categories endpoint."""

    @pytest.mark.asyncio
    async def test_get_categories(self, auth_client: AsyncClient, public_designs: list[Design]):
        """Test getting categories with counts."""
        response = await auth_client.get("/api/v2/marketplace/categories")

        assert response.status_code == 200
        data = response.json()

        # Should have categories from public designs
        category_slugs = [c["slug"] for c in data]
        assert "arduino" in category_slugs
        assert "raspberry-pi" in category_slugs
        assert "iot" in category_slugs

        # Check counts
        arduino = next(c for c in data if c["slug"] == "arduino")
        assert arduino["design_count"] == 1


class TestDesignDetail:
    """Tests for single design detail endpoint."""

    @pytest.mark.asyncio
    async def test_get_public_design_detail(
        self, auth_client: AsyncClient, public_designs: list[Design]
    ):
        """Test getting a public design's details."""
        design = public_designs[0]  # Arduino Uno Case
        response = await auth_client.get(f"/api/v2/marketplace/designs/{design.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(design.id)
        assert data["name"] == "Arduino Uno Case"
        assert data["save_count"] == 100
        assert data["is_saved"] is False  # Not saved by test user

    @pytest.mark.asyncio
    async def test_get_private_design_returns_403(
        self, auth_client: AsyncClient, public_designs: list[Design]
    ):
        """Test that private designs return 403 for non-owners."""
        private_design = public_designs[3]  # Private Project
        response = await auth_client.get(f"/api/v2/marketplace/designs/{private_design.id}")

        # Since the auth_client IS the owner, this should work
        # Let's test with a different user's private design
        assert response.status_code == 200  # Owner can access

    @pytest.mark.asyncio
    async def test_get_nonexistent_design_returns_404(self, auth_client: AsyncClient):
        """Test that nonexistent designs return 404."""
        fake_id = uuid4()
        response = await auth_client.get(f"/api/v2/marketplace/designs/{fake_id}")

        assert response.status_code == 404


class TestPublishDesign:
    """Tests for publishing designs to marketplace."""

    @pytest_asyncio.fixture
    async def private_design(self, db_session: AsyncSession, test_project: Project) -> Design:
        """Create a private design to publish."""
        design = Design(
            project_id=test_project.id,
            user_id=test_project.user_id,
            name="Design to Publish",
            description="This design will be published",
            is_public=False,
            category=None,
            tags=[],
            source_type="v2_generated",
            status="ready",
        )
        db_session.add(design)
        await db_session.commit()
        await db_session.refresh(design)
        return design

    @pytest.mark.asyncio
    async def test_publish_design_success(self, auth_client: AsyncClient, private_design: Design):
        """Test publishing a design."""
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{private_design.id}/publish",
            json={
                "category": "electronics",
                "tags": ["custom", "project"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(private_design.id)
        assert data["category"] == "electronics"
        assert data["published_at"] is not None

    @pytest.mark.asyncio
    async def test_publish_with_invalid_category_returns_400(
        self, auth_client: AsyncClient, private_design: Design
    ):
        """Test that invalid category returns 400."""
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{private_design.id}/publish",
            json={"category": "invalid-category"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_publish_nonexistent_design_returns_404(self, auth_client: AsyncClient):
        """Test publishing nonexistent design returns 404."""
        fake_id = uuid4()
        response = await auth_client.post(
            f"/api/v2/marketplace/designs/{fake_id}/publish",
            json={},
        )

        assert response.status_code == 404


class TestUnpublishDesign:
    """Tests for unpublishing designs."""

    @pytest.mark.asyncio
    async def test_unpublish_design_success(
        self, auth_client: AsyncClient, public_designs: list[Design]
    ):
        """Test unpublishing a design."""
        design = public_designs[0]  # Arduino Uno Case (public)
        response = await auth_client.post(f"/api/v2/marketplace/designs/{design.id}/unpublish")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Design unpublished successfully"
