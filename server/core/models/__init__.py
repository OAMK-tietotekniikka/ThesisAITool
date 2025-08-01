"""
Models package for ThesisAI Tool.

This package contains all the data models used throughout the application.
"""

from .user import User
from .thesis import Thesis
from .feedback import Feedback
from .ai_request import AIRequest
from ai.providers.ai_provider import AIProvider

__all__ = [
    'User',
    'Thesis', 
    'Feedback',
    'AIRequest',
    'AIProvider'
] 