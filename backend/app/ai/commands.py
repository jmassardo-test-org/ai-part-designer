"""
Chat command parser.

Parses slash commands from chat input for quick actions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class CommandDefinition:
    """Definition of a slash command."""

    name: str
    description: str
    args: int = 0  # Number of expected arguments
    arg_names: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)


@dataclass
class ParsedCommand:
    """Result of parsing a command from input."""

    command: str
    args: list[str]
    raw: str
    valid: bool = True
    error: str | None = None

    def get_arg(self, index: int, default: str = "") -> str:
        """Get argument at index with default."""
        return self.args[index] if index < len(self.args) else default


# =============================================================================
# Command Definitions
# =============================================================================


COMMANDS: dict[str, CommandDefinition] = {
    # Design management
    "save": CommandDefinition(
        name="save",
        description="Save the current design",
        args=0,
    ),
    "saveas": CommandDefinition(
        name="saveas",
        description="Save current design with a new name",
        args=1,
        arg_names=["name"],
    ),
    "rename": CommandDefinition(
        name="rename",
        description="Rename the current design",
        args=1,
        arg_names=["new_name"],
    ),
    "delete": CommandDefinition(
        name="delete",
        description="Delete the current design",
        args=0,
    ),

    # Export
    "export": CommandDefinition(
        name="export",
        description="Export design to specified format",
        args=1,
        arg_names=["format"],
        aliases=["download"],
    ),
    "exportall": CommandDefinition(
        name="exportall",
        description="Export all designs in project",
        args=1,
        arg_names=["format"],
    ),

    # Templates
    "maketemplate": CommandDefinition(
        name="maketemplate",
        description="Save current design as a template",
        args=0,
        aliases=["template"],
    ),

    # History
    "undo": CommandDefinition(
        name="undo",
        description="Undo last modification",
        args=0,
    ),
    "redo": CommandDefinition(
        name="redo",
        description="Redo last undone modification",
        args=0,
    ),
    "history": CommandDefinition(
        name="history",
        description="Show version history",
        args=0,
        aliases=["versions"],
    ),
    "restore": CommandDefinition(
        name="restore",
        description="Restore to a specific version",
        args=1,
        arg_names=["version"],
    ),

    # View
    "view": CommandDefinition(
        name="view",
        description="Switch view mode (top, front, side, iso)",
        args=1,
        arg_names=["mode"],
    ),
    "zoom": CommandDefinition(
        name="zoom",
        description="Zoom to fit or percentage",
        args=1,
        arg_names=["level"],
    ),
    "measure": CommandDefinition(
        name="measure",
        description="Enable measurement tool",
        args=0,
    ),

    # Help
    "help": CommandDefinition(
        name="help",
        description="Show available commands",
        args=0,
        aliases=["?", "commands"],
    ),

    # Debug/Dev
    "debug": CommandDefinition(
        name="debug",
        description="Show debug information",
        args=0,
    ),
    "clear": CommandDefinition(
        name="clear",
        description="Clear conversation history",
        args=0,
    ),
}


# Build alias lookup
ALIASES: dict[str, str] = {}
for cmd_name, cmd_def in COMMANDS.items():
    for alias in cmd_def.aliases:
        ALIASES[alias] = cmd_name


# =============================================================================
# Command Parser
# =============================================================================


class CommandParser:
    """
    Parses slash commands from user input.

    Commands start with / and may have arguments:
    - /save
    - /export stl
    - /rename "My New Design"
    """

    # Pattern to match commands at start of input
    COMMAND_PATTERN = re.compile(r"^/(\w+)(?:\s+(.*))?$", re.IGNORECASE)

    # Pattern to parse quoted arguments
    QUOTED_ARG_PATTERN = re.compile(r'"([^"]*)"')

    def __init__(self, commands: dict[str, CommandDefinition] | None = None):
        """
        Initialize parser with command definitions.

        Args:
            commands: Custom command definitions (defaults to COMMANDS)
        """
        self.commands = commands or COMMANDS
        self.aliases = {}

        # Build alias lookup
        for cmd_name, cmd_def in self.commands.items():
            for alias in cmd_def.aliases:
                self.aliases[alias] = cmd_name

    def parse(self, message: str) -> ParsedCommand | None:
        """
        Parse a slash command from message.

        Args:
            message: User input message

        Returns:
            ParsedCommand if message is a command, None otherwise
        """
        message = message.strip()

        if not message.startswith("/"):
            return None

        match = self.COMMAND_PATTERN.match(message)
        if not match:
            return ParsedCommand(
                command="",
                args=[],
                raw=message,
                valid=False,
                error="Invalid command format",
            )

        command_name = match.group(1).lower()
        args_str = match.group(2) or ""

        # Resolve alias
        if command_name in self.aliases:
            command_name = self.aliases[command_name]

        # Check if command exists
        if command_name not in self.commands:
            return ParsedCommand(
                command=command_name,
                args=[],
                raw=message,
                valid=False,
                error=f"Unknown command: /{command_name}",
            )

        # Parse arguments
        args = self._parse_args(args_str)
        cmd_def = self.commands[command_name]

        # Validate argument count
        if len(args) < cmd_def.args:
            return ParsedCommand(
                command=command_name,
                args=args,
                raw=message,
                valid=False,
                error=f"Missing argument: {cmd_def.arg_names[len(args)] if cmd_def.arg_names else 'argument'}",
            )

        return ParsedCommand(
            command=command_name,
            args=args,
            raw=message,
            valid=True,
        )

    def _parse_args(self, args_str: str) -> list[str]:
        """Parse arguments from string, handling quoted strings."""
        if not args_str.strip():
            return []

        args = []

        # First extract quoted strings
        quoted_matches = self.QUOTED_ARG_PATTERN.findall(args_str)
        remaining = self.QUOTED_ARG_PATTERN.sub("", args_str)

        # Add quoted args
        args.extend(quoted_matches)

        # Split remaining by whitespace
        unquoted_args = remaining.split()
        args.extend(unquoted_args)

        return args

    def get_help(self, command: str | None = None) -> str:
        """
        Get help text for commands.

        Args:
            command: Specific command to get help for, or None for all

        Returns:
            Help text
        """
        if command:
            cmd = command.lstrip("/").lower()
            if cmd in self.aliases:
                cmd = self.aliases[cmd]

            if cmd not in self.commands:
                return f"Unknown command: /{command}"

            cmd_def = self.commands[cmd]
            args_str = " ".join(f"<{arg}>" for arg in cmd_def.arg_names) if cmd_def.arg_names else ""
            aliases_str = f" (aliases: {', '.join('/' + a for a in cmd_def.aliases)})" if cmd_def.aliases else ""

            return f"/{cmd} {args_str}\n{cmd_def.description}{aliases_str}"

        # All commands
        lines = ["**Available Commands:**", ""]
        for cmd_name, cmd_def in sorted(self.commands.items()):
            args_str = " ".join(f"<{arg}>" for arg in cmd_def.arg_names) if cmd_def.arg_names else ""
            lines.append(f"- `/{cmd_name}{' ' + args_str if args_str else ''}` - {cmd_def.description}")

        return "\n".join(lines)

    def is_command(self, message: str) -> bool:
        """Check if a message is a command."""
        return message.strip().startswith("/")


# =============================================================================
# Singleton
# =============================================================================

command_parser = CommandParser()
