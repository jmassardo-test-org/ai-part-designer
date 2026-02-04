"""
Tests for Abuse Detection Service.

Tests violation types, severity configuration, ban durations,
and escalation rules.
"""

import pytest

from app.services.abuse_detection import (
    ViolationType,
    BanDuration,
    VIOLATION_SEVERITY,
)


# =============================================================================
# Violation Type Tests
# =============================================================================

class TestViolationType:
    """Tests for violation type enum."""

    def test_weapon_content(self):
        """Test weapon content violation type."""
        assert ViolationType.WEAPON_CONTENT == "weapon_content"

    def test_illegal_content(self):
        """Test illegal content violation type."""
        assert ViolationType.ILLEGAL_CONTENT == "illegal_content"

    def test_rate_limit_abuse(self):
        """Test rate limit abuse violation type."""
        assert ViolationType.RATE_LIMIT_ABUSE == "rate_limit_abuse"

    def test_prompt_injection(self):
        """Test prompt injection violation type."""
        assert ViolationType.PROMPT_INJECTION == "prompt_injection"

    def test_account_abuse(self):
        """Test account abuse violation type."""
        assert ViolationType.ACCOUNT_ABUSE == "account_abuse"

    def test_spam(self):
        """Test spam violation type."""
        assert ViolationType.SPAM == "spam"

    def test_evasion_attempt(self):
        """Test evasion attempt violation type."""
        assert ViolationType.EVASION_ATTEMPT == "evasion_attempt"

    def test_tos_violation(self):
        """Test TOS violation type."""
        assert ViolationType.TOS_VIOLATION == "tos_violation"

    def test_off_topic_abuse(self):
        """Test off-topic abuse violation type."""
        assert ViolationType.OFF_TOPIC_ABUSE == "off_topic_abuse"

    def test_api_proxy_abuse(self):
        """Test API proxy abuse violation type."""
        assert ViolationType.API_PROXY_ABUSE == "api_proxy_abuse"


# =============================================================================
# Ban Duration Tests
# =============================================================================

class TestBanDuration:
    """Tests for ban duration enum."""

    def test_warning(self):
        """Test warning ban duration."""
        assert BanDuration.WARNING == "warning"

    def test_1_hour(self):
        """Test 1 hour ban duration."""
        assert BanDuration.HOUR_1 == "1_hour"

    def test_24_hours(self):
        """Test 24 hours ban duration."""
        assert BanDuration.HOUR_24 == "24_hours"

    def test_7_days(self):
        """Test 7 days ban duration."""
        assert BanDuration.DAYS_7 == "7_days"

    def test_30_days(self):
        """Test 30 days ban duration."""
        assert BanDuration.DAYS_30 == "30_days"

    def test_permanent(self):
        """Test permanent ban duration."""
        assert BanDuration.PERMANENT == "permanent"


# =============================================================================
# Violation Severity Tests
# =============================================================================

class TestViolationSeverity:
    """Tests for violation severity configuration."""

    def test_weapon_content_is_critical(self):
        """Test that weapon content has critical severity."""
        config = VIOLATION_SEVERITY[ViolationType.WEAPON_CONTENT]
        
        assert config["base_severity"] == "critical"
        assert config["first_offense"] == BanDuration.PERMANENT

    def test_illegal_content_is_critical(self):
        """Test that illegal content has critical severity."""
        config = VIOLATION_SEVERITY[ViolationType.ILLEGAL_CONTENT]
        
        assert config["base_severity"] == "critical"
        assert config["first_offense"] == BanDuration.PERMANENT

    def test_prompt_injection_is_high(self):
        """Test that prompt injection has high severity."""
        config = VIOLATION_SEVERITY[ViolationType.PROMPT_INJECTION]
        
        assert config["base_severity"] == "high"
        assert config["first_offense"] == BanDuration.HOUR_24
        assert config["escalation"] == BanDuration.DAYS_7

    def test_evasion_is_high(self):
        """Test that evasion has high severity."""
        config = VIOLATION_SEVERITY[ViolationType.EVASION_ATTEMPT]
        
        assert config["base_severity"] == "high"
        assert config["first_offense"] == BanDuration.DAYS_7
        assert config["escalation"] == BanDuration.PERMANENT

    def test_api_proxy_abuse_is_high(self):
        """Test that API proxy abuse has high severity."""
        config = VIOLATION_SEVERITY[ViolationType.API_PROXY_ABUSE]
        
        assert config["base_severity"] == "high"
        assert config["first_offense"] == BanDuration.DAYS_7

    def test_rate_limit_abuse_has_escalation(self):
        """Test that rate limit abuse escalates properly."""
        config = VIOLATION_SEVERITY[ViolationType.RATE_LIMIT_ABUSE]
        
        assert config["base_severity"] == "medium"
        assert config["first_offense"] == BanDuration.WARNING
        assert config["second_offense"] == BanDuration.HOUR_1
        assert config["third_offense"] == BanDuration.HOUR_24
        assert config["escalation"] == BanDuration.DAYS_7

    def test_account_abuse_is_medium(self):
        """Test that account abuse is medium severity."""
        config = VIOLATION_SEVERITY[ViolationType.ACCOUNT_ABUSE]
        
        assert config["base_severity"] == "medium"
        assert config["first_offense"] == BanDuration.HOUR_24

    def test_off_topic_abuse_is_medium(self):
        """Test that off-topic abuse is medium severity."""
        config = VIOLATION_SEVERITY[ViolationType.OFF_TOPIC_ABUSE]
        
        assert config["base_severity"] == "medium"
        assert config["first_offense"] == BanDuration.WARNING
        assert config["third_offense"] == BanDuration.HOUR_1

    def test_spam_is_low(self):
        """Test that spam has low severity."""
        config = VIOLATION_SEVERITY[ViolationType.SPAM]
        
        assert config["base_severity"] == "low"
        assert config["first_offense"] == BanDuration.WARNING
        assert config["second_offense"] == BanDuration.WARNING

    def test_tos_violation_is_low(self):
        """Test that TOS violation has low severity."""
        config = VIOLATION_SEVERITY[ViolationType.TOS_VIOLATION]
        
        assert config["base_severity"] == "low"
        assert config["first_offense"] == BanDuration.WARNING
        assert config["escalation"] == BanDuration.DAYS_7


# =============================================================================
# Configuration Completeness Tests
# =============================================================================

class TestConfigurationCompleteness:
    """Tests for configuration completeness."""

    def test_all_violation_types_have_config(self):
        """Test that all violation types have severity config."""
        for violation_type in ViolationType:
            assert violation_type in VIOLATION_SEVERITY, \
                f"Missing config for {violation_type}"
            
            config = VIOLATION_SEVERITY[violation_type]
            assert "base_severity" in config
            assert "first_offense" in config

    def test_all_configs_have_escalation(self):
        """Test that all configs have escalation defined."""
        for violation_type in ViolationType:
            config = VIOLATION_SEVERITY[violation_type]
            assert "escalation" in config, \
                f"Missing escalation for {violation_type}"

    def test_critical_violations_permanent_ban(self):
        """Test that critical violations result in permanent ban."""
        critical_types = [
            ViolationType.WEAPON_CONTENT,
            ViolationType.ILLEGAL_CONTENT,
        ]
        
        for vtype in critical_types:
            config = VIOLATION_SEVERITY[vtype]
            assert config["base_severity"] == "critical"
            assert config["first_offense"] == BanDuration.PERMANENT
            assert config["escalation"] == BanDuration.PERMANENT


# =============================================================================
# Escalation Logic Tests
# =============================================================================

class TestEscalationLogic:
    """Tests for violation escalation logic."""

    def test_first_offense_always_defined(self):
        """Test that first offense is always defined."""
        for violation_type in ViolationType:
            config = VIOLATION_SEVERITY[violation_type]
            assert "first_offense" in config

    def test_warning_is_not_a_ban(self):
        """Test that warning is distinct from bans."""
        assert BanDuration.WARNING.value == "warning"
        # Violations that start with warnings
        warning_violations = [
            ViolationType.RATE_LIMIT_ABUSE,
            ViolationType.SPAM,
            ViolationType.TOS_VIOLATION,
            ViolationType.OFF_TOPIC_ABUSE,
        ]
        
        for vtype in warning_violations:
            config = VIOLATION_SEVERITY[vtype]
            assert config["first_offense"] == BanDuration.WARNING

    def test_medium_severity_gradual_escalation(self):
        """Test medium severity has gradual escalation."""
        config = VIOLATION_SEVERITY[ViolationType.RATE_LIMIT_ABUSE]
        
        # Should escalate: warning -> 1h -> 24h -> 7d
        assert config["first_offense"] == BanDuration.WARNING
        assert config["second_offense"] == BanDuration.HOUR_1
        assert config["third_offense"] == BanDuration.HOUR_24
        assert config["escalation"] == BanDuration.DAYS_7

    def test_high_severity_quick_escalation(self):
        """Test high severity has quick escalation."""
        config = VIOLATION_SEVERITY[ViolationType.EVASION_ATTEMPT]
        
        # Should go to 7 days immediately, then permanent
        assert config["first_offense"] == BanDuration.DAYS_7
        assert config["escalation"] == BanDuration.PERMANENT


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_ban_duration_values_are_strings(self):
        """Test all ban durations are string values."""
        for duration in BanDuration:
            assert isinstance(duration.value, str)

    def test_violation_type_values_are_strings(self):
        """Test all violation types are string values."""
        for vtype in ViolationType:
            assert isinstance(vtype.value, str)

    def test_severity_levels_valid(self):
        """Test all severity levels are valid."""
        valid_severities = {"low", "medium", "high", "critical"}
        
        for violation_type in ViolationType:
            config = VIOLATION_SEVERITY[violation_type]
            assert config["base_severity"] in valid_severities
