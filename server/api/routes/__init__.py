"""
Routes package for ThesisAI Tool.

This package contains all API route modules.
"""

from .auth_routes import router as auth_router
from .thesis_routes import router as thesis_router
from .ai_routes import router as ai_router
from .user_routes import router as user_router

__all__ = [
    'auth_router',
    'thesis_router',
    'ai_router', 
    'user_router'
] 