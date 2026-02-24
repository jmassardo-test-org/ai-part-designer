"""
Tests for the thread library API endpoints (v2).

Covers all seven endpoints: family listing, size listing, spec lookup,
tap drill info, thread generation, print-optimised generation, and
print recommendations.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.cad.thread_generator import ThreadGenerationResult
from app.cad.threads import ThreadFamily


# =============================================================================
# Helpers
# =============================================================================

API_PREFIX = "/api/v2/threads"


def _mock_generation_result() -> ThreadGenerationResult:
    """Build a lightweight mock ``ThreadGenerationResult``."""
    return ThreadGenerationResult(
        part=MagicMock(),  # Build123d Part — not serialised
        metadata={"family": "iso_metric", "size": "M8"},
        generation_time_ms=42,
        estimated_face_count=1024,
    )


# =============================================================================
# GET /families
# =============================================================================


class TestListFamilies:
    """Tests for listing thread families."""

    @pytest.mark.asyncio
    async def test_returns_all_families(
        self, client: AsyncClient,
    ) -> None:
        """Should return every registered thread family."""
        resp = await client.get(f"{API_PREFIX}/families")
        assert resp.status_code == 200

        data = resp.json()
        families = data["families"]
        assert len(families) == len(ThreadFamily)

    @pytest.mark.asyncio
    async def test_response_has_total(
        self, client: AsyncClient,
    ) -> None:
        """Total field should match the families list length."""
        resp = await client.get(f"{API_PREFIX}/families")
        data = resp.json()
        assert data["total"] == len(data["families"])

    @pytest.mark.asyncio
    async def test_each_family_has_required_fields(
        self, client: AsyncClient,
    ) -> None:
        """Every family object should contain the expected keys."""
        resp = await client.get(f"{API_PREFIX}/families")
        for fam in resp.json()["families"]:
            assert "family" in fam
            assert "name" in fam
            assert "description" in fam
            assert "standard_ref" in fam
            assert "size_count" in fam
            assert isinstance(fam["size_count"], int)
            assert fam["size_count"] > 0


# =============================================================================
# GET /standards/{family}
# =============================================================================


class TestListSizes:
    """Tests for listing thread sizes within a family."""

    @pytest.mark.asyncio
    async def test_valid_family_returns_sizes(
        self, client: AsyncClient,
    ) -> None:
        """Should return sizes for a valid family."""
        resp = await client.get(f"{API_PREFIX}/standards/iso_metric")
        assert resp.status_code == 200

        data = resp.json()
        assert data["family"] == "iso_metric"
        assert len(data["sizes"]) > 0
        assert data["total"] == len(data["sizes"])

    @pytest.mark.asyncio
    async def test_unknown_family_returns_404(
        self, client: AsyncClient,
    ) -> None:
        """Should return 404 for a non-existent family."""
        resp = await client.get(f"{API_PREFIX}/standards/bogus_family")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_metric_coarse_filter(
        self, client: AsyncClient,
    ) -> None:
        """Filtering by coarse pitch series should narrow results."""
        all_resp = await client.get(f"{API_PREFIX}/standards/iso_metric")
        coarse_resp = await client.get(
            f"{API_PREFIX}/standards/iso_metric?pitch_series=coarse",
        )

        assert all_resp.status_code == 200
        assert coarse_resp.status_code == 200

        all_sizes = all_resp.json()["sizes"]
        coarse_sizes = coarse_resp.json()["sizes"]
        assert len(coarse_sizes) <= len(all_sizes)
        assert coarse_resp.json()["pitch_series"] == "coarse"


# =============================================================================
# GET /standards/{family}/{size}
# =============================================================================


class TestGetSpec:
    """Tests for retrieving a specific thread specification."""

    @pytest.mark.asyncio
    async def test_valid_spec_returns_data(
        self, client: AsyncClient,
    ) -> None:
        """Should return the full specification for a known size."""
        resp = await client.get(f"{API_PREFIX}/standards/iso_metric/M8")
        assert resp.status_code == 200

        data = resp.json()
        assert data["family"] == "iso_metric"
        assert data["size"] == "M8"
        assert data["pitch_mm"] > 0
        assert data["major_diameter"] > 0

    @pytest.mark.asyncio
    async def test_unknown_family_returns_404(
        self, client: AsyncClient,
    ) -> None:
        """Should return 404 for a non-existent family."""
        resp = await client.get(f"{API_PREFIX}/standards/bogus/M8")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unknown_size_returns_404(
        self, client: AsyncClient,
    ) -> None:
        """Should return 404 for a non-existent size."""
        resp = await client.get(f"{API_PREFIX}/standards/iso_metric/M999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_size_with_slash_works(
        self, client: AsyncClient,
    ) -> None:
        """Sizes containing slashes (e.g. 1/4-20) should be routed."""
        resp = await client.get(f"{API_PREFIX}/standards/unc/1/4-20")
        assert resp.status_code == 200

        data = resp.json()
        assert data["size"] == "1/4-20"


# =============================================================================
# GET /tap-drill/{family}/{size}
# =============================================================================


class TestGetTapDrill:
    """Tests for tap drill information."""

    @pytest.mark.asyncio
    async def test_valid_returns_drill_info(
        self, client: AsyncClient,
    ) -> None:
        """Should return positive drill dimensions."""
        resp = await client.get(f"{API_PREFIX}/tap-drill/iso_metric/M8")
        assert resp.status_code == 200

        data = resp.json()
        assert data["family"] == "iso_metric"
        assert data["size"] == "M8"
        assert data["tap_drill_mm"] > 0
        assert data["clearance_hole_close_mm"] > 0

    @pytest.mark.asyncio
    async def test_unknown_size_returns_404(
        self, client: AsyncClient,
    ) -> None:
        """Should return 404 for a non-existent size."""
        resp = await client.get(f"{API_PREFIX}/tap-drill/iso_metric/M999")
        assert resp.status_code == 404


# =============================================================================
# POST /generate
# =============================================================================


class TestGenerate:
    """Tests for thread geometry generation."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient,
    ) -> None:
        """Should reject unauthenticated requests."""
        resp = await client.post(
            f"{API_PREFIX}/generate",
            json={
                "family": "iso_metric",
                "size": "M8",
                "length_mm": 20.0,
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_request_returns_success(
        self,
        mock_auth_client: AsyncClient,
    ) -> None:
        """Should generate thread geometry for a valid request."""
        mock_result = _mock_generation_result()

        with patch(
            "app.api.v2.threads.generate_thread",
            return_value=mock_result,
        ):
            resp = await mock_auth_client.post(
                f"{API_PREFIX}/generate",
                json={
                    "family": "iso_metric",
                    "size": "M8",
                    "length_mm": 20.0,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["generation_time_ms"] >= 0
        assert data["estimated_face_count"] > 0

    @pytest.mark.asyncio
    async def test_invalid_family_returns_error(
        self,
        mock_auth_client: AsyncClient,
    ) -> None:
        """Should return 404 for an unknown family."""
        resp = await mock_auth_client.post(
            f"{API_PREFIX}/generate",
            json={
                "family": "bogus",
                "size": "M8",
                "length_mm": 20.0,
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_length_returns_422(
        self,
        mock_auth_client: AsyncClient,
    ) -> None:
        """Should reject non-positive or excessively large lengths."""
        resp = await mock_auth_client.post(
            f"{API_PREFIX}/generate",
            json={
                "family": "iso_metric",
                "size": "M8",
                "length_mm": -5.0,
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_length_over_max_returns_422(
        self,
        mock_auth_client: AsyncClient,
    ) -> None:
        """Should reject length exceeding the 200 mm maximum."""
        resp = await mock_auth_client.post(
            f"{API_PREFIX}/generate",
            json={
                "family": "iso_metric",
                "size": "M8",
                "length_mm": 999.0,
            },
        )
        assert resp.status_code == 422


# =============================================================================
# POST /generate/print-optimized
# =============================================================================


class TestGeneratePrintOptimized:
    """Tests for print-optimised thread generation."""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient,
    ) -> None:
        """Should reject unauthenticated requests."""
        resp = await client.post(
            f"{API_PREFIX}/generate/print-optimized",
            json={
                "family": "iso_metric",
                "size": "M8",
                "length_mm": 20.0,
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_request_returns_success(
        self,
        mock_auth_client: AsyncClient,
    ) -> None:
        """Should return success with feasibility information."""
        mock_result = _mock_generation_result()

        with patch(
            "app.api.v2.threads.generate_thread",
            return_value=mock_result,
        ):
            resp = await mock_auth_client.post(
                f"{API_PREFIX}/generate/print-optimized",
                json={
                    "family": "iso_metric",
                    "size": "M8",
                    "length_mm": 20.0,
                    "process": "fdm",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "feasibility" in data
        assert "recommendation" in data

    @pytest.mark.asyncio
    async def test_includes_feasibility(
        self,
        mock_auth_client: AsyncClient,
    ) -> None:
        """Response should contain feasibility rating and adjustments."""
        mock_result = _mock_generation_result()

        with patch(
            "app.api.v2.threads.generate_thread",
            return_value=mock_result,
        ):
            resp = await mock_auth_client.post(
                f"{API_PREFIX}/generate/print-optimized",
                json={
                    "family": "iso_metric",
                    "size": "M8",
                    "length_mm": 20.0,
                    "process": "fdm",
                    "tolerance_class": "standard",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["feasibility"] in [
            "excellent",
            "good",
            "marginal",
            "not_recommended",
        ]
        assert isinstance(data["adjustments_applied"], dict)
        rec = data["recommendation"]
        assert "orientation_advice" in rec
        assert rec["estimated_strength_pct"] > 0


# =============================================================================
# GET /print-recommendations/{family}/{size}
# =============================================================================


class TestGetPrintRecommendation:
    """Tests for print feasibility recommendations."""

    @pytest.mark.asyncio
    async def test_valid_returns_recommendation(
        self, client: AsyncClient,
    ) -> None:
        """Should return recommendation for a valid family/size."""
        resp = await client.get(
            f"{API_PREFIX}/print-recommendations/iso_metric/M8",
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["family"] == "iso_metric"
        assert data["size"] == "M8"
        assert data["feasibility"] in [
            "excellent",
            "good",
            "marginal",
            "not_recommended",
        ]
        assert data["estimated_strength_pct"] > 0

    @pytest.mark.asyncio
    async def test_fdm_small_thread_shows_warning(
        self, client: AsyncClient,
    ) -> None:
        """Small threads on FDM should return a warning or lower rating."""
        resp = await client.get(
            f"{API_PREFIX}/print-recommendations/iso_metric/M3"
            "?process=fdm&nozzle_diameter_mm=0.4",
        )
        assert resp.status_code == 200

        data = resp.json()
        # M3 with 0.5 mm pitch is below FDM minimum (1.0 mm) → not recommended
        assert data["feasibility"] in ["marginal", "not_recommended"]

    @pytest.mark.asyncio
    async def test_unknown_family_returns_404(
        self, client: AsyncClient,
    ) -> None:
        """Should return 404 for a non-existent family."""
        resp = await client.get(
            f"{API_PREFIX}/print-recommendations/bogus/M8",
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_process_returns_400(
        self, client: AsyncClient,
    ) -> None:
        """Should return 400 for an unsupported print process."""
        resp = await client.get(
            f"{API_PREFIX}/print-recommendations/iso_metric/M8"
            "?process=magic_printer",
        )
        assert resp.status_code == 400
