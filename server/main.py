"""
Main application file for ThesisAI Tool.

This is the entry point for the FastAPI application with all routes and middleware configured.
"""

import asyncio
import traceback
import logging
import sys
import os

# Add the server directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Import our refactored modules using absolute imports
from config.config import config
from database.database import user_repo, thesis_repo, feedback_repo
from ai.services.unified_ai_model import UnifiedAIModel
from auth.auth_service import get_current_active_user, check_student
from core.models import User, Thesis, Feedback, AIRequest
from ai.providers.ai_provider import AIProvider
from file_processing.text_extractor import extract_text_from_file
from file_processing.image_converter import convert_document_to_images

# Import routes
from api.routes.auth_routes import router as auth_router
from api.routes.thesis_routes import router as thesis_router
from api.routes.ai_routes import router as ai_router
from api.routes.user_routes import router as user_router

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pdfminer").setLevel(logging.WARNING)

# Initialize FastAPI
app = FastAPI(
    title="ThesisAI API",
    description="API for ThesisAI application with student, supervisor, and admin roles",
    version="1.0.0",
    debug=config.DEBUG,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files from client directory
import os
client_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client")
app.mount("/web", StaticFiles(directory=client_path), name="web")

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(thesis_router, prefix="/thesis", tags=["thesis"])
app.include_router(ai_router, prefix="/ai", tags=["ai"])
app.include_router(user_router, prefix="/users", tags=["users"])

# Initialize the unified AI model
ai_model = UnifiedAIModel()

# Root route
@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("./_baocao/index.html", encoding='utf8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ThesisAI API</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>ThesisAI API</h1>
            <p>The API is running successfully!</p>
            <p>Check the <a href="/docs">API documentation</a> for available endpoints.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

# Test static files route
@app.get("/test-static")
async def test_static():
    return HTMLResponse(content="""
    <h1>Static Files Test</h1>
    <p>If you can see this, the server is running.</p>
    <p>Try these links:</p>
    <ul>
        <li><a href="/web/">/web/</a> - Client directory listing</li>
        <li><a href="/web/index.html">/web/index.html</a> - Main HTML file</li>
        <li><a href="/web/main.js">/web/main.js</a> - JavaScript file</li>
        <li><a href="/web/style.css">/web/style.css</a> - CSS file</li>
    </ul>
    """)

# Configuration status route
@app.get("/config/status")
async def get_config_status():
    """Get configuration status including JWT and AI provider status"""
    jwt_valid = config.validate_jwt_config()
    ai_status = config.validate_ai_config()
    
    return {
        "jwt": {
            "valid": jwt_valid,
            "algorithm": config.ALGORITHM,
            "expire_minutes": config.ACCESS_TOKEN_EXPIRE_MINUTES
        },
        "ai_providers": ai_status,
        "active_provider": config.get_active_provider(),
        "server": {
            "host": config.HOST,
            "port": config.PORT,
            "debug": config.DEBUG
        },
        "directories": {
            "upload_dir": config.UPLOAD_DIR,
            "feedback_dir": config.FEEDBACK_DIR,
            "ai_responses_dir": config.AI_RESPONSES_DIR
        }
    }

# AI providers route
@app.get("/ai-providers")
async def get_ai_providers():
    """Get available AI providers and their configuration"""
    return config.get_available_providers()

# Streaming configuration route
@app.get("/streaming-config")
async def get_streaming_config():
    """Get streaming configuration for client-side optimization"""
    return {
        "pacing_delay": 0.01,  # seconds between chunks
        "buffer_size": 10,      # characters per chunk
        "timeout": 120,         # seconds
        "retry_attempts": 3,
        "supported_types": [
            "content",      # Regular content chunks
            "status",       # Status updates
            "progress",     # Progress indicators
            "section",      # Section headers
            "error",        # Error messages
            "complete"      # Stream completion
        ]
    }

# AI feedback options route
@app.get("/ai-feedback-options")
async def get_ai_feedback_options():
    """Get available AI feedback options for dynamic checkbox generation"""
    return {
        "options": [
            {
                "id": "formatting_style",
                "label": "Formatting style",
                "description": "Check formatting, structure, and presentation quality",
                "enabled": True,
                "default": True
            },
            {
                "id": "purpose_objectives",
                "label": "Purpose and objectives",
                "description": "Evaluate clarity and grounding of purposes and objectives",
                "enabled": True,
                "default": True
            },
            {
                "id": "theoretical_foundation",
                "label": "Theoretical foundation",
                "description": "Assess theoretical framework and critical thinking",
                "enabled": True,
                "default": True
            },
            {
                "id": "professional_connection",
                "label": "Connection of subject to professional field and expertise",
                "description": "Evaluate relevance to professional development and working life",
                "enabled": True,
                "default": True
            },
            {
                "id": "development_task",
                "label": "Development/research task and its definition",
                "description": "Assess clarity and justification of research/development tasks",
                "enabled": True,
                "default": True
            },
            {
                "id": "conclusions_proposals",
                "label": "Conclusions/development proposals",
                "description": "Evaluate quality of conclusions and development proposals",
                "enabled": True,
                "default": True
            },
            {
                "id": "material_methodology",
                "label": "Material and methodological choices",
                "description": "Assess diversity and foundation of materials and methods",
                "enabled": True,
                "default": True
            },
            {
                "id": "treatment_analysis",
                "label": "Treatment and analysis of material",
                "description": "Evaluate controlled treatment and proficient analysis",
                "enabled": True,
                "default": True
            },
            {
                "id": "results_product",
                "label": "Results/Product",
                "description": "Assess originality and application of results",
                "enabled": True,
                "default": True
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    # Print configuration status on startup
    print("🚀 Starting ThesisAI Tool...")
    print(f"📁 Upload directory: {config.UPLOAD_DIR}")
    print(f"📁 Feedback directory: {config.FEEDBACK_DIR}")
    print(f"📁 AI responses directory: {config.AI_RESPONSES_DIR}")
    print(f"🤖 Active AI provider: {config.get_active_provider()}")
    
    # Check JWT configuration
    if not config.validate_jwt_config():
        print("⚠️  JWT configuration warning - using default secret key")
    
    # Check AI provider configuration
    ai_status = config.validate_ai_config()
    available_providers = [k for k, v in ai_status.items() if v]
    if available_providers:
        print(f"✅ Available AI providers: {', '.join(available_providers)}")
    else:
        print("⚠️  No AI providers configured - using fallback mode")
    
    uvicorn.run(app, host=config.HOST, port=config.PORT, reload=config.DEBUG) 