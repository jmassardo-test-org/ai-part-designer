"""
Tests for CAD Exception Classes.

Tests exception hierarchy, error serialization, and specific exception types.
"""

import pytest

from app.cad.exceptions import (
    CADError,
    ExportError,
    GeometryError,
    TemplateError,
    ValidationError,
)
from app.cad.exceptions import (
    ImportError as CADImportError,
)
from app.cad.exceptions import (
    TimeoutError as CADTimeoutError,
)

# =============================================================================
# CADError Base Class Tests
# =============================================================================


class TestCADError:
    """Tests for base CADError class."""

    def test_basic_error(self):
        """Test creating basic CAD error."""
        error = CADError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with details dict."""
        error = CADError(
            "Failed operation",
            details={"operation": "fillet", "radius": 5.0},
        )

        assert error.details["operation"] == "fillet"
        assert error.details["radius"] == 5.0

    def test_to_dict(self):
        """Test converting error to dictionary."""
        error = CADError(
            "Test error",
            details={"key": "value"},
        )

        result = error.to_dict()

        assert result["error"] == "CADError"
        assert result["message"] == "Test error"
        assert result["details"] == {"key": "value"}

    def test_inheritance(self):
        """Test that CADError inherits from Exception."""
        error = CADError("test")
        assert isinstance(error, Exception)


# =============================================================================
# GeometryError Tests
# =============================================================================


class TestGeometryError:
    """Tests for geometry errors."""

    def test_basic_geometry_error(self):
        """Test creating geometry error."""
        error = GeometryError("Invalid geometry result")

        assert error.message == "Invalid geometry result"

    def test_geometry_error_with_details(self):
        """Test geometry error with operation details."""
        error = GeometryError(
            "Boolean operation failed",
            details={"operation": "union", "reason": "empty result"},
        )

        assert error.details["operation"] == "union"

    def test_to_dict_class_name(self):
        """Test to_dict includes correct class name."""
        error = GeometryError("test")

        assert error.to_dict()["error"] == "GeometryError"

    def test_inheritance(self):
        """Test inheritance from CADError."""
        error = GeometryError("test")
        assert isinstance(error, CADError)


# =============================================================================
# ExportError Tests
# =============================================================================


class TestExportError:
    """Tests for export errors."""

    def test_basic_export_error(self):
        """Test creating export error."""
        error = ExportError("Cannot export file")

        assert error.message == "Cannot export file"

    def test_export_error_with_format(self):
        """Test export error with format details."""
        error = ExportError(
            "Export failed",
            details={"format": "STEP", "path": "/tmp/output.step"},
        )

        assert error.details["format"] == "STEP"

    def test_to_dict_class_name(self):
        """Test to_dict includes correct class name."""
        error = ExportError("test")

        assert error.to_dict()["error"] == "ExportError"

    def test_inheritance(self):
        """Test inheritance from CADError."""
        error = ExportError("test")
        assert isinstance(error, CADError)


# =============================================================================
# ValidationError Tests
# =============================================================================


class TestValidationError:
    """Tests for validation errors."""

    def test_basic_validation_error(self):
        """Test creating validation error."""
        error = ValidationError("Invalid parameter")

        assert error.message == "Invalid parameter"

    def test_validation_error_with_params(self):
        """Test validation error with parameter details."""
        error = ValidationError(
            "Dimension out of range",
            details={
                "parameter": "length",
                "value": -5.0,
                "min": 0.0,
            },
        )

        assert error.details["parameter"] == "length"
        assert error.details["value"] == -5.0

    def test_to_dict_class_name(self):
        """Test to_dict includes correct class name."""
        error = ValidationError("test")

        assert error.to_dict()["error"] == "ValidationError"

    def test_inheritance(self):
        """Test inheritance from CADError."""
        error = ValidationError("test")
        assert isinstance(error, CADError)


# =============================================================================
# TemplateError Tests
# =============================================================================


class TestTemplateError:
    """Tests for template errors."""

    def test_basic_template_error(self):
        """Test creating template error."""
        error = TemplateError("Template not found")

        assert error.message == "Template not found"

    def test_template_error_with_name(self):
        """Test template error with template name."""
        error = TemplateError(
            "Template execution failed",
            details={"template": "box_with_lid", "line": 42},
        )

        assert error.details["template"] == "box_with_lid"

    def test_to_dict_class_name(self):
        """Test to_dict includes correct class name."""
        error = TemplateError("test")

        assert error.to_dict()["error"] == "TemplateError"

    def test_inheritance(self):
        """Test inheritance from CADError."""
        error = TemplateError("test")
        assert isinstance(error, CADError)


# =============================================================================
# TimeoutError Tests
# =============================================================================


class TestCADTimeoutError:
    """Tests for CAD timeout errors."""

    def test_basic_timeout_error(self):
        """Test creating timeout error."""
        error = CADTimeoutError("Operation timed out")

        assert error.message == "Operation timed out"

    def test_timeout_error_with_duration(self):
        """Test timeout error with duration details."""
        error = CADTimeoutError(
            "Generation timed out",
            details={"timeout_seconds": 30, "operation": "boolean"},
        )

        assert error.details["timeout_seconds"] == 30

    def test_to_dict_class_name(self):
        """Test to_dict includes correct class name."""
        error = CADTimeoutError("test")

        assert error.to_dict()["error"] == "TimeoutError"

    def test_inheritance(self):
        """Test inheritance from CADError."""
        error = CADTimeoutError("test")
        assert isinstance(error, CADError)


# =============================================================================
# ImportError Tests
# =============================================================================


class TestCADImportError:
    """Tests for CAD import errors."""

    def test_basic_import_error(self):
        """Test creating import error."""
        error = CADImportError("Cannot import file")

        assert error.message == "Cannot import file"

    def test_import_error_with_file(self):
        """Test import error with file details."""
        error = CADImportError(
            "Invalid file format",
            details={"file": "model.xyz", "reason": "unknown format"},
        )

        assert error.details["file"] == "model.xyz"

    def test_to_dict_class_name(self):
        """Test to_dict includes correct class name."""
        error = CADImportError("test")

        assert error.to_dict()["error"] == "ImportError"

    def test_inheritance(self):
        """Test inheritance from CADError."""
        error = CADImportError("test")
        assert isinstance(error, CADError)


# =============================================================================
# Exception Hierarchy Tests
# =============================================================================


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_all_inherit_from_cad_error(self):
        """Test all specific exceptions inherit from CADError."""
        exceptions = [
            GeometryError("test"),
            ExportError("test"),
            ValidationError("test"),
            TemplateError("test"),
            CADTimeoutError("test"),
            CADImportError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, CADError)

    def test_all_are_exceptions(self):
        """Test all can be raised and caught."""
        exceptions = [
            CADError("test"),
            GeometryError("test"),
            ExportError("test"),
            ValidationError("test"),
            TemplateError("test"),
            CADTimeoutError("test"),
            CADImportError("test"),
        ]

        for exc in exceptions:
            with pytest.raises(CADError):
                raise exc

    def test_catch_specific_exception(self):
        """Test catching specific exception type."""
        with pytest.raises(GeometryError):
            raise GeometryError("Boolean failed", details={"op": "union"})


# =============================================================================
# Error Serialization Tests
# =============================================================================


class TestErrorSerialization:
    """Tests for error serialization to API responses."""

    def test_to_dict_structure(self):
        """Test to_dict returns proper structure."""
        error = CADError("Test", details={"a": 1})
        result = error.to_dict()

        assert "error" in result
        assert "message" in result
        assert "details" in result

    def test_subclass_names_in_dict(self):
        """Test each subclass has correct name in to_dict."""
        test_cases = [
            (GeometryError("test"), "GeometryError"),
            (ExportError("test"), "ExportError"),
            (ValidationError("test"), "ValidationError"),
            (TemplateError("test"), "TemplateError"),
            (CADTimeoutError("test"), "TimeoutError"),
            (CADImportError("test"), "ImportError"),
        ]

        for error, expected_name in test_cases:
            assert error.to_dict()["error"] == expected_name
