"""
Contact Form API Tests.
"""

import pytest
from httpx import AsyncClient


@pytest.fixture
def valid_contact_data():
    """Valid contact form data."""
    return {
        "name": "John Doe",
        "email": "john@example.com",
        "subject": "Question about pricing",
        "message": "I'm interested in your Enterprise plan. Can you provide more details about the features and pricing options?",
    }


@pytest.mark.asyncio
class TestContactFormSubmission:
    """Tests for contact form submission endpoint."""

    async def test_submit_contact_form_success(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test successful contact form submission."""
        response = await async_client.post("/api/v1/contact", json=valid_contact_data)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "message" in data

    async def test_submit_contact_form_missing_name(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test contact form with missing name."""
        del valid_contact_data["name"]
        response = await async_client.post("/api/v1/contact", json=valid_contact_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_submit_contact_form_invalid_email(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test contact form with invalid email."""
        valid_contact_data["email"] = "not-an-email"
        response = await async_client.post("/api/v1/contact", json=valid_contact_data)

        assert response.status_code == 422

    async def test_submit_contact_form_short_name(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test contact form with name too short."""
        valid_contact_data["name"] = "J"
        response = await async_client.post("/api/v1/contact", json=valid_contact_data)

        assert response.status_code == 422

    async def test_submit_contact_form_short_subject(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test contact form with subject too short."""
        valid_contact_data["subject"] = "Hi"
        response = await async_client.post("/api/v1/contact", json=valid_contact_data)

        assert response.status_code == 422

    async def test_submit_contact_form_short_message(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test contact form with message too short."""
        valid_contact_data["message"] = "Short message."
        response = await async_client.post("/api/v1/contact", json=valid_contact_data)

        assert response.status_code == 422

    async def test_submit_contact_form_strips_whitespace(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test that whitespace is stripped from fields."""
        valid_contact_data["name"] = "  John Doe  "
        valid_contact_data["subject"] = "  Question about features  "
        response = await async_client.post("/api/v1/contact", json=valid_contact_data)

        assert response.status_code == 201


@pytest.mark.asyncio
class TestContactFormRateLimiting:
    """Tests for contact form rate limiting."""

    async def test_rate_limit_exceeded(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test that rate limit is enforced."""
        # Reset rate limiting state
        from app.api.v1.contact import _submission_times

        _submission_times.clear()

        # Make 5 successful requests (the limit)
        for i in range(5):
            valid_contact_data["email"] = f"user{i}@example.com"
            response = await async_client.post(
                "/api/v1/contact",
                json=valid_contact_data,
            )
            assert response.status_code == 201

        # 6th request should be rate limited
        valid_contact_data["email"] = "user6@example.com"
        response = await async_client.post(
            "/api/v1/contact",
            json=valid_contact_data,
        )

        assert response.status_code == 429
        assert "too many" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestContactFormSpamDetection:
    """Tests for contact form spam detection."""

    async def test_spam_keywords_detected(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test that spam keywords are detected but return success."""
        # Reset rate limiting
        from app.api.v1.contact import _submission_times

        _submission_times.clear()

        valid_contact_data["message"] = (
            "Congratulations! You've won the LOTTERY! Click here to claim your prize money now!"
        )
        response = await async_client.post("/api/v1/contact", json=valid_contact_data)

        # Returns success to not reveal detection
        assert response.status_code == 201

    async def test_legitimate_message_passes(
        self,
        async_client: AsyncClient,
        valid_contact_data: dict,
    ):
        """Test that legitimate messages are not flagged as spam."""
        # Reset rate limiting
        from app.api.v1.contact import _submission_times

        _submission_times.clear()

        valid_contact_data["message"] = (
            "I'm interested in integrating AssemblematicAI with my existing "
            "CAD workflow. Do you have any documentation on API integration?"
        )
        response = await async_client.post("/api/v1/contact", json=valid_contact_data)

        assert response.status_code == 201


@pytest.mark.asyncio
class TestContactInfo:
    """Tests for contact information endpoint."""

    async def test_get_contact_info(self, async_client: AsyncClient):
        """Test getting public contact information."""
        response = await async_client.get("/api/v1/contact/info")

        assert response.status_code == 200
        data = response.json()

        assert "email" in data
        assert "sales_email" in data
        assert "address" in data
        assert "response_time" in data
        assert "social" in data

    async def test_contact_info_contains_address(self, async_client: AsyncClient):
        """Test that contact info contains full address."""
        response = await async_client.get("/api/v1/contact/info")
        data = response.json()

        address = data["address"]
        assert "street" in address
        assert "city" in address
        assert "state" in address
        assert "zip" in address
        assert "country" in address
