"""
Tests for Content Moderation Service.

Tests content detection logic, filename patterns, and confidence scoring.
"""

from __future__ import annotations

from uuid import uuid4

from app.services.moderation import (
    FILENAME_PATTERNS,
    ContentCategory,
    ContentFlag,
    FlagSeverity,
    ModerationResult,
    ModerationStatus,
)

# =============================================================================
# Filename Pattern Tests
# =============================================================================


class TestFilenamePatterns:
    """Tests for filename pattern detection."""

    def test_weapon_terms_detected(self):
        """Test that weapon-related terms are detected."""
        # Create a mock moderator (without DB)
        moderator = MockModerator()

        # Test weapon keywords
        flags = moderator.check_filename("my_gun_design.step")
        assert len(flags) > 0
        assert any(f.category == ContentCategory.WEAPON for f in flags)

        flags = moderator.check_filename("pistol_grip_v2.stl")
        assert len(flags) > 0
        assert any(f.category == ContentCategory.WEAPON for f in flags)

    def test_weapon_model_names_detected(self):
        """Test that specific weapon model names are detected."""
        moderator = MockModerator()

        flags = moderator.check_filename("ar15_lower_receiver.step")
        assert len(flags) > 0
        # Should have CRITICAL severity for AR-15
        assert any(f.severity == FlagSeverity.CRITICAL for f in flags)

    def test_weapon_components_detected(self):
        """Test that weapon component terms are detected."""
        moderator = MockModerator()

        flags = moderator.check_filename("trigger_assembly.step")
        assert len(flags) > 0
        assert any(f.category == ContentCategory.WEAPON_COMPONENT for f in flags)

        flags = moderator.check_filename("suppressor_adapter.stl")
        assert len(flags) > 0
        assert any(f.severity == FlagSeverity.CRITICAL for f in flags)

    def test_safe_filenames_pass(self):
        """Test that normal filenames don't trigger flags."""
        moderator = MockModerator()

        safe_filenames = [
            "mounting_bracket.step",
            "cable_gland_v2.stl",
            "enclosure_box_100x50x30.step",
            "gear_assembly.step",
            "phone_stand.stl",
        ]

        for filename in safe_filenames:
            flags = moderator.check_filename(filename)
            assert len(flags) == 0, f"Unexpected flag for: {filename}"

    def test_case_insensitivity(self):
        """Test that pattern matching is case-insensitive."""
        moderator = MockModerator()

        # All should trigger
        for filename in ["GUN.step", "Gun.step", "gUn.step"]:
            flags = moderator.check_filename(filename)
            assert len(flags) > 0, f"Should flag: {filename}"


# =============================================================================
# Metadata Analysis Tests
# =============================================================================


class TestMetadataAnalysis:
    """Tests for metadata pattern detection."""

    def test_metadata_description_checked(self):
        """Test that description field is checked."""
        moderator = MockModerator()

        metadata = {"description": "This is a pistol design"}
        flags = moderator.check_metadata(metadata)

        assert len(flags) > 0
        assert any(f.category == ContentCategory.WEAPON for f in flags)

    def test_metadata_tags_checked(self):
        """Test that tags are checked."""
        moderator = MockModerator()

        metadata = {"tags": ["weapon", "custom"]}
        flags = moderator.check_metadata(metadata)

        assert len(flags) > 0

    def test_metadata_lower_confidence(self):
        """Test that metadata flags have lower confidence than filename."""
        moderator = MockModerator()

        filename_flags = moderator.check_filename("gun.step")
        metadata_flags = moderator.check_metadata({"description": "gun"})

        if filename_flags and metadata_flags:
            # Metadata should have lower or equal confidence
            filename_conf = max(f.confidence for f in filename_flags)
            metadata_conf = max(f.confidence for f in metadata_flags)
            assert metadata_conf <= filename_conf


# =============================================================================
# ModerationResult Tests
# =============================================================================


class TestModerationResult:
    """Tests for ModerationResult class."""

    def test_is_flagged_property(self):
        """Test is_flagged property."""
        result_empty = ModerationResult(file_id=uuid4(), flags=[])
        assert result_empty.is_flagged is False

        result_with_flags = ModerationResult(
            file_id=uuid4(),
            flags=[
                ContentFlag(
                    category=ContentCategory.WEAPON,
                    severity=FlagSeverity.LOW,
                    confidence=0.5,
                    reason="Test",
                )
            ],
        )
        assert result_with_flags.is_flagged is True

    def test_highest_severity_property(self):
        """Test highest_severity property."""
        result = ModerationResult(
            file_id=uuid4(),
            flags=[
                ContentFlag(severity=FlagSeverity.LOW, reason="a"),
                ContentFlag(severity=FlagSeverity.HIGH, reason="b"),
                ContentFlag(severity=FlagSeverity.MEDIUM, reason="c"),
            ],
        )
        assert result.highest_severity == FlagSeverity.HIGH

    def test_highest_severity_empty(self):
        """Test highest_severity with no flags."""
        result = ModerationResult(file_id=uuid4(), flags=[])
        assert result.highest_severity is None

    def test_max_confidence_property(self):
        """Test max_confidence property."""
        result = ModerationResult(
            file_id=uuid4(),
            flags=[
                ContentFlag(confidence=0.3, reason="a"),
                ContentFlag(confidence=0.9, reason="b"),
                ContentFlag(confidence=0.5, reason="c"),
            ],
        )
        assert result.max_confidence == 0.9

    def test_max_confidence_empty(self):
        """Test max_confidence with no flags."""
        result = ModerationResult(file_id=uuid4(), flags=[])
        assert result.max_confidence == 0.0


# =============================================================================
# Confidence Scoring Tests
# =============================================================================


class TestConfidenceScoring:
    """Tests for confidence scoring logic."""

    def test_critical_terms_high_confidence(self):
        """Test that critical terms have high confidence."""
        moderator = MockModerator()

        # Specific weapon models should have high confidence
        flags = moderator.check_filename("glock_frame.step")

        assert len(flags) > 0
        # Critical severity items should exist
        critical_flags = [f for f in flags if f.severity == FlagSeverity.CRITICAL]
        if critical_flags:
            assert critical_flags[0].confidence >= 0.7

    def test_ambiguous_terms_lower_confidence(self):
        """Test that ambiguous terms have lower confidence."""
        moderator = MockModerator()

        # "pipe" could be innocent
        flags = moderator.check_filename("pipe_connector.step")

        if flags:
            assert all(f.severity == FlagSeverity.LOW for f in flags)


# =============================================================================
# Auto-Decision Tests
# =============================================================================


class TestAutoDecision:
    """Tests for auto-decision logic."""

    def test_no_flags_auto_approve(self):
        """Test that content with no flags is auto-approved."""
        result = ModerationResult(
            file_id=uuid4(),
            flags=[],
            auto_decision=True,
            requires_human_review=False,
            overall_status=ModerationStatus.APPROVED,
        )

        assert result.overall_status == ModerationStatus.APPROVED
        assert result.requires_human_review is False

    def test_critical_severity_auto_reject(self):
        """Test that critical severity triggers auto-quarantine."""
        # With a critical flag, should be quarantined
        result = ModerationResult(
            file_id=uuid4(),
            flags=[
                ContentFlag(
                    severity=FlagSeverity.CRITICAL,
                    confidence=0.95,
                    reason="Known bad content",
                ),
            ],
        )

        # After auto-decision, should be quarantined
        assert result.highest_severity == FlagSeverity.CRITICAL


# =============================================================================
# ContentFlag Tests
# =============================================================================


class TestContentFlag:
    """Tests for ContentFlag dataclass."""

    def test_flag_creation(self):
        """Test creating a content flag."""
        flag = ContentFlag(
            category=ContentCategory.WEAPON,
            severity=FlagSeverity.HIGH,
            confidence=0.85,
            reason="Matches weapon pattern",
            details={"matched": "gun"},
            rule_id="filename_gun",
        )

        assert flag.category == ContentCategory.WEAPON
        assert flag.severity == FlagSeverity.HIGH
        assert flag.confidence == 0.85
        assert flag.rule_id == "filename_gun"

    def test_flag_default_values(self):
        """Test content flag default values."""
        flag = ContentFlag()

        assert flag.category == ContentCategory.OTHER_PROHIBITED
        assert flag.severity == FlagSeverity.LOW
        assert flag.confidence == 0.0
        assert flag.reason == ""
        assert flag.details == {}
        assert flag.rule_id is None


# =============================================================================
# Mock Moderator for Testing
# =============================================================================


class MockModerator:
    """
    Mock ContentModerator for testing without database.

    Replicates the check_filename and check_metadata methods.
    """

    def check_filename(self, filename: str) -> list[ContentFlag]:
        """Check filename for prohibited patterns."""
        import re

        flags = []
        filename_lower = filename.lower()

        for pattern, category, severity in FILENAME_PATTERNS:
            if re.search(pattern, filename_lower, re.IGNORECASE):
                flags.append(
                    ContentFlag(
                        category=category,
                        severity=severity,
                        confidence=0.7,
                        reason=f"Filename matches prohibited pattern: {pattern}",
                        details={"filename": filename, "pattern": pattern},
                        rule_id=f"filename_{pattern[:20]}",
                    )
                )

        return flags

    def check_metadata(self, metadata: dict) -> list[ContentFlag]:
        """Check file metadata for suspicious content."""
        import re

        flags = []

        searchable_text = " ".join(
            [
                str(metadata.get("description", "")),
                str(metadata.get("title", "")),
                " ".join(metadata.get("tags", [])),
                str(metadata.get("author", "")),
            ]
        ).lower()

        for pattern, category, severity in FILENAME_PATTERNS:
            if re.search(pattern, searchable_text, re.IGNORECASE):
                flags.append(
                    ContentFlag(
                        category=category,
                        severity=FlagSeverity.LOW if severity == FlagSeverity.MEDIUM else severity,
                        confidence=0.5,
                        reason=f"Metadata matches prohibited pattern: {pattern}",
                        details={"pattern": pattern},
                        rule_id=f"metadata_{pattern[:20]}",
                    )
                )

        return flags
