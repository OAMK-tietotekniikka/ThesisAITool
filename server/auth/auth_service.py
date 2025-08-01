"""
Authentication service for ThesisAI Tool.

This module contains all authentication-related functions and utilities.
"""

import jwt
from jwt import PyJWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional

from core.models import User
from database.database import user_repo
from config.config import config

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def get_user(username: str) -> Optional[dict]:
    """Get user by username"""
    return user_repo.get_user_by_username(username)

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    user_dict = get_user(username)
    if not user_dict:
        return None
    if not verify_password(password, user_dict['hashed_password']):
        return None
    return User(**user_dict)

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    
    user_dict = get_user(username)
    if user_dict is None:
        raise credentials_exception
    return User(**user_dict)

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_student_name(student_id: str) -> str:
    """Get student name by ID"""
    student_dict = user_repo.get_user_by_id(student_id)
    if student_dict and student_dict['role'] == "student":
        return student_dict['full_name']
    else:
        raise HTTPException(status_code=404, detail="Student not found")

def check_admin(user: User) -> None:
    """Check if user has admin privileges"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

def check_supervisor(user: User) -> None:
    """Check if user has supervisor privileges"""
    if user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor privileges required")

def check_student(user: User) -> None:
    """Check if user has student privileges"""
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student privileges required") 