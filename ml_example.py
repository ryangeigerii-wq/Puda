#!/usr/bin/env python3
"""
Puda ML Module - Example Usage

Demonstrates modular design:
- Models are separate from data
- Inference is separate from models
- Easy to swap components

Run:
    python ml_example.py
"""

import torch
from pathlib import Path


def example_1_basic_usage():
    """Example 1: Basic model creation and inference."""
    print("\n" + "="*60)
    print("Example 1: Basic Usage")
    print("="*60)
    
    from src.ml.models import ModelRegistry
    from src.ml.inference import InferenceEngine
    
    # Create lightweight model
    print("\n1. Creating MobileNetV3-Small (2.5M params)...")
    model = ModelRegistry.create(
        "mobilenet_v3_small",
        num_classes=10,
        pretrained=True
    )
    
    print(f"   ✓ Total parameters: {model.num_parameters:,}")
    print(f"   ✓ Trainable parameters: {model.num_trainable_parameters:,}")
    
    # Create inference engine
    print("\n2. Creating inference engine...")
    engine = InferenceEngine(model, device="cpu")
    
    print(f"   ✓ Device: {engine.device}")
    print(f"   ✓ Batch size: {engine.batch_size}")
    
    # Test with dummy input
    print("\n3. Testing with dummy input...")
    dummy_input = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        output = model(dummy_input)
    
    print(f"   ✓ Input shape: {dummy_input.shape}")
    print(f"   ✓ Output shape: {output.shape}")
    
    # Benchmark
    print("\n4. Benchmarking inference speed...")
    stats = engine.benchmark(num_iterations=50, warmup=5)
    print(f"   ✓ Average: {stats['mean_ms']:.2f}ms")
    print(f"   ✓ Min: {stats['min_ms']:.2f}ms")
    print(f"   ✓ Max: {stats['max_ms']:.2f}ms")


def example_2_model_comparison():
    """Example 2: Compare different models."""
    print("\n" + "="*60)
    print("Example 2: Model Comparison")
    print("="*60)
    
    from src.ml.models import ModelRegistry
    
    models_to_compare = [
        ("mobilenet_v3_small", "MobileNetV3-Small (Default)"),
        ("mobilenet_v3_large", "MobileNetV3-Large"),
        ("resnet18", "ResNet-18")
    ]
    
    print("\n{:<25} {:>15} {:>15}".format("Model", "Parameters", "Inference (ms)"))
    print("-" * 60)
    
    for model_name, display_name in models_to_compare:
        try:
            # Create model
            model = ModelRegistry.create(model_name, num_classes=10, pretrained=True)
            
            # Benchmark
            from src.ml.inference import InferenceEngine
            engine = InferenceEngine(model, device="cpu")
            stats = engine.benchmark(num_iterations=20, warmup=3)
            
            print("{:<25} {:>15,} {:>15.2f}".format(
                display_name,
                model.num_parameters,
                stats['mean_ms']
            ))
        except Exception as e:
            print(f"{display_name}: Error - {e}")


def example_3_modularity():
    """Example 3: Demonstrate modularity - swap components easily."""
    print("\n" + "="*60)
    print("Example 3: Modularity - Easy Component Swapping")
    print("="*60)
    
    from src.ml.models import ModelRegistry
    from src.ml.inference import InferenceEngine
    
    # Configuration-driven approach
    configs = [
        {"model": "mobilenet_v3_small", "optimize": False},
        {"model": "mobilenet_v3_small", "optimize": True},
        {"model": "resnet18", "optimize": False},
    ]
    
    print("\nTesting different configurations:\n")
    
    for i, config in enumerate(configs, 1):
        print(f"{i}. Model: {config['model']}, Optimize: {config['optimize']}")
        
        # Create model from config
        model = ModelRegistry.create(config['model'], num_classes=10)
        
        # Create engine with optimization
        engine = InferenceEngine(
            model,
            device="cpu",
            optimize=config['optimize']
        )
        
        # Quick benchmark
        stats = engine.benchmark(num_iterations=10, warmup=2)
        print(f"   → Inference: {stats['mean_ms']:.2f}ms")
        print()


def example_4_save_load():
    """Example 4: Save and load models."""
    print("\n" + "="*60)
    print("Example 4: Save and Load Models")
    print("="*60)
    
    from src.ml.models import ModelRegistry
    from src.ml.inference import InferenceEngine
    
    # Create models directory if it doesn't exist
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    checkpoint_path = models_dir / "example_classifier.pt"
    
    # 1. Create and save model
    print("\n1. Creating and saving model...")
    model = ModelRegistry.create("mobilenet_v3_small", num_classes=5)
    model.save(str(checkpoint_path))
    print(f"   ✓ Saved to: {checkpoint_path}")
    print(f"   ✓ File size: {checkpoint_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # 2. Load model
    print("\n2. Loading model from checkpoint...")
    loaded_model = ModelRegistry.create("mobilenet_v3_small", num_classes=5)
    loaded_model = loaded_model.load(str(checkpoint_path))
    print(f"   ✓ Loaded successfully")
    
    # 3. Use with inference engine
    print("\n3. Creating inference engine from checkpoint...")
    engine = InferenceEngine.from_checkpoint(str(checkpoint_path))
    print(f"   ✓ Engine ready")
    print(f"   ✓ Model: {engine.get_model_info()['architecture']}")
    
    # Cleanup
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print(f"\n   ✓ Cleaned up: {checkpoint_path}")


def example_5_registry():
    """Example 5: Model registry features."""
    print("\n" + "="*60)
    print("Example 5: Model Registry")
    print("="*60)
    
    from src.ml.models import ModelRegistry
    
    # List available models
    print("\n1. Available Models:")
    for model_name in ModelRegistry.list_models():
        print(f"   - {model_name}")
    
    # Get model info
    print("\n2. Model Information:")
    for model_name in ModelRegistry.list_models()[:2]:  # First 2 models
        info = ModelRegistry.get_model_info(model_name)
        print(f"\n   {info['name']}:")
        print(f"      Class: {info['class']}")
        print(f"      Module: {info['module']}")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Puda ML Module - Modular Design Examples")
    print("="*60)
    print("\nDesign Philosophy:")
    print("  ✓ Everything modular (models, data, inference separated)")
    print("  ✓ Start light (small CNN/transformer, scale when proven)")
    print("  ✓ Clear separation (each module has single responsibility)")
    
    try:
        # Check if torch is available
        import torch
        print(f"\nPyTorch Version: {torch.__version__}")
        print(f"CUDA Available: {torch.cuda.is_available()}")
        
        # Run examples
        example_1_basic_usage()
        example_2_model_comparison()
        example_3_modularity()
        example_4_save_load()
        example_5_registry()
        
        print("\n" + "="*60)
        print("✓ All examples completed successfully!")
        print("="*60)
        print("\nNext Steps:")
        print("  1. Install ML dependencies: pip install torch torchvision")
        print("  2. Read: src/ml/README.md")
        print("  3. Read: DESIGN_PHILOSOPHY.md")
        print("  4. Integrate with dashboard_api.py")
        print()
        
    except ImportError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease install dependencies:")
        print("  pip install torch torchvision")
        print()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
