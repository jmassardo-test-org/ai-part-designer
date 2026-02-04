"""
Tests for v2 starters API endpoints.

Tests starter gallery browsing and remix functionality.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design import Design
from app.models.project import Project


@pytest_asyncio.fixture
async def admin_project(db_session: AsyncSession, test_admin) -> Project:
    """Create a project for admin/vendor designs."""
    project = Project(
        user_id=test_admin.id,
        name="Vendor Designs",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def starter_designs(db_session: AsyncSession, admin_project) -> list[Design]:
    """Create a set of starter designs."""
    now = datetime.now(timezone.utc)
    designs = []
    
    # Raspberry Pi starter
    design1 = Design(
        project_id=admin_project.id,
        user_id=admin_project.user_id,
        name="Raspberry Pi 5 Basic Case",
        description="A simple case for Raspberry Pi 5 with ventilation",
        source_type="template",
        is_public=True,
        is_starter=True,
        published_at=now,
        category="raspberry-pi",
        tags=["raspberry-pi", "pi5", "basic"],
        remix_count=50,
        enclosure_spec={
            "exterior": {
                "width": {"value": 100, "unit": "mm"},
                "depth": {"value": 70, "unit": "mm"},
                "height": {"value": 30, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 2, "unit": "mm"}},
            "lid": {"type": "snap_fit"},
            "ventilation": {"enabled": True, "sides": ["top"]},
            "features": [
                {"type": "port", "port_type": "usb-c"},
                {"type": "port", "port_type": "hdmi"},
            ],
        },
    )
    designs.append(design1)
    
    # Arduino starter
    design2 = Design(
        project_id=admin_project.id,
        user_id=admin_project.user_id,
        name="Arduino Uno Shield Case",
        description="Enclosure for Arduino Uno with room for shields",
        source_type="template",
        is_public=True,
        is_starter=True,
        published_at=now,
        category="arduino",
        tags=["arduino", "uno", "shields"],
        remix_count=30,
        enclosure_spec={
            "exterior": {
                "width": {"value": 80, "unit": "mm"},
                "depth": {"value": 60, "unit": "mm"},
                "height": {"value": 40, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 2.5, "unit": "mm"}},
            "lid": {"type": "screw_on"},
        },
    )
    designs.append(design2)
    
    # ESP32 starter
    design3 = Design(
        project_id=admin_project.id,
        user_id=admin_project.user_id,
        name="ESP32 Compact Case",
        description="Minimal case for ESP32 development boards",
        source_type="template",
        is_public=True,
        is_starter=True,
        published_at=now,
        category="esp32",
        tags=["esp32", "iot", "compact"],
        remix_count=20,
        enclosure_spec={
            "exterior": {
                "width": {"value": 60, "unit": "mm"},
                "depth": {"value": 40, "unit": "mm"},
                "height": {"value": 20, "unit": "mm"},
            },
            "walls": {"thickness": {"value": 1.5, "unit": "mm"}},
        },
    )
    designs.append(design3)
    
    # Non-starter public design (should not appear in starters)
    design4 = Design(
        project_id=admin_project.id,
        user_id=admin_project.user_id,
        name="Regular Public Design",
        description="This is public but not a starter",
        source_type="template",
        is_public=True,
        is_starter=False,
        published_at=now,
        category="electronics",
    )
    designs.append(design4)
    
    for design in designs:
        db_session.add(design)
    
    await db_session.commit()
    
    for design in designs:
        await db_session.refresh(design)
    
    return designs


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user) -> Project:
    """Create a test project for the test user."""
    project = Project(
        user_id=test_user.id,
        name="My Designs",
        description="Default project",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


class TestListStarters:
    """Tests for listing starter designs."""
    
    @pytest.mark.asyncio
    async def test_list_starters_returns_only_starters(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test that list only returns starter designs."""
        response = await auth_client.get("/api/v2/starters/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return 3 starters, not 4 (regular public is excluded)
        assert data["total"] == 3
        assert len(data["items"]) == 3
        
        names = [d["name"] for d in data["items"]]
        assert "Raspberry Pi 5 Basic Case" in names
        assert "Arduino Uno Shield Case" in names
        assert "ESP32 Compact Case" in names
        assert "Regular Public Design" not in names
    
    @pytest.mark.asyncio
    async def test_list_starters_sorted_by_remix_count(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test that starters are sorted by remix count."""
        response = await auth_client.get("/api/v2/starters/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Most remixed first
        assert data["items"][0]["name"] == "Raspberry Pi 5 Basic Case"  # 50 remixes
        assert data["items"][1]["name"] == "Arduino Uno Shield Case"  # 30 remixes
        assert data["items"][2]["name"] == "ESP32 Compact Case"  # 20 remixes
    
    @pytest.mark.asyncio
    async def test_list_starters_filter_by_category(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test filtering starters by category."""
        response = await auth_client.get(
            "/api/v2/starters/",
            params={"category": "arduino"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Arduino Uno Shield Case"
    
    @pytest.mark.asyncio
    async def test_list_starters_filter_by_tags(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test filtering starters by tags."""
        response = await auth_client.get(
            "/api/v2/starters/",
            params={"tags": ["iot"]},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["items"][0]["name"] == "ESP32 Compact Case"
    
    @pytest.mark.asyncio
    async def test_list_starters_search(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test searching starters."""
        response = await auth_client.get(
            "/api/v2/starters/",
            params={"search": "raspberry"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Raspberry Pi 5 Basic Case"
    
    @pytest.mark.asyncio
    async def test_list_starters_includes_feature_info(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test that starters include extracted feature info."""
        response = await auth_client.get("/api/v2/starters/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Find the Pi design
        pi_design = next(d for d in data["items"] if "Raspberry Pi" in d["name"])
        
        assert pi_design["exterior_dimensions"] is not None
        assert pi_design["exterior_dimensions"]["width"] == 100
        assert "port" in pi_design["features"]


class TestGetStarterDetail:
    """Tests for getting starter details."""
    
    @pytest.mark.asyncio
    async def test_get_starter_detail(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test getting full starter details."""
        starter = starter_designs[0]  # Raspberry Pi case
        response = await auth_client.get(f"/api/v2/starters/{starter.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(starter.id)
        assert data["name"] == "Raspberry Pi 5 Basic Case"
        assert data["enclosure_spec"] is not None
        assert "exterior" in data["enclosure_spec"]
    
    @pytest.mark.asyncio
    async def test_get_non_starter_returns_404(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test that non-starters return 404."""
        non_starter = starter_designs[3]  # Regular Public Design
        response = await auth_client.get(f"/api/v2/starters/{non_starter.id}")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_starter_returns_404(
        self, auth_client: AsyncClient
    ):
        """Test nonexistent starter returns 404."""
        fake_id = uuid4()
        response = await auth_client.get(f"/api/v2/starters/{fake_id}")
        
        assert response.status_code == 404


class TestRemixDesign:
    """Tests for remixing starter designs."""
    
    @pytest.mark.asyncio
    async def test_remix_design_creates_copy(
        self, auth_client: AsyncClient, starter_designs: list[Design], test_project: Project
    ):
        """Test remixing creates a new design."""
        starter = starter_designs[0]  # Raspberry Pi case
        
        response = await auth_client.post(
            f"/api/v2/starters/{starter.id}/remix",
            json={},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["remixed_from_id"] == str(starter.id)
        assert data["remixed_from_name"] == starter.name
        assert "Remix" in data["name"]
        assert data["enclosure_spec"] is not None
    
    @pytest.mark.asyncio
    async def test_remix_with_custom_name(
        self, auth_client: AsyncClient, starter_designs: list[Design], test_project: Project
    ):
        """Test remixing with custom name."""
        starter = starter_designs[0]
        
        response = await auth_client.post(
            f"/api/v2/starters/{starter.id}/remix",
            json={"name": "My Custom Pi Case"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "My Custom Pi Case"
    
    @pytest.mark.asyncio
    async def test_remix_increments_remix_count(
        self, auth_client: AsyncClient, starter_designs: list[Design], test_project: Project, db_session: AsyncSession
    ):
        """Test that remixing increments the remix count."""
        starter = starter_designs[0]
        original_count = starter.remix_count
        
        await auth_client.post(
            f"/api/v2/starters/{starter.id}/remix",
            json={},
        )
        
        await db_session.refresh(starter)
        assert starter.remix_count == original_count + 1
    
    @pytest.mark.asyncio
    async def test_remix_copies_enclosure_spec(
        self, auth_client: AsyncClient, starter_designs: list[Design], test_project: Project
    ):
        """Test that remix copies the enclosure spec."""
        starter = starter_designs[0]
        
        response = await auth_client.post(
            f"/api/v2/starters/{starter.id}/remix",
            json={},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Spec should match original
        assert data["enclosure_spec"]["exterior"]["width"]["value"] == 100
        assert data["enclosure_spec"]["exterior"]["depth"]["value"] == 70
    
    @pytest.mark.asyncio
    async def test_remix_non_starter_returns_404(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test that remixing non-starter returns 404."""
        non_starter = starter_designs[3]
        
        response = await auth_client.post(
            f"/api/v2/starters/{non_starter.id}/remix",
            json={},
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_remix_requires_authentication(
        self, client: AsyncClient, starter_designs: list[Design]
    ):
        """Test that remix requires authentication."""
        starter = starter_designs[0]
        
        response = await client.post(
            f"/api/v2/starters/{starter.id}/remix",
            json={},
        )
        
        assert response.status_code == 401


class TestStarterCategories:
    """Tests for starter categories."""
    
    @pytest.mark.asyncio
    async def test_get_categories_with_counts(
        self, auth_client: AsyncClient, starter_designs: list[Design]
    ):
        """Test getting categories with design counts."""
        response = await auth_client.get("/api/v2/starters/categories")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only include categories that have starters
        slugs = [c["slug"] for c in data]
        assert "raspberry-pi" in slugs
        assert "arduino" in slugs
        assert "esp32" in slugs
        
        # Check counts
        pi_cat = next(c for c in data if c["slug"] == "raspberry-pi")
        assert pi_cat["count"] == 1


class TestListRemixes:
    """Tests for listing remixes of a starter."""
    
    @pytest.mark.asyncio
    async def test_list_public_remixes(
        self, auth_client: AsyncClient, starter_designs: list[Design], db_session: AsyncSession, test_project: Project
    ):
        """Test listing public remixes of a starter."""
        starter = starter_designs[0]
        
        # Create some remixes
        for i in range(3):
            remix = Design(
                project_id=test_project.id,
                user_id=test_project.user_id,
                name=f"Remix {i}",
                source_type="modified",
                remixed_from_id=starter.id,
                is_public=i < 2,  # First 2 are public
            )
            db_session.add(remix)
        
        await db_session.commit()
        
        response = await auth_client.get(f"/api/v2/starters/{starter.id}/remixes")
        
        assert response.status_code == 200
        data = response.json()
        
        # Only 2 public remixes
        assert data["total"] == 2
