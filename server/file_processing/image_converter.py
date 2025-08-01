"""
Image conversion module for ThesisAI Tool.

This module handles document to image conversion for preview purposes.
"""

import io
import base64
import fitz  # PyMuPDF
import docx
from typing import List, Dict, Any
from fastapi import HTTPException

# Image processing imports
try:
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    print("Warning: Image processing libraries not available. Thesis preview as images will be disabled.")

def convert_document_to_images(file_path: str, max_pages: int = 5) -> List[Dict[str, Any]]:
    """Convert document pages to images for preview"""
    if not IMAGE_PROCESSING_AVAILABLE:
        raise HTTPException(status_code=500, detail="Image processing not available")
    
    import os
    file_ext = os.path.splitext(file_path)[1].lower()
    images = []
    
    try:
        if file_ext == ".pdf":
            # Convert PDF pages to images
            pdf_document = fitz.open(file_path)
            num_pages = min(len(pdf_document), max_pages)
            
            for page_num in range(num_pages):
                page = pdf_document[page_num]
                # Render page to image with higher resolution
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Resize for web display (max width 800px)
                max_width = 800
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to base64 for web display
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                
                images.append({
                    'page': page_num + 1,
                    'image': f"data:image/png;base64,{img_base64}",
                    'width': img.width,
                    'height': img.height
                })
            
            pdf_document.close()
            
        elif file_ext in [".doc", ".docx"]:
            # For DOC/DOCX, we'll create a simple text-based preview
            # since converting DOC/DOCX to images is complex
            try:
                doc = docx.Document(file_path)
                text_content = ""
                for para in doc.paragraphs:
                    text_content += para.text + "\n"
                
                # Create a simple text preview image
                img = create_text_preview_image(text_content[:2000], "Document Preview")  # First 2000 chars
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                
                images.append({
                    'page': 1,
                    'image': f"data:image/png;base64,{img_base64}",
                    'width': img.width,
                    'height': img.height,
                    'text_content': text_content
                })
                
            except Exception as e:
                print(f"Error processing DOC/DOCX: {str(e)}")
                # Create a fallback image
                img = create_error_preview_image("Unable to preview document")
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                
                images.append({
                    'page': 1,
                    'image': f"data:image/png;base64,{img_base64}",
                    'width': img.width,
                    'height': img.height
                })
        
        else:
            # For unsupported formats, create an error image
            img = create_error_preview_image("Unsupported file format")
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            images.append({
                'page': 1,
                'image': f"data:image/png;base64,{img_base64}",
                'width': img.width,
                'height': img.height
            })
    
    except Exception as e:
        print(f"Error converting document to images: {str(e)}")
        # Create error image
        img = create_error_preview_image("Error processing document")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        images.append({
            'page': 1,
            'image': f"data:image/png;base64,{img_base64}",
            'width': img.width,
            'height': img.height
        })
    
    return images

def create_text_preview_image(text: str, title: str) -> Image.Image:
    """Create a preview image from text content"""
    # Create image with white background
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 14)
        title_font = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    
    # Draw title
    draw.text((20, 20), title, fill='black', font=title_font)
    
    # Draw text content with word wrapping
    lines = []
    words = text.split()
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] > 760:  # 800 - 40 (margins)
            if current_line:
                lines.append(current_line)
                current_line = word
            else:
                lines.append(word)
        else:
            current_line = test_line
    
    if current_line:
        lines.append(current_line)
    
    # Draw lines
    y_position = 60
    for line in lines[:30]:  # Limit to 30 lines
        draw.text((20, y_position), line, fill='black', font=font)
        y_position += 18
        if y_position > 550:
            break
    
    if len(lines) > 30:
        draw.text((20, y_position), "...", fill='gray', font=font)
    
    return img

def create_error_preview_image(message: str) -> Image.Image:
    """Create an error preview image"""
    img = Image.new('RGB', (400, 200), color='#f8f9fa')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Draw error message
    draw.text((20, 80), message, fill='#dc3545', font=font)
    draw.text((20, 110), "Please download the file to view its contents.", fill='#6c757d', font=font)
    
    return img 