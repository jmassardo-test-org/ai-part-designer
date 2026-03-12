"""
Tests for admin panel Epic 10 user stories:
- US-10.10: Content Management (FAQs, Docs, Help)
- US-10.15: Assemblies & BOM Management
- US-10.16: Conversations & AI Interactions
- US-10.17: Trash & Data Retention Management

Security review checklist:
- All endpoints protected by require_admin() dependency
- User inputs validated via Pydantic schemas
- Rate limiting handled at middleware level
- Security events logged via SecurityAuditService where applicable
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assembly import Assembly, AssemblyComponent, BOMItem, Vendor
from app.models.content import ContentCategory, ContentItem, ContentStatus, ContentType
from app.models.conversation import Conversation, ConversationMessage
from app.models.design import Design
from app.models.file import File as FileModel
from app.models.project import Project
from app.models.user import User
from tests.factories import (
    ConversationFactory,
    Counter,
    DesignFactory,
    ProjectFactory,
    UserFactory,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_counters() -> None:
    """Reset factory counters before each test."""
    Counter.reset()


async def _create_content_item(
    db: AsyncSession,
    *,
    content_type: str = ContentType.FAQ,
    title: str = "Test FAQ",
    slug: str | None = None,
    body: str = "Test body",
    category: str | None = "general",
    status: str = ContentStatus.DRAFT,
    created_by: None = None,
) -> ContentItem:
    """Helper to create a content item in the database.

    Args:
        db: Database session.
        content_type: FAQ or ARTICLE.
        title: Item title.
        slug: URL slug (auto-generated if None).
        body: Item body text.
        category: Category name.
        status: Publication status.
        created_by: Creator user ID.

    Returns:
        The created ContentItem.
    """
    item = ContentItem(
        id=uuid4(),
        content_type=content_type,
        title=title,
        slug=slug or f"test-{content_type}-{uuid4().hex[:8]}",
        body=body,
        category=category,
        status=status,
        created_by=created_by,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _create_vendor(
    db: AsyncSession,
    *,
    name: str | None = None,
    display_name: str | None = None,
) -> Vendor:
    """Helper to create a vendor in the database.

    Args:
        db: Database session.
        name: Vendor name (auto-generated if None).
        display_name: Display name (auto-generated if None).

    Returns:
        The created Vendor.
    """
    uid = uuid4().hex[:8]
    vendor = Vendor(
        id=uuid4(),
        name=name or f"vendor-{uid}",
        display_name=display_name or f"Vendor {uid}",
        website="https://example.com",
        categories=["fasteners"],
        is_active=True,
    )
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return vendor


async def _create_assembly(
    db: AsyncSession,
    user: User,
    project: Project,
    *,
    name: str = "Test Assembly",
    assembly_status: str = "draft",
) -> Assembly:
    """Helper to create an assembly in the database.

    Args:
        db: Database session.
        user: Owner user.
        project: Parent project.
        name: Assembly name.
        assembly_status: Assembly status string.

    Returns:
        The created Assembly.
    """
    assembly = Assembly(
        id=uuid4(),
        user_id=user.id,
        project_id=project.id,
        name=name,
        status=assembly_status,
    )
    db.add(assembly)
    await db.commit()
    await db.refresh(assembly)
    return assembly


# =============================================================================
# US-10.10: Content Management Tests
# =============================================================================


class TestContentFAQEndpoints:
    """Tests for FAQ content management endpoints."""

    async def test_list_faqs_requires_admin(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Non-admin users cannot list FAQs."""
        response = await client.get("/api/v1/admin/content/faqs", headers=auth_headers)
        assert response.status_code == 403

    async def test_list_faqs_empty(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """List FAQs returns empty when none exist."""
        response = await client.get("/api/v1/admin/content/faqs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_faqs_with_items(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """List FAQs returns existing FAQ items."""
        await _create_content_item(db_session, title="FAQ 1")
        await _create_content_item(db_session, title="FAQ 2")

        response = await client.get("/api/v1/admin/content/faqs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_faqs_filter_by_category(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Filter FAQs by category."""
        await _create_content_item(db_session, title="FAQ Cat A", category="catA")
        await _create_content_item(db_session, title="FAQ Cat B", category="catB")

        response = await client.get(
            "/api/v1/admin/content/faqs?category=catA", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "catA"

    async def test_list_faqs_filter_by_status(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Filter FAQs by publication status."""
        await _create_content_item(db_session, status=ContentStatus.PUBLISHED)
        await _create_content_item(db_session, status=ContentStatus.DRAFT)

        response = await client.get(
            "/api/v1/admin/content/faqs?status=published", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    async def test_list_faqs_search(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Search FAQs by title text."""
        await _create_content_item(db_session, title="How to reset password")
        await _create_content_item(db_session, title="Pricing info")

        response = await client.get(
            "/api/v1/admin/content/faqs?search=reset", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    async def test_create_faq(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Create a new FAQ item."""
        response = await client.post(
            "/api/v1/admin/content/faqs",
            headers=admin_headers,
            json={
                "title": "New FAQ Item",
                "body": "This is the FAQ body.",
                "category": "general",
                "status": "draft",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New FAQ Item"
        assert data["content_type"] == "faq"
        assert data["status"] == "draft"

    async def test_create_faq_missing_title_fails(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Creating a FAQ without title should fail validation."""
        response = await client.post(
            "/api/v1/admin/content/faqs",
            headers=admin_headers,
            json={"body": "No title"},
        )
        assert response.status_code == 422

    async def test_update_faq(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Update an existing FAQ item."""
        item = await _create_content_item(db_session, title="Original Title")

        response = await client.patch(
            f"/api/v1/admin/content/faqs/{item.id}",
            headers=admin_headers,
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    async def test_update_faq_not_found(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Updating a non-existent FAQ returns 404."""
        response = await client.patch(
            f"/api/v1/admin/content/faqs/{uuid4()}",
            headers=admin_headers,
            json={"title": "Not Found"},
        )
        assert response.status_code == 404

    async def test_delete_faq(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Soft-delete a FAQ item."""
        item = await _create_content_item(db_session, title="To Delete")

        response = await client.delete(
            f"/api/v1/admin/content/faqs/{item.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200

        # Verify soft-deleted
        result = await db_session.execute(
            select(ContentItem).where(ContentItem.id == item.id)
        )
        deleted = result.scalar_one()
        assert deleted.deleted_at is not None

    async def test_delete_faq_not_found(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Deleting a non-existent FAQ returns 404."""
        response = await client.delete(
            f"/api/v1/admin/content/faqs/{uuid4()}",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_publish_faq(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Publish a FAQ item sets status and published_at."""
        item = await _create_content_item(db_session, status=ContentStatus.DRAFT)

        response = await client.post(
            f"/api/v1/admin/content/faqs/{item.id}/publish",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None

    async def test_publish_faq_not_found(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Publishing a non-existent FAQ returns 404."""
        response = await client.post(
            f"/api/v1/admin/content/faqs/{uuid4()}/publish",
            headers=admin_headers,
        )
        assert response.status_code == 404


class TestContentArticleEndpoints:
    """Tests for article content management endpoints."""

    async def test_list_articles_empty(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """List articles returns empty when none exist."""
        response = await client.get(
            "/api/v1/admin/content/articles", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_create_article(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Create a new article content item."""
        response = await client.post(
            "/api/v1/admin/content/articles",
            headers=admin_headers,
            json={
                "title": "Getting Started Guide",
                "body": "This guide walks you through...",
                "category": "tutorials",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content_type"] == "article"
        assert data["title"] == "Getting Started Guide"

    async def test_update_article(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Update an existing article."""
        item = await _create_content_item(
            db_session, content_type=ContentType.ARTICLE, title="Old Article"
        )

        response = await client.patch(
            f"/api/v1/admin/content/articles/{item.id}",
            headers=admin_headers,
            json={"title": "Updated Article"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Article"

    async def test_update_article_not_found(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Updating a non-existent article returns 404."""
        response = await client.patch(
            f"/api/v1/admin/content/articles/{uuid4()}",
            headers=admin_headers,
            json={"title": "Missing"},
        )
        assert response.status_code == 404

    async def test_delete_article(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Soft-delete an article."""
        item = await _create_content_item(
            db_session, content_type=ContentType.ARTICLE, title="Delete Me"
        )

        response = await client.delete(
            f"/api/v1/admin/content/articles/{item.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200

    async def test_publish_article(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Publish an article sets status and published_at."""
        item = await _create_content_item(
            db_session, content_type=ContentType.ARTICLE, status=ContentStatus.DRAFT
        )

        response = await client.post(
            f"/api/v1/admin/content/articles/{item.id}/publish",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None


class TestContentCategoryEndpoints:
    """Tests for content category management endpoints."""

    async def test_list_content_categories_empty(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """List categories returns empty list when none exist."""
        response = await client.get(
            "/api/v1/admin/content/categories", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_content_category(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Create a new content category."""
        response = await client.post(
            "/api/v1/admin/content/categories",
            headers=admin_headers,
            json={"name": "Tutorials", "slug": "tutorials"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Tutorials"
        assert data["slug"] == "tutorials"

    async def test_create_category_duplicate_slug_fails(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Creating a category with duplicate slug returns 409."""
        cat = ContentCategory(
            id=uuid4(), name="Existing", slug="existing", display_order=0
        )
        db_session.add(cat)
        await db_session.commit()

        response = await client.post(
            "/api/v1/admin/content/categories",
            headers=admin_headers,
            json={"name": "Another", "slug": "existing"},
        )
        assert response.status_code == 409


class TestContentReorderAndAnalytics:
    """Tests for content reordering and analytics endpoints."""

    async def test_reorder_content(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Reorder content items by updating display_order."""
        item1 = await _create_content_item(db_session, title="Item 1")
        item2 = await _create_content_item(db_session, title="Item 2")

        response = await client.patch(
            "/api/v1/admin/content/reorder",
            headers=admin_headers,
            json={
                "item_orders": [
                    {"id": str(item1.id), "display_order": 10},
                    {"id": str(item2.id), "display_order": 20},
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 2

    async def test_content_analytics(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Get content analytics returns valid data."""
        await _create_content_item(
            db_session, status=ContentStatus.PUBLISHED, title="Published FAQ"
        )
        await _create_content_item(
            db_session,
            content_type=ContentType.ARTICLE,
            status=ContentStatus.DRAFT,
            title="Draft Article",
        )

        response = await client.get(
            "/api/v1/admin/content/analytics", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_faqs" in data
        assert "total_articles" in data
        assert "popular_items" in data
        assert "categories_breakdown" in data


# =============================================================================
# US-10.15: Assemblies & BOM Management Tests
# =============================================================================


class TestAssemblyEndpoints:
    """Tests for assembly management endpoints."""

    async def test_list_assemblies_requires_admin(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Non-admin users cannot list assemblies."""
        response = await client.get(
            "/api/v1/admin/assemblies", headers=auth_headers
        )
        assert response.status_code == 403

    async def test_list_assemblies_empty(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """List assemblies returns empty when none exist."""
        response = await client.get(
            "/api/v1/admin/assemblies", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_list_assemblies_with_items(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """List assemblies returns existing items."""
        project = await ProjectFactory.create(db_session, user=test_user)
        await _create_assembly(db_session, test_user, project, name="Assy 1")
        await _create_assembly(db_session, test_user, project, name="Assy 2")

        response = await client.get(
            "/api/v1/admin/assemblies", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_assemblies_filter_by_search(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Filter assemblies by search term."""
        project = await ProjectFactory.create(db_session, user=test_user)
        await _create_assembly(db_session, test_user, project, name="Robot Arm")
        await _create_assembly(db_session, test_user, project, name="Motor Mount")

        response = await client.get(
            "/api/v1/admin/assemblies?search=Robot", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    async def test_assembly_stats(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Get assembly statistics returns valid data."""
        response = await client.get(
            "/api/v1/admin/assemblies/stats", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_assemblies" in data
        assert "avg_components_per_assembly" in data
        assert "assemblies_by_status" in data


class TestVendorEndpoints:
    """Tests for vendor management endpoints."""

    async def test_list_vendors_empty(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """List vendors returns empty when none exist."""
        response = await client.get(
            "/api/v1/admin/vendors", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_vendor(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Create a new vendor."""
        response = await client.post(
            "/api/v1/admin/vendors",
            headers=admin_headers,
            json={
                "name": "mcmaster-carr",
                "display_name": "McMaster-Carr",
                "website": "https://mcmaster.com",
                "categories": ["fasteners", "mechanical"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "mcmaster-carr"
        assert data["is_active"] is True

    async def test_create_vendor_duplicate_name_fails(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Creating vendor with duplicate name returns 409."""
        await _create_vendor(db_session, name="dup-vendor")

        response = await client.post(
            "/api/v1/admin/vendors",
            headers=admin_headers,
            json={"name": "dup-vendor", "display_name": "Dup Vendor"},
        )
        assert response.status_code == 409

    async def test_update_vendor(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Update vendor details."""
        vendor = await _create_vendor(db_session)

        response = await client.patch(
            f"/api/v1/admin/vendors/{vendor.id}",
            headers=admin_headers,
            json={"display_name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Updated Name"

    async def test_update_vendor_not_found(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Updating a non-existent vendor returns 404."""
        response = await client.patch(
            f"/api/v1/admin/vendors/{uuid4()}",
            headers=admin_headers,
            json={"display_name": "Missing"},
        )
        assert response.status_code == 404

    async def test_deactivate_vendor(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Soft-delete a vendor."""
        vendor = await _create_vendor(db_session)

        response = await client.delete(
            f"/api/v1/admin/vendors/{vendor.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200

        # Verify soft-deleted
        result = await db_session.execute(
            select(Vendor).where(Vendor.id == vendor.id)
        )
        deactivated = result.scalar_one()
        assert deactivated.deleted_at is not None
        assert deactivated.is_active is False

    async def test_vendor_analytics(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Get vendor analytics returns valid data."""
        response = await client.get(
            "/api/v1/admin/vendors/analytics", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_vendors" in data
        assert "active_vendors" in data
        assert "most_used_vendors" in data


class TestBOMEndpoints:
    """Tests for BOM management endpoints."""

    async def test_bulk_price_update_empty_list(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Bulk price update with empty list returns success."""
        response = await client.post(
            "/api/v1/admin/components/bulk-price-update",
            headers=admin_headers,
            json={"updates": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 0

    async def test_bulk_price_update_nonexistent_component(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Bulk price update with non-existent component adds it to failed list."""
        fake_id = str(uuid4())
        response = await client.post(
            "/api/v1/admin/components/bulk-price-update",
            headers=admin_headers,
            json={"updates": [{"component_id": fake_id, "new_price": 9.99}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 0
        assert fake_id in data["failed"]

    async def test_bom_audit_queue(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Get BOM audit queue returns list."""
        response = await client.get(
            "/api/v1/admin/bom/audit-queue", headers=admin_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# =============================================================================
# US-10.16: Conversations & AI Interactions Tests
# =============================================================================


class TestConversationEndpoints:
    """Tests for conversation management endpoints."""

    async def test_conversation_stats_requires_admin(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Non-admin users cannot access conversation stats."""
        response = await client.get(
            "/api/v1/admin/conversations/stats", headers=auth_headers
        )
        assert response.status_code == 403

    async def test_conversation_stats(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Get conversation statistics returns valid structure."""
        response = await client.get(
            "/api/v1/admin/conversations/stats", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_conversations" in data
        assert "avg_messages_per_conversation" in data
        assert "conversations_by_status" in data
        assert "active_today" in data
        assert "total_messages" in data

    async def test_conversation_stats_with_data(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Conversation stats reflect existing conversations."""
        user = await UserFactory.create(db_session)
        await ConversationFactory.create(db_session, user=user, status="completed")
        await ConversationFactory.create(db_session, user=user, status="active")

        response = await client.get(
            "/api/v1/admin/conversations/stats", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_conversations"] >= 2

    async def test_flagged_conversations(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Get flagged conversations returns paginated response."""
        response = await client.get(
            "/api/v1/admin/conversations/flagged", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_flagged_conversations_with_failed(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Flagged conversations include failed conversations."""
        user = await UserFactory.create(db_session)
        await ConversationFactory.create(db_session, user=user, status="failed")

        response = await client.get(
            "/api/v1/admin/conversations/flagged", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_conversation_detail(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Get conversation detail returns full conversation with messages."""
        user = await UserFactory.create(db_session)
        conv = await ConversationFactory.create(db_session, user=user)

        response = await client.get(
            f"/api/v1/admin/conversations/{conv.id}", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(conv.id)
        assert "messages" in data

    async def test_conversation_detail_not_found(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Get conversation detail for non-existent ID returns 404."""
        response = await client.get(
            f"/api/v1/admin/conversations/{uuid4()}", headers=admin_headers
        )
        assert response.status_code == 404

    async def test_quality_metrics(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Get quality metrics returns valid structure."""
        response = await client.get(
            "/api/v1/admin/conversations/quality-metrics", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_conversations" in data
        assert "completion_rate" in data
        assert "avg_messages_to_completion" in data

    async def test_export_conversations(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Export conversations returns CSV response."""
        response = await client.get(
            "/api/v1/admin/conversations/export", headers=admin_headers
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    async def test_export_conversations_with_filters(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Export conversations accepts date and status filters."""
        response = await client.get(
            "/api/v1/admin/conversations/export?status=completed",
            headers=admin_headers,
        )
        assert response.status_code == 200


# =============================================================================
# US-10.17: Trash & Data Retention Management Tests
# =============================================================================


class TestTrashEndpoints:
    """Tests for trash and data retention management endpoints."""

    async def test_trash_stats_requires_admin(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Non-admin users cannot access trash stats."""
        response = await client.get(
            "/api/v1/admin/trash/stats", headers=auth_headers
        )
        assert response.status_code == 403

    async def test_trash_stats_empty(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Trash stats with no deleted items."""
        response = await client.get(
            "/api/v1/admin/trash/stats", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "deleted_designs" in data
        assert "deleted_projects" in data
        assert "deleted_assemblies" in data
        assert "deleted_files" in data
        assert "total_deleted" in data

    async def test_update_retention_policy(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Update retention policy sets new days value."""
        response = await client.patch(
            "/api/v1/admin/trash/retention-policy",
            headers=admin_headers,
            json={"retention_days": 60},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["retention_days"] == 60

    async def test_update_retention_policy_invalid_days(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Retention policy rejects invalid day values."""
        response = await client.patch(
            "/api/v1/admin/trash/retention-policy",
            headers=admin_headers,
            json={"retention_days": 0},
        )
        assert response.status_code == 422

    async def test_permanent_delete_invalid_type(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Permanent delete with invalid resource type returns 400."""
        response = await client.delete(
            f"/api/v1/admin/trash/invalid_type/{uuid4()}/permanent",
            headers=admin_headers,
        )
        assert response.status_code == 400

    async def test_permanent_delete_not_in_trash(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Permanent delete of non-trashed resource returns 404."""
        response = await client.delete(
            f"/api/v1/admin/trash/design/{uuid4()}/permanent",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_permanent_delete_design(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Permanently delete a soft-deleted design."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, user=user, project=project)

        # Soft-delete first
        design.deleted_at = datetime.now(tz=UTC)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/admin/trash/design/{design.id}/permanent",
            headers=admin_headers,
        )
        assert response.status_code == 200

        # Verify permanently deleted
        result = await db_session.execute(
            select(Design).where(Design.id == design.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_restore_from_trash(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ) -> None:
        """Restore a soft-deleted design from trash."""
        user = await UserFactory.create(db_session)
        project = await ProjectFactory.create(db_session, user=user)
        design = await DesignFactory.create(db_session, user=user, project=project)

        # Soft-delete first
        design.deleted_at = datetime.now(tz=UTC)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/admin/trash/design/{design.id}/restore",
            headers=admin_headers,
        )
        assert response.status_code == 200

        # Verify restored
        await db_session.refresh(design)
        assert design.deleted_at is None

    async def test_restore_not_in_trash(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Restoring a non-trashed resource returns 404."""
        response = await client.post(
            f"/api/v1/admin/trash/project/{uuid4()}/restore",
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_restore_invalid_resource_type(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Restoring with invalid resource type returns 400."""
        response = await client.post(
            f"/api/v1/admin/trash/foobar/{uuid4()}/restore",
            headers=admin_headers,
        )
        assert response.status_code == 400

    async def test_force_trash_cleanup(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Force trash cleanup returns summary."""
        response = await client.post(
            "/api/v1/admin/trash/cleanup",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "cleaned" in data
        assert "total_cleaned" in data

    async def test_reclamation_potential(
        self, client: AsyncClient, admin_headers: dict
    ) -> None:
        """Get reclamation potential returns valid structure."""
        response = await client.get(
            "/api/v1/admin/trash/reclamation-potential",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "reclaimable_files" in data
        assert "reclaimable_bytes" in data
        assert "reclaimable_human" in data
        assert "by_type" in data
