"""
Data quality validation framework.

Provides validators for ensuring data integrity and quality
at ingestion and processing boundaries.
"""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ValidationSeverity(StrEnum):
    """Severity levels for validation issues."""

    ERROR = "error"  # Must fix, blocks processing
    WARNING = "warning"  # Should fix, doesn't block
    INFO = "info"  # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue."""

    field: str
    message: str
    severity: ValidationSeverity
    value: Any = None
    rule: str | None = None


@dataclass
class ValidationResult:
    """Result of validation check."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(tz=datetime.UTC))

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": len(self.warnings),
            "issues": [
                {
                    "field": i.field,
                    "message": i.message,
                    "severity": i.severity.value,
                    "rule": i.rule,
                }
                for i in self.issues
            ],
        }


class DataValidator(Generic[T]):
    """
    Generic data validator with composable rules.

    Example:
        validator = DataValidator[UserInput]()
        validator.add_rule("email", Rules.email())
        validator.add_rule("name", Rules.not_empty())

        result = validator.validate(user_input)
    """

    def __init__(self):
        self._rules: list[tuple[str, Callable[[Any], ValidationIssue | None]]] = []

    def add_rule(
        self,
        field: str,
        rule: Callable[[Any], ValidationIssue | None],
    ) -> "DataValidator[T]":
        """Add a validation rule for a field."""
        self._rules.append((field, rule))
        return self

    def validate(self, data: dict | BaseModel) -> ValidationResult:
        """
        Validate data against all rules.

        Args:
            data: Dictionary or Pydantic model to validate

        Returns:
            ValidationResult with issues found
        """
        if isinstance(data, BaseModel):
            data = data.model_dump()

        issues = []

        for field_name, rule in self._rules:
            value = self._get_nested_value(data, field_name)

            try:
                issue = rule(value)
                if issue:
                    issue.field = field_name
                    issue.value = value
                    issues.append(issue)
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        field=field,
                        message=f"Validation error: {e!s}",
                        severity=ValidationSeverity.ERROR,
                        value=value,
                    )
                )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(is_valid=is_valid, issues=issues)

    def _get_nested_value(self, data: dict, field: str) -> Any:
        """Get value from nested field path (e.g., 'user.email')."""
        keys = field.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


class Rules:
    """
    Factory for common validation rules.

    Each rule returns a function that takes a value and returns
    a ValidationIssue if validation fails, or None if it passes.
    """

    @staticmethod
    def required() -> Callable[[Any], ValidationIssue | None]:
        """Value must not be None."""

        def check(value: Any) -> ValidationIssue | None:
            if value is None:
                return ValidationIssue(
                    field="",
                    message="Value is required",
                    severity=ValidationSeverity.ERROR,
                    rule="required",
                )
            return None

        return check

    @staticmethod
    def not_empty() -> Callable[[Any], ValidationIssue | None]:
        """String must not be empty."""

        def check(value: Any) -> ValidationIssue | None:
            if value is None or (isinstance(value, str) and not value.strip()):
                return ValidationIssue(
                    field="",
                    message="Value must not be empty",
                    severity=ValidationSeverity.ERROR,
                    rule="not_empty",
                )
            return None

        return check

    @staticmethod
    def min_length(min_len: int) -> Callable[[Any], ValidationIssue | None]:
        """String must have minimum length."""

        def check(value: Any) -> ValidationIssue | None:
            if value and len(str(value)) < min_len:
                return ValidationIssue(
                    field="",
                    message=f"Value must be at least {min_len} characters",
                    severity=ValidationSeverity.ERROR,
                    rule="min_length",
                )
            return None

        return check

    @staticmethod
    def max_length(max_len: int) -> Callable[[Any], ValidationIssue | None]:
        """String must not exceed maximum length."""

        def check(value: Any) -> ValidationIssue | None:
            if value and len(str(value)) > max_len:
                return ValidationIssue(
                    field="",
                    message=f"Value must not exceed {max_len} characters",
                    severity=ValidationSeverity.ERROR,
                    rule="max_length",
                )
            return None

        return check

    @staticmethod
    def email() -> Callable[[Any], ValidationIssue | None]:
        """Value must be a valid email address."""
        EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

        def check(value: Any) -> ValidationIssue | None:
            if value and not EMAIL_REGEX.match(str(value)):
                return ValidationIssue(
                    field="",
                    message="Invalid email address",
                    severity=ValidationSeverity.ERROR,
                    rule="email",
                )
            return None

        return check

    @staticmethod
    def uuid() -> Callable[[Any], ValidationIssue | None]:
        """Value must be a valid UUID."""

        def check(value: Any) -> ValidationIssue | None:
            if value is None:
                return None
            try:
                if isinstance(value, UUID):
                    return None
                UUID(str(value))
                return None
            except ValueError:
                return ValidationIssue(
                    field="",
                    message="Invalid UUID format",
                    severity=ValidationSeverity.ERROR,
                    rule="uuid",
                )

        return check

    @staticmethod
    def in_list(allowed: list[Any]) -> Callable[[Any], ValidationIssue | None]:
        """Value must be in allowed list."""

        def check(value: Any) -> ValidationIssue | None:
            if value is not None and value not in allowed:
                return ValidationIssue(
                    field="",
                    message=f"Value must be one of: {allowed}",
                    severity=ValidationSeverity.ERROR,
                    rule="in_list",
                )
            return None

        return check

    @staticmethod
    def numeric_range(
        min_val: float | None = None,
        max_val: float | None = None,
    ) -> Callable[[Any], ValidationIssue | None]:
        """Number must be within range."""

        def check(value: Any) -> ValidationIssue | None:
            if value is None:
                return None
            try:
                num = float(value)
                if min_val is not None and num < min_val:
                    return ValidationIssue(
                        field="",
                        message=f"Value must be >= {min_val}",
                        severity=ValidationSeverity.ERROR,
                        rule="numeric_range",
                    )
                if max_val is not None and num > max_val:
                    return ValidationIssue(
                        field="",
                        message=f"Value must be <= {max_val}",
                        severity=ValidationSeverity.ERROR,
                        rule="numeric_range",
                    )
                return None
            except (TypeError, ValueError):
                return ValidationIssue(
                    field="",
                    message="Value must be numeric",
                    severity=ValidationSeverity.ERROR,
                    rule="numeric_range",
                )

        return check

    @staticmethod
    def regex(
        pattern: str, message: str = "Invalid format"
    ) -> Callable[[Any], ValidationIssue | None]:
        """Value must match regex pattern."""
        compiled = re.compile(pattern)

        def check(value: Any) -> ValidationIssue | None:
            if value and not compiled.match(str(value)):
                return ValidationIssue(
                    field="",
                    message=message,
                    severity=ValidationSeverity.ERROR,
                    rule="regex",
                )
            return None

        return check

    @staticmethod
    def positive() -> Callable[[Any], ValidationIssue | None]:
        """Number must be positive."""
        return Rules.numeric_range(min_val=0.0001)

    @staticmethod
    def non_negative() -> Callable[[Any], ValidationIssue | None]:
        """Number must be non-negative."""
        return Rules.numeric_range(min_val=0)

    @staticmethod
    def custom(
        check_fn: Callable[[Any], bool],
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
    ) -> Callable[[Any], ValidationIssue | None]:
        """Custom validation rule."""

        def check(value: Any) -> ValidationIssue | None:
            if not check_fn(value):
                return ValidationIssue(
                    field="",
                    message=message,
                    severity=severity,
                    rule="custom",
                )
            return None

        return check


# =========================================================================
# Domain-Specific Validators
# =========================================================================


class CADParameterValidator:
    """Validator for CAD template parameters."""

    @staticmethod
    def validate_parameters(
        parameters: dict,
        schema: dict,
    ) -> ValidationResult:
        """
        Validate CAD parameters against template schema.

        Args:
            parameters: User-provided parameter values
            schema: Template parameter schema

        Returns:
            ValidationResult with any issues found
        """
        issues = []

        for param_name, param_schema in schema.items():
            value = parameters.get(param_name)
            param_type = param_schema.get("type")

            # Check required
            if value is None:
                if param_schema.get("required", True):
                    issues.append(
                        ValidationIssue(
                            field=param_name,
                            message=f"Parameter '{param_name}' is required",
                            severity=ValidationSeverity.ERROR,
                            rule="required",
                        )
                    )
                continue

            # Type validation
            if param_type == "number":
                try:
                    num_val = float(value)

                    # Range validation
                    min_val = param_schema.get("min")
                    max_val = param_schema.get("max")

                    if min_val is not None and num_val < min_val:
                        issues.append(
                            ValidationIssue(
                                field=param_name,
                                message=f"Value must be >= {min_val}",
                                severity=ValidationSeverity.ERROR,
                                value=value,
                                rule="min_value",
                            )
                        )

                    if max_val is not None and num_val > max_val:
                        issues.append(
                            ValidationIssue(
                                field=param_name,
                                message=f"Value must be <= {max_val}",
                                severity=ValidationSeverity.ERROR,
                                value=value,
                                rule="max_value",
                            )
                        )

                except (TypeError, ValueError):
                    issues.append(
                        ValidationIssue(
                            field=param_name,
                            message="Value must be a number",
                            severity=ValidationSeverity.ERROR,
                            value=value,
                            rule="type",
                        )
                    )

            elif param_type == "boolean":
                if not isinstance(value, bool):
                    issues.append(
                        ValidationIssue(
                            field=param_name,
                            message="Value must be true or false",
                            severity=ValidationSeverity.ERROR,
                            value=value,
                            rule="type",
                        )
                    )

            elif param_type == "select":
                options = param_schema.get("options", [])
                if value not in options:
                    issues.append(
                        ValidationIssue(
                            field=param_name,
                            message=f"Value must be one of: {options}",
                            severity=ValidationSeverity.ERROR,
                            value=value,
                            rule="options",
                        )
                    )

        # Check for unknown parameters (warning only)
        for param_name in parameters:
            if param_name not in schema:
                issues.append(
                    ValidationIssue(
                        field=param_name,
                        message=f"Unknown parameter '{param_name}'",
                        severity=ValidationSeverity.WARNING,
                        rule="unknown",
                    )
                )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        return ValidationResult(is_valid=is_valid, issues=issues)


class DataQualityChecker:
    """
    Data quality checker for monitoring data health.

    Tracks quality metrics and can be used for alerting
    when data quality degrades.
    """

    def __init__(self):
        self._checks: list[tuple[str, Callable[[], ValidationResult]]] = []
        self._results: dict[str, ValidationResult] = {}

    def add_check(
        self,
        name: str,
        check_fn: Callable[[], ValidationResult],
    ) -> "DataQualityChecker":
        """Add a quality check."""
        self._checks.append((name, check_fn))
        return self

    async def run_all_checks(self) -> dict[str, ValidationResult]:
        """Run all quality checks and return results."""
        results = {}

        for name, check_fn in self._checks:
            try:
                result = check_fn()
                results[name] = result
            except Exception as e:
                logger.error(f"Quality check '{name}' failed: {e}")
                results[name] = ValidationResult(
                    is_valid=False,
                    issues=[
                        ValidationIssue(
                            field="check",
                            message=f"Check failed with error: {e!s}",
                            severity=ValidationSeverity.ERROR,
                        )
                    ],
                )

        self._results = results
        return results

    def get_summary(self) -> dict:
        """Get summary of last check run."""
        passed = sum(1 for r in self._results.values() if r.is_valid)
        failed = len(self._results) - passed

        return {
            "total_checks": len(self._results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(self._results) if self._results else 0,
            "checks": {name: result.to_dict() for name, result in self._results.items()},
        }
