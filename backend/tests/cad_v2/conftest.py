"""Pytest fixtures for CAD v2 tests."""

import pytest
from prometheus_client import REGISTRY


@pytest.fixture(autouse=True)
def cleanup_prometheus_registry():
    """Clean up Prometheus registry between tests to avoid duplicate metric errors.
    
    The prometheus-fastapi-instrumentator registers metrics with the global
    REGISTRY. When tests create multiple app instances (via TestClient),
    the same metrics get registered multiple times, causing the
    "Duplicated timeseries" error.
    
    This fixture cleans up the registry after each test to prevent this.
    """
    yield
    
    # Unregister collectors added by tests
    # Note: Accessing _collector_to_names is necessary as prometheus_client doesn't provide
    # a public API for listing collectors. This is a common pattern in testing.
    collectors_to_remove = []
    for collector in list(REGISTRY._collector_to_names.keys()):
        # Keep the default process and platform collectors
        if collector.__class__.__name__ not in [
            "ProcessCollector",
            "PlatformCollector",
            "GCCollector",
        ]:
            collectors_to_remove.append(collector)

    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass  # Ignore errors during cleanup
