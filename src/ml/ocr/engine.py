"""
OCR engine for text extraction from images.
Supports multilingual OCR with English, French, and Arabic.
"""

import pytesseract
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
import re

from .preprocessor import ImagePreprocessor, load_image, load_image_from_bytes

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR extraction result."""
    text: str
    confidence: float
    language: str
    layout: Dict
    word_confidences: List[float]
    processing_time_ms: float


class OCREngine:
    """Multilingual OCR engine using Tesseract."""
    
    # Language codes
    SUPPORTED_LANGUAGES = {
        'en': 'eng',
        'fr': 'fra',
        'ar': 'ara'
    }
    
    def __init__(
        self,
        languages: str = 'eng+fra+ara',
        tesseract_cmd: Optional[str] = None,
        preprocess: bool = True
    ):
        """
        Initialize OCR engine.
        
        Args:
            languages: Tesseract language codes (e.g., 'eng+fra+ara')
            tesseract_cmd: Path to tesseract executable (optional)
            preprocess: Enable image preprocessing
        """
        self.languages = languages
        self.preprocess_enabled = preprocess
        self.preprocessor = ImagePreprocessor() if preprocess else None
        
        # Set tesseract command path if provided
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        logger.info(f"Initialized OCR engine with languages: {languages}")
    
    def extract_text(
        self,
        image: np.ndarray,
        languages: Optional[str] = None,
        psm: int = 1,
        preprocess: Optional[bool] = None
    ) -> OCRResult:
        """
        Extract text from image.
        
        Args:
            image: Image as numpy array (BGR or grayscale)
            languages: Override language setting (e.g., 'eng' or 'eng+fra')
            psm: Page segmentation mode (1 = auto with OSD, 3 = auto without OSD)
            preprocess: Override preprocessing setting
        
        Returns:
            OCRResult with extracted text and metadata
        """
        import time
        start_time = time.time()
        
        # Use instance settings if not overridden
        lang = languages or self.languages
        do_preprocess = preprocess if preprocess is not None else self.preprocess_enabled
        
        # Preprocess image
        if do_preprocess and self.preprocessor:
            processed_image = self.preprocessor.preprocess(image)
        else:
            processed_image = image
        
        # Tesseract configuration
        config = f"--psm {psm} -l {lang}"
        
        # Extract text
        text = pytesseract.image_to_string(processed_image, config=config)
        
        # Get detailed data (words, confidence, positions)
        data = pytesseract.image_to_data(
            processed_image,
            config=config,
            output_type=pytesseract.Output.DICT
        )
        
        # Calculate average confidence
        word_confidences = [
            float(conf) for conf in data['conf'] 
            if conf != -1  # -1 means no confidence (e.g., empty line)
        ]
        avg_confidence = np.mean(word_confidences) if word_confidences else 0.0
        
        # Detect primary language
        detected_lang = self._detect_language(text, lang)
        
        # Build layout information
        layout = self._build_layout(data)
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        logger.info(f"OCR completed in {processing_time:.1f}ms, "
                   f"confidence: {avg_confidence:.1f}%, "
                   f"language: {detected_lang}")
        
        return OCRResult(
            text=text.strip(),
            confidence=avg_confidence / 100.0,  # Convert to 0-1 range
            language=detected_lang,
            layout=layout,
            word_confidences=word_confidences,
            processing_time_ms=processing_time
        )
    
    def extract_text_from_file(
        self,
        image_path: str,
        **kwargs
    ) -> OCRResult:
        """
        Extract text from image file.
        
        Args:
            image_path: Path to image file
            **kwargs: Additional arguments for extract_text()
        
        Returns:
            OCRResult
        """
        image = load_image(image_path)
        return self.extract_text(image, **kwargs)
    
    def extract_text_from_bytes(
        self,
        image_bytes: bytes,
        **kwargs
    ) -> OCRResult:
        """
        Extract text from image bytes (e.g., uploaded file).
        
        Args:
            image_bytes: Raw image bytes
            **kwargs: Additional arguments for extract_text()
        
        Returns:
            OCRResult
        """
        image = load_image_from_bytes(image_bytes)
        return self.extract_text(image, **kwargs)
    
    def _detect_language(self, text: str, available_langs: str) -> str:
        """
        Detect primary language from text.
        
        Args:
            text: Extracted text
            available_langs: Available language codes (e.g., 'eng+fra+ara')
        
        Returns:
            Detected language code ('en', 'fr', 'ar')
        """
        if not text or len(text) < 10:
            # Default to first language
            return available_langs.split('+')[0]
        
        # Count characters by script
        latin_chars = len(re.findall(r'[a-zA-ZÀ-ÿ]', text))
        arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
        
        # Determine language by script
        if arabic_chars > latin_chars:
            return 'ar'
        
        # Distinguish between English and French by common words
        text_lower = text.lower()
        
        # French indicators
        french_words = ['le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 
                       'et', 'pour', 'avec', 'dans', 'sur']
        french_count = sum(1 for word in french_words if f' {word} ' in text_lower)
        
        # English indicators
        english_words = ['the', 'of', 'and', 'to', 'in', 'for', 'on', 'with']
        english_count = sum(1 for word in english_words if f' {word} ' in text_lower)
        
        if french_count > english_count:
            return 'fr'
        
        return 'en'
    
    def _build_layout(self, data: Dict) -> Dict:
        """
        Build layout information from Tesseract data.
        
        Args:
            data: Tesseract output data dictionary
        
        Returns:
            Layout information with words, lines, paragraphs
        """
        layout = {
            'words': [],
            'lines': [],
            'paragraphs': []
        }
        
        # Extract words with positions
        for i, text in enumerate(data['text']):
            if not text.strip():
                continue
            
            confidence = data['conf'][i]
            if confidence == -1:
                continue
            
            word_info = {
                'text': text,
                'confidence': float(confidence),
                'bbox': {
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i]
                },
                'line_num': data['line_num'][i],
                'word_num': data['word_num'][i]
            }
            layout['words'].append(word_info)
        
        # Group by lines
        lines_dict = {}
        for word in layout['words']:
            line_num = word['line_num']
            if line_num not in lines_dict:
                lines_dict[line_num] = []
            lines_dict[line_num].append(word)
        
        # Build line information
        for line_num, words in sorted(lines_dict.items()):
            if not words:
                continue
            
            line_text = ' '.join(w['text'] for w in words)
            line_confidence = np.mean([w['confidence'] for w in words])
            
            # Calculate bounding box for entire line
            xs = [w['bbox']['x'] for w in words]
            ys = [w['bbox']['y'] for w in words]
            widths = [w['bbox']['width'] for w in words]
            heights = [w['bbox']['height'] for w in words]
            
            line_bbox = {
                'x': min(xs),
                'y': min(ys),
                'width': max(xs[i] + widths[i] for i in range(len(xs))) - min(xs),
                'height': max(heights)
            }
            
            layout['lines'].append({
                'text': line_text,
                'confidence': line_confidence,
                'bbox': line_bbox,
                'word_count': len(words)
            })
        
        return layout
    
    def get_text_with_boxes(
        self,
        image: np.ndarray,
        languages: Optional[str] = None
    ) -> Tuple[str, List[Dict]]:
        """
        Extract text with bounding boxes for each word.
        
        Useful for layout analysis and key-value extraction.
        
        Args:
            image: Image as numpy array
            languages: Language codes
        
        Returns:
            Tuple of (full_text, list of word boxes)
        """
        result = self.extract_text(image, languages=languages)
        
        boxes = []
        for word in result.layout['words']:
            boxes.append({
                'text': word['text'],
                'confidence': word['confidence'],
                'x': word['bbox']['x'],
                'y': word['bbox']['y'],
                'width': word['bbox']['width'],
                'height': word['bbox']['height']
            })
        
        return result.text, boxes
    
    def draw_boxes(
        self,
        image: np.ndarray,
        boxes: List[Dict],
        min_confidence: float = 0.0
    ) -> np.ndarray:
        """
        Draw bounding boxes on image (for debugging/visualization).
        
        Args:
            image: Image as numpy array
            boxes: List of word boxes from get_text_with_boxes()
            min_confidence: Only draw boxes with confidence >= this threshold
        
        Returns:
            Image with boxes drawn
        """
        output = image.copy()
        
        for box in boxes:
            if box['confidence'] < min_confidence:
                continue
            
            x, y, w, h = box['x'], box['y'], box['width'], box['height']
            
            # Color based on confidence (green = high, red = low)
            conf = box['confidence'] / 100.0
            color = (
                int(255 * (1 - conf)),  # Red component
                int(255 * conf),        # Green component
                0                        # Blue component
            )
            
            cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
            
            # Draw confidence text
            cv2.putText(
                output,
                f"{box['confidence']:.0f}%",
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1
            )
        
        return output


# Convenience function
def ocr_image(
    image_path: str,
    languages: str = 'eng+fra+ara',
    preprocess: bool = True
) -> str:
    """
    Quick OCR function for simple text extraction.
    
    Args:
        image_path: Path to image file
        languages: Language codes
        preprocess: Enable preprocessing
    
    Returns:
        Extracted text
    """
    engine = OCREngine(languages=languages, preprocess=preprocess)
    result = engine.extract_text_from_file(image_path)
    return result.text


# Example usage
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python engine.py <image_path>")
        sys.exit(1)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    image_path = sys.argv[0]
    
    # Create OCR engine
    engine = OCREngine(languages='eng+fra+ara')
    
    # Extract text
    result = engine.extract_text_from_file(image_path)
    
    print(f"\n{'='*60}")
    print("OCR RESULT")
    print(f"{'='*60}")
    print(f"Language: {result.language}")
    print(f"Confidence: {result.confidence:.1%}")
    print(f"Processing time: {result.processing_time_ms:.1f}ms")
    print(f"Words detected: {len(result.layout['words'])}")
    print(f"Lines detected: {len(result.layout['lines'])}")
    print(f"\n{'='*60}")
    print("EXTRACTED TEXT")
    print(f"{'='*60}")
    print(result.text)
    print(f"{'='*60}\n")
