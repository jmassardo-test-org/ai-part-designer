"""
Tests for the thread geometry generator.

Validates configuration dataclasses, input validation, dimension
resolution, metadata assembly, and Build123d geometry construction
(mocked so tests run without OpenCascade).
"""

from __future__ import annotations

import dataclasses
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.cad.exceptions import ThreadGenerationError, ValidationError
from app.cad.thread_generator import (
    DEFAULT_SEGMENTS_PER_REVOLUTION,
    MAX_REVOLUTIONS,
    MAX_THREAD_LENGTH_MM,
    ThreadGenerationResult,
    ThreadGeneratorConfig,
    _build_metadata,
    _get_effective_dimensions,
    _validate_config,
    generate_thread,
)
from app.cad.threads import (
    PitchSeries,
    ThreadFamily,
    ThreadForm,
    ThreadHand,
    ThreadSpec,
    ThreadType,
    get_thread_spec,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_spec(**overrides: Any) -> ThreadSpec:
    """Create a minimal ThreadSpec with sensible defaults for testing."""
    defaults: dict[str, Any] = {
        "family": ThreadFamily.ISO_METRIC,
        "size": "M8",
        "pitch_mm": 1.25,
        "form": ThreadForm.TRIANGULAR,
        "pitch_series": PitchSeries.COARSE,
        "major_diameter": 8.0,
        "pitch_diameter_ext": 7.188,
        "minor_diameter_ext": 6.647,
        "major_diameter_int": 8.0,
        "pitch_diameter_int": 7.188,
        "minor_diameter_int": 6.647,
        "profile_angle_deg": 60.0,
        "taper_per_mm": 0.0,
        "tap_drill_mm": 6.8,
        "clearance_hole_close_mm": 8.4,
        "clearance_hole_medium_mm": 9.0,
        "clearance_hole_free_mm": 10.0,
        "engagement_length_mm": 10.0,
        "standard_ref": "ISO 261",
    }
    defaults.update(overrides)
    return ThreadSpec(**defaults)


def _make_config(**overrides: Any) -> ThreadGeneratorConfig:
    """Build a ThreadGeneratorConfig with safe test defaults."""
    defaults: dict[str, Any] = {
        "spec": _make_spec(),
        "thread_type": ThreadType.EXTERNAL,
        "length_mm": 20.0,
    }
    defaults.update(overrides)
    return ThreadGeneratorConfig(**defaults)


def _mock_part() -> MagicMock:
    """Return a MagicMock that behaves like a Build123d Part."""
    part = MagicMock(name="Part")
    part.cut.return_value = part
    part.fuse.return_value = part
    part.moved.return_value = part
    return part


# =============================================================================
# Configuration Dataclass Tests
# =============================================================================


class TestThreadGeneratorConfig:
    """Tests for ThreadGeneratorConfig frozen dataclass."""

    def test_config_is_frozen(self) -> None:
        """ThreadGeneratorConfig must be immutable."""
        cfg = _make_config()
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.length_mm = 99.0  # type: ignore[misc]

    def test_config_with_defaults(self) -> None:
        """Unspecified optional fields should receive default values."""
        cfg = _make_config()
        assert cfg.hand == ThreadHand.RIGHT
        assert cfg.segments_per_revolution == DEFAULT_SEGMENTS_PER_REVOLUTION
        assert cfg.add_chamfer is True
        assert cfg.custom_pitch_mm is None
        assert cfg.custom_diameter_mm is None

    def test_config_with_custom_pitch(self) -> None:
        """Custom pitch override should be stored correctly."""
        cfg = _make_config(custom_pitch_mm=2.0)
        assert cfg.custom_pitch_mm == 2.0

    def test_config_with_custom_diameter(self) -> None:
        """Custom diameter override should be stored correctly."""
        cfg = _make_config(custom_diameter_mm=10.0)
        assert cfg.custom_diameter_mm == 10.0


class TestThreadGenerationResult:
    """Tests for ThreadGenerationResult mutable dataclass."""

    def test_result_is_mutable(self) -> None:
        """ThreadGenerationResult fields should be reassignable."""
        result = ThreadGenerationResult(part=_mock_part())
        result.generation_time_ms = 42
        assert result.generation_time_ms == 42

    def test_result_defaults(self) -> None:
        """Default metadata should be empty and counters zero."""
        result = ThreadGenerationResult(part=_mock_part())
        assert result.metadata == {}
        assert result.generation_time_ms == 0
        assert result.estimated_face_count == 0


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidateConfig:
    """Tests for _validate_config boundary enforcement."""

    def test_valid_config_passes(self) -> None:
        """A well-formed config should not raise."""
        _validate_config(_make_config())

    def test_zero_length_raises(self) -> None:
        """Zero length must be rejected."""
        with pytest.raises(ValidationError, match="positive"):
            _validate_config(_make_config(length_mm=0.0))

    def test_negative_length_raises(self) -> None:
        """Negative length must be rejected."""
        with pytest.raises(ValidationError, match="positive"):
            _validate_config(_make_config(length_mm=-5.0))

    def test_exceeds_max_length_raises(self) -> None:
        """Length above MAX_THREAD_LENGTH_MM must be rejected."""
        with pytest.raises(ValidationError, match="exceeds maximum"):
            _validate_config(
                _make_config(length_mm=MAX_THREAD_LENGTH_MM + 1.0)
            )

    def test_exceeds_max_revolutions_raises(self) -> None:
        """Config whose length/pitch exceeds MAX_REVOLUTIONS is rejected."""
        tiny_pitch_spec = _make_spec(pitch_mm=0.1)
        cfg = _make_config(
            spec=tiny_pitch_spec,
            length_mm=100.0,  # 100 / 0.1 = 1000 revolutions
        )
        with pytest.raises(ValidationError, match="revolutions"):
            _validate_config(cfg)

    def test_zero_pitch_raises(self) -> None:
        """Spec with zero pitch must be rejected."""
        zero_pitch_spec = _make_spec(pitch_mm=0.0)
        with pytest.raises(ValidationError, match="pitch"):
            _validate_config(_make_config(spec=zero_pitch_spec))

    def test_negative_pitch_raises(self) -> None:
        """Spec with negative pitch must be rejected."""
        neg_spec = _make_spec(pitch_mm=-1.0)
        with pytest.raises(ValidationError, match="pitch"):
            _validate_config(_make_config(spec=neg_spec))

    def test_negative_custom_pitch_raises(self) -> None:
        """Negative custom_pitch_mm must be rejected."""
        with pytest.raises(ValidationError, match="Custom pitch"):
            _validate_config(_make_config(custom_pitch_mm=-0.5))

    def test_negative_custom_diameter_raises(self) -> None:
        """Negative custom_diameter_mm must be rejected."""
        with pytest.raises(ValidationError, match="Custom diameter"):
            _validate_config(_make_config(custom_diameter_mm=-2.0))

    def test_low_segments_raises(self) -> None:
        """segments_per_revolution below 4 must be rejected."""
        with pytest.raises(ValidationError, match="segments"):
            _validate_config(_make_config(segments_per_revolution=2))

    def test_exactly_max_length_passes(self) -> None:
        """Length exactly at the limit should be allowed."""
        _validate_config(_make_config(length_mm=MAX_THREAD_LENGTH_MM))


# =============================================================================
# Effective Dimension Tests
# =============================================================================


class TestGetEffectiveDimensions:
    """Tests for _get_effective_dimensions resolution logic."""

    def test_uses_spec_values_by_default_external(self) -> None:
        """Without custom overrides, spec values are used for external."""
        cfg = _make_config(thread_type=ThreadType.EXTERNAL)
        pitch, major, minor = _get_effective_dimensions(cfg)
        assert pitch == cfg.spec.pitch_mm
        assert major == cfg.spec.major_diameter
        assert minor == cfg.spec.minor_diameter_ext

    def test_uses_spec_values_by_default_internal(self) -> None:
        """For internal threads, internal spec diameters are used."""
        cfg = _make_config(thread_type=ThreadType.INTERNAL)
        pitch, major, minor = _get_effective_dimensions(cfg)
        assert major == cfg.spec.major_diameter_int
        assert minor == cfg.spec.minor_diameter_int

    def test_custom_pitch_overrides(self) -> None:
        """custom_pitch_mm should override spec pitch."""
        cfg = _make_config(custom_pitch_mm=2.5)
        pitch, _, _ = _get_effective_dimensions(cfg)
        assert pitch == 2.5

    def test_custom_diameter_overrides(self) -> None:
        """custom_diameter_mm should override spec major diameter."""
        cfg = _make_config(custom_diameter_mm=12.0)
        _, major, _ = _get_effective_dimensions(cfg)
        assert major == 12.0

    def test_custom_diameter_scales_minor(self) -> None:
        """Minor diameter should scale proportionally with custom major."""
        spec = _make_spec(major_diameter=8.0, minor_diameter_ext=6.647)
        cfg = _make_config(spec=spec, custom_diameter_mm=16.0)
        _, _, minor = _get_effective_dimensions(cfg)
        expected_ratio = 6.647 / 8.0
        assert abs(minor - 16.0 * expected_ratio) < 1e-6

    def test_custom_diameter_fallback_when_major_zero(self) -> None:
        """When spec major_diameter is 0 the pitch-based formula is used."""
        spec = _make_spec(major_diameter=0.0, minor_diameter_ext=0.0, pitch_mm=1.0)
        cfg = _make_config(spec=spec, custom_diameter_mm=10.0)
        _, major, minor = _get_effective_dimensions(cfg)
        assert major == 10.0
        # minor = 10.0 - 1.0825 * 1.0
        assert abs(minor - (10.0 - 1.0825)) < 1e-6


# =============================================================================
# External Thread Generation Tests (Build123d mocked)
# =============================================================================


class TestGenerateExternalThread:
    """Tests for external thread generation with mocked Build123d."""

    @patch("app.cad.thread_generator.Cylinder")
    def test_external_returns_part(self, mock_cyl: MagicMock) -> None:
        """generate_thread should return a ThreadGenerationResult."""
        mock_cyl.return_value = _mock_part()
        result = generate_thread(_make_config())
        assert isinstance(result, ThreadGenerationResult)
        assert result.part is not None

    @patch("app.cad.thread_generator.Cylinder")
    def test_external_metadata_has_expected_keys(
        self, mock_cyl: MagicMock
    ) -> None:
        """Metadata must contain standard keys."""
        mock_cyl.return_value = _mock_part()
        result = generate_thread(_make_config())
        expected_keys = {
            "family", "size", "thread_type", "hand",
            "pitch_mm", "major_diameter_mm", "revolutions",
            "length_mm", "form", "generation_time_ms",
        }
        assert expected_keys.issubset(result.metadata.keys())

    @patch("app.cad.thread_generator.Cylinder")
    def test_external_iso_metric_thread(self, mock_cyl: MagicMock) -> None:
        """ISO Metric M8 config should produce correct metadata values."""
        mock_cyl.return_value = _mock_part()
        cfg = _make_config()
        result = generate_thread(cfg)
        assert result.metadata["family"] == "iso_metric"
        assert result.metadata["size"] == "M8"
        assert result.metadata["thread_type"] == "external"
        assert result.metadata["pitch_mm"] == 1.25

    @patch("app.cad.thread_generator.Cylinder")
    def test_external_generation_time_is_non_negative(
        self, mock_cyl: MagicMock
    ) -> None:
        """generation_time_ms must be ≥ 0."""
        mock_cyl.return_value = _mock_part()
        result = generate_thread(_make_config())
        assert result.generation_time_ms >= 0

    @patch("app.cad.thread_generator.Cylinder")
    def test_external_estimated_faces_positive(
        self, mock_cyl: MagicMock
    ) -> None:
        """Face count estimate must be positive for non-trivial threads."""
        mock_cyl.return_value = _mock_part()
        result = generate_thread(_make_config())
        assert result.estimated_face_count > 0


# =============================================================================
# Internal Thread Generation Tests (Build123d mocked)
# =============================================================================


class TestGenerateInternalThread:
    """Tests for internal thread generation with mocked Build123d."""

    @patch("app.cad.thread_generator.Cylinder")
    def test_internal_returns_part(self, mock_cyl: MagicMock) -> None:
        """Internal thread should produce a valid result."""
        mock_cyl.return_value = _mock_part()
        cfg = _make_config(thread_type=ThreadType.INTERNAL)
        result = generate_thread(cfg)
        assert isinstance(result, ThreadGenerationResult)

    @patch("app.cad.thread_generator.Cylinder")
    def test_internal_metadata_type_is_internal(
        self, mock_cyl: MagicMock
    ) -> None:
        """Metadata thread_type must be 'internal'."""
        mock_cyl.return_value = _mock_part()
        cfg = _make_config(thread_type=ThreadType.INTERNAL)
        result = generate_thread(cfg)
        assert result.metadata["thread_type"] == "internal"


# =============================================================================
# Metadata Tests
# =============================================================================


class TestGenerateThreadMetadata:
    """Tests for metadata assembly."""

    @patch("app.cad.thread_generator.Cylinder")
    def test_metadata_includes_family(self, mock_cyl: MagicMock) -> None:
        """Family field should be present and correct."""
        mock_cyl.return_value = _mock_part()
        result = generate_thread(_make_config())
        assert result.metadata["family"] == "iso_metric"

    @patch("app.cad.thread_generator.Cylinder")
    def test_metadata_includes_generation_time(
        self, mock_cyl: MagicMock
    ) -> None:
        """generation_time_ms must be a non-negative int in metadata."""
        mock_cyl.return_value = _mock_part()
        result = generate_thread(_make_config())
        assert isinstance(result.metadata["generation_time_ms"], int)
        assert result.metadata["generation_time_ms"] >= 0

    @patch("app.cad.thread_generator.Cylinder")
    def test_metadata_includes_revolutions(
        self, mock_cyl: MagicMock
    ) -> None:
        """Revolutions field should equal length / pitch."""
        mock_cyl.return_value = _mock_part()
        cfg = _make_config(length_mm=10.0)
        result = generate_thread(cfg)
        expected_rev = round(10.0 / cfg.spec.pitch_mm, 2)
        assert result.metadata["revolutions"] == expected_rev

    @patch("app.cad.thread_generator.Cylinder")
    def test_metadata_chamfer_flag(self, mock_cyl: MagicMock) -> None:
        """Chamfered flag should reflect config."""
        mock_cyl.return_value = _mock_part()
        result_yes = generate_thread(_make_config(add_chamfer=True))
        result_no = generate_thread(_make_config(add_chamfer=False))
        assert result_yes.metadata["chamfered"] is True
        assert result_no.metadata["chamfered"] is False

    @patch("app.cad.thread_generator.Cylinder")
    def test_metadata_custom_flags(self, mock_cyl: MagicMock) -> None:
        """Custom override flags should be set correctly."""
        mock_cyl.return_value = _mock_part()
        result = generate_thread(
            _make_config(custom_pitch_mm=2.0, custom_diameter_mm=10.0)
        )
        assert result.metadata["custom_pitch_applied"] is True
        assert result.metadata["custom_diameter_applied"] is True

    def test_build_metadata_standalone(self) -> None:
        """_build_metadata should produce all expected keys."""
        cfg = _make_config()
        meta = _build_metadata(
            config=cfg,
            effective_pitch=1.25,
            effective_diameter=8.0,
            revolutions=16.0,
            generation_time_ms=5,
        )
        assert meta["family"] == "iso_metric"
        assert meta["pitch_mm"] == 1.25
        assert meta["major_diameter_mm"] == 8.0
        assert meta["generation_time_ms"] == 5
        assert meta["standard_ref"] == "ISO 261"


# =============================================================================
# Edge-Case / Variant Tests
# =============================================================================


class TestGenerateThreadEdgeCases:
    """Edge-case and variant thread tests."""

    @patch("app.cad.thread_generator.Cylinder")
    def test_npt_tapered_thread(self, mock_cyl: MagicMock) -> None:
        """NPT-style spec with non-zero taper should succeed."""
        mock_cyl.return_value = _mock_part()
        spec = _make_spec(
            family=ThreadFamily.NPT,
            size="1/4-18",
            pitch_mm=1.411,
            form=ThreadForm.NPT,
            taper_per_mm=0.0625,
            profile_angle_deg=60.0,
        )
        cfg = _make_config(spec=spec, length_mm=15.0)
        result = generate_thread(cfg)
        assert result.metadata["taper_per_mm"] == 0.0625

    @patch("app.cad.thread_generator.Cylinder")
    def test_left_hand_thread(self, mock_cyl: MagicMock) -> None:
        """Left-hand thread should be recorded in metadata."""
        mock_cyl.return_value = _mock_part()
        cfg = _make_config(hand=ThreadHand.LEFT)
        result = generate_thread(cfg)
        assert result.metadata["hand"] == "left"

    @patch("app.cad.thread_generator.Cylinder")
    def test_acme_thread_profile(self, mock_cyl: MagicMock) -> None:
        """ACME spec should report trapezoidal form in metadata."""
        mock_cyl.return_value = _mock_part()
        spec = _make_spec(
            family=ThreadFamily.ACME,
            size="1/2-10",
            pitch_mm=2.54,
            form=ThreadForm.ACME,
            profile_angle_deg=29.0,
        )
        cfg = _make_config(spec=spec, length_mm=20.0)
        result = generate_thread(cfg)
        assert result.metadata["form"] == "acme"
        assert result.metadata["profile_angle_deg"] == 29.0

    @patch("app.cad.thread_generator.Cylinder")
    def test_custom_overrides_applied(self, mock_cyl: MagicMock) -> None:
        """Custom pitch and diameter should flow into metadata."""
        mock_cyl.return_value = _mock_part()
        cfg = _make_config(custom_pitch_mm=3.0, custom_diameter_mm=14.0)
        result = generate_thread(cfg)
        assert result.metadata["pitch_mm"] == 3.0
        assert result.metadata["major_diameter_mm"] == 14.0

    @patch("app.cad.thread_generator.Cylinder")
    def test_no_chamfer_option(self, mock_cyl: MagicMock) -> None:
        """Disabling chamfer should still produce a valid result."""
        mock_cyl.return_value = _mock_part()
        cfg = _make_config(add_chamfer=False)
        result = generate_thread(cfg)
        assert result.metadata["chamfered"] is False

    @patch("app.cad.thread_generator.Cylinder")
    def test_minimum_length_succeeds(self, mock_cyl: MagicMock) -> None:
        """A very short but valid length should still succeed."""
        mock_cyl.return_value = _mock_part()
        cfg = _make_config(length_mm=0.5)
        result = generate_thread(cfg)
        assert result.generation_time_ms >= 0

    @patch("app.cad.thread_generator.Cylinder")
    def test_geometry_exception_wraps_in_thread_error(
        self, mock_cyl: MagicMock
    ) -> None:
        """Unexpected Build123d errors should be wrapped in ThreadGenerationError."""
        mock_cyl.side_effect = RuntimeError("OCCT kernel panic")
        with pytest.raises(ThreadGenerationError, match="build failed"):
            generate_thread(_make_config())

    def test_validation_rejects_before_geometry(self) -> None:
        """Invalid config should raise before any Build123d calls."""
        cfg = _make_config(length_mm=-1.0)
        with pytest.raises(ValidationError):
            generate_thread(cfg)
