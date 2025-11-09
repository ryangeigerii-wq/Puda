"""
Models Module - Model Architectures for Puda ML

Provides model architectures following modular design:
- Backbones: CNN, Transformer, Hybrid architectures
- Heads: Classification, detection, segmentation
- Registry: Central model management
- Export: ONNX, TorchScript, Quantized exports

Start lightweight: MobileNetV3-Small (~2.5M params)
Every model is exportable to ONNX for production deployment.
"""

from .base import BaseModel, BaseClassifier
from .registry import ModelRegistry, get_model
from .backbones.cnn import (
    MobileNetV3Small,
    MobileNetV3Large,
    ResNet18Classifier,
    DefaultClassifier
)
from .export import ModelExporter, export_model

__all__ = [
    "BaseModel",
    "BaseClassifier",
    "ModelRegistry",
    "get_model",
    "MobileNetV3Small",
    "MobileNetV3Large",
    "ResNet18Classifier",
    "DefaultClassifier",
    "ModelExporter",
    "export_model",
]
