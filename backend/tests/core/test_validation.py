"""
Tests for Core Validation Module.

Tests validation severity levels, validation issues, and results.
"""

from datetime import datetime

from app.core.validation import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

# =============================================================================
# ValidationSeverity Tests
# =============================================================================


class TestValidationSeverity:
    """Tests for ValidationSeverity enum."""

    def test_error_severity(self):
        """Test error severity."""
        assert ValidationSeverity.ERROR == "error"

    def test_warning_severity(self):
        """Test warning severity."""
        assert ValidationSeverity.WARNING == "warning"

    def test_info_severity(self):
        """Test info severity."""
        assert ValidationSeverity.INFO == "info"

    def test_all_severities_are_strings(self):
        """Test all severities are strings."""
        for severity in ValidationSeverity:
            assert isinstance(severity.value, str)


# =============================================================================
# ValidationIssue Tests
# =============================================================================


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_basic_creation(self):
        """Test creating a basic validation issue."""
        issue = ValidationIssue(
            field="email",
            message="Invalid email format",
            severity=ValidationSeverity.ERROR,
        )

        assert issue.field == "email"
        assert issue.message == "Invalid email format"
        assert issue.severity == ValidationSeverity.ERROR

    def test_with_value(self):
        """Test issue with value."""
        issue = ValidationIssue(
            field="age",
            message="Age must be positive",
            severity=ValidationSeverity.ERROR,
            value=-5,
        )

        assert issue.value == -5

    def test_with_rule(self):
        """Test issue with rule identifier."""
        issue = ValidationIssue(
            field="password",
            message="Password too short",
            severity=ValidationSeverity.ERROR,
            rule="min_length",
        )

        assert issue.rule == "min_length"

    def test_default_values(self):
        """Test default values."""
        issue = ValidationIssue(
            field="test",
            message="test message",
            severity=ValidationSeverity.WARNING,
        )

        assert issue.value is None
        assert issue.rule is None


# =============================================================================
# ValidationResult Tests
# =============================================================================


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test a valid result."""
        result = ValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.issues == []

    def test_invalid_result(self):
        """Test an invalid result."""
        result = ValidationResult(is_valid=False)

        assert result.is_valid is False

    def test_with_issues(self):
        """Test result with issues."""
        issues = [
            ValidationIssue("field1", "error 1", ValidationSeverity.ERROR),
            ValidationIssue("field2", "warning 1", ValidationSeverity.WARNING),
        ]
        result = ValidationResult(is_valid=False, issues=issues)

        assert len(result.issues) == 2

    def test_errors_property(self):
        """Test errors property filters correctly."""
        issues = [
            ValidationIssue("f1", "e1", ValidationSeverity.ERROR),
            ValidationIssue("f2", "w1", ValidationSeverity.WARNING),
            ValidationIssue("f3", "e2", ValidationSeverity.ERROR),
            ValidationIssue("f4", "i1", ValidationSeverity.INFO),
        ]
        result = ValidationResult(is_valid=False, issues=issues)

        assert len(result.errors) == 2
        for error in result.errors:
            assert error.severity == ValidationSeverity.ERROR

    def test_warnings_property(self):
        """Test warnings property filters correctly."""
        issues = [
            ValidationIssue("f1", "e1", ValidationSeverity.ERROR),
            ValidationIssue("f2", "w1", ValidationSeverity.WARNING),
            ValidationIssue("f3", "w2", ValidationSeverity.WARNING),
        ]
        result = ValidationResult(is_valid=False, issues=issues)

        assert len(result.warnings) == 2
        for warning in result.warnings:
            assert warning.severity == ValidationSeverity.WARNING

    def test_error_count_property(self):
        """Test error_count property."""
        issues = [
            ValidationIssue("f1", "e1", ValidationSeverity.ERROR),
            ValidationIssue("f2", "e2", ValidationSeverity.ERROR),
            ValidationIssue("f3", "w1", ValidationSeverity.WARNING),
        ]
        result = ValidationResult(is_valid=False, issues=issues)

        assert result.error_count == 2

    def test_validated_at_auto_generated(self):
        """Test validated_at is auto-generated."""
        result = ValidationResult(is_valid=True)

        assert result.validated_at is not None
        assert isinstance(result.validated_at, datetime)

    def test_to_dict(self):
        """Test to_dict method."""
        issues = [
            ValidationIssue("email", "invalid", ValidationSeverity.ERROR, rule="format"),
            ValidationIssue("name", "too long", ValidationSeverity.WARNING),
        ]
        result = ValidationResult(is_valid=False, issues=issues)

        data = result.to_dict()

        assert data["is_valid"] is False
        assert data["error_count"] == 1
        assert data["warning_count"] == 1
        assert len(data["issues"]) == 2
        assert data["issues"][0]["field"] == "email"
        assert data["issues"][0]["severity"] == "error"
        assert data["issues"][0]["rule"] == "format"

    def test_to_dict_empty_issues(self):
        """Test to_dict with no issues."""
        result = ValidationResult(is_valid=True)

        data = result.to_dict()

        assert data["is_valid"] is True
        assert data["error_count"] == 0
        assert data["warning_count"] == 0
        assert data["issues"] == []


# =============================================================================
# Edge Cases
# =============================================================================


class TestValidationEdgeCases:
    """Tests for edge cases."""

    def test_empty_field_name(self):
        """Test issue with empty field name."""
        issue = ValidationIssue(
            field="",
            message="test",
            severity=ValidationSeverity.ERROR,
        )

        assert issue.field == ""

    def test_empty_message(self):
        """Test issue with empty message."""
        issue = ValidationIssue(
            field="test",
            message="",
            severity=ValidationSeverity.WARNING,
        )

        assert issue.message == ""

    def test_complex_value(self):
        """Test issue with complex value."""
        complex_value = {"nested": {"data": [1, 2, 3]}}
        issue = ValidationIssue(
            field="config",
            message="invalid config",
            severity=ValidationSeverity.ERROR,
            value=complex_value,
        )

        assert issue.value == complex_value

    def test_many_issues(self):
        """Test result with many issues."""
        issues = [
            ValidationIssue(f"field_{i}", f"message_{i}", ValidationSeverity.ERROR)
            for i in range(100)
        ]
        result = ValidationResult(is_valid=False, issues=issues)

        assert len(result.issues) == 100
        assert result.error_count == 100

    def test_mixed_severities(self):
        """Test result with all severity types."""
        issues = [
            ValidationIssue("f1", "error", ValidationSeverity.ERROR),
            ValidationIssue("f2", "warning", ValidationSeverity.WARNING),
            ValidationIssue("f3", "info", ValidationSeverity.INFO),
        ]
        result = ValidationResult(is_valid=False, issues=issues)

        assert result.error_count == 1
        assert len(result.warnings) == 1
        # No property for info, but it's in issues
        info_issues = [i for i in result.issues if i.severity == ValidationSeverity.INFO]
        assert len(info_issues) == 1
