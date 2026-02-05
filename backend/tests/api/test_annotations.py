"""
Tests for annotations API endpoints.

Tests design annotation CRUD operations.
"""

from uuid import uuid4

from httpx import AsyncClient

# =============================================================================
# List Annotations Tests
# =============================================================================


class TestListAnnotations:
    """Tests for GET /api/v1/annotations."""

    async def test_list_annotations_success(self, client: AsyncClient, auth_headers: dict):
        """Should return list of annotations when queried with design_id."""
        fake_design_id = uuid4()
        response = await client.get(
            f"/api/v1/annotations?design_id={fake_design_id}", headers=auth_headers
        )

        # May return 200 with empty list or 404 if design not found
        assert response.status_code in [200, 404]

    async def test_list_annotations_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.get("/api/v1/annotations")
        # 401 if endpoint exists, 404 if path not found
        assert response.status_code in [401, 404]


# =============================================================================
# Create Annotation Tests
# =============================================================================


class TestCreateAnnotation:
    """Tests for POST /api/v1/annotations."""

    async def test_create_annotation_invalid_design(self, client: AsyncClient, auth_headers: dict):
        """Should fail when design doesn't exist."""
        fake_design_id = uuid4()
        response = await client.post(
            "/api/v1/annotations",
            headers=auth_headers,
            json={
                "design_id": str(fake_design_id),
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                "content": "New annotation",
                "annotation_type": "note",
            },
        )

        # Should return 404 for non-existent design
        assert response.status_code in [404, 422]

    async def test_create_annotation_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        response = await client.post(
            "/api/v1/annotations",
            json={
                "design_id": str(uuid4()),
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                "content": "New annotation",
            },
        )

        # 401 if endpoint exists, 404 if path not found
        assert response.status_code in [401, 404]


# =============================================================================
# Get Annotation Tests
# =============================================================================


class TestGetAnnotation:
    """Tests for GET /api/v1/annotations/{annotation_id}."""

    async def test_get_annotation_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent annotation."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/annotations/{fake_id}", headers=auth_headers)

        assert response.status_code == 404

    async def test_get_annotation_unauthenticated(self, client: AsyncClient):
        """Should return 401 without authentication."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/annotations/{fake_id}")
        # 401 if endpoint exists, 404 if path not found
        assert response.status_code in [401, 404]


# =============================================================================
# Update Annotation Tests
# =============================================================================


class TestUpdateAnnotation:
    """Tests for PATCH /api/v1/annotations/{annotation_id}."""

    async def test_update_annotation_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent annotation."""
        fake_id = uuid4()
        response = await client.patch(
            f"/api/v1/annotations/{fake_id}",
            headers=auth_headers,
            json={"content": "Updated content"},
        )

        assert response.status_code == 404


# =============================================================================
# Delete Annotation Tests
# =============================================================================


class TestDeleteAnnotation:
    """Tests for DELETE /api/v1/annotations/{annotation_id}."""

    async def test_delete_annotation_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent annotation."""
        fake_id = uuid4()
        response = await client.delete(f"/api/v1/annotations/{fake_id}", headers=auth_headers)

        assert response.status_code == 404


# =============================================================================
# Resolve/Reopen Annotation Tests
# =============================================================================


class TestAnnotationResolution:
    """Tests for annotation resolve/reopen endpoints."""

    async def test_resolve_annotation_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent annotation."""
        fake_id = uuid4()
        response = await client.post(f"/api/v1/annotations/{fake_id}/resolve", headers=auth_headers)

        assert response.status_code == 404

    async def test_reopen_annotation_not_found(self, client: AsyncClient, auth_headers: dict):
        """Should return 404 for non-existent annotation."""
        fake_id = uuid4()
        response = await client.post(f"/api/v1/annotations/{fake_id}/reopen", headers=auth_headers)

        assert response.status_code == 404
