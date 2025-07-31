# pip install aiofiles pydantic[email] python-docx PyMuPDF pdfplumber chardet python-multipart fastapi uvicorn passlib[bcrypt] python-jose[cryptography] python-dotenv requests beautifulsoup4 pandas openai

import fitz  # PyMuPDF
import docx
import pdfplumber
import chardet
import pandas as pd
from bs4 import BeautifulSoup

import asyncio
import os, time, re, math
import uuid
import requests, random
import json
import aiohttp
from datetime import datetime
from typing import List, Optional, AsyncGenerator, Dict, Any
from enum import Enum

from fastapi import (
    FastAPI, 
    UploadFile, 
    File, 
    Form, 
    HTTPException, 
    Depends, 
    status,
    Security,
    Request
)
from fastapi.security import (
    OAuth2PasswordBearer, 
    OAuth2PasswordRequestForm,
    HTTPBearer,
    HTTPAuthorizationCredentials
)
from fastapi import HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
import jwt
from jwt import PyJWTError
import aiofiles

import traceback
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pdfminer").setLevel(logging.WARNING)

# Import our configuration
from config import config

# AI Provider Enum
class AIProvider(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"

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

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
security = HTTPBearer()

# Database models (in a real app, use a proper database)
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: EmailStr
    full_name: str
    hashed_password: str
    role: str  # "student", "supervisor", or "admin"
    disabled: bool = False
    supervisor_id: Optional[str] = None  # For students
    assigned_students: List[str] = []  # For supervisors

class Thesis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    filename: str
    filepath: str
    upload_date: datetime = Field(default_factory=datetime.now)
    status: str = "pending"  # pending, reviewed_by_ai, reviewed_by_supervisor, approved
    ai_feedback_id: Optional[str] = None
    supervisor_feedback_id: Optional[str] = None

class Feedback(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thesis_id: str
    reviewer_id: str  # AI or supervisor ID
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    is_ai_feedback: bool

class AIRequest(BaseModel):
    thesis_id: str
    custom_instructions: str
    predefined_questions: List[str]
    provider: AIProvider = None  # Will use active provider if None
    model: Optional[str] = None

# Mock database
fake_users_db = {
    "admin": User(
        username="admin",
        email="admin@gmail.com",
        full_name="Admin User",
        hashed_password=pwd_context.hash("1234"),
        role="admin"
    ),
    "gv": User(
        username="gv",
        email="gv@gmail.com",
        full_name="Dr. Jane Smith",
        hashed_password=pwd_context.hash("1234"),
        role="supervisor",
        assigned_students=[],
    ),
    "gv0": User(
        username="gv0",
        email="gv0@gmail.com",
        full_name="Dr. Billy Andersson",
        hashed_password=pwd_context.hash("1234"),
        role="supervisor",
        assigned_students=["sv"],
    ),
    "sv": User(
        username="sv",
        email="sv@gmail.com",
        full_name="John Doe",
        hashed_password=pwd_context.hash("1234"),
        role="student",
        supervisor_id="gv0"
    ),
    "sv2": User(
        username="sv2",
        email="sv2@gmail.com",
        full_name="New Student",
        hashed_password=pwd_context.hash("1234"),
        role="student",
    ),
}

fake_theses_db = {}
fake_feedback_db = {}

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username].dict()
        return User(**user_dict)
    return None

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
    
    user = get_user(fake_users_db, username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_student_name(student_id: str) -> str:
    student = next((user for user in fake_users_db.values() if user.id == student_id), None)
    if student and student.role == "student":
        return student.full_name
    else:
        raise HTTPException(status_code=404, detail="Student not found")

def check_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

def check_supervisor(user: User):
    if user.role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor privileges required")

def check_student(user: User):
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student privileges required")

# Function to detect file format and extract text
def extract_text_from_file(file_path: str) -> str:
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == ".txt":
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        try:
            with open(file_path, "rb") as file:
                raw_data = file.read()
                detected_encoding = chardet.detect(raw_data)['encoding']
                if detected_encoding:
                    return raw_data.decode(detected_encoding)
                else:
                    return raw_data.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error reading text file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading text file: {str(e)}")

    elif file_ext == ".pdf":
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            print(f"Error extracting PDF text: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error extracting PDF text: {str(e)}")

    elif file_ext == ".docx":
        try:
            doc = docx.Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            print(f"Error extracting DOCX text: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error extracting DOCX text: {str(e)}")

    else:
        print("Unsupported file format")
        raise HTTPException(status_code=400, detail="Unsupported file format")

# Unified AI Interface
class UnifiedAIModel:
    def __init__(self):
        self.config = config
        self.seed = config.AI_SEED
        self.provider_config = config.get_ai_provider_config()

    def get_api_key(self, provider: AIProvider) -> Optional[str]:
        """Get API key for the specified provider"""
        provider_name = provider.value
        return self.provider_config.get(provider_name, {}).get('api_key')

    def get_model(self, provider: AIProvider, model: Optional[str] = None) -> str:
        """Get the model to use for the specified provider"""
        if model:
            return model
        provider_name = provider.value
        return self.provider_config.get(provider_name, {}).get('default_model', 'gpt-4o')

    def get_headers(self, provider: AIProvider) -> Dict[str, str]:
        """Get headers for the specified provider"""
        api_key = self.get_api_key(provider)
        if not api_key:
            raise HTTPException(status_code=500, detail=f"No API key configured for {provider}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Add provider-specific headers
        if provider == AIProvider.OPENROUTER:
            headers.update({
                "HTTP-Referer": "http://localhost",
                "X-Title": "ThesisAI"
            })
        
        return headers

    def get_api_url(self, provider: AIProvider) -> str:
        """Get API URL for the specified provider"""
        provider_name = provider.value
        return self.provider_config.get(provider_name, {}).get('api_url', '')

    async def make_request(self, provider: AIProvider, messages: List[Dict[str, str]], 
                          model: Optional[str] = None, stream: bool = False) -> Dict[str, Any]:
        """Make a request to the specified AI provider"""
        api_key = self.get_api_key(provider)
        if not api_key:
            raise HTTPException(status_code=500, detail=f"No API key configured for {provider}")
        
        model_name = self.get_model(provider, model)
        headers = self.get_headers(provider)
        api_url = self.get_api_url(provider)
        
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
        }
        
        # Add provider-specific parameters
        if provider == AIProvider.OPENROUTER:
            payload["seed"] = self.seed
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error with {provider}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error with {provider}: {str(e)}")

    async def make_streaming_request(self, provider: AIProvider, messages: List[Dict[str, str]], 
                                   model: Optional[str] = None, pacing_delay: float = 0.01) -> AsyncGenerator[str, None]:
        """Make a streaming request to the specified AI provider with improved UX"""
        api_key = self.get_api_key(provider)
        if not api_key:
            print(f"🔄 Using fallback mode for {provider} - no API key available")
            yield f"data: {json.dumps({'type': 'status', 'content': f'[FALLBACK MODE] {provider.value.upper()} Analysis'})}\n\n"
            yield f"data: {json.dumps({'type': 'content', 'content': f'This is a simulated response since no API key is configured for {provider}.'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            return
        
        model_name = self.get_model(provider, model)
        headers = self.get_headers(provider)
        api_url = self.get_api_url(provider)
        
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,
        }
        
        if provider == AIProvider.OPENROUTER:
            payload["seed"] = self.seed
        
        try:
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'content': f'Connecting to {provider.value.upper()}...'})}\n\n"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ HTTP Error: {response.status} - {error_text}")
                        yield f"data: {json.dumps({'type': 'error', 'content': f'Failed to get AI feedback from {provider}: {response.status}'})}\n\n"
                        return
                    
                    # Send connected status
                    yield f"data: {json.dumps({'type': 'status', 'content': f'Connected to {provider.value.upper()}. Generating response...'})}\n\n"
                    
                    buffer = ""
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_content = line_str[6:]
                            if data_content == '[DONE]':
                                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                                break
                            try:
                                json_data = json.loads(data_content)
                                if 'choices' in json_data and len(json_data['choices']) > 0:
                                    delta = json_data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        buffer += content
                                        
                                        # Send content in chunks for better UX
                                        if len(buffer) >= 10 or '\n' in buffer:  # Send every 10 chars or on newline
                                            yield f"data: {json.dumps({'type': 'content', 'content': buffer})}\n\n"
                                            buffer = ""
                                            await asyncio.sleep(pacing_delay)  # Control pacing
                                        
                            except json.JSONDecodeError:
                                continue
                    
                    # Send any remaining buffer
                    if buffer:
                        yield f"data: {json.dumps({'type': 'content', 'content': buffer})}\n\n"
                        
        except asyncio.TimeoutError:
            print(f"❌ Timeout with {provider}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Request timed out for {provider}'})}\n\n"
        except Exception as e:
            print(f"❌ Error with {provider} streaming: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error with {provider}: {str(e)}'})}\n\n"

    async def analyze_thesis(self, file_path: str, custom_instructions: str, 
                           predefined_questions: List[str], provider: AIProvider = None, 
                           model: Optional[str] = None) -> str:
        """Analyze thesis content using the specified AI provider"""
        if provider is None:
            provider = AIProvider(config.get_active_provider())
            
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading thesis file: {str(e)}")
        
        prompt = f"Analyze the following thesis content: {thesis_content}\nPlease answer the following questions:\n"
        for question in predefined_questions:
            prompt += f"- {question}\n"
        
        messages = [{"role": "user", "content": prompt}]
        
        if custom_instructions:
            messages.insert(0, {"role": "system", "content": custom_instructions})
        
        try:
            response_json = await self.make_request(provider, messages, model)
            message = response_json["choices"][0]["message"]["content"]
            return message
        except Exception as e:
            print(f"❌ Error in analyze_thesis with {provider}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error with {provider}: {str(e)}")

    async def analyze_thesis_stream(self, file_path: str, custom_instructions: str, 
                                  predefined_questions: List[str], provider: AIProvider = None, 
                                  model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream thesis analysis using the specified AI provider with enhanced UX"""
        if provider is None:
            provider = AIProvider(config.get_active_provider())
            
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error reading thesis file: {str(e)}'})}\n\n"
            return
        
        prompt = f"Analyze the following thesis content: {thesis_content}\nPlease answer the following questions:\n"
        for question in predefined_questions:
            prompt += f"- {question}\n"
        
        messages = [{"role": "user", "content": prompt}]
        
        if custom_instructions:
            messages.insert(0, {"role": "system", "content": custom_instructions})
        
        async for chunk in self.make_streaming_request(provider, messages, model):
            yield chunk

    async def grade_objective(self, file_path: str, provider: AIProvider = None, 
                            model: Optional[str] = None) -> str:
        """Grade thesis objectives using the specified AI provider"""
        if provider is None:
            provider = AIProvider(config.get_active_provider())
            
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading thesis file: {str(e)}")
        
        custom_instructions = """
            Analyze the content, then grade the Purpose and objectives from 1-5 based on these criteria:
            - Excellent (5): The purpose and objectives of the thesis are well-founded from the perspectives of working life and theoretical foundation. The intention is to apply the results of the work to the development of the professional field. 
            - Good (4–3): The purpose and objectives of the thesis aim at developing the professional field.
            - Satisfactory (2–1): The thesis has objectives.
            - Fail (0) / Unfinished: The purpose and objectives of the thesis are vaguely defined and/or the work does not follow the approved plan. 
        """
        
        prompt = f"Analyze the following thesis content: {thesis_content}"
        messages = [{"role": "user", "content": prompt}]
        messages.insert(0, {"role": "system", "content": custom_instructions})
        
        try:
            response_json = await self.make_request(provider, messages, model)
            message = response_json["choices"][0]["message"]["content"]
            return message
        except Exception as e:
            print(f"❌ Error in grade_objective with {provider}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error with {provider}: {str(e)}")

    async def grade_objective_stream(self, file_path: str, provider: AIProvider = None, 
                                   model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream objective grading using the specified AI provider with enhanced UX"""
        if provider is None:
            provider = AIProvider(config.get_active_provider())
            
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error reading thesis file: {str(e)}'})}\n\n"
            return
        
        prompt = f"""
        Analyze the following thesis content and provide detailed grading for PURPOSES AND OBJECTIVES.
        
        Thesis Content:
        {thesis_content}
        
        Please evaluate the thesis based on the following criteria:
        1. Clarity and specificity of research objectives
        2. Alignment between objectives and methodology
        3. Feasibility and scope of the research
        4. Contribution to the field
        5. Practical relevance
        
        Provide a comprehensive analysis with specific examples from the thesis.
        """
        
        messages = [{"role": "user", "content": prompt}]
        
        async for chunk in self.make_streaming_request(provider, messages, model):
            yield chunk

    async def grade_theoretical_foundation(self, file_path: str, provider: AIProvider = None, 
                                        model: Optional[str] = None) -> str:
        """Grade theoretical foundation using the specified AI provider"""
        if provider is None:
            provider = AIProvider(config.get_active_provider())
            
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading thesis file: {str(e)}")
        
        custom_instructions = """
            Analyze the content (called thesis), then grade the Theoretical foundation from 1-5 based on these criteria:
            - Excellent (5): The theoretical foundation conveys the author's own, critical and creative thinking. It is carefully considered, topical and purposeful in terms of the nature of the work. A sufficient amount of key scientific/artistic research and specialist knowledge has been used for the theoretical foundation. 
            - Good (4–3): The thesis has a theoretical foundation and is based on versatile industry sources.
            - Satisfactory (2–1): The thesis has a theoretical foundation and is based on industry sources.
            - Fail (0) / Unfinished: The theoretical foundation is noticeably limited and selected uncritically.
        """
        
        prompt = f"Analyze the following thesis content: {thesis_content}"
        messages = [{"role": "user", "content": prompt}]
        messages.insert(0, {"role": "system", "content": custom_instructions})
        
        try:
            response_json = await self.make_request(provider, messages, model)
            message = response_json["choices"][0]["message"]["content"]
            return message
        except Exception as e:
            print(f"❌ Error in grade_theoretical_foundation with {provider}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error with {provider}: {str(e)}")

    async def grade_theoretical_foundation_stream(self, file_path: str, provider: AIProvider = None, 
                                               model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream theoretical foundation grading using the specified AI provider with enhanced UX"""
        if provider is None:
            provider = AIProvider(config.get_active_provider())
            
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Error reading thesis file: {str(e)}'})}\n\n"
            return
        
        prompt = f"""
        Analyze the following thesis content and provide detailed grading for THEORETICAL FOUNDATION.
        
        Thesis Content:
        {thesis_content}
        
        Please evaluate the thesis based on the following criteria:
        1. Depth and breadth of theoretical framework
        2. Appropriate use of relevant theories and concepts
        3. Integration of theoretical and practical elements
        4. Critical analysis of existing literature
        5. Theoretical contribution to the field
        
        Provide a comprehensive analysis with specific examples from the thesis.
        """
        
        messages = [{"role": "user", "content": prompt}]
        
        async for chunk in self.make_streaming_request(provider, messages, model):
            yield chunk

# Initialize the unified AI model
ai_model = UnifiedAIModel()

# Routes
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    print("form_data:", form_data);
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register")
async def register(
    username: str = Form(...),
    email: EmailStr = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    supervisor_id: Optional[str] = Form(None),
):
    if username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if role not in ["student", "supervisor", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    hashed_password = get_password_hash(password)
    user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        role=role,
        supervisor_id=supervisor_id
    )
    
    fake_users_db[username] = user
    
    if role == "student" and supervisor_id:
        supervisor = fake_users_db.get(supervisor_id)
        if supervisor:
            supervisor.assigned_students.append(username)
    
    return {"message": "User created successfully", "user_id": user.id}

@app.post("/upload-thesis")
async def upload_thesis(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    check_student(current_user)
    
    print(f"📤 Uploading thesis for user: {current_user.username} (ID: {current_user.id})")
    print(f"📄 File name: {file.filename}")
    
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
    file_path = os.path.join(config.UPLOAD_DIR, unique_filename)
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while content := await file.read(1024):
                await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    thesis = Thesis(
        student_id=current_user.id,
        filename=file.filename,
        filepath=file_path,
    )
    
    print(f"📝 Created thesis with ID: {thesis.id}")
    fake_theses_db[thesis.id] = thesis
    
    return {"message": "Thesis uploaded successfully", "thesis_id": thesis.id}

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

async def stream_ai_feedback(thesis_id: str, custom_instructions: str, predefined_questions: List[str], 
                           provider: AIProvider = None, model: Optional[str] = None) -> AsyncGenerator[str, None]:
    """Stream AI feedback for a thesis using the specified provider with enhanced UX"""
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        print(f"❌ Thesis not found: {thesis_id}")
        yield f"data: {json.dumps({'type': 'error', 'content': 'Thesis not found'})}\n\n"
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
        return
    
    print(f"✅ Starting AI feedback for thesis: {thesis_id}")
    print(f"📄 File path: {thesis.filepath}")
    print(f"🤖 Provider: {provider or 'active'}")
    print(f"🤖 Model: {model or 'default'}")
    
    try:
        if not os.path.exists(thesis.filepath):
            print(f"❌ Thesis file not found: {thesis.filepath}")
            yield f"data: {json.dumps({'type': 'error', 'content': 'Thesis file not found'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            return
        
        # Send initial progress
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Starting thesis analysis...', 'step': 1, 'total': 3})}\n\n"
        
        # Step 1: Thesis Analysis
        print("🔄 Starting thesis analysis...")
        async for chunk in ai_model.analyze_thesis_stream(thesis.filepath, custom_instructions, predefined_questions, provider, model):
            # Parse the chunk to extract structured data
            if chunk.startswith('data: '):
                try:
                    data = json.loads(chunk[6:])
                    if data.get('type') == 'content':
                        yield chunk
                    elif data.get('type') == 'error':
                        yield chunk
                        return
                    elif data.get('type') == 'complete':
                        break
                except json.JSONDecodeError:
                    # Handle legacy format
                    yield chunk
            else:
                yield chunk
            
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Thesis analysis completed. Starting objective grading...', 'step': 2, 'total': 3})}\n\n"
        yield f"data: {json.dumps({'type': 'section', 'content': 'GRADING PURPOSES AND OBJECTIVES'})}\n\n"
        
        # Step 2: Objective Grading
        print("🔄 Starting objective grading...")
        async for chunk in ai_model.grade_objective_stream(thesis.filepath, provider, model):
            if chunk.startswith('data: '):
                try:
                    data = json.loads(chunk[6:])
                    if data.get('type') == 'content':
                        yield chunk
                    elif data.get('type') == 'error':
                        yield chunk
                        return
                    elif data.get('type') == 'complete':
                        break
                except json.JSONDecodeError:
                    yield chunk
            else:
                yield chunk
                
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Objective grading completed. Starting theoretical foundation grading...', 'step': 3, 'total': 3})}\n\n"
        yield f"data: {json.dumps({'type': 'section', 'content': 'GRADING THEORETICAL FOUNDATION'})}\n\n"
        
        # Step 3: Theoretical Foundation Grading
        print("🔄 Starting theoretical foundation grading...")
        async for chunk in ai_model.grade_theoretical_foundation_stream(thesis.filepath, provider, model):
            if chunk.startswith('data: '):
                try:
                    data = json.loads(chunk[6:])
                    if data.get('type') == 'content':
                        yield chunk
                    elif data.get('type') == 'error':
                        yield chunk
                        return
                    elif data.get('type') == 'complete':
                        break
                except json.JSONDecodeError:
                    yield chunk
            else:
                yield chunk
            
        print("✅ AI feedback streaming completed successfully")
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Analysis completed successfully!', 'step': 3, 'total': 3})}\n\n"
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
    except Exception as e:
        print("❌ Full traceback:\n", traceback.format_exc())
        print(f"❌ Error in stream_ai_feedback: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'content': f'AI service error: {str(e)}'})}\n\n"
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

@app.post("/request-ai-feedback")
async def request_ai_feedback(
    thesis_id: str,
    custom_instructions: str = Form("Please review this thesis and provide feedback"),
    predefined_questions: List[str] = Form(["What are the strengths?", "What areas need improvement?"]),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    print(f"🔍 Looking for thesis_id: {thesis_id}")
    print(f"🔍 Current user: {current_user.username} (ID: {current_user.id})")
    print(f"🔍 Provider: {provider or 'active'}")
    print(f"🔍 Model: {model}")
    
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        print(f"❌ Thesis not found in database. Available theses: {list(fake_theses_db.keys())}")
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if thesis.student_id != current_user.id:
        print(f"❌ Thesis belongs to student {thesis.student_id}, but current user is {current_user.id}")
        raise HTTPException(status_code=403, detail="Not your thesis")
    
    return StreamingResponse(
        stream_ai_feedback(thesis_id, custom_instructions, predefined_questions, provider, model),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.post("/save-ai-feedback")
async def save_ai_feedback(
    thesis_id: str,
    feedback_content: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if thesis.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your thesis")
    
    feedback = Feedback(
        thesis_id=thesis_id,
        reviewer_id="ai_system",
        content=feedback_content,
        is_ai_feedback=True
    )
    fake_feedback_db[feedback.id] = feedback
    
    thesis.ai_feedback_id = feedback.id
    thesis.status = "reviewed_by_ai"
    
    ai_response_path = os.path.join(config.AI_RESPONSES_DIR, f"{thesis_id}_ai_response.txt")
    async with aiofiles.open(ai_response_path, 'w', encoding='utf-8') as f:
        await f.write(feedback_content)

    return {"message": "Feedback saved successfully", "feedback_id": feedback.id}

@app.post("/submit-supervisor-feedback")
async def submit_supervisor_feedback(
    thesis_id: str,
    feedback_content: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    check_supervisor(current_user)
    
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if thesis.student_id not in current_user.assigned_students:
        raise HTTPException(status_code=403, detail="Not your assigned student")
    
    feedback = Feedback(
        thesis_id=thesis_id,
        reviewer_id=current_user.id,
        content=feedback_content,
        is_ai_feedback=False
    )
    fake_feedback_db[feedback.id] = feedback
    
    thesis.supervisor_feedback_id = feedback.id
    thesis.status = "reviewed_by_supervisor"
    
    feedback_path = os.path.join(config.FEEDBACK_DIR, f"{thesis_id}_supervisor_feedback.txt")
    async with aiofiles.open(feedback_path, 'w') as f:
        await f.write(feedback_content)
    
    return {"message": "Feedback submitted successfully", "feedback_id": feedback.id}

@app.get("/get-supervisor-feedback/{thesis_id}")
async def get_supervisor_feedback(
    thesis_id: str,
    current_user: User = Depends(get_current_active_user)
):
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if current_user.role == "student" and thesis.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your thesis")
    
    if current_user.role == "supervisor" and thesis.student_id not in current_user.assigned_students:
        raise HTTPException(status_code=403, detail="Not your assigned student")
    
    if not thesis.supervisor_feedback_id:
        raise HTTPException(status_code=404, detail="No supervisor feedback available")
    
    feedback = fake_feedback_db.get(thesis.supervisor_feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return feedback

@app.post("/assign-supervisor")
async def assign_supervisor(
    student_username: str = Form(...),
    supervisor_username: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    check_admin(current_user)
    
    student = fake_users_db.get(student_username)
    if not student or student.role != "student":
        raise HTTPException(status_code=404, detail="Student not found")
    
    supervisor = fake_users_db.get(supervisor_username)
    if not supervisor or supervisor.role != "supervisor":
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    if student.supervisor_id:
        prev_supervisor = fake_users_db.get(student.supervisor_id)
        if prev_supervisor and student_username in prev_supervisor.assigned_students:
            prev_supervisor.assigned_students.remove(student_username)
    
    student.supervisor_id = supervisor_username
    if student_username not in supervisor.assigned_students:
        supervisor.assigned_students.append(student_username)
    
    return {"message": f"Supervisor {supervisor_username} assigned to student {student_username}"}

@app.get("/my-theses")
async def get_my_theses(current_user: User = Depends(get_current_active_user)):
    print(f"🔍 Getting theses for user: {current_user.username} (ID: {current_user.id})")
    print(f"🔍 User role: {current_user.role}")
    
    if current_user.role == "student":
        theses = [t for t in fake_theses_db.values() if t.student_id == current_user.id]
        print(f"🔍 Found {len(theses)} theses for student")
    elif current_user.role == "supervisor":
        student_ids = current_user.assigned_students
        print(f"🔍 Supervisor assigned students: {student_ids}")
        theses = [t for t in fake_theses_db.values() if t.student_id in student_ids]
        print(f"🔍 Found {len(theses)} theses for supervisor")
    else:  # admin
        theses = list(fake_theses_db.values())
        print(f"🔍 Found {len(theses)} theses for admin")
    
    print(f"🔍 Returning theses: {[{'id': t.id, 'filename': t.filename, 'student_id': t.student_id} for t in theses]}")
    
    return theses

@app.get("/download-thesis/{thesis_id}")
async def download_thesis(
    thesis_id: str,
    current_user: User = Depends(get_current_active_user)
):
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if current_user.role == "student" and thesis.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your thesis")
    
    if current_user.role == "supervisor" and thesis.student_id not in current_user.assigned_students:
        raise HTTPException(status_code=403, detail="Not your assigned student")
    
    if not os.path.exists(thesis.filepath):
        raise HTTPException(status_code=404, detail="Thesis file not found")
    
    return FileResponse(
        thesis.filepath,
        filename=thesis.filename,
        media_type="application/octet-stream"
    )

@app.get("/theses-to-review")
async def get_theses_to_review(current_user: User = Depends(get_current_active_user)):
    check_supervisor(current_user)
    theses_to_review = []
    
    for thesis in fake_theses_db.values():
        if thesis.status in ["reviewed_by_ai", "pending"] and thesis.student_id in current_user.assigned_students:
            student = next((user for user in fake_users_db.values() if user.id == thesis.student_id), None)
            if student:
                thesis_data = {
                    "student_name": student.full_name,
                    "filename": thesis.filename,
                    "upload_date": thesis.upload_date.isoformat(),
                    "status": thesis.status
                }
                theses_to_review.append(thesis_data)

    return theses_to_review

@app.get("/users")
async def get_users(current_user: User = Depends(get_current_active_user)):
    check_admin(current_user)
    return list(fake_users_db.values())

@app.get("/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/supervisors")
async def get_supervisors(current_user: User = Depends(get_current_active_user)):
    supervisors = [u for u in fake_users_db.values() if u.role == "supervisor"]
    return supervisors

@app.get("/students")
async def get_students(current_user: User = Depends(get_current_active_user)):
    if current_user.role == "supervisor":
        students = [fake_users_db[s] for s in current_user.assigned_students]
    else:
        check_admin(current_user)
        students = [u for u in fake_users_db.values() if u.role == "student"]
    return students

@app.get("/supervisor-assignments")
async def get_supervisor_assignments(current_user: User = Depends(get_current_active_user)):
    check_admin(current_user)
    assignments = []
    for user in fake_users_db.values():
        if user.role == "student":
            supervisor_name = None
            if user.supervisor_id and user.supervisor_id in fake_users_db:
                supervisor_name = fake_users_db[user.supervisor_id].full_name
            assignments.append({
                "student_id": user.username,
                "student_name": user.full_name,
                "supervisor_name": supervisor_name
            })
    return assignments

@app.get("/all-theses")
async def get_all_theses(current_user: User = Depends(get_current_active_user)):
    check_admin(current_user)
    
    theses_with_student_names = []
    for thesis in fake_theses_db.values():
        student = next((user for user in fake_users_db.values() if user.id == thesis.student_id and user.role == "student"), None)
        if student:
            thesis_dict = thesis.dict()
            thesis_dict["student_name"] = student.full_name
            theses_with_student_names.append(thesis_dict)
    
    return theses_with_student_names

@app.get("/ai-providers")
async def get_ai_providers():
    """Get available AI providers and their configuration"""
    return config.get_available_providers()

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

@app.post("/request-ai-feedback-enhanced")
async def request_ai_feedback_enhanced(
    thesis_id: str,
    custom_instructions: str = Form("Please review this thesis and provide feedback"),
    predefined_questions: List[str] = Form(["What are the strengths?", "What areas need improvement?"]),
    provider: AIProvider = Form(None),
    model: Optional[str] = Form(None),
    pacing_delay: float = Form(0.01),
    current_user: User = Depends(get_current_active_user)
):
    """Enhanced AI feedback endpoint with configurable pacing and better error handling"""
    print(f"🔍 Enhanced AI feedback request for thesis_id: {thesis_id}")
    print(f"🔍 Current user: {current_user.username} (ID: {current_user.id})")
    print(f"🔍 Provider: {provider or 'active'}")
    print(f"🔍 Model: {model}")
    print(f"🔍 Pacing delay: {pacing_delay}")
    
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        print(f"❌ Thesis not found in database. Available theses: {list(fake_theses_db.keys())}")
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if thesis.student_id != current_user.id:
        print(f"❌ Thesis belongs to student {thesis.student_id}, but current user is {current_user.id}")
        raise HTTPException(status_code=403, detail="Not your thesis")
    
    return StreamingResponse(
        stream_ai_feedback_enhanced(thesis_id, custom_instructions, predefined_questions, provider, model, pacing_delay),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "X-Streaming-Version": "2.0"
        }
    )

async def stream_ai_feedback_enhanced(thesis_id: str, custom_instructions: str, predefined_questions: List[str], 
                                     provider: AIProvider = None, model: Optional[str] = None, 
                                     pacing_delay: float = 0.01) -> AsyncGenerator[str, None]:
    """Enhanced streaming function with better pacing and error recovery"""
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        yield f"data: {json.dumps({'type': 'error', 'content': 'Thesis not found'})}\n\n"
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
        return
    
    try:
        if not os.path.exists(thesis.filepath):
            yield f"data: {json.dumps({'type': 'error', 'content': 'Thesis file not found'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            return
        
        # Send initial status with metadata
        yield f"data: {json.dumps({
            'type': 'status', 
            'content': 'Starting analysis...',
            'metadata': {
                'thesis_id': thesis_id,
                'provider': provider.value if provider else 'active',
                'model': model or 'default',
                'pacing_delay': pacing_delay
            }
        })}\n\n"
        
        # Step 1: Thesis Analysis
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Analyzing thesis content...', 'step': 1, 'total': 3})}\n\n"
        
        async for chunk in ai_model.analyze_thesis_stream(thesis.filepath, custom_instructions, predefined_questions, provider, model):
            if chunk.startswith('data: '):
                try:
                    data = json.loads(chunk[6:])
                    if data.get('type') == 'content':
                        yield chunk
                        await asyncio.sleep(pacing_delay)  # Apply pacing
                    elif data.get('type') == 'error':
                        yield chunk
                        return
                    elif data.get('type') == 'complete':
                        break
                except json.JSONDecodeError:
                    yield chunk
            else:
                yield chunk
                await asyncio.sleep(pacing_delay)  # Apply pacing to legacy format
        
        # Step 2: Objective Grading
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Grading objectives...', 'step': 2, 'total': 3})}\n\n"
        yield f"data: {json.dumps({'type': 'section', 'content': 'GRADING PURPOSES AND OBJECTIVES'})}\n\n"
        
        async for chunk in ai_model.grade_objective_stream(thesis.filepath, provider, model):
            if chunk.startswith('data: '):
                try:
                    data = json.loads(chunk[6:])
                    if data.get('type') == 'content':
                        yield chunk
                        await asyncio.sleep(pacing_delay)
                    elif data.get('type') == 'error':
                        yield chunk
                        return
                    elif data.get('type') == 'complete':
                        break
                except json.JSONDecodeError:
                    yield chunk
                    await asyncio.sleep(pacing_delay)
            else:
                yield chunk
                await asyncio.sleep(pacing_delay)
        
        # Step 3: Theoretical Foundation Grading
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Grading theoretical foundation...', 'step': 3, 'total': 3})}\n\n"
        yield f"data: {json.dumps({'type': 'section', 'content': 'GRADING THEORETICAL FOUNDATION'})}\n\n"
        
        async for chunk in ai_model.grade_theoretical_foundation_stream(thesis.filepath, provider, model):
            if chunk.startswith('data: '):
                try:
                    data = json.loads(chunk[6:])
                    if data.get('type') == 'content':
                        yield chunk
                        await asyncio.sleep(pacing_delay)
                    elif data.get('type') == 'error':
                        yield chunk
                        return
                    elif data.get('type') == 'complete':
                        break
                except json.JSONDecodeError:
                    yield chunk
                    await asyncio.sleep(pacing_delay)
            else:
                yield chunk
                await asyncio.sleep(pacing_delay)
        
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Analysis completed successfully!', 'step': 3, 'total': 3})}\n\n"
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
            
    except Exception as e:
        print(f"❌ Error in enhanced streaming: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'content': f'Streaming error: {str(e)}'})}\n\n"
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

@app.get("/simple-test-page")
async def simple_test_page():
    """Serve the simple streaming test page"""
    try:
        with open("./server/simple_test.html", encoding='utf8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Simple test page not found</h1>")

@app.get("/debug-streaming-page")
async def debug_streaming_page():
    """Serve the debug streaming tool"""
    try:
        with open("./server/debug_streaming.html", encoding='utf8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Debug tool not found</h1>")

@app.get("/test-streaming-page")
async def test_streaming_page():
    """Serve the test streaming page"""
    try:
        with open("./server/test_streaming.html", encoding='utf8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Test page not found</h1>")

@app.get("/test-streaming")
async def test_streaming():
    """Test endpoint to verify streaming format"""
    async def test_stream():
        yield f"data: {json.dumps({'type': 'status', 'content': 'Starting test...'})}\n\n"
        await asyncio.sleep(0.5)
        
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Step 1/3', 'step': 1, 'total': 3})}\n\n"
        await asyncio.sleep(0.5)
        
        yield f"data: {json.dumps({'type': 'content', 'content': 'This is a test message. '})}\n\n"
        await asyncio.sleep(0.5)
        
        yield f"data: {json.dumps({'type': 'content', 'content': 'It should display properly. '})}\n\n"
        await asyncio.sleep(0.5)
        
        yield f"data: {json.dumps({'type': 'content', 'content': 'With proper formatting.'})}\n\n"
        await asyncio.sleep(0.5)
        
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
    
    return StreamingResponse(
        test_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/test-ai-feedback")
async def test_ai_feedback():
    """Test endpoint for AI feedback without authentication"""
    
    async def test_stream():
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Starting test analysis...', 'step': 1, 'total': 2})}\n\n"
        
        # Simulate some content
        test_content = """### Test Feedback Analysis

This is a test response to verify that the streaming endpoint is working correctly.

#### Strengths
- The system is properly configured
- Streaming is functional
- JSON parsing works correctly

#### Areas for Improvement
- Add more comprehensive error handling
- Implement better progress tracking
- Enhance the user interface

#### Recommendations
1. Continue testing the system
2. Monitor performance
3. Gather user feedback

This test confirms that the AI feedback system is operational."""
        
        # Stream the content in chunks
        words = test_content.split()
        for i, word in enumerate(words):
            yield f"data: {json.dumps({'type': 'content', 'content': word + ' '})}\n\n"
            await asyncio.sleep(0.1)  # Simulate processing time
        
        yield f"data: {json.dumps({'type': 'progress', 'content': 'Test completed successfully!', 'step': 2, 'total': 2})}\n\n"
        yield f"data: {json.dumps({'type': 'complete'})}\n\n"
    
    return StreamingResponse(
        test_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    # Print configuration status on startup
    print("🚀 Starting ThesisAI Server...")
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