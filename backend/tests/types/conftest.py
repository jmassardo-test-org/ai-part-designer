"""
Test configuration for app.types module tests.

These are pure unit tests that don't need the autouse fixtures
from the parent conftest (like mock_redis).
"""

import pytest


@pytest.fixture(autouse=True)
def mock_redis():
    """Override parent mock_redis fixture - no-op for types tests."""
    return
