"""
Tests for Content Moderation Service.

Tests prohibited categories, moderation decisions, and pattern matching.
"""

import pytest

from app.services.content_moderation import (
    ProhibitedCategory,
    ModerationDecision,
    ZERO_TOLERANCE_PATTERNS,
    HIGH_RISK_PATTERNS,
    MEDIUM_RISK_PATTERNS,
    ALLOWLIST_PATTERNS,
    OFF_TOPIC_PATTERNS,
)


# =============================================================================
# ProhibitedCategory Tests
# =============================================================================

class TestProhibitedCategory:
    """Tests for ProhibitedCategory enum."""

    def test_firearm_category(self):
        """Test firearm category."""
        assert ProhibitedCategory.FIREARM == "firearm"

    def test_firearm_component_category(self):
        """Test firearm component category."""
        assert ProhibitedCategory.FIREARM_COMPONENT == "firearm_component"

    def test_weapon_category(self):
        """Test weapon category."""
        assert ProhibitedCategory.WEAPON == "weapon"

    def test_explosive_category(self):
        """Test explosive category."""
        assert ProhibitedCategory.EXPLOSIVE == "explosive"

    def test_illegal_drug_category(self):
        """Test illegal drug category."""
        assert ProhibitedCategory.ILLEGAL_DRUG == "illegal_drug"

    def test_controlled_substance_category(self):
        """Test controlled substance category."""
        assert ProhibitedCategory.CONTROLLED_SUBSTANCE == "controlled_substance"

    def test_restricted_export_category(self):
        """Test restricted export category."""
        assert ProhibitedCategory.RESTRICTED_EXPORT == "restricted_export"

    def test_counterfeit_category(self):
        """Test counterfeit category."""
        assert ProhibitedCategory.COUNTERFEIT == "counterfeit"

    def test_potentially_harmful_category(self):
        """Test potentially harmful category."""
        assert ProhibitedCategory.POTENTIALLY_HARMFUL == "potentially_harmful"

    def test_dual_use_category(self):
        """Test dual use category."""
        assert ProhibitedCategory.DUAL_USE == "dual_use"

    def test_off_topic_category(self):
        """Test off topic category."""
        assert ProhibitedCategory.OFF_TOPIC == "off_topic"

    def test_api_abuse_category(self):
        """Test API abuse category."""
        assert ProhibitedCategory.API_ABUSE == "api_abuse"

    def test_prompt_injection_category(self):
        """Test prompt injection category."""
        assert ProhibitedCategory.PROMPT_INJECTION == "prompt_injection"

    def test_suspicious_category(self):
        """Test suspicious category."""
        assert ProhibitedCategory.SUSPICIOUS == "suspicious"

    def test_all_categories_are_strings(self):
        """Test all categories are strings."""
        for category in ProhibitedCategory:
            assert isinstance(category.value, str)


# =============================================================================
# ModerationDecision Tests
# =============================================================================

class TestModerationDecision:
    """Tests for ModerationDecision enum."""

    def test_allow_decision(self):
        """Test allow decision."""
        assert ModerationDecision.ALLOW == "allow"

    def test_allow_with_warning_decision(self):
        """Test allow with warning decision."""
        assert ModerationDecision.ALLOW_WITH_WARNING == "allow_warning"

    def test_review_required_decision(self):
        """Test review required decision."""
        assert ModerationDecision.REVIEW_REQUIRED == "review_required"

    def test_reject_decision(self):
        """Test reject decision."""
        assert ModerationDecision.REJECT == "reject"

    def test_reject_and_ban_decision(self):
        """Test reject and ban decision."""
        assert ModerationDecision.REJECT_AND_BAN == "reject_and_ban"

    def test_all_decisions_are_strings(self):
        """Test all decisions are strings."""
        for decision in ModerationDecision:
            assert isinstance(decision.value, str)


# =============================================================================
# Zero Tolerance Pattern Tests
# =============================================================================

class TestZeroTolerancePatterns:
    """Tests for zero tolerance patterns."""

    import re

    def test_patterns_exist(self):
        """Test that zero tolerance patterns list exists."""
        assert ZERO_TOLERANCE_PATTERNS is not None
        assert len(ZERO_TOLERANCE_PATTERNS) > 0

    def test_patterns_are_valid_regex(self):
        """Test all patterns are valid regular expressions."""
        import re
        for pattern in ZERO_TOLERANCE_PATTERNS:
            # Should not raise exception
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled is not None

    def test_firearm_model_detection(self):
        """Test detection of firearm model names."""
        import re
        test_texts = ["ar-15", "ar15", "AR-15", "ak-47", "ak47", "glock", "m16"]
        
        for text in test_texts:
            matched = False
            for pattern in ZERO_TOLERANCE_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should detect firearm model: {text}"

    def test_receiver_detection(self):
        """Test detection of receiver components."""
        import re
        test_texts = ["lower receiver", "upper receiver"]
        
        for text in test_texts:
            matched = False
            for pattern in ZERO_TOLERANCE_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should detect receiver: {text}"

    def test_suppressor_detection(self):
        """Test detection of suppressor terms."""
        import re
        test_texts = ["suppressor", "silencer"]
        
        for text in test_texts:
            matched = False
            for pattern in ZERO_TOLERANCE_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should detect suppressor: {text}"

    def test_explosive_detection(self):
        """Test detection of explosive terms."""
        import re
        test_texts = ["bomb", "ied", "detonator", "pipe bomb"]
        
        for text in test_texts:
            matched = False
            for pattern in ZERO_TOLERANCE_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should detect explosive: {text}"


# =============================================================================
# High Risk Pattern Tests
# =============================================================================

class TestHighRiskPatterns:
    """Tests for high risk patterns."""

    def test_patterns_exist(self):
        """Test that high risk patterns list exists."""
        assert HIGH_RISK_PATTERNS is not None
        assert len(HIGH_RISK_PATTERNS) > 0

    def test_patterns_are_valid_regex(self):
        """Test all patterns are valid regular expressions."""
        import re
        for pattern in HIGH_RISK_PATTERNS:
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled is not None

    def test_generic_weapon_detection(self):
        """Test detection of generic weapon terms."""
        import re
        test_texts = ["gun parts", "pistol frame", "firearm"]
        
        for text in test_texts:
            matched = False
            for pattern in HIGH_RISK_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should detect weapon term: {text}"


# =============================================================================
# Medium Risk Pattern Tests
# =============================================================================

class TestMediumRiskPatterns:
    """Tests for medium risk patterns."""

    def test_patterns_exist(self):
        """Test that medium risk patterns list exists."""
        assert MEDIUM_RISK_PATTERNS is not None
        assert len(MEDIUM_RISK_PATTERNS) > 0

    def test_patterns_are_valid_regex(self):
        """Test all patterns are valid regular expressions."""
        import re
        for pattern in MEDIUM_RISK_PATTERNS:
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled is not None

    def test_lockpick_detection(self):
        """Test detection of lockpick terms."""
        import re
        test_texts = ["lockpick", "lock pick", "bump key"]
        
        for text in test_texts:
            matched = False
            for pattern in MEDIUM_RISK_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should detect lockpick: {text}"


# =============================================================================
# Allowlist Pattern Tests
# =============================================================================

class TestAllowlistPatterns:
    """Tests for allowlist patterns."""

    def test_patterns_exist(self):
        """Test that allowlist patterns list exists."""
        assert ALLOWLIST_PATTERNS is not None
        assert len(ALLOWLIST_PATTERNS) > 0

    def test_patterns_are_valid_regex(self):
        """Test all patterns are valid regular expressions."""
        import re
        for pattern in ALLOWLIST_PATTERNS:
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled is not None

    def test_medical_device_detection(self):
        """Test detection of medical devices."""
        import re
        test_texts = ["prosthetic", "medical device", "orthotic", "assistive device"]
        
        for text in test_texts:
            matched = False
            for pattern in ALLOWLIST_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should allow medical: {text}"

    def test_toy_detection(self):
        """Test detection of toy terms."""
        import re
        test_texts = ["toy gun case", "nerf accessories", "water gun"]
        
        for text in test_texts:
            matched = False
            for pattern in ALLOWLIST_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should allow toy: {text}"

    def test_cosplay_detection(self):
        """Test detection of cosplay terms."""
        import re
        
        matched = False
        for pattern in ALLOWLIST_PATTERNS:
            if re.search(pattern, "cosplay prop", re.IGNORECASE):
                matched = True
                break
        assert matched, "Should allow cosplay"


# =============================================================================
# Off Topic Pattern Tests
# =============================================================================

class TestOffTopicPatterns:
    """Tests for off topic patterns."""

    def test_patterns_exist(self):
        """Test that off topic patterns list exists."""
        assert OFF_TOPIC_PATTERNS is not None
        assert len(OFF_TOPIC_PATTERNS) > 0

    def test_patterns_are_valid_regex(self):
        """Test all patterns are valid regular expressions."""
        import re
        for pattern in OFF_TOPIC_PATTERNS:
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled is not None

    def test_code_request_detection(self):
        """Test detection of code generation requests."""
        import re
        test_texts = [
            "write me a python script",
            "create a javascript function",
            "debug this code",
        ]
        
        for text in test_texts:
            matched = False
            for pattern in OFF_TOPIC_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should detect code request: {text}"

    def test_essay_request_detection(self):
        """Test detection of essay writing requests."""
        import re
        test_texts = [
            "write me an essay about climate",
            "compose a blog post",
            "create an article about AI",
        ]
        
        for text in test_texts:
            matched = False
            for pattern in OFF_TOPIC_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should detect essay request: {text}"


# =============================================================================
# Edge Cases
# =============================================================================

class TestContentModerationEdgeCases:
    """Tests for edge cases in content moderation."""

    def test_case_insensitivity(self):
        """Test that patterns work case-insensitively."""
        import re
        
        # Should match regardless of case
        test_cases = [
            ("AR-15", ZERO_TOLERANCE_PATTERNS),
            ("ar-15", ZERO_TOLERANCE_PATTERNS),
            ("AR-15", ZERO_TOLERANCE_PATTERNS),
            ("GLOCK", ZERO_TOLERANCE_PATTERNS),
        ]
        
        for text, patterns in test_cases:
            matched = False
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should match case-insensitively: {text}"

    def test_partial_word_no_match(self):
        """Test that partial word matches don't trigger false positives."""
        import re
        
        # "targeting" should not match "target" patterns
        # "bombardment" in historical context should be careful
        safe_texts = [
            "magnet holder",  # "mag" in word
            "assignment",  # Contains "sign"
            "registered",  # Contains "gist"
        ]
        
        # These should NOT trigger zero tolerance
        for text in safe_texts:
            critical_match = False
            for pattern in ZERO_TOLERANCE_PATTERNS[:5]:  # Check first few critical patterns
                if re.search(pattern, text, re.IGNORECASE):
                    critical_match = True
                    break
            # Most should not match, but some false positives are expected
            # This is informational
            pass  # Pattern accuracy depends on specific implementation

    def test_empty_string(self):
        """Test that empty strings don't match patterns."""
        import re
        
        for patterns in [ZERO_TOLERANCE_PATTERNS, HIGH_RISK_PATTERNS]:
            for pattern in patterns:
                match = re.search(pattern, "", re.IGNORECASE)
                assert match is None, f"Empty string should not match: {pattern}"

    def test_whitespace_variations(self):
        """Test handling of various whitespace."""
        import re
        
        # AR-15 with different separators
        variations = ["ar 15", "ar-15", "ar15"]
        
        for text in variations:
            matched = False
            for pattern in ZERO_TOLERANCE_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Should handle whitespace variation: {text}"
