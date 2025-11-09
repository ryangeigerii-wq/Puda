#!/usr/bin/env python3
"""
Model Export Examples

Demonstrates ONNX export capabilities for all Puda ML models.

Philosophy: Every model must be exportable for production deployment.

Run:
    python export_example.py
"""

from pathlib import Path


def example_1_basic_onnx_export():
    """Example 1: Basic ONNX export."""
    print("\n" + "="*60)
    print("Example 1: Basic ONNX Export")
    print("="*60)
    
    from src.ml.models import ModelRegistry, export_model
    
    # Create model
    print("\n1. Creating MobileNetV3-Small...")
    model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
    print(f"   ✓ Parameters: {model.num_parameters:,}")
    
    # Export to ONNX
    print("\n2. Exporting to ONNX...")
    result = export_model(
        model,
        "exports/mobilenet_v3_small.onnx",
        format="onnx"
    )
    
    print(f"\n   Export Results:")
    print(f"   - File size: {result['file_size_mb']:.2f} MB")
    print(f"   - Opset version: {result['opset_version']}")
    print(f"   - Optimized: {result['optimized']}")


def example_2_verify_export():
    """Example 2: Export and verify ONNX model."""
    print("\n" + "="*60)
    print("Example 2: Export and Verify ONNX")
    print("="*60)
    
    from src.ml.models import ModelRegistry, ModelExporter
    
    # Create model
    print("\n1. Creating model...")
    model = ModelRegistry.create("mobilenet_v3_small", num_classes=5)
    
    # Create exporter
    exporter = ModelExporter(model, input_shape=(1, 3, 224, 224))
    
    # Export
    print("\n2. Exporting to ONNX...")
    onnx_path = "exports/mobilenet_verified.onnx"
    exporter.export_onnx(onnx_path, optimize=True)
    
    # Verify
    print("\n3. Verifying export...")
    verification = exporter.verify_onnx(onnx_path, num_tests=10)
    
    if verification["passed"]:
        print("\n   ✓ Verification PASSED")
        print(f"   - Max difference: {verification['max_difference']:.2e}")
    else:
        print("\n   ✗ Verification FAILED")


def example_3_export_all_formats():
    """Example 3: Export to all formats."""
    print("\n" + "="*60)
    print("Example 3: Export to All Formats")
    print("="*60)
    
    from src.ml.models import ModelRegistry, export_model
    
    # Create model
    print("\nCreating model...")
    model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
    
    # Export to all formats
    print("\nExporting to all formats...")
    results = export_model(
        model,
        "exports/mobilenet_complete",
        format="all"
    )
    
    # Print summary
    print("\nExport Summary:")
    print("-" * 60)
    
    formats = ["onnx", "torchscript", "quantized"]
    for fmt in formats:
        if fmt in results and "error" not in results[fmt]:
            size = results[fmt].get("file_size_mb", 0)
            print(f"  {fmt.upper():<15} {size:>8.2f} MB")
            
            # Show reduction for quantized
            if fmt == "quantized" and "size_reduction_percent" in results[fmt]:
                reduction = results[fmt]["size_reduction_percent"]
                print(f"  {'':15} ({reduction:>5.1f}% smaller)")
        else:
            error = results.get(fmt, {}).get("error", "Unknown error")
            print(f"  {fmt.upper():<15} {'ERROR'}")


def example_4_compare_models():
    """Example 4: Export and compare multiple models."""
    print("\n" + "="*60)
    print("Example 4: Compare Model Exports")
    print("="*60)
    
    from src.ml.models import ModelRegistry, ModelExporter
    
    models_to_export = [
        "mobilenet_v3_small",
        "mobilenet_v3_large",
        "resnet18"
    ]
    
    print("\n{:<25} {:>12} {:>12} {:>12}".format(
        "Model", "PyTorch (MB)", "ONNX (MB)", "Reduction"
    ))
    print("-" * 65)
    
    for model_name in models_to_export:
        try:
            # Create model
            model = ModelRegistry.create(model_name, num_classes=10)
            
            # Calculate PyTorch size
            pytorch_size = sum(
                p.numel() * p.element_size() 
                for p in model.parameters()
            ) / 1024 / 1024
            
            # Export to ONNX
            exporter = ModelExporter(model)
            onnx_path = f"exports/{model_name}.onnx"
            result = exporter.export_onnx(onnx_path, optimize=True)
            
            onnx_size = result["file_size_mb"]
            reduction = (1 - onnx_size / pytorch_size) * 100
            
            print("{:<25} {:>12.2f} {:>12.2f} {:>11.1f}%".format(
                model_name,
                pytorch_size,
                onnx_size,
                reduction
            ))
            
        except Exception as e:
            print(f"{model_name:<25} Error: {e}")


def example_5_dynamic_batch_size():
    """Example 5: Export with dynamic batch size."""
    print("\n" + "="*60)
    print("Example 5: Dynamic Batch Size Export")
    print("="*60)
    
    from src.ml.models import ModelRegistry, ModelExporter
    import torch
    
    # Create model
    print("\n1. Creating model...")
    model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
    
    # Export with dynamic batch size
    print("\n2. Exporting with dynamic batch size...")
    exporter = ModelExporter(model, input_shape=(1, 3, 224, 224))
    
    dynamic_axes = {
        "input": {0: "batch_size"},
        "output": {0: "batch_size"}
    }
    
    result = exporter.export_onnx(
        "exports/mobilenet_dynamic.onnx",
        dynamic_axes=dynamic_axes
    )
    
    print("\n3. Testing different batch sizes...")
    
    try:
        import onnxruntime as ort
        
        session = ort.InferenceSession("exports/mobilenet_dynamic.onnx")
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        # Test different batch sizes
        for batch_size in [1, 4, 8, 16]:
            test_input = torch.randn(batch_size, 3, 224, 224).numpy()
            output = session.run(
                [output_name],
                {input_name: test_input}
            )[0]
            
            print(f"   ✓ Batch size {batch_size:2d}: Output shape {output.shape}")
            
    except ImportError:
        print("   ⚠ onnxruntime not installed, skipping test")


def example_6_production_deployment():
    """Example 6: Production deployment workflow."""
    print("\n" + "="*60)
    print("Example 6: Production Deployment Workflow")
    print("="*60)
    
    from src.ml.models import ModelRegistry, ModelExporter
    
    # 1. Train/load model (simulated here)
    print("\n1. Loading trained model...")
    model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
    print("   ✓ Model loaded")
    
    # 2. Export to ONNX for production
    print("\n2. Exporting for production deployment...")
    exporter = ModelExporter(model)
    
    production_dir = Path("production")
    production_dir.mkdir(exist_ok=True)
    
    onnx_path = production_dir / "classifier.onnx"
    result = exporter.export_onnx(str(onnx_path), optimize=True)
    
    print(f"   ✓ ONNX model: {onnx_path}")
    print(f"   ✓ Size: {result['file_size_mb']:.2f} MB")
    
    # 3. Verify export
    print("\n3. Verifying production model...")
    verification = exporter.verify_onnx(str(onnx_path), num_tests=100)
    
    if verification["passed"]:
        print("   ✓ Verification passed - Ready for deployment")
    else:
        print("   ✗ Verification failed - DO NOT DEPLOY")
        return
    
    # 4. Benchmark ONNX performance
    print("\n4. Benchmarking ONNX performance...")
    
    try:
        import onnxruntime as ort
        import time
        import numpy as np
        
        session = ort.InferenceSession(str(onnx_path))
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        # Warmup
        dummy_input = np.random.randn(1, 3, 224, 224).astype(np.float32)
        for _ in range(10):
            session.run([output_name], {input_name: dummy_input})
        
        # Benchmark
        times = []
        for _ in range(100):
            start = time.perf_counter()
            session.run([output_name], {input_name: dummy_input})
            end = time.perf_counter()
            times.append((end - start) * 1000)
        
        print(f"   ✓ Average inference: {np.mean(times):.2f}ms")
        print(f"   ✓ Min: {np.min(times):.2f}ms")
        print(f"   ✓ Max: {np.max(times):.2f}ms")
        
        print("\n5. Deployment checklist:")
        print("   ✓ Model exported to ONNX")
        print("   ✓ Export verified (outputs match PyTorch)")
        print("   ✓ Performance benchmarked")
        print("   ✓ Ready for production deployment")
        
    except ImportError:
        print("   ⚠ onnxruntime not installed")


def main():
    """Run all export examples."""
    print("\n" + "="*60)
    print("Puda ML - Model Export Examples")
    print("="*60)
    print("\nPhilosophy: Every model must be exportable to ONNX")
    print("            for production deployment across platforms.")
    
    # Create exports directory
    Path("exports").mkdir(exist_ok=True)
    
    try:
        # Check dependencies
        import torch
        print(f"\nPyTorch version: {torch.__version__}")
        
        try:
            import onnx
            import onnxruntime
            print(f"ONNX available: Yes")
            print(f"  onnx: {onnx.__version__}")
            print(f"  onnxruntime: {onnxruntime.__version__}")
        except ImportError:
            print(f"ONNX available: No (install: pip install onnx onnxruntime)")
        
        # Run examples
        example_1_basic_onnx_export()
        
        try:
            example_2_verify_export()
            example_3_export_all_formats()
            example_4_compare_models()
            example_5_dynamic_batch_size()
            example_6_production_deployment()
        except ImportError as e:
            print(f"\n⚠ Some examples skipped: {e}")
            print("   Install ONNX: pip install onnx onnxruntime")
        
        print("\n" + "="*60)
        print("✓ Export examples completed!")
        print("="*60)
        print("\nNext Steps:")
        print("  1. Install ONNX: pip install onnx onnxruntime")
        print("  2. Export your trained model: export_model(model, 'model.onnx')")
        print("  3. Deploy with ONNX Runtime (Python, C++, JavaScript, etc.)")
        print("  4. See: src/ml/models/export.py for full API")
        print()
        
    except ImportError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease install dependencies:")
        print("  pip install torch torchvision")
        print("  pip install onnx onnxruntime  # For ONNX export")
        print()


if __name__ == "__main__":
    main()
