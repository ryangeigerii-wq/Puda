"""
Backbones Module

Lightweight CNN backbones for document processing.
"""

from .cnn import (
    MobileNetV3Small,
    MobileNetV3Large,
    ResNet18Classifier,
    DefaultClassifier
)

__all__ = [
    "MobileNetV3Small",
    "MobileNetV3Large",
    "ResNet18Classifier",
    "DefaultClassifier",
]
