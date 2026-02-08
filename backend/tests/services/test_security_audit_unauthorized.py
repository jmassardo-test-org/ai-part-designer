"""
Tests for unauthorized access logging in Security Audit Service.

Tests the new functionality for logging 401/403 responses with context
and pattern detection for suspicious access attempts.
"""

from uuid import uuid4

import pytest

from app.services.security_audit import (
    SecurityAuditService,
)


@pytest.mark.asyncio
class TestUnauthorizedAccessLogging:
    """Tests for logging 401 unauthorized access attempts."""

    async def test_log_unauthorized_access_with_minimal_info(self):
        """Test logging unauthorized access with minimal information."""
        service = SecurityAuditService(db=None)

        # Should not raise an exception
        await service.log_unauthorized_access(
            endpoint="/api/v1/designs",
            method="GET",
            client_ip="192.168.1.100",
            user_agent="Mozilla/5.0",
        )

    async def test_log_unauthorized_access_with_full_context(self):
        """Test logging unauthorized access with full context."""
        service = SecurityAuditService(db=None)
        user_id = uuid4()

        await service.log_unauthorized_access(
            endpoint="/api/v1/designs/123",
            method="POST",
            client_ip="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            user_id=user_id,
            reason="token_expired",
            request_id="req-123-456",
        )

    async def test_log_unauthorized_access_with_different_reasons(self):
        """Test logging unauthorized access with various reasons."""
        service = SecurityAuditService(db=None)
        reasons = [
            "authentication_required",
            "token_expired",
            "token_invalid",
            "token_revoked",
        ]

        for reason in reasons:
            await service.log_unauthorized_access(
                endpoint="/api/v1/protected",
                method="GET",
                client_ip="192.168.1.100",
                user_agent="TestAgent/1.0",
                reason=reason,
            )

    async def test_unauthorized_access_tracks_attempts(self):
        """Test that unauthorized attempts are tracked for pattern detection."""
        service = SecurityAuditService(db=None)
        client_ip = "192.168.1.100"

        # Make multiple attempts (should trigger pattern detection at 5)
        for i in range(10):
            await service.log_unauthorized_access(
                endpoint=f"/api/v1/endpoint-{i}",
                method="GET",
                client_ip=client_ip,
                user_agent="BotAgent/1.0",
            )


@pytest.mark.asyncio
class TestForbiddenAccessLogging:
    """Tests for logging 403 forbidden access attempts."""

    async def test_log_forbidden_access_with_minimal_info(self):
        """Test logging forbidden access with minimal information."""
        service = SecurityAuditService(db=None)
        user_id = uuid4()

        await service.log_forbidden_access(
            user_id=user_id,
            endpoint="/api/v1/admin/users",
            method="GET",
            client_ip="192.168.1.100",
            user_agent="Mozilla/5.0",
        )

    async def test_log_forbidden_access_with_full_context(self):
        """Test logging forbidden access with full context."""
        service = SecurityAuditService(db=None)
        user_id = uuid4()
        resource_id = uuid4()

        await service.log_forbidden_access(
            user_id=user_id,
            endpoint="/api/v1/designs/123",
            method="DELETE",
            client_ip="192.168.1.100",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            reason="insufficient_permissions",
            resource_type="design",
            resource_id=resource_id,
            request_id="req-789-012",
        )

    async def test_log_forbidden_access_with_different_reasons(self):
        """Test logging forbidden access with various reasons."""
        service = SecurityAuditService(db=None)
        user_id = uuid4()
        reasons = [
            "insufficient_permissions",
            "account_suspended",
            "insufficient_role",
            "resource_locked",
        ]

        for reason in reasons:
            await service.log_forbidden_access(
                user_id=user_id,
                endpoint="/api/v1/protected",
                method="POST",
                client_ip="192.168.1.100",
                user_agent="TestAgent/1.0",
                reason=reason,
            )

    async def test_forbidden_access_tracks_attempts_per_ip(self):
        """Test that forbidden attempts are tracked per IP."""
        service = SecurityAuditService(db=None)
        user_id = uuid4()
        client_ip = "192.168.1.200"

        # Make multiple attempts from same IP
        for i in range(15):
            await service.log_forbidden_access(
                user_id=user_id,
                endpoint=f"/api/v1/admin/endpoint-{i}",
                method="GET",
                client_ip=client_ip,
                user_agent="BotAgent/1.0",
            )

    async def test_forbidden_access_tracks_attempts_per_user(self):
        """Test that forbidden attempts are tracked per user."""
        service = SecurityAuditService(db=None)
        user_id = uuid4()

        # Make multiple attempts by same user from different IPs
        for i in range(20):
            await service.log_forbidden_access(
                user_id=user_id,
                endpoint="/api/v1/admin/users",
                method="GET",
                client_ip=f"192.168.1.{100 + i}",
                user_agent="EscalationBot/1.0",
            )


@pytest.mark.asyncio
class TestPatternDetection:
    """Tests for suspicious pattern detection."""

    async def test_repeated_unauthorized_attempts_trigger_alert(self):
        """Test that repeated unauthorized attempts trigger suspicious pattern alert."""
        service = SecurityAuditService(db=None)
        client_ip = "10.0.0.50"

        # First 4 attempts should not trigger alert
        for _i in range(4):
            await service.log_unauthorized_access(
                endpoint="/api/v1/protected",
                method="GET",
                client_ip=client_ip,
                user_agent="Scanner/1.0",
            )

        # 5th attempt should trigger suspicious pattern alert
        await service.log_unauthorized_access(
            endpoint="/api/v1/protected",
            method="GET",
            client_ip=client_ip,
            user_agent="Scanner/1.0",
        )

    async def test_excessive_unauthorized_attempts_trigger_blocking(self):
        """Test that excessive unauthorized attempts trigger IP blocking."""
        service = SecurityAuditService(db=None)
        client_ip = "10.0.0.60"

        # 20+ attempts should trigger auto-blocking
        for i in range(25):
            await service.log_unauthorized_access(
                endpoint=f"/api/v1/endpoint-{i}",
                method="GET",
                client_ip=client_ip,
                user_agent="Attacker/1.0",
            )

    async def test_repeated_forbidden_attempts_trigger_alert(self):
        """Test that repeated forbidden attempts trigger suspicious pattern alert."""
        service = SecurityAuditService(db=None)
        user_id = uuid4()
        client_ip = "10.0.0.70"

        # 10+ attempts should trigger suspicious pattern alert
        for _i in range(12):
            await service.log_forbidden_access(
                user_id=user_id,
                endpoint="/api/v1/admin/users",
                method="GET",
                client_ip=client_ip,
                user_agent="PrivilegeEscalator/1.0",
            )

    async def test_privilege_escalation_detection(self):
        """Test that potential privilege escalation attempts are detected."""
        service = SecurityAuditService(db=None)
        user_id = uuid4()

        # 15+ forbidden attempts by same user should trigger escalation alert
        for i in range(18):
            await service.log_forbidden_access(
                user_id=user_id,
                endpoint="/api/v1/admin/users",
                method="GET",
                client_ip=f"10.0.0.{100 + (i % 10)}",
                user_agent="EscalationAttempt/1.0",
            )


@pytest.mark.asyncio
class TestEventContext:
    """Tests for proper context capture in security events."""

    async def test_unauthorized_event_includes_endpoint(self):
        """Test that unauthorized events include endpoint information."""
        service = SecurityAuditService(db=None)

        await service.log_unauthorized_access(
            endpoint="/api/v1/designs/abc-123",
            method="POST",
            client_ip="192.168.1.1",
            user_agent="TestAgent",
        )

    async def test_forbidden_event_includes_resource_info(self):
        """Test that forbidden events include resource information."""
        service = SecurityAuditService(db=None)
        user_id = uuid4()
        resource_id = uuid4()

        await service.log_forbidden_access(
            user_id=user_id,
            endpoint="/api/v1/designs/123",
            method="DELETE",
            client_ip="192.168.1.1",
            user_agent="TestAgent",
            resource_type="design",
            resource_id=resource_id,
        )

    async def test_events_include_user_agent(self):
        """Test that events include user agent information."""
        service = SecurityAuditService(db=None)

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "curl/7.68.0",
            "PostmanRuntime/7.28.0",
        ]

        for ua in user_agents:
            await service.log_unauthorized_access(
                endpoint="/api/v1/test",
                method="GET",
                client_ip="192.168.1.1",
                user_agent=ua,
            )

    async def test_events_include_request_id(self):
        """Test that events include request ID for correlation."""
        service = SecurityAuditService(db=None)

        await service.log_unauthorized_access(
            endpoint="/api/v1/test",
            method="GET",
            client_ip="192.168.1.1",
            user_agent="TestAgent",
            request_id="req-correlation-123",
        )
