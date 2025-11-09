"""
Model Export Utilities

Export Puda ML models to different formats:
- ONNX: Cross-platform inference (TensorRT, ONNX Runtime, etc.)
- TorchScript: Optimized PyTorch format
- Quantized: Reduced size for mobile/edge

Philosophy: Every model must be exportable for production deployment.
"""

from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import json
import torch
import torch.nn as nn

try:
    import onnx
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


class ModelExporter:
    """
    Export models to various formats.
    
    Ensures every model can be deployed in production environments
    that don't support PyTorch natively.
    
    Supported formats:
    - ONNX: Cross-platform standard
    - TorchScript: PyTorch optimized
    - Quantized: Mobile/edge deployment
    
    Example:
        model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
        exporter = ModelExporter(model)
        
        # Export to ONNX
        exporter.export_onnx("model.onnx")
        
        # Verify export
        exporter.verify_onnx("model.onnx")
    """
    
    def __init__(self, model: nn.Module, input_shape: Tuple[int, ...] = (1, 3, 224, 224)):
        """
        Initialize exporter.
        
        Args:
            model: PyTorch model to export
            input_shape: Model input shape (batch, channels, height, width)
        """
        self.model = model
        self.input_shape = input_shape
        self.model.eval()
    
    def export_onnx(
        self,
        output_path: str,
        opset_version: int = 14,
        optimize: bool = True,
        dynamic_axes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export model to ONNX format.
        
        Args:
            output_path: Path to save ONNX model
            opset_version: ONNX opset version (11-17 supported)
            optimize: Apply ONNX optimization passes
            dynamic_axes: Dynamic axes for variable batch size
                         e.g., {"input": {0: "batch"}, "output": {0: "batch"}}
        
        Returns:
            Dictionary with export metadata
        
        Raises:
            ImportError: If onnx not installed
        """
        if not ONNX_AVAILABLE:
            raise ImportError(
                "ONNX not installed. Install via: pip install onnx onnxruntime"
            )
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create dummy input
        dummy_input = torch.randn(*self.input_shape)
        
        # Default dynamic axes for batch dimension
        if dynamic_axes is None:
            dynamic_axes = {
                "input": {0: "batch_size"},
                "output": {0: "batch_size"}
            }
        
        print(f"Exporting to ONNX...")
        print(f"  Input shape: {self.input_shape}")
        print(f"  Opset version: {opset_version}")
        print(f"  Dynamic axes: {dynamic_axes is not None}")
        
        # Export to ONNX
        torch.onnx.export(
            self.model,
            dummy_input,
            str(output_path),
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes=dynamic_axes
        )
        
        print(f"  ✓ Exported to: {output_path}")
        
        # Optimize ONNX model
        if optimize:
            self._optimize_onnx(output_path)
        
        # Get metadata
        file_size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"  ✓ File size: {file_size_mb:.2f} MB")
        
        # Save metadata
        metadata = {
            "format": "onnx",
            "opset_version": opset_version,
            "input_shape": list(self.input_shape),
            "dynamic_axes": dynamic_axes is not None,
            "optimized": optimize,
            "file_size_mb": file_size_mb,
            "model_class": self.model.__class__.__name__
        }
        
        metadata_path = output_path.with_suffix(".json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"  ✓ Metadata saved: {metadata_path}")
        
        return metadata
    
    def _optimize_onnx(self, model_path: Path):
        """
        Apply ONNX optimization passes.
        
        Args:
            model_path: Path to ONNX model
        """
        try:
            import onnx
            from onnx import optimizer
            
            print("  Optimizing ONNX model...")
            
            # Load model
            onnx_model = onnx.load(str(model_path))
            
            # Apply optimization passes
            passes = [
                "eliminate_identity",
                "eliminate_nop_transpose",
                "eliminate_nop_pad",
                "eliminate_unused_initializer",
                "fuse_consecutive_transposes",
                "fuse_matmul_add_bias_into_gemm",
                "fuse_pad_into_conv",
            ]
            
            optimized_model = optimizer.optimize(onnx_model, passes)
            
            # Save optimized model
            onnx.save(optimized_model, str(model_path))
            
            print("  ✓ ONNX optimization complete")
            
        except Exception as e:
            print(f"  ⚠ Optimization failed: {e}")
    
    def verify_onnx(
        self,
        onnx_path: str,
        tolerance: float = 1e-5,
        num_tests: int = 5
    ) -> Dict[str, Any]:
        """
        Verify ONNX export by comparing outputs with PyTorch.
        
        Args:
            onnx_path: Path to ONNX model
            tolerance: Maximum allowed difference
            num_tests: Number of random inputs to test
        
        Returns:
            Dictionary with verification results
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX Runtime not installed")
        
        print(f"\nVerifying ONNX export...")
        
        # Load ONNX model
        ort_session = ort.InferenceSession(str(onnx_path))
        
        # Get input/output names
        input_name = ort_session.get_inputs()[0].name
        output_name = ort_session.get_outputs()[0].name
        
        print(f"  Input: {input_name}")
        print(f"  Output: {output_name}")
        
        max_diff = 0.0
        all_passed = True
        
        with torch.no_grad():
            for i in range(num_tests):
                # Generate random input
                test_input = torch.randn(*self.input_shape)
                
                # PyTorch inference
                torch_output = self.model(test_input).cpu().numpy()
                
                # ONNX inference
                onnx_output = ort_session.run(
                    [output_name],
                    {input_name: test_input.cpu().numpy()}
                )[0]
                
                # Compare
                diff = abs(torch_output - onnx_output).max()
                max_diff = max(max_diff, diff)
                
                if diff > tolerance:
                    all_passed = False
                    print(f"  ✗ Test {i+1}: diff = {diff:.2e} (exceeds tolerance)")
                else:
                    print(f"  ✓ Test {i+1}: diff = {diff:.2e}")
        
        print(f"\nVerification {'PASSED' if all_passed else 'FAILED'}")
        print(f"  Max difference: {max_diff:.2e}")
        print(f"  Tolerance: {tolerance:.2e}")
        
        return {
            "passed": all_passed,
            "max_difference": float(max_diff),
            "tolerance": tolerance,
            "num_tests": num_tests
        }
    
    def export_torchscript(
        self,
        output_path: str,
        method: str = "trace"
    ) -> Dict[str, Any]:
        """
        Export model to TorchScript format.
        
        Args:
            output_path: Path to save TorchScript model
            method: Export method ("trace" or "script")
        
        Returns:
            Dictionary with export metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Exporting to TorchScript...")
        print(f"  Method: {method}")
        
        # Create dummy input
        dummy_input = torch.randn(*self.input_shape)
        
        # Export
        if method == "trace":
            traced_model = torch.jit.trace(self.model, dummy_input)
        elif method == "script":
            traced_model = torch.jit.script(self.model)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Save
        traced_model.save(str(output_path))
        
        file_size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"  ✓ Exported to: {output_path}")
        print(f"  ✓ File size: {file_size_mb:.2f} MB")
        
        return {
            "format": "torchscript",
            "method": method,
            "file_size_mb": file_size_mb
        }
    
    def export_quantized(
        self,
        output_path: str,
        quantization_type: str = "dynamic"
    ) -> Dict[str, Any]:
        """
        Export quantized model (INT8).
        
        Args:
            output_path: Path to save quantized model
            quantization_type: "dynamic" or "static"
        
        Returns:
            Dictionary with export metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Exporting quantized model...")
        print(f"  Type: {quantization_type}")
        
        if quantization_type == "dynamic":
            # Dynamic quantization (easiest, good for CPU)
            quantized_model = torch.quantization.quantize_dynamic(
                self.model,
                {torch.nn.Linear, torch.nn.Conv2d},
                dtype=torch.qint8
            )
        else:
            raise NotImplementedError(f"Quantization type '{quantization_type}' not implemented")
        
        # Save
        torch.save({
            "model_state_dict": quantized_model.state_dict(),
            "quantization_type": quantization_type
        }, str(output_path))
        
        file_size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"  ✓ Exported to: {output_path}")
        print(f"  ✓ File size: {file_size_mb:.2f} MB")
        
        # Compare sizes
        original_size = sum(p.numel() * p.element_size() for p in self.model.parameters()) / 1024 / 1024
        reduction = (1 - file_size_mb / original_size) * 100
        print(f"  ✓ Size reduction: {reduction:.1f}%")
        
        return {
            "format": "quantized_pytorch",
            "quantization_type": quantization_type,
            "file_size_mb": file_size_mb,
            "size_reduction_percent": reduction
        }
    
    def export_all(self, output_dir: str, base_name: str = "model") -> Dict[str, Any]:
        """
        Export model to all formats.
        
        Args:
            output_dir: Directory to save exports
            base_name: Base filename (without extension)
        
        Returns:
            Dictionary with all export results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("="*60)
        print(f"Exporting {self.model.__class__.__name__} to all formats")
        print("="*60)
        
        results = {}
        
        # ONNX
        print("\n1. ONNX Export")
        print("-" * 60)
        try:
            onnx_path = output_dir / f"{base_name}.onnx"
            results["onnx"] = self.export_onnx(str(onnx_path))
            results["onnx"]["verified"] = self.verify_onnx(str(onnx_path))
        except Exception as e:
            print(f"  ✗ ONNX export failed: {e}")
            results["onnx"] = {"error": str(e)}
        
        # TorchScript
        print("\n2. TorchScript Export")
        print("-" * 60)
        try:
            ts_path = output_dir / f"{base_name}.pt"
            results["torchscript"] = self.export_torchscript(str(ts_path))
        except Exception as e:
            print(f"  ✗ TorchScript export failed: {e}")
            results["torchscript"] = {"error": str(e)}
        
        # Quantized
        print("\n3. Quantized Export")
        print("-" * 60)
        try:
            quant_path = output_dir / f"{base_name}_quantized.pt"
            results["quantized"] = self.export_quantized(str(quant_path))
        except Exception as e:
            print(f"  ✗ Quantized export failed: {e}")
            results["quantized"] = {"error": str(e)}
        
        # Summary
        print("\n" + "="*60)
        print("Export Summary")
        print("="*60)
        
        for fmt, result in results.items():
            if "error" not in result:
                size = result.get("file_size_mb", 0)
                print(f"  ✓ {fmt.upper()}: {size:.2f} MB")
            else:
                print(f"  ✗ {fmt.upper()}: {result['error']}")
        
        print()
        
        # Save summary
        summary_path = output_dir / f"{base_name}_export_summary.json"
        with open(summary_path, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"✓ Export summary saved: {summary_path}")
        
        return results


def export_model(
    model: nn.Module,
    output_path: str,
    format: str = "onnx",
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to export a model.
    
    Args:
        model: Model to export
        output_path: Output file path
        format: Export format ("onnx", "torchscript", "quantized", "all")
        **kwargs: Additional arguments for exporter
    
    Returns:
        Export metadata
    
    Example:
        model = ModelRegistry.create("mobilenet_v3_small", num_classes=10)
        
        # Export to ONNX
        export_model(model, "model.onnx", format="onnx")
        
        # Export to all formats
        export_model(model, "exports/model", format="all")
    """
    exporter = ModelExporter(model, **kwargs)
    
    if format == "onnx":
        return exporter.export_onnx(output_path)
    elif format == "torchscript":
        return exporter.export_torchscript(output_path)
    elif format == "quantized":
        return exporter.export_quantized(output_path)
    elif format == "all":
        # Extract directory and basename
        path = Path(output_path)
        return exporter.export_all(str(path.parent), path.stem)
    else:
        raise ValueError(f"Unknown format: {format}")
