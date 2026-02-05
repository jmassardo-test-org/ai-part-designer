"""
AI integration package.

Provides Claude (Anthropic) client, prompt templates, and natural language parsing
for converting user descriptions into CAD parameters.
"""

from app.ai.client import ClaudeClient, get_ai_client
from app.ai.exceptions import (
    AIConnectionError,
    AIError,
    AIParseError,
    AIRateLimitError,
    AITimeoutError,
    AIValidationError,
)
from app.ai.generator import GenerationResult, generate_from_description
from app.ai.parser import (
    CADParameters,
    DescriptionParser,
    ParseResult,
    parse_description,
)
from app.ai.prompts import DIMENSION_EXTRACTION_PROMPT, PromptTemplate

__all__ = [
    "DIMENSION_EXTRACTION_PROMPT",
    "AIConnectionError",
    # Exceptions
    "AIError",
    "AIParseError",
    "AIRateLimitError",
    "AITimeoutError",
    "AIValidationError",
    # Parser
    "CADParameters",
    # Client
    "ClaudeClient",
    "DescriptionParser",
    "GenerationResult",
    "ParseResult",
    # Prompts
    "PromptTemplate",
    # Generator
    "generate_from_description",
    "get_ai_client",
    "parse_description",
]
