"""
File processing package for ThesisAI Tool.

This package contains all file processing-related modules.
"""

from .text_extractor import extract_text_from_file
from .image_converter import (
    convert_document_to_images,
    create_text_preview_image,
    create_error_preview_image
)

__all__ = [
    'extract_text_from_file',
    'convert_document_to_images',
    'create_text_preview_image',
    'create_error_preview_image'
] 