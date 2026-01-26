"""
AI integration package.

Provides OpenAI client, prompt templates, and natural language parsing
for converting user descriptions into CAD parameters.
"""

from app.ai.client import OpenAIClient, get_ai_client
from app.ai.prompts import PromptTemplate, DIMENSION_EXTRACTION_PROMPT
from app.ai.parser import (
    CADParameters,
    ParseResult,
    parse_description,
    DescriptionParser,
)
from app.ai.generator import generate_from_description, GenerationResult
from app.ai.exceptions import (
    AIError,
    AIConnectionError,
    AIRateLimitError,
    AIParseError,
    AITimeoutError,
    AIValidationError,
)

__all__ = [
    # Client
    "OpenAIClient",
    "get_ai_client",
    # Prompts
    "PromptTemplate",
    "DIMENSION_EXTRACTION_PROMPT",
    # Parser
    "CADParameters",
    "ParseResult",
    "parse_description",
    "DescriptionParser",
    # Generator
    "generate_from_description",
    "GenerationResult",
    # Exceptions
    "AIError",
    "AIConnectionError",
    "AIRateLimitError",
    "AIParseError",
    "AITimeoutError",
    "AIValidationError",
]
