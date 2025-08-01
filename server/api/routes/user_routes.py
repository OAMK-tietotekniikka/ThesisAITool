"""
User routes for ThesisAI Tool.

This module contains all user management API endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException

from auth.auth_service import get_current_active_user, check_admin, check_supervisor
from core.models import User
from database.database import user_repo, thesis_repo, feedback_repo

router = APIRouter()

@router.get("/supervisors")
async def get_supervisors(current_user: User = Depends(get_current_active_user)):
    """Get all supervisors"""
    return user_repo.get_users_by_role("supervisor")

@router.get("/students")
async def get_students(current_user: User = Depends(get_current_active_user)):
    """Get all students"""
    if current_user.role == "supervisor":
        # Supervisors can only see their assigned students
        return user_repo.get_assigned_students(current_user.id)
    else:
        # Admins can see all students
        return user_repo.get_users_by_role("student")

@router.get("/supervisor-assignments")
async def get_supervisor_assignments(current_user: User = Depends(get_current_active_user)):
    """Get supervisor-student assignments"""
    check_supervisor(current_user)
    
    assignments = []
    assigned_students = user_repo.get_assigned_students(current_user.id)
    
    for student in assigned_students:
        # Get theses for this student
        theses = thesis_repo.get_theses_by_student(student['id'])
        assignments.append({
            "supervisor_id": current_user.id,
            "supervisor_name": current_user.full_name,
            "student_id": student['id'],
            "student_name": student['full_name'],
            "theses": theses
        })
    
    return assignments

@router.post("/assign-supervisor")
async def assign_supervisor(
    student_username: str = Form(...),
    supervisor_username: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    """Assign a supervisor to a student (admin only)"""
    check_admin(current_user)
    
    # Get student and supervisor
    student = user_repo.get_user_by_username(student_username)
    supervisor = user_repo.get_user_by_username(supervisor_username)
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    if student['role'] != "student":
        raise HTTPException(status_code=400, detail="User is not a student")
    if supervisor['role'] != "supervisor":
        raise HTTPException(status_code=400, detail="User is not a supervisor")
    
    # Update student's supervisor
    user_repo.update_user_supervisor(student['id'], supervisor['id'])
    
    # Update supervisor's assigned students
    user_repo.add_assigned_student(supervisor['id'], student['id'])
    
    return {
        "message": "Supervisor assigned successfully",
        "student_id": student['id'],
        "supervisor_id": supervisor['id']
    }

@router.post("/submit-supervisor-feedback")
async def submit_supervisor_feedback(
    thesis_id: str = Form(...),
    feedback_content: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    """Submit supervisor feedback for a thesis"""
    check_supervisor(current_user)
    
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    # Check if supervisor is assigned to this student
    student = user_repo.get_user_by_id(thesis['student_id'])
    if not student or student['supervisor_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to review this thesis")
    
    # Create feedback record
    feedback_data = {
        "thesis_id": thesis_id,
        "reviewer_id": current_user.id,
        "content": feedback_content,
        "is_ai_feedback": False
    }
    
    feedback_id = feedback_repo.create_feedback(feedback_data)
    
    # Update thesis status
    thesis_repo.update_thesis_status(thesis_id, "reviewed_by_supervisor", feedback_id)
    
    return {
        "message": "Supervisor feedback submitted successfully",
        "feedback_id": feedback_id
    }

@router.get("/supervisor-feedback")
async def get_all_supervisor_feedback(current_user: User = Depends(get_current_active_user)):
    """Get all supervisor feedback"""
    check_supervisor(current_user)
    
    feedbacks = feedback_repo.get_feedback_by_reviewer(current_user.id)
    
    # Add thesis and student information
    for feedback in feedbacks:
        thesis = thesis_repo.get_thesis_by_id(feedback['thesis_id'])
        if thesis:
            feedback['thesis'] = thesis
            student = user_repo.get_user_by_id(thesis['student_id'])
            feedback['student_name'] = student['full_name'] if student else "Unknown"
    
    return feedbacks

@router.get("/supervisor-feedback/{thesis_id}")
async def get_supervisor_feedback(
    thesis_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get supervisor feedback for a specific thesis"""
    check_supervisor(current_user)
    
    # Get the thesis
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    # Check if the thesis belongs to a student assigned to this supervisor
    student = user_repo.get_user_by_id(thesis['student_id'])
    if not student or student['supervisor_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this thesis")
    
    # Get supervisor feedback
    feedback = feedback_repo.get_supervisor_feedback_by_thesis_id(thesis_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="No supervisor feedback found")
    
    return feedback

@router.delete("/users/{username}")
async def delete_user(
    username: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a user (admin only)"""
    check_admin(current_user)
    
    # Don't allow admin to delete themselves
    if username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Get the user to delete
    user_to_delete = user_repo.get_user_by_username(username)
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has any theses
    theses = thesis_repo.get_theses_by_student_id(user_to_delete['id'])
    if theses:
        raise HTTPException(status_code=400, detail="Cannot delete user with existing theses")
    
    # Check if user has any feedback
    feedback = feedback_repo.get_feedback_by_reviewer(user_to_delete['id'])
    if feedback:
        raise HTTPException(status_code=400, detail="Cannot delete user with existing feedback")
    
    # Delete the user
    try:
        success = user_repo.delete_user(username)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "message": f"User {username} deleted successfully",
            "deleted_user": {
                "username": user_to_delete['username'],
                "email": user_to_delete['email'],
                "full_name": user_to_delete['full_name'],
                "role": user_to_delete['role']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

@router.get("/users/{username}")
async def get_user(
    username: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get user details (admin only)"""
    check_admin(current_user)
    
    user = user_repo.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.put("/users/{username}")
async def update_user(
    username: str,
    email: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    supervisor_username: str = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Update user details (admin only)"""
    check_admin(current_user)
    
    # Get the user to update
    user_to_update = user_repo.get_user_by_username(username)
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate role
    if role not in ["student", "supervisor", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Update user data
    update_data = {
        "email": email,
        "full_name": full_name,
        "role": role
    }
    
    # Handle supervisor assignment
    if role == "student" and supervisor_username:
        supervisor = user_repo.get_user_by_username(supervisor_username)
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        if supervisor['role'] != "supervisor":
            raise HTTPException(status_code=400, detail="User is not a supervisor")
        update_data["supervisor_id"] = supervisor['id']
    elif role == "student":
        # Remove supervisor assignment if role is student but no supervisor provided
        update_data["supervisor_id"] = None
    
    try:
        success = user_repo.update_user(username, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get updated user data
        updated_user = user_repo.get_user_by_username(username)
        
        return {
            "message": f"User {username} updated successfully",
            "user": updated_user
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@router.get("/users")
async def get_users(current_user: User = Depends(get_current_active_user)):
    """Get all users (admin only)"""
    check_admin(current_user)
    return user_repo.get_all_users() 