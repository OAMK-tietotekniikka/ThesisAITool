"""
AI Request model for ThesisAI Tool.

This module defines the AIRequest data model used for AI analysis requests.
"""

from typing import List, Optional
from pydantic import BaseModel
from ai.providers.ai_provider import AIProvider

class AIRequest(BaseModel):
    """AI Request model representing an AI analysis request"""
    thesis_id: str
    custom_instructions: str
    predefined_questions: List[str]
    provider: AIProvider = None  # Will use active provider if None
    model: Optional[str] = None 