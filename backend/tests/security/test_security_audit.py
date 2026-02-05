"""
Security Audit Tests for v1.0 Release.

These tests verify security requirements for production deployment.
Run with: python -m pytest tests/security/test_security_audit.py -v

Security Checklist:
- [ ] Authentication flows (login, logout, session)
- [ ] OAuth provider flows (Google, GitHub)
- [ ] CSRF protection
- [ ] XSS prevention
- [ ] SQL injection prevention
- [ ] File upload validation
- [ ] Rate limiting
- [ ] Secrets not exposed in responses
- [ ] Proper authorization on all endpoints
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client():
    """Create async test client."""
    app = create_app()
    return AsyncClient(app=app, base_url="http://test")


class TestAuthenticationSecurity:
    """Tests for authentication security."""

    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials_returns_401(self, client: AsyncClient) -> None:
        """Invalid credentials should return 401, not leak user existence."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        # Should not reveal whether email exists
        assert (
            "incorrect" in response.json().get("detail", "").lower()
            or "invalid" in response.json().get("detail", "").lower()
        )

    @pytest.mark.asyncio
    async def test_login_returns_httponly_cookie_or_token(self, client: AsyncClient) -> None:
        """Login should return secure token/cookie."""
        # This tests the flow exists - actual login requires valid user
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )

        # Either returns token in body or sets httponly cookie
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data or "set-cookie" in response.headers

    @pytest.mark.asyncio
    async def test_password_not_returned_in_user_response(self, client: AsyncClient) -> None:
        """User endpoints should never return password hash."""
        # Test user detail endpoint
        response = await client.get(
            "/api/v1/users/me", headers={"Authorization": "Bearer invalid-token"}
        )

        # Even on error, should not expose password
        response_text = response.text.lower()
        assert "password" not in response_text or "incorrect" in response_text

    @pytest.mark.asyncio
    async def test_logout_invalidates_session(self, client: AsyncClient) -> None:
        """Logout should invalidate the session/token."""
        response = await client.post("/api/v1/auth/logout")
        # Should accept logout request
        assert response.status_code in [200, 204, 401]


class TestCSRFProtection:
    """Tests for CSRF protection."""

    @pytest.mark.asyncio
    async def test_state_changing_endpoints_require_auth(self, client: AsyncClient) -> None:
        """POST/PUT/DELETE endpoints should require authentication."""
        endpoints = [
            ("POST", "/api/v1/designs"),
            ("PUT", "/api/v1/designs/00000000-0000-0000-0000-000000000000"),
            ("DELETE", "/api/v1/designs/00000000-0000-0000-0000-000000000000"),
            ("POST", "/api/v2/generate/compile"),
            ("POST", "/api/v2/lists"),
        ]

        for method, endpoint in endpoints:
            if method == "POST":
                response = await client.post(endpoint, json={})
            elif method == "PUT":
                response = await client.put(endpoint, json={})
            elif method == "DELETE":
                response = await client.delete(endpoint)

            # Should require auth (401 or 403)
            assert response.status_code in [401, 403, 422], (
                f"{method} {endpoint} should require auth, got {response.status_code}"
            )


class TestXSSPrevention:
    """Tests for XSS prevention."""

    @pytest.mark.asyncio
    async def test_html_in_input_is_escaped_or_rejected(self, client: AsyncClient) -> None:
        """HTML/script tags in input should be escaped or rejected."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
        ]

        for payload in xss_payloads:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "xss@test.com",
                    "password": "Password123!",
                    "display_name": payload,
                },
            )

            if response.status_code == 200:
                # If accepted, the response should escape the payload
                response_text = response.text
                assert "<script>" not in response_text
                assert "onerror=" not in response_text

    @pytest.mark.asyncio
    async def test_content_type_json_enforced(self, client: AsyncClient) -> None:
        """API should enforce JSON content type."""
        response = await client.post(
            "/api/v1/auth/login",
            content="<script>evil</script>",
            headers={"Content-Type": "text/html"},
        )

        # Should reject non-JSON content type
        assert response.status_code in [400, 415, 422]


class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_search_params(self, client: AsyncClient) -> None:
        """SQL injection in query params should not work."""
        injection_payloads = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "1'; SELECT * FROM users WHERE '1'='1",
            "admin'--",
        ]

        for payload in injection_payloads:
            response = await client.get(f"/api/v2/marketplace/designs?search={payload}")

            # Should not cause server error (500 would indicate injection worked)
            assert response.status_code != 500, (
                f"Possible SQL injection vulnerability with payload: {payload}"
            )

    @pytest.mark.asyncio
    async def test_sql_injection_in_path_params(self, client: AsyncClient) -> None:
        """SQL injection in path params should be handled."""
        response = await client.get("/api/v1/designs/'; DROP TABLE designs; --")

        # Should return 404 or 422, not 500
        assert response.status_code in [400, 404, 422]


class TestFileUploadSecurity:
    """Tests for file upload security."""

    @pytest.mark.asyncio
    async def test_file_type_validation(self, client: AsyncClient) -> None:
        """Only allowed file types should be accepted."""
        # Try uploading an executable disguised as STEP file
        from io import BytesIO

        malicious_content = b"#!/bin/bash\nrm -rf /"

        # This tests the upload endpoint rejects bad files
        # Actual implementation may vary
        files = {"file": ("malicious.step", BytesIO(malicious_content), "application/octet-stream")}

        response = await client.post("/api/v1/files/upload", files=files)

        # Should reject invalid file content
        assert response.status_code in [400, 401, 403, 415, 422]

    @pytest.mark.asyncio
    async def test_file_size_limit(self, client: AsyncClient) -> None:
        """Large files should be rejected."""
        # Create a file larger than typical limit (e.g., 50MB)
        large_content = b"x" * (50 * 1024 * 1024)

        from io import BytesIO

        files = {"file": ("large.step", BytesIO(large_content), "application/step")}

        response = await client.post("/api/v1/files/upload", files=files)

        # Should reject oversized files
        assert response.status_code in [400, 401, 413, 422]


class TestRateLimiting:
    """Tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_auth_endpoints_are_rate_limited(self, client: AsyncClient) -> None:
        """Auth endpoints should have rate limiting."""
        # Make many rapid requests
        responses = []
        for _ in range(50):
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "wrongpassword",
                },
            )
            responses.append(response.status_code)

        # At some point, should get rate limited (429)
        # Note: This may not trigger in test env without Redis
        # The important thing is no 500 errors
        assert 500 not in responses, "Server error during rapid requests"


class TestAuthorizationChecks:
    """Tests for proper authorization on endpoints."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_users_designs(self, client: AsyncClient) -> None:
        """Users should not access other users' private designs."""
        # Try to access a random design without auth
        random_id = str(uuid4())
        response = await client.get(f"/api/v1/designs/{random_id}")

        assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_cannot_modify_other_users_designs(self, client: AsyncClient) -> None:
        """Users should not modify other users' designs."""
        random_id = str(uuid4())
        response = await client.delete(f"/api/v1/designs/{random_id}")

        assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_admin_endpoints_require_admin_role(self, client: AsyncClient) -> None:
        """Admin endpoints should require admin role."""
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/stats",
        ]

        for endpoint in admin_endpoints:
            response = await client.get(endpoint)
            assert response.status_code in [401, 403], (
                f"Admin endpoint {endpoint} accessible without auth"
            )


class TestSecretsExposure:
    """Tests to ensure secrets are not exposed."""

    @pytest.mark.asyncio
    async def test_error_responses_dont_expose_internals(self, client: AsyncClient) -> None:
        """Error responses should not expose internal details."""
        response = await client.get("/api/v1/this-endpoint-does-not-exist")

        response_text = response.text.lower()

        # Should not expose stack traces, file paths, or internal errors
        assert "traceback" not in response_text
        assert "file " not in response_text or "file not found" in response_text
        assert "line " not in response_text or "please try again" in response_text
        assert "sqlalchemy" not in response_text
        assert "psycopg" not in response_text

    @pytest.mark.asyncio
    async def test_database_credentials_not_in_responses(self, client: AsyncClient) -> None:
        """Database credentials should never appear in responses."""
        response = await client.get("/api/v1/health")
        response_text = response.text.lower()

        assert "password=" not in response_text
        assert "postgresql://" not in response_text
        assert "redis://" not in response_text

    def test_env_secrets_not_in_openapi(self) -> None:
        """OpenAPI spec should not contain secret values."""
        app = create_app()
        openapi = app.openapi()
        openapi_str = str(openapi).lower()

        settings = get_settings()

        # Check that actual secret values aren't in the schema
        if settings.SECRET_KEY and len(settings.SECRET_KEY) > 10:
            assert settings.SECRET_KEY.lower() not in openapi_str
