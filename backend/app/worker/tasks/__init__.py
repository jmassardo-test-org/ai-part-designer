"""
Worker tasks package.

Exports all Celery tasks for CAD generation, AI processing, exports, and extraction.
"""

from app.worker.tasks.cad import (
    generate_from_template,
    generate_from_description_task,
    generate_thumbnail,
)
from app.worker.tasks.cad_v2 import (
    compile_enclosure_v2,
    generate_from_description_v2,
)
from app.worker.tasks.ai import (
    moderate_content,
    generate_from_prompt,
    suggest_modifications,
)
from app.worker.tasks.export import (
    convert_format,
    batch_export,
    generate_print_file,
)
from app.worker.tasks.extraction import (
    extract_component_task,
    batch_extract_task,
)

__all__ = [
    # CAD tasks
    "generate_from_template",
    "generate_from_description_task",
    "generate_thumbnail",
    # CAD v2 tasks
    "compile_enclosure_v2",
    "generate_from_description_v2",
    # AI tasks
    "moderate_content",
    "generate_from_prompt",
    "suggest_modifications",
    # Export tasks
    "convert_format",
    "batch_export",
    "generate_print_file",
    # Extraction tasks
    "extract_component_task",
    "batch_extract_task",
]
