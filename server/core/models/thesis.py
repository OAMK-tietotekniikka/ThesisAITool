"""
Thesis model for the ThesisAI Tool.

This module defines the Thesis data model used throughout the application.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Thesis(BaseModel):
    """Thesis model representing a thesis document in the system"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    filename: str
    filepath: str
    upload_date: datetime = Field(default_factory=datetime.now)
    status: str = "pending"  # pending, reviewed_by_ai, reviewed_by_supervisor, approved
    ai_feedback_id: Optional[str] = None
    supervisor_feedback_id: Optional[str] = None 