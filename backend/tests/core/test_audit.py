"""
Tests for audit logging decorators and utilities.

Tests the audit_log decorator, context extraction, and failure logging.
"""

from unittest.mock import MagicMock, Mock
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import _extract_resource_id, audit_failure, audit_log
from app.models.audit import AuditActions, AuditLog
from app.models.user import User

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_user() -> User:
    """Create a mock user."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_db() -> AsyncSession:
    """Create a mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.add = Mock()
    db.flush = Mock(return_value=None)
    return db


@pytest.fixture
def mock_request() -> Request:
    """Create a mock request."""
    request = Mock(spec=Request)
    request.headers = {
        "User-Agent": "TestClient/1.0",
        "X-Forwarded-For": "192.168.1.1",
    }
    request.client = Mock()
    request.client.host = "192.168.1.1"
    request.state = Mock()
    request.state.request_id = "test-request-id"
    return request


# =============================================================================
# Resource ID Extraction Tests
# =============================================================================


class TestExtractResourceId:
    """Tests for _extract_resource_id function."""

    def test_extract_from_kwargs_direct(self) -> None:
        """Test extracting UUID directly from kwargs."""
        design_id = uuid4()
        kwargs = {"design_id": design_id, "name": "Test"}

        result = _extract_resource_id("design_id", None, kwargs)

        assert result == design_id

    def test_extract_from_kwargs_string(self) -> None:
        """Test extracting UUID string from kwargs and converting."""
        design_id = uuid4()
        kwargs = {"design_id": str(design_id)}

        result = _extract_resource_id("design_id", None, kwargs)

        assert result == design_id

    def test_extract_from_response_attribute(self) -> None:
        """Test extracting ID from response object attribute."""
        design_id = uuid4()
        response = Mock()
        response.id = design_id

        result = _extract_resource_id("response.id", response, {})

        assert result == design_id

    def test_extract_from_response_dict(self) -> None:
        """Test extracting ID from response dict."""
        design_id = uuid4()
        response = {"id": design_id, "name": "Test"}

        result = _extract_resource_id("response.id", response, {})

        assert result == design_id

    def test_extract_nested_path(self) -> None:
        """Test extracting ID from nested path."""
        design_id = uuid4()
        response = Mock()
        response.data = Mock()
        response.data.id = design_id

        result = _extract_resource_id("response.data.id", response, {})

        assert result == design_id

    def test_extract_returns_none_when_not_found(self) -> None:
        """Test that extraction returns None when path doesn't exist."""
        result = _extract_resource_id("missing_param", None, {})

        assert result is None

    def test_extract_returns_none_for_invalid_uuid_string(self) -> None:
        """Test that invalid UUID strings return None."""
        kwargs = {"id": "not-a-uuid"}

        result = _extract_resource_id("id", None, kwargs)

        assert result is None


# =============================================================================
# Audit Log Decorator Tests
# =============================================================================


class TestAuditLogDecorator:
    """Tests for audit_log decorator."""

    @pytest.mark.asyncio
    async def test_decorator_logs_successful_action(
        self,
        mock_user: User,
        mock_db: AsyncSession,
        mock_request: Request,
    ) -> None:
        """Test that decorator logs successful action to database."""

        @audit_log(
            action=AuditActions.CREATE,
            resource_type="design",
        )
        async def create_design(
            name: str,
            current_user: User,
            db: AsyncSession,
            request: Request,
        ) -> dict[str, str]:
            return {"id": str(uuid4()), "name": name}

        # Call decorated function
        result = await create_design(
            name="Test Design",
            current_user=mock_user,
            db=mock_db,
            request=mock_request,
        )

        # Verify function executed
        assert result["name"] == "Test Design"

        # Verify audit log was created
        mock_db.add.assert_called_once()
        audit_entry = mock_db.add.call_args[0][0]
        assert isinstance(audit_entry, AuditLog)
        assert audit_entry.action == AuditActions.CREATE
        assert audit_entry.resource_type == "design"
        assert audit_entry.user_id == mock_user.id
        assert audit_entry.status == "success"

    @pytest.mark.asyncio
    async def test_decorator_extracts_resource_id_from_response(
        self,
        mock_user: User,
        mock_db: AsyncSession,
        mock_request: Request,
    ) -> None:
        """Test that decorator extracts resource ID from response."""
        design_id = uuid4()

        @audit_log(
            action=AuditActions.CREATE,
            resource_type="design",
            resource_id_param="response.id",
        )
        async def create_design(
            current_user: User,
            db: AsyncSession,
            request: Request,
        ) -> dict[str, UUID]:
            return {"id": design_id}

        await create_design(
            current_user=mock_user,
            db=mock_db,
            request=mock_request,
        )

        # Verify resource ID was captured
        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.resource_id == design_id

    @pytest.mark.asyncio
    async def test_decorator_extracts_resource_id_from_kwargs(
        self,
        mock_user: User,
        mock_db: AsyncSession,
        mock_request: Request,
    ) -> None:
        """Test that decorator extracts resource ID from kwargs."""
        design_id = uuid4()

        @audit_log(
            action=AuditActions.UPDATE,
            resource_type="design",
            resource_id_param="design_id",
        )
        async def update_design(
            design_id: UUID,
            current_user: User,
            db: AsyncSession,
            request: Request,
        ) -> dict[str, str]:
            return {"status": "updated"}

        await update_design(
            design_id=design_id,
            current_user=mock_user,
            db=mock_db,
            request=mock_request,
        )

        # Verify resource ID was captured
        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.resource_id == design_id

    @pytest.mark.asyncio
    async def test_decorator_uses_context_builder(
        self,
        mock_user: User,
        mock_db: AsyncSession,
        mock_request: Request,
    ) -> None:
        """Test that decorator uses context_builder to add custom context."""

        def build_context(**kwargs: dict[str, str]) -> dict[str, str]:
            return {
                "design_name": kwargs["name"],
                "project_id": kwargs["project_id"],
            }

        @audit_log(
            action=AuditActions.CREATE,
            resource_type="design",
            context_builder=build_context,
        )
        async def create_design(
            name: str,
            project_id: str,
            current_user: User,
            db: AsyncSession,
            request: Request,
        ) -> dict[str, str]:
            return {"id": str(uuid4())}

        await create_design(
            name="Test Design",
            project_id="proj-123",
            current_user=mock_user,
            db=mock_db,
            request=mock_request,
        )

        # Verify context was added
        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.context["design_name"] == "Test Design"
        assert audit_entry.context["project_id"] == "proj-123"

    @pytest.mark.asyncio
    async def test_decorator_captures_request_metadata(
        self,
        mock_user: User,
        mock_db: AsyncSession,
        mock_request: Request,
    ) -> None:
        """Test that decorator captures IP address and user agent."""

        @audit_log(
            action=AuditActions.CREATE,
            resource_type="design",
        )
        async def create_design(
            current_user: User,
            db: AsyncSession,
            request: Request,
        ) -> dict[str, str]:
            return {"id": str(uuid4())}

        await create_design(
            current_user=mock_user,
            db=mock_db,
            request=mock_request,
        )

        # Verify request metadata was captured
        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.ip_address == "192.168.1.1"
        assert audit_entry.user_agent == "TestClient/1.0"
        assert audit_entry.context["request_id"] == "test-request-id"

    @pytest.mark.asyncio
    async def test_decorator_handles_x_forwarded_for_multiple_ips(
        self,
        mock_user: User,
        mock_db: AsyncSession,
    ) -> None:
        """Test that decorator uses first IP from X-Forwarded-For."""
        request = Mock(spec=Request)
        request.headers = {
            "X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3",
        }
        request.state = Mock()
        request.state.request_id = "test-id"

        @audit_log(
            action=AuditActions.CREATE,
            resource_type="design",
        )
        async def create_design(
            current_user: User,
            db: AsyncSession,
            request: Request,
        ) -> dict[str, str]:
            return {"id": str(uuid4())}

        await create_design(
            current_user=mock_user,
            db=mock_db,
            request=request,
        )

        # Verify first IP was used
        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.ip_address == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_decorator_skips_logging_without_db(
        self,
        mock_user: User,
        mock_request: Request,
    ) -> None:
        """Test that decorator skips logging when db is not provided."""

        @audit_log(
            action=AuditActions.CREATE,
            resource_type="design",
        )
        async def create_design(
            current_user: User,
            request: Request,
        ) -> dict[str, str]:
            return {"id": str(uuid4())}

        # Should not raise error even without db
        result = await create_design(
            current_user=mock_user,
            request=mock_request,
        )

        assert result["id"]  # Function still executes

    @pytest.mark.asyncio
    async def test_decorator_continues_on_audit_error(
        self,
        mock_user: User,
        mock_request: Request,
    ) -> None:
        """Test that decorator doesn't fail request if audit logging fails."""
        mock_db = MagicMock(spec=AsyncSession)
        mock_db.add.side_effect = Exception("Database error")

        @audit_log(
            action=AuditActions.CREATE,
            resource_type="design",
        )
        async def create_design(
            current_user: User,
            db: AsyncSession,
            request: Request,
        ) -> dict[str, str]:
            return {"id": str(uuid4()), "status": "created"}

        # Should not raise even though audit logging fails
        result = await create_design(
            current_user=mock_user,
            db=mock_db,
            request=mock_request,
        )

        assert result["status"] == "created"


# =============================================================================
# Audit Failure Function Tests
# =============================================================================


class TestAuditFailure:
    """Tests for audit_failure function."""

    def test_audit_failure_creates_failure_log(
        self,
        mock_user: User,
        mock_db: AsyncSession,
        mock_request: Request,
    ) -> None:
        """Test that audit_failure creates a failure audit log."""
        design_id = uuid4()

        audit_failure(
            action=AuditActions.DELETE,
            resource_type="design",
            error_message="Permission denied",
            user=mock_user,
            db=mock_db,
            resource_id=design_id,
            request=mock_request,
        )

        # Verify failure log was created
        mock_db.add.assert_called_once()
        audit_entry = mock_db.add.call_args[0][0]
        assert isinstance(audit_entry, AuditLog)
        assert audit_entry.action == AuditActions.DELETE
        assert audit_entry.resource_type == "design"
        assert audit_entry.resource_id == design_id
        assert audit_entry.user_id == mock_user.id
        assert audit_entry.status == "failure"
        assert audit_entry.error_message == "Permission denied"

    def test_audit_failure_works_without_user(
        self,
        mock_db: AsyncSession,
    ) -> None:
        """Test that audit_failure works for unauthenticated attempts."""
        audit_failure(
            action=AuditActions.CREATE,
            resource_type="design",
            error_message="Authentication required",
            user=None,
            db=mock_db,
        )

        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.user_id is None
        assert audit_entry.status == "failure"

    def test_audit_failure_includes_custom_context(
        self,
        mock_user: User,
        mock_db: AsyncSession,
    ) -> None:
        """Test that audit_failure includes custom context."""
        context = {
            "attempted_action": "delete_all",
            "reason": "insufficient_permissions",
        }

        audit_failure(
            action=AuditActions.DELETE,
            resource_type="design",
            error_message="Bulk delete not allowed",
            user=mock_user,
            db=mock_db,
            context=context,
        )

        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.context["attempted_action"] == "delete_all"
        assert audit_entry.context["reason"] == "insufficient_permissions"

    def test_audit_failure_extracts_ip_from_request(
        self,
        mock_user: User,
        mock_db: AsyncSession,
        mock_request: Request,
    ) -> None:
        """Test that audit_failure extracts IP address from request."""
        audit_failure(
            action=AuditActions.UPDATE,
            resource_type="design",
            error_message="Update failed",
            user=mock_user,
            db=mock_db,
            request=mock_request,
        )

        audit_entry = mock_db.add.call_args[0][0]
        assert audit_entry.ip_address == "192.168.1.1"
        assert audit_entry.user_agent == "TestClient/1.0"
