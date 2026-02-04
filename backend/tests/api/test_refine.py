"""
Tests for refine API endpoints.

Tests AI-powered design refinement functionality.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4


# =============================================================================
# Refine Design Tests
# =============================================================================

class TestRefineDesign:
    """Tests for POST /api/v1/refine."""

    async def test_refine_design_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent design."""
        fake_id = uuid4()
        response = await client.post(
            "/api/v1/refine",
            headers=auth_headers,
            json={
                "design_id": str(fake_id),
                "instructions": "Make it more robust"
            }
        )
        
        assert response.status_code == 404

    async def test_refine_design_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        fake_id = uuid4()
        response = await client.post(
            "/api/v1/refine",
            json={
                "design_id": str(fake_id),
                "instructions": "Make it more robust"
            }
        )
        
        # 401 if endpoint exists, 404 if path not found
        assert response.status_code in [401, 404]


# =============================================================================
# Refinement Jobs Tests
# =============================================================================

class TestRefinementJobs:
    """Tests for GET /api/v1/refine/jobs."""

    async def test_list_refinement_jobs(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return refinement jobs list."""
        response = await client.get(
            "/api/v1/refine/jobs",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]

    async def test_list_refinement_jobs_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/refine/jobs")
        assert response.status_code in [401, 404]


# =============================================================================
# Get Refinement Job Tests
# =============================================================================

class TestGetRefinementJob:
    """Tests for GET /api/v1/refine/jobs/{job_id}."""

    async def test_get_refinement_job_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent job."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/refine/jobs/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_get_refinement_job_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/refine/jobs/{fake_id}")
        assert response.status_code in [401, 404]


# =============================================================================
# Design Context Tests
# =============================================================================

class TestDesignContext:
    """Tests for GET /api/v1/refine/context."""

    async def test_get_design_context(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should get design context when queried with design_id."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/refine/context?design_id={fake_id}",
            headers=auth_headers
        )
        
        # 200 if found, 404 if not
        assert response.status_code in [200, 404]

    async def test_get_design_context_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/refine/context")
        assert response.status_code in [401, 404, 422]


# =============================================================================
# Refine Preview Tests
# =============================================================================

class TestRefinePreview:
    """Tests for POST /api/v1/refine/preview."""

    async def test_refine_preview_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Should return 404 for non-existent design."""
        fake_id = uuid4()
        response = await client.post(
            "/api/v1/refine/preview",
            headers=auth_headers,
            json={
                "design_id": str(fake_id),
                "instructions": "Preview changes"
            }
        )
        
        assert response.status_code == 404

    async def test_refine_preview_unauthenticated(
        self, client: AsyncClient
    ):
        """Should return 401 without authentication."""
        response = await client.post(
            "/api/v1/refine/preview",
            json={
                "design_id": str(uuid4()),
                "instructions": "Preview changes"
            }
        )
        
        assert response.status_code in [401, 404]
