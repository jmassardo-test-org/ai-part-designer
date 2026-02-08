"""
Security audit and threat detection service.

Provides:
- Security event logging
- Threat detection patterns
- Anomaly detection
- Security metrics collection
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import redis_client
from app.models import AuditLog

logger = logging.getLogger("security.audit")


# =============================================================================
# Security Event Types
# =============================================================================


class SecurityEventType(StrEnum):
    """Types of security events to track."""

    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token.refresh"
    TOKEN_REVOKED = "auth.token.revoked"
    PASSWORD_CHANGED = "auth.password.changed"
    PASSWORD_RESET_REQUESTED = "auth.password.reset_requested"
    PASSWORD_RESET_COMPLETED = "auth.password.reset_completed"

    # Authorization events
    ACCESS_DENIED = "authz.access_denied"
    PERMISSION_ESCALATION = "authz.permission_escalation"
    RESOURCE_ACCESS = "authz.resource_access"
    UNAUTHORIZED_ACCESS_ATTEMPT = "authz.unauthorized_access_attempt"
    FORBIDDEN_ACCESS_ATTEMPT = "authz.forbidden_access_attempt"

    # API key events
    API_KEY_CREATED = "apikey.created"
    API_KEY_REVOKED = "apikey.revoked"
    API_KEY_USED = "apikey.used"
    API_KEY_FAILED = "apikey.failed"

    # Rate limiting events
    RATE_LIMIT_EXCEEDED = "ratelimit.exceeded"
    RATE_LIMIT_WARNING = "ratelimit.warning"

    # Suspicious activity
    SUSPICIOUS_REQUEST = "threat.suspicious_request"
    BRUTE_FORCE_DETECTED = "threat.brute_force"
    INJECTION_ATTEMPT = "threat.injection"
    PATH_TRAVERSAL = "threat.path_traversal"

    # Administrative events
    USER_CREATED = "admin.user.created"
    USER_UPDATED = "admin.user.updated"
    USER_DELETED = "admin.user.deleted"
    USER_SUSPENDED = "admin.user.suspended"
    ROLE_CHANGED = "admin.role.changed"

    # Data events
    SENSITIVE_DATA_ACCESS = "data.sensitive_access"
    BULK_EXPORT = "data.bulk_export"
    DATA_DELETED = "data.deleted"

    # IP events
    IP_BLOCKED = "ip.blocked"
    IP_UNBLOCKED = "ip.unblocked"


class SecuritySeverity(StrEnum):
    """Severity levels for security events."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Event severity mapping
EVENT_SEVERITY: dict[SecurityEventType, SecuritySeverity] = {
    SecurityEventType.LOGIN_SUCCESS: SecuritySeverity.INFO,
    SecurityEventType.LOGIN_FAILED: SecuritySeverity.LOW,
    SecurityEventType.LOGOUT: SecuritySeverity.INFO,
    SecurityEventType.ACCESS_DENIED: SecuritySeverity.MEDIUM,
    SecurityEventType.UNAUTHORIZED_ACCESS_ATTEMPT: SecuritySeverity.MEDIUM,
    SecurityEventType.FORBIDDEN_ACCESS_ATTEMPT: SecuritySeverity.MEDIUM,
    SecurityEventType.RATE_LIMIT_EXCEEDED: SecuritySeverity.MEDIUM,
    SecurityEventType.BRUTE_FORCE_DETECTED: SecuritySeverity.HIGH,
    SecurityEventType.INJECTION_ATTEMPT: SecuritySeverity.HIGH,
    SecurityEventType.PATH_TRAVERSAL: SecuritySeverity.HIGH,
    SecurityEventType.PERMISSION_ESCALATION: SecuritySeverity.CRITICAL,
    SecurityEventType.USER_DELETED: SecuritySeverity.HIGH,
    SecurityEventType.IP_BLOCKED: SecuritySeverity.MEDIUM,
}


# =============================================================================
# Security Audit Service
# =============================================================================


class SecurityAuditService:
    """
    Service for logging and analyzing security events.

    Provides comprehensive security monitoring and threat detection.
    """

    # Thresholds for threat detection
    FAILED_LOGIN_THRESHOLD = 5  # Per IP in 15 minutes
    RATE_LIMIT_THRESHOLD = 10  # Hits before warning
    SUSPICIOUS_PATTERN_THRESHOLD = 3  # Matches before alert

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def log_event(
        self,
        event_type: SecurityEventType,
        user_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        details: dict[str, Any] | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """
        Log a security event.

        Args:
            event_type: Type of security event
            user_id: User who triggered the event
            resource_type: Type of resource involved
            resource_id: ID of resource involved
            details: Additional event details
            client_ip: Client IP address
            user_agent: Client user agent
            request_id: Request correlation ID
        """
        severity = EVENT_SEVERITY.get(event_type, SecuritySeverity.INFO)

        event_data = {
            "event_type": event_type.value,
            "severity": severity.value,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "user_id": str(user_id) if user_id else None,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "client_ip": client_ip,
            "user_agent": user_agent[:200] if user_agent else None,
            "request_id": request_id,
            "details": details or {},
        }

        # Log to standard logger
        log_message = f"Security Event: {event_type.value}"
        if severity == SecuritySeverity.CRITICAL:
            logger.critical(log_message, extra=event_data)
        elif severity == SecuritySeverity.HIGH:
            logger.error(log_message, extra=event_data)
        elif severity == SecuritySeverity.MEDIUM:
            logger.warning(log_message, extra=event_data)
        else:
            logger.info(log_message, extra=event_data)

        # Store in Redis for real-time analysis
        await self._store_event(event_data)

        # Store in database for audit trail
        if self.db:
            await self._persist_event(event_data)

        # Trigger threat detection
        await self._analyze_event(event_data)

    async def _store_event(self, event_data: dict[str, Any]) -> None:
        """Store event in Redis for real-time analysis."""
        event_key = f"security:events:{datetime.now(tz=UTC).strftime('%Y%m%d%H')}"
        await redis_client.lpush(event_key, json.dumps(event_data))
        await redis_client.expire(event_key, 86400 * 7)  # Keep for 7 days

        # Increment event counters
        await redis_client.increment_counter(  # type: ignore[attr-defined]
            f"security:count:{event_data['event_type']}",
            window_seconds=3600,
        )

    async def _persist_event(self, event_data: dict[str, Any]) -> None:
        """Persist event to database audit log."""
        audit_entry = AuditLog(
            action=event_data["event_type"],
            resource_type=event_data.get("resource_type"),
            resource_id=UUID(event_data["resource_id"]) if event_data.get("resource_id") else None,
            user_id=UUID(event_data["user_id"]) if event_data.get("user_id") else None,
            ip_address=event_data.get("client_ip"),
            user_agent=event_data.get("user_agent"),
            context={"details": event_data.get("details"), "severity": event_data["severity"]},
        )
        assert self.db is not None
        self.db.add(audit_entry)
        await self.db.flush()

    async def _analyze_event(self, event_data: dict[str, Any]) -> None:
        """Analyze event for threat patterns."""
        event_type = event_data["event_type"]
        client_ip = event_data.get("client_ip")

        # Check for brute force attacks
        if event_type == SecurityEventType.LOGIN_FAILED.value and client_ip:
            failed_count = await self._get_failed_login_count(client_ip)
            if failed_count >= self.FAILED_LOGIN_THRESHOLD:
                await self.log_event(
                    SecurityEventType.BRUTE_FORCE_DETECTED,
                    client_ip=client_ip,
                    details={"failed_attempts": failed_count},
                )
                # Auto-block IP
                await self._auto_block_ip(client_ip, "brute_force")

    async def _get_failed_login_count(self, client_ip: str) -> int:
        """Get failed login count for IP in last 15 minutes."""
        key = f"security:failed_login:{client_ip}"
        count = await redis_client.get(key)
        return int(count) if count else 0

    async def _auto_block_ip(
        self,
        ip_address: str,
        reason: str,
        duration_seconds: int = 3600,
    ) -> None:
        """Automatically block an IP address."""
        from app.middleware.security import block_ip

        await block_ip(ip_address, duration_seconds, reason)

        await self.log_event(
            SecurityEventType.IP_BLOCKED,
            client_ip=ip_address,
            details={
                "reason": reason,
                "duration_seconds": duration_seconds,
                "auto_blocked": True,
            },
        )

    # =========================================================================
    # Authentication Event Helpers
    # =========================================================================

    async def log_login_success(
        self,
        user_id: UUID,
        client_ip: str,
        user_agent: str,
        mfa_used: bool = False,
    ) -> None:
        """Log successful login."""
        await self.log_event(
            SecurityEventType.LOGIN_SUCCESS,
            user_id=user_id,
            client_ip=client_ip,
            user_agent=user_agent,
            details={"mfa_used": mfa_used},
        )

        # Clear failed login counter
        await redis_client.delete(f"security:failed_login:{client_ip}")

    async def log_login_failed(
        self,
        email: str,
        client_ip: str,
        user_agent: str,
        reason: str = "invalid_credentials",
    ) -> None:
        """Log failed login attempt."""
        # Increment failed login counter
        key = f"security:failed_login:{client_ip}"
        await redis_client.increment_counter(key, window_seconds=900)  # type: ignore[attr-defined]

        # Hash email for privacy
        email_hash = hashlib.sha256(email.encode()).hexdigest()[:16]

        await self.log_event(
            SecurityEventType.LOGIN_FAILED,
            client_ip=client_ip,
            user_agent=user_agent,
            details={
                "email_hash": email_hash,
                "reason": reason,
            },
        )

    async def log_logout(
        self,
        user_id: UUID,
        client_ip: str,
        reason: str = "user_initiated",
    ) -> None:
        """Log user logout."""
        await self.log_event(
            SecurityEventType.LOGOUT,
            user_id=user_id,
            client_ip=client_ip,
            details={"reason": reason},
        )

    async def log_password_change(
        self,
        user_id: UUID,
        client_ip: str,
        forced: bool = False,
    ) -> None:
        """Log password change."""
        await self.log_event(
            SecurityEventType.PASSWORD_CHANGED,
            user_id=user_id,
            client_ip=client_ip,
            details={"forced": forced},
        )

    # =========================================================================
    # Authorization Event Helpers
    # =========================================================================

    async def log_access_denied(
        self,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        required_permission: str,
        client_ip: str,
    ) -> None:
        """Log access denied event."""
        await self.log_event(
            SecurityEventType.ACCESS_DENIED,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            client_ip=client_ip,
            details={"required_permission": required_permission},
        )

    async def log_unauthorized_access(
        self,
        endpoint: str,
        method: str,
        client_ip: str,
        user_agent: str,
        user_id: UUID | None = None,
        reason: str = "authentication_required",
        request_id: str | None = None,
    ) -> None:
        """
        Log 401 unauthorized access attempt.

        Args:
            endpoint: API endpoint that was accessed
            method: HTTP method (GET, POST, etc.)
            client_ip: Client IP address
            user_agent: Client user agent
            user_id: User ID if token was present but invalid
            reason: Reason for denial (e.g., 'token_expired', 'token_invalid')
            request_id: Request correlation ID
        """
        await self.log_event(
            SecurityEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
            user_id=user_id,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            details={
                "endpoint": endpoint,
                "method": method,
                "reason": reason,
            },
        )

        # Track unauthorized attempts for pattern detection
        if client_ip:
            await self._track_unauthorized_attempt(client_ip, endpoint)

    async def log_forbidden_access(
        self,
        user_id: UUID,
        endpoint: str,
        method: str,
        client_ip: str,
        user_agent: str,
        reason: str = "insufficient_permissions",
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        request_id: str | None = None,
    ) -> None:
        """
        Log 403 forbidden access attempt.

        Args:
            user_id: User who attempted access
            endpoint: API endpoint that was accessed
            method: HTTP method (GET, POST, etc.)
            client_ip: Client IP address
            user_agent: Client user agent
            reason: Reason for denial (e.g., 'insufficient_permissions', 'account_suspended')
            resource_type: Type of resource attempted to access
            resource_id: ID of resource attempted to access
            request_id: Request correlation ID
        """
        await self.log_event(
            SecurityEventType.FORBIDDEN_ACCESS_ATTEMPT,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            details={
                "endpoint": endpoint,
                "method": method,
                "reason": reason,
            },
        )

        # Track forbidden attempts for pattern detection
        if client_ip:
            await self._track_forbidden_attempt(client_ip, user_id, endpoint)

    async def _track_unauthorized_attempt(self, client_ip: str, endpoint: str) -> None:
        """Track unauthorized access attempts for pattern detection."""
        key = f"security:unauthorized_attempts:{client_ip}"
        count = await redis_client.increment_counter(key, window_seconds=900)  # type: ignore[attr-defined]

        # Alert on suspicious patterns (5+ attempts in 15 minutes)
        if count >= 5:
            await self.log_event(
                SecurityEventType.SUSPICIOUS_REQUEST,
                client_ip=client_ip,
                details={
                    "pattern": "repeated_unauthorized_attempts",
                    "count": count,
                    "endpoint": endpoint,
                    "window_minutes": 15,
                },
            )

            # Consider auto-blocking after more severe threshold
            if count >= 20:
                await self._auto_block_ip(client_ip, "excessive_unauthorized_attempts")

    async def _track_forbidden_attempt(
        self,
        client_ip: str,
        user_id: UUID,
        endpoint: str,
    ) -> None:
        """Track forbidden access attempts for pattern detection."""
        # Track per IP
        ip_key = f"security:forbidden_attempts:{client_ip}"
        ip_count = await redis_client.increment_counter(ip_key, window_seconds=900)  # type: ignore[attr-defined]

        # Track per user
        user_key = f"security:forbidden_attempts:user:{user_id}"
        user_count = await redis_client.increment_counter(user_key, window_seconds=900)  # type: ignore[attr-defined]

        # Alert on suspicious patterns
        if ip_count >= 10 or user_count >= 10:
            await self.log_event(
                SecurityEventType.SUSPICIOUS_REQUEST,
                user_id=user_id,
                client_ip=client_ip,
                details={
                    "pattern": "repeated_forbidden_attempts",
                    "ip_count": ip_count,
                    "user_count": user_count,
                    "endpoint": endpoint,
                    "window_minutes": 15,
                },
            )

            # Potential privilege escalation attempt
            if user_count >= 15:
                await self.log_event(
                    SecurityEventType.PERMISSION_ESCALATION,
                    user_id=user_id,
                    client_ip=client_ip,
                    details={
                        "attempts": user_count,
                        "endpoint": endpoint,
                        "alert": "possible_privilege_escalation_attempt",
                    },
                )

    # =========================================================================
    # Threat Detection Helpers
    # =========================================================================

    async def log_suspicious_request(
        self,
        client_ip: str,
        path: str,
        pattern: str,
        user_id: UUID | None = None,
    ) -> None:
        """Log suspicious request pattern."""
        await self.log_event(
            SecurityEventType.SUSPICIOUS_REQUEST,
            user_id=user_id,
            client_ip=client_ip,
            details={
                "path": path[:500],
                "pattern": pattern,
            },
        )

    # =========================================================================
    # Security Metrics
    # =========================================================================

    async def get_security_metrics(
        self,
        hours: int = 24,
    ) -> dict[str, Any]:
        """
        Get security metrics for monitoring.

        Returns counts of various security events.
        """
        events: dict[str, int] = {}

        # Get event counts
        for event_type in SecurityEventType:
            count = await redis_client.get(f"security:count:{event_type.value}")
            if count:
                events[event_type.value] = int(count)

        return {
            "period_hours": hours,
            "events": events,
            "top_blocked_ips": [],
            "top_failed_logins": [],
        }

    async def get_user_security_events(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get recent security events for a user."""
        if not self.db:
            return []

        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .where(AuditLog.action.like("auth.%"))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )

        events = result.scalars().all()
        return [
            {
                "action": e.action,
                "timestamp": e.created_at.isoformat(),
                "ip_address": e.ip_address,
                "details": getattr(e, "changes", None) or getattr(e, "details", {}),
            }
            for e in events
        ]


# =============================================================================
# Global Instance
# =============================================================================


def get_security_audit_service(db: AsyncSession | None = None) -> SecurityAuditService:
    """Get security audit service instance."""
    return SecurityAuditService(db)
