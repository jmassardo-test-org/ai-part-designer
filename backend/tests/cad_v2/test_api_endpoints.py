"""Tests for CAD v2 API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestComponentsEndpoints:
    """Tests for /api/v2/components endpoints."""

    def test_list_components(self, client: TestClient) -> None:
        """Should list all components."""
        response = client.get("/api/v2/components/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check structure
        comp = data[0]
        assert "id" in comp
        assert "name" in comp
        assert "category" in comp
        assert "dimensions_mm" in comp

    def test_list_components_filter_by_category(self, client: TestClient) -> None:
        """Should filter components by category."""
        response = client.get("/api/v2/components/?category=board")
        assert response.status_code == 200
        data = response.json()
        assert all(c["category"] == "board" for c in data)

    def test_list_components_empty_category(self, client: TestClient) -> None:
        """Should return empty list for non-existent category."""
        response = client.get("/api/v2/components/?category=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_categories(self, client: TestClient) -> None:
        """Should list all categories."""
        response = client.get("/api/v2/components/categories", follow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "board" in data["categories"]
        assert "display" in data["categories"]

    def test_search_components(self, client: TestClient) -> None:
        """Should search for components."""
        response = client.get("/api/v2/components/search?q=raspberry", follow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "raspberry"
        assert data["total"] > 0

    def test_search_components_no_results(self, client: TestClient) -> None:
        """Should handle no search results."""
        response = client.get("/api/v2/components/search?q=xyznonexistent", follow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_search_requires_query(self, client: TestClient) -> None:
        """Should require search query."""
        response = client.get("/api/v2/components/search?q=", follow_redirects=True)
        assert response.status_code == 422

    def test_get_component_by_id(self, client: TestClient) -> None:
        """Should get component details by ID."""
        response = client.get("/api/v2/components/raspberry-pi-5", follow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "raspberry-pi-5"
        assert data["name"] == "Raspberry Pi 5"
        assert "mounting_holes" in data
        assert "ports" in data

    def test_get_component_not_found(self, client: TestClient) -> None:
        """Should return 404 for non-existent component."""
        response = client.get("/api/v2/components/nonexistent-board", follow_redirects=True)
        assert response.status_code == 404

    def test_enclosure_suggestion(self, client: TestClient) -> None:
        """Should get enclosure suggestion for component."""
        response = client.get(
            "/api/v2/components/raspberry-pi-5/enclosure-suggestion", follow_redirects=True
        )
        assert response.status_code == 200
        data = response.json()
        assert "component" in data
        assert "suggested_enclosure" in data
        assert "exterior" in data["suggested_enclosure"]
        assert "notes" in data

    def test_enclosure_suggestion_not_found(self, client: TestClient) -> None:
        """Should return 404 for non-existent component."""
        response = client.get(
            "/api/v2/components/nonexistent/enclosure-suggestion", follow_redirects=True
        )
        assert response.status_code == 404


class TestEnclosuresEndpoints:
    """Tests for /api/v2/enclosures endpoints."""

    def test_create_enclosure(self, client: TestClient) -> None:
        """Should create enclosure from dimensions."""
        response = client.post(
            "/api/v2/enclosures/",
            json={
                "width_mm": 100,
                "depth_mm": 80,
                "height_mm": 40,
                "wall_thickness_mm": 2.5,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "enclosure_schema" in data
        assert "exterior_mm" in data
        assert "interior_mm" in data
        assert data["exterior_mm"] == [100, 80, 40]

    def test_create_enclosure_with_options(self, client: TestClient) -> None:
        """Should create enclosure with all options."""
        response = client.post(
            "/api/v2/enclosures/",
            json={
                "width_mm": 120,
                "depth_mm": 100,
                "height_mm": 50,
                "wall_thickness_mm": 3.0,
                "corner_radius_mm": 5.0,
                "lid_type": "screw_on",
                "ventilation_enabled": True,
                "ventilation_sides": ["left", "right"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        schema = data["enclosure_schema"]
        assert schema["corner_radius"]["value"] == 5.0
        assert schema["lid"]["type"] == "screw_on"
        assert schema["ventilation"]["enabled"] is True

    def test_create_enclosure_invalid_dimensions(self, client: TestClient) -> None:
        """Should reject invalid dimensions."""
        response = client.post(
            "/api/v2/enclosures/",
            json={
                "width_mm": -10,  # Invalid
                "depth_mm": 80,
                "height_mm": 40,
            },
        )
        assert response.status_code == 422

    def test_validate_schema(self, client: TestClient) -> None:
        """Should validate enclosure schema."""
        response = client.post(
            "/api/v2/enclosures/validate",
            json={
                "enclosure_schema": {
                    "exterior": {
                        "width": {"value": 100, "unit": "mm"},
                        "depth": {"value": 80, "unit": "mm"},
                        "height": {"value": 40, "unit": "mm"},
                    },
                    "walls": {
                        "thickness": {"value": 2.5, "unit": "mm"},
                    },
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_validate_schema_invalid(self, client: TestClient) -> None:
        """Should detect invalid schema."""
        response = client.post(
            "/api/v2/enclosures/validate",
            json={
                "enclosure_schema": {
                    "exterior": {},  # Missing required fields
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["issues"]) > 0

    def test_get_presets(self, client: TestClient) -> None:
        """Should get enclosure presets."""
        response = client.get("/api/v2/enclosures/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert "raspberry-pi-5" in data["presets"]


class TestGenerateEndpoints:
    """Tests for /api/v2/generate endpoints."""

    def test_preview_schema(self, client: TestClient) -> None:
        """Should preview schema without compiling."""
        # Mock the AI provider to avoid actual API calls
        with patch("app.cad_v2.ai.schema_generator.get_ai_provider") as mock_provider:
            mock_provider.return_value.complete = AsyncMock(
                return_value='{"exterior": {"width": {"value": 100}, "depth": {"value": 80}, "height": {"value": 40}}, "walls": {"thickness": {"value": 2.5}}}'
            )
            mock_provider.return_value.is_configured = True

            response = client.post(
                "/api/v2/generate/preview",
                json={"description": "A simple 100x80x40mm box"},
            )

            # The response depends on the mock setup
            assert response.status_code == 200

    def test_compile_schema(self, client: TestClient) -> None:
        """Should compile schema directly."""
        response = client.post(
            "/api/v2/generate/compile",
            json={
                "enclosure_schema": {
                    "exterior": {
                        "width": {"value": 100, "unit": "mm"},
                        "depth": {"value": 80, "unit": "mm"},
                        "height": {"value": 40, "unit": "mm"},
                    },
                    "walls": {
                        "thickness": {"value": 2.5, "unit": "mm"},
                    },
                },
                "export_format": "step",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "body" in data["parts"]

    def test_compile_invalid_schema(self, client: TestClient) -> None:
        """Should reject invalid schema."""
        response = client.post(
            "/api/v2/generate/compile",
            json={
                "enclosure_schema": {
                    "invalid": "schema",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0


class TestV1ToV2Routing:
    """Tests for v1 endpoint routing to v2 pipeline."""

    def test_v1_generate_has_deprecation_headers(self, client: TestClient) -> None:
        """V1 generate endpoint should include deprecation headers."""
        with patch("app.cad_v2.ai.schema_generator.get_ai_provider") as mock_provider:
            mock_provider.return_value.complete = AsyncMock(
                return_value='{"exterior": {"width": {"value": 100}, "depth": {"value": 80}, "height": {"value": 40}}, "walls": {"thickness": {"value": 2.5}}}'
            )
            mock_provider.return_value.is_configured = True

            response = client.post(
                "/api/v1/generate",
                json={"description": "A 100x80x40mm enclosure"},
            )

            # Check deprecation headers are present
            assert response.headers.get("Deprecation") == "true"
            assert "Sunset" in response.headers
            assert "successor-version" in response.headers.get("Link", "")

    def test_v1_generate_routes_to_v2_pipeline(self, client: TestClient) -> None:
        """V1 generate should use v2 pipeline when CAD_V2_AS_DEFAULT is True."""
        # Mock the AI provider for schema generation (not intent parsing)
        # Use a description that triggers high-confidence heuristic parsing
        with patch("app.cad_v2.ai.schema_generator.get_ai_provider") as mock_provider:
            mock_provider.return_value.complete = AsyncMock(
                return_value='{"exterior": {"width": {"value": 100, "unit": "mm"}, "depth": {"value": 80, "unit": "mm"}, "height": {"value": 40, "unit": "mm"}}, "walls": {"thickness": {"value": 2.5, "unit": "mm"}}}'
            )
            mock_provider.return_value.is_configured = True

            # Description with "create" keyword and dimensions triggers high-confidence heuristic
            response = client.post(
                "/api/v1/generate",
                json={
                    "description": "Create an enclosure 100mm x 80mm x 40mm for a Raspberry Pi 5"
                },
            )

            assert response.status_code == 201
            data = response.json()

            # V2 pipeline returns "enclosure" as shape type
            assert data["shape"] == "enclosure"
            # V2 pipeline has high confidence for validated schema
            assert data["confidence"] >= 0.9
            # V2 generates body part
            assert "body" in [p.get("name") for p in data.get("parts", [])]


class TestDownloadsEndpoints:
    """Tests for /api/v2/downloads endpoints."""

    def test_compile_and_download(self, client: TestClient) -> None:
        """Should compile schema and download resulting file."""
        # First, compile a schema
        response = client.post(
            "/api/v2/generate/compile",
            json={
                "enclosure_schema": {
                    "exterior": {
                        "width": {"value": 100, "unit": "mm"},
                        "depth": {"value": 80, "unit": "mm"},
                        "height": {"value": 40, "unit": "mm"},
                    },
                    "walls": {
                        "thickness": {"value": 2.5, "unit": "mm"},
                    },
                },
                "export_format": "step",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Extract job_id from response
        job_id = data["job_id"]
        assert job_id

        # Check download URL is correct
        assert "body" in data["downloads"]
        download_url = data["downloads"]["body"]
        assert job_id in download_url

        # Now download the file
        download_response = client.get(download_url)
        assert download_response.status_code == 200
        assert len(download_response.content) > 0  # File has content

    def test_list_job_files(self, client: TestClient) -> None:
        """Should list files for a job."""
        # First, compile a schema
        response = client.post(
            "/api/v2/generate/compile",
            json={
                "enclosure_schema": {
                    "exterior": {
                        "width": {"value": 100, "unit": "mm"},
                        "depth": {"value": 80, "unit": "mm"},
                        "height": {"value": 40, "unit": "mm"},
                    },
                    "walls": {
                        "thickness": {"value": 2.5, "unit": "mm"},
                    },
                },
            },
        )
        data = response.json()
        job_id = data["job_id"]

        # List files for job
        list_response = client.get(f"/api/v2/downloads/{job_id}")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["job_id"] == job_id
        assert len(list_data["files"]) > 0
        assert any("body.step" in f["name"] for f in list_data["files"])

    def test_download_nonexistent_job(self, client: TestClient) -> None:
        """Should return 404 for nonexistent job."""
        response = client.get("/api/v2/downloads/nonexistent-job-id/file.step")
        assert response.status_code == 404

    def test_download_invalid_job_id(self, client: TestClient) -> None:
        """Should reject path traversal attempts."""
        # Path traversal should fail (either 400 or 404 is acceptable)
        response = client.get("/api/v2/downloads/../../../etc/passwd/file.step")
        assert response.status_code in (400, 404)

    def test_list_nonexistent_job(self, client: TestClient) -> None:
        """Should return 404 for listing nonexistent job."""
        response = client.get("/api/v2/downloads/nonexistent-job-id")
        assert response.status_code == 404
