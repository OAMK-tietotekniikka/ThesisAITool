"""
User model for the ThesisAI Tool.

This module defines the User data model used throughout the application.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

class User(BaseModel):
    """User model representing a user in the system"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: EmailStr
    full_name: str
    hashed_password: str
    role: str  # "student", "supervisor", or "admin"
    disabled: bool = False
    supervisor_id: Optional[str] = None  # For students
    assigned_students: List[str] = []  # For supervisors 