"""
Model Registry

Central registry for all models in Puda ML system.
Enables easy model creation, loading, and management.

Usage:
    # Register a model
    @ModelRegistry.register("mobilenet_v3")
    class MobileNetV3Classifier(BaseClassifier):
        ...
    
    # Create model from registry
    model = ModelRegistry.create("mobilenet_v3", num_classes=10)
    
    # List available models
    models = ModelRegistry.list_models()
"""

from typing import Dict, Type, Any, Optional
from pathlib import Path
import json
from .base import BaseModel


class ModelRegistry:
    """
    Registry for model architectures.
    
    Provides factory pattern for model creation and management.
    """
    
    _registry: Dict[str, Type[BaseModel]] = {}
    _checkpoints: Dict[str, str] = {}
    
    @classmethod
    def register(cls, name: str):
        """
        Decorator to register a model class.
        
        Args:
            name: Unique model identifier
            
        Example:
            @ModelRegistry.register("my_model")
            class MyModel(BaseModel):
                ...
        """
        def decorator(model_class: Type[BaseModel]):
            if name in cls._registry:
                raise ValueError(f"Model '{name}' already registered")
            cls._registry[name] = model_class
            return model_class
        return decorator
    
    @classmethod
    def create(cls, name: str, **kwargs) -> BaseModel:
        """
        Create model instance from registry.
        
        Args:
            name: Registered model name
            **kwargs: Model initialization arguments
            
        Returns:
            Model instance
            
        Raises:
            ValueError: If model not registered
        """
        if name not in cls._registry:
            raise ValueError(
                f"Model '{name}' not registered. "
                f"Available models: {list(cls._registry.keys())}"
            )
        
        model_class = cls._registry[name]
        return model_class(**kwargs)
    
    @classmethod
    def register_checkpoint(cls, name: str, checkpoint_path: str):
        """
        Register a trained model checkpoint.
        
        Args:
            name: Model identifier
            checkpoint_path: Path to checkpoint file
        """
        if not Path(checkpoint_path).exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        cls._checkpoints[name] = checkpoint_path
    
    @classmethod
    def load(cls, name: str, device: str = "cpu") -> BaseModel:
        """
        Load model from registered checkpoint.
        
        Args:
            name: Registered checkpoint name
            device: Device to load model on
            
        Returns:
            Loaded model
            
        Raises:
            ValueError: If checkpoint not registered
        """
        if name not in cls._checkpoints:
            raise ValueError(
                f"Checkpoint '{name}' not registered. "
                f"Available checkpoints: {list(cls._checkpoints.keys())}"
            )
        
        checkpoint_path = cls._checkpoints[name]
        
        # Load checkpoint to determine model type
        import torch
        checkpoint = torch.load(checkpoint_path, map_location=device)
        config = checkpoint.get("config", {})
        model_type = config.get("architecture")
        
        if model_type not in cls._registry:
            raise ValueError(f"Model type '{model_type}' not registered")
        
        # Load using model class
        model_class = cls._registry[model_type]
        return model_class.load(checkpoint_path, device=device)
    
    @classmethod
    def list_models(cls) -> list:
        """List all registered model architectures."""
        return list(cls._registry.keys())
    
    @classmethod
    def list_checkpoints(cls) -> list:
        """List all registered checkpoints."""
        return list(cls._checkpoints.keys())
    
    @classmethod
    def get_model_info(cls, name: str) -> Dict[str, Any]:
        """
        Get information about a registered model.
        
        Args:
            name: Model name
            
        Returns:
            Dictionary with model information
        """
        if name not in cls._registry:
            raise ValueError(f"Model '{name}' not registered")
        
        model_class = cls._registry[name]
        return {
            "name": name,
            "class": model_class.__name__,
            "module": model_class.__module__,
            "doc": model_class.__doc__
        }


# Convenience function
def get_model(name: str, checkpoint: Optional[str] = None, **kwargs) -> BaseModel:
    """
    Get model from registry, optionally loading from checkpoint.
    
    Args:
        name: Model name
        checkpoint: Optional checkpoint name to load
        **kwargs: Model initialization arguments (if not loading checkpoint)
        
    Returns:
        Model instance
    """
    if checkpoint:
        return ModelRegistry.load(checkpoint)
    else:
        return ModelRegistry.create(name, **kwargs)
