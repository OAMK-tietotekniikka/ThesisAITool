# pip install aiofiles pydantic[email] python-docx PyMuPDF pdfplumber chardet python-multipart fastapi uvicorn passlib[bcrypt] python-jose[cryptography] python-dotenv requests beautifulsoup4 pandas

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
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Optional, AsyncGenerator

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

# Configuration
SECRET_KEY = "your-secret-key-here"  # In production, use environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
UPLOAD_DIR = "thesis_uploads"
FEEDBACK_DIR = "feedback_files"
AI_RESPONSES_DIR = "ai_responses"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FEEDBACK_DIR, exist_ok=True)
os.makedirs(AI_RESPONSES_DIR, exist_ok=True)

# Initialize FastAPI
app = FastAPI(
    title="ThesisAI API",
    description="API for ThesisAI application with student, supervisor, and admin roles",
    version="1.0.0",
    debug=False,
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
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
    # Find the student in the fake users database using their student_id
    student = next((user for user in fake_users_db.values() if user.id == student_id), None)
    
    # Check if student exists
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
        # For text files, try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        # If all encodings fail, try with chardet
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
        # For PDFs, use PyMuPDF (fitz) or pdfplumber to extract text
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
        # For DOCX files, use python-docx to extract text
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

# AI Integration
class AIModel:
    def __init__(self):
        self.api_key = self.get_api_key()  # Use environment variables in production
        self.seed = 1
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"  # OpenRouter API URL
            # self.api_url = "https://llm.chutes.ai/v1/chat/completions" # chutes.ai
        # self.api_default_model = "deepseek/deepseek-chat-v3-0324:free"

        # self.api_default_model = "deepseek/deepseek-chat-v3-0324"
        # self.api_default_model = "deepseek-ai/DeepSeek-V3-0324"
        # self.api_default_model = "deepseek/deepseek-r1:free"
        # self.api_default_model = "google/gemini-2.5-pro-preview-03-25"

        self.max_tokens = 18000

    def get_context_length_by_id(self, model_id, file_path='openrouter_models.json'):
        try:
            # Open the JSON file
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Iterate through the list of models in the 'data' field
            for model in data['data']:
                # Check if the 'id' matches the given model_id
                if model['id'] == model_id:
                    # Return the context_length
                    return model['context_length']
            
            # If the model_id is not found, return None or a message
            return None
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error reading model context length: {e}")
            return None

    def get_api_key(self):
        # Load .env file
        load_dotenv()

        # Try to get API_KEY from environment variables
        api_key = os.getenv('OPENROUTER_API_KEY')

        if not api_key:
            print("⚠️  WARNING: OPENROUTER_API_KEY is not set. Using fallback mode.")
            return None

        return api_key

    async def is_ref_valid(self, file_path: str, statement: str) -> dict:
        """
        Extracts text from a file, sends it to OpenRouter along with a statement,
        and checks if the statement is related to the file's content.
        Returns structured JSON output with summary, judgement, reasoning, and evidence.
        """

        # Step 1: Extract text from the file
        try:
            article_text = extract_text_from_file(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")

        # Step 2: Instructions and prompt for OpenRouter
        system_prompt = """
            Analyze the following article and determine whether the given statement is related to it.
            Your answer must be returned in valid JSON format with the structure provided below.

            Instructions:
            1. Read and understand the main idea of the article.
            2. Assess whether the statement is directly or indirectly related to the article’s content.
            3. Return your output strictly in the following JSON format:
            {
              "summary": "A brief summary of the article's main idea.",
              "judgement": true,
              "reasoning": "Explanation of why the statement is considered related or not.",
              "evidence": "Relevant excerpt(s) or references from the article that support the judgement."
            }
            Set "judgement" to true if the statement is related, otherwise set it to false.
            Do not add any extra commentary outside of the JSON.
        """

        user_prompt = f"""
            Input Article:
            {article_text}

            Statement:
            {statement}
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "ReferenceCheck"
        }

        payload = {
            "model": self.api_default_model,
            "messages": [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()}
            ],
            "stream": False
        }

        # Step 3: Send to OpenRouter
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]["content"]
            return json.loads(message)

        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
            print("❌ Error in is_ref_valid:", str(e))
            return {
                "summary": "",
                "judgement": False,
                "reasoning": "AI service failed or returned invalid JSON.",
                "evidence": ""
            }

    def extract_references(self, text):
        possible_ref_section = text.split('\n')[-300:]  # last 300 lines
        references = []
        in_ref_section = False
        for line in possible_ref_section:
            if re.search(r'\b(references|bibliography)\b', line, re.I):
                in_ref_section = True
            if in_ref_section and line.strip():
                references.append(line.strip())
        print(f"Extracted {len(references)} references (raw).")
        return references

    def extract_intext_citations(self, text):
        patterns = [
            r'\(([^()]+?, \d{4}[a-z]?)\)',  # APA-style
            r'\[\d+\]',                     # IEEE-style
            r'\([A-Z][a-z]+ et al\., \d{4}\)'  # APA multiple authors
        ]
        citations = set()
        for pattern in patterns:
            found = re.findall(pattern, text)
            citations.update(found)
        print(f"Extracted {len(citations)} in-text citations.")
        return list(citations)

    async def fetch_reference_text_from_url(self, url, file_path):
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.content, "html.parser")
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=' ')
            text = ' '.join(text.split())
            if not text:
                return "", False, ""
            is_valid_result = await self.is_ref_valid(file_path, text)
            is_valid = is_valid_result.get("judgement", False)
            sentences = re.split(r'(?<=[.!?]) +', text)
            random_text = random.choice(sentences) if sentences else ""
            return text, is_valid, random_text
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return "", False, ""

    async def check_ref_validity(self, file_path):
        full_text = extract_text_from_file(file_path)
        intext_cits = self.extract_intext_citations(full_text)
        references = self.extract_references(full_text)

        data = []
        for ref in references:
            if "http" in ref or "www." in ref:
                url_match = re.search(r'(https?://\S+)', ref)
                if url_match:
                    url = url_match.group(1)
                    plain_text, is_valid, rand_text = await self.fetch_reference_text_from_url(url, file_path)
                    print(f"URL Checked: {url}, Valid: {is_valid}")
                    data.append((None, ref, "Yes" if is_valid else "No", rand_text))
            else:
                data.append((None, ref, "N/A", ""))

        for i, cit in enumerate(intext_cits):
            if i < len(data):
                data[i] = (cit, *data[i][1:])
            else:
                data.append((cit, "", "N/A", ""))

        # Filter out rows with N/A in the "Valid" column (index 2)
        filtered_data = [row for row in data if row[2] != "N/A"]

        # Create markdown table
        headers = ["InTextCitation", "Reference", "Valid", "RandomSentence"]
        md_table = "| " + " | ".join(headers) + " |\n"
        md_table += "|" + "|".join(["---"] * len(headers)) + "|\n"
        
        for row in filtered_data:
            # Escape any existing pipe characters in the data
            escaped_row = [str(item).replace("|", "\\|") if item is not None else "" for item in row]
            md_table += "| " + " | ".join(escaped_row) + " |\n"
        
        return md_table

    async def grade_objective(self, file_path: str, model_id: str = "") -> str:
        """Analyze thesis content and return AI feedback using OpenRouter"""
        if not model_id:
            model_id = self.api_default_model
        print('analyze_thesis, model_id:', model_id)

        # Extract the plain text from the thesis file based on its format
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading thesis file: {str(e)}")
        
        # Prepare the prompt
        # prompt = f"Analyze the following thesis content: {thesis_content}\nPlease answer the following questions:\n"
        # for question in predefined_questions:
        #     prompt += f"- {question}\n"

        # Test: hard coded custom_instructions
        custom_instructions = f"""
            Analyze the conetent, then grade the Purpose and objectives from 1-5 based on these criteria:
            - Excellent (5): The purpose and objectives of the thesis are well-founded from the perspectives of working life and theoretical foundation. The intention is to apply the results of the work to the development of the professional field. 
            - Good (4–3): The purpose and objectives of the thesis aim at developing the  professional field.
            - Satisfactory (2–1): The thesis has objectives.
            - Fail (0) / Unfinished: The purpose and objectives of the thesis are vaguely defined and/or the work does not follow the approved plan. 
        """
        prompt = f"Analyze the following thesis content: {thesis_content}"
        
        # Construct the headers and request data
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Thesis-Analysis"
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        # Add custom instructions if provided
        if custom_instructions:
            messages.insert(0, {"role": "system", "content": custom_instructions})

        data = {
            "model": model_id,  # Set your model here
            "messages": messages,
            "stream": False,  # Set to False for non-streaming, True if you want to stream the response
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }

        try:
            # Send the request to OpenRouter
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()  # Raise error for bad status codes
            
            response_json = response.json()
            print("Send the request to OpenRouter, response response_json:", response_json);
            message = response_json["choices"][0]["message"]["content"]
            print("Send the request to OpenRouter, response message:", message);
            
            # Return the AI feedback content
            return message

        except requests.exceptions.HTTPError as errh:
            print(f"❌ HTTP Error: {errh} - Status code: {response.status_code}")
            try:
                print("Details:", response.json())
            except:
                pass
            raise HTTPException(status_code=500, detail="Failed to get AI feedback from OpenRouter")

        except requests.exceptions.ConnectionError as errc:
            print("❌ Connection Error:", errc)
            raise HTTPException(status_code=500, detail="Connection error with OpenRouter")

        except requests.exceptions.Timeout as errt:
            print("❌ Timeout Error:", errt)
            raise HTTPException(status_code=500, detail="Request to OpenRouter timed out")

        except requests.exceptions.RequestException as err:
            print("❌ Unknown Request Error:", err)
            raise HTTPException(status_code=500, detail="An error occurred while requesting OpenRouter")

        except KeyError as e:
            print("❌ Unexpected response format. Could not extract message:", e)
            raise HTTPException(status_code=500, detail="Unexpected response from OpenRouter")

        except json.JSONDecodeError:
            print("❌ Failed to parse JSON response")
            raise HTTPException(status_code=500, detail="Failed to parse OpenRouter response")

    async def grade_objective_stream(self, file_path: str, model_id: str = "") -> AsyncGenerator[str, None]:
        """Stream objective grading using OpenRouter"""
        if not model_id:
            model_id = self.api_default_model
        print('grade_objective_stream, model_id:', model_id)

        # Check if API key is available
        if not self.api_key:
            print("🔄 Using fallback mode for objective grading - no API key available")
            # Use fake streaming as fallback
            yield f"data: [FALLBACK MODE] Grading Purposes and Objectives\n\n"
            yield f"data: This is a simulated grading response since no API key is configured.\n\n"
            yield f"data: In a real implementation, this would analyze the thesis objectives and provide detailed feedback.\n\n"
            return

        # Extract the plain text from the thesis file based on its format
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading thesis file: {str(e)}")
        
        # Prepare the prompt for objective grading
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
        
        # Construct the headers and request data
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Objective-Grading"
        }
        
        messages = [{"role": "user", "content": prompt}]

        data = {
            "model": model_id,
            "messages": messages,
            "stream": True,  # Enable streaming
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ HTTP Error: {response.status} - {error_text}")
                        raise HTTPException(status_code=500, detail="Failed to get AI feedback from OpenRouter")
                    
                    # Stream the response
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_content = line_str[6:]  # Remove 'data: ' prefix
                            if data_content == '[DONE]':
                                break
                            try:
                                json_data = json.loads(data_content)
                                if 'choices' in json_data and len(json_data['choices']) > 0:
                                    delta = json_data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield f"data: {delta['content']}\n\n"
                            except json.JSONDecodeError:
                                continue

        except aiohttp.ClientError as e:
            print(f"❌ Connection Error: {e}")
            raise HTTPException(status_code=500, detail="Connection error with OpenRouter")
        except Exception as e:
            print(f"❌ Unknown Error: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while requesting OpenRouter")

    async def grade_theoretical_foundation(self, file_path: str, model_id: str = "") -> str:
        """Analyze thesis content and return AI feedback using OpenRouter"""
        if not model_id:
            model_id = self.api_default_model
        print('analyze_thesis, model_id:', model_id)

        # Extract the plain text from the thesis file based on its format
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading thesis file: {str(e)}")
        
        # Prepare the prompt
        # prompt = f"Analyze the following thesis content: {thesis_content}\nPlease answer the following questions:\n"
        # for question in predefined_questions:
        #     prompt += f"- {question}\n"

        # Test: hard coded custom_instructions
        custom_instructions = f"""
            Analyze the content (called thesis), then grade the Theoretical foundation from 1-5 based on these criteria:
            - Excellent (5): The theoretical foundation conveys the author’s own, critical and creative  thinking. It is carefully considered, topical and purposeful in terms of the nature of the work. A sufficient amount of key scientific/artistic research and specialist knowledge has been used for the theoretical foundation. 
            - Good (4–3): The thesis has a theoretical foundation and is based on versatile industry sources.
            - Satisfactory (2–1): The thesis has a theoretical foundation and is based on industry sources.
            - Fail (0) / Unfinished: The theoretical foundation is noticeably limited and  selected uncritically.
        """
        prompt = f"Analyze the following thesis content: {thesis_content}"
        
        # Construct the headers and request data
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Thesis-Analysis"
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        # Add custom instructions if provided
        if custom_instructions:
            messages.insert(0, {"role": "system", "content": custom_instructions})

        data = {
            "model": model_id,  # Set your model here
            "messages": messages,
            "stream": False,  # Set to False for non-streaming, True if you want to stream the response
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }

        try:
            # Send the request to OpenRouter
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()  # Raise error for bad status codes
            
            response_json = response.json()
            print("Send the request to OpenRouter, response response_json:", response_json);
            message = response_json["choices"][0]["message"]["content"]
            print("Send the request to OpenRouter, response message:", message);
            
            # Return the AI feedback content
            return message

        except requests.exceptions.HTTPError as errh:
            print(f"❌ HTTP Error: {errh} - Status code: {response.status_code}")
            try:
                print("Details:", response.json())
            except:
                pass
            raise HTTPException(status_code=500, detail="Failed to get AI feedback from OpenRouter")

        except requests.exceptions.ConnectionError as errc:
            print("❌ Connection Error:", errc)
            raise HTTPException(status_code=500, detail="Connection error with OpenRouter")

        except requests.exceptions.Timeout as errt:
            print("❌ Timeout Error:", errt)
            raise HTTPException(status_code=500, detail="Request to OpenRouter timed out")

        except requests.exceptions.RequestException as err:
            print("❌ Unknown Request Error:", err)
            raise HTTPException(status_code=500, detail="An error occurred while requesting OpenRouter")

        except KeyError as e:
            print("❌ Unexpected response format. Could not extract message:", e)
            raise HTTPException(status_code=500, detail="Unexpected response from OpenRouter")

        except json.JSONDecodeError:
            print("❌ Failed to parse JSON response")
            raise HTTPException(status_code=500, detail="Failed to parse OpenRouter response")

    async def grade_theoretical_foundation_stream(self, file_path: str, model_id: str = "") -> AsyncGenerator[str, None]:
        """Stream theoretical foundation grading using OpenRouter"""
        if not model_id:
            model_id = self.api_default_model
        print('grade_theoretical_foundation_stream, model_id:', model_id)

        # Check if API key is available
        if not self.api_key:
            print("🔄 Using fallback mode for theoretical foundation grading - no API key available")
            # Use fake streaming as fallback
            yield f"data: [FALLBACK MODE] Grading Theoretical Foundation\n\n"
            yield f"data: This is a simulated grading response since no API key is configured.\n\n"
            yield f"data: In a real implementation, this would analyze the theoretical framework and provide detailed feedback.\n\n"
            return

        # Extract the plain text from the thesis file based on its format
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading thesis file: {str(e)}")
        
        # Prepare the prompt for theoretical foundation grading
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
        
        # Construct the headers and request data
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Theoretical-Grading"
        }
        
        messages = [{"role": "user", "content": prompt}]

        data = {
            "model": model_id,
            "messages": messages,
            "stream": True,  # Enable streaming
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ HTTP Error: {response.status} - {error_text}")
                        raise HTTPException(status_code=500, detail="Failed to get AI feedback from OpenRouter")
                    
                    # Stream the response
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_content = line_str[6:]  # Remove 'data: ' prefix
                            if data_content == '[DONE]':
                                break
                            try:
                                json_data = json.loads(data_content)
                                if 'choices' in json_data and len(json_data['choices']) > 0:
                                    delta = json_data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield f"data: {delta['content']}\n\n"
                            except json.JSONDecodeError:
                                continue

        except aiohttp.ClientError as e:
            print(f"❌ Connection Error: {e}")
            raise HTTPException(status_code=500, detail="Connection error with OpenRouter")
        except Exception as e:
            print(f"❌ Unknown Error: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while requesting OpenRouter")

    async def analyze_thesis(self, file_path: str, custom_instructions: str, predefined_questions: List[str], model_id: str = "") -> str:
        """Analyze thesis content and return AI feedback using OpenRouter"""
        if not model_id:
            model_id = self.api_default_model
        print('analyze_thesis, model_id:', model_id)

        # Extract the plain text from the thesis file based on its format
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading thesis file: {str(e)}")
        
        # Prepare the prompt
        # prompt = f"Analyze the following thesis content: {thesis_content}\nPlease answer the following questions:\n"
        # for question in predefined_questions:
        #     prompt += f"- {question}\n"

        # Test: hard coded custom_instructions
        custom_instructions = f"""
            You are designed to check the user's uploaded file (called 'thesis').
            You give short answers and explanations for the questions below (no introductory sentence and no follow-up suggestion), make sure to indicate all the issues specifically, don't ignore any issue:
            - Detect the reference style used in thesis, tell its name, and if it is not Harvard style, suggest the Havard style are being used in the school. Specifically indicate where the problem(s) are (page number or chapter)
            - List all incorrect reference styles, each item in the format "**Identifier**: explanation"
            - List all incorrect reference orders, each item in the format "**Identifier**: explanation"
            - List all empty chapters, each item in the format "**Chapter Identifier**: explanation". A chapter is considered empty if: It is formatted as a level 2 heading (e.g., 2.2) or level 3 heading (e.g., 2.3.5), and It does not have any body text beneath it. Use the heading structure to determine whether body text is associated with a chapter. A section of body text is typically assumed to belong to the most recent heading above it.
            - List all theoretical information without references, each item in the format "**Identifier**: explanation"
            - List all figures and tables without any reference in text, each item in the format "**Figure/Table identifier**: explanation"
            - Is there a thesis goal defined anywhere in text? Answer in the format "**Yes or No**: explanation"
        """
        prompt = f"Analyze the following thesis content: {thesis_content}"
        
        # Construct the headers and request data
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Thesis-Analysis"
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        # Add custom instructions if provided
        if custom_instructions:
            messages.insert(0, {"role": "system", "content": custom_instructions})

        data = {
            "model": model_id,  # Set your model here
            "messages": messages,
            "stream": False,  # Set to False for non-streaming, True if you want to stream the response
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }

        try:
            # Send the request to OpenRouter
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()  # Raise error for bad status codes
            
            response_json = response.json()
            print("Send the request to OpenRouter, response response_json:", response_json);
            message = response_json["choices"][0]["message"]["content"]
            print("Send the request to OpenRouter, response message:", message);
            
            # Return the AI feedback content
            return message

        except requests.exceptions.HTTPError as errh:
            print(f"❌ HTTP Error: {errh} - Status code: {response.status_code}")
            try:
                print("Details:", response.json())
            except:
                pass
            raise HTTPException(status_code=500, detail="Failed to get AI feedback from OpenRouter")

        except requests.exceptions.ConnectionError as errc:
            print("❌ Connection Error:", errc)
            raise HTTPException(status_code=500, detail="Connection error with OpenRouter")

        except requests.exceptions.Timeout as errt:
            print("❌ Timeout Error:", errt)
            raise HTTPException(status_code=500, detail="Request to OpenRouter timed out")

        except requests.exceptions.RequestException as err:
            print("❌ Unknown Request Error:", err)
            raise HTTPException(status_code=500, detail="An error occurred while requesting OpenRouter")

        except KeyError as e:
            print("❌ Unexpected response format. Could not extract message:", e)
            raise HTTPException(status_code=500, detail="Unexpected response from OpenRouter")

        except json.JSONDecodeError:
            print("❌ Failed to parse JSON response")
            raise HTTPException(status_code=500, detail="Failed to parse OpenRouter response")

    async def analyze_thesis_stream(self, file_path: str, custom_instructions: str, predefined_questions: List[str], model_id: str = "") -> AsyncGenerator[str, None]:
        """Stream AI feedback for thesis analysis using OpenRouter"""
        if not model_id:
            model_id = self.api_default_model
        print('analyze_thesis_stream, model_id:', model_id)

        # Check if API key is available
        if not self.api_key:
            print("🔄 Using fallback mode - no API key available")
            # Use fake streaming as fallback
            async for chunk in fake_ai_feedback_stream("thesis_id", custom_instructions, predefined_questions):
                yield chunk
            return

        # Extract the plain text from the thesis file based on its format
        try:
            thesis_content = extract_text_from_file(file_path)
        except Exception as e:
            print(f"Error reading thesis file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error reading thesis file: {str(e)}")
        
        # Prepare the prompt
        prompt = f"Analyze the following thesis content: {thesis_content}\nPlease answer the following questions:\n"
        for question in predefined_questions:
            prompt += f"- {question}\n"
        
        # Construct the headers and request data
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Thesis-Analysis"
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        # Add custom instructions if provided
        if custom_instructions:
            messages.insert(0, {"role": "system", "content": custom_instructions})

        data = {
            "model": model_id,
            "messages": messages,
            "stream": True,  # Enable streaming
            "seed": self.seed,
            "max_tokens": self.max_tokens,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ HTTP Error: {response.status} - {error_text}")
                        raise HTTPException(status_code=500, detail="Failed to get AI feedback from OpenRouter")
                    
                    # Stream the response
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_content = line_str[6:]  # Remove 'data: ' prefix
                            if data_content == '[DONE]':
                                break
                            try:
                                json_data = json.loads(data_content)
                                if 'choices' in json_data and len(json_data['choices']) > 0:
                                    delta = json_data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield f"data: {delta['content']}\n\n"
                            except json.JSONDecodeError:
                                continue

        except aiohttp.ClientError as e:
            print(f"❌ Connection Error: {e}")
            raise HTTPException(status_code=500, detail="Connection error with OpenRouter")
        except Exception as e:
            print(f"❌ Unknown Error: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while requesting OpenRouter")

# Streaming text generator
async def fake_ai_feedback_stream(thesis_id: str, instructions: str, questions: List[str]) -> AsyncGenerator[str, None]:
    texts = [
        f"Reviewing thesis `{thesis_id}`...",
        "Analyzing content...",
        "Strengths: Well-structured arguments, clear methodology.",
        "Areas for improvement: Need more citations in literature review.",
        "Answering predefined questions...",
        *[f"Q: {q} — A: (Simulated response here)" for q in questions],
        "Done! ✅"
    ]
    for text in texts:
        yield f"data: {text}\n\n"
        print(f"data: {text}\n\n")  # print to server console
        await asyncio.sleep(1)

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
    # current_user: User = Depends(get_current_active_user)  # temp off
):
    # Temporarily off for testing
    # check_admin(current_user)
    
    if username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if role not in ["student", "supervisor", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # if role == "student" and not supervisor_id:
    #     raise HTTPException(status_code=400, detail="Students must have a supervisor")
    
    # if role == "student" and supervisor_id not in fake_users_db:
    #     raise HTTPException(status_code=404, detail="Supervisor not found")
    
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
    
    # If this is a student, add to supervisor's assigned_students
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
    
    # Save the file
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while content := await file.read(1024):
                await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Create thesis record
    thesis = Thesis(
        student_id=current_user.id,
        filename=file.filename,
        filepath=file_path,
    )
    
    print(f"📝 Created thesis with ID: {thesis.id}")
    print(f"📝 Thesis student_id: {thesis.student_id}")
    print(f"📝 Thesis filepath: {thesis.filepath}")
    
    fake_theses_db[thesis.id] = thesis
    
    print(f"💾 Stored thesis in database. Available theses: {list(fake_theses_db.keys())}")
    
    return {"message": "Thesis uploaded successfully", "thesis_id": thesis.id}

# Optional route for testing HTML directly
@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("./_baocao/index.html", encoding='utf8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback HTML if the file doesn't exist
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

async def stream_ai_feedback(thesis_id: str, custom_instructions: str, predefined_questions: List[str], model_id: str = "") -> AsyncGenerator[str, None]:
    """Stream AI feedback for a thesis"""
    # Check if thesis exists
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        print(f"❌ Thesis not found: {thesis_id}")
        yield f"data: Error: Thesis not found\n\n"
        return
    
    print(f"✅ Starting AI feedback for thesis: {thesis_id}")
    print(f"📄 File path: {thesis.filepath}")
    print(f"🤖 Model ID: {model_id}")
    
    ai_model = AIModel()
    
    try:
        # Check if the thesis file exists
        if not os.path.exists(thesis.filepath):
            print(f"❌ Thesis file not found: {thesis.filepath}")
            yield f"data: Error: Thesis file not found\n\n"
            return
        
        print("🔄 Starting thesis analysis...")
        # Stream the analysis
        async for chunk in ai_model.analyze_thesis_stream(thesis.filepath, custom_instructions, predefined_questions, model_id):
            print(f"📤 Sending chunk: {chunk[:100]}...")  # Log first 100 chars
            yield chunk
            
        # Add separator
        yield f"data: \n{'=' * 80}\n\n"
        
        # Stream objective grading
        print("🔄 Starting objective grading...")
        yield f"data: GRADING PURPOSES AND OBJECTIVES...\n\n"
        async for chunk in ai_model.grade_objective_stream(thesis.filepath, model_id):
            print(f"📤 Sending objective chunk: {chunk[:100]}...")  # Log first 100 chars
            yield chunk
            
        # Add separator
        yield f"data: \n{'=' * 80}\n\n"
        
        # Stream theoretical foundation grading
        print("🔄 Starting theoretical foundation grading...")
        yield f"data: GRADING THEORETICAL FOUNDATION...\n\n"
        async for chunk in ai_model.grade_theoretical_foundation_stream(thesis.filepath, model_id):
            print(f"📤 Sending theoretical chunk: {chunk[:100]}...")  # Log first 100 chars
            yield chunk
            
        print("✅ AI feedback streaming completed successfully")
            
    except Exception as e:
        print("❌ Full traceback:\n", traceback.format_exc())
        print(f"❌ Error in stream_ai_feedback: {str(e)}")
        yield f"data: Error: AI service error: {str(e)}\n\n"

@app.post("/request-ai-feedback")
async def request_ai_feedback(
    thesis_id: str,
    custom_instructions: str = Form("Please review this thesis and provide feedback"),
    predefined_questions: List[str] = Form(["What are the strengths?", "What areas need improvement?"]),
    model_id: str = "",
    current_user: User = Depends(get_current_active_user)
):
    # Check if thesis exists and belongs to the student
    print(f"🔍 Looking for thesis_id: {thesis_id}")
    print(f"🔍 Current user: {current_user.username} (ID: {current_user.id})")
    print(f"🔍 Available theses in database: {list(fake_theses_db.keys())}")
    
    thesis = fake_theses_db.get(thesis_id)
    print("request-ai-feedback, thesis:", thesis);
    if not thesis:
        print(f"❌ Thesis not found in database. Available theses: {list(fake_theses_db.keys())}")
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if thesis.student_id != current_user.id:
        print(f"❌ Thesis belongs to student {thesis.student_id}, but current user is {current_user.id}")
        raise HTTPException(status_code=403, detail="Not your thesis")
    
    # Return streaming response
    return StreamingResponse(
        stream_ai_feedback(thesis_id, custom_instructions, predefined_questions, model_id),
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
    """Save AI feedback after streaming is complete"""
    # Check if thesis exists and belongs to the student
    thesis = fake_theses_db.get(thesis_id)
    if not thesis:
        raise HTTPException(status_code=404, detail="Thesis not found")
    
    if thesis.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your thesis")
    
    # Save feedback
    feedback = Feedback(
        thesis_id=thesis_id,
        reviewer_id="ai_system",
        content=feedback_content,
        is_ai_feedback=True
    )
    fake_feedback_db[feedback.id] = feedback
    
    # Update thesis
    thesis.ai_feedback_id = feedback.id
    thesis.status = "reviewed_by_ai"
    
    # Save AI response to file with UTF-8 encoding
    ai_response_path = os.path.join(AI_RESPONSES_DIR, f"{thesis_id}_ai_response.txt")
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
    
    # Create feedback
    feedback = Feedback(
        thesis_id=thesis_id,
        reviewer_id=current_user.id,
        content=feedback_content,
        is_ai_feedback=False
    )
    fake_feedback_db[feedback.id] = feedback
    
    # Update thesis
    thesis.supervisor_feedback_id = feedback.id
    thesis.status = "reviewed_by_supervisor"
    
    # Save feedback to file
    feedback_path = os.path.join(FEEDBACK_DIR, f"{thesis_id}_supervisor_feedback.txt")
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
    
    # Check permissions
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
    print("Before assign, supervisor:", supervisor);
    if not supervisor or supervisor.role != "supervisor":
        raise HTTPException(status_code=404, detail="Supervisor not found")
    
    # Remove from previous supervisor if any
    if student.supervisor_id:
        prev_supervisor = fake_users_db.get(student.supervisor_id)
        if prev_supervisor and student_username in prev_supervisor.assigned_students:
            prev_supervisor.assigned_students.remove(student_username)
    
    # Assign to new supervisor
    student.supervisor_id = supervisor_username
    if student_username not in supervisor.assigned_students:
        supervisor.assigned_students.append(student_username)
    print("After assign, supervisor:", supervisor);
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
    
    # Check permissions
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
    print("current_user:", current_user);
    theses_to_review = []
    
    # Iterate through all theses
    for thesis in fake_theses_db.values():
        # Print thesis info to check its status and student_id
        print(f"Thesis: {thesis.id}, Status: {thesis.status}, Student ID: {thesis.student_id}")

        if thesis.status in ["reviewed_by_ai", "pending"] and thesis.student_id in current_user.assigned_students:
            student = next((user for user in fake_users_db.values() if user.id == thesis.student_id), None)
            print(f"Checking student for thesis {thesis.id}: student_id={thesis.student_id}, found={student is not None}")
            if student:
                thesis_data = {
                    "student_name": student.full_name,
                    "filename": thesis.filename,
                    "upload_date": thesis.upload_date.isoformat(),
                    "status": thesis.status
                }
                theses_to_review.append(thesis_data)

    # Log the final output for verification
    print(f"Theses to Review: {theses_to_review}")

    return theses_to_review

@app.get("/users")
async def get_users(current_user: User = Depends(get_current_active_user)):
    check_admin(current_user)
    return list(fake_users_db.values())

# Additional utility endpoints
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
    check_admin(current_user)  # Ensure only admins can access this data
    
    # Add student_name to each thesis by looking it up in the users database
    theses_with_student_names = []
    for thesis in fake_theses_db.values():
        # Find the student by student_id in fake_users_db
        student = next((user for user in fake_users_db.values() if user.id == thesis.student_id and user.role == "student"), None)
        if student:
            thesis_dict = thesis.dict()  # Convert thesis to a dictionary to modify it
            thesis_dict["student_name"] = student.full_name  # Add student_name field
            theses_with_student_names.append(thesis_dict)
    
    return theses_with_student_names

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)