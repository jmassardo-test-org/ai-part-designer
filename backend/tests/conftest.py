"""
Pytest configuration and fixtures for the AI Part Designer test suite.

This module provides shared fixtures for database sessions, test clients,
authentication, mocking, and factory utilities.
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test environment before importing app modules
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long"
# Set POSTGRES_DB to test_db before app imports (to override app/core/config.py default)
if "POSTGRES_DB" not in os.environ:
    os.environ["POSTGRES_DB"] = "test_db"
# Use PostgreSQL for testing - build URL from POSTGRES_* vars if DATABASE_URL not set
# Note: SQLite doesn't support JSONB, so PostgreSQL is required
if "DATABASE_URL" not in os.environ:
    # Build from individual postgres variables (for Docker container)
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    db = os.environ.get("POSTGRES_DB", "test_db")
    os.environ["DATABASE_URL"] = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
if "REDIS_URL" not in os.environ:
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from datetime import UTC

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Base

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from app.models import User
    from app.models.project import Project


# =============================================================================
# Event Loop Configuration
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Database Fixtures
# =============================================================================


def get_database_url():
    """Construct database URL from environment variables."""
    # Check for DATABASE_URL first
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    # Build from individual postgres variables (for Docker container)
    # Default to test_db for tests - matches docker-compose.test.yml
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    db = os.environ.get("POSTGRES_DB", "test_db")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine using PostgreSQL."""
    database_url = get_database_url()

    engine = create_async_engine(
        database_url,
        echo=False,
    )

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create isolated database session for each test."""
    from sqlalchemy import text

    async_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        # Clean up any existing data before the test
        # Get all table names and truncate them (excluding alembic)
        try:
            await session.execute(
                text("""
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version') LOOP
                        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;
                END $$;
            """)
            )
            await session.commit()
        except Exception:
            # If truncate fails (e.g., first run), that's ok
            await session.rollback()

        yield session

        # Clean up after the test
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def db(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Alias for db_session fixture for backward compatibility."""
    yield db_session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database dependency override."""
    from httpx import ASGITransport

    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_client(client: AsyncClient, auth_headers: dict[str, str]) -> AsyncClient:
    """Create authenticated test HTTP client."""
    client.headers.update(auth_headers)
    return client


@pytest_asyncio.fixture(scope="function")
async def admin_client(client: AsyncClient, admin_headers: dict[str, str]) -> AsyncClient:
    """Create admin authenticated test HTTP client."""
    client.headers.update(admin_headers)
    return client


@pytest_asyncio.fixture(scope="function")
async def simple_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client without database (for endpoints that don't need DB)."""
    from httpx import ASGITransport

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def async_client(client: AsyncClient) -> AsyncClient:
    """Alias for client fixture to match test naming conventions."""
    return client


@pytest.fixture
def mock_current_user():
    """Create a mock user for testing.

    Note: This fixture alone doesn't inject auth into the client.
    Use it with `mock_auth_client` or manually override the dependency.
    """
    from uuid import uuid4

    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.username = "testuser"
    user.is_active = True
    user.is_superuser = False
    user.role = "user"
    return user


@pytest_asyncio.fixture(scope="function")
async def mock_auth_client(
    db_session: AsyncSession,
    mock_current_user,
) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with mocked authentication.

    This client overrides get_current_user to return mock_current_user,
    allowing tests to bypass real authentication while still testing
    authorization and business logic.

    Also mocks require_org_feature to skip feature checks for unit tests.
    """
    from unittest.mock import patch

    from httpx import ASGITransport

    from app.core.auth import get_current_user
    from app.main import app

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return mock_current_user

    # Mock require_org_feature to return a no-op dependency
    def mock_require_org_feature(feature_name: str):
        async def no_op(*args, **kwargs):
            return None

        return no_op

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Patch require_org_feature at the module level
    with patch("app.api.deps.require_org_feature", mock_require_org_feature):
        with patch("app.api.v1.teams.require_org_feature", mock_require_org_feature):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac

    app.dependency_overrides.clear()


# =============================================================================
# Authentication Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    from datetime import datetime

    from app.core.security import hash_password
    from app.models import User

    user = User(
        email="test@example.com",
        password_hash=hash_password("TestPassword123!"),
        display_name="Test User",
        status="active",
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user_2(db_session: AsyncSession) -> User:
    """Create a second test user for access control tests."""
    from datetime import datetime

    from app.core.security import hash_password
    from app.models import User

    user = User(
        email="testuser2@example.com",
        password_hash=hash_password("TestPassword123!"),
        display_name="Test User 2",
        status="active",
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    from datetime import datetime

    from app.core.security import hash_password
    from app.models import User

    admin = User(
        email="admin@example.com",
        password_hash=hash_password("AdminPassword123!"),
        display_name="Admin User",
        status="active",
        role="admin",
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_project(db_session: AsyncSession, test_user: User) -> Project:
    """Create a test project."""
    from app.models.project import Project

    project = Project(
        user_id=test_user.id,
        name="Test Project",
        description="A test project for unit tests",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Generate authentication headers for test user."""
    from app.core.security import create_access_token

    token = create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        role=test_user.role,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_2(test_user_2: User) -> dict[str, str]:
    """Generate authentication headers for second test user."""
    from app.core.security import create_access_token

    token = create_access_token(
        user_id=test_user_2.id,
        email=test_user_2.email,
        role=test_user_2.role,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """Generate access token for test user (without Bearer prefix)."""
    from app.core.security import create_access_token

    return create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        role=test_user.role,
    )


@pytest.fixture
def admin_headers(test_admin: User) -> dict[str, str]:
    """Generate authentication headers for admin user."""
    from app.core.security import create_access_token

    token = create_access_token(
        user_id=test_admin.id,
        email=test_admin.email,
        role=test_admin.role,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def subscription_tiers(db_session: AsyncSession):
    """Seed subscription tiers for tests that need them."""
    from sqlalchemy import select

    from app.models.subscription import SubscriptionTier

    # Check if already seeded (by autouse fixture or previous test)
    result = await db_session.execute(
        select(SubscriptionTier).where(SubscriptionTier.slug == "free")
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Return existing tiers
        result = await db_session.execute(select(SubscriptionTier))
        return result.scalars().all()

    tiers = [
        SubscriptionTier(
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
            features={"basic_generation": True},
            is_active=True,
        ),
        SubscriptionTier(
            slug="pro",
            name="Pro",
            description="Professional tier",
            price_monthly_cents=1999,
            price_yearly_cents=19990,
            monthly_credits=1000,
            max_projects=50,
            max_designs_per_project=100,
            max_concurrent_jobs=5,
            max_storage_gb=10,
            max_file_size_mb=100,
            features={"basic_generation": True, "advanced_generation": True},
            is_active=True,
        ),
    ]

    for tier in tiers:
        db_session.add(tier)

    await db_session.commit()
    return tiers


@pytest_asyncio.fixture
async def test_org_with_features(db_session: AsyncSession, test_user: User):
    """Create a test organization with all features enabled."""
    from uuid import uuid4

    from app.core.features import OrgFeature
    from app.models.organization import Organization, OrganizationMember, OrganizationRole

    org = Organization(
        id=uuid4(),
        name="Test Organization",
        slug=f"test-org-{uuid4().hex[:8]}",
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

    return org


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis client for all tests."""
    mock = MagicMock()
    mock.exists = AsyncMock(return_value=False)  # Token not blacklisted
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.incr = AsyncMock(return_value=1)  # For rate limiting
    mock.expire = AsyncMock(return_value=True)
    mock.check_rate_limit = AsyncMock(return_value=(True, 100))
    mock.lpush = AsyncMock(return_value=1)  # For security audit logs
    mock.lrange = AsyncMock(return_value=[])  # For retrieving audit logs
    mock.increment_counter = AsyncMock(return_value=1)  # For security counters
    mock._connected = True

    # Patch in all modules that import redis_client directly
    patches = []
    patch_targets = [
        "app.core.auth.redis_client",
        "app.core.cache.redis_client",
        "app.core.rate_limiter.redis_client",
        "app.core.undo_tokens.redis_client",
        "app.services.security_audit.redis_client",
    ]

    # Create patches - some modules may not be loaded yet
    for target in patch_targets:
        patches.append(patch(target, mock))

    # Start patches - handle cases where modules aren't available yet
    for p in patches:
        try:
            p.start()
        except AttributeError:
            # Module not found during patch.start(), skip this patch
            pass

    yield mock

    # Stop patches - handle cases where patches weren't successfully started
    for p in patches:
        try:
            p.stop()
        except RuntimeError:
            # Patch was not started, skip
            pass


@pytest.fixture
def mock_celery():
    """Mock Celery task invocation."""
    with patch("app.worker.celery.app") as mock_app:
        mock_app.send_task = MagicMock()
        yield mock_app


@pytest.fixture
def mock_storage():
    """Mock MinIO storage client."""
    with patch("app.core.storage.get_storage") as mock:
        storage_mock = AsyncMock()
        storage_mock.upload_file.return_value = "https://storage.test/file.stl"
        storage_mock.download_file.return_value = b"file content"
        storage_mock.delete_file.return_value = True
        storage_mock.get_presigned_url.return_value = "https://storage.test/presigned"
        mock.return_value = storage_mock
        yield storage_mock


@pytest.fixture
def mock_claude():
    """Mock Claude (Anthropic) client."""
    with patch("app.ai.client.ClaudeClient") as mock:
        mock_instance = MagicMock()
        mock_instance.complete = AsyncMock(
            return_value='{"type": "box", "dimensions": {"length": 100}}'
        )
        mock_instance.is_configured = True
        mock.return_value = mock_instance
        yield mock


# =============================================================================
# CAD Fixtures
# =============================================================================


@pytest.fixture
def sample_box():
    """Create a sample box shape for testing."""
    from app.cad.primitives import create_box

    return create_box(100, 50, 25)


@pytest.fixture
def sample_cylinder():
    """Create a sample cylinder shape for testing."""
    from app.cad.primitives import create_cylinder

    return create_cylinder(radius=25, height=100)


@pytest.fixture
def sample_sphere():
    """Create a sample sphere shape for testing."""
    from app.cad.primitives import create_sphere

    return create_sphere(radius=50)


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for file operations."""
    return tmp_path


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings cache between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_factory_counters():
    """Reset factory counters between tests."""
    from tests.factories import reset_factories

    reset_factories()
    yield
    reset_factories()


# =============================================================================
# Factory Fixtures
# =============================================================================


@pytest.fixture
def user_factory():
    """Provide UserFactory for creating test users."""
    from tests.factories import UserFactory

    return UserFactory


@pytest.fixture
def project_factory():
    """Provide ProjectFactory for creating test projects."""
    from tests.factories import ProjectFactory

    return ProjectFactory


@pytest.fixture
def design_factory():
    """Provide DesignFactory for creating test designs."""
    from tests.factories import DesignFactory

    return DesignFactory


@pytest.fixture
def job_factory():
    """Provide JobFactory for creating test jobs."""
    from tests.factories import JobFactory

    return JobFactory


@pytest.fixture
def file_factory():
    """Provide FileFactory for creating test files."""
    from tests.factories import FileFactory

    return FileFactory


@pytest.fixture
def template_factory():
    """Provide TemplateFactory for creating test templates."""
    from tests.factories import TemplateFactory

    return TemplateFactory


@pytest.fixture
def version_factory():
    """Provide DesignVersionFactory for creating test versions."""
    from tests.factories import DesignVersionFactory

    return DesignVersionFactory


# =============================================================================
# Markers
# =============================================================================


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "cad: marks CAD-specific tests")
    config.addinivalue_line("markers", "ai: marks AI/LLM tests")


def pytest_collection_modifyitems(config, items):
    """Apply markers based on test location and skip slow tests by default."""
    for item in items:
        # Auto-mark based on path
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "cad" in str(item.fspath):
            item.add_marker(pytest.mark.cad)
        if "ai" in str(item.fspath):
            item.add_marker(pytest.mark.ai)

    # Skip slow tests unless explicitly requested
    if config.getoption("-m") != "slow":
        skip_slow = pytest.mark.skip(reason="need -m slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
