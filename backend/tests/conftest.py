"""
Pytest configuration and fixtures for the AI Part Designer test suite.

This module provides shared fixtures for database sessions, test clients,
authentication, mocking, and factory utilities.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.models import Base
from app.core.database import get_db
from app.core.config import get_settings

if TYPE_CHECKING:
    from app.models import User


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

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine with in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create isolated database session for each test."""
    async_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()


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
async def simple_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client without database (for endpoints that don't need DB)."""
    from httpx import ASGITransport
    from app.main import app
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> "User":
    """Create a test user."""
    from app.models import User
    from app.core.security import hash_password
    
    user = User(
        email="test@example.com",
        hashed_password=hash_password("TestPassword123!"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> "User":
    """Create a test admin user."""
    from app.models import User
    from app.core.security import hash_password
    
    admin = User(
        email="admin@example.com",
        hashed_password=hash_password("AdminPassword123!"),
        full_name="Admin User",
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(test_user: "User") -> dict[str, str]:
    """Generate authentication headers for test user."""
    from app.core.auth import create_access_token
    
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(test_admin: "User") -> dict[str, str]:
    """Generate authentication headers for admin user."""
    from app.core.auth import create_access_token
    
    token = create_access_token(subject=str(test_admin.id))
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("app.core.cache.get_redis") as mock:
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.delete.return_value = 1
        mock.return_value = redis_mock
        yield redis_mock


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
def mock_openai():
    """Mock OpenAI client."""
    with patch("app.services.ai.client") as mock:
        mock.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            content='{"type": "box", "dimensions": {"length": 100}}'
                        )
                    )
                ]
            )
        )
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
