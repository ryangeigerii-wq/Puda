"""
Base Model Classes

Abstract base classes for all models in Puda ML system.
Ensures consistent interface across different architectures.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import torch
import torch.nn as nn


class BaseModel(nn.Module, ABC):
    """
    Abstract base class for all Puda ML models.
    
    All models must implement:
    - forward(): Forward pass
    - get_config(): Return model configuration
    - from_config(): Create model from configuration
    """
    
    def __init__(self):
        super().__init__()
        self._version = "1.0.0"
        self._name = self.__class__.__name__
    
    @abstractmethod
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the model.
        
        Args:
            x: Input tensor
            
        Returns:
            Output tensor
        """
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get model configuration for serialization.
        
        Returns:
            Dictionary with model configuration
        """
        return {
            "name": self._name,
            "version": self._version,
            "architecture": self.__class__.__name__
        }
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> 'BaseModel':
        """
        Create model from configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Model instance
        """
        pass
    
    def save(self, path: str):
        """
        Save model checkpoint.
        
        Args:
            path: Path to save checkpoint
        """
        checkpoint = {
            "model_state_dict": self.state_dict(),
            "config": self.get_config()
        }
        torch.save(checkpoint, path)
    
    @classmethod
    def load(cls, path: str, device: str = "cpu") -> 'BaseModel':
        """
        Load model from checkpoint.
        
        Args:
            path: Path to checkpoint
            device: Device to load model on
            
        Returns:
            Loaded model
        """
        checkpoint = torch.load(path, map_location=device)
        model = cls.from_config(checkpoint["config"])
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        return model
    
    @property
    def num_parameters(self) -> int:
        """Get total number of model parameters."""
        return sum(p.numel() for p in self.parameters())
    
    @property
    def num_trainable_parameters(self) -> int:
        """Get number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class BaseClassifier(BaseModel):
    """
    Base class for classification models.
    
    Adds classification-specific functionality on top of BaseModel.
    """
    
    def __init__(self, num_classes: int):
        super().__init__()
        self.num_classes = num_classes
    
    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """
        Get class predictions.
        
        Args:
            x: Input tensor
            
        Returns:
            Class indices
        """
        logits = self.forward(x)
        return torch.argmax(logits, dim=-1)
    
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """
        Get class probabilities.
        
        Args:
            x: Input tensor
            
        Returns:
            Class probabilities
        """
        logits = self.forward(x)
        return torch.softmax(logits, dim=-1)
    
    def get_config(self) -> Dict[str, Any]:
        config = super().get_config()
        config["num_classes"] = self.num_classes
        return config
