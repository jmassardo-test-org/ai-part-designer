"""
Tests for the large-scale seed data generator.

These tests verify the seed script's functionality without requiring
an actual database connection.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_tiers():
    """Create mock subscription tiers."""
    return {
        "free": uuid4(),
        "starter": uuid4(),
        "pro": uuid4(),
        "enterprise": uuid4(),
    }


# =============================================================================
# Test User Generation
# =============================================================================


class TestGenerateUser:
    """Tests for user generation."""

    def test_generate_user_creates_valid_user(self):
        """User generator creates a valid User instance."""
        from app.seeds.large_scale import generate_user

        hashed_pwd = "hashed_password_123"
        user = generate_user("free", hashed_pwd, 0)

        assert user.id is not None
        assert isinstance(user.id, UUID)
        assert user.email.startswith("seed_")
        assert user.password_hash == hashed_pwd
        assert user.display_name is not None
        assert user.role == "user"

    def test_generate_user_email_has_seed_prefix(self):
        """Generated users have seed_ prefix in email for identification."""
        from app.seeds.large_scale import generate_user

        user = generate_user("pro", "pwd", 42)

        assert user.email.startswith("seed_")
        assert "@" in user.email

    def test_generate_user_with_different_indices_unique_emails(self):
        """Different indices produce different email addresses."""
        from app.seeds.large_scale import generate_user

        user1 = generate_user("free", "pwd", 0)
        user2 = generate_user("free", "pwd", 1)

        assert user1.email != user2.email


# =============================================================================
# Test Organization Generation
# =============================================================================


class TestGenerateOrganization:
    """Tests for organization generation."""

    def test_generate_organization_creates_valid_org(self):
        """Organization generator creates a valid Organization instance."""
        from app.seeds.large_scale import generate_organization

        owner_id = str(uuid4())
        org = generate_organization(owner_id)

        assert org.id is not None
        assert isinstance(org.id, UUID)
        assert org.name is not None
        assert org.slug is not None
        assert org.owner_id == owner_id

    def test_generate_organization_has_valid_slug(self):
        """Generated organizations have valid URL-safe slugs."""
        from app.seeds.large_scale import generate_organization

        org = generate_organization(str(uuid4()))

        # Slugs should be lowercase with no spaces
        assert org.slug == org.slug.lower() or "-" in org.slug


# =============================================================================
# Test Project Generation
# =============================================================================


class TestGenerateProject:
    """Tests for project generation."""

    def test_generate_project_creates_valid_project(self):
        """Project generator creates a valid Project instance."""
        from app.seeds.large_scale import generate_project

        user_id = str(uuid4())
        project = generate_project(user_id)

        assert project.id is not None
        assert project.name is not None
        assert project.user_id == user_id

    def test_generate_project_with_org_id(self):
        """Projects can be assigned to organizations."""
        from app.seeds.large_scale import generate_project

        user_id = str(uuid4())
        org_id = str(uuid4())
        project = generate_project(user_id, org_id)

        assert project.organization_id == org_id

    def test_generate_project_without_org_id(self):
        """Projects can be created without organizations."""
        from app.seeds.large_scale import generate_project

        user_id = str(uuid4())
        project = generate_project(user_id, None)

        assert project.organization_id is None


# =============================================================================
# Test Design Generation
# =============================================================================


class TestGenerateDesign:
    """Tests for design generation."""

    def test_generate_design_creates_valid_design(self):
        """Design generator creates a valid Design instance."""
        from app.seeds.large_scale import generate_design

        project_id = str(uuid4())
        user_id = str(uuid4())  # Kept for API compatibility
        design = generate_design(project_id, user_id)

        assert design.id is not None
        assert design.name is not None
        assert design.project_id == project_id
        # Note: Design doesn't have direct user_id - gets user through Project

    def test_generate_design_has_valid_source(self):
        """Generated designs have valid source types."""
        from app.seeds.large_scale import DESIGN_SOURCES, generate_design

        design = generate_design(str(uuid4()), str(uuid4()))

        assert design.source_type in DESIGN_SOURCES


# =============================================================================
# Test Notification Generation
# =============================================================================


class TestGenerateNotification:
    """Tests for notification generation."""

    def test_generate_notification_creates_valid_notification(self):
        """Notification generator creates a valid Notification instance."""
        from app.seeds.large_scale import generate_notification

        user_id = str(uuid4())
        notification = generate_notification(user_id)

        assert notification.id is not None
        assert notification.user_id == user_id
        assert notification.message is not None

    def test_generate_notification_has_valid_type(self):
        """Generated notifications have valid types."""
        from app.models.notification import NotificationType
        from app.seeds.large_scale import generate_notification

        notification = generate_notification(str(uuid4()))

        valid_types = [
            NotificationType.SYSTEM_ANNOUNCEMENT,
            NotificationType.JOB_COMPLETED,
            NotificationType.JOB_FAILED,
        ]
        assert notification.type in valid_types


# =============================================================================
# Test Audit Log Generation
# =============================================================================


class TestGenerateAuditLog:
    """Tests for audit log generation."""

    def test_generate_audit_log_creates_valid_log(self):
        """Audit log generator creates a valid AuditLog instance."""
        from app.seeds.large_scale import generate_audit_log

        user_id = str(uuid4())
        log = generate_audit_log(user_id)

        assert log.id is not None
        assert log.user_id == user_id
        assert log.action is not None

    def test_generate_audit_log_without_user(self):
        """Audit logs can be created without a user (system actions)."""
        from app.seeds.large_scale import generate_audit_log

        log = generate_audit_log(None)

        assert log.id is not None
        assert log.user_id is None


# =============================================================================
# Test Scale Presets
# =============================================================================


class TestScalePresets:
    """Tests for scale preset configurations."""

    def test_scale_presets_exist(self):
        """All scale presets are defined."""
        from app.seeds.large_scale import SCALE_PRESETS

        assert "small" in SCALE_PRESETS
        assert "medium" in SCALE_PRESETS
        assert "large" in SCALE_PRESETS

    def test_scale_presets_have_required_keys(self):
        """Each preset has all required configuration keys."""
        from app.seeds.large_scale import SCALE_PRESETS

        required_keys = {"users", "orgs", "projects_per_user", "designs_per_project"}

        for preset_name, preset in SCALE_PRESETS.items():
            assert required_keys.issubset(preset.keys()), f"Missing keys in {preset_name}"

    def test_small_preset_values(self):
        """Small preset has appropriate values."""
        from app.seeds.large_scale import SCALE_PRESETS

        small = SCALE_PRESETS["small"]

        assert small["users"] <= 1000
        assert small["orgs"] <= 50

    def test_large_preset_values(self):
        """Large preset has larger values than small."""
        from app.seeds.large_scale import SCALE_PRESETS

        small = SCALE_PRESETS["small"]
        large = SCALE_PRESETS["large"]

        assert large["users"] > small["users"]
        assert large["orgs"] > small["orgs"]


# =============================================================================
# Test Tier Distribution
# =============================================================================


class TestTierDistribution:
    """Tests for subscription tier distribution."""

    def test_tier_distribution_sums_to_one(self):
        """Tier distribution percentages sum to 1.0."""
        from app.seeds.large_scale import TIER_DISTRIBUTION

        total = sum(TIER_DISTRIBUTION.values())
        assert abs(total - 1.0) < 0.001  # Allow small floating point error

    def test_tier_distribution_has_all_tiers(self):
        """All subscription tiers are represented."""
        from app.seeds.large_scale import TIER_DISTRIBUTION

        expected_tiers = {"free", "starter", "pro", "enterprise"}
        assert set(TIER_DISTRIBUTION.keys()) == expected_tiers

    def test_tier_distribution_values_are_positive(self):
        """All tier percentages are positive."""
        from app.seeds.large_scale import TIER_DISTRIBUTION

        for tier, pct in TIER_DISTRIBUTION.items():
            assert pct > 0, f"Tier {tier} has non-positive percentage"


# =============================================================================
# Test Batch Insert Helper
# =============================================================================


class TestBatchInsert:
    """Tests for the batch insert helper."""

    @pytest.mark.asyncio
    async def test_batch_insert_adds_all_objects(self, mock_session):
        """Batch insert adds all objects to session."""
        from app.seeds.large_scale import batch_insert

        objects = [MagicMock() for _ in range(10)]

        count = await batch_insert(mock_session, objects, batch_size=5)

        assert count == 10
        assert mock_session.add_all.call_count == 2  # Two batches
        assert mock_session.flush.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_insert_respects_batch_size(self, mock_session):
        """Batch insert respects the batch size parameter."""
        from app.seeds.large_scale import batch_insert

        objects = [MagicMock() for _ in range(25)]

        await batch_insert(mock_session, objects, batch_size=10)

        # 25 objects / 10 batch size = 3 batches (10 + 10 + 5)
        assert mock_session.add_all.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_insert_empty_list(self, mock_session):
        """Batch insert handles empty list."""
        from app.seeds.large_scale import batch_insert

        count = await batch_insert(mock_session, [])

        assert count == 0
        assert mock_session.add_all.call_count == 0


# =============================================================================
# Test Idempotency Functions
# =============================================================================


class TestIdempotencyFunctions:
    """Tests for idempotency and cleanup functions."""

    def test_seed_marker_email_defined(self):
        """Seed marker email is defined."""
        from app.seeds.large_scale import SEED_MARKER_EMAIL

        assert SEED_MARKER_EMAIL is not None
        assert "@" in SEED_MARKER_EMAIL

    @pytest.mark.asyncio
    async def test_check_if_seeded_returns_false_when_not_seeded(self):
        """check_if_seeded returns False when marker user not found."""
        from app.seeds.large_scale import check_if_seeded

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await check_if_seeded(mock_session)

        assert result is False

    @pytest.mark.asyncio
    async def test_check_if_seeded_returns_true_when_seeded(self):
        """check_if_seeded returns True when marker user found."""
        from app.seeds.large_scale import check_if_seeded

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # User exists
        mock_session.execute.return_value = mock_result

        result = await check_if_seeded(mock_session)

        assert result is True


# =============================================================================
# Test Project Status Distribution
# =============================================================================


class TestProjectStatusDistribution:
    """Tests for project status distribution."""

    def test_project_status_distribution_sums_to_one(self):
        """Project status percentages sum to 1.0."""
        from app.seeds.large_scale import PROJECT_STATUS_DISTRIBUTION

        total = sum(PROJECT_STATUS_DISTRIBUTION.values())
        assert abs(total - 1.0) < 0.001

    def test_project_status_distribution_has_common_statuses(self):
        """Common project statuses are represented."""
        from app.seeds.large_scale import PROJECT_STATUS_DISTRIBUTION

        assert "active" in PROJECT_STATUS_DISTRIBUTION
        assert PROJECT_STATUS_DISTRIBUTION["active"] > 0.5  # Most projects active
