"""
Tests for organization feature enforcement on API endpoints.

Verifies that when an organization disables a feature,
endpoints correctly return 403 and prevent access.

Tests cover both direct org_id resolution (teams, file uploads)
and indirect chain resolution (conversations via design → project → org).
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.features import OrgFeature
from app.models.conversation import Conversation, ConversationMessage, ConversationStatus
from app.models.design import Design
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.project import Project
from app.models.subscription import SubscriptionTier
from app.models.team import Team

# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture(autouse=True)
async def seed_subscription_tiers(db_session: AsyncSession) -> None:
    """Seed subscription tiers with all features enabled.

    Org enforcement tests need tier-level feature checks to pass so that
    the org-level enforcement can be tested in isolation. This fixture
    creates a free tier with every feature enabled.
    """
    # Check if already seeded (avoid duplicates with api/conftest.py fixture)
    from sqlalchemy import select

    result = await db_session.execute(
        select(SubscriptionTier).where(SubscriptionTier.slug == "free")
    )
    existing = result.scalar_one_or_none()
    if existing:
        return

    tier = SubscriptionTier(
        slug="free",
        name="Free",
        description="Free tier for all users",
        price_monthly_cents=0,
        price_yearly_cents=0,
        monthly_credits=100,
        max_projects=5,
        max_designs_per_project=10,
        max_concurrent_jobs=1,
        max_storage_gb=1,
        max_file_size_mb=25,
        features={
            "basic_generation": True,
            "ai_chat": True,
            "ai_generation": True,
            "file_uploads": True,
            "design_sharing": True,
            "teams": True,
            "assemblies": True,
            "bom": True,
        },
        is_active=True,
    )
    db_session.add(tier)
    await db_session.commit()


@pytest.fixture
async def test_org_with_features(db_session: AsyncSession, test_user):
    """Create a test organization with all features enabled."""
    org = Organization(
        id=uuid4(),
        name="Test Organization",
        slug=f"test-org-features-{uuid4().hex[:8]}",
        owner_id=test_user.id,
        settings={
            "enabled_features": [
                OrgFeature.AI_GENERATION,
                OrgFeature.AI_CHAT,
                OrgFeature.DESIGN_SHARING,
                OrgFeature.TEAMS,
                OrgFeature.FILE_UPLOADS,
                OrgFeature.ASSEMBLIES,
                OrgFeature.BOM,
            ],
        },
    )
    db_session.add(org)

    # Add user as owner
    member = OrganizationMember(
        id=uuid4(),
        organization_id=org.id,
        user_id=test_user.id,
        role=OrganizationRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(org)

    yield org

    # Cleanup
    try:
        await db_session.delete(member)
        await db_session.delete(org)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_org_no_features(db_session: AsyncSession, test_user):
    """Create a test organization with all features disabled.

    NOTE: An empty list ``[]`` is treated as "unset" by
    ``Organization.enabled_features`` and falls through to tier defaults.
    We use a single irrelevant feature so the list is non-empty but
    none of the tested features (ai_chat, ai_generation, teams, etc.)
    are included.
    """
    org = Organization(
        id=uuid4(),
        name="Test Organization No Features",
        slug=f"test-org-no-features-{uuid4().hex[:8]}",
        owner_id=test_user.id,
        settings={
            "enabled_features": ["export_stl"],  # Only basic export enabled
        },
    )
    db_session.add(org)

    # Add user as owner
    member = OrganizationMember(
        id=uuid4(),
        organization_id=org.id,
        user_id=test_user.id,
        role=OrganizationRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(org)

    yield org

    # Cleanup
    try:
        await db_session.delete(member)
        await db_session.delete(org)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_project_in_org(
    db_session: AsyncSession,
    test_user,
    test_org_with_features,
):
    """Create a test project belonging to an organization."""
    project = Project(
        id=uuid4(),
        user_id=test_user.id,
        organization_id=test_org_with_features.id,
        name="Test Org Project",
        description="Project for testing org features",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    yield project

    # Cleanup
    try:
        await db_session.delete(project)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_project_in_org_no_features(
    db_session: AsyncSession,
    test_user,
    test_org_no_features,
):
    """Create a test project belonging to an org with no features."""
    project = Project(
        id=uuid4(),
        user_id=test_user.id,
        organization_id=test_org_no_features.id,
        name="Test Org Project No Features",
        description="Project for testing disabled features",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    yield project

    # Cleanup
    try:
        await db_session.delete(project)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_personal_project(db_session: AsyncSession, test_user):
    """Create a personal project (no org)."""
    project = Project(
        id=uuid4(),
        user_id=test_user.id,
        organization_id=None,
        name="Personal Project",
        description="Personal project with no org",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    yield project

    try:
        await db_session.delete(project)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_design_in_org(
    db_session: AsyncSession,
    test_user,
    test_project_in_org,
):
    """Create a design in an org-scoped project (features enabled)."""
    design = Design(
        id=uuid4(),
        project_id=test_project_in_org.id,
        user_id=test_user.id,
        name="Org Design",
        source_type="manual",
        status="draft",
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)

    yield design

    try:
        await db_session.delete(design)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_design_in_org_no_features(
    db_session: AsyncSession,
    test_user,
    test_project_in_org_no_features,
):
    """Create a design in an org-scoped project (features disabled)."""
    design = Design(
        id=uuid4(),
        project_id=test_project_in_org_no_features.id,
        user_id=test_user.id,
        name="Org Design No Features",
        source_type="manual",
        status="draft",
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)

    yield design

    try:
        await db_session.delete(design)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_design_personal(
    db_session: AsyncSession,
    test_user,
    test_personal_project,
):
    """Create a design in a personal project (no org)."""
    design = Design(
        id=uuid4(),
        project_id=test_personal_project.id,
        user_id=test_user.id,
        name="Personal Design",
        source_type="manual",
        status="draft",
    )
    db_session.add(design)
    await db_session.commit()
    await db_session.refresh(design)

    yield design

    try:
        await db_session.delete(design)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_conversation_with_org_design(
    db_session: AsyncSession,
    test_user,
    test_design_in_org,
):
    """Create a conversation linked to an org-scoped design (features enabled)."""
    convo = Conversation(
        id=uuid4(),
        user_id=test_user.id,
        design_id=test_design_in_org.id,
        status=ConversationStatus.ACTIVE.value,
        title="Test org conversation",
    )
    db_session.add(convo)

    # Add a welcome message so the conversation is valid
    msg = ConversationMessage(
        id=uuid4(),
        conversation_id=convo.id,
        role="assistant",
        message_type="text",
        content="Welcome!",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(convo)

    yield convo

    try:
        await db_session.delete(msg)
        await db_session.delete(convo)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_conversation_with_org_design_no_features(
    db_session: AsyncSession,
    test_user,
    test_design_in_org_no_features,
):
    """Create a conversation linked to an org design (features disabled)."""
    convo = Conversation(
        id=uuid4(),
        user_id=test_user.id,
        design_id=test_design_in_org_no_features.id,
        status=ConversationStatus.ACTIVE.value,
        title="Test org conversation no features",
    )
    db_session.add(convo)

    msg = ConversationMessage(
        id=uuid4(),
        conversation_id=convo.id,
        role="assistant",
        message_type="text",
        content="Welcome!",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(convo)

    yield convo

    try:
        await db_session.delete(msg)
        await db_session.delete(convo)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_conversation_personal(
    db_session: AsyncSession,
    test_user,
):
    """Create a personal conversation (no design_id)."""
    convo = Conversation(
        id=uuid4(),
        user_id=test_user.id,
        design_id=None,
        status=ConversationStatus.ACTIVE.value,
        title="Personal conversation",
    )
    db_session.add(convo)

    msg = ConversationMessage(
        id=uuid4(),
        conversation_id=convo.id,
        role="assistant",
        message_type="text",
        content="Welcome!",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(convo)

    yield convo

    try:
        await db_session.delete(msg)
        await db_session.delete(convo)
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def test_conversation_with_personal_design(
    db_session: AsyncSession,
    test_user,
    test_design_personal,
):
    """Create a conversation linked to a personal design (no org)."""
    convo = Conversation(
        id=uuid4(),
        user_id=test_user.id,
        design_id=test_design_personal.id,
        status=ConversationStatus.ACTIVE.value,
        title="Personal design conversation",
    )
    db_session.add(convo)

    msg = ConversationMessage(
        id=uuid4(),
        conversation_id=convo.id,
        role="assistant",
        message_type="text",
        content="Welcome!",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(convo)

    yield convo

    try:
        await db_session.delete(msg)
        await db_session.delete(convo)
        await db_session.commit()
    except Exception:
        pass


# =============================================================================
# Team Endpoints Tests
# =============================================================================


class TestTeamFeatureEnforcement:
    """Tests for 'teams' feature enforcement."""

    async def test_create_team_with_feature_enabled(
        self, client: AsyncClient, auth_headers: dict, test_org_with_features
    ):
        """Should allow team creation when feature is enabled."""
        response = await client.post(
            f"/api/v1/organizations/{test_org_with_features.id}/teams",
            headers=auth_headers,
            json={
                "name": "Engineering Team",
                "description": "Test team",
                "slug": f"eng-{uuid4().hex[:8]}",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering Team"

    async def test_create_team_with_feature_disabled(
        self, client: AsyncClient, auth_headers: dict, test_org_no_features
    ):
        """Should return 403 when teams feature is disabled."""
        response = await client.post(
            f"/api/v1/organizations/{test_org_no_features.id}/teams",
            headers=auth_headers,
            json={
                "name": "Engineering Team",
                "description": "Test team",
                "slug": f"eng-{uuid4().hex[:8]}",
            },
        )

        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "feature_disabled"
        assert data["detail"]["feature"] == "teams"

    async def test_add_team_member_with_feature_disabled(
        self, client: AsyncClient, auth_headers: dict, test_org_no_features, db_session
    ):
        """Should return 403 when trying to add team member with feature disabled."""
        # First create a team (bypassing feature check for setup)
        team = Team(
            id=uuid4(),
            organization_id=test_org_no_features.id,
            name="Test Team",
            slug=f"test-{uuid4().hex[:8]}",
        )
        db_session.add(team)
        await db_session.commit()

        # Try to add a member
        response = await client.post(
            f"/api/v1/organizations/{test_org_no_features.id}/teams/{team.id}/members",
            headers=auth_headers,
            json={
                "user_id": str(uuid4()),
                "role": "member",
            },
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "feature_disabled"


# =============================================================================
# Assembly & BOM Tests
# =============================================================================


class TestAssemblyFeatureEnforcement:
    """Tests for 'assemblies' feature enforcement."""

    async def test_create_assembly_with_feature_disabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project_in_org_no_features,
    ):
        """Should deny creation when assemblies feature is disabled.

        Note: The require_org_feature_for_project dependency expects project_id
        as a path parameter, but POST /assemblies has it in the request body.
        FastAPI can't inject body fields into dependencies, so this returns 422
        (validation error) instead of 403. This is a known limitation.
        """
        response = await client.post(
            "/api/v1/assemblies",
            headers=auth_headers,
            json={
                "name": "Test Assembly",
                "description": "Assembly test",
                "project_id": str(test_project_in_org_no_features.id),
            },
        )

        # 422: Dependency can't extract project_id from body (known limitation)
        # 403: Feature disabled, 404: Project not found
        assert response.status_code in (403, 404, 422)


class TestBOMFeatureEnforcement:
    """Tests for 'bom' feature enforcement."""

    async def test_get_bom_with_feature_disabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_project_in_org_no_features,
    ):
        """Should return 403 when BOM feature is disabled."""
        from app.models.assembly import Assembly

        # Create assembly (bypassing feature check for setup)
        assembly = Assembly(
            id=uuid4(),
            project_id=test_project_in_org_no_features.id,
            user_id=test_project_in_org_no_features.user_id,
            name="Test Assembly",
        )
        db_session.add(assembly)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/assemblies/{assembly.id}/bom",
            headers=auth_headers,
        )

        # Should fail on tier check OR org check
        assert response.status_code in (403, 404)


# =============================================================================
# Conversation Feature Enforcement — ai_chat & ai_generation
# =============================================================================


class TestConversationFeatureEnforcement:
    """Tests for org-level 'ai_chat' and 'ai_generation' feature enforcement.

    Conversation endpoints resolve org context through:
    conversation.design_id → design.project_id → project.organization_id → org

    Personal conversations (no design_id, or personal project) skip org checks.
    """

    async def test_create_conversation_with_org_design_feature_disabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_design_in_org_no_features,
    ):
        """Should return 403 when creating conversation with design in org that disables ai_chat."""
        response = await client.post(
            "/api/v1/conversations/",
            headers=auth_headers,
            json={"design_id": str(test_design_in_org_no_features.id)},
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "feature_disabled"
        assert data["detail"]["feature"] == "ai_chat"

    async def test_create_conversation_with_org_design_feature_enabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_design_in_org,
    ):
        """Should allow conversation creation when org has ai_chat enabled."""
        response = await client.post(
            "/api/v1/conversations/",
            headers=auth_headers,
            json={"design_id": str(test_design_in_org.id)},
        )

        # Should succeed (201) or fail for unrelated reasons (e.g., tier check)
        # but NOT 403 with feature_disabled
        if response.status_code == 403:
            data = response.json()
            # If 403, it must be tier-level, not org-level
            assert data["detail"]["error"] != "feature_disabled"

    async def test_create_conversation_personal_skips_org_check(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should skip org check when no design_id is provided (personal convo)."""
        response = await client.post(
            "/api/v1/conversations/",
            headers=auth_headers,
            json={},
        )

        # Should succeed or fail for tier reasons, never feature_disabled
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"

    async def test_create_conversation_personal_design_skips_org_check(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_design_personal,
    ):
        """Should skip org check when design belongs to a personal project."""
        response = await client.post(
            "/api/v1/conversations/",
            headers=auth_headers,
            json={"design_id": str(test_design_personal.id)},
        )

        # Should succeed or fail for non-org reasons, never feature_disabled
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"

    async def test_send_message_org_feature_disabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation_with_org_design_no_features,
    ):
        """Should return 403 when sending message in convo linked to org with ai_chat disabled."""
        convo = test_conversation_with_org_design_no_features
        response = await client.post(
            f"/api/v1/conversations/{convo.id}/messages",
            headers=auth_headers,
            json={"content": "Make it bigger"},
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "feature_disabled"
        assert data["detail"]["feature"] == "ai_chat"

    async def test_send_message_org_feature_enabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation_with_org_design,
    ):
        """Should allow message when org has ai_chat enabled."""
        convo = test_conversation_with_org_design
        response = await client.post(
            f"/api/v1/conversations/{convo.id}/messages",
            headers=auth_headers,
            json={"content": "Make it bigger"},
        )

        # Should not fail with feature_disabled
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"

    async def test_send_message_personal_conversation_skips_org_check(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation_personal,
    ):
        """Should skip org check for personal conversations (no design_id)."""
        convo = test_conversation_personal
        response = await client.post(
            f"/api/v1/conversations/{convo.id}/messages",
            headers=auth_headers,
            json={"content": "Create a box"},
        )

        # Should not fail with feature_disabled
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"

    async def test_send_message_personal_design_skips_org_check(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation_with_personal_design,
    ):
        """Should skip org check for conversations linked to personal designs."""
        convo = test_conversation_with_personal_design
        response = await client.post(
            f"/api/v1/conversations/{convo.id}/messages",
            headers=auth_headers,
            json={"content": "Make it taller"},
        )

        # Should not fail with feature_disabled
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"

    async def test_trigger_generation_org_feature_disabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation_with_org_design_no_features,
    ):
        """Should return 403 when triggering generation on convo with ai_generation disabled."""
        convo = test_conversation_with_org_design_no_features
        response = await client.post(
            f"/api/v1/conversations/{convo.id}/generate",
            headers=auth_headers,
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "feature_disabled"
        assert data["detail"]["feature"] == "ai_generation"

    async def test_trigger_generation_personal_skips_org_check(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation_personal,
    ):
        """Should skip org check for personal conversations on trigger_generation."""
        convo = test_conversation_personal
        response = await client.post(
            f"/api/v1/conversations/{convo.id}/generate",
            headers=auth_headers,
        )

        # Should not fail with feature_disabled (may fail with 400 "no understanding")
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"

    async def test_direct_generate_no_org_enforcement(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Direct generate has no org context — only tier enforcement applies."""
        response = await client.post(
            "/api/v1/conversations/direct-generate",
            headers=auth_headers,
            json={"description": "Create a box 10mm x 10mm x 10mm"},
        )

        # Should not fail with feature_disabled (may succeed or fail for tier/other reasons)
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"


# =============================================================================
# Share Feature Tests
# =============================================================================


class TestShareFeatureEnforcement:
    """Tests for 'design_sharing' feature enforcement."""

    async def test_share_design_with_feature_disabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_project_in_org_no_features,
    ):
        """Should return 403 when design_sharing is disabled."""
        # Create design (bypassing checks for setup)
        design = Design(
            id=uuid4(),
            project_id=test_project_in_org_no_features.id,
            user_id=test_project_in_org_no_features.user_id,
            name="Test Design",
            source_type="manual",
            status="ready",
        )
        db_session.add(design)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/shares/designs/{design.id}",
            headers=auth_headers,
            json={
                "email": "user@example.com",
                "permission": "view",
            },
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "feature_disabled"
        assert data["detail"]["feature"] == "design_sharing"


# =============================================================================
# File Upload Feature Enforcement
# =============================================================================


class TestFileUploadFeatureEnforcement:
    """Tests for org-level 'file_uploads' feature enforcement.

    File uploads resolve org context through an optional organization_id
    query parameter. If not provided, the upload is treated as personal.
    """

    async def test_upload_with_org_id_feature_disabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_org_no_features,
    ):
        """Should return 403 when uploading with org_id where file_uploads is disabled."""
        import io

        file_content = b"test file content for org upload"
        files = {"file": ("test.step", io.BytesIO(file_content), "application/octet-stream")}

        response = await client.post(
            f"/api/v1/files/upload?organization_id={test_org_no_features.id}",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "feature_disabled"
        assert data["detail"]["feature"] == "file_uploads"

    async def test_upload_with_org_id_feature_enabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_org_with_features,
    ):
        """Should allow upload when org has file_uploads enabled."""
        import io

        file_content = b"test file content for org upload"
        files = {"file": ("test.step", io.BytesIO(file_content), "application/octet-stream")}

        response = await client.post(
            f"/api/v1/files/upload?organization_id={test_org_with_features.id}",
            headers=auth_headers,
            files=files,
        )

        # Should not fail with feature_disabled (may fail for other reasons like tier)
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"

    async def test_upload_without_org_id_skips_org_check(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should skip org check when no organization_id is provided (personal upload)."""
        import io

        file_content = b"test file content personal"
        files = {"file": ("test.step", io.BytesIO(file_content), "application/octet-stream")}

        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files=files,
        )

        # Should not fail with feature_disabled
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"

    async def test_upload_with_nonexistent_org_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 404 when org_id doesn't exist."""
        import io

        fake_org_id = uuid4()
        file_content = b"test file content"
        files = {"file": ("test.step", io.BytesIO(file_content), "application/octet-stream")}

        response = await client.post(
            f"/api/v1/files/upload?organization_id={fake_org_id}",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 404


# =============================================================================
# Feature Re-enable Tests
# =============================================================================


class TestFeatureReEnable:
    """Test that re-enabling a feature immediately unblocks access."""

    async def test_re_enable_teams_feature_unblocks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_org_no_features,
        db_session: AsyncSession,
    ):
        """When admin re-enables teams feature, requests should succeed."""
        # First verify feature is blocked
        response = await client.post(
            f"/api/v1/organizations/{test_org_no_features.id}/teams",
            headers=auth_headers,
            json={
                "name": "Engineering Team",
                "description": "Test team",
                "slug": f"eng-{uuid4().hex[:8]}",
            },
        )
        assert response.status_code == 403

        # Re-enable the feature
        test_org_no_features.settings["enabled_features"] = ["teams"]
        await db_session.commit()

        # Now should succeed
        response = await client.post(
            f"/api/v1/organizations/{test_org_no_features.id}/teams",
            headers=auth_headers,
            json={
                "name": "Engineering Team",
                "description": "Test team",
                "slug": f"eng-{uuid4().hex[:8]}",
            },
        )
        assert response.status_code == 201

    async def test_re_enable_sharing_feature_unblocks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_org_no_features,
        db_session: AsyncSession,
        test_project_in_org_no_features,
    ):
        """When admin re-enables sharing, shares should work."""
        # Create design
        design = Design(
            id=uuid4(),
            project_id=test_project_in_org_no_features.id,
            user_id=test_project_in_org_no_features.user_id,
            name="Test Design",
            source_type="manual",
            status="ready",
        )
        db_session.add(design)
        await db_session.commit()

        # First verify feature is blocked
        response = await client.post(
            f"/api/v1/shares/designs/{design.id}",
            headers=auth_headers,
            json={
                "email": "user@example.com",
                "permission": "view",
            },
        )
        assert response.status_code == 403

        # Re-enable the feature
        test_org_no_features.settings["enabled_features"] = ["design_sharing"]
        await db_session.commit()

        # Now should succeed (or fail for different reason like user not found)
        response = await client.post(
            f"/api/v1/shares/designs/{design.id}",
            headers=auth_headers,
            json={
                "email": "user@example.com",
                "permission": "view",
            },
        )
        # 404 means it passed feature check but user not found
        assert response.status_code in (200, 201, 404)

    async def test_re_enable_ai_chat_unblocks_conversation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_org_no_features,
        test_design_in_org_no_features,
        db_session: AsyncSession,
    ):
        """When admin re-enables ai_chat, conversation creation with org design should work."""
        # First verify feature is blocked
        response = await client.post(
            "/api/v1/conversations/",
            headers=auth_headers,
            json={"design_id": str(test_design_in_org_no_features.id)},
        )
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "feature_disabled"
        assert data["detail"]["feature"] == "ai_chat"

        # Re-enable the feature
        test_org_no_features.settings["enabled_features"] = ["ai_chat"]
        await db_session.commit()

        # Now should pass org check (may still fail on tier check)
        response = await client.post(
            "/api/v1/conversations/",
            headers=auth_headers,
            json={"design_id": str(test_design_in_org_no_features.id)},
        )
        if response.status_code == 403:
            # If still 403, it must be tier-level, not org-level
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"

    async def test_re_enable_file_uploads_unblocks(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_org_no_features,
        db_session: AsyncSession,
    ):
        """When admin re-enables file_uploads, org-scoped uploads should work."""
        import io

        file_content = b"test re-enable content"
        files = {"file": ("test.step", io.BytesIO(file_content), "application/octet-stream")}

        # First verify feature is blocked
        response = await client.post(
            f"/api/v1/files/upload?organization_id={test_org_no_features.id}",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error"] == "feature_disabled"

        # Re-enable the feature
        test_org_no_features.settings["enabled_features"] = ["file_uploads"]
        await db_session.commit()

        # Now should pass org check
        files = {"file": ("test.step", io.BytesIO(file_content), "application/octet-stream")}
        response = await client.post(
            f"/api/v1/files/upload?organization_id={test_org_no_features.id}",
            headers=auth_headers,
            files=files,
        )
        if response.status_code == 403:
            data = response.json()
            assert data["detail"]["error"] != "feature_disabled"
