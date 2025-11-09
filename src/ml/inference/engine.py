"""
Inference Engine - Modular Inference System

Handles model inference separate from model definition.
Supports batching, streaming, and optimization.

Philosophy: Inference logic should be independent of model architecture.
"""

from typing import Union, List, Dict, Any, Optional
from pathlib import Path
import torch
import numpy as np
from PIL import Image

from ..models import BaseModel, ModelRegistry


class InferenceEngine:
    """
    Modular inference engine for Puda ML models.
    
    Separates inference logic from model architecture.
    Handles preprocessing, batching, and post-processing.
    
    Args:
        model: Model instance or checkpoint name
        device: Device to run inference on ("cpu", "cuda", "cuda:0")
        batch_size: Batch size for batch inference
        optimize: Enable optimization (quantization, TorchScript)
    
    Example:
        # From model instance
        model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
        engine = InferenceEngine(model, device="cuda")
        
        # From checkpoint
        engine = InferenceEngine.from_checkpoint("models/classifier.pt")
        
        # Inference
        result = engine.predict_single("scan.jpg")
        results = engine.predict_batch(["scan1.jpg", "scan2.jpg"])
    """
    
    def __init__(
        self,
        model: Union[BaseModel, str],
        device: str = "cpu",
        batch_size: int = 32,
        optimize: bool = False
    ):
        # Load model if string (checkpoint name)
        if isinstance(model, str):
            self.model = ModelRegistry.load(model, device=device)
        else:
            self.model = model
            self.model.to(device)
        
        self.device = device
        self.batch_size = batch_size
        
        # Set to evaluation mode
        self.model.eval()
        
        # Optimize if requested
        if optimize:
            self._optimize_model()
    
    @classmethod
    def from_checkpoint(cls, checkpoint_path: str, device: str = "cpu", **kwargs):
        """
        Create engine from checkpoint file.
        
        Args:
            checkpoint_path: Path to model checkpoint
            device: Device to load on
            **kwargs: Additional InferenceEngine arguments
            
        Returns:
            InferenceEngine instance
        """
        checkpoint = torch.load(checkpoint_path, map_location=device)
        config = checkpoint["config"]
        architecture = config["architecture"]
        
        # Load model from config
        model_class = ModelRegistry._registry.get(architecture)
        if model_class is None:
            raise ValueError(f"Unknown architecture: {architecture}")
        
        model = model_class.from_config(config)
        model.load_state_dict(checkpoint["model_state_dict"])
        
        return cls(model, device=device, **kwargs)
    
    def _optimize_model(self):
        """Apply optimization techniques (quantization, scripting)."""
        try:
            # Dynamic quantization for CPU inference
            if self.device == "cpu":
                self.model = torch.quantization.quantize_dynamic(
                    self.model,
                    {torch.nn.Linear},
                    dtype=torch.qint8
                )
            
            # TorchScript compilation
            self.model = torch.jit.script(self.model)
        except Exception as e:
            print(f"Warning: Optimization failed: {e}")
    
    def _load_image(self, image_path: Union[str, Path]) -> torch.Tensor:
        """
        Load and preprocess image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Preprocessed tensor [1, 3, 224, 224]
        """
        image = Image.open(image_path).convert("RGB")
        
        # Simple preprocessing (should use data module in production)
        import torchvision.transforms as transforms
        
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        tensor = transform(image).unsqueeze(0)  # Add batch dimension
        return tensor.to(self.device)
    
    def predict_single(
        self,
        image_path: Union[str, Path],
        return_probabilities: bool = True
    ) -> Dict[str, Any]:
        """
        Predict single image.
        
        Args:
            image_path: Path to image
            return_probabilities: Return class probabilities
            
        Returns:
            Dictionary with prediction results:
            {
                "class": int,
                "confidence": float,
                "probabilities": List[float]  # if return_probabilities
            }
        """
        with torch.no_grad():
            # Load and preprocess
            image_tensor = self._load_image(image_path)
            
            # Forward pass
            logits = self.model(image_tensor)
            probabilities = torch.softmax(logits, dim=-1)
            
            # Get prediction
            confidence, predicted_class = torch.max(probabilities, dim=-1)
            
            result = {
                "class": predicted_class.item(),
                "confidence": confidence.item()
            }
            
            if return_probabilities:
                result["probabilities"] = probabilities[0].cpu().numpy().tolist()
            
            return result
    
    def predict_batch(
        self,
        image_paths: List[Union[str, Path]],
        return_probabilities: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Predict batch of images.
        
        Args:
            image_paths: List of image paths
            return_probabilities: Return class probabilities
            
        Returns:
            List of prediction dictionaries
        """
        results = []
        
        # Process in batches
        for i in range(0, len(image_paths), self.batch_size):
            batch_paths = image_paths[i:i + self.batch_size]
            
            with torch.no_grad():
                # Load batch
                batch_tensors = [self._load_image(path) for path in batch_paths]
                batch = torch.cat(batch_tensors, dim=0)
                
                # Forward pass
                logits = self.model(batch)
                probabilities = torch.softmax(logits, dim=-1)
                
                # Get predictions
                confidences, predicted_classes = torch.max(probabilities, dim=-1)
                
                # Convert to results
                for j in range(len(batch_paths)):
                    result = {
                        "class": predicted_classes[j].item(),
                        "confidence": confidences[j].item()
                    }
                    
                    if return_probabilities:
                        result["probabilities"] = probabilities[j].cpu().numpy().tolist()
                    
                    results.append(result)
        
        return results
    
    def benchmark(self, num_iterations: int = 100, warmup: int = 10) -> Dict[str, float]:
        """
        Benchmark inference performance.
        
        Args:
            num_iterations: Number of iterations for timing
            warmup: Number of warmup iterations
            
        Returns:
            Dictionary with timing statistics
        """
        import time
        
        # Create dummy input
        dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
        
        # Warmup
        with torch.no_grad():
            for _ in range(warmup):
                _ = self.model(dummy_input)
        
        # Benchmark
        times = []
        with torch.no_grad():
            for _ in range(num_iterations):
                start = time.perf_counter()
                _ = self.model(dummy_input)
                end = time.perf_counter()
                times.append((end - start) * 1000)  # Convert to ms
        
        return {
            "mean_ms": np.mean(times),
            "std_ms": np.std(times),
            "min_ms": np.min(times),
            "max_ms": np.max(times),
            "median_ms": np.median(times)
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "architecture": self.model.__class__.__name__,
            "device": self.device,
            "num_parameters": self.model.num_parameters,
            "num_trainable_parameters": self.model.num_trainable_parameters,
            "batch_size": self.batch_size
        }
