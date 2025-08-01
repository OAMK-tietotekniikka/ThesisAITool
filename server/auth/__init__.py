"""
Authentication package for ThesisAI Tool.

This package contains all authentication-related modules.
"""

from .auth_service import (
    verify_password,
    get_password_hash,
    get_user,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_active_user,
    check_admin,
    check_supervisor,
    check_student
)

__all__ = [
    'verify_password',
    'get_password_hash', 
    'get_user',
    'authenticate_user',
    'create_access_token',
    'get_current_user',
    'get_current_active_user',
    'check_admin',
    'check_supervisor',
    'check_student'
] 