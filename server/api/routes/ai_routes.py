"""
AI routes for ThesisAI Tool.

This module contains all AI-related API endpoints.
"""

import json
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import StreamingResponse

from auth.auth_service import get_current_active_user
from core.models import User
from database.database import thesis_repo, feedback_repo
from ai.services.unified_ai_model import UnifiedAIModel
from ai.providers.ai_provider import AIProvider

router = APIRouter()

# Initialize AI model
ai_model = UnifiedAIModel()

@router.post("/feedback")
async def request_ai_feedback(
    thesis_id: str = Form(...),
    custom_instructions: str = Form(""),
    predefined_questions: List[str] = Form([]),
    selected_options: str = Form(""),
    current_user: User = Depends(get_current_active_user)
):
    """Request AI feedback for a thesis"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    # Check permissions
    if current_user.role == "student" and thesis['student_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_feedback():
        try:
            async for chunk in ai_model.analyze_thesis_stream(
                thesis['filepath'], 
                custom_instructions, 
                predefined_questions
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error generating AI feedback: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_feedback(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/feedback-enhanced")
async def request_ai_feedback_enhanced(
    thesis_id: str = Form(...),
    custom_instructions: str = Form("Please review this thesis and provide feedback"),
    predefined_questions: List[str] = Form(["What are the strengths?", "What areas need improvement?"]),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    pacing_delay: float = Form(0.01),
    current_user: User = Depends(get_current_active_user)
):
    """Request enhanced AI feedback with provider selection"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    # Check permissions
    if current_user.role == "student" and thesis['student_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_feedback():
        try:
            async for chunk in ai_model.analyze_thesis_stream(
                thesis['filepath'], 
                custom_instructions, 
                predefined_questions,
                provider,
                model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error generating AI feedback: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_feedback(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/grade-formatting")
async def grade_formatting_style(
    thesis_id: str = Form(...),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Grade formatting and style aspects"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_grading():
        try:
            async for chunk in ai_model.grade_formatting_style(
                thesis['filepath'], provider, model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error grading formatting: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_grading(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/grade-purpose-objectives")
async def grade_purpose_objectives(
    thesis_id: str = Form(...),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Grade purpose and objectives"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_grading():
        try:
            async for chunk in ai_model.grade_purpose_objectives(
                thesis['filepath'], provider, model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error grading purpose: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_grading(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/grade-theoretical-foundation")
async def grade_theoretical_foundation(
    thesis_id: str = Form(...),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Grade theoretical foundation"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_grading():
        try:
            async for chunk in ai_model.grade_theoretical_foundation(
                thesis['filepath'], provider, model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error grading theoretical foundation: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_grading(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/grade-professional-connection")
async def grade_professional_connection(
    thesis_id: str = Form(...),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Grade professional connection"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_grading():
        try:
            async for chunk in ai_model.grade_professional_connection(
                thesis['filepath'], provider, model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error grading professional connection: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_grading(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/grade-development-task")
async def grade_development_task(
    thesis_id: str = Form(...),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Grade development task"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_grading():
        try:
            async for chunk in ai_model.grade_development_task(
                thesis['filepath'], provider, model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error grading development task: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_grading(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/grade-conclusions-proposals")
async def grade_conclusions_proposals(
    thesis_id: str = Form(...),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Grade conclusions and proposals"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_grading():
        try:
            async for chunk in ai_model.grade_conclusions_proposals(
                thesis['filepath'], provider, model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error grading conclusions: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_grading(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/grade-material-methodology")
async def grade_material_methodology(
    thesis_id: str = Form(...),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Grade material and methodology"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_grading():
        try:
            async for chunk in ai_model.grade_material_methodology(
                thesis['filepath'], provider, model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error grading material methodology: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_grading(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/grade-treatment-analysis")
async def grade_treatment_analysis(
    thesis_id: str = Form(...),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Grade treatment and analysis"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_grading():
        try:
            async for chunk in ai_model.grade_treatment_analysis(
                thesis['filepath'], provider, model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error grading treatment analysis: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_grading(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/grade-results-product")
async def grade_results_product(
    thesis_id: str = Form(...),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Grade results and product"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if not os.path.exists(thesis['filepath']):
        raise HTTPException(status_code=404, detail="File not found")
    
    async def stream_grading():
        try:
            async for chunk in ai_model.grade_results_product(
                thesis['filepath'], provider, model
            ):
                yield chunk
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'content': f'Error grading results product: {str(e)}'
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        stream_grading(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/save-feedback")
async def save_ai_feedback(
    thesis_id: str = Form(...),
    feedback_content: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    """Save AI feedback to database"""
    thesis = thesis_repo.get_thesis_by_id(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    # Check permissions
    if current_user.role == "student" and thesis['student_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Create feedback record
    feedback_data = {
        "thesis_id": thesis_id,
        "reviewer_id": current_user.id,
        "content": feedback_content,
        "is_ai_feedback": True
    }
    
    feedback = feedback_repo.create_feedback(feedback_data)
    
    # Update thesis status
    thesis_repo.update_thesis_status(thesis_id, "reviewed_by_ai", feedback['id'])
    
    return {
        "message": "AI feedback saved successfully",
        "feedback_id": feedback['id']
    }

@router.get("/feedback-options")
async def get_ai_feedback_options(current_user: User = Depends(get_current_active_user)):
    """Get available AI feedback options"""
    options = [
        {
            "id": "strengths",
            "label": "Strengths Analysis",
            "description": "Identify and analyze the strengths of the thesis",
            "enabled": True,
            "default": True
        },
        {
            "id": "improvements",
            "label": "Areas for Improvement",
            "description": "Identify areas that need improvement",
            "enabled": True,
            "default": True
        },
        {
            "id": "methodology",
            "label": "Research Methodology",
            "description": "Evaluate the research methodology and approach",
            "enabled": True,
            "default": True
        },
        {
            "id": "references",
            "label": "References and Citations",
            "description": "Check references and citations format (Harvard style)",
            "enabled": True,
            "default": True
        },
        {
            "id": "theoretical_framework",
            "label": "Theoretical Framework",
            "description": "Evaluate the theoretical foundation and literature review",
            "enabled": True,
            "default": True
        },
        {
            "id": "structure",
            "label": "Structure and Organization",
            "description": "Assess the structure and organization of the thesis",
            "enabled": True,
            "default": True
        },
        {
            "id": "writing_quality",
            "label": "Writing Quality",
            "description": "Evaluate the overall writing quality and clarity",
            "enabled": True,
            "default": True
        },
        {
            "id": "practical_relevance",
            "label": "Practical Relevance",
            "description": "Assess the practical relevance and real-world impact",
            "enabled": True,
            "default": True
        },
        {
            "id": "objectives",
            "label": "Research Objectives",
            "description": "Evaluate the clarity and feasibility of research objectives",
            "enabled": True,
            "default": True
        },
        {
            "id": "conclusions",
            "label": "Conclusions and Recommendations",
            "description": "Assess the strength of conclusions and recommendations",
            "enabled": True,
            "default": True
        }
    ]
    
    return {
        "options": options,
        "total_count": len(options),
        "enabled_count": len([opt for opt in options if opt["enabled"]])
    } 