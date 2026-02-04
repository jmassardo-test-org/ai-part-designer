"""
Tests for template ratings API endpoints.

Tests rating creation, retrieval, summary, and feedback.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import Counter, TemplateFactory, UserFactory


@pytest.fixture(autouse=True)
def reset_counters():
    """Reset factory counters before each test."""
    Counter.reset()


class TestTemplateRatings:
    """Tests for template rating endpoints."""

    async def test_rate_template_success(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """User can rate a template."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        response = await client.post(
            f"/api/v1/templates/{template.id}/ratings",
            headers=auth_headers,
            json={"score": 5, "review": "Excellent template!"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["score"] == 5
        assert data["review"] == "Excellent template!"

    async def test_rate_template_updates_existing(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Rating again updates existing rating."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        # First rating
        await client.post(
            f"/api/v1/templates/{template.id}/ratings",
            headers=auth_headers,
            json={"score": 3}
        )
        
        # Update rating
        response = await client.post(
            f"/api/v1/templates/{template.id}/ratings",
            headers=auth_headers,
            json={"score": 5, "review": "Changed my mind, great!"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["score"] == 5
        assert data["review"] == "Changed my mind, great!"

    async def test_rate_template_invalid_score(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Invalid score returns 422."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        response = await client.post(
            f"/api/v1/templates/{template.id}/ratings",
            headers=auth_headers,
            json={"score": 0}  # Invalid - must be 1-5
        )
        
        assert response.status_code == 422

    async def test_get_template_ratings(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Anyone can view template ratings."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        response = await client.get(
            f"/api/v1/templates/{template.id}/ratings"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_rating_summary(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Get rating summary with average and distribution."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        # Add a rating
        await client.post(
            f"/api/v1/templates/{template.id}/ratings",
            headers=auth_headers,
            json={"score": 4}
        )
        
        response = await client.get(
            f"/api/v1/templates/{template.id}/ratings/summary"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "average" in data
        assert "total_count" in data
        assert "distribution" in data

    async def test_get_my_rating(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """User can get their own rating."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        # Create rating
        await client.post(
            f"/api/v1/templates/{template.id}/ratings",
            headers=auth_headers,
            json={"score": 5}
        )
        
        response = await client.get(
            f"/api/v1/templates/{template.id}/ratings/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 5

    async def test_get_my_rating_not_rated(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Returns null if user hasn't rated."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        response = await client.get(
            f"/api/v1/templates/{template.id}/ratings/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json() is None

    async def test_delete_rating(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """User can delete their rating."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        # Create rating
        await client.post(
            f"/api/v1/templates/{template.id}/ratings",
            headers=auth_headers,
            json={"score": 3}
        )
        
        response = await client.delete(
            f"/api/v1/templates/{template.id}/ratings",
            headers=auth_headers
        )
        
        assert response.status_code == 204

    async def test_delete_rating_not_found(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Deleting non-existent rating returns 404."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        response = await client.delete(
            f"/api/v1/templates/{template.id}/ratings",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestTemplateFeedback:
    """Tests for template feedback (thumbs up/down) endpoints."""

    async def test_set_thumbs_up(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """User can give thumbs up."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        response = await client.post(
            f"/api/v1/templates/{template.id}/feedback",
            headers=auth_headers,
            json={"feedback_type": "thumbs_up"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["feedback_type"] == "thumbs_up"

    async def test_set_thumbs_down(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """User can give thumbs down."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        response = await client.post(
            f"/api/v1/templates/{template.id}/feedback",
            headers=auth_headers,
            json={"feedback_type": "thumbs_down"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["feedback_type"] == "thumbs_down"

    async def test_change_feedback(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """User can change their feedback."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        # Set thumbs up
        await client.post(
            f"/api/v1/templates/{template.id}/feedback",
            headers=auth_headers,
            json={"feedback_type": "thumbs_up"}
        )
        
        # Change to thumbs down
        response = await client.post(
            f"/api/v1/templates/{template.id}/feedback",
            headers=auth_headers,
            json={"feedback_type": "thumbs_down"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["feedback_type"] == "thumbs_down"

    async def test_get_feedback_summary(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Get feedback summary with counts."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        # Add feedback
        await client.post(
            f"/api/v1/templates/{template.id}/feedback",
            headers=auth_headers,
            json={"feedback_type": "thumbs_up"}
        )
        
        response = await client.get(
            f"/api/v1/templates/{template.id}/feedback",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "thumbs_up_count" in data
        assert "thumbs_down_count" in data
        assert data["thumbs_up_count"] >= 1

    async def test_remove_feedback(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """User can remove their feedback."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        # Add feedback
        await client.post(
            f"/api/v1/templates/{template.id}/feedback",
            headers=auth_headers,
            json={"feedback_type": "thumbs_up"}
        )
        
        response = await client.delete(
            f"/api/v1/templates/{template.id}/feedback",
            headers=auth_headers
        )
        
        assert response.status_code == 204

    async def test_remove_feedback_not_found(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Removing non-existent feedback returns 404."""
        template = await TemplateFactory.create(db_session, is_active=True)
        
        response = await client.delete(
            f"/api/v1/templates/{template.id}/feedback",
            headers=auth_headers
        )
        
        assert response.status_code == 404
