"""
Command handlers for slash commands.

Implements the business logic for each slash command.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.ai.commands import ParsedCommand, command_parser

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models import Conversation, Design, User


logger = logging.getLogger(__name__)


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class CommandResult:
    """Result of executing a command."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    show_in_chat: bool = True


# =============================================================================
# Command Handler
# =============================================================================


class CommandHandler:
    """
    Handles execution of parsed slash commands.

    Each command has a dedicated handler method:
    handle_{command_name}
    """

    def __init__(self):
        self.parser = command_parser

    async def handle(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None = None,
        design: Design | None = None,
    ) -> CommandResult:
        """
        Execute a parsed command.

        Args:
            command: Parsed command to execute
            user: Current user
            db: Database session
            conversation: Optional current conversation
            design: Optional current design

        Returns:
            CommandResult with status and message
        """
        if not command.valid:
            return CommandResult(
                success=False,
                message=command.error or "Invalid command",
            )

        handler = getattr(self, f"handle_{command.command}", None)
        if not handler:
            return CommandResult(
                success=False,
                message=f"Unknown command: /{command.command}",
            )

        try:
            return await handler(command, user, db, conversation, design)
        except Exception as e:
            logger.exception(f"Error executing command /{command.command}")
            return CommandResult(
                success=False,
                message=f"Error executing command: {e!s}",
            )

    # =========================================================================
    # Design Management Commands
    # =========================================================================

    async def handle_save(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Save the current design."""
        if not design:
            return CommandResult(
                success=False,
                message="No design to save. Create a design first.",
            )

        # Design is already saved, just update
        from app.repositories import DesignRepository

        repo = DesignRepository(db)
        design.updated_at = datetime.utcnow()
        await repo.update(design.id, updated_at=design.updated_at)
        await db.commit()

        return CommandResult(
            success=True,
            message=f"✅ Design '{design.name}' saved!",
            data={"design_id": str(design.id)},
        )

    async def handle_saveas(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Save design with a new name."""
        if not design:
            return CommandResult(
                success=False,
                message="No design to save. Create a design first.",
            )

        new_name = command.get_arg(0)
        if not new_name:
            return CommandResult(
                success=False,
                message="Please provide a name: `/saveas <name>`",
            )

        from app.repositories import DesignRepository

        repo = DesignRepository(db)

        # Create a copy with new name
        new_design = await repo.create(
            name=new_name,
            user_id=user.id,
            project_id=design.project_id,
            description=design.description,
            cadquery_script=design.cadquery_script,
            parameters=design.parameters,
            file_url=design.file_url,
        )
        await db.commit()

        return CommandResult(
            success=True,
            message=f"✅ Design saved as '{new_name}'!",
            data={"design_id": str(new_design.id)},
        )

    async def handle_rename(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Rename the current design."""
        if not design:
            return CommandResult(
                success=False,
                message="No design to rename. Create a design first.",
            )

        new_name = command.get_arg(0)
        if not new_name:
            return CommandResult(
                success=False,
                message="Please provide a name: `/rename <name>`",
            )

        from app.repositories import DesignRepository

        repo = DesignRepository(db)
        old_name = design.name
        await repo.update(design.id, name=new_name)
        await db.commit()

        return CommandResult(
            success=True,
            message=f"✅ Design renamed from '{old_name}' to '{new_name}'!",
            data={"design_id": str(design.id), "name": new_name},
        )

    async def handle_delete(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Delete the current design (soft delete)."""
        if not design:
            return CommandResult(
                success=False,
                message="No design to delete.",
            )

        from app.repositories import DesignRepository

        repo = DesignRepository(db)
        await repo.soft_delete(design.id)
        await db.commit()

        return CommandResult(
            success=True,
            message=f"🗑️ Design '{design.name}' moved to trash.",
            data={"design_id": str(design.id)},
        )

    # =========================================================================
    # Export Commands
    # =========================================================================

    async def handle_export(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Export design to specified format."""
        if not design:
            return CommandResult(
                success=False,
                message="No design to export. Create a design first.",
            )

        format_arg = command.get_arg(0, "step").lower()
        supported_formats = ["step", "stl", "obj", "gltf", "dxf"]

        if format_arg not in supported_formats:
            return CommandResult(
                success=False,
                message=f"Unsupported format '{format_arg}'. Supported: {', '.join(supported_formats)}",
            )

        # Trigger export job
        from app.worker.tasks.export import export_design

        job = export_design.delay(
            design_id=str(design.id),
            format=format_arg,
            user_id=str(user.id),
        )

        return CommandResult(
            success=True,
            message=f"📦 Exporting design to {format_arg.upper()}. You'll be notified when ready.",
            data={
                "job_id": str(job.id),
                "format": format_arg,
                "design_id": str(design.id),
            },
        )

    async def handle_exportall(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Export all designs in the project."""
        if not design or not design.project_id:
            return CommandResult(
                success=False,
                message="No project context. Open a project first.",
            )

        format_arg = command.get_arg(0, "step").lower()

        # TODO: Trigger batch export
        return CommandResult(
            success=True,
            message=f"📦 Exporting all project designs to {format_arg.upper()}...",
            data={"project_id": str(design.project_id), "format": format_arg},
        )

    # =========================================================================
    # Template Commands
    # =========================================================================

    async def handle_maketemplate(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Save current design as a template."""
        if not design:
            return CommandResult(
                success=False,
                message="No design to template. Create a design first.",
            )

        if not design.cadquery_script:
            return CommandResult(
                success=False,
                message="Design has no CAD script to template.",
            )

        from app.repositories import TemplateRepository

        repo = TemplateRepository(db)

        template = await repo.create(
            name=f"{design.name} Template",
            description=design.description or f"Template from {design.name}",
            category="custom",
            cadquery_script=design.cadquery_script,
            parameters=design.parameters or {},
            created_by=user.id,
            is_public=False,
        )
        await db.commit()

        return CommandResult(
            success=True,
            message=f"📋 Template '{template.name}' created!",
            data={"template_id": str(template.id)},
        )

    # =========================================================================
    # History Commands
    # =========================================================================

    async def handle_undo(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Undo last modification."""
        if not design:
            return CommandResult(
                success=False,
                message="No design to undo changes on.",
            )

        from app.repositories import VersionRepository

        repo = VersionRepository(db)
        versions = await repo.list_for_design(design.id, limit=2)

        if len(versions) < 2:
            return CommandResult(
                success=False,
                message="No previous version to restore.",
            )

        # Restore previous version
        prev_version = versions[1]
        from app.repositories import DesignRepository

        design_repo = DesignRepository(db)
        await design_repo.update(
            design.id,
            cadquery_script=prev_version.cadquery_script,
            parameters=prev_version.parameters,
        )
        await db.commit()

        return CommandResult(
            success=True,
            message=f"↩️ Restored to version {prev_version.version_number}.",
            data={"version": prev_version.version_number},
        )

    async def handle_redo(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Redo last undone modification."""
        # TODO: Implement redo stack
        return CommandResult(
            success=False,
            message="Redo is not yet implemented.",
        )

    async def handle_history(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Show version history."""
        if not design:
            return CommandResult(
                success=False,
                message="No design to show history for.",
            )

        from app.repositories import VersionRepository

        repo = VersionRepository(db)
        versions = await repo.list_for_design(design.id, limit=10)

        if not versions:
            return CommandResult(
                success=True,
                message="No version history available.",
            )

        history_lines = ["**Version History:**"]
        for v in versions:
            history_lines.append(
                f"- v{v.version_number}: {v.description or 'No description'} "
                f"({v.created_at.strftime('%Y-%m-%d %H:%M')})"
            )

        return CommandResult(
            success=True,
            message="\n".join(history_lines),
            data={"versions": [str(v.id) for v in versions]},
        )

    async def handle_restore(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Restore to a specific version."""
        if not design:
            return CommandResult(
                success=False,
                message="No design to restore.",
            )

        version_num = command.get_arg(0)
        if not version_num:
            return CommandResult(
                success=False,
                message="Please specify version number: `/restore <version>`",
            )

        try:
            version_number = int(version_num)
        except ValueError:
            return CommandResult(
                success=False,
                message="Invalid version number.",
            )

        from app.repositories import VersionRepository

        repo = VersionRepository(db)
        version = await repo.get_by_design_and_number(design.id, version_number)

        if not version:
            return CommandResult(
                success=False,
                message=f"Version {version_number} not found.",
            )

        from app.repositories import DesignRepository

        design_repo = DesignRepository(db)
        await design_repo.update(
            design.id,
            cadquery_script=version.cadquery_script,
            parameters=version.parameters,
        )
        await db.commit()

        return CommandResult(
            success=True,
            message=f"✅ Restored to version {version_number}.",
            data={"version": version_number},
        )

    # =========================================================================
    # View Commands
    # =========================================================================

    async def handle_view(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Switch view mode."""
        mode = command.get_arg(0, "").lower()
        valid_modes = ["top", "front", "side", "iso", "isometric"]

        if mode not in valid_modes:
            return CommandResult(
                success=False,
                message=f"Invalid view mode. Options: {', '.join(valid_modes)}",
            )

        # View changes happen on frontend
        return CommandResult(
            success=True,
            message=f"📐 Switched to {mode} view.",
            data={"view_mode": mode},
        )

    async def handle_zoom(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Zoom to level."""
        level = command.get_arg(0, "fit").lower()

        if level == "fit":
            return CommandResult(
                success=True,
                message="🔍 Zoom to fit.",
                data={"zoom": "fit"},
            )

        try:
            zoom_percent = int(level.replace("%", ""))
            if zoom_percent < 10 or zoom_percent > 500:
                raise ValueError("Out of range")

            return CommandResult(
                success=True,
                message=f"🔍 Zoom set to {zoom_percent}%.",
                data={"zoom": zoom_percent},
            )
        except ValueError:
            return CommandResult(
                success=False,
                message="Invalid zoom level. Use 'fit' or a percentage (10-500).",
            )

    async def handle_measure(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Enable measurement tool."""
        return CommandResult(
            success=True,
            message="📏 Measurement tool enabled. Click on surfaces to measure.",
            data={"tool": "measure"},
        )

    # =========================================================================
    # Help Commands
    # =========================================================================

    async def handle_help(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Show available commands."""
        help_text = self.parser.get_help()
        return CommandResult(
            success=True,
            message=help_text,
        )

    # =========================================================================
    # Debug/Dev Commands
    # =========================================================================

    async def handle_debug(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Show debug information."""
        debug_info = {
            "user_id": str(user.id),
            "user_email": user.email,
            "conversation_id": str(conversation.id) if conversation else None,
            "design_id": str(design.id) if design else None,
            "design_name": design.name if design else None,
        }

        lines = ["**Debug Info:**"]
        for key, value in debug_info.items():
            lines.append(f"- {key}: `{value}`")

        return CommandResult(
            success=True,
            message="\n".join(lines),
            data=debug_info,
        )

    async def handle_clear(
        self,
        command: ParsedCommand,
        user: User,
        db: AsyncSession,
        conversation: Conversation | None,
        design: Design | None,
    ) -> CommandResult:
        """Clear conversation history."""
        if not conversation:
            return CommandResult(
                success=False,
                message="No active conversation to clear.",
            )

        # This signals frontend to clear local messages
        return CommandResult(
            success=True,
            message="🗑️ Conversation cleared.",
            data={"action": "clear_conversation", "conversation_id": str(conversation.id)},
        )


# =============================================================================
# Singleton Instance
# =============================================================================

command_handler = CommandHandler()
