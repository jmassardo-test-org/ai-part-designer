"""
Tests for Security Audit Service.

Tests security event types, severity levels, threshold configuration,
and event severity mappings.
"""

from app.services.security_audit import (
    EVENT_SEVERITY,
    SecurityAuditService,
    SecurityEventType,
    SecuritySeverity,
)

# =============================================================================
# Security Event Type Tests
# =============================================================================


class TestSecurityEventType:
    """Tests for security event type enum."""

    def test_authentication_events(self):
        """Test authentication event types."""
        assert SecurityEventType.LOGIN_SUCCESS == "auth.login.success"
        assert SecurityEventType.LOGIN_FAILED == "auth.login.failed"
        assert SecurityEventType.LOGOUT == "auth.logout"
        assert SecurityEventType.TOKEN_REFRESH == "auth.token.refresh"
        assert SecurityEventType.TOKEN_REVOKED == "auth.token.revoked"
        assert SecurityEventType.PASSWORD_CHANGED == "auth.password.changed"
        assert SecurityEventType.PASSWORD_RESET_REQUESTED == "auth.password.reset_requested"
        assert SecurityEventType.PASSWORD_RESET_COMPLETED == "auth.password.reset_completed"

    def test_authorization_events(self):
        """Test authorization event types."""
        assert SecurityEventType.ACCESS_DENIED == "authz.access_denied"
        assert SecurityEventType.PERMISSION_ESCALATION == "authz.permission_escalation"
        assert SecurityEventType.RESOURCE_ACCESS == "authz.resource_access"
        assert SecurityEventType.UNAUTHORIZED_ACCESS_ATTEMPT == "authz.unauthorized_access_attempt"
        assert SecurityEventType.FORBIDDEN_ACCESS_ATTEMPT == "authz.forbidden_access_attempt"

    def test_api_key_events(self):
        """Test API key event types."""
        assert SecurityEventType.API_KEY_CREATED == "apikey.created"
        assert SecurityEventType.API_KEY_REVOKED == "apikey.revoked"
        assert SecurityEventType.API_KEY_USED == "apikey.used"
        assert SecurityEventType.API_KEY_FAILED == "apikey.failed"

    def test_rate_limiting_events(self):
        """Test rate limiting event types."""
        assert SecurityEventType.RATE_LIMIT_EXCEEDED == "ratelimit.exceeded"
        assert SecurityEventType.RATE_LIMIT_WARNING == "ratelimit.warning"

    def test_threat_events(self):
        """Test threat detection event types."""
        assert SecurityEventType.SUSPICIOUS_REQUEST == "threat.suspicious_request"
        assert SecurityEventType.BRUTE_FORCE_DETECTED == "threat.brute_force"
        assert SecurityEventType.INJECTION_ATTEMPT == "threat.injection"
        assert SecurityEventType.PATH_TRAVERSAL == "threat.path_traversal"

    def test_admin_events(self):
        """Test administrative event types."""
        assert SecurityEventType.USER_CREATED == "admin.user.created"
        assert SecurityEventType.USER_UPDATED == "admin.user.updated"
        assert SecurityEventType.USER_DELETED == "admin.user.deleted"
        assert SecurityEventType.USER_SUSPENDED == "admin.user.suspended"
        assert SecurityEventType.ROLE_CHANGED == "admin.role.changed"

    def test_data_events(self):
        """Test data access event types."""
        assert SecurityEventType.SENSITIVE_DATA_ACCESS == "data.sensitive_access"
        assert SecurityEventType.BULK_EXPORT == "data.bulk_export"
        assert SecurityEventType.DATA_DELETED == "data.deleted"

    def test_ip_events(self):
        """Test IP-related event types."""
        assert SecurityEventType.IP_BLOCKED == "ip.blocked"
        assert SecurityEventType.IP_UNBLOCKED == "ip.unblocked"


# =============================================================================
# Security Severity Tests
# =============================================================================


class TestSecuritySeverity:
    """Tests for security severity levels."""

    def test_info_level(self):
        """Test info severity level."""
        assert SecuritySeverity.INFO == "info"

    def test_low_level(self):
        """Test low severity level."""
        assert SecuritySeverity.LOW == "low"

    def test_medium_level(self):
        """Test medium severity level."""
        assert SecuritySeverity.MEDIUM == "medium"

    def test_high_level(self):
        """Test high severity level."""
        assert SecuritySeverity.HIGH == "high"

    def test_critical_level(self):
        """Test critical severity level."""
        assert SecuritySeverity.CRITICAL == "critical"

    def test_all_levels_exist(self):
        """Test all expected severity levels exist."""
        levels = [s.value for s in SecuritySeverity]
        assert "info" in levels
        assert "low" in levels
        assert "medium" in levels
        assert "high" in levels
        assert "critical" in levels


# =============================================================================
# Event Severity Mapping Tests
# =============================================================================


class TestEventSeverityMapping:
    """Tests for event to severity mappings."""

    def test_login_success_is_info(self):
        """Test successful login is info level."""
        assert EVENT_SEVERITY[SecurityEventType.LOGIN_SUCCESS] == SecuritySeverity.INFO

    def test_login_failed_is_low(self):
        """Test failed login is low level."""
        assert EVENT_SEVERITY[SecurityEventType.LOGIN_FAILED] == SecuritySeverity.LOW

    def test_logout_is_info(self):
        """Test logout is info level."""
        assert EVENT_SEVERITY[SecurityEventType.LOGOUT] == SecuritySeverity.INFO

    def test_access_denied_is_medium(self):
        """Test access denied is medium level."""
        assert EVENT_SEVERITY[SecurityEventType.ACCESS_DENIED] == SecuritySeverity.MEDIUM

    def test_unauthorized_access_attempt_is_medium(self):
        """Test unauthorized access attempt is medium level."""
        assert (
            EVENT_SEVERITY[SecurityEventType.UNAUTHORIZED_ACCESS_ATTEMPT] == SecuritySeverity.MEDIUM
        )

    def test_forbidden_access_attempt_is_medium(self):
        """Test forbidden access attempt is medium level."""
        assert EVENT_SEVERITY[SecurityEventType.FORBIDDEN_ACCESS_ATTEMPT] == SecuritySeverity.MEDIUM

    def test_rate_limit_exceeded_is_medium(self):
        """Test rate limit exceeded is medium level."""
        assert EVENT_SEVERITY[SecurityEventType.RATE_LIMIT_EXCEEDED] == SecuritySeverity.MEDIUM

    def test_brute_force_is_high(self):
        """Test brute force detection is high level."""
        assert EVENT_SEVERITY[SecurityEventType.BRUTE_FORCE_DETECTED] == SecuritySeverity.HIGH

    def test_injection_attempt_is_high(self):
        """Test injection attempts are high level."""
        assert EVENT_SEVERITY[SecurityEventType.INJECTION_ATTEMPT] == SecuritySeverity.HIGH

    def test_path_traversal_is_high(self):
        """Test path traversal is high level."""
        assert EVENT_SEVERITY[SecurityEventType.PATH_TRAVERSAL] == SecuritySeverity.HIGH

    def test_permission_escalation_is_critical(self):
        """Test permission escalation is critical level."""
        assert EVENT_SEVERITY[SecurityEventType.PERMISSION_ESCALATION] == SecuritySeverity.CRITICAL

    def test_user_deleted_is_high(self):
        """Test user deletion is high level."""
        assert EVENT_SEVERITY[SecurityEventType.USER_DELETED] == SecuritySeverity.HIGH

    def test_ip_blocked_is_medium(self):
        """Test IP blocked is medium level."""
        assert EVENT_SEVERITY[SecurityEventType.IP_BLOCKED] == SecuritySeverity.MEDIUM


# =============================================================================
# Threshold Configuration Tests
# =============================================================================


class TestSecurityThresholds:
    """Tests for security threshold configuration."""

    def test_failed_login_threshold(self):
        """Test failed login threshold is reasonable."""
        assert SecurityAuditService.FAILED_LOGIN_THRESHOLD == 5
        assert SecurityAuditService.FAILED_LOGIN_THRESHOLD > 0

    def test_rate_limit_threshold(self):
        """Test rate limit threshold is reasonable."""
        assert SecurityAuditService.RATE_LIMIT_THRESHOLD == 10
        assert SecurityAuditService.RATE_LIMIT_THRESHOLD > 0

    def test_suspicious_pattern_threshold(self):
        """Test suspicious pattern threshold is reasonable."""
        assert SecurityAuditService.SUSPICIOUS_PATTERN_THRESHOLD == 3
        assert SecurityAuditService.SUSPICIOUS_PATTERN_THRESHOLD > 0


# =============================================================================
# Event Prefix Tests
# =============================================================================


class TestEventPrefixes:
    """Tests for event type prefix patterns."""

    def test_auth_events_have_auth_prefix(self):
        """Test auth events have auth. prefix."""
        auth_events = [
            SecurityEventType.LOGIN_SUCCESS,
            SecurityEventType.LOGIN_FAILED,
            SecurityEventType.LOGOUT,
            SecurityEventType.TOKEN_REFRESH,
            SecurityEventType.PASSWORD_CHANGED,
        ]
        for event in auth_events:
            assert event.value.startswith("auth.")

    def test_threat_events_have_threat_prefix(self):
        """Test threat events have threat. prefix."""
        threat_events = [
            SecurityEventType.SUSPICIOUS_REQUEST,
            SecurityEventType.BRUTE_FORCE_DETECTED,
            SecurityEventType.INJECTION_ATTEMPT,
            SecurityEventType.PATH_TRAVERSAL,
        ]
        for event in threat_events:
            assert event.value.startswith("threat.")

    def test_admin_events_have_admin_prefix(self):
        """Test admin events have admin. prefix."""
        admin_events = [
            SecurityEventType.USER_CREATED,
            SecurityEventType.USER_UPDATED,
            SecurityEventType.USER_DELETED,
            SecurityEventType.USER_SUSPENDED,
            SecurityEventType.ROLE_CHANGED,
        ]
        for event in admin_events:
            assert event.value.startswith("admin.")


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in security auditing."""

    def test_service_can_be_created_without_db(self):
        """Test service can be created with no database."""
        service = SecurityAuditService(db=None)
        assert service.db is None

    def test_all_event_types_are_strings(self):
        """Test all event type values are strings."""
        for event_type in SecurityEventType:
            assert isinstance(event_type.value, str)

    def test_all_severity_values_are_strings(self):
        """Test all severity values are strings."""
        for severity in SecuritySeverity:
            assert isinstance(severity.value, str)

    def test_thresholds_are_integers(self):
        """Test all thresholds are integers."""
        assert isinstance(SecurityAuditService.FAILED_LOGIN_THRESHOLD, int)
        assert isinstance(SecurityAuditService.RATE_LIMIT_THRESHOLD, int)
        assert isinstance(SecurityAuditService.SUSPICIOUS_PATTERN_THRESHOLD, int)
