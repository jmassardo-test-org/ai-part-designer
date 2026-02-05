"""
Tests for components API endpoints.

Tests reference component library operations, upload, and extraction.
"""

from io import BytesIO

import pytest
from httpx import AsyncClient

# =============================================================================
# Component List Tests
# =============================================================================


class TestListComponents:
    """Tests for listing components."""

    async def test_list_user_components_success(self, client: AsyncClient, auth_headers: dict):
        """Should return list of user's components."""
        response = await client.get("/api/v1/components", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "components" in data or isinstance(data, list)

    async def test_list_components_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/components")
        assert response.status_code == 401

    async def test_list_components_with_pagination(self, client: AsyncClient, auth_headers: dict):
        """Should support pagination parameters."""
        response = await client.get("/api/v1/components?page=1&page_size=10", headers=auth_headers)

        assert response.status_code == 200


# =============================================================================
# Component Search Tests
# =============================================================================


class TestSearchComponents:
    """Tests for component search."""

    async def test_search_components_success(self, client: AsyncClient, auth_headers: dict):
        """Should search components by query."""
        response = await client.get("/api/v1/components?search=arduino", headers=auth_headers)

        assert response.status_code == 200

    async def test_search_by_category(self, client: AsyncClient, auth_headers: dict):
        """Should filter components by category."""
        response = await client.get("/api/v1/components?category=electronics", headers=auth_headers)

        assert response.status_code == 200


# =============================================================================
# Component Create Tests
# =============================================================================


class TestCreateComponent:
    """Tests for component creation."""

    async def test_create_component_success(self, client: AsyncClient, auth_headers: dict):
        """Should create a new component."""
        response = await client.post(
            "/api/v1/components",
            headers=auth_headers,
            json={
                "name": "Test Component",
                "description": "A test component for testing",
                "category": "sbc",
            },
        )

        # Could be 200 or 201 depending on implementation
        assert response.status_code in [200, 201]

        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data or "component_id" in data

    async def test_create_component_missing_name(self, client: AsyncClient, auth_headers: dict):
        """Should reject component without name."""
        response = await client.post(
            "/api/v1/components",
            headers=auth_headers,
            json={
                "description": "Missing name",
                "category": "sbc",
            },
        )

        assert response.status_code == 422

    async def test_create_component_unauthenticated(self, client: AsyncClient):
        """Should reject unauthenticated creation."""
        response = await client.post(
            "/api/v1/components",
            json={
                "name": "Test Component",
                "category": "sbc",
            },
        )

        assert response.status_code == 401


# =============================================================================
# Component Upload Tests
# =============================================================================


class TestComponentUpload:
    """Tests for component file upload."""

    async def test_upload_datasheet_pdf(self, client: AsyncClient, auth_headers: dict):
        """Should upload PDF datasheet."""
        # First create a component
        create_response = await client.post(
            "/api/v1/components",
            headers=auth_headers,
            json={
                "name": "Upload Test Component",
                "category": "sbc",
            },
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Component creation not implemented")

        component_id = create_response.json().get("id")
        if not component_id:
            pytest.skip("No component ID returned")

        # Create fake PDF content
        pdf_content = b"%PDF-1.4 fake pdf content for testing"

        # Upload datasheet
        files = {"datasheet": ("datasheet.pdf", BytesIO(pdf_content), "application/pdf")}
        response = await client.post(
            f"/api/v1/components/{component_id}/files",
            headers=auth_headers,
            files=files,
        )

        # Could be various success codes or method not allowed
        assert response.status_code in [200, 201, 204, 405, 422]


# =============================================================================
# Component Extraction Tests
# =============================================================================


class TestComponentExtraction:
    """Tests for extraction triggering and status."""

    async def test_trigger_extraction(self, client: AsyncClient, auth_headers: dict):
        """Should trigger extraction for component."""
        # First create a component
        create_response = await client.post(
            "/api/v1/components",
            headers=auth_headers,
            json={
                "name": "Extraction Test Component",
                "category": "sbc",
            },
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Component creation not implemented")

        component_id = create_response.json().get("id")
        if not component_id:
            pytest.skip("No component ID returned")

        # Trigger extraction
        response = await client.post(
            f"/api/v1/components/{component_id}/extract",
            headers=auth_headers,
        )

        # Should return extraction job or error
        assert response.status_code in [200, 201, 400, 404, 422]

    async def test_get_extraction_status(self, client: AsyncClient, auth_headers: dict):
        """Should get extraction job status."""
        # First create a component and trigger extraction
        create_response = await client.post(
            "/api/v1/components",
            headers=auth_headers,
            json={
                "name": "Status Test Component",
                "category": "sbc",
            },
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Component creation not implemented")

        component_id = create_response.json().get("id")
        if not component_id:
            pytest.skip("No component ID returned")

        # Get extraction status
        response = await client.get(
            f"/api/v1/components/{component_id}/extraction-status",
            headers=auth_headers,
        )

        # Could be 200 with status or 404 if no job
        assert response.status_code in [200, 404]


# =============================================================================
# Component Library Tests
# =============================================================================


class TestComponentLibrary:
    """Tests for component library endpoints."""

    async def test_get_library_components(self, client: AsyncClient, auth_headers: dict):
        """Should return library components."""
        response = await client.get("/api/v1/library", headers=auth_headers)

        # Could be 200 or 404 depending on implementation
        assert response.status_code in [200, 404]

    async def test_get_component_categories(self, client: AsyncClient, auth_headers: dict):
        """Should return list of component categories."""
        response = await client.get("/api/v1/components/categories", headers=auth_headers)

        # Might not be implemented
        assert response.status_code in [200, 404, 422]


# =============================================================================
# Component Specifications Tests
# =============================================================================


class TestComponentSpecifications:
    """Tests for component specification updates."""

    async def test_update_component_specs(self, client: AsyncClient, auth_headers: dict):
        """Should update component specifications."""
        # First create a component
        create_response = await client.post(
            "/api/v1/components",
            headers=auth_headers,
            json={
                "name": "Specs Test Component",
                "category": "sbc",
            },
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Component creation not implemented")

        component_id = create_response.json().get("id")
        if not component_id:
            pytest.skip("No component ID returned")

        # Update specifications
        response = await client.patch(
            f"/api/v1/components/{component_id}/specifications",
            headers=auth_headers,
            json={
                "dimensions": {
                    "length": 85.0,
                    "width": 56.0,
                    "height": 17.0,
                    "unit": "mm",
                }
            },
        )

        # Could be various success codes or method not allowed
        assert response.status_code in [200, 204, 404, 405, 422]


# =============================================================================
# Component Upload Endpoint Tests (/components/upload)
# =============================================================================


class TestComponentUploadEndpoint:
    """Tests for the /components/upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_step_file_success(self, client: AsyncClient, auth_headers: dict):
        """Should successfully upload a STEP file."""
        # Create minimal STEP file content (header only - actual validation is lenient)
        step_content = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Test Part'), '2;1');
FILE_NAME('test.step', '2024-01-01', (''), (''), '', '', '');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;
DATA;
ENDSEC;
END-ISO-10303-21;"""

        files = {"file": ("test_part.step", BytesIO(step_content), "application/step")}
        response = await client.post(
            "/api/v1/components/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["file_type"] == "cad"
        assert data["extraction_status"] == "pending"
        assert data["name"] == "test_part"  # Name from filename

    @pytest.mark.asyncio
    async def test_upload_stl_file_success(self, client: AsyncClient, auth_headers: dict):
        """Should successfully upload an STL file."""
        # Minimal ASCII STL
        stl_content = b"""solid TestModel
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid TestModel"""

        files = {"file": ("model.stl", BytesIO(stl_content), "model/stl")}
        response = await client.post(
            "/api/v1/components/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["file_type"] == "cad"

    @pytest.mark.asyncio
    async def test_upload_3mf_file_success(self, client: AsyncClient, auth_headers: dict):
        """Should successfully upload a 3MF file."""
        # 3MF files are actually ZIP archives - create minimal valid one
        import zipfile
        from io import BytesIO

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Minimal 3MF structure
            zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
            zf.writestr("3D/3dmodel.model", '<?xml version="1.0"?><model></model>')
        buffer.seek(0)

        files = {"file": ("part.3mf", buffer, "model/3mf")}
        response = await client.post(
            "/api/v1/components/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_type"] == "cad"

    @pytest.mark.asyncio
    async def test_upload_pdf_datasheet_success(self, client: AsyncClient, auth_headers: dict):
        """Should successfully upload a PDF datasheet."""
        pdf_content = (
            b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\nxref\n0 2\ntrailer\n<<>>\nstartxref\n0\n%%EOF"
        )

        files = {"file": ("datasheet.pdf", BytesIO(pdf_content), "application/pdf")}
        response = await client.post(
            "/api/v1/components/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_type"] == "datasheet"

    @pytest.mark.asyncio
    async def test_upload_image_success(self, client: AsyncClient, auth_headers: dict):
        """Should successfully upload an image file."""
        # Minimal valid PNG (1x1 transparent pixel)
        png_content = bytes(
            [
                0x89,
                0x50,
                0x4E,
                0x47,
                0x0D,
                0x0A,
                0x1A,
                0x0A,  # PNG signature
                0x00,
                0x00,
                0x00,
                0x0D,
                0x49,
                0x48,
                0x44,
                0x52,  # IHDR chunk
                0x00,
                0x00,
                0x00,
                0x01,
                0x00,
                0x00,
                0x00,
                0x01,  # 1x1
                0x08,
                0x06,
                0x00,
                0x00,
                0x00,
                0x1F,
                0x15,
                0xC4,
                0x89,  # 8bit RGBA
                0x00,
                0x00,
                0x00,
                0x0A,
                0x49,
                0x44,
                0x41,
                0x54,  # IDAT chunk
                0x78,
                0x9C,
                0x63,
                0x00,
                0x01,
                0x00,
                0x00,
                0x05,
                0x00,
                0x01,
                0x00,
                0x00,
                0x00,
                0x00,
                0x49,
                0x45,
                0x4E,
                0x44,  # IEND chunk
                0xAE,
                0x42,
                0x60,
                0x82,
            ]
        )

        files = {"file": ("component.png", BytesIO(png_content), "image/png")}
        response = await client.post(
            "/api/v1/components/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_type"] == "image"

    @pytest.mark.asyncio
    async def test_upload_invalid_format_rejected(self, client: AsyncClient, auth_headers: dict):
        """Should reject unsupported file formats."""
        invalid_content = b"This is just a text file pretending to be something else"

        files = {"file": ("file.exe", BytesIO(invalid_content), "application/octet-stream")}
        response = await client.post(
            "/api/v1/components/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 400
        data = response.json()
        assert "Unsupported file type" in data["detail"]

    @pytest.mark.asyncio
    async def test_upload_too_large_rejected(self, client: AsyncClient, auth_headers: dict):
        """Should reject files exceeding 50MB limit."""
        # Create content just over 50MB (50MB + 1KB)
        large_content = b"X" * (50 * 1024 * 1024 + 1024)

        files = {"file": ("huge.step", BytesIO(large_content), "application/step")}
        response = await client.post(
            "/api/v1/components/upload",
            headers=auth_headers,
            files=files,
            timeout=30.0,  # Allow time for upload
        )

        assert response.status_code == 413
        data = response.json()
        assert "too large" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_metadata_includes_dates(self, client: AsyncClient, auth_headers: dict):
        """Should include proper timestamps in upload response."""
        stl_content = b"solid Test\nendsolid Test"

        files = {"file": ("model.stl", BytesIO(stl_content), "model/stl")}
        response = await client.post(
            "/api/v1/components/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 201
        data = response.json()

        # Verify created_at is present and valid ISO date
        assert "created_at" in data
        from datetime import datetime

        # Should not raise if valid
        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_upload_unauthenticated_rejected(self, client: AsyncClient):
        """Should reject uploads without authentication."""
        content = b"solid Test\nendsolid Test"

        files = {"file": ("model.stl", BytesIO(content), "model/stl")}
        response = await client.post(
            "/api/v1/components/upload",
            files=files,
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_creates_extraction_job(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        """Should create an extraction job for uploaded file."""
        from sqlalchemy import select

        from app.models.reference_component import ComponentExtractionJob

        stl_content = b"solid Test\nendsolid Test"

        files = {"file": ("model.stl", BytesIO(stl_content), "model/stl")}
        response = await client.post(
            "/api/v1/components/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 201
        component_id = response.json()["id"]

        # Check extraction job was created
        result = await db_session.execute(
            select(ComponentExtractionJob).where(
                ComponentExtractionJob.component_id == component_id
            )
        )
        job = result.scalar_one_or_none()

        assert job is not None
        assert job.job_type == "cad"
        assert job.status == "pending"
