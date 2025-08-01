"""
Text extraction module for ThesisAI Tool.

This module handles text extraction from various file formats.
"""

import os
import chardet
import docx
import pdfplumber
from fastapi import HTTPException

def extract_text_from_file(file_path: str) -> str:
    """Extract text from various file formats"""
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