"""
API Performance Benchmarking Tests.

These tests measure and validate response times for critical API endpoints.
They serve as baseline performance metrics and regression detection.

Usage:
    pytest tests/performance/test_api_performance.py -v --benchmark-only
    pytest tests/performance/test_api_performance.py -v  # Regular run with timing assertions

Requirements:
    - pytest-benchmark (optional, for detailed benchmarks)
    - Running database with test data
"""

import asyncio
import statistics
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.main import app
from app.models.user import User

# =============================================================================
# Configuration
# =============================================================================

# Performance thresholds (in seconds)
THRESHOLDS = {
    "auth_login": 0.5,  # Login should be under 500ms
    "auth_register": 0.5,  # Registration under 500ms
    "designs_list": 0.3,  # List designs under 300ms
    "designs_create": 0.5,  # Create design under 500ms
    "designs_get": 0.2,  # Get single design under 200ms
    "templates_list": 0.3,  # List templates under 300ms
    "projects_list": 0.3,  # List projects under 300ms
    "projects_get": 0.2,  # Get single project under 200ms
    "users_me": 0.1,  # Get current user under 100ms
    "health_check": 0.05,  # Health check under 50ms
}

# Number of iterations for averaging
ITERATIONS = 5


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def perf_user_data() -> dict[str, str]:
    """Generate unique user data for performance tests."""
    unique_id = str(uuid4())[:8]
    return {
        "email": f"perf-test-{unique_id}@example.com",
        "password": "PerfTest123!",
        "display_name": "Performance Test User",
    }


@pytest.fixture
async def perf_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for performance testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def perf_auth_client(
    perf_client: AsyncClient,
    db_session: AsyncSession,
) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    """Create an authenticated client with test user for performance testing."""
    # Create a test user directly in the database
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"perf-auth-{user_id}@example.com",
        password_hash=hash_password("PerfTest123!"),
        display_name="Perf Auth User",
        role="user",
        status="active",
        email_verified_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Login to get token
    response = await perf_client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "PerfTest123!",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Set auth header
    perf_client.headers["Authorization"] = f"Bearer {token}"

    yield perf_client, user

    # Cleanup
    await db_session.delete(user)
    await db_session.commit()


# =============================================================================
# Helper Functions
# =============================================================================


async def measure_request(
    client: AsyncClient,
    method: str,
    url: str,
    iterations: int = ITERATIONS,
    **kwargs: Any,
) -> dict[str, float]:
    """Measure request performance over multiple iterations.

    Args:
        client: HTTP client to use.
        method: HTTP method (GET, POST, etc.).
        url: URL to request.
        iterations: Number of iterations for averaging.
        **kwargs: Additional arguments to pass to the request.

    Returns:
        Dictionary with timing statistics.
    """
    times: list[float] = []

    for _ in range(iterations):
        start = time.perf_counter()

        if method.upper() == "GET":
            await client.get(url, **kwargs)
        elif method.upper() == "POST":
            await client.post(url, **kwargs)
        elif method.upper() == "PUT":
            await client.put(url, **kwargs)
        elif method.upper() == "DELETE":
            await client.delete(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

        elapsed = time.perf_counter() - start
        times.append(elapsed)

        # Small delay between requests
        await asyncio.sleep(0.01)

    return {
        "min": min(times),
        "max": max(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "p95": sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else max(times),
        "iterations": iterations,
    }


def assert_performance(
    stats: dict[str, float],
    threshold: float,
    endpoint_name: str,
) -> None:
    """Assert that performance meets the threshold.

    Args:
        stats: Timing statistics from measure_request.
        threshold: Maximum acceptable mean time in seconds.
        endpoint_name: Name of the endpoint for error message.
    """
    assert stats["mean"] < threshold, (
        f"{endpoint_name} is too slow! "
        f"Mean: {stats['mean'] * 1000:.2f}ms, "
        f"Threshold: {threshold * 1000:.2f}ms, "
        f"Min: {stats['min'] * 1000:.2f}ms, "
        f"Max: {stats['max'] * 1000:.2f}ms"
    )


# =============================================================================
# Performance Tests
# =============================================================================


class TestHealthPerformance:
    """Performance tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_performance(
        self,
        perf_client: AsyncClient,
    ) -> None:
        """Health check should respond quickly."""
        stats = await measure_request(
            perf_client,
            "GET",
            "/api/v1/health",
        )

        assert_performance(stats, THRESHOLDS["health_check"], "Health check")

        print("\nHealth Check Performance:")
        print(f"  Mean: {stats['mean'] * 1000:.2f}ms")
        print(f"  Min: {stats['min'] * 1000:.2f}ms")
        print(f"  Max: {stats['max'] * 1000:.2f}ms")


class TestAuthPerformance:
    """Performance tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_performance(
        self,
        perf_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Login should complete within threshold."""
        # Create a user for login testing
        user = User(
            id=uuid4(),
            email=f"login-perf-{uuid4()}@example.com",
            password_hash=hash_password("LoginTest123!"),
            display_name="Login Perf User",
            role="user",
            status="active",
            email_verified_at=datetime.now(UTC),
        )
        db_session.add(user)
        await db_session.commit()

        try:
            stats = await measure_request(
                perf_client,
                "POST",
                "/api/v1/auth/login",
                json={
                    "email": user.email,
                    "password": "LoginTest123!",
                },
            )

            assert_performance(stats, THRESHOLDS["auth_login"], "Login")

            print("\nLogin Performance:")
            print(f"  Mean: {stats['mean'] * 1000:.2f}ms")
            print(f"  Min: {stats['min'] * 1000:.2f}ms")
            print(f"  Max: {stats['max'] * 1000:.2f}ms")
        finally:
            await db_session.delete(user)
            await db_session.commit()


class TestDesignsPerformance:
    """Performance tests for design endpoints."""

    @pytest.mark.asyncio
    async def test_list_designs_performance(
        self,
        perf_auth_client: tuple[AsyncClient, User],
    ) -> None:
        """Listing designs should be fast."""
        client, _ = perf_auth_client

        stats = await measure_request(
            client,
            "GET",
            "/api/v1/designs",
        )

        assert_performance(stats, THRESHOLDS["designs_list"], "List designs")

        print("\nList Designs Performance:")
        print(f"  Mean: {stats['mean'] * 1000:.2f}ms")
        print(f"  Min: {stats['min'] * 1000:.2f}ms")
        print(f"  Max: {stats['max'] * 1000:.2f}ms")


class TestProjectsPerformance:
    """Performance tests for project endpoints."""

    @pytest.mark.asyncio
    async def test_list_projects_performance(
        self,
        perf_auth_client: tuple[AsyncClient, User],
    ) -> None:
        """Listing projects should be fast."""
        client, _ = perf_auth_client

        stats = await measure_request(
            client,
            "GET",
            "/api/v1/projects",
        )

        assert_performance(stats, THRESHOLDS["projects_list"], "List projects")

        print("\nList Projects Performance:")
        print(f"  Mean: {stats['mean'] * 1000:.2f}ms")
        print(f"  Min: {stats['min'] * 1000:.2f}ms")
        print(f"  Max: {stats['max'] * 1000:.2f}ms")


class TestTemplatesPerformance:
    """Performance tests for template endpoints."""

    @pytest.mark.asyncio
    async def test_list_templates_performance(
        self,
        perf_client: AsyncClient,
    ) -> None:
        """Listing templates should be fast (public endpoint)."""
        stats = await measure_request(
            perf_client,
            "GET",
            "/api/v1/templates",
        )

        assert_performance(stats, THRESHOLDS["templates_list"], "List templates")

        print("\nList Templates Performance:")
        print(f"  Mean: {stats['mean'] * 1000:.2f}ms")
        print(f"  Min: {stats['min'] * 1000:.2f}ms")
        print(f"  Max: {stats['max'] * 1000:.2f}ms")


class TestUserPerformance:
    """Performance tests for user endpoints."""

    @pytest.mark.asyncio
    async def test_get_current_user_performance(
        self,
        perf_auth_client: tuple[AsyncClient, User],
    ) -> None:
        """Getting current user should be very fast."""
        client, _ = perf_auth_client

        stats = await measure_request(
            client,
            "GET",
            "/api/v1/users/me",
        )

        assert_performance(stats, THRESHOLDS["users_me"], "Get current user")

        print("\nGet Current User Performance:")
        print(f"  Mean: {stats['mean'] * 1000:.2f}ms")
        print(f"  Min: {stats['min'] * 1000:.2f}ms")
        print(f"  Max: {stats['max'] * 1000:.2f}ms")


# =============================================================================
# Benchmark Summary
# =============================================================================


class TestPerformanceSummary:
    """Generate a performance summary report."""

    @pytest.mark.asyncio
    async def test_performance_summary(
        self,
        perf_auth_client: tuple[AsyncClient, User],
    ) -> None:
        """Run all performance tests and generate summary."""
        client, _ = perf_auth_client

        results: dict[str, dict[str, float]] = {}

        # Health check
        results["health_check"] = await measure_request(
            client,
            "GET",
            "/api/v1/health",
        )

        # Public endpoints - Templates
        results["templates_list"] = await measure_request(
            client,
            "GET",
            "/api/v1/templates",
        )

        # User
        results["users_me"] = await measure_request(
            client,
            "GET",
            "/api/v1/users/me",
        )

        # Projects
        results["projects_list"] = await measure_request(
            client,
            "GET",
            "/api/v1/projects",
        )

        # Designs
        results["designs_list"] = await measure_request(
            client,
            "GET",
            "/api/v1/designs",
        )

        # Print summary
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 60)
        print(f"{'Endpoint':<25} {'Mean':<12} {'Min':<12} {'Max':<12} {'Status':<10}")
        print("-" * 60)

        all_passed = True
        for name, stats in results.items():
            threshold = THRESHOLDS.get(name, 0.5)
            status = "✓ PASS" if stats["mean"] < threshold else "✗ FAIL"
            if stats["mean"] >= threshold:
                all_passed = False

            print(
                f"{name:<25} "
                f"{stats['mean'] * 1000:>8.2f}ms  "
                f"{stats['min'] * 1000:>8.2f}ms  "
                f"{stats['max'] * 1000:>8.2f}ms  "
                f"{status}"
            )

        print("-" * 60)
        print(f"Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
        print("=" * 60)

        assert all_passed, "Some endpoints failed performance thresholds"
