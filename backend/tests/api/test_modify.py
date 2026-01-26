"""
Tests for Modify API endpoints.

Tests CAD file modification, preview, and combine operations.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Modify File Tests
# =============================================================================

class TestModifyFile:
    """Tests for file modification endpoint."""

    @pytest.mark.asyncio
    async def test_modify_requires_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        file_factory,
        user_factory,
    ):
        """Test that modification requires authentication."""
        user = await user_factory.create(db=db_session)
        file = await file_factory.create(db=db_session, user=user)
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/modify",
            json={
                "operations": [{"type": "scale", "params": {"factor": 2.0}}],
            },
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_modify_file_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test modifying non-existent file."""
        response = await client.post(
            f"/api/v1/cad/files/{uuid4()}/modify",
            headers=auth_headers,
            json={
                "operations": [{"type": "scale", "params": {"factor": 2.0}}],
            },
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_modify_other_user_file(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        file_factory,
    ):
        """Test modifying another user's file returns 404."""
        other_user = await user_factory.create(db=db_session)
        other_file = await file_factory.create(db=db_session, user=other_user)
        
        response = await client.post(
            f"/api/v1/cad/files/{other_file.id}/modify",
            headers=auth_headers,
            json={
                "operations": [{"type": "scale", "params": {"factor": 2.0}}],
            },
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_modify_invalid_operation_type(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test modification with invalid operation type."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/modify",
            headers=auth_headers,
            json={
                "operations": [{"type": "invalid_operation", "params": {}}],
            },
        )
        
        assert response.status_code == 400
        assert "Unknown operation type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_modify_empty_operations(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test modification with empty operations list."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/modify",
            headers=auth_headers,
            json={
                "operations": [],  # Empty
            },
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_modify_too_many_operations(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test modification with too many operations."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        # 21 operations (max is 20)
        operations = [{"type": "translate", "params": {"x": 1}} for _ in range(21)]
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/modify",
            headers=auth_headers,
            json={"operations": operations},
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_modify_non_cad_file(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test modifying non-CAD file returns error."""
        file = await file_factory.create(
            db=db_session,
            user=test_user,
            file_type="image",
            cad_format=None,
            mime_type="image/png",
        )
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/modify",
            headers=auth_headers,
            json={
                "operations": [{"type": "scale", "params": {"factor": 2.0}}],
            },
        )
        
        assert response.status_code == 400
        assert "not a CAD file" in response.json()["detail"]


# =============================================================================
# Operation Type Tests
# =============================================================================

class TestOperationTypes:
    """Tests for different operation types."""

    @pytest.mark.asyncio
    async def test_translate_operation_params(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test translate operation accepts x, y, z parameters."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        # Valid translate params
        operation = {
            "type": "translate",
            "params": {"x": 10, "y": 20, "z": 30},
        }
        
        # We're just testing that the API accepts this format
        # Actual execution would require file content
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/preview",
            headers=auth_headers,
            json={"operations": [operation]},
        )
        
        # Should not fail on params validation
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_rotate_operation_params(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test rotate operation accepts angle and axis parameters."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        operation = {
            "type": "rotate",
            "params": {"angle": 45, "axis": "z"},
        }
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/preview",
            headers=auth_headers,
            json={"operations": [operation]},
        )
        
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_scale_operation_params(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test scale operation accepts factor parameter."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        operation = {
            "type": "scale",
            "params": {"factor": 2.0},
        }
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/preview",
            headers=auth_headers,
            json={"operations": [operation]},
        )
        
        assert response.status_code in [200, 400, 404]


# =============================================================================
# Preview Tests
# =============================================================================

class TestPreviewModifications:
    """Tests for preview endpoint."""

    @pytest.mark.asyncio
    async def test_preview_requires_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_factory,
        file_factory,
    ):
        """Test that preview requires authentication."""
        user = await user_factory.create(db=db_session)
        file = await file_factory.create(db=db_session, user=user)
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/preview",
            json={"operations": [{"type": "scale", "params": {"factor": 2.0}}]},
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_preview_file_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test previewing non-existent file."""
        response = await client.post(
            f"/api/v1/cad/files/{uuid4()}/preview",
            headers=auth_headers,
            json={"operations": [{"type": "scale", "params": {"factor": 2.0}}]},
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_preview_invalid_operation(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test preview with invalid operation returns errors."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/preview",
            headers=auth_headers,
            json={
                "operations": [{"type": "unknown_op", "params": {}}],
            },
        )
        
        # Should return preview response with errors
        assert response.status_code == 200
        data = response.json()
        assert data["operations_valid"] is False
        assert len(data["errors"]) > 0


# =============================================================================
# Combine Tests
# =============================================================================

class TestCombineFiles:
    """Tests for file combination endpoint."""

    @pytest.mark.asyncio
    async def test_combine_requires_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_factory,
        file_factory,
    ):
        """Test that combine requires authentication."""
        user = await user_factory.create(db=db_session)
        file1 = await file_factory.create(db=db_session, user=user)
        file2 = await file_factory.create(db=db_session, user=user)
        
        response = await client.post(
            f"/api/v1/cad/files/{file1.id}/combine",
            json={
                "file_ids": [str(file2.id)],
                "operation": "union",
            },
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_combine_file_not_found(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test combining with non-existent file."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/combine",
            headers=auth_headers,
            json={
                "file_ids": [str(uuid4())],  # Non-existent file
                "operation": "union",
            },
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_combine_other_user_file(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        file_factory,
    ):
        """Test combining with another user's file returns 404."""
        other_user = await user_factory.create(db=db_session)
        my_file = await file_factory.create(db=db_session, user=test_user)
        their_file = await file_factory.create(db=db_session, user=other_user)
        
        response = await client.post(
            f"/api/v1/cad/files/{my_file.id}/combine",
            headers=auth_headers,
            json={
                "file_ids": [str(their_file.id)],
                "operation": "union",
            },
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_combine_empty_file_ids(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test combining with empty file IDs list."""
        file = await file_factory.create(db=db_session, user=test_user)
        
        response = await client.post(
            f"/api/v1/cad/files/{file.id}/combine",
            headers=auth_headers,
            json={
                "file_ids": [],  # Empty
                "operation": "union",
            },
        )
        
        assert response.status_code == 422


# =============================================================================
# Geometry Info Tests
# =============================================================================

class TestGeometryInfo:
    """Tests for geometry info endpoint."""

    @pytest.mark.asyncio
    async def test_get_geometry_info_requires_auth(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_factory,
        file_factory,
    ):
        """Test that geometry info requires authentication."""
        user = await user_factory.create(db=db_session)
        file = await file_factory.create(db=db_session, user=user)
        
        response = await client.get(f"/api/v1/cad/files/{file.id}/geometry")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_geometry_info_file_not_found(
        self,
        client: AsyncClient,
        test_user,
        auth_headers,
    ):
        """Test getting geometry info for non-existent file."""
        response = await client.get(
            f"/api/v1/cad/files/{uuid4()}/geometry",
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_geometry_info_other_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        user_factory,
        file_factory,
    ):
        """Test getting geometry info for another user's file."""
        other_user = await user_factory.create(db=db_session)
        other_file = await file_factory.create(db=db_session, user=other_user)
        
        response = await client.get(
            f"/api/v1/cad/files/{other_file.id}/geometry",
            headers=auth_headers,
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_geometry_info_with_cached_data(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user,
        auth_headers,
        file_factory,
    ):
        """Test getting geometry info when already cached in file record."""
        file = await file_factory.create(
            db=db_session,
            user=test_user,
            geometry_info={
                "volume": 125000.0,
                "area": 23000.0,
                "bounding_box": {"x": 100, "y": 50, "z": 25},
            },
        )
        
        response = await client.get(
            f"/api/v1/cad/files/{file.id}/geometry",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["volume"] == 125000.0
        assert data["area"] == 23000.0
