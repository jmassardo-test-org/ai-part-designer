"""
Tests for AI command handlers.

Tests the execution of slash commands including design management,
export, template, and other commands.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.command_handlers import CommandHandler, CommandResult
from app.ai.commands import ParsedCommand
from app.models import Design, User


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def command_handler() -> CommandHandler:
    """Create a command handler instance."""
    return CommandHandler()


@pytest_asyncio.fixture
async def mock_user(db_session: AsyncSession) -> User:
    """Create a mock user for testing."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def mock_design(db_session: AsyncSession, mock_user: User) -> Design:
    """Create a mock design for testing."""
    design = Design(
        id=uuid4(),
        name="Test Design",
        user_id=mock_user.id,
        description="Test description",
        source_type="ai_generated",
    )
    db_session.add(design)
    await db_session.commit()
    return design


@pytest.fixture
def valid_command():
    """Create a valid parsed command."""
    return ParsedCommand(
        command="save",
        args=[],
        raw="/save",
        valid=True,
        error=None,
    )


@pytest.fixture
def invalid_command():
    """Create an invalid parsed command."""
    return ParsedCommand(
        command="invalid",
        args=[],
        raw="/invalid",
        valid=False,
        error="Invalid command syntax",
    )


# =============================================================================
# Command Handler Base Tests
# =============================================================================


@pytest.mark.asyncio
async def test_handle_invalid_command_returns_error(
    command_handler: CommandHandler,
    invalid_command: ParsedCommand,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test handling an invalid command returns error result."""
    result = await command_handler.handle(
        invalid_command,
        mock_user,
        db_session,
    )

    assert not result.success
    assert "Invalid command" in result.message or invalid_command.error in result.message


@pytest.mark.asyncio
async def test_handle_unknown_command_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test handling an unknown command returns error."""
    unknown_command = ParsedCommand(
        command="nonexistent",
        args=[],
        raw="/nonexistent",
        valid=True,
    )

    result = await command_handler.handle(
        unknown_command,
        mock_user,
        db_session,
    )

    assert not result.success
    assert "Unknown command" in result.message
    assert "nonexistent" in result.message


@pytest.mark.asyncio
async def test_handle_command_with_exception(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test command handler catches exceptions and returns error result."""
    command = ParsedCommand(
        command="save",
        args=[],
        raw="/save",
        valid=True,
    )

    # Patch the handler to raise an exception
    with patch.object(
        command_handler,
        "handle_save",
        side_effect=Exception("Test error"),
    ):
        result = await command_handler.handle(
            command,
            mock_user,
            db_session,
        )

    assert not result.success
    assert "Error executing command" in result.message


# =============================================================================
# Design Management Command Tests
# =============================================================================


@pytest.mark.asyncio
async def test_handle_save_with_design_success(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test save command with existing design succeeds."""
    command = ParsedCommand(
        command="save",
        args=[],
        raw="/save",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert result.success
    assert "saved" in result.message.lower()
    assert mock_design.name in result.message
    assert result.data is not None
    assert "design_id" in result.data


@pytest.mark.asyncio
async def test_handle_save_without_design_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test save command without design returns error."""
    command = ParsedCommand(
        command="save",
        args=[],
        raw="/save",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=None,
    )

    assert not result.success
    assert "No design" in result.message


@pytest.mark.asyncio
async def test_handle_saveas_with_valid_name(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test saveas command with valid name creates new design."""
    new_name = "New Design Name"
    command = ParsedCommand(
        command="saveas",
        args=[new_name],
        raw=f"/saveas {new_name}",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert result.success
    assert new_name in result.message
    assert result.data is not None
    assert "design_id" in result.data


@pytest.mark.asyncio
async def test_handle_saveas_without_name_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test saveas command without name returns error."""
    command = ParsedCommand(
        command="saveas",
        args=[],
        raw="/saveas",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert not result.success
    assert "provide a name" in result.message.lower()


@pytest.mark.asyncio
async def test_handle_saveas_without_design_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test saveas command without design returns error."""
    command = ParsedCommand(
        command="saveas",
        args=["New Name"],
        raw="/saveas New Name",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=None,
    )

    assert not result.success
    assert "No design" in result.message


@pytest.mark.asyncio
async def test_handle_rename_with_valid_name(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test rename command with valid name."""
    new_name = "Renamed Design"
    command = ParsedCommand(
        command="rename",
        args=[new_name],
        raw=f"/rename {new_name}",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert result.success
    assert new_name in result.message
    # Verify design was renamed
    await db_session.refresh(mock_design)
    assert mock_design.name == new_name


@pytest.mark.asyncio
async def test_handle_rename_without_name_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test rename command without name returns error."""
    command = ParsedCommand(
        command="rename",
        args=[],
        raw="/rename",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert not result.success
    assert "provide a name" in result.message.lower()


@pytest.mark.asyncio
async def test_handle_rename_without_design_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test rename command without design returns error."""
    command = ParsedCommand(
        command="rename",
        args=["New Name"],
        raw="/rename New Name",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=None,
    )

    assert not result.success
    assert "No design" in result.message


@pytest.mark.asyncio
async def test_handle_delete_with_design(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test delete command with design."""
    command = ParsedCommand(
        command="delete",
        args=[],
        raw="/delete",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert result.success
    assert "deleted" in result.message.lower()


@pytest.mark.asyncio
async def test_handle_delete_without_design_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test delete command without design returns error."""
    command = ParsedCommand(
        command="delete",
        args=[],
        raw="/delete",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=None,
    )

    assert not result.success
    assert "No design" in result.message


# =============================================================================
# Export Command Tests
# =============================================================================


@pytest.mark.asyncio
async def test_handle_export_with_valid_format(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test export command with valid format."""
    command = ParsedCommand(
        command="export",
        args=["stl"],
        raw="/export stl",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert result.success
    assert "export" in result.message.lower()


@pytest.mark.asyncio
async def test_handle_export_without_format_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test export command without format returns error."""
    command = ParsedCommand(
        command="export",
        args=[],
        raw="/export",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert not result.success
    assert "format" in result.message.lower()


@pytest.mark.asyncio
async def test_handle_export_without_design_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test export command without design returns error."""
    command = ParsedCommand(
        command="export",
        args=["stl"],
        raw="/export stl",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=None,
    )

    assert not result.success
    assert "No design" in result.message


# =============================================================================
# Template Command Tests
# =============================================================================


@pytest.mark.asyncio
async def test_handle_maketemplate_with_design(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test maketemplate command with design."""
    command = ParsedCommand(
        command="maketemplate",
        args=[],
        raw="/maketemplate",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert result.success
    assert "template" in result.message.lower()


@pytest.mark.asyncio
async def test_handle_maketemplate_without_design_returns_error(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test maketemplate command without design returns error."""
    command = ParsedCommand(
        command="maketemplate",
        args=[],
        raw="/maketemplate",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        design=None,
    )

    assert not result.success
    assert "No design" in result.message


# =============================================================================
# History Command Tests
# =============================================================================


@pytest.mark.asyncio
async def test_handle_undo_with_conversation(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test undo command with conversation."""
    from app.models import Conversation

    conversation = Conversation(
        id=uuid4(),
        user_id=mock_user.id,
        design_id=None,
    )
    db_session.add(conversation)
    await db_session.commit()

    command = ParsedCommand(
        command="undo",
        args=[],
        raw="/undo",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        conversation=conversation,
    )

    assert result.success
    assert "undo" in result.message.lower()


@pytest.mark.asyncio
async def test_handle_redo_with_conversation(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test redo command with conversation."""
    from app.models import Conversation

    conversation = Conversation(
        id=uuid4(),
        user_id=mock_user.id,
        design_id=None,
    )
    db_session.add(conversation)
    await db_session.commit()

    command = ParsedCommand(
        command="redo",
        args=[],
        raw="/redo",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
        conversation=conversation,
    )

    assert result.success
    assert "redo" in result.message.lower()


# =============================================================================
# Help Command Tests
# =============================================================================


@pytest.mark.asyncio
async def test_handle_help_command(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test help command returns available commands."""
    command = ParsedCommand(
        command="help",
        args=[],
        raw="/help",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
    )

    assert result.success
    assert "commands" in result.message.lower() or "help" in result.message.lower()


@pytest.mark.asyncio
async def test_handle_help_for_specific_command(
    command_handler: CommandHandler,
    mock_user: User,
    db_session: AsyncSession,
):
    """Test help command with specific command argument."""
    command = ParsedCommand(
        command="help",
        args=["save"],
        raw="/help save",
        valid=True,
    )

    result = await command_handler.handle(
        command,
        mock_user,
        db_session,
    )

    assert result.success
    # Should contain information about save command


# =============================================================================
# Command Result Tests
# =============================================================================


def test_command_result_creation():
    """Test CommandResult dataclass creation."""
    result = CommandResult(
        success=True,
        message="Test message",
        data={"key": "value"},
        show_in_chat=True,
    )

    assert result.success
    assert result.message == "Test message"
    assert result.data == {"key": "value"}
    assert result.show_in_chat


def test_command_result_defaults():
    """Test CommandResult default values."""
    result = CommandResult(
        success=False,
        message="Error message",
    )

    assert not result.success
    assert result.message == "Error message"
    assert result.data is None
    assert result.show_in_chat is True


# =============================================================================
# ParsedCommand Helper Tests
# =============================================================================


def test_parsed_command_get_arg_with_existing_arg():
    """Test get_arg returns existing argument."""
    command = ParsedCommand(
        command="test",
        args=["arg1", "arg2", "arg3"],
        raw="/test arg1 arg2 arg3",
        valid=True,
    )

    assert command.get_arg(0) == "arg1"
    assert command.get_arg(1) == "arg2"
    assert command.get_arg(2) == "arg3"


def test_parsed_command_get_arg_with_default():
    """Test get_arg returns default for missing argument."""
    command = ParsedCommand(
        command="test",
        args=["arg1"],
        raw="/test arg1",
        valid=True,
    )

    assert command.get_arg(0) == "arg1"
    assert command.get_arg(1) == ""
    assert command.get_arg(2, "default") == "default"


def test_parsed_command_get_arg_out_of_bounds():
    """Test get_arg handles out of bounds gracefully."""
    command = ParsedCommand(
        command="test",
        args=[],
        raw="/test",
        valid=True,
    )

    assert command.get_arg(0) == ""
    assert command.get_arg(10) == ""
    assert command.get_arg(100, "fallback") == "fallback"


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_command_handler_initialization():
    """Test command handler initializes correctly."""
    handler = CommandHandler()

    assert handler is not None
    assert handler.parser is not None
    assert hasattr(handler, "handle")
    assert hasattr(handler, "handle_save")
    assert hasattr(handler, "handle_saveas")
    assert hasattr(handler, "handle_rename")
    assert hasattr(handler, "handle_delete")
    assert hasattr(handler, "handle_export")


@pytest.mark.asyncio
async def test_multiple_commands_in_sequence(
    command_handler: CommandHandler,
    mock_user: User,
    mock_design: Design,
    db_session: AsyncSession,
):
    """Test executing multiple commands in sequence."""
    # First command: rename
    rename_cmd = ParsedCommand(
        command="rename",
        args=["Updated Name"],
        raw="/rename Updated Name",
        valid=True,
    )

    result1 = await command_handler.handle(
        rename_cmd,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert result1.success

    # Second command: save
    save_cmd = ParsedCommand(
        command="save",
        args=[],
        raw="/save",
        valid=True,
    )

    result2 = await command_handler.handle(
        save_cmd,
        mock_user,
        db_session,
        design=mock_design,
    )

    assert result2.success
