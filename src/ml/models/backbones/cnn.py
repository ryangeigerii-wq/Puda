"""
CNN Backbones - Lightweight Convolutional Neural Networks

Implements efficient CNN architectures for document classification:
- MobileNetV3: Efficient mobile architecture (~2.5M params)
- ResNet18: Small ResNet variant (~11M params)
- EfficientNet-B0: Efficient scaling (~5M params)

Philosophy: Start with MobileNetV3, scale up only when proven necessary.
"""

from typing import Dict, Any, Optional
import torch
import torch.nn as nn

try:
    from torchvision.models import (
        mobilenet_v3_small,
        mobilenet_v3_large,
        resnet18,
        efficientnet_b0,
        MobileNet_V3_Small_Weights,
        MobileNet_V3_Large_Weights,
        ResNet18_Weights,
        EfficientNet_B0_Weights
    )
    TORCHVISION_AVAILABLE = True
except ImportError:
    TORCHVISION_AVAILABLE = False

from ..base import BaseClassifier
from ..registry import ModelRegistry


@ModelRegistry.register("mobilenet_v3_small")
class MobileNetV3Small(BaseClassifier):
    """
    MobileNetV3-Small for document classification.
    
    Lightweight CNN optimized for mobile/edge devices.
    
    Parameters:
        - Total: ~2.5M
        - Trainable (with frozen backbone): ~10K
    
    Performance:
        - Inference: 5-10ms per image (CPU)
        - Memory: ~10MB
    
    Args:
        num_classes: Number of document classes
        pretrained: Use ImageNet pretrained weights
        freeze_backbone: Freeze backbone for transfer learning
    """
    
    def __init__(
        self,
        num_classes: int = 10,
        pretrained: bool = True,
        freeze_backbone: bool = False
    ):
        super().__init__(num_classes=num_classes)
        
        if not TORCHVISION_AVAILABLE:
            raise ImportError("torchvision not installed. Install via: pip install torchvision")
        
        # Load backbone
        weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        self.backbone = mobilenet_v3_small(weights=weights)
        
        # Freeze backbone if requested
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False
        
        # Replace classifier head
        in_features = self.backbone.classifier[3].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Linear(in_features, 1024),
            nn.Hardswish(),
            nn.Dropout(p=0.2),
            nn.Linear(1024, num_classes)
        )
        
        self._pretrained = pretrained
        self._freeze_backbone = freeze_backbone
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input images [B, 3, 224, 224]
            
        Returns:
            Class logits [B, num_classes]
        """
        return self.backbone(x)
    
    def get_config(self) -> Dict[str, Any]:
        config = super().get_config()
        config.update({
            "pretrained": self._pretrained,
            "freeze_backbone": self._freeze_backbone
        })
        return config
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'MobileNetV3Small':
        return cls(
            num_classes=config["num_classes"],
            pretrained=config.get("pretrained", True),
            freeze_backbone=config.get("freeze_backbone", False)
        )


@ModelRegistry.register("mobilenet_v3_large")
class MobileNetV3Large(BaseClassifier):
    """
    MobileNetV3-Large for document classification.
    
    Larger variant with better accuracy, still efficient.
    
    Parameters: ~5.5M
    Inference: 10-15ms per image (CPU)
    
    Args:
        num_classes: Number of document classes
        pretrained: Use ImageNet pretrained weights
        freeze_backbone: Freeze backbone for transfer learning
    """
    
    def __init__(
        self,
        num_classes: int = 10,
        pretrained: bool = True,
        freeze_backbone: bool = False
    ):
        super().__init__(num_classes=num_classes)
        
        if not TORCHVISION_AVAILABLE:
            raise ImportError("torchvision not installed")
        
        weights = MobileNet_V3_Large_Weights.IMAGENET1K_V1 if pretrained else None
        self.backbone = mobilenet_v3_large(weights=weights)
        
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False
        
        in_features = self.backbone.classifier[3].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Linear(in_features, 1280),
            nn.Hardswish(),
            nn.Dropout(p=0.2),
            nn.Linear(1280, num_classes)
        )
        
        self._pretrained = pretrained
        self._freeze_backbone = freeze_backbone
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)
    
    def get_config(self) -> Dict[str, Any]:
        config = super().get_config()
        config.update({
            "pretrained": self._pretrained,
            "freeze_backbone": self._freeze_backbone
        })
        return config
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'MobileNetV3Large':
        return cls(
            num_classes=config["num_classes"],
            pretrained=config.get("pretrained", True),
            freeze_backbone=config.get("freeze_backbone", False)
        )


@ModelRegistry.register("resnet18")
class ResNet18Classifier(BaseClassifier):
    """
    ResNet-18 for document classification.
    
    Small ResNet variant, good baseline.
    
    Parameters: ~11M
    Inference: 15-20ms per image (CPU)
    
    Args:
        num_classes: Number of document classes
        pretrained: Use ImageNet pretrained weights
        freeze_backbone: Freeze backbone for transfer learning
    """
    
    def __init__(
        self,
        num_classes: int = 10,
        pretrained: bool = True,
        freeze_backbone: bool = False
    ):
        super().__init__(num_classes=num_classes)
        
        if not TORCHVISION_AVAILABLE:
            raise ImportError("torchvision not installed")
        
        weights = ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        self.backbone = resnet18(weights=weights)
        
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad = False
        
        in_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Linear(in_features, num_classes)
        
        self._pretrained = pretrained
        self._freeze_backbone = freeze_backbone
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)
    
    def get_config(self) -> Dict[str, Any]:
        config = super().get_config()
        config.update({
            "pretrained": self._pretrained,
            "freeze_backbone": self._freeze_backbone
        })
        return config
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'ResNet18Classifier':
        return cls(
            num_classes=config["num_classes"],
            pretrained=config.get("pretrained", True),
            freeze_backbone=config.get("freeze_backbone", False)
        )


# Default: Start with MobileNetV3-Small
DefaultClassifier = MobileNetV3Small
