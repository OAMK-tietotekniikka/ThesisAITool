#!/usr/bin/env python3
"""
Simple test script to verify the server can start without errors.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    try:
        import fitz  # PyMuPDF
        import docx
        import pdfplumber
        import chardet
        import pandas as pd
        from bs4 import BeautifulSoup
        import asyncio
        import uuid
        import requests
        import random
        import json
        from dotenv import load_dotenv
        from datetime import datetime
        from typing import List, Optional, AsyncGenerator
        from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status, Security, Request
        from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
        from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel, EmailStr, Field
        from passlib.context import CryptContext
        import jwt
        from jwt import PyJWTError
        import aiofiles
        import traceback
        import logging
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_app_creation():
    """Test that the FastAPI app can be created."""
    try:
        from app import app
        print("✅ FastAPI app created successfully")
        return True
    except Exception as e:
        print(f"❌ App creation error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing server setup...")
    
    if not test_imports():
        print("❌ Import test failed")
        return False
    
    if not test_app_creation():
        print("❌ App creation test failed")
        return False
    
    print("✅ All tests passed! Server should start without errors.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 