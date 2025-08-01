"""
Feedback model for the ThesisAI Tool.

This module defines the Feedback data model used throughout the application.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class Feedback(BaseModel):
    """Feedback model representing feedback on a thesis"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thesis_id: str
    reviewer_id: str  # AI or supervisor ID
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    is_ai_feedback: bool 