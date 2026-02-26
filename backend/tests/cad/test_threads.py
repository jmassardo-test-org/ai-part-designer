"""
Tests for the standard thread data library.

Covers enums, ThreadSpec dataclass, all thread family data dictionaries,
lookup functions, and consistency with existing hardware.py values.
"""

from __future__ import annotations

import pytest

from app.cad.exceptions import ThreadDataError
from app.cad.hardware import CLEARANCE_HOLES, TAP_DRILL_SIZES
from app.cad.threads import (
    ACME_THREADS,
    BSPP_THREADS,
    BSPT_THREADS,
    ISO_METRIC_COARSE,
    ISO_METRIC_FINE,
    NPT_THREADS,
    THREAD_FAMILY_INFO,
    THREAD_REGISTRY,
    TRAPEZOIDAL_THREADS,
    UNC_THREADS,
    UNF_THREADS,
    PitchSeries,
    ThreadFamily,
    ThreadForm,
    ThreadHand,
    ThreadType,
    get_tap_drill_info,
    get_thread_spec,
    list_thread_families,
    list_thread_sizes,
)

# =============================================================================
# Enum Tests
# =============================================================================


class TestThreadEnums:
    """Tests for thread-related StrEnum classes."""

    def test_thread_family_values_are_strings(self) -> None:
        """All ThreadFamily members should be string values."""
        for member in ThreadFamily:
            assert isinstance(member.value, str)

    def test_thread_family_has_all_families(self) -> None:
        """ThreadFamily should contain all eight standard families."""
        expected = {
            "iso_metric",
            "unc",
            "unf",
            "npt",
            "bspp",
            "bspt",
            "acme",
            "trapezoidal",
        }
        assert {m.value for m in ThreadFamily} == expected

    def test_thread_type_has_internal_external(self) -> None:
        """ThreadType should have internal and external."""
        assert ThreadType.INTERNAL == "internal"
        assert ThreadType.EXTERNAL == "external"

    def test_pitch_series_values(self) -> None:
        """PitchSeries should have coarse, fine, superfine."""
        assert PitchSeries.COARSE == "coarse"
        assert PitchSeries.FINE == "fine"
        assert PitchSeries.SUPERFINE == "superfine"

    def test_thread_form_has_all_profiles(self) -> None:
        """ThreadForm should contain all six profile shapes."""
        expected = {
            "triangular",
            "truncated_triangular",
            "trapezoidal",
            "acme",
            "npt",
            "square",
        }
        assert {m.value for m in ThreadForm} == expected

    def test_thread_hand_values(self) -> None:
        """ThreadHand should have right and left."""
        assert ThreadHand.RIGHT == "right"
        assert ThreadHand.LEFT == "left"


# =============================================================================
# ThreadSpec Tests
# =============================================================================


class TestThreadSpec:
    """Tests for the ThreadSpec frozen dataclass."""

    def test_thread_spec_is_frozen(self) -> None:
        """ThreadSpec instances should be immutable."""
        spec = ISO_METRIC_COARSE["M3"]
        with pytest.raises(AttributeError):
            spec.pitch_mm = 99.0  # type: ignore[misc]

    def test_to_dict_includes_all_fields(self) -> None:
        """to_dict should include every field that has a non-None value."""
        spec = ISO_METRIC_COARSE["M8"]
        d = spec.to_dict()
        assert "family" in d
        assert "size" in d
        assert "pitch_mm" in d
        assert "major_diameter" in d
        assert "tap_drill_mm" in d

    def test_to_dict_omits_none_optional_fields(self) -> None:
        """to_dict should exclude fields whose value is None."""
        spec = ISO_METRIC_COARSE["M3"]
        d = spec.to_dict()
        # ISO metric coarse has no tpi or nominal_size_inch
        assert "tpi" not in d
        assert "nominal_size_inch" not in d

    def test_to_dict_includes_tpi_when_set(self) -> None:
        """to_dict should include tpi for imperial threads."""
        spec = UNC_THREADS["1/4-20"]
        d = spec.to_dict()
        assert "tpi" in d
        assert d["tpi"] == 20.0


# =============================================================================
# ISO Metric Coarse Tests
# =============================================================================


class TestISOMetricCoarse:
    """Tests for ISO Metric coarse thread data (ISO 261)."""

    def test_m3_pitch_is_0_5(self) -> None:
        """M3 coarse pitch should be 0.5 mm."""
        assert ISO_METRIC_COARSE["M3"].pitch_mm == 0.5

    def test_m8_pitch_is_1_25(self) -> None:
        """M8 coarse pitch should be 1.25 mm."""
        assert ISO_METRIC_COARSE["M8"].pitch_mm == 1.25

    def test_m8_major_diameter_is_8(self) -> None:
        """M8 major diameter should be 8.0 mm."""
        assert ISO_METRIC_COARSE["M8"].major_diameter == 8.0

    def test_all_sizes_have_positive_pitch(self) -> None:
        """Every ISO metric coarse entry must have pitch > 0."""
        for size, spec in ISO_METRIC_COARSE.items():
            assert spec.pitch_mm > 0, f"{size} has non-positive pitch"

    def test_all_sizes_have_major_gt_minor(self) -> None:
        """Major diameter must exceed minor diameter for all sizes."""
        for size, spec in ISO_METRIC_COARSE.items():
            assert spec.major_diameter > spec.minor_diameter_ext, (
                f"{size}: major {spec.major_diameter} <= minor {spec.minor_diameter_ext}"
            )

    def test_all_sizes_have_tap_drill(self) -> None:
        """Every entry should have a positive tap drill diameter."""
        for size, spec in ISO_METRIC_COARSE.items():
            assert spec.tap_drill_mm > 0, f"{size} missing tap drill"

    def test_pitch_series_is_coarse(self) -> None:
        """All ISO metric coarse entries should have COARSE pitch series."""
        for size, spec in ISO_METRIC_COARSE.items():
            assert spec.pitch_series == PitchSeries.COARSE, f"{size} has wrong pitch series"

    def test_minimum_sizes_present(self) -> None:
        """Should contain at least the 12 required sizes."""
        required = {
            "M2",
            "M2.5",
            "M3",
            "M4",
            "M5",
            "M6",
            "M8",
            "M10",
            "M12",
            "M16",
            "M20",
            "M24",
        }
        assert required.issubset(ISO_METRIC_COARSE.keys())


# =============================================================================
# ISO Metric Fine Tests
# =============================================================================


class TestISOMetricFine:
    """Tests for ISO Metric fine thread data (ISO 261)."""

    def test_m8x1_pitch_is_1_0(self) -> None:
        """M8x1.0 fine pitch should be 1.0 mm."""
        assert ISO_METRIC_FINE["M8x1.0"].pitch_mm == 1.0

    def test_pitch_series_is_fine(self) -> None:
        """All fine entries should have FINE pitch series."""
        for size, spec in ISO_METRIC_FINE.items():
            assert spec.pitch_series == PitchSeries.FINE, f"{size} has wrong pitch series"

    def test_minimum_sizes_present(self) -> None:
        """Should contain at least the 6 required sizes."""
        required = {
            "M8x1.0",
            "M10x1.0",
            "M10x1.25",
            "M12x1.25",
            "M12x1.5",
            "M16x1.5",
        }
        assert required.issubset(ISO_METRIC_FINE.keys())


# =============================================================================
# UNC Tests
# =============================================================================


class TestUNCThreads:
    """Tests for Unified National Coarse thread data (ASME B1.1)."""

    def test_quarter_20_exists(self) -> None:
        """1/4-20 UNC should be in the data."""
        assert "1/4-20" in UNC_THREADS

    def test_quarter_20_tpi_is_20(self) -> None:
        """1/4-20 UNC should have 20 threads per inch."""
        assert UNC_THREADS["1/4-20"].tpi == 20.0

    def test_all_have_tpi(self) -> None:
        """All UNC entries must have a tpi value."""
        for size, spec in UNC_THREADS.items():
            assert spec.tpi is not None and spec.tpi > 0, f"{size} missing tpi"  # noqa: PT018

    def test_all_have_nominal_size_inch(self) -> None:
        """All UNC entries must have a nominal inch size."""
        for size, spec in UNC_THREADS.items():
            assert spec.nominal_size_inch is not None, f"{size} missing nominal_size_inch"


# =============================================================================
# UNF Tests
# =============================================================================


class TestUNFThreads:
    """Tests for Unified National Fine thread data (ASME B1.1)."""

    def test_quarter_28_exists(self) -> None:
        """1/4-28 UNF should be in the data."""
        assert "1/4-28" in UNF_THREADS

    def test_all_have_tpi(self) -> None:
        """All UNF entries must have a tpi value."""
        for size, spec in UNF_THREADS.items():
            assert spec.tpi is not None and spec.tpi > 0, f"{size} missing tpi"  # noqa: PT018

    def test_all_have_nominal_size_inch(self) -> None:
        """All UNF entries must have a nominal inch size."""
        for size, spec in UNF_THREADS.items():
            assert spec.nominal_size_inch is not None, f"{size} missing nominal_size_inch"


# =============================================================================
# NPT Tests
# =============================================================================


class TestNPTThreads:
    """Tests for National Pipe Taper thread data (ASME B1.20.1)."""

    def test_quarter_npt_has_taper(self) -> None:
        """1/4 NPT should have non-zero taper."""
        assert NPT_THREADS["1/4"].taper_per_mm > 0

    def test_all_have_engagement_length(self) -> None:
        """All NPT entries must have a positive engagement length."""
        for size, spec in NPT_THREADS.items():
            assert spec.engagement_length_mm > 0, f"{size} missing engagement length"

    def test_profile_angle_is_60(self) -> None:
        """All NPT entries should have 60° profile angle."""
        for size, spec in NPT_THREADS.items():
            assert spec.profile_angle_deg == 60.0, f"{size} has wrong profile angle"

    def test_form_is_npt(self) -> None:
        """All NPT entries should have NPT thread form."""
        for size, spec in NPT_THREADS.items():
            assert spec.form == ThreadForm.NPT, f"{size} has wrong thread form"


# =============================================================================
# BSPP Tests
# =============================================================================


class TestBSPPThreads:
    """Tests for British Standard Pipe Parallel thread data (ISO 228-1)."""

    def test_profile_angle_is_55(self) -> None:
        """All BSPP entries should have 55° profile angle."""
        for size, spec in BSPP_THREADS.items():
            assert spec.profile_angle_deg == 55.0, f"{size} has wrong profile angle"

    def test_taper_is_zero(self) -> None:
        """BSPP threads are parallel — taper should be 0."""
        for size, spec in BSPP_THREADS.items():
            assert spec.taper_per_mm == 0.0, f"{size} has non-zero taper"


# =============================================================================
# BSPT Tests
# =============================================================================


class TestBSPTThreads:
    """Tests for British Standard Pipe Taper thread data (ISO 7-1)."""

    def test_profile_angle_is_55(self) -> None:
        """All BSPT entries should have 55° profile angle."""
        for size, spec in BSPT_THREADS.items():
            assert spec.profile_angle_deg == 55.0, f"{size} has wrong profile angle"

    def test_all_have_taper(self) -> None:
        """All BSPT entries should have non-zero taper."""
        for size, spec in BSPT_THREADS.items():
            assert spec.taper_per_mm > 0, f"{size} missing taper"


# =============================================================================
# ACME Tests
# =============================================================================


class TestACMEThreads:
    """Tests for ACME thread data (ASME B1.5)."""

    def test_profile_angle_is_29(self) -> None:
        """All ACME entries should have 29° profile angle."""
        for size, spec in ACME_THREADS.items():
            assert spec.profile_angle_deg == 29.0, f"{size} has wrong profile angle"

    def test_all_have_tpi(self) -> None:
        """All ACME entries must have a tpi value."""
        for size, spec in ACME_THREADS.items():
            assert spec.tpi is not None and spec.tpi > 0, f"{size} missing tpi"  # noqa: PT018

    def test_form_is_acme(self) -> None:
        """All ACME entries should have ACME thread form."""
        for size, spec in ACME_THREADS.items():
            assert spec.form == ThreadForm.ACME, f"{size} has wrong thread form"


# =============================================================================
# Trapezoidal Tests
# =============================================================================


class TestTrapezoidalThreads:
    """Tests for Trapezoidal thread data (ISO 2904)."""

    def test_profile_angle_is_30(self) -> None:
        """All Trapezoidal entries should have 30° profile angle."""
        for size, spec in TRAPEZOIDAL_THREADS.items():
            assert spec.profile_angle_deg == 30.0, f"{size} has wrong profile angle"

    def test_form_is_trapezoidal(self) -> None:
        """All Trapezoidal entries should have TRAPEZOIDAL thread form."""
        for size, spec in TRAPEZOIDAL_THREADS.items():
            assert spec.form == ThreadForm.TRAPEZOIDAL, f"{size} has wrong thread form"

    def test_minimum_sizes_present(self) -> None:
        """Should contain at least the 6 required sizes."""
        required = {
            "Tr8x1.5",
            "Tr10x2",
            "Tr12x3",
            "Tr16x4",
            "Tr20x4",
            "Tr24x5",
        }
        assert required.issubset(TRAPEZOIDAL_THREADS.keys())


# =============================================================================
# get_thread_spec Tests
# =============================================================================


class TestGetThreadSpec:
    """Tests for the get_thread_spec lookup function."""

    def test_valid_lookup_returns_spec(self) -> None:
        """Looking up a known size should return the correct ThreadSpec."""
        spec = get_thread_spec(ThreadFamily.ISO_METRIC, "M8")
        assert spec.size == "M8"
        assert spec.pitch_mm == 1.25

    def test_unknown_family_raises(self) -> None:
        """An invalid family string should raise ThreadDataError."""
        with pytest.raises(ThreadDataError):
            get_thread_spec("bogus_family", "M8")  # type: ignore[arg-type]

    def test_unknown_size_raises(self) -> None:
        """An unknown size should raise ThreadDataError."""
        with pytest.raises(ThreadDataError):
            get_thread_spec(ThreadFamily.ISO_METRIC, "M99")

    def test_metric_fine_lookup(self) -> None:
        """Should successfully look up fine-pitch metric threads."""
        spec = get_thread_spec(ThreadFamily.ISO_METRIC, "M8x1.0")
        assert spec.pitch_mm == 1.0
        assert spec.pitch_series == PitchSeries.FINE

    def test_pitch_series_mismatch_raises(self) -> None:
        """Requesting wrong pitch series for a size should raise."""
        with pytest.raises(ThreadDataError):
            get_thread_spec(
                ThreadFamily.ISO_METRIC,
                "M8",
                pitch_series=PitchSeries.FINE,
            )

    def test_unc_lookup(self) -> None:
        """Should look up UNC threads by family and size."""
        spec = get_thread_spec(ThreadFamily.UNC, "1/4-20")
        assert spec.tpi == 20.0

    def test_npt_lookup(self) -> None:
        """Should look up NPT threads by family and size."""
        spec = get_thread_spec(ThreadFamily.NPT, "1/2")
        assert spec.taper_per_mm > 0


# =============================================================================
# list_thread_sizes Tests
# =============================================================================


class TestListThreadSizes:
    """Tests for the list_thread_sizes function."""

    def test_returns_sorted_list(self) -> None:
        """Returned sizes should be in sorted order."""
        sizes = list_thread_sizes(ThreadFamily.UNC)
        assert sizes == sorted(sizes)

    def test_unknown_family_raises(self) -> None:
        """An invalid family should raise ThreadDataError."""
        with pytest.raises(ThreadDataError):
            list_thread_sizes("bogus")  # type: ignore[arg-type]

    def test_metric_coarse_filter(self) -> None:
        """Filtering by COARSE should return only coarse entries."""
        sizes = list_thread_sizes(
            ThreadFamily.ISO_METRIC,
            pitch_series=PitchSeries.COARSE,
        )
        assert "M8" in sizes
        assert "M8x1.0" not in sizes

    def test_metric_fine_filter(self) -> None:
        """Filtering by FINE should return only fine entries."""
        sizes = list_thread_sizes(
            ThreadFamily.ISO_METRIC,
            pitch_series=PitchSeries.FINE,
        )
        assert "M8x1.0" in sizes
        assert "M8" not in sizes

    def test_no_filter_returns_all(self) -> None:
        """Without pitch_series filter, return all sizes."""
        sizes = list_thread_sizes(ThreadFamily.ISO_METRIC)
        assert "M8" in sizes
        assert "M8x1.0" in sizes


# =============================================================================
# list_thread_families Tests
# =============================================================================


class TestListThreadFamilies:
    """Tests for the list_thread_families function."""

    def test_returns_all_families(self) -> None:
        """Should return every family in the registry."""
        families = list_thread_families()
        assert ThreadFamily.ISO_METRIC in families
        assert ThreadFamily.UNC in families
        assert ThreadFamily.NPT in families
        assert ThreadFamily.ACME in families

    def test_returns_list(self) -> None:
        """Return type should be a list."""
        families = list_thread_families()
        assert isinstance(families, list)

    def test_length_matches_registry(self) -> None:
        """Number of families should match THREAD_REGISTRY keys."""
        families = list_thread_families()
        assert len(families) == len(THREAD_REGISTRY)


# =============================================================================
# get_tap_drill_info Tests
# =============================================================================


class TestGetTapDrillInfo:
    """Tests for the get_tap_drill_info function."""

    def test_returns_dict_with_expected_keys(self) -> None:
        """Returned dict should contain all four drilling keys."""
        info = get_tap_drill_info(ThreadFamily.ISO_METRIC, "M8")
        expected_keys = {
            "tap_drill_mm",
            "clearance_hole_close_mm",
            "clearance_hole_medium_mm",
            "clearance_hole_free_mm",
        }
        assert set(info.keys()) == expected_keys

    def test_m8_tap_drill_is_6_8(self) -> None:
        """M8 tap drill should be 6.8 mm."""
        info = get_tap_drill_info(ThreadFamily.ISO_METRIC, "M8")
        assert info["tap_drill_mm"] == 6.8

    def test_unknown_size_raises(self) -> None:
        """Unknown size should raise ThreadDataError."""
        with pytest.raises(ThreadDataError):
            get_tap_drill_info(ThreadFamily.ISO_METRIC, "M99")


# =============================================================================
# Registry & Family Info consistency
# =============================================================================


class TestRegistryConsistency:
    """Tests for THREAD_REGISTRY and THREAD_FAMILY_INFO integrity."""

    def test_registry_has_all_families(self) -> None:
        """THREAD_REGISTRY should have an entry for every ThreadFamily."""
        for family in ThreadFamily:
            assert family in THREAD_REGISTRY, f"{family} missing from THREAD_REGISTRY"

    def test_family_info_has_all_families(self) -> None:
        """THREAD_FAMILY_INFO should have metadata for every ThreadFamily."""
        for family in ThreadFamily:
            assert family in THREAD_FAMILY_INFO, f"{family} missing from THREAD_FAMILY_INFO"

    def test_family_info_has_required_keys(self) -> None:
        """Each family info entry should have name, description, standard_ref."""
        for family, info in THREAD_FAMILY_INFO.items():
            assert "name" in info, f"{family} missing name"
            assert "description" in info, f"{family} missing description"
            assert "standard_ref" in info, f"{family} missing standard_ref"


# =============================================================================
# Consistency with hardware.py
# =============================================================================


class TestThreadHardwareConsistency:
    """Verify thread data is consistent with existing hardware.py values."""

    def test_tap_drill_matches_hardware_py(self) -> None:
        """Tap drill values should match TAP_DRILL_SIZES from hardware.py."""
        for size_label, expected_drill in TAP_DRILL_SIZES.items():
            if size_label in ISO_METRIC_COARSE:
                spec = ISO_METRIC_COARSE[size_label]
                assert spec.tap_drill_mm == expected_drill, (
                    f"{size_label}: thread tap_drill={spec.tap_drill_mm} "
                    f"!= hardware={expected_drill}"
                )

    def test_clearance_hole_matches_hardware_py(self) -> None:
        """Close-fit clearance holes should match CLEARANCE_HOLES
        from hardware.py."""
        for size_label, expected_clearance in CLEARANCE_HOLES.items():
            if size_label in ISO_METRIC_COARSE:
                spec = ISO_METRIC_COARSE[size_label]
                assert spec.clearance_hole_close_mm == expected_clearance, (
                    f"{size_label}: thread clearance_close="
                    f"{spec.clearance_hole_close_mm} "
                    f"!= hardware={expected_clearance}"
                )
