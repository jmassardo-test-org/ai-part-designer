"""
Tests for AI Commands Module.

Tests slash command parsing, command definitions, and the CommandParser class.
"""

import pytest

from app.ai.commands import (
    ALIASES,
    COMMANDS,
    CommandDefinition,
    CommandParser,
    ParsedCommand,
    command_parser,
)

# =============================================================================
# CommandDefinition Tests
# =============================================================================


class TestCommandDefinition:
    """Tests for CommandDefinition dataclass."""

    def test_basic_command(self):
        """Test creating a basic command with no args."""
        cmd = CommandDefinition(
            name="test",
            description="A test command",
        )

        assert cmd.name == "test"
        assert cmd.description == "A test command"
        assert cmd.args == 0
        assert cmd.arg_names == []
        assert cmd.aliases == []

    def test_command_with_args(self):
        """Test creating a command with arguments."""
        cmd = CommandDefinition(
            name="export",
            description="Export design",
            args=2,
            arg_names=["format", "filename"],
        )

        assert cmd.args == 2
        assert cmd.arg_names == ["format", "filename"]

    def test_command_with_aliases(self):
        """Test creating a command with aliases."""
        cmd = CommandDefinition(
            name="help",
            description="Show help",
            aliases=["?", "commands"],
        )

        assert "?" in cmd.aliases
        assert "commands" in cmd.aliases


# =============================================================================
# ParsedCommand Tests
# =============================================================================


class TestParsedCommand:
    """Tests for ParsedCommand dataclass."""

    def test_valid_command(self):
        """Test a valid parsed command."""
        cmd = ParsedCommand(
            command="save",
            args=[],
            raw="/save",
            valid=True,
        )

        assert cmd.command == "save"
        assert cmd.valid is True
        assert cmd.error is None

    def test_invalid_command(self):
        """Test an invalid parsed command."""
        cmd = ParsedCommand(
            command="unknown",
            args=[],
            raw="/unknown",
            valid=False,
            error="Unknown command",
        )

        assert cmd.valid is False
        assert cmd.error == "Unknown command"

    def test_get_arg_with_valid_index(self):
        """Test getting argument by index."""
        cmd = ParsedCommand(
            command="export",
            args=["stl", "myfile"],
            raw="/export stl myfile",
        )

        assert cmd.get_arg(0) == "stl"
        assert cmd.get_arg(1) == "myfile"

    def test_get_arg_with_invalid_index(self):
        """Test getting argument with invalid index returns default."""
        cmd = ParsedCommand(
            command="export",
            args=["stl"],
            raw="/export stl",
        )

        assert cmd.get_arg(5) == ""
        assert cmd.get_arg(5, "default") == "default"


# =============================================================================
# COMMANDS Registry Tests
# =============================================================================


class TestCommandsRegistry:
    """Tests for the COMMANDS registry."""

    def test_save_command_exists(self):
        """Test save command is defined."""
        assert "save" in COMMANDS
        assert COMMANDS["save"].description == "Save the current design"
        assert COMMANDS["save"].args == 0

    def test_export_command_exists(self):
        """Test export command is defined."""
        assert "export" in COMMANDS
        assert COMMANDS["export"].args == 1
        assert "format" in COMMANDS["export"].arg_names
        assert "download" in COMMANDS["export"].aliases

    def test_undo_command_exists(self):
        """Test undo command is defined."""
        assert "undo" in COMMANDS
        assert COMMANDS["undo"].args == 0

    def test_redo_command_exists(self):
        """Test redo command is defined."""
        assert "redo" in COMMANDS
        assert COMMANDS["redo"].args == 0

    def test_help_command_exists(self):
        """Test help command is defined."""
        assert "help" in COMMANDS
        assert "?" in COMMANDS["help"].aliases

    def test_rename_command_requires_arg(self):
        """Test rename command requires an argument."""
        assert "rename" in COMMANDS
        assert COMMANDS["rename"].args == 1
        assert "new_name" in COMMANDS["rename"].arg_names

    def test_view_command_exists(self):
        """Test view command is defined."""
        assert "view" in COMMANDS
        assert COMMANDS["view"].args == 1
        assert "mode" in COMMANDS["view"].arg_names

    def test_clear_command_exists(self):
        """Test clear command is defined."""
        assert "clear" in COMMANDS


# =============================================================================
# ALIASES Registry Tests
# =============================================================================


class TestAliasesRegistry:
    """Tests for the ALIASES registry."""

    def test_download_alias_to_export(self):
        """Test download is alias for export."""
        assert "download" in ALIASES
        assert ALIASES["download"] == "export"

    def test_question_mark_alias_to_help(self):
        """Test ? is alias for help."""
        assert "?" in ALIASES
        assert ALIASES["?"] == "help"

    def test_commands_alias_to_help(self):
        """Test commands is alias for help."""
        assert "commands" in ALIASES
        assert ALIASES["commands"] == "help"

    def test_template_alias_to_maketemplate(self):
        """Test template is alias for maketemplate."""
        assert "template" in ALIASES
        assert ALIASES["template"] == "maketemplate"

    def test_versions_alias_to_history(self):
        """Test versions is alias for history."""
        assert "versions" in ALIASES
        assert ALIASES["versions"] == "history"


# =============================================================================
# CommandParser Tests
# =============================================================================


class TestCommandParser:
    """Tests for CommandParser class."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return CommandParser()

    def test_is_command_with_slash(self, parser):
        """Test is_command returns True for slash commands."""
        assert parser.is_command("/save") is True
        assert parser.is_command("/export stl") is True

    def test_is_command_without_slash(self, parser):
        """Test is_command returns False for non-commands."""
        assert parser.is_command("hello") is False
        assert parser.is_command("create a box") is False

    def test_is_command_with_whitespace(self, parser):
        """Test is_command handles leading whitespace."""
        assert parser.is_command("  /save") is True

    def test_parse_returns_none_for_non_command(self, parser):
        """Test parse returns None for non-commands."""
        assert parser.parse("hello world") is None
        assert parser.parse("create a box") is None

    def test_parse_simple_command(self, parser):
        """Test parsing a simple command with no args."""
        result = parser.parse("/save")

        assert result is not None
        assert result.command == "save"
        assert result.args == []
        assert result.valid is True

    def test_parse_command_with_arg(self, parser):
        """Test parsing a command with an argument."""
        result = parser.parse("/export stl")

        assert result is not None
        assert result.command == "export"
        assert "stl" in result.args
        assert result.valid is True

    def test_parse_command_with_quoted_arg(self, parser):
        """Test parsing a command with quoted argument."""
        result = parser.parse('/rename "My New Design"')

        assert result is not None
        assert result.command == "rename"
        assert "My New Design" in result.args
        assert result.valid is True

    def test_parse_unknown_command(self, parser):
        """Test parsing an unknown command."""
        result = parser.parse("/unknown")

        assert result is not None
        assert result.valid is False
        assert "Unknown command" in result.error

    def test_parse_alias(self, parser):
        """Test parsing a command alias."""
        result = parser.parse("/download stl")

        assert result is not None
        assert result.command == "export"  # Resolved from alias
        assert result.valid is True

    def test_parse_missing_required_arg(self, parser):
        """Test parsing command with missing required arg."""
        result = parser.parse("/export")  # Missing format arg

        assert result is not None
        assert result.valid is False
        assert "Missing argument" in result.error

    def test_parse_case_insensitive(self, parser):
        """Test command parsing is case insensitive."""
        result = parser.parse("/SAVE")

        assert result is not None
        assert result.command == "save"
        assert result.valid is True

    def test_parse_command_with_multiple_args(self, parser):
        """Test parsing command with multiple args."""
        # Custom parser with multi-arg command
        custom_commands = {
            "multi": CommandDefinition(
                name="multi",
                description="Test multi args",
                args=2,
                arg_names=["arg1", "arg2"],
            ),
        }
        custom_parser = CommandParser(commands=custom_commands)

        result = custom_parser.parse("/multi first second")

        assert result is not None
        assert result.valid is True
        assert result.args == ["first", "second"]

    def test_parse_preserves_raw(self, parser):
        """Test parsed command preserves raw input."""
        result = parser.parse("/export stl")

        assert result.raw == "/export stl"


# =============================================================================
# CommandParser Help Tests
# =============================================================================


class TestCommandParserHelp:
    """Tests for CommandParser help functionality."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return CommandParser()

    def test_get_help_all_commands(self, parser):
        """Test getting help for all commands."""
        help_text = parser.get_help()

        assert "Available Commands" in help_text
        assert "/save" in help_text
        assert "/export" in help_text

    def test_get_help_specific_command(self, parser):
        """Test getting help for a specific command."""
        help_text = parser.get_help("save")

        assert "/save" in help_text
        assert "Save the current design" in help_text

    def test_get_help_command_with_slash(self, parser):
        """Test getting help with slash prefix."""
        help_text = parser.get_help("/export")

        assert "/export" in help_text
        assert "format" in help_text.lower()

    def test_get_help_unknown_command(self, parser):
        """Test getting help for unknown command."""
        help_text = parser.get_help("unknowncmd")

        assert "Unknown command" in help_text

    def test_get_help_shows_aliases(self, parser):
        """Test help shows aliases for commands."""
        help_text = parser.get_help("help")

        assert "aliases" in help_text.lower()


# =============================================================================
# Singleton Tests
# =============================================================================


class TestCommandParserSingleton:
    """Tests for the command_parser singleton."""

    def test_singleton_exists(self):
        """Test singleton is created."""
        assert command_parser is not None
        assert isinstance(command_parser, CommandParser)

    def test_singleton_has_commands(self):
        """Test singleton has commands loaded."""
        assert len(command_parser.commands) > 0

    def test_singleton_is_command(self):
        """Test singleton is_command method."""
        assert command_parser.is_command("/save") is True

    def test_singleton_parse(self):
        """Test singleton parse method."""
        result = command_parser.parse("/help")

        assert result is not None
        assert result.command == "help"


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return CommandParser()

    def test_empty_message(self, parser):
        """Test parsing empty message."""
        assert parser.parse("") is None

    def test_whitespace_only(self, parser):
        """Test parsing whitespace only."""
        assert parser.parse("   ") is None

    def test_slash_only(self, parser):
        """Test parsing just a slash."""
        result = parser.parse("/")

        assert result is not None
        assert result.valid is False

    def test_empty_quoted_arg(self, parser):
        """Test parsing empty quoted argument."""
        result = parser.parse('/rename ""')

        assert result is not None
        # Empty quoted string is still a valid arg
        assert "" in result.args

    def test_multiple_quotes(self, parser):
        """Test parsing with multiple quoted strings."""
        custom_commands = {
            "multi": CommandDefinition(
                name="multi",
                description="Test",
                args=2,
                arg_names=["a", "b"],
            ),
        }
        custom_parser = CommandParser(commands=custom_commands)

        result = custom_parser.parse('/multi "first arg" "second arg"')

        assert result is not None
        assert "first arg" in result.args
        assert "second arg" in result.args
