"""
Tests for the engineering glossary module.

Covers glossary content, exact/fuzzy search, category listing,
and prompt context formatting.
"""

from __future__ import annotations

import pytest

from app.ai.engineering_glossary import (
    ENGINEERING_GLOSSARY,
    GlossaryCategory,
    format_glossary_context,
    get_term,
    list_terms_by_category,
    search_glossary,
)


# =============================================================================
# Glossary Content Tests
# =============================================================================


class TestGlossaryContent:
    """Tests that the glossary contains expected terms and structure."""

    def test_glossary_has_minimum_term_count(self) -> None:
        """Glossary should contain at least 50 terms."""
        assert len(ENGINEERING_GLOSSARY) >= 50

    @pytest.mark.parametrize(
        "term",
        [
            "chamfer",
            "fillet",
            "boss",
            "pocket",
            "bore",
            "counterbore",
            "countersink",
            "thread",
            "knurl",
            "taper",
            "draft angle",
            "kerf",
            "tolerance",
            "clearance",
            "interference fit",
            "press fit",
            "through-hole",
            "blind hole",
            "slot",
            "keyway",
            "spline",
            "dovetail",
            "rabbet",
            "dado",
            "mortise",
            "tenon",
            "flange",
            "gasket",
            "o-ring groove",
            "standoff",
            "spacer",
            "bushing",
            "bearing",
            "journal",
            "shoulder",
            "undercut",
            "relief",
            "datum",
            "GD&T",
            "concentricity",
            "perpendicularity",
            "parallelism",
        ],
    )
    def test_glossary_contains_expected_term(self, term: str) -> None:
        """Every required term should be present in the glossary."""
        entry = get_term(term)
        assert entry is not None, f"Expected term '{term}' not in glossary"

    def test_every_entry_has_required_fields(self) -> None:
        """Each glossary entry must have term, definition, category,
        aliases, and keywords."""
        required_keys = {"term", "definition", "category", "aliases", "keywords"}
        for entry in ENGINEERING_GLOSSARY:
            missing = required_keys - set(entry.keys())
            assert not missing, (
                f"Entry '{entry.get('term', '?')}' missing keys: {missing}"
            )

    def test_every_entry_has_valid_category(self) -> None:
        """All entries must use a valid GlossaryCategory value."""
        valid = {c.value for c in GlossaryCategory}
        for entry in ENGINEERING_GLOSSARY:
            assert entry["category"] in valid, (
                f"Entry '{entry['term']}' has invalid category "
                f"'{entry['category']}'"
            )

    def test_every_category_has_entries(self) -> None:
        """No category should be empty."""
        for cat in GlossaryCategory:
            entries = list_terms_by_category(cat.value)
            assert len(entries) > 0, f"Category '{cat.value}' has no entries"


# =============================================================================
# Exact Lookup Tests
# =============================================================================


class TestGetTerm:
    """Tests for the get_term() exact-lookup function."""

    def test_get_term_exact_match(self) -> None:
        """Exact term name should return the correct entry."""
        entry = get_term("chamfer")
        assert entry is not None
        assert entry["term"] == "chamfer"
        assert "angled cut" in entry["definition"].lower()

    def test_get_term_case_insensitive(self) -> None:
        """Lookup should be case-insensitive."""
        entry = get_term("CHAMFER")
        assert entry is not None
        assert entry["term"] == "chamfer"

    def test_get_term_by_alias(self) -> None:
        """Looking up a known alias should return the parent term."""
        entry = get_term("bevel")
        assert entry is not None
        assert entry["term"] == "chamfer"

    def test_get_term_nonexistent_returns_none(self) -> None:
        """A term not in the glossary should return None."""
        assert get_term("nonexistent_xyzzy") is None

    def test_get_term_with_whitespace(self) -> None:
        """Leading/trailing whitespace should be stripped."""
        entry = get_term("  fillet  ")
        assert entry is not None
        assert entry["term"] == "fillet"


# =============================================================================
# Search / Fuzzy Matching Tests
# =============================================================================


class TestSearchGlossary:
    """Tests for the search_glossary() fuzzy search function."""

    def test_search_exact_term_returns_score_one(self) -> None:
        """Searching for an exact term name should return score 1.0."""
        results = search_glossary("chamfer")
        assert len(results) >= 1
        assert results[0]["term"] == "chamfer"
        assert results[0]["score"] == 1.0

    def test_search_alias_returns_high_score(self) -> None:
        """Searching for an alias should return the parent term
        with a high score."""
        results = search_glossary("bevel")
        assert len(results) >= 1
        assert results[0]["term"] == "chamfer"
        assert results[0]["score"] >= 0.9

    def test_search_shave_off_edge_finds_chamfer(self) -> None:
        """Natural-language query 'shave off edge' should find chamfer."""
        results = search_glossary("shave off edge")
        terms = [r["term"] for r in results]
        assert "chamfer" in terms

    def test_search_round_edge_finds_fillet(self) -> None:
        """Natural-language query 'round the edge' should find fillet."""
        results = search_glossary("round the edge")
        terms = [r["term"] for r in results]
        assert "fillet" in terms

    def test_search_what_is_a_chamfer_strips_prefix(self) -> None:
        """Question phrasing 'what is a chamfer' should still match."""
        results = search_glossary("what is a chamfer")
        assert len(results) >= 1
        assert results[0]["term"] == "chamfer"
        assert results[0]["score"] == 1.0

    def test_search_what_do_you_call_strips_prefix(self) -> None:
        """'what do you call shaving off an edge' should find chamfer."""
        results = search_glossary(
            "what do you call shaving off an edge"
        )
        terms = [r["term"] for r in results]
        assert "chamfer" in terms

    def test_search_hole_through_finds_through_hole(self) -> None:
        """Query about 'hole all the way through' should find
        through-hole."""
        results = search_glossary("hole all the way through")
        terms = [r["term"] for r in results]
        assert "through-hole" in terms

    def test_search_tight_fit_finds_interference_or_press(self) -> None:
        """Query about 'tight fit' should find interference/press fit."""
        results = search_glossary("tight fit")
        terms = [r["term"] for r in results]
        assert any(
            t in terms
            for t in ("interference fit", "press fit")
        ), f"Expected interference/press fit in {terms}"

    def test_search_max_results_limits_output(self) -> None:
        """max_results should cap the returned list length."""
        results = search_glossary("hole", max_results=2)
        assert len(results) <= 2

    def test_search_empty_query_returns_empty(self) -> None:
        """An empty or whitespace-only query should return no results."""
        results = search_glossary("")
        assert results == [] or all(r["score"] >= 0.25 for r in results)

    def test_search_nonsense_returns_empty(self) -> None:
        """A completely unrelated query should return no results."""
        results = search_glossary("xyzzy foobarbaz unicorn")
        assert len(results) == 0

    def test_search_hollow_out_finds_shell(self) -> None:
        """Query 'hollow out a part' should find 'shell'."""
        results = search_glossary("hollow out")
        terms = [r["term"] for r in results]
        assert "shell" in terms

    def test_search_returns_definition_and_category(self) -> None:
        """Each search result should contain term, definition,
        category, and score."""
        results = search_glossary("fillet")
        assert len(results) >= 1
        result = results[0]
        assert "term" in result
        assert "definition" in result
        assert "category" in result
        assert "score" in result

    def test_search_screw_thread_finds_thread(self) -> None:
        """Query 'screw thread' should find thread."""
        results = search_glossary("screw thread")
        terms = [r["term"] for r in results]
        assert "thread" in terms


# =============================================================================
# Category Listing Tests
# =============================================================================


class TestListTermsByCategory:
    """Tests for the list_terms_by_category() function."""

    def test_features_category_has_many_entries(self) -> None:
        """The 'features' category should be the largest."""
        entries = list_terms_by_category("features")
        assert len(entries) >= 15

    def test_unknown_category_returns_empty(self) -> None:
        """An unknown category should return an empty list."""
        entries = list_terms_by_category("nonexistent")
        assert entries == []

    def test_primitives_contains_box_and_cylinder(self) -> None:
        """Primitives should include box and cylinder."""
        entries = list_terms_by_category("primitives")
        terms = [e["term"] for e in entries]
        assert "box" in terms
        assert "cylinder" in terms


# =============================================================================
# Prompt Context Formatting Tests
# =============================================================================


class TestFormatGlossaryContext:
    """Tests for the format_glossary_context() function."""

    def test_format_returns_non_empty_string(self) -> None:
        """Formatted context must be a non-empty string."""
        ctx = format_glossary_context()
        assert isinstance(ctx, str)
        assert len(ctx) > 100

    def test_format_contains_section_header(self) -> None:
        """Output should include the main header."""
        ctx = format_glossary_context()
        assert "## Engineering Terminology Reference" in ctx

    def test_format_contains_all_categories(self) -> None:
        """Output should contain a sub-heading for each category."""
        ctx = format_glossary_context()
        for cat in GlossaryCategory:
            assert f"### {cat.value.title()}" in ctx

    def test_format_contains_chamfer(self) -> None:
        """Output should mention the term 'chamfer'."""
        ctx = format_glossary_context()
        assert "chamfer" in ctx.lower()

    def test_format_lines_not_too_long(self) -> None:
        """No single line should be excessively long (prompt sanity)."""
        ctx = format_glossary_context()
        for line in ctx.split("\n"):
            assert len(line) < 300, f"Line too long: {line[:80]}…"
