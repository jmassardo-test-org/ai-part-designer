"""
Tests for user-specific API endpoints.
"""

import csv
import json
from datetime import UTC, datetime, timedelta
from io import StringIO
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


@pytest.mark.asyncio
class TestUserAuditLogsExportCSV:
    """Tests for GET /api/v1/users/me/audit-logs/export/csv endpoint."""

    async def test_export_audit_logs_csv_requires_authentication(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that CSV export requires authentication."""
        response = await client.get("/api/v1/users/me/audit-logs/export/csv")
        assert response.status_code == 401

    async def test_export_audit_logs_csv_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test CSV export when user has no logs."""
        response = await client.get(
            "/api/v1/users/me/audit-logs/export/csv",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "Content-Disposition" in response.headers
        assert "audit_logs.csv" in response.headers["Content-Disposition"]

        # Parse CSV
        csv_reader = csv.reader(StringIO(response.text))
        rows = list(csv_reader)

        # Should have header but no data rows
        assert len(rows) == 1  # Only header
        assert rows[0][0] == "ID"
        assert rows[0][1] == "Timestamp"
        assert rows[0][2] == "Action"

    async def test_export_audit_logs_csv_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test CSV export with audit log data."""
        now = datetime.now(UTC)

        # Create test audit logs
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
                "actor_type": "user",
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
                "actor_type": "user",
                "created_at": now - timedelta(hours=1),
            },
            {
                "user_id": test_user.id,
                "action": "delete",
                "resource_type": "design",
                "resource_id": uuid4(),
                "status": "failure",
                "error_message": "Permission denied",
                "context": {},
                "ip_address": "192.168.1.2",
                "user_agent": "Chrome/100",
                "actor_type": "user",
                "created_at": now,
            },
        ]

        for log_data in logs_data:
            audit_log = AuditLog(**log_data)
            db.add(audit_log)
        await db.commit()

        # Export as CSV
        response = await client.get(
            "/api/v1/users/me/audit-logs/export/csv",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        # Parse CSV
        csv_reader = csv.reader(StringIO(response.text))
        rows = list(csv_reader)

        # Should have header + 3 data rows
        assert len(rows) == 4

        # Check header
        header = rows[0]
        assert header == [
            "ID",
            "Timestamp",
            "Action",
            "Resource Type",
            "Resource ID",
            "Actor Type",
            "Status",
            "Error Message",
            "IP Address",
            "User Agent",
            "Context",
        ]

        # Check data rows (most recent first)
        row1 = rows[1]
        assert row1[2] == "delete"  # Action
        assert row1[3] == "design"  # Resource Type
        assert row1[5] == "user"  # Actor Type
        assert row1[6] == "failure"  # Status
        assert row1[7] == "Permission denied"  # Error Message
        assert row1[8] == "192.168.1.2"  # IP Address

        row2 = rows[2]
        assert row2[2] == "create"
        assert row2[6] == "success"

        row3 = rows[3]
        assert row3[2] == "login"
        assert row3[6] == "success"

        # Check that context is JSON serialized
        context1 = json.loads(row1[10])
        assert isinstance(context1, dict)

        context2 = json.loads(row2[10])
        assert context2["name"] == "Test Design"

    async def test_export_audit_logs_csv_with_filters(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test CSV export with filters applied."""
        now = datetime.now(UTC)

        # Create diverse audit logs
        for action in ["login", "create", "update", "delete"]:
            audit_log = AuditLog(
                user_id=test_user.id,
                action=action,
                resource_type="design" if action in ["create", "update"] else "user",
                status="success",
                context={},
                created_at=now - timedelta(hours=1) if action == "login" else now,
            )
            db.add(audit_log)
        await db.commit()

        # Export only design-related logs
        response = await client.get(
            "/api/v1/users/me/audit-logs/export/csv?resource_type=design",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Parse CSV
        csv_reader = csv.reader(StringIO(response.text))
        rows = list(csv_reader)

        # Should have header + 2 data rows (create and update)
        assert len(rows) == 3
        assert all(row[3] == "design" for row in rows[1:])

    async def test_export_audit_logs_csv_with_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test CSV export with date range filters."""
        now = datetime.now(UTC)

        # Create logs at different times
        times = [
            now - timedelta(days=5),
            now - timedelta(days=3),
            now - timedelta(days=1),
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

        # Export logs from last 2 days
        start_date = (now - timedelta(days=2)).isoformat()
        response = await client.get(
            f"/api/v1/users/me/audit-logs/export/csv?start_date={start_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Verify filename includes date
        assert "from_" in response.headers["Content-Disposition"]

        # Parse CSV
        csv_reader = csv.reader(StringIO(response.text))
        rows = list(csv_reader)

        # Should have header + 1 data row (only the log from 1 day ago)
        assert len(rows) == 2

    async def test_export_audit_logs_csv_filename_with_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test CSV filename includes date range when provided."""
        now = datetime.now(UTC)

        # Create a log
        audit_log = AuditLog(
            user_id=test_user.id,
            action="login",
            resource_type="user",
            status="success",
            context={},
            created_at=now,
        )
        db.add(audit_log)
        await db.commit()

        # Export with date range
        start_date = (now - timedelta(days=7)).isoformat()
        end_date = now.isoformat()
        response = await client.get(
            f"/api/v1/users/me/audit-logs/export/csv?start_date={start_date}&end_date={end_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Check filename includes both dates
        content_disposition = response.headers["Content-Disposition"]
        assert "from_" in content_disposition
        assert "to_" in content_disposition
        assert ".csv" in content_disposition


@pytest.mark.asyncio
class TestUserAuditLogsExportJSON:
    """Tests for GET /api/v1/users/me/audit-logs/export/json endpoint."""

    async def test_export_audit_logs_json_requires_authentication(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that JSON export requires authentication."""
        response = await client.get("/api/v1/users/me/audit-logs/export/json")
        assert response.status_code == 401

    async def test_export_audit_logs_json_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test JSON export when user has no logs."""
        response = await client.get(
            "/api/v1/users/me/audit-logs/export/json",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "Content-Disposition" in response.headers
        assert "audit_logs.json" in response.headers["Content-Disposition"]

        # Parse JSON
        data = response.json()

        assert "export_metadata" in data
        assert "audit_logs" in data
        assert data["audit_logs"] == []
        assert data["export_metadata"]["total_records"] == 0
        assert "exported_at" in data["export_metadata"]
        assert "user_id" in data["export_metadata"]
        assert "filters" in data["export_metadata"]

    async def test_export_audit_logs_json_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test JSON export with audit log data."""
        now = datetime.now(UTC)

        # Create test audit logs
        test_resource_id = uuid4()
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
                "actor_type": "user",
                "created_at": now - timedelta(hours=1),
            },
            {
                "user_id": test_user.id,
                "action": "create",
                "resource_type": "design",
                "resource_id": test_resource_id,
                "status": "success",
                "context": {"name": "Test Design", "version": 1},
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "actor_type": "user",
                "created_at": now,
            },
        ]

        for log_data in logs_data:
            audit_log = AuditLog(**log_data)
            db.add(audit_log)
        await db.commit()

        # Export as JSON
        response = await client.get(
            "/api/v1/users/me/audit-logs/export/json",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        # Parse JSON
        data = response.json()

        # Check metadata
        assert data["export_metadata"]["total_records"] == 2
        assert data["export_metadata"]["user_id"] == str(test_user.id)

        # Check audit logs
        logs = data["audit_logs"]
        assert len(logs) == 2

        # Check first log (most recent)
        log1 = logs[0]
        assert log1["action"] == "create"
        assert log1["resource_type"] == "design"
        assert log1["resource_id"] == str(test_resource_id)
        assert log1["status"] == "success"
        assert log1["context"]["name"] == "Test Design"
        assert log1["context"]["version"] == 1
        assert log1["ip_address"] == "192.168.1.1"
        assert log1["actor_type"] == "user"

        # Check second log
        log2 = logs[1]
        assert log2["action"] == "login"
        assert log2["status"] == "success"
        assert log2["context"]["method"] == "password"

    async def test_export_audit_logs_json_with_filters(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test JSON export with filters applied."""
        now = datetime.now(UTC)

        # Create diverse audit logs
        for action in ["login", "create", "update", "delete"]:
            audit_log = AuditLog(
                user_id=test_user.id,
                action=action,
                resource_type="design" if action in ["create", "update"] else "user",
                status="success" if action != "delete" else "failure",
                error_message="Test error" if action == "delete" else None,
                context={},
                created_at=now,
            )
            db.add(audit_log)
        await db.commit()

        # Export only failed actions
        response = await client.get(
            "/api/v1/users/me/audit-logs/export/json?status=failure",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Parse JSON
        data = response.json()

        # Check filters in metadata
        assert data["export_metadata"]["filters"]["status"] == "failure"
        assert data["export_metadata"]["total_records"] == 1

        # Check data
        logs = data["audit_logs"]
        assert len(logs) == 1
        assert logs[0]["action"] == "delete"
        assert logs[0]["status"] == "failure"
        assert logs[0]["error_message"] == "Test error"

    async def test_export_audit_logs_json_with_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test JSON export with date range filters."""
        now = datetime.now(UTC)

        # Create logs at different times
        times = [
            now - timedelta(days=10),
            now - timedelta(days=5),
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

        # Export logs from specific date range
        start_date = (now - timedelta(days=6)).isoformat()
        end_date = (now - timedelta(days=2)).isoformat()
        response = await client.get(
            f"/api/v1/users/me/audit-logs/export/json?start_date={start_date}&end_date={end_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Parse JSON
        data = response.json()

        # Check filters in metadata
        assert data["export_metadata"]["filters"]["start_date"] is not None
        assert data["export_metadata"]["filters"]["end_date"] is not None
        assert data["export_metadata"]["total_records"] == 1

        # Should only include the log from 5 days ago
        logs = data["audit_logs"]
        assert len(logs) == 1

    async def test_export_audit_logs_json_null_values(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test JSON export handles null values correctly."""
        now = datetime.now(UTC)

        # Create audit log with minimal data (many nulls)
        audit_log = AuditLog(
            user_id=test_user.id,
            action="test_action",
            resource_type="test_resource",
            resource_id=None,  # Null
            status="success",
            error_message=None,  # Null
            context={},
            ip_address=None,  # Null
            user_agent=None,  # Null
            created_at=now,
        )
        db.add(audit_log)
        await db.commit()

        # Export as JSON
        response = await client.get(
            "/api/v1/users/me/audit-logs/export/json",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Parse JSON
        data = response.json()
        logs = data["audit_logs"]
        assert len(logs) == 1

        log = logs[0]
        assert log["resource_id"] is None
        assert log["error_message"] is None
        assert log["ip_address"] is None
        assert log["user_agent"] is None
        assert log["context"] == {}

    async def test_export_audit_logs_json_filename_with_date_range(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test JSON filename includes date range when provided."""
        now = datetime.now(UTC)

        # Create a log
        audit_log = AuditLog(
            user_id=test_user.id,
            action="login",
            resource_type="user",
            status="success",
            context={},
            created_at=now,
        )
        db.add(audit_log)
        await db.commit()

        # Export with date range
        start_date = (now - timedelta(days=30)).isoformat()
        end_date = now.isoformat()
        response = await client.get(
            f"/api/v1/users/me/audit-logs/export/json?start_date={start_date}&end_date={end_date}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Check filename includes both dates
        content_disposition = response.headers["Content-Disposition"]
        assert "from_" in content_disposition
        assert "to_" in content_disposition
        assert ".json" in content_disposition


@pytest.mark.asyncio
class TestUserAuditLogsExportRateLimiting:
    """Tests for rate limiting on audit log export endpoints."""

    async def test_export_csv_respects_rate_limits(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test that CSV export is rate limited."""
        # Create a test log
        audit_log = AuditLog(
            user_id=test_user.id,
            action="login",
            resource_type="user",
            status="success",
            context={},
            created_at=datetime.now(UTC),
        )
        db.add(audit_log)
        await db.commit()

        # Make multiple requests to trigger rate limit
        # Free tier has 30/hour for exports
        success_count = 0
        rate_limited = False

        for _ in range(35):
            response = await client.get(
                "/api/v1/users/me/audit-logs/export/csv",
                headers=auth_headers,
            )
            if response.status_code == 200:
                success_count += 1
                # Check rate limit headers are present
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
            elif response.status_code == 429:
                rate_limited = True
                # Check retry-after header
                assert "Retry-After" in response.headers
                break

        # Should eventually hit rate limit
        assert rate_limited or success_count <= 30

    async def test_export_json_respects_rate_limits(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: AsyncSession,
    ) -> None:
        """Test that JSON export is rate limited."""
        # Create a test log
        audit_log = AuditLog(
            user_id=test_user.id,
            action="login",
            resource_type="user",
            status="success",
            context={},
            created_at=datetime.now(UTC),
        )
        db.add(audit_log)
        await db.commit()

        # Make multiple requests to trigger rate limit
        success_count = 0
        rate_limited = False

        for _ in range(35):
            response = await client.get(
                "/api/v1/users/me/audit-logs/export/json",
                headers=auth_headers,
            )
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited = True
                break

        # Should eventually hit rate limit
        assert rate_limited or success_count <= 30
