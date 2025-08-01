"""
AI Provider enumeration for the ThesisAI Tool.

This module defines the available AI providers that can be used for thesis analysis.
"""

from enum import Enum

class AIProvider(str, Enum):
    """Enumeration of available AI providers"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter" 