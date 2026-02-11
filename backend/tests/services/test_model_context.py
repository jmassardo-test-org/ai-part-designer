"""
Tests for model context service.

Tests extraction of model metadata for AI conversations.
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.design import Design
from app.services.model_context import (
    ModelContext,
    extract_model_context,
    get_design_by_id,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def test_design_with_metadata(db_session: AsyncSession, test_user, test_project):
    """Create a test design with full metadata."""
    design = Design(
        id=uuid4(),
        user_id=test_user.id,
        project_id=test_project.id,
        name="Test Box",
        description="A simple box with mounting holes",
        source_type="ai_generated",
        status="ready",
        extra_data={
            "parameters": {
                "length": 100,
                "width": 50,
                "height": 30,
            },
            "dimensions": {
                "x": 100,
                "y": 50,
                "z": 30,
                "unit": "mm",
            },
            "features": [
                {
                    "type": "hole",
                    "description": "mounting hole",
                    "parameters": {"diameter": 5},
                    "location": "corner",
                    "count": 4,
                },
                {
                    "type": "fillet",
                    "description": "rounded edges",
                    "parameters": {"radius": 2},
                    "location": "all_edges",
                    "count": 12,
                },
            ],
            "volume": 150000,
            "surfaceArea": 23000,
            "isPrintable": True,
        },
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)

    yield design

    # Cleanup
    try:
        await db_session.delete(design)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_design_minimal(db_session: AsyncSession, test_user, test_project):
    """Create a test design with minimal metadata."""
    design = Design(
        id=uuid4(),
        user_id=test_user.id,
        project_id=test_project.id,
        name="Minimal Design",
        description=None,
        source_type="imported",
        status="ready",
        extra_data={},
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)

    yield design

    # Cleanup
    try:
        await db_session.delete(design)
        await db_session.commit()
    except Exception:
        pass


# =============================================================================
# extract_model_context Tests
# =============================================================================


async def test_extract_model_context_with_full_metadata(test_design_with_metadata):
    """Test extracting context from a design with complete metadata."""
    context = extract_model_context(test_design_with_metadata)

    assert isinstance(context, ModelContext)
    assert context.design_id == test_design_with_metadata.id
    assert context.name == "Test Box"
    assert context.description == "A simple box with mounting holes"

    # Check dimensions
    assert context.dimensions == {
        "x": 100,
        "y": 50,
        "z": 30,
        "unit": "mm",
    }

    # Check features
    assert len(context.features) == 2
    assert context.features[0]["type"] == "hole"
    assert context.features[0]["count"] == 4
    assert context.features[1]["type"] == "fillet"

    # Check metadata
    assert context.metadata["volume"] == 150000
    assert context.metadata["surfaceArea"] == 23000
    assert context.metadata["isPrintable"] is True


async def test_extract_model_context_with_minimal_metadata(test_design_minimal):
    """Test extracting context from a design with minimal metadata."""
    context = extract_model_context(test_design_minimal)

    assert isinstance(context, ModelContext)
    assert context.design_id == test_design_minimal.id
    assert context.name == "Minimal Design"
    assert context.description is None
    assert context.dimensions == {}
    assert context.features == []
    assert context.metadata == {}


async def test_extract_model_context_dimensions_from_parameters(
    db_session: AsyncSession, test_user, test_project
):
    """Test extracting dimensions from parameters when dimensions not explicitly set."""
    design = Design(
        id=uuid4(),
        user_id=test_user.id,
        project_id=test_project.id,
        name="Parametric Design",
        source_type="template",
        status="ready",
        extra_data={
            "parameters": {
                "length": 200,
                "width": 100,
                "thickness": 5,
                "material": "PLA",  # Non-dimension parameter
            },
        },
    )
    db_session.add(design)
    await db_session.commit()

    context = extract_model_context(design)

    # Should extract dimension-like parameters
    assert "length" in context.dimensions
    assert context.dimensions["length"] == 200
    assert "width" in context.dimensions
    assert context.dimensions["width"] == 100
    assert "thickness" in context.dimensions
    assert context.dimensions["thickness"] == 5
    assert context.dimensions.get("unit") == "mm"
    # Non-dimension parameter should be in parameters, not dimensions
    assert "material" not in context.dimensions

    await db_session.delete(design)
    await db_session.commit()


# =============================================================================
# ModelContext.to_dict Tests
# =============================================================================


async def test_model_context_to_dict(test_design_with_metadata):
    """Test converting ModelContext to dictionary."""
    context = extract_model_context(test_design_with_metadata)
    context_dict = context.to_dict()

    assert isinstance(context_dict, dict)
    assert context_dict["design_id"] == str(test_design_with_metadata.id)
    assert context_dict["name"] == "Test Box"
    assert context_dict["description"] == "A simple box with mounting holes"
    assert "dimensions" in context_dict
    assert "features" in context_dict
    assert "metadata" in context_dict


# =============================================================================
# ModelContext.format_for_ai Tests
# =============================================================================


async def test_model_context_format_for_ai_full(test_design_with_metadata):
    """Test formatting context for AI with full metadata."""
    context = extract_model_context(test_design_with_metadata)
    formatted = context.format_for_ai()

    assert "Current Model: Test Box" in formatted
    assert "Description: A simple box with mounting holes" in formatted
    assert "Dimensions:" in formatted
    assert "x: 100mm" in formatted
    assert "y: 50mm" in formatted
    assert "z: 30mm" in formatted
    assert "Features:" in formatted
    assert "hole:" in formatted
    assert "fillet:" in formatted
    assert "Metadata:" in formatted
    assert "volume: 150000" in formatted
    assert "isPrintable: yes" in formatted


async def test_model_context_format_for_ai_minimal(test_design_minimal):
    """Test formatting context for AI with minimal metadata."""
    context = extract_model_context(test_design_minimal)
    formatted = context.format_for_ai()

    assert "Current Model: Minimal Design" in formatted
    # Should not include sections with no data
    assert "Dimensions:" not in formatted
    assert "Features:" not in formatted


# =============================================================================
# get_design_by_id Tests
# =============================================================================


async def test_get_design_by_id_success(
    db_session: AsyncSession,
    test_design_with_metadata,
    test_user,
):
    """Test retrieving a design by ID."""
    design = await get_design_by_id(
        test_design_with_metadata.id,
        test_user.id,
        db_session,
    )

    assert design is not None
    assert design.id == test_design_with_metadata.id
    assert design.name == "Test Box"


async def test_get_design_by_id_not_found(
    db_session: AsyncSession,
    test_user,
):
    """Test retrieving a non-existent design."""
    fake_id = uuid4()
    design = await get_design_by_id(
        fake_id,
        test_user.id,
        db_session,
    )

    assert design is None


async def test_get_design_by_id_wrong_user(
    db_session: AsyncSession,
    test_design_with_metadata,
    test_user_2,
):
    """Test retrieving a design with wrong user."""
    design = await get_design_by_id(
        test_design_with_metadata.id,
        test_user_2.id,
        db_session,
    )

    assert design is None


async def test_get_design_by_id_soft_deleted(
    db_session: AsyncSession,
    test_design_with_metadata,
    test_user,
):
    """Test that soft-deleted designs are not returned."""
    from datetime import UTC, datetime

    # Soft delete the design
    test_design_with_metadata.deleted_at = datetime.now(UTC)
    await db_session.commit()

    design = await get_design_by_id(
        test_design_with_metadata.id,
        test_user.id,
        db_session,
    )

    assert design is None
