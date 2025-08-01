"""
Thesis routes for ThesisAI Tool.

This module contains all thesis-related API endpoints.
"""

import os
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse

from auth.auth_service import get_current_active_user, check_student, check_supervisor
from core.models import User, Thesis
from database.database import thesis_repo, user_repo
from file_processing.text_extractor import extract_text_from_file
from file_processing.image_converter import convert_document_to_images

router = APIRouter()

@router.post("/upload")
async def upload_thesis(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a thesis file"""
    check_student(current_user)
    
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    # Create upload directory if it doesn't exist
    upload_dir = "thesis_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Create thesis record
    thesis_data = {
        "student_id": current_user.id,
        "filename": file.filename,
        "filepath": file_path,
        "upload_date": datetime.now(),
        "status": "pending"
    }
    
    thesis_id = thesis_repo.create_thesis(thesis_data)
    
    return {
        "message": "Thesis uploaded successfully",
        "thesis_id": thesis_id,
        "filename": file.filename,
        "status": "pending"
    }

@router.get("/my-theses")
async def get_my_theses(current_user: User = Depends(get_current_active_user)):
    """Get theses for current user"""
    if current_user.role == "student":
        theses = thesis_repo.get_theses_by_student(current_user.id)
    elif current_user.role == "supervisor":
        theses = thesis_repo.get_theses_by_supervisor(current_user.id)
    else:  # admin
        theses = thesis_repo.get_all_theses()
    
    # Add student names to theses
    for thesis in theses:
        student = user_repo.get_user_by_id(thesis['student_id'])
        thesis['student_name'] = student['full_name'] if student else "Unknown"
    
    return theses

@router.get("/download/{thesis_id}")
async def download_thesis(
    thesis_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Download a thesis file"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    # Check permissions
    if current_user.role == "student" and thesis['student_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=thesis['filepath'],
        filename=thesis['filename'],
        media_type='application/octet-stream'
    )

@router.get("/preview-images/{thesis_id}")
async def get_thesis_preview_images(
    thesis_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get preview images for a thesis"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    # Check permissions
    if current_user.role == "student" and thesis['student_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        images = convert_document_to_images(thesis['filepath'])
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")

@router.get("/extract-text/{thesis_id}")
async def extract_thesis_text(
    thesis_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Extract text from a thesis file"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    # Check permissions
    if current_user.role == "student" and thesis['student_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        text = extract_text_from_file(thesis['filepath'])
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")

@router.get("/to-review")
async def get_theses_to_review(current_user: User = Depends(get_current_active_user)):
    """Get theses that need supervisor review"""
    check_supervisor(current_user)
    
    theses = thesis_repo.get_theses_by_supervisor(current_user.id)
    
    # Add student names and filter for pending review
    reviewed_theses = []
    for thesis in theses:
        if thesis['status'] == 'pending' or thesis['status'] == 'reviewed_by_ai':
            student = user_repo.get_user_by_id(thesis['student_id'])
            thesis['student_name'] = student['full_name'] if student else "Unknown"
            reviewed_theses.append(thesis)
    
    return reviewed_theses

@router.get("/all")
async def get_all_theses(current_user: User = Depends(get_current_active_user)):
    """Get all theses (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    theses = thesis_repo.get_all_theses()
    
    # Add student names
    for thesis in theses:
        student = user_repo.get_user_by_id(thesis['student_id'])
        thesis['student_name'] = student['full_name'] if student else "Unknown"
    
    return theses 