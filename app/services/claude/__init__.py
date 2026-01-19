"""Claude AI services.

This package provides:
- Async Claude API client with retry logic
- Spell generation service
- Default prompt templates for different spell types
"""

from app.services.claude.client import (
    ClaudeClient,
    ClaudeAPIError,
    get_claude_client,
)
from app.services.claude.generator import (
    SpellGenerator,
    SpellGenerationError,
    generate_spell_for_order,
    regenerate_spell,
)
from app.services.claude.prompts import (
    SYSTEM_PROMPT,
    DEFAULT_PROMPT_TEMPLATE,
    get_template_for_spell_type,
    TEMPLATE_VARIABLES,
)

__all__ = [
    # Client
    "ClaudeClient",
    "ClaudeAPIError",
    "get_claude_client",
    # Generator
    "SpellGenerator",
    "SpellGenerationError",
    "generate_spell_for_order",
    "regenerate_spell",
    # Prompts
    "SYSTEM_PROMPT",
    "DEFAULT_PROMPT_TEMPLATE",
    "get_template_for_spell_type",
    "TEMPLATE_VARIABLES",
]
