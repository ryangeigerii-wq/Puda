"""
Puda ML Module - Modular Machine Learning for Document Processing

Design Philosophy:
- Everything modular: Models, data, and inference are completely separated
- Start light: Small transformer or CNN backbone, expand when proven necessary
- Clear separation: Each module has single responsibility
- Exportable: Every model exportable to ONNX for production deployment

Modules:
- ocr: Text extraction from images (Tesseract) - no torch required
- models: Model architectures (CNN, Transformer, Hybrid) + Export utilities
- data: Data loading, preprocessing, augmentation
- inference: Inference engine, batching, optimization
- training: Training loop, callbacks, metrics
"""

__version__ = "1.0.0"

# Lazy imports to avoid loading torch unnecessarily
__all__ = [
    "ModelRegistry",
    "InferenceEngine",
    "export_model",
    "OCREngine"
]

def __getattr__(name):
    """Lazy import to avoid loading heavy dependencies like torch."""
    if name == 'ModelRegistry':
        from .models import ModelRegistry
        return ModelRegistry
    elif name == 'export_model':
        from .models import export_model
        return export_model
    elif name == 'InferenceEngine':
        from .inference import InferenceEngine
        return InferenceEngine
    elif name == 'OCREngine':
        from .ocr import OCREngine
        return OCREngine
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
