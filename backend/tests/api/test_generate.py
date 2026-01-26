"""
Tests for generation API endpoints.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from httpx import AsyncClient

from app.ai.parser import CADParameters, ShapeType, ParseResult
from app.ai.generator import GenerationResult


# =============================================================================
# Generate Endpoint Tests
# =============================================================================

class TestGenerateEndpoint:
    """Tests for POST /api/v1/generate endpoint."""
    
    @pytest.mark.asyncio
    async def test_generate_success(self, client: AsyncClient):
        """Test successful CAD generation."""
        mock_result = GenerationResult(
            description="Create a box 100x50x30mm",
            parameters=CADParameters(
                shape=ShapeType.BOX,
                dimensions={"length": 100, "width": 50, "height": 30},
                confidence=0.9,
            ),
            shape=MagicMock(),
            step_data=b"step content",
            stl_data=b"stl content",
            step_path=Path("/tmp/box.step"),
            stl_path=Path("/tmp/box.stl"),
            parse_time_ms=100,
            generate_time_ms=50,
            export_time_ms=200,
            total_time_ms=350,
            job_id="test-job-123",
            warnings=["Assumed millimeters"],
        )
        
        with patch("app.api.v1.generate.generate_from_description", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_result
            
            with patch("app.core.config.get_settings") as mock_settings:
                mock_settings.return_value.OPENAI_API_KEY = "test-key"
                
                response = await client.post(
                    "/api/v1/generate/",
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
    async def test_generate_no_api_key(self, client: AsyncClient):
        """Test error when OpenAI API key not configured."""
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.OPENAI_API_KEY = None
            
            response = await client.post(
                "/api/v1/generate/",
                json={"description": "Create a box"},
            )
        
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_invalid_quality(self, client: AsyncClient):
        """Test error for invalid STL quality."""
        with patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            
            response = await client.post(
                "/api/v1/generate/",
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
            "/api/v1/generate/",
            json={"description": ""},
        )
        
        # Pydantic validation should catch this
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_generate_short_description(self, client: AsyncClient):
        """Test validation error for too-short description."""
        response = await client.post(
            "/api/v1/generate/",
            json={"description": "ab"},  # Less than min_length=3
        )
        
        assert response.status_code == 422


# =============================================================================
# Parse Endpoint Tests
# =============================================================================

class TestParseEndpoint:
    """Tests for POST /api/v1/generate/parse endpoint."""
    
    @pytest.mark.asyncio
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
        
        with patch("app.api.v1.generate.parse_description", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_result
            
            with patch("app.core.config.get_settings") as mock_settings:
                mock_settings.return_value.OPENAI_API_KEY = "test-key"
                
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
            response = await simple_client.get(
                f"/api/v1/generate/{job_id}/download/stl"
            )
            
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
            response = await simple_client.get(
                f"/api/v1/generate/{job_id}/download/step"
            )
            
            assert response.status_code == 200
            assert b"ISO-10303-21" in response.content
            assert "application/STEP" in response.headers.get("content-type", "")
        finally:
            step_file.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_download_not_found(self, simple_client: AsyncClient):
        """Test 404 when file doesn't exist."""
        response = await simple_client.get(
            "/api/v1/generate/nonexistent-job-id/download/stl"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_download_invalid_format(self, simple_client: AsyncClient):
        """Test error for invalid format."""
        response = await simple_client.get(
            "/api/v1/generate/some-job-id/download/obj"
        )
        
        # FastAPI returns 422 for invalid path parameter values
        assert response.status_code == 422
