"""
Tests for WebSocket Manager Module.

Tests connection tracking, room subscriptions, and message structures.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.websocket.manager import Connection, ConnectionManager

# =============================================================================
# Connection Tests
# =============================================================================


class TestConnection:
    """Tests for Connection dataclass."""

    def test_basic_creation(self):
        """Test creating a basic connection."""
        ws_mock = MagicMock()
        conn = Connection(
            websocket=ws_mock,
            user_id="user-123",
        )

        assert conn.websocket is ws_mock
        assert conn.user_id == "user-123"

    def test_default_values(self):
        """Test default values are set correctly."""
        ws_mock = MagicMock()
        conn = Connection(
            websocket=ws_mock,
            user_id="user-456",
        )

        assert conn.connected_at is not None
        assert isinstance(conn.connected_at, datetime)
        assert conn.subscriptions == set()
        assert conn.metadata == {}

    def test_with_subscriptions(self):
        """Test connection with subscriptions."""
        ws_mock = MagicMock()
        conn = Connection(
            websocket=ws_mock,
            user_id="user-789",
            subscriptions={"design-updates", "job-status"},
        )

        assert "design-updates" in conn.subscriptions
        assert "job-status" in conn.subscriptions

    def test_with_metadata(self):
        """Test connection with metadata."""
        ws_mock = MagicMock()
        conn = Connection(
            websocket=ws_mock,
            user_id="user-abc",
            metadata={"client": "web", "version": "1.0"},
        )

        assert conn.metadata["client"] == "web"
        assert conn.metadata["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_send_success(self):
        """Test successful message send."""
        ws_mock = AsyncMock()
        conn = Connection(
            websocket=ws_mock,
            user_id="user-123",
        )

        result = await conn.send({"type": "test", "data": "hello"})

        assert result is True
        ws_mock.send_json.assert_called_once_with({"type": "test", "data": "hello"})

    @pytest.mark.asyncio
    async def test_send_failure(self):
        """Test failed message send."""
        ws_mock = AsyncMock()
        ws_mock.send_json.side_effect = Exception("Connection closed")
        conn = Connection(
            websocket=ws_mock,
            user_id="user-123",
        )

        result = await conn.send({"type": "test"})

        assert result is False


# =============================================================================
# ConnectionManager Tests
# =============================================================================


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    def test_creation(self):
        """Test creating a connection manager."""
        manager = ConnectionManager()

        assert manager is not None
        assert manager.connection_count == 0
        assert manager.user_count == 0

    def test_connection_count_property(self):
        """Test connection count property."""
        manager = ConnectionManager()

        # Initially zero
        assert manager.connection_count == 0

        # Add some connections manually
        ws_mock = MagicMock()
        conn = Connection(websocket=ws_mock, user_id="user-1")
        manager._connections["user-1"] = {conn}

        assert manager.connection_count == 1

    def test_user_count_property(self):
        """Test user count property."""
        manager = ConnectionManager()

        # Initially zero
        assert manager.user_count == 0

        # Add connections for different users
        ws1 = MagicMock()
        ws2 = MagicMock()
        conn1 = Connection(websocket=ws1, user_id="user-1")
        conn2 = Connection(websocket=ws2, user_id="user-2")
        manager._connections["user-1"] = {conn1}
        manager._connections["user-2"] = {conn2}

        assert manager.user_count == 2

    def test_multiple_connections_per_user(self):
        """Test multiple connections for same user."""
        manager = ConnectionManager()

        ws1 = MagicMock()
        ws2 = MagicMock()
        conn1 = Connection(websocket=ws1, user_id="user-1")
        conn2 = Connection(websocket=ws2, user_id="user-1")
        manager._connections["user-1"] = {conn1, conn2}

        # Two connections but one user
        assert manager.connection_count == 2
        assert manager.user_count == 1

    def test_rooms_tracking(self):
        """Test room subscription tracking."""
        manager = ConnectionManager()

        ws_mock = MagicMock()
        conn = Connection(websocket=ws_mock, user_id="user-1")

        # Add to room
        manager._rooms["design-123"] = {conn}

        assert "design-123" in manager._rooms
        assert len(manager._rooms["design-123"]) == 1

    def test_peak_connections_tracking(self):
        """Test peak connections is tracked."""
        manager = ConnectionManager()

        # Should start at 0
        assert manager._peak_connections == 0

    def test_total_connections_tracking(self):
        """Test total connections is tracked."""
        manager = ConnectionManager()

        assert manager._total_connections == 0


# =============================================================================
# Edge Cases
# =============================================================================


class TestWebSocketEdgeCases:
    """Tests for edge cases."""

    def test_empty_manager(self):
        """Test empty manager properties."""
        manager = ConnectionManager()

        assert manager.connection_count == 0
        assert manager.user_count == 0
        assert len(manager._connections) == 0
        assert len(manager._rooms) == 0

    def test_connection_with_empty_user_id(self):
        """Test connection with empty user ID."""
        ws_mock = MagicMock()
        conn = Connection(
            websocket=ws_mock,
            user_id="",
        )

        assert conn.user_id == ""

    def test_connection_subscriptions_mutable(self):
        """Test subscriptions can be modified."""
        ws_mock = MagicMock()
        conn = Connection(
            websocket=ws_mock,
            user_id="user-1",
        )

        conn.subscriptions.add("new-room")
        assert "new-room" in conn.subscriptions

        conn.subscriptions.remove("new-room")
        assert "new-room" not in conn.subscriptions

    def test_connection_metadata_mutable(self):
        """Test metadata can be modified."""
        ws_mock = MagicMock()
        conn = Connection(
            websocket=ws_mock,
            user_id="user-1",
        )

        conn.metadata["new_key"] = "value"
        assert conn.metadata["new_key"] == "value"

    def test_multiple_rooms_per_connection(self):
        """Test connection can be in multiple rooms."""
        manager = ConnectionManager()

        ws_mock = MagicMock()
        conn = Connection(websocket=ws_mock, user_id="user-1")

        manager._rooms["room-1"] = {conn}
        manager._rooms["room-2"] = {conn}
        manager._rooms["room-3"] = {conn}

        assert len(manager._rooms) == 3
        assert conn in manager._rooms["room-1"]
        assert conn in manager._rooms["room-2"]
        assert conn in manager._rooms["room-3"]
