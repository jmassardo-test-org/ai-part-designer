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

__all__ = [
    "batch_export",
    "batch_extract_task",
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
    "suggest_modifications",
]
