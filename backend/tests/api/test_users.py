"""
Tests for user-specific API endpoints.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User


@pytest.mark.asyncio
class TestUserAuditLogs:
    """Tests for GET /api/v1/users/me/audit-logs endpoint."""

    async def test_get_user_audit_logs_requires_authentication(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that the endpoint requires authentication."""
        response = await client.get("/api/v1/users/me/audit-logs")
        assert response.status_code == 401

    async def test_get_user_audit_logs_empty_list(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test getting audit logs when user has none."""
        response = await client.get(
            "/api/v1/users/me/audit-logs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50  # default limit

    async def test_get_user_audit_logs_with_logs(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test getting audit logs when user has some."""
        # Create some audit logs for the test user
        now = datetime.now(UTC)
        logs_data = [
            {
                "user_id": test_user.id,
                "action": "login",
                "resource_type": "user",
                "resource_id": test_user.id,
                "status": "success",
                "context": {"method": "password"},
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "created_at": now - timedelta(hours=2),
            },
            {
                "user_id": test_user.id,
                "action": "create",
                "resource_type": "design",
                "resource_id": uuid4(),
                "status": "success",
                "context": {"name": "Test Design"},
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "created_at": now - timedelta(hours=1),
            },
            {
                "user_id": test_user.id,
                "action": "update",
                "resource_type": "user",
                "resource_id": test_user.id,
                "status": "success",
                "context": {"field": "display_name"},
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "created_at": now,
            },
        ]

        for log_data in logs_data:
            audit_log = AuditLog(**log_data)
            db.add(audit_log)
        await db.commit()

        # Get audit logs
        response = await client.get(
            "/api/v1/users/me/audit-logs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 3
        assert data["total"] == 3

        # Verify logs are ordered by created_at desc (most recent first)
        assert data["logs"][0]["action"] == "update"
        assert data["logs"][1]["action"] == "create"
        assert data["logs"][2]["action"] == "login"

        # Verify log structure
        log = data["logs"][0]
        assert "id" in log
        assert log["action"] == "update"
        assert log["resource_type"] == "user"
        assert log["status"] == "success"
        assert log["context"]["field"] == "display_name"
        assert log["ip_address"] == "192.168.1.1"

    async def test_get_user_audit_logs_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test pagination of audit logs."""
        # Create 10 audit logs
        now = datetime.now(UTC)
        for i in range(10):
            audit_log = AuditLog(
                user_id=test_user.id,
                action="login",
                resource_type="user",
                status="success",
                context={},
                created_at=now - timedelta(hours=i),
            )
            db.add(audit_log)
        await db.commit()

        # Get first page (5 items)
        response = await client.get(
            "/api/v1/users/me/audit-logs?skip=0&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 5
        assert data["total"] == 10
        assert data["skip"] == 0
        assert data["limit"] == 5

        # Get second page
        response = await client.get(
            "/api/v1/users/me/audit-logs?skip=5&limit=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 5
        assert data["total"] == 10
        assert data["skip"] == 5
        assert data["limit"] == 5

    async def test_get_user_audit_logs_filter_by_action(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test filtering audit logs by action type."""
        now = datetime.now(UTC)

        # Create logs with different actions
        for action in ["login", "create", "update", "delete", "login"]:
            audit_log = AuditLog(
                user_id=test_user.id,
                action=action,
                resource_type="user",
                status="success",
                context={},
                created_at=now,
            )
            db.add(audit_log)
        await db.commit()

        # Filter by login action
        response = await client.get(
            "/api/v1/users/me/audit-logs?action=login",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 2
        assert data["total"] == 2
        assert all(log["action"] == "login" for log in data["logs"])

        # Filter by create action
        response = await client.get(
            "/api/v1/users/me/audit-logs?action=create",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        assert data["total"] == 1
        assert data["logs"][0]["action"] == "create"

    async def test_get_user_audit_logs_filter_by_resource_type(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test filtering audit logs by resource type."""
        now = datetime.now(UTC)

        # Create logs with different resource types
        for resource_type in ["user", "design", "project", "design"]:
            audit_log = AuditLog(
                user_id=test_user.id,
                action="create",
                resource_type=resource_type,
                status="success",
                context={},
                created_at=now,
            )
            db.add(audit_log)
        await db.commit()

        # Filter by design resource type
        response = await client.get(
            "/api/v1/users/me/audit-logs?resource_type=design",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 2
        assert data["total"] == 2
        assert all(log["resource_type"] == "design" for log in data["logs"])

    async def test_get_user_audit_logs_filter_by_status(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test filtering audit logs by status."""
        now = datetime.now(UTC)

        # Create logs with different statuses
        for status in ["success", "failure", "error", "success"]:
            audit_log = AuditLog(
                user_id=test_user.id,
                action="login",
                resource_type="user",
                status=status,
                error_message="Test error" if status != "success" else None,
                context={},
                created_at=now,
            )
            db.add(audit_log)
        await db.commit()

        # Filter by failure status
        response = await client.get(
            "/api/v1/users/me/audit-logs?status=failure",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        assert data["total"] == 1
        assert data["logs"][0]["status"] == "failure"
        assert data["logs"][0]["error_message"] == "Test error"

        # Filter by success status
        response = await client.get(
            "/api/v1/users/me/audit-logs?status=success",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 2
        assert data["total"] == 2

    async def test_get_user_audit_logs_filter_by_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test filtering audit logs by date range."""
        now = datetime.now(UTC)

        # Create logs at different times
        times = [
            now - timedelta(days=5),
            now - timedelta(days=3),
            now - timedelta(days=1),
            now,
        ]

        for time in times:
            audit_log = AuditLog(
                user_id=test_user.id,
                action="login",
                resource_type="user",
                status="success",
                context={},
                created_at=time,
            )
            db.add(audit_log)
        await db.commit()

        # Filter by date range (last 2 days)
        start_date = (now - timedelta(days=2)).isoformat()
        response = await client.get(
            f"/api/v1/users/me/audit-logs?start_date={start_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 2
        assert data["total"] == 2

        # Filter by end date
        end_date = (now - timedelta(days=2)).isoformat()
        response = await client.get(
            f"/api/v1/users/me/audit-logs?end_date={end_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 2
        assert data["total"] == 2

        # Filter by date range
        start_date = (now - timedelta(days=4)).isoformat()
        end_date = (now - timedelta(days=2)).isoformat()
        response = await client.get(
            f"/api/v1/users/me/audit-logs?start_date={start_date}&end_date={end_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        assert data["total"] == 1

    async def test_get_user_audit_logs_combined_filters(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test combining multiple filters."""
        now = datetime.now(UTC)

        # Create diverse audit logs
        logs_data = [
            {
                "action": "login",
                "resource_type": "user",
                "status": "success",
                "created_at": now - timedelta(days=1),
            },
            {
                "action": "login",
                "resource_type": "user",
                "status": "failure",
                "created_at": now - timedelta(days=1),
            },
            {
                "action": "create",
                "resource_type": "design",
                "status": "success",
                "created_at": now,
            },
            {
                "action": "update",
                "resource_type": "design",
                "status": "success",
                "created_at": now,
            },
        ]

        for log_data in logs_data:
            audit_log = AuditLog(
                user_id=test_user.id,
                context={},
                **log_data,
            )
            db.add(audit_log)
        await db.commit()

        # Filter by action and status
        response = await client.get(
            "/api/v1/users/me/audit-logs?action=login&status=success",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        assert data["total"] == 1
        assert data["logs"][0]["action"] == "login"
        assert data["logs"][0]["status"] == "success"

        # Filter by resource_type and date
        start_date = (now - timedelta(hours=1)).isoformat()
        response = await client.get(
            f"/api/v1/users/me/audit-logs?resource_type=design&start_date={start_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 2
        assert data["total"] == 2
        assert all(log["resource_type"] == "design" for log in data["logs"])

    async def test_get_user_audit_logs_only_sees_own_logs(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test that users only see their own audit logs."""
        # Create another user
        other_user = User(
            email="other@example.com",
            hashed_password="hashed",
            display_name="Other User",
            is_active=True,
        )
        db.add(other_user)
        await db.commit()
        await db.refresh(other_user)

        now = datetime.now(UTC)

        # Create audit logs for both users
        for user_id in [test_user.id, other_user.id]:
            audit_log = AuditLog(
                user_id=user_id,
                action="login",
                resource_type="user",
                status="success",
                context={},
                created_at=now,
            )
            db.add(audit_log)
        await db.commit()

        # Get audit logs for test_user
        response = await client.get(
            "/api/v1/users/me/audit-logs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1
        assert data["total"] == 1
        assert str(data["logs"][0]["id"]) is not None

    async def test_get_user_audit_logs_pagination_validation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test pagination parameter validation."""
        # Test negative skip
        response = await client.get(
            "/api/v1/users/me/audit-logs?skip=-1",
            headers=auth_headers,
        )
        assert response.status_code == 422

        # Test limit too high
        response = await client.get(
            "/api/v1/users/me/audit-logs?limit=101",
            headers=auth_headers,
        )
        assert response.status_code == 422

        # Test limit too low
        response = await client.get(
            "/api/v1/users/me/audit-logs?limit=0",
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_get_user_audit_logs_with_context_data(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test that context data is returned correctly."""
        now = datetime.now(UTC)

        # Create audit log with complex context
        complex_context = {
            "changes": {
                "name": {"old": "Old Name", "new": "New Name"},
                "description": {"old": "Old Desc", "new": "New Desc"},
            },
            "request_id": "req_123",
            "session_id": "sess_456",
        }

        audit_log = AuditLog(
            user_id=test_user.id,
            action="update",
            resource_type="design",
            resource_id=uuid4(),
            status="success",
            context=complex_context,
            created_at=now,
        )
        db.add(audit_log)
        await db.commit()

        # Get audit logs
        response = await client.get(
            "/api/v1/users/me/audit-logs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["logs"]) == 1

        # Verify context is preserved
        log = data["logs"][0]
        assert log["context"]["changes"]["name"]["old"] == "Old Name"
        assert log["context"]["changes"]["name"]["new"] == "New Name"
        assert log["context"]["request_id"] == "req_123"
