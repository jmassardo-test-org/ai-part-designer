"""
Tests for admin API Batches 5-6 endpoints.

Tests the following new admin endpoints:

Batch 5 - US-10.12 Files/Storage:
  - GET /files/{file_id} - File detail + download URL
  - GET /files/flagged - Flagged files
  - GET /files/failed-uploads - Failed uploads
  - POST /users/{user_id}/storage-quota - Adjust user storage quota
  - GET /storage/top-users - Top storage consumers
  - GET /storage/analytics - Storage analytics
  - POST /storage/garbage-collect - Force garbage collection

Batch 5 - US-10.13 Audit/Security:
  - GET /audit-logs/export - Export audit logs as CSV
  - GET /security/events - Security event log
  - GET /security/failed-logins - Failed login attempts
  - GET /security/blocked-ips - List blocked IPs
  - POST /security/blocked-ips - Block an IP
  - DELETE /security/blocked-ips/{ip} - Unblock an IP
  - GET /security/sessions - Active sessions
  - DELETE /security/sessions/{session_id} - Terminate session
  - GET /security/dashboard - Security overview dashboard

Batch 6 - US-10.14 System Health:
  - GET /system/services/{service_name} - Individual service details
  - GET /system/performance - Performance metrics
  - GET /system/resources - Resource utilization
  - GET /system/errors - Recent error logs
  - GET /system/ai-providers - AI provider status
  - GET /system/config - Sanitized system config
  - POST /system/health-check - Manual health check trigger
  - GET /system/uptime - Uptime history
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.file import File as FileModel
from app.models.moderation import ModerationLog
from app.models.user import User
from tests.factories import Counter, UserFactory


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_counters():
    """Reset factory counters before each test."""
    Counter.reset()


@pytest.fixture(autouse=True)
def reset_blocked_ips():
    """Reset in-memory blocked IPs store before each test."""
    from app.api.v1.admin import _blocked_ips

    _blocked_ips.clear()
    yield
    _blocked_ips.clear()


# =============================================================================
# Helper Factories
# =============================================================================


async def _create_file(
    db: AsyncSession,
    user_id: UUID,
    filename: str = "test_file.stl",
    original_filename: str = "Test File.stl",
    mime_type: str = "model/stl",
    size_bytes: int = 1024 * 1024,
    file_type: str = "cad",
    status: str = "ready",
    is_deleted: bool = False,
    storage_bucket: str = "uploads",
    storage_path: str = "users/test/test_file.stl",
) -> FileModel:
    """Create a FileModel instance for testing."""
    f = FileModel(
        id=uuid4(),
        user_id=user_id,
        filename=filename,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        file_type=file_type,
        status=status,
        is_deleted=is_deleted,
        storage_bucket=storage_bucket,
        storage_path=storage_path,
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


async def _create_audit_log(
    db: AsyncSession,
    action: str = "test_action",
    resource_type: str = "test",
    user_id: UUID | None = None,
    actor_type: str = "user",
    status: str = "success",
    error_message: str | None = None,
    ip_address: str | None = None,
    context: dict | None = None,
) -> AuditLog:
    """Create an AuditLog entry for testing."""
    log = AuditLog(
        id=uuid4(),
        user_id=user_id,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        status=status,
        error_message=error_message,
        ip_address=ip_address,
        context=context or {},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def _create_moderation_log(
    db: AsyncSession,
    user_id: UUID,
    content_type: str = "file",
    decision: str = "pending",
    reason: str | None = "Suspicious content",
) -> ModerationLog:
    """Create a ModerationLog entry for testing."""
    log = ModerationLog(
        id=uuid4(),
        user_id=user_id,
        content_type=content_type,
        decision=decision,
        reason=reason,
        content_text="Test flagged content",
        details={"filename": "suspicious.stl"},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


# =============================================================================
# US-10.12: File/Storage Tests
# =============================================================================


class TestGetFileDetail:
    """Tests for GET /admin/files/{file_id}."""

    async def test_get_file_detail_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can retrieve detailed file information."""
        user = await UserFactory.create(db_session)
        file = await _create_file(db_session, user.id)

        response = await client.get(
            f"/api/v1/admin/files/{file.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(file.id)
        assert data["filename"] == "test_file.stl"
        assert data["user_email"] == user.email
        assert data["download_url"] is not None
        assert data["size_bytes"] == 1024 * 1024

    async def test_get_file_detail_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 for non-existent file."""
        response = await client.get(
            f"/api/v1/admin/files/{uuid4()}",
            headers=admin_headers,
        )

        assert response.status_code == 404

    async def test_get_file_detail_requires_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Non-admin users cannot access file details."""
        user = await UserFactory.create(db_session)
        file = await _create_file(db_session, user.id)

        response = await client.get(
            f"/api/v1/admin/files/{file.id}",
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestListFlaggedFiles:
    """Tests for GET /admin/files/flagged."""

    async def test_list_flagged_files_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can list flagged files."""
        user = await UserFactory.create(db_session)
        await _create_moderation_log(db_session, user.id)

        response = await client.get(
            "/api/v1/admin/files/flagged",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_list_flagged_files_pagination(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Flagged files endpoint supports pagination."""
        user = await UserFactory.create(db_session)
        for _ in range(3):
            await _create_moderation_log(db_session, user.id)

        response = await client.get(
            "/api/v1/admin/files/flagged?page=1&page_size=2",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["page_size"] == 2


class TestListFailedUploads:
    """Tests for GET /admin/files/failed-uploads."""

    async def test_list_failed_uploads_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can list failed uploads."""
        user = await UserFactory.create(db_session)
        await _create_file(db_session, user.id, status="failed")

        response = await client.get(
            "/api/v1/admin/files/failed-uploads",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["items"][0]["status"] == "failed"

    async def test_list_failed_uploads_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns empty list when no failed uploads exist."""
        response = await client.get(
            "/api/v1/admin/files/failed-uploads",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestAdjustUserStorageQuota:
    """Tests for POST /admin/users/{user_id}/storage-quota."""

    async def test_adjust_storage_quota_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can adjust a user's storage quota."""
        user = await UserFactory.create(db_session)

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/storage-quota",
            json={"storage_limit_bytes": 5_000_000_000},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["new_limit_bytes"] == 5_000_000_000
        assert data["user_id"] == str(user.id)

    async def test_adjust_storage_quota_user_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 when user does not exist."""
        response = await client.post(
            f"/api/v1/admin/users/{uuid4()}/storage-quota",
            json={"storage_limit_bytes": 5_000_000_000},
            headers=admin_headers,
        )

        assert response.status_code == 404

    async def test_adjust_storage_quota_invalid_value(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Returns 422 for invalid storage limit (zero or negative)."""
        user = await UserFactory.create(db_session)

        response = await client.post(
            f"/api/v1/admin/users/{user.id}/storage-quota",
            json={"storage_limit_bytes": 0},
            headers=admin_headers,
        )

        assert response.status_code == 422


class TestTopStorageUsers:
    """Tests for GET /admin/storage/top-users."""

    async def test_top_storage_users_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can list top storage consumers."""
        user = await UserFactory.create(db_session)
        await _create_file(db_session, user.id, size_bytes=10_000_000)
        await _create_file(
            db_session,
            user.id,
            filename="file2.stl",
            storage_path="users/test/file2.stl",
            size_bytes=20_000_000,
        )

        response = await client.get(
            "/api/v1/admin/storage/top-users",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        # Should have at least one entry for our user
        assert len(data["users"]) >= 1

    async def test_top_storage_users_with_limit(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Supports limit query parameter."""
        response = await client.get(
            "/api/v1/admin/storage/top-users?limit=5",
            headers=admin_headers,
        )

        assert response.status_code == 200


class TestStorageAnalytics:
    """Tests for GET /admin/storage/analytics."""

    async def test_storage_analytics_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can retrieve storage analytics."""
        user = await UserFactory.create(db_session)
        await _create_file(db_session, user.id)

        response = await client.get(
            "/api/v1/admin/storage/analytics",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_files" in data
        assert "total_size_bytes" in data
        assert "files_by_type" in data
        assert "files_by_status" in data
        assert "uploads_per_day" in data
        assert data["total_files"] >= 1


class TestGarbageCollect:
    """Tests for POST /admin/storage/garbage-collect."""

    async def test_garbage_collect_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can trigger garbage collection."""
        user = await UserFactory.create(db_session)
        # Create an old deleted file that should be collected
        f = await _create_file(db_session, user.id, is_deleted=True, status="deleted")
        # Make the file old enough by modifying deleted_at
        f.deleted_at = datetime.now(tz=UTC) - timedelta(hours=48)
        await db_session.commit()

        response = await client.post(
            "/api/v1/admin/storage/garbage-collect",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "files_cleaned" in data
        assert "space_reclaimed_bytes" in data
        assert data["files_cleaned"] >= 1

    async def test_garbage_collect_no_orphans(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 0 cleaned files when no orphans exist."""
        response = await client.post(
            "/api/v1/admin/storage/garbage-collect",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["files_cleaned"] == 0


# =============================================================================
# US-10.13: Audit/Security Tests
# =============================================================================


class TestExportAuditLogs:
    """Tests for GET /admin/audit-logs/export."""

    async def test_export_audit_logs_csv(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can export audit logs as CSV."""
        user = await UserFactory.create(db_session)
        await _create_audit_log(db_session, user_id=user.id, action="test_export")

        response = await client.get(
            "/api/v1/admin/audit-logs/export",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers.get("content-disposition", "")
        content = response.text
        assert "id" in content
        assert "action" in content

    async def test_export_audit_logs_with_filters(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Export supports action and user_id filters."""
        user = await UserFactory.create(db_session)
        await _create_audit_log(db_session, user_id=user.id, action="filtered_action")

        response = await client.get(
            f"/api/v1/admin/audit-logs/export?action=filtered_action&user_id={user.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]


class TestSecurityEvents:
    """Tests for GET /admin/security/events."""

    async def test_security_events_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can list security events."""
        user = await UserFactory.create(db_session)
        await _create_audit_log(
            db_session,
            user_id=user.id,
            action="auth.login.failed",
            context={"severity": "low"},
        )

        response = await client.get(
            "/api/v1/admin/security/events",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_security_events_filter_by_type(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Supports event_type filter."""
        user = await UserFactory.create(db_session)
        await _create_audit_log(
            db_session,
            user_id=user.id,
            action="auth.login.failed",
            context={"severity": "low"},
        )

        response = await client.get(
            "/api/v1/admin/security/events?event_type=auth.login.failed",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_security_events_filter_by_severity(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Supports severity filter."""
        user = await UserFactory.create(db_session)
        await _create_audit_log(
            db_session,
            user_id=user.id,
            action="threat.brute_force",
            context={"severity": "high"},
        )

        response = await client.get(
            "/api/v1/admin/security/events?severity=high",
            headers=admin_headers,
        )

        assert response.status_code == 200


class TestFailedLogins:
    """Tests for GET /admin/security/failed-logins."""

    async def test_failed_logins_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can list failed login attempts."""
        user = await UserFactory.create(db_session)
        await _create_audit_log(
            db_session,
            user_id=user.id,
            action="auth.login.failed",
            ip_address="192.168.1.100",
        )

        response = await client.get(
            "/api/v1/admin/security/failed-logins",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    async def test_failed_logins_pagination(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Failed logins endpoint supports pagination."""
        user = await UserFactory.create(db_session)
        for _ in range(3):
            await _create_audit_log(
                db_session,
                user_id=user.id,
                action="auth.login.failed",
            )

        response = await client.get(
            "/api/v1/admin/security/failed-logins?page=1&page_size=2",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2


class TestBlockedIPs:
    """Tests for blocked IP management endpoints."""

    async def test_list_blocked_ips_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns empty list when no IPs are blocked."""
        response = await client.get(
            "/api/v1/admin/security/blocked-ips",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_block_ip_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can block an IP address."""
        response = await client.post(
            "/api/v1/admin/security/blocked-ips",
            json={"ip_address": "10.0.0.1", "reason": "Suspicious activity"},
            headers=admin_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["ip_address"] == "10.0.0.1"

    async def test_list_blocked_ips_after_block(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Blocked IPs appear in the list."""
        await client.post(
            "/api/v1/admin/security/blocked-ips",
            json={"ip_address": "10.0.0.2", "reason": "Test"},
            headers=admin_headers,
        )

        response = await client.get(
            "/api/v1/admin/security/blocked-ips",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["ip_address"] == "10.0.0.2"

    async def test_unblock_ip_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can unblock a blocked IP."""
        await client.post(
            "/api/v1/admin/security/blocked-ips",
            json={"ip_address": "10.0.0.3", "reason": "Test"},
            headers=admin_headers,
        )

        response = await client.delete(
            "/api/v1/admin/security/blocked-ips/10.0.0.3",
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert "unblocked" in response.json()["message"]

    async def test_unblock_ip_not_found(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 404 when trying to unblock a non-blocked IP."""
        response = await client.delete(
            "/api/v1/admin/security/blocked-ips/99.99.99.99",
            headers=admin_headers,
        )

        assert response.status_code == 404


class TestActiveSessions:
    """Tests for GET /admin/security/sessions."""

    async def test_list_active_sessions_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can list active sessions."""
        user = await UserFactory.create(db_session)
        await _create_audit_log(db_session, user_id=user.id, action="login_success")

        response = await client.get(
            "/api/v1/admin/security/sessions",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestTerminateSession:
    """Tests for DELETE /admin/security/sessions/{session_id}."""

    async def test_terminate_session_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can terminate a session."""
        session_id = str(uuid4())

        response = await client.delete(
            f"/api/v1/admin/security/sessions/{session_id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id


class TestSecurityDashboard:
    """Tests for GET /admin/security/dashboard."""

    async def test_security_dashboard_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can retrieve the security dashboard."""
        response = await client.get(
            "/api/v1/admin/security/dashboard",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "failed_logins_24h" in data
        assert "blocked_ips_count" in data
        assert "active_sessions" in data
        assert "security_events_24h" in data
        assert "threat_level" in data
        assert data["threat_level"] in ("low", "medium", "high", "critical")

    async def test_security_dashboard_threat_level(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Threat level is computed from metrics."""
        # With no events, threat level should be 'low'
        response = await client.get(
            "/api/v1/admin/security/dashboard",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["threat_level"] == "low"


# =============================================================================
# US-10.14: System Health Tests
# =============================================================================


class TestServiceDetail:
    """Tests for GET /admin/system/services/{service_name}."""

    async def test_service_detail_database(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can get database service details."""
        response = await client.get(
            "/api/v1/admin/system/services/database",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "database"
        assert data["status"] in ("healthy", "unhealthy")

    async def test_service_detail_redis(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can get Redis service details."""
        response = await client.get(
            "/api/v1/admin/system/services/redis",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "redis"

    async def test_service_detail_unknown_service(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns 400 for unknown service name."""
        response = await client.get(
            "/api/v1/admin/system/services/nonexistent",
            headers=admin_headers,
        )

        assert response.status_code == 400


class TestPerformanceMetrics:
    """Tests for GET /admin/system/performance."""

    async def test_performance_metrics_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can retrieve performance metrics."""
        response = await client.get(
            "/api/v1/admin/system/performance",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "avg_response_time_ms" in data
        assert "p95_response_time_ms" in data
        assert "p99_response_time_ms" in data
        assert "error_rate_percent" in data
        assert "requests_per_minute" in data


class TestResourceUtilization:
    """Tests for GET /admin/system/resources."""

    async def test_resource_utilization_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can retrieve resource utilization."""
        response = await client.get(
            "/api/v1/admin/system/resources",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "memory_used_mb" in data
        assert "memory_total_mb" in data
        assert "disk_used_gb" in data
        assert "disk_total_gb" in data


class TestRecentErrors:
    """Tests for GET /admin/system/errors."""

    async def test_recent_errors_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
    ):
        """Admin can list recent errors."""
        user = await UserFactory.create(db_session)
        await _create_audit_log(
            db_session,
            user_id=user.id,
            action="api_error",
            resource_type="endpoint",
            status="error",
            error_message="Something went wrong",
        )

        response = await client.get(
            "/api/v1/admin/system/errors",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        assert data["items"][0]["message"] == "Something went wrong"

    async def test_recent_errors_with_days_param(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Supports days query parameter."""
        response = await client.get(
            "/api/v1/admin/system/errors?days=3",
            headers=admin_headers,
        )

        assert response.status_code == 200

    async def test_recent_errors_empty(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Returns empty list when no errors exist."""
        response = await client.get(
            "/api/v1/admin/system/errors",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)


class TestAIProviders:
    """Tests for GET /admin/system/ai-providers."""

    async def test_ai_providers_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can list AI provider statuses."""
        response = await client.get(
            "/api/v1/admin/system/ai-providers",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert len(data["providers"]) >= 1
        provider = data["providers"][0]
        assert "name" in provider
        assert "status" in provider


class TestSystemConfig:
    """Tests for GET /admin/system/config."""

    async def test_system_config_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can retrieve sanitized system config."""
        response = await client.get(
            "/api/v1/admin/system/config",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "environment" in data
        assert "debug" in data
        assert "max_upload_size_mb" in data
        assert "storage_backend" in data

    async def test_system_config_no_secrets(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Config response does not contain secrets."""
        response = await client.get(
            "/api/v1/admin/system/config",
            headers=admin_headers,
        )

        assert response.status_code == 200
        content = response.text.lower()
        # Verify no secret-like fields leak
        assert "secret_key" not in content
        assert "password" not in content
        assert "aws_secret" not in content


class TestManualHealthCheck:
    """Tests for POST /admin/system/health-check."""

    async def test_manual_health_check_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can trigger a manual health check."""
        response = await client.post(
            "/api/v1/admin/system/health-check",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "services" in data
        assert "checked_at" in data
        assert "duration_ms" in data
        assert data["overall_status"] in ("healthy", "degraded", "unhealthy")


class TestUptime:
    """Tests for GET /admin/system/uptime."""

    async def test_uptime_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Admin can retrieve uptime information."""
        response = await client.get(
            "/api/v1/admin/system/uptime",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "uptime_formatted" in data
        assert "start_time" in data
        assert "uptime_percentage_30d" in data
        assert data["uptime_seconds"] >= 0

    async def test_uptime_format(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """Uptime formatted string contains expected components."""
        response = await client.get(
            "/api/v1/admin/system/uptime",
            headers=admin_headers,
        )

        data = response.json()
        # Should contain days/hours/minutes/seconds format
        assert "d" in data["uptime_formatted"]
        assert "h" in data["uptime_formatted"]
        assert "m" in data["uptime_formatted"]
        assert "s" in data["uptime_formatted"]
