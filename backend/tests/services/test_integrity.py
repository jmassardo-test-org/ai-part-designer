"""
Tests for Data Integrity Service.

Tests integrity check types, severity levels, issue tracking, and report generation.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.services.integrity import (
    IntegrityCheckType,
    IntegritySeverity,
    IntegrityIssue,
    IntegrityReport,
)


# =============================================================================
# IntegrityCheckType Tests
# =============================================================================

class TestIntegrityCheckType:
    """Tests for IntegrityCheckType enum."""

    def test_orphaned_records(self):
        """Test orphaned records check type."""
        assert IntegrityCheckType.ORPHANED_RECORDS == "orphaned_records"

    def test_missing_files(self):
        """Test missing files check type."""
        assert IntegrityCheckType.MISSING_FILES == "missing_files"

    def test_checksum_validation(self):
        """Test checksum validation check type."""
        assert IntegrityCheckType.CHECKSUM_VALIDATION == "checksum_validation"

    def test_referential_integrity(self):
        """Test referential integrity check type."""
        assert IntegrityCheckType.REFERENTIAL_INTEGRITY == "referential_integrity"

    def test_storage_consistency(self):
        """Test storage consistency check type."""
        assert IntegrityCheckType.STORAGE_CONSISTENCY == "storage_consistency"

    def test_all_types_are_strings(self):
        """Test all check types are strings."""
        for check_type in IntegrityCheckType:
            assert isinstance(check_type.value, str)


# =============================================================================
# IntegritySeverity Tests
# =============================================================================

class TestIntegritySeverity:
    """Tests for IntegritySeverity enum."""

    def test_info_severity(self):
        """Test info severity."""
        assert IntegritySeverity.INFO == "info"

    def test_warning_severity(self):
        """Test warning severity."""
        assert IntegritySeverity.WARNING == "warning"

    def test_error_severity(self):
        """Test error severity."""
        assert IntegritySeverity.ERROR == "error"

    def test_critical_severity(self):
        """Test critical severity."""
        assert IntegritySeverity.CRITICAL == "critical"

    def test_all_severities_are_strings(self):
        """Test all severities are strings."""
        for severity in IntegritySeverity:
            assert isinstance(severity.value, str)


# =============================================================================
# IntegrityIssue Tests
# =============================================================================

class TestIntegrityIssue:
    """Tests for IntegrityIssue dataclass."""

    def test_basic_creation(self):
        """Test creating a basic integrity issue."""
        issue = IntegrityIssue(
            check_type=IntegrityCheckType.ORPHANED_RECORDS,
            severity=IntegritySeverity.WARNING,
        )
        
        assert issue.check_type == IntegrityCheckType.ORPHANED_RECORDS
        assert issue.severity == IntegritySeverity.WARNING
        assert issue.table is None
        assert issue.record_id is None
        assert issue.message == ""
        assert issue.details == {}

    def test_detailed_creation(self):
        """Test creating a detailed integrity issue."""
        issue = IntegrityIssue(
            check_type=IntegrityCheckType.MISSING_FILES,
            severity=IntegritySeverity.ERROR,
            table="design_files",
            record_id="abc123",
            message="Referenced file not found in storage",
            details={"file_path": "/uploads/design.step"},
        )
        
        assert issue.table == "design_files"
        assert issue.record_id == "abc123"
        assert "file not found" in issue.message
        assert issue.details["file_path"] == "/uploads/design.step"

    def test_to_dict(self):
        """Test converting issue to dictionary."""
        issue = IntegrityIssue(
            check_type=IntegrityCheckType.CHECKSUM_VALIDATION,
            severity=IntegritySeverity.CRITICAL,
            table="backups",
            record_id="backup-001",
            message="Checksum mismatch",
        )
        
        data = issue.to_dict()
        
        assert data["check_type"] == "checksum_validation"
        assert data["severity"] == "critical"
        assert data["table"] == "backups"
        assert data["record_id"] == "backup-001"
        assert data["message"] == "Checksum mismatch"
        assert "detected_at" in data

    def test_detected_at_auto_generated(self):
        """Test that detected_at is auto-generated."""
        issue = IntegrityIssue(
            check_type=IntegrityCheckType.STORAGE_CONSISTENCY,
            severity=IntegritySeverity.INFO,
        )
        
        assert issue.detected_at is not None
        assert isinstance(issue.detected_at, datetime)


# =============================================================================
# IntegrityReport Tests
# =============================================================================

class TestIntegrityReport:
    """Tests for IntegrityReport dataclass."""

    def test_default_creation(self):
        """Test creating a default report."""
        report = IntegrityReport()
        
        assert report.started_at is not None
        assert report.completed_at is None
        assert report.checks_run == []
        assert report.issues == []
        assert report.stats == {}

    def test_is_healthy_with_no_issues(self):
        """Test is_healthy returns True with no issues."""
        report = IntegrityReport()
        
        assert report.is_healthy is True

    def test_is_healthy_with_info_warning(self):
        """Test is_healthy returns True with only info/warning."""
        report = IntegrityReport(
            issues=[
                IntegrityIssue(
                    check_type=IntegrityCheckType.ORPHANED_RECORDS,
                    severity=IntegritySeverity.INFO,
                ),
                IntegrityIssue(
                    check_type=IntegrityCheckType.MISSING_FILES,
                    severity=IntegritySeverity.WARNING,
                ),
            ]
        )
        
        assert report.is_healthy is True

    def test_is_healthy_with_error(self):
        """Test is_healthy returns False with error."""
        report = IntegrityReport(
            issues=[
                IntegrityIssue(
                    check_type=IntegrityCheckType.CHECKSUM_VALIDATION,
                    severity=IntegritySeverity.ERROR,
                ),
            ]
        )
        
        assert report.is_healthy is False

    def test_is_healthy_with_critical(self):
        """Test is_healthy returns False with critical."""
        report = IntegrityReport(
            issues=[
                IntegrityIssue(
                    check_type=IntegrityCheckType.REFERENTIAL_INTEGRITY,
                    severity=IntegritySeverity.CRITICAL,
                ),
            ]
        )
        
        assert report.is_healthy is False

    def test_issue_counts_empty(self):
        """Test issue_counts with no issues."""
        report = IntegrityReport()
        
        counts = report.issue_counts
        
        assert counts["info"] == 0
        assert counts["warning"] == 0
        assert counts["error"] == 0
        assert counts["critical"] == 0

    def test_issue_counts_with_issues(self):
        """Test issue_counts with various issues."""
        report = IntegrityReport(
            issues=[
                IntegrityIssue(
                    check_type=IntegrityCheckType.ORPHANED_RECORDS,
                    severity=IntegritySeverity.INFO,
                ),
                IntegrityIssue(
                    check_type=IntegrityCheckType.ORPHANED_RECORDS,
                    severity=IntegritySeverity.INFO,
                ),
                IntegrityIssue(
                    check_type=IntegrityCheckType.MISSING_FILES,
                    severity=IntegritySeverity.WARNING,
                ),
                IntegrityIssue(
                    check_type=IntegrityCheckType.CHECKSUM_VALIDATION,
                    severity=IntegritySeverity.ERROR,
                ),
            ]
        )
        
        counts = report.issue_counts
        
        assert counts["info"] == 2
        assert counts["warning"] == 1
        assert counts["error"] == 1
        assert counts["critical"] == 0

    def test_with_checks_run(self):
        """Test report with checks_run list."""
        report = IntegrityReport(
            checks_run=[
                IntegrityCheckType.ORPHANED_RECORDS,
                IntegrityCheckType.MISSING_FILES,
                IntegrityCheckType.CHECKSUM_VALIDATION,
            ]
        )
        
        assert len(report.checks_run) == 3
        assert IntegrityCheckType.ORPHANED_RECORDS in report.checks_run

    def test_with_stats(self):
        """Test report with stats dictionary."""
        report = IntegrityReport(
            stats={
                "tables_checked": 15,
                "records_scanned": 50000,
                "files_verified": 1200,
                "duration_seconds": 45.3,
            }
        )
        
        assert report.stats["tables_checked"] == 15
        assert report.stats["records_scanned"] == 50000


# =============================================================================
# Edge Cases
# =============================================================================

class TestIntegrityEdgeCases:
    """Tests for edge cases in integrity module."""

    def test_empty_message(self):
        """Test issue with empty message."""
        issue = IntegrityIssue(
            check_type=IntegrityCheckType.STORAGE_CONSISTENCY,
            severity=IntegritySeverity.INFO,
            message="",
        )
        
        assert issue.message == ""

    def test_long_message(self):
        """Test issue with very long message."""
        long_message = "A" * 10000
        issue = IntegrityIssue(
            check_type=IntegrityCheckType.ORPHANED_RECORDS,
            severity=IntegritySeverity.WARNING,
            message=long_message,
        )
        
        assert len(issue.message) == 10000

    def test_complex_details(self):
        """Test issue with complex details structure."""
        details = {
            "affected_records": ["id1", "id2", "id3"],
            "expected_checksum": "abc123",
            "actual_checksum": "def456",
            "file_metadata": {
                "size": 1024,
                "modified": "2024-01-15T10:00:00",
            },
        }
        issue = IntegrityIssue(
            check_type=IntegrityCheckType.CHECKSUM_VALIDATION,
            severity=IntegritySeverity.ERROR,
            details=details,
        )
        
        data = issue.to_dict()
        assert data["details"]["affected_records"] == ["id1", "id2", "id3"]
        assert data["details"]["file_metadata"]["size"] == 1024

    def test_report_with_many_issues(self):
        """Test report with many issues."""
        issues = [
            IntegrityIssue(
                check_type=IntegrityCheckType.ORPHANED_RECORDS,
                severity=IntegritySeverity.WARNING,
                record_id=str(i),
            )
            for i in range(100)
        ]
        report = IntegrityReport(issues=issues)
        
        assert len(report.issues) == 100
        assert report.issue_counts["warning"] == 100
        assert report.is_healthy is True  # Warnings don't make unhealthy

    def test_mixed_severity_report(self):
        """Test report with mixed severity issues."""
        report = IntegrityReport(
            issues=[
                IntegrityIssue(
                    check_type=IntegrityCheckType.ORPHANED_RECORDS,
                    severity=IntegritySeverity.INFO,
                ),
                IntegrityIssue(
                    check_type=IntegrityCheckType.MISSING_FILES,
                    severity=IntegritySeverity.WARNING,
                ),
                IntegrityIssue(
                    check_type=IntegrityCheckType.CHECKSUM_VALIDATION,
                    severity=IntegritySeverity.ERROR,
                ),
                IntegrityIssue(
                    check_type=IntegrityCheckType.REFERENTIAL_INTEGRITY,
                    severity=IntegritySeverity.CRITICAL,
                ),
            ]
        )
        
        counts = report.issue_counts
        assert counts["info"] == 1
        assert counts["warning"] == 1
        assert counts["error"] == 1
        assert counts["critical"] == 1
        assert report.is_healthy is False
