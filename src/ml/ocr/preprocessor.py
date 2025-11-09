"""
OCR preprocessing utilities for image enhancement.
Prepares images for optimal Tesseract OCR performance.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocesses images for OCR."""
    
    def __init__(self, target_dpi: int = 300):
        """
        Initialize preprocessor.
        
        Args:
            target_dpi: Target DPI for OCR (Tesseract works best at 300 DPI)
        """
        self.target_dpi = target_dpi
    
    def preprocess(
        self,
        image: np.ndarray,
        deskew: bool = True,
        denoise: bool = True,
        enhance_contrast: bool = True,
        binarize: bool = True
    ) -> np.ndarray:
        """
        Full preprocessing pipeline.
        
        Args:
            image: Input image (BGR or grayscale)
            deskew: Correct image rotation
            denoise: Remove noise
            enhance_contrast: Improve contrast
            binarize: Convert to binary (black/white)
        
        Returns:
            Preprocessed image
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        logger.debug(f"Original image shape: {gray.shape}")
        
        # Deskew
        if deskew:
            gray = self.deskew_image(gray)
        
        # Denoise
        if denoise:
            gray = self.denoise_image(gray)
        
        # Enhance contrast
        if enhance_contrast:
            gray = self.enhance_contrast(gray)
        
        # Binarize
        if binarize:
            gray = self.binarize_image(gray)
        
        logger.debug(f"Preprocessed image shape: {gray.shape}")
        return gray
    
    def deskew_image(self, image: np.ndarray) -> np.ndarray:
        """
        Detect and correct image skew.
        
        Args:
            image: Grayscale image
        
        Returns:
            Deskewed image
        """
        # Detect edges
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        
        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None:
            logger.debug("No lines detected for deskewing")
            return image
        
        # Calculate average angle
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            # Filter out near-horizontal and near-vertical lines
            if -45 < angle < 45:
                angles.append(angle)
        
        if not angles:
            logger.debug("No valid angles for deskewing")
            return image
        
        median_angle = np.median(angles)
        logger.debug(f"Detected skew angle: {median_angle:.2f}°")
        
        # Only correct if angle is significant (>0.5 degrees)
        if abs(median_angle) > 0.5:
            # Rotate image
            (h, w) = image.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            logger.debug(f"Corrected skew by {median_angle:.2f}°")
            return rotated
        
        return image
    
    def denoise_image(self, image: np.ndarray) -> np.ndarray:
        """
        Remove noise from image.
        
        Args:
            image: Grayscale image
        
        Returns:
            Denoised image
        """
        # Use Non-local Means Denoising
        denoised = cv2.fastNlMeansDenoising(
            image,
            h=10,  # Filter strength (higher = more denoising)
            templateWindowSize=7,
            searchWindowSize=21
        )
        logger.debug("Applied denoising")
        return denoised
    
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance image contrast using CLAHE.
        
        Args:
            image: Grayscale image
        
        Returns:
            Contrast-enhanced image
        """
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        logger.debug("Enhanced contrast with CLAHE")
        return enhanced
    
    def binarize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Convert to binary (black/white) using adaptive thresholding.
        
        Args:
            image: Grayscale image
        
        Returns:
            Binary image
        """
        # Adaptive threshold (better than global threshold for varied lighting)
        binary = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2
        )
        logger.debug("Applied adaptive binarization")
        return binary
    
    def resize_to_dpi(
        self,
        image: np.ndarray,
        current_dpi: Optional[int] = None
    ) -> np.ndarray:
        """
        Resize image to target DPI.
        
        Args:
            image: Input image
            current_dpi: Current image DPI (if known)
        
        Returns:
            Resized image
        """
        if current_dpi is None:
            # Assume 72 DPI if unknown
            current_dpi = 72
        
        scale = self.target_dpi / current_dpi
        
        if abs(scale - 1.0) < 0.1:
            # No need to resize
            return image
        
        new_width = int(image.shape[1] * scale)
        new_height = int(image.shape[0] * scale)
        
        resized = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
        )
        
        logger.debug(f"Resized from {current_dpi} to {self.target_dpi} DPI: "
                    f"{image.shape} → {resized.shape}")
        return resized
    
    def remove_borders(self, image: np.ndarray, border_size: int = 10) -> np.ndarray:
        """
        Remove border noise from image edges.
        
        Args:
            image: Input image
            border_size: Border width to remove (pixels)
        
        Returns:
            Image with borders removed
        """
        h, w = image.shape[:2]
        cropped = image[border_size:h-border_size, border_size:w-border_size]
        logger.debug(f"Removed {border_size}px borders")
        return cropped
    
    def correct_orientation(self, image: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Detect and correct image orientation (0°, 90°, 180°, 270°).
        
        Uses Tesseract's OSD (Orientation and Script Detection).
        
        Args:
            image: Input image
        
        Returns:
            Tuple of (corrected_image, rotation_angle)
        """
        try:
            import pytesseract
            
            # Get orientation info from Tesseract
            osd = pytesseract.image_to_osd(image)
            
            # Parse rotation angle
            rotation = int([line for line in osd.split('\n') 
                          if 'Rotate' in line][0].split(':')[1].strip())
            
            if rotation == 0:
                return image, 0
            
            # Rotate image
            if rotation == 90:
                rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            elif rotation == 180:
                rotated = cv2.rotate(image, cv2.ROTATE_180)
            elif rotation == 270:
                rotated = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            else:
                rotated = image
            
            logger.debug(f"Corrected orientation: {rotation}° rotation")
            return rotated, rotation
            
        except Exception as e:
            logger.warning(f"Could not detect orientation: {e}")
            return image, 0


def load_image(image_path: str) -> np.ndarray:
    """
    Load image from file path.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Image as numpy array (BGR)
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    return image


def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """
    Load image from bytes (e.g., uploaded file).
    
    Args:
        image_bytes: Raw image bytes
    
    Returns:
        Image as numpy array (BGR)
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    # Decode image
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image from bytes")
    return image


def save_image(image: np.ndarray, output_path: str) -> None:
    """
    Save image to file.
    
    Args:
        image: Image as numpy array
        output_path: Output file path
    """
    cv2.imwrite(output_path, image)
    logger.debug(f"Saved image to {output_path}")
