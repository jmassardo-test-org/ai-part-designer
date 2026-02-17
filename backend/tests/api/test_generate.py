"""
Tests for generation API endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.generator import GenerationResult
from app.ai.parser import CADParameters, ParseResult, ShapeType

if TYPE_CHECKING:
    from httpx import AsyncClient

# =============================================================================
# Generate Endpoint Tests
# =============================================================================


class TestGenerateEndpoint:
    """Tests for POST /api/v1/generate endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires FastAPI dependency override for proper mocking. See CAD v2 migration.")
    async def test_generate_success(self, client: AsyncClient):
        """Test successful CAD generation."""
        mock_result = GenerationResult(
            description="Create a box 100x50x30mm",
            shape_type="box",
            confidence=0.9,
            dimensions={"length": 100, "width": 50, "height": 30},
            shape=MagicMock(),
            step_data=b"step content",
            stl_data=b"stl content",
            step_path=Path("/tmp/box.step"),
            stl_path=Path("/tmp/box.stl"),
            reasoning_time_ms=100,
            generation_time_ms=50,
            export_time_ms=200,
            total_time_ms=350,
            job_id="test-job-123",
            warnings=["Assumed millimeters"],
        )

        with patch(
            "app.api.v1.generate.generate_from_description", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_result

            with patch("app.api.v1.generate.get_settings") as mock_settings:
                mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
                # Route through v1 pipeline for this test
                mock_settings.return_value.CAD_V2_ENABLED = False
                mock_settings.return_value.CAD_V2_AS_DEFAULT = False

                response = await client.post(
                    "/api/v1/generate",
                    json={"description": "Create a box 100x50x30mm"},
                )

        assert response.status_code == 201
        data = response.json()

        assert data["job_id"] == "test-job-123"
        assert data["status"] == "completed"
        assert data["shape"] == "box"
        assert data["confidence"] == 0.9
        assert data["dimensions"]["length"] == 100
        assert "step" in data["downloads"]
        assert "stl" in data["downloads"]

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires FastAPI dependency override for proper mocking. See CAD v2 migration.")
    async def test_generate_no_ai_provider(self, client: AsyncClient):
        """Test error when AI provider not configured."""
        with patch("app.api.v1.generate.get_settings") as mock_settings:
            # Route through v1 pipeline
            mock_settings.return_value.CAD_V2_ENABLED = False
            mock_settings.return_value.CAD_V2_AS_DEFAULT = False
            mock_settings.return_value.ANTHROPIC_API_KEY = None
            mock_settings.return_value.OPENAI_API_KEY = None
            
            with patch("app.ai.providers.get_ai_provider") as mock_provider:
                mock_provider.side_effect = ValueError("No AI provider configured")

                response = await client.post(
                    "/api/v1/generate",
                    json={"description": "Create a box"},
                )

        assert response.status_code == 503
        assert "configured" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires FastAPI dependency override for proper mocking. See CAD v2 migration.")
    async def test_generate_invalid_quality(self, client: AsyncClient):
        """Test error for invalid STL quality."""
        with patch("app.api.v1.generate.get_settings") as mock_settings:
            mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
            # Route through v1 pipeline for quality validation
            mock_settings.return_value.CAD_V2_ENABLED = False
            mock_settings.return_value.CAD_V2_AS_DEFAULT = False

            response = await client.post(
                "/api/v1/generate",
                json={
                    "description": "Create a box",
                    "stl_quality": "invalid_quality",
                },
            )

        assert response.status_code == 400
        assert "quality" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_generate_empty_description(self, client: AsyncClient):
        """Test validation error for empty description."""
        response = await client.post(
            "/api/v1/generate",
            json={"description": ""},
        )

        # Pydantic validation should catch this
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_short_description(self, client: AsyncClient):
        """Test validation error for too-short description."""
        response = await client.post(
            "/api/v1/generate",
            json={"description": "ab"},  # Less than min_length=3
        )

        assert response.status_code == 422


# =============================================================================
# Parse Endpoint Tests
# =============================================================================


class TestParseEndpoint:
    """Tests for POST /api/v1/generate/parse endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires FastAPI dependency override for proper mocking. See CAD v2 migration.")
    async def test_parse_success(self, client: AsyncClient):
        """Test successful description parsing."""
        mock_result = ParseResult(
            parameters=CADParameters(
                shape=ShapeType.CYLINDER,
                dimensions={"radius": 25, "height": 100},
                confidence=0.85,
                assumptions=["Assumed centered"],
            ),
            raw_response="{}",
            parse_time_ms=80,
        )

        # Mock the parse_description in the correct location (app.ai.parser)
        with patch("app.ai.parser.parse_description", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_result

            with patch("app.api.v1.generate.get_settings") as mock_settings:
                mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"

                response = await client.post(
                    "/api/v1/generate/parse",
                    json={"description": "Create a cylinder 50mm diameter, 100mm tall"},
                )

        assert response.status_code == 200
        data = response.json()

        assert data["shape"] == "cylinder"
        assert data["dimensions"]["radius"] == 25
        assert data["confidence"] == 0.85
        assert "Assumed centered" in data["assumptions"]


# =============================================================================
# List Endpoints Tests
# =============================================================================


class TestListEndpoints:
    """Tests for list endpoints."""

    @pytest.mark.asyncio
    async def test_list_shapes(self, client: AsyncClient):
        """Test GET /api/v1/generate/shapes."""
        response = await client.get("/api/v1/generate/shapes")

        assert response.status_code == 200
        data = response.json()

        assert "shapes" in data
        shape_ids = [s["id"] for s in data["shapes"]]

        assert "box" in shape_ids
        assert "cylinder" in shape_ids
        assert "sphere" in shape_ids

    @pytest.mark.asyncio
    async def test_list_qualities(self, client: AsyncClient):
        """Test GET /api/v1/generate/qualities."""
        response = await client.get("/api/v1/generate/qualities")

        assert response.status_code == 200
        data = response.json()

        assert "qualities" in data
        quality_ids = [q["id"] for q in data["qualities"]]

        assert "draft" in quality_ids
        assert "standard" in quality_ids
        assert "high" in quality_ids
        assert "ultra" in quality_ids


# =============================================================================
# Download Endpoint Tests
# =============================================================================


class TestDownloadEndpoint:
    """Tests for GET /api/v1/generate/{job_id}/download/{format} endpoint."""

    @pytest.mark.asyncio
    async def test_download_stl_success(self, simple_client: AsyncClient, tmp_path):
        """Test successful STL download."""
        import tempfile
        from pathlib import Path

        # Create a fake STL file in the expected location
        job_id = "abc12345-1234-5678-9abc-def012345678"
        export_dir = Path(tempfile.gettempdir()) / "cad_exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        stl_file = export_dir / f"box_{job_id[:8]}.stl"
        stl_file.write_bytes(b"solid test\nendsolid test")

        try:
            response = await simple_client.get(f"/api/v1/generate/{job_id}/download/stl")

            assert response.status_code == 200
            assert b"solid test" in response.content
            assert "application/sla" in response.headers.get("content-type", "")
        finally:
            stl_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_download_step_success(self, simple_client: AsyncClient, tmp_path):
        """Test successful STEP download."""
        import tempfile
        from pathlib import Path

        # Create a fake STEP file in the expected location
        job_id = "def12345-1234-5678-9abc-def012345678"
        export_dir = Path(tempfile.gettempdir()) / "cad_exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        step_file = export_dir / f"cylinder_{job_id[:8]}.step"
        step_file.write_bytes(b"ISO-10303-21;\nHEADER;\nENDSEC;")

        try:
            response = await simple_client.get(f"/api/v1/generate/{job_id}/download/step")

            assert response.status_code == 200
            assert b"ISO-10303-21" in response.content
            assert "application/STEP" in response.headers.get("content-type", "")
        finally:
            step_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_download_not_found(self, simple_client: AsyncClient):
        """Test 404 when file doesn't exist."""
        import uuid

        # Use a valid UUID format that doesn't have an existing file
        job_id = str(uuid.uuid4())
        response = await simple_client.get(f"/api/v1/generate/{job_id}/download/stl")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_invalid_format(self, simple_client: AsyncClient):
        """Test error for invalid format."""
        response = await simple_client.get("/api/v1/generate/some-job-id/download/obj")

        # FastAPI returns 422 for invalid path parameter values
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_download_invalid_job_id_format(self, simple_client: AsyncClient):
        """Test 400 for invalid job ID format (non-UUID)."""
        # Test with an invalid non-UUID job_id
        response = await simple_client.get("/api/v1/generate/invalid-job-id/download/stl")

        # Should be rejected as 400 (invalid UUID format)
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_with_auth_user_mismatch(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_2,
        db_session,
    ):
        """Test 403 when user tries to download another user's job."""
        from uuid import uuid4

        from app.models.job import Job

        # Create another user's job using test_user_2
        job_id = uuid4()

        job = Job(
            id=job_id,
            user_id=test_user_2.id,  # Different user (test_user_2)
            job_type="generation",
            status="completed",
            input_params={"description": "test"},
            result={"shape": "box"},
        )
        db_session.add(job)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/generate/{job_id}/download/stl",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "denied" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_download_file_expired_message(self, simple_client: AsyncClient):
        """Test that expired file message is helpful."""
        import uuid

        job_id = str(uuid.uuid4())

        response = await simple_client.get(f"/api/v1/generate/{job_id}/download/stl")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "expired" in detail.lower() or "not found" in detail.lower()


class TestAssemblyPartDownloadSecurity:
    """Security tests for assembly part download endpoint."""

    @pytest.mark.asyncio
    async def test_assembly_download_invalid_chars_blocked(self, simple_client: AsyncClient):
        """Test that invalid characters in part names are blocked."""
        import uuid

        job_id = str(uuid.uuid4())

        # Test patterns with invalid characters that actually reach the endpoint
        # Note: Some path traversal patterns (like ..) are handled by URL routing
        # before reaching the endpoint, so we test characters that pass through routing
        invalid_patterns = [
            "..%00",  # Null byte injection attempt
            "part%3B",  # Semicolon (encoded)
            ".hidden",  # Hidden file prefix
        ]

        for pattern in invalid_patterns:
            response = await simple_client.get(
                f"/api/v1/generate/{job_id}/download/step/{pattern}"
            )
            # Should be rejected as 400 (invalid part name) or 422 (validation error)
            assert response.status_code in (400, 422), f"Pattern {pattern} should be rejected"

    @pytest.mark.asyncio
    async def test_assembly_download_invalid_part_name_chars(self, simple_client: AsyncClient):
        """Test that special characters in part_name are rejected."""
        import uuid

        job_id = str(uuid.uuid4())

        # Test with special characters that will reach the endpoint
        # and fail the regex validation [a-zA-Z0-9_-]+
        invalid_names = [
            "part;rm",  # Semicolon
            "part%3Cscript%3E",  # URL-encoded angle brackets
            "part%00null",  # Null byte (encoded)
        ]

        for part_name in invalid_names:
            response = await simple_client.get(
                f"/api/v1/generate/{job_id}/download/step/{part_name}"
            )
            # Should be rejected as 400 (invalid chars) or 422 (validation error)
            assert response.status_code in (400, 422), f"Should reject part_name: {part_name}"

    @pytest.mark.asyncio
    async def test_assembly_download_valid_part_name_format(self, simple_client: AsyncClient):
        """Test that valid part names are accepted (but file not found is OK)."""
        import uuid

        job_id = str(uuid.uuid4())

        # Valid part names (will 404 because file doesn't exist, but shouldn't 400)
        valid_names = [
            "enclosure_base",
            "lid-top",
            "Part1",
            "mount_bracket_v2",
        ]

        for part_name in valid_names:
            response = await simple_client.get(
                f"/api/v1/generate/{job_id}/download/step/{part_name}"
            )
            # Should be 404 (not found) not 400 (bad request)
            assert response.status_code == 404, (
                f"Valid part name {part_name} should pass validation"
            )

    @pytest.mark.asyncio
    async def test_assembly_download_invalid_job_id(self, simple_client: AsyncClient):
        """Test that invalid job IDs are rejected."""
        response = await simple_client.get("/api/v1/generate/not-a-uuid/download/step/base_part")

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_assembly_download_auth_check(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user_2,
        db_session,
    ):
        """Test that authenticated users can only download their own assembly parts."""
        from uuid import uuid4

        from app.models.job import Job

        job_id = uuid4()

        job = Job(
            id=job_id,
            user_id=test_user_2.id,  # Different user (test_user_2)
            job_type="generation",
            status="completed",
            input_params={"description": "test assembly"},
            result={"shape": "enclosure"},
        )
        db_session.add(job)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/generate/{job_id}/download/step/enclosure_base",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "denied" in response.json()["detail"].lower()
