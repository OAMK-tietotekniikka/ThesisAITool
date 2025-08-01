"""
Authentication routes for ThesisAI Tool.

This module contains all authentication-related API endpoints.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr

from auth.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
    check_admin
)
from core.models import User
from database.database import user_repo

router = APIRouter()

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint to get access token"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "supervisor_id": user.supervisor_id,
            "assigned_students": user.assigned_students
        }
    }

@router.post("/register")
async def register(
    username: str = Form(...),
    email: EmailStr = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    supervisor_id: str = Form(None),
):
    """Register a new user"""
    # Check if user already exists
    existing_user = user_repo.get_user_by_username(username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email already exists
    existing_email = user_repo.get_user_by_email(email)
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate role
    if role not in ["student", "supervisor", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Create new user
    hashed_password = get_password_hash(password)
    user_data = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "hashed_password": hashed_password,
        "role": role,
        "supervisor_id": supervisor_id,
        "assigned_students": []
    }
    
    user_id = user_repo.create_user(user_data)
    
    return {
        "message": "User registered successfully",
        "user_id": user_id,
        "username": username,
        "role": role
    }

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "supervisor_id": current_user.supervisor_id,
        "assigned_students": current_user.assigned_students
    } 