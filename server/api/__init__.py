"""
API package for ThesisAI Tool.

This package contains all API-related modules including routes and middleware.
"""

from .routes import auth_routes, thesis_routes, ai_routes, user_routes

__all__ = [
    'auth_routes',
    'thesis_routes', 
    'ai_routes',
    'user_routes'
] 