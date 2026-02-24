"""
Tests for the print-optimized thread profile module.

Covers enums, dataclasses, clearance defaults, feasibility assessment,
thread optimization, and orientation advice.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.cad.threads import (
    ThreadFamily,
    ThreadForm,
    ThreadSpec,
    ThreadType,
    PitchSeries,
)
from app.cad.thread_print_optimizer import (
    CLEARANCE_DEFAULTS,
    MIN_PRINTABLE_PITCH_MM,
    PrintFeasibility,
    PrintProcess,
    PrintRecommendation,
    PrintThreadConfig,
    PrintThreadResult,
    ToleranceClass,
    get_orientation_advice,
    get_print_recommendation,
    optimize_thread_for_print,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def m8_spec() -> ThreadSpec:
    """Return an M8 coarse thread spec for testing."""
    return ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M8",
        pitch_mm=1.25,
        pitch_series=PitchSeries.COARSE,
        major_diameter=8.0,
        pitch_diameter_ext=7.188,
        minor_diameter_ext=6.466,
        major_diameter_int=8.0,
        pitch_diameter_int=7.188,
        minor_diameter_int=6.647,
        tap_drill_mm=6.8,
        standard_ref="ISO 261",
    )


@pytest.fixture()
def m3_spec() -> ThreadSpec:
    """Return an M3 coarse thread spec for testing."""
    return ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M3",
        pitch_mm=0.5,
        pitch_series=PitchSeries.COARSE,
        major_diameter=3.0,
        pitch_diameter_ext=2.675,
        minor_diameter_ext=2.387,
        major_diameter_int=3.0,
        pitch_diameter_int=2.675,
        minor_diameter_int=2.459,
        tap_drill_mm=2.5,
        standard_ref="ISO 261",
    )


@pytest.fixture()
def m20_spec() -> ThreadSpec:
    """Return an M20 coarse thread spec for testing (large thread)."""
    return ThreadSpec(
        family=ThreadFamily.ISO_METRIC,
        size="M20",
        pitch_mm=2.5,
        pitch_series=PitchSeries.COARSE,
        major_diameter=20.0,
        pitch_diameter_ext=18.376,
        minor_diameter_ext=16.933,
        major_diameter_int=20.0,
        pitch_diameter_int=18.376,
        minor_diameter_int=17.294,
        tap_drill_mm=17.5,
        standard_ref="ISO 261",
    )


@pytest.fixture()
def npt_half_inch_spec() -> ThreadSpec:
    """Return a 1/2-14 NPT thread spec for testing."""
    return ThreadSpec(
        family=ThreadFamily.NPT,
        size="1/2-14",
        pitch_mm=1.814,
        form=ThreadForm.NPT,
        major_diameter=21.223,
        pitch_diameter_ext=20.226,
        minor_diameter_ext=19.229,
        major_diameter_int=21.223,
        pitch_diameter_int=20.226,
        minor_diameter_int=19.429,
        tpi=14.0,
        nominal_size_inch="1/2",
        taper_per_mm=0.0625,
        profile_angle_deg=60.0,
        standard_ref="ASME B1.20.1",
    )


# =============================================================================
# Enum Tests
# =============================================================================


class TestPrintProcess:
    """Tests for the PrintProcess enum."""

    def test_values_are_strings(self) -> None:
        """All PrintProcess members should be string values."""
        for member in PrintProcess:
            assert isinstance(member.value, str)

    def test_has_fdm_sla_sls_mjf(self) -> None:
        """PrintProcess should contain FDM, SLA, SLS, and MJF."""
        expected = {"fdm", "sla", "sls", "mjf"}
        assert {m.value for m in PrintProcess} == expected


class TestToleranceClass:
    """Tests for the ToleranceClass enum."""

    def test_values_are_strings(self) -> None:
        """All ToleranceClass members should be string values."""
        for member in ToleranceClass:
            assert isinstance(member.value, str)

    def test_has_tight_standard_loose(self) -> None:
        """ToleranceClass should contain tight, standard, and loose."""
        expected = {"tight", "standard", "loose"}
        assert {m.value for m in ToleranceClass} == expected


class TestPrintFeasibility:
    """Tests for the PrintFeasibility enum."""

    def test_has_four_levels(self) -> None:
        """PrintFeasibility should contain exactly four rating levels."""
        assert len(PrintFeasibility) == 4

    def test_values_are_strings(self) -> None:
        """All PrintFeasibility members should be string values."""
        for member in PrintFeasibility:
            assert isinstance(member.value, str)

    def test_expected_values(self) -> None:
        """PrintFeasibility should have the expected rating values."""
        expected = {"excellent", "good", "marginal", "not_recommended"}
        assert {m.value for m in PrintFeasibility} == expected


# =============================================================================
# Dataclass Tests
# =============================================================================


class TestPrintThreadConfig:
    """Tests for the PrintThreadConfig frozen dataclass."""

    def test_is_frozen(self, m8_spec: ThreadSpec) -> None:
        """PrintThreadConfig should be immutable (frozen)."""
        config = PrintThreadConfig(spec=m8_spec)
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.process = PrintProcess.SLA  # type: ignore[misc]

    def test_default_values(self, m8_spec: ThreadSpec) -> None:
        """PrintThreadConfig should have sensible defaults."""
        config = PrintThreadConfig(spec=m8_spec)
        assert config.process == PrintProcess.FDM
        assert config.tolerance_class == ToleranceClass.STANDARD
        assert config.thread_type == ThreadType.EXTERNAL
        assert config.nozzle_diameter_mm == 0.4
        assert config.layer_height_mm == 0.2
        assert config.use_flat_bottom is False
        assert config.add_lead_in_chamfer is True
        assert config.custom_clearance_mm is None

    def test_custom_clearance(self, m8_spec: ThreadSpec) -> None:
        """PrintThreadConfig should accept custom clearance."""
        config = PrintThreadConfig(
            spec=m8_spec,
            custom_clearance_mm=0.42,
        )
        assert config.custom_clearance_mm == 0.42

    def test_all_processes_accepted(self, m8_spec: ThreadSpec) -> None:
        """PrintThreadConfig should accept all print processes."""
        for proc in PrintProcess:
            config = PrintThreadConfig(spec=m8_spec, process=proc)
            assert config.process == proc


class TestPrintRecommendation:
    """Tests for the PrintRecommendation dataclass."""

    def test_has_all_expected_fields(self) -> None:
        """PrintRecommendation should expose all documented fields."""
        rec = PrintRecommendation(
            feasibility=PrintFeasibility.GOOD,
            min_recommended_size="M6",
            recommended_tolerance=ToleranceClass.STANDARD,
            clearance_mm=0.3,
            notes=["test note"],
            orientation_advice="vertical",
            estimated_strength_pct=55.0,
        )
        assert rec.feasibility == PrintFeasibility.GOOD
        assert rec.min_recommended_size == "M6"
        assert rec.recommended_tolerance == ToleranceClass.STANDARD
        assert rec.clearance_mm == 0.3
        assert rec.notes == ["test note"]
        assert rec.orientation_advice == "vertical"
        assert rec.estimated_strength_pct == 55.0


# =============================================================================
# Clearance Defaults Tests
# =============================================================================


class TestClearanceDefaults:
    """Tests for CLEARANCE_DEFAULTS constant."""

    def test_fdm_standard_is_0_3(self) -> None:
        """FDM standard clearance should be 0.3 mm."""
        assert CLEARANCE_DEFAULTS[PrintProcess.FDM][ToleranceClass.STANDARD] == 0.3

    def test_sla_has_lower_clearance_than_fdm(self) -> None:
        """SLA clearances should be lower than FDM for every tolerance."""
        for tol in ToleranceClass:
            assert (
                CLEARANCE_DEFAULTS[PrintProcess.SLA][tol]
                < CLEARANCE_DEFAULTS[PrintProcess.FDM][tol]
            )

    def test_all_processes_have_all_tolerances(self) -> None:
        """Every process should define clearances for all tolerances."""
        for proc in PrintProcess:
            for tol in ToleranceClass:
                assert tol in CLEARANCE_DEFAULTS[proc], (
                    f"Missing {tol} for {proc}"
                )

    def test_tight_less_than_standard_less_than_loose(self) -> None:
        """Clearances should increase from tight to standard to loose."""
        for proc in PrintProcess:
            tight = CLEARANCE_DEFAULTS[proc][ToleranceClass.TIGHT]
            standard = CLEARANCE_DEFAULTS[proc][ToleranceClass.STANDARD]
            loose = CLEARANCE_DEFAULTS[proc][ToleranceClass.LOOSE]
            assert tight < standard < loose, (
                f"Clearance ordering violated for {proc}: "
                f"{tight} < {standard} < {loose}"
            )


# =============================================================================
# Min Printable Pitch Tests
# =============================================================================


class TestMinPrintablePitch:
    """Tests for MIN_PRINTABLE_PITCH_MM constant."""

    def test_fdm_min_pitch_is_1_0(self) -> None:
        """FDM minimum printable pitch should be 1.0 mm."""
        assert MIN_PRINTABLE_PITCH_MM[PrintProcess.FDM] == 1.0

    def test_sla_allows_smaller_than_fdm(self) -> None:
        """SLA minimum pitch should be smaller than FDM."""
        assert (
            MIN_PRINTABLE_PITCH_MM[PrintProcess.SLA]
            < MIN_PRINTABLE_PITCH_MM[PrintProcess.FDM]
        )

    def test_all_processes_have_min_pitch(self) -> None:
        """Every process should have a minimum printable pitch defined."""
        for proc in PrintProcess:
            assert proc in MIN_PRINTABLE_PITCH_MM
            assert MIN_PRINTABLE_PITCH_MM[proc] > 0


# =============================================================================
# get_print_recommendation Tests
# =============================================================================


class TestGetPrintRecommendation:
    """Tests for the get_print_recommendation function."""

    def test_large_thread_fdm_is_excellent_or_good(
        self, m20_spec: ThreadSpec,
    ) -> None:
        """A large thread (M20) on FDM should be EXCELLENT or GOOD."""
        rec = get_print_recommendation(m20_spec, PrintProcess.FDM)
        assert rec.feasibility in (
            PrintFeasibility.EXCELLENT,
            PrintFeasibility.GOOD,
        )

    def test_small_thread_fdm_is_marginal_or_not_recommended(
        self, m3_spec: ThreadSpec,
    ) -> None:
        """A small thread (M3, 0.5 mm pitch) on FDM should be poor."""
        rec = get_print_recommendation(m3_spec, PrintProcess.FDM)
        assert rec.feasibility in (
            PrintFeasibility.MARGINAL,
            PrintFeasibility.NOT_RECOMMENDED,
        )

    def test_sla_allows_finer_threads(
        self, m3_spec: ThreadSpec,
    ) -> None:
        """SLA should rate an M3 thread better than FDM does."""
        fdm_rec = get_print_recommendation(m3_spec, PrintProcess.FDM)
        sla_rec = get_print_recommendation(m3_spec, PrintProcess.SLA)
        # SLA feasibility should be better or equal
        feasibility_order = [
            PrintFeasibility.NOT_RECOMMENDED,
            PrintFeasibility.MARGINAL,
            PrintFeasibility.GOOD,
            PrintFeasibility.EXCELLENT,
        ]
        assert feasibility_order.index(sla_rec.feasibility) >= (
            feasibility_order.index(fdm_rec.feasibility)
        )

    def test_returns_orientation_advice(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Recommendation should include non-empty orientation advice."""
        rec = get_print_recommendation(m8_spec, PrintProcess.FDM)
        assert isinstance(rec.orientation_advice, str)
        assert len(rec.orientation_advice) > 0

    def test_returns_estimated_strength(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Estimated strength should be between 0 and 100 percent."""
        rec = get_print_recommendation(m8_spec, PrintProcess.FDM)
        assert 0 < rec.estimated_strength_pct <= 100

    def test_returns_notes_list(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Notes should be a list of strings."""
        rec = get_print_recommendation(m8_spec, PrintProcess.FDM)
        assert isinstance(rec.notes, list)
        for note in rec.notes:
            assert isinstance(note, str)

    def test_npt_thread_recommendation(
        self, npt_half_inch_spec: ThreadSpec,
    ) -> None:
        """NPT thread should receive a valid recommendation."""
        rec = get_print_recommendation(
            npt_half_inch_spec, PrintProcess.FDM,
        )
        assert isinstance(rec.feasibility, PrintFeasibility)
        assert rec.clearance_mm > 0

    def test_excellent_has_higher_strength_than_marginal(
        self, m20_spec: ThreadSpec, m3_spec: ThreadSpec,
    ) -> None:
        """Better feasibility should yield higher strength estimate."""
        rec_large = get_print_recommendation(m20_spec, PrintProcess.FDM)
        rec_small = get_print_recommendation(m3_spec, PrintProcess.FDM)
        # Large thread should have equal or higher strength estimate
        assert (
            rec_large.estimated_strength_pct
            >= rec_small.estimated_strength_pct
        )

    def test_marginal_or_worse_recommends_loose(
        self, m3_spec: ThreadSpec,
    ) -> None:
        """Marginal/not-recommended threads should suggest loose tolerance."""
        rec = get_print_recommendation(m3_spec, PrintProcess.FDM)
        if rec.feasibility in (
            PrintFeasibility.MARGINAL,
            PrintFeasibility.NOT_RECOMMENDED,
        ):
            assert rec.recommended_tolerance == ToleranceClass.LOOSE

    def test_layer_height_warning_when_coarse(
        self, m3_spec: ThreadSpec,
    ) -> None:
        """Large layer height relative to pitch should trigger a note."""
        rec = get_print_recommendation(
            m3_spec,
            PrintProcess.FDM,
            layer_height_mm=0.3,
        )
        has_layer_note = any("layer height" in n.lower() for n in rec.notes)
        assert has_layer_note


# =============================================================================
# optimize_thread_for_print Tests
# =============================================================================


class TestOptimizeThreadForPrint:
    """Tests for the optimize_thread_for_print function."""

    def test_external_reduces_diameters(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """External threads should have diameters reduced by clearance."""
        config = PrintThreadConfig(
            spec=m8_spec,
            thread_type=ThreadType.EXTERNAL,
            process=PrintProcess.FDM,
            tolerance_class=ToleranceClass.STANDARD,
        )
        result = optimize_thread_for_print(config)
        clearance = CLEARANCE_DEFAULTS[PrintProcess.FDM][ToleranceClass.STANDARD]
        assert result.adjusted_spec.major_diameter == pytest.approx(
            m8_spec.major_diameter - clearance,
        )
        assert result.adjusted_spec.minor_diameter_ext == pytest.approx(
            m8_spec.minor_diameter_ext - clearance,
        )

    def test_internal_increases_diameters(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Internal threads should have diameters increased by clearance."""
        config = PrintThreadConfig(
            spec=m8_spec,
            thread_type=ThreadType.INTERNAL,
            process=PrintProcess.FDM,
            tolerance_class=ToleranceClass.STANDARD,
        )
        result = optimize_thread_for_print(config)
        clearance = CLEARANCE_DEFAULTS[PrintProcess.FDM][ToleranceClass.STANDARD]
        assert result.adjusted_spec.major_diameter == pytest.approx(
            m8_spec.major_diameter + clearance,
        )
        assert result.adjusted_spec.minor_diameter_ext == pytest.approx(
            m8_spec.minor_diameter_ext + clearance,
        )

    def test_custom_clearance_used(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Custom clearance should override the process default."""
        custom = 0.42
        config = PrintThreadConfig(
            spec=m8_spec,
            thread_type=ThreadType.EXTERNAL,
            custom_clearance_mm=custom,
        )
        result = optimize_thread_for_print(config)
        assert result.adjusted_spec.major_diameter == pytest.approx(
            m8_spec.major_diameter - custom,
        )
        assert result.adjustments_applied["clearance_mm"] == custom

    def test_adjustments_documented(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """adjustments_applied should document all changes."""
        config = PrintThreadConfig(spec=m8_spec)
        result = optimize_thread_for_print(config)
        assert "major_diameter" in result.adjustments_applied
        assert "minor_diameter_ext" in result.adjustments_applied
        assert "clearance_mm" in result.adjustments_applied

    def test_adjusted_spec_is_new_object(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Adjusted spec should be a new object, not the original."""
        config = PrintThreadConfig(spec=m8_spec)
        result = optimize_thread_for_print(config)
        assert result.adjusted_spec is not m8_spec

    def test_loose_tolerance_larger_adjustment(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Loose tolerance should apply larger clearance than tight."""
        tight_cfg = PrintThreadConfig(
            spec=m8_spec, tolerance_class=ToleranceClass.TIGHT,
        )
        loose_cfg = PrintThreadConfig(
            spec=m8_spec, tolerance_class=ToleranceClass.LOOSE,
        )
        tight_result = optimize_thread_for_print(tight_cfg)
        loose_result = optimize_thread_for_print(loose_cfg)
        # Loose should reduce diameter more (external)
        assert (
            loose_result.adjusted_spec.major_diameter
            < tight_result.adjusted_spec.major_diameter
        )

    def test_tight_tolerance_smaller_adjustment(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Tight tolerance should produce closer-to-nominal diameters."""
        tight_cfg = PrintThreadConfig(
            spec=m8_spec, tolerance_class=ToleranceClass.TIGHT,
        )
        std_cfg = PrintThreadConfig(
            spec=m8_spec, tolerance_class=ToleranceClass.STANDARD,
        )
        tight_result = optimize_thread_for_print(tight_cfg)
        std_result = optimize_thread_for_print(std_cfg)
        # Tight should be closer to nominal
        tight_diff = abs(
            m8_spec.major_diameter
            - tight_result.adjusted_spec.major_diameter
        )
        std_diff = abs(
            m8_spec.major_diameter
            - std_result.adjusted_spec.major_diameter
        )
        assert tight_diff < std_diff

    def test_flat_bottom_noted(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """use_flat_bottom should be recorded in adjustments."""
        config = PrintThreadConfig(
            spec=m8_spec, use_flat_bottom=True,
        )
        result = optimize_thread_for_print(config)
        assert "flat_bottom" in result.adjustments_applied
        assert result.adjustments_applied["flat_bottom"] == 1.0

    def test_flat_bottom_not_noted_when_false(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """flat_bottom should not appear when not requested."""
        config = PrintThreadConfig(
            spec=m8_spec, use_flat_bottom=False,
        )
        result = optimize_thread_for_print(config)
        assert "flat_bottom" not in result.adjustments_applied

    def test_includes_recommendation(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Result should include a PrintRecommendation."""
        config = PrintThreadConfig(spec=m8_spec)
        result = optimize_thread_for_print(config)
        assert isinstance(result.recommendation, PrintRecommendation)
        assert isinstance(
            result.recommendation.feasibility, PrintFeasibility,
        )

    def test_sla_process_applied(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """SLA process should use SLA-specific clearance values."""
        config = PrintThreadConfig(
            spec=m8_spec,
            process=PrintProcess.SLA,
            tolerance_class=ToleranceClass.STANDARD,
        )
        result = optimize_thread_for_print(config)
        clearance = CLEARANCE_DEFAULTS[PrintProcess.SLA][
            ToleranceClass.STANDARD
        ]
        assert result.adjusted_spec.major_diameter == pytest.approx(
            m8_spec.major_diameter - clearance,
        )

    def test_pitch_diameters_adjusted(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """Pitch diameters should also be adjusted by clearance."""
        config = PrintThreadConfig(
            spec=m8_spec,
            thread_type=ThreadType.EXTERNAL,
            tolerance_class=ToleranceClass.STANDARD,
        )
        result = optimize_thread_for_print(config)
        clearance = CLEARANCE_DEFAULTS[PrintProcess.FDM][
            ToleranceClass.STANDARD
        ]
        assert result.adjusted_spec.pitch_diameter_ext == pytest.approx(
            m8_spec.pitch_diameter_ext - clearance,
        )


# =============================================================================
# get_orientation_advice Tests
# =============================================================================


class TestGetOrientationAdvice:
    """Tests for the get_orientation_advice function."""

    def test_fdm_mentions_vertical(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """FDM advice should mention vertical/Z-axis orientation."""
        advice = get_orientation_advice(m8_spec, PrintProcess.FDM)
        assert "vertical" in advice.lower() or "z-axis" in advice.lower()

    def test_sla_orientation(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """SLA advice should be non-empty and process-relevant."""
        advice = get_orientation_advice(m8_spec, PrintProcess.SLA)
        assert len(advice) > 0
        assert "sla" in advice.lower() or "orientation" in advice.lower()

    def test_returns_non_empty_string(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """All processes should return non-empty advice strings."""
        for proc in PrintProcess:
            advice = get_orientation_advice(m8_spec, proc)
            assert isinstance(advice, str)
            assert len(advice) > 10

    def test_sls_orientation(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """SLS advice should mention flexibility or accuracy."""
        advice = get_orientation_advice(m8_spec, PrintProcess.SLS)
        assert "sls" in advice.lower() or "accuracy" in advice.lower()

    def test_mjf_orientation(
        self, m8_spec: ThreadSpec,
    ) -> None:
        """MJF advice should mention surface finish or detail."""
        advice = get_orientation_advice(m8_spec, PrintProcess.MJF)
        assert "surface" in advice.lower() or "detail" in advice.lower()
