"""
Worker tasks package.

Exports all Celery tasks for CAD generation, AI processing, exports, and extraction.
"""

from app.worker.tasks.ai import (
    generate_from_prompt,
    moderate_content,
    suggest_modifications,
)
from app.worker.tasks.cad import (
    generate_from_description_task,
    generate_from_template,
    generate_thumbnail,
)
from app.worker.tasks.cad_v2 import (
    compile_enclosure_v2,
    generate_from_description_v2,
)
from app.worker.tasks.export import (
    batch_export,
    convert_format,
    generate_print_file,
)
from app.worker.tasks.extraction import (
    batch_extract_task,
    extract_component_task,
)
from app.worker.tasks.maintenance import (
    archive_old_audit_logs,
    backup_database,
    check_data_integrity,
    check_stale_jobs,
    cleanup_old_jobs,
    cleanup_temp_files,
    purge_expired_trash,
    send_trash_deletion_warnings,
    verify_backups,
)

__all__ = [
    # Maintenance tasks
    "archive_old_audit_logs",
    "backup_database",
    "batch_export",
    "batch_extract_task",
    "check_data_integrity",
    "check_stale_jobs",
    "cleanup_old_jobs",
    "cleanup_temp_files",
    # CAD v2 tasks
    "compile_enclosure_v2",
    # Export tasks
    "convert_format",
    # Extraction tasks
    "extract_component_task",
    "generate_from_description_task",
    "generate_from_description_v2",
    "generate_from_prompt",
    # CAD tasks
    "generate_from_template",
    "generate_print_file",
    "generate_thumbnail",
    # AI tasks
    "moderate_content",
    "purge_expired_trash",
    "send_trash_deletion_warnings",
    "suggest_modifications",
    "verify_backups",
]
