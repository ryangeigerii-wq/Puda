"""
OCR module for text extraction from images.

Supports multilingual OCR with preprocessing and layout analysis.
"""

from .engine import OCREngine, OCRResult, ocr_image
from .preprocessor import ImagePreprocessor, load_image, load_image_from_bytes

__all__ = [
    'OCREngine',
    'OCRResult',
    'ocr_image',
    'ImagePreprocessor',
    'load_image',
    'load_image_from_bytes'
]
