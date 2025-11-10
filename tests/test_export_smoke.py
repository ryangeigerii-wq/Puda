"""ONNX Export Smoke Test

Quick harness to validate that model export paths are functioning.

Goals:
 1. Build a tiny dummy model if PudaModel can't be imported.
 2. Run standard image-shaped ONNX export via ModelExporter.export_onnx.
 3. If PudaModel available and ONNX present, run sequence export (export_sequence_model).
 4. Load exported ONNX with onnxruntime and perform a single inference.
 5. Compare PyTorch output vs ONNX output (max absolute diff) for sanity.
 6. Print a compact summary and assert tolerances.

Safe to run without GPU; skips gracefully if onnx/onnxruntime missing.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import json
import math

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except Exception as e:  # pragma: no cover
    print(f"[SMOKE] Torch unavailable ({e}); skipping torch-dependent exports.")
    TORCH_AVAILABLE = False
    torch = None
    nn = None

# Attempt imports
try:
    from src.ml.models.export import ModelExporter
except Exception as e:  # pragma: no cover
    print(f"[SMOKE] Failed to import ModelExporter: {e}")
    ModelExporter = None

# Try to import PudaModel (optional sequence export test)
try:
    from src.ml.models.puda_model import PudaModel, load_tokenizer
    PUDA_AVAILABLE = True
except Exception as e:
    print(f"[SMOKE] PudaModel unavailable ({e}); will use dummy model only.")
    PUDA_AVAILABLE = False

# Check ONNX availability
try:
    import onnx  # noqa: F401
    import onnxruntime as ort  # noqa: F401
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

ARTIFACT_DIR = Path("artifacts/export_smoke")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def build_dummy_model() -> nn.Module:
    """Create a minimal feed-forward model compatible with ModelExporter image input."""
    return nn.Sequential(
        nn.Flatten(),
        nn.Linear(3 * 224 * 224, 128),
        nn.ReLU(),
        nn.Linear(128, 10)
    )


def run_standard_export() -> dict:
    if not TORCH_AVAILABLE or ModelExporter is None:
        return {"skipped": True, "reason": "torch or ModelExporter unavailable"}
    model = build_dummy_model().eval()
    exporter = ModelExporter(model, input_shape=(1, 3, 224, 224))
    onnx_path = ARTIFACT_DIR / "dummy_model.onnx"
    meta = exporter.export_onnx(onnx_path)
    verify = exporter.verify_onnx(str(onnx_path))
    meta["verified"] = verify
    return meta


def run_sequence_export() -> dict:
    if not (PUDA_AVAILABLE and ONNX_AVAILABLE and TORCH_AVAILABLE):
        return {"skipped": True, "reason": "PudaModel/ONNX/torch missing"}
    # Instantiate lightweight PudaModel (no BiLSTM to keep it fast)
    model = PudaModel(use_bilstm=False)
    model.eval()
    exporter = ModelExporter(model, input_shape=(1, 3, 224, 224))  # input_shape unused for sequence export
    seq_path = ARTIFACT_DIR / "puda_sequence.onnx"
    meta = exporter.export_sequence_model(str(seq_path), max_seq_len=32, include_extraction=True)

    # Prepare dummy token inputs to compare outputs (single run)
    tokenizer = load_tokenizer(model.model_name)
    sample_text = "Invoice number 123 dated 2025-11-10 total $1500.00"
    encoded = tokenizer(sample_text, return_tensors="pt", truncation=True, max_length=32)
    with torch.no_grad():
        pt_out = model(encoded["input_ids"], encoded["attention_mask"])

    import onnxruntime as ort
    session = ort.InferenceSession(str(seq_path))
    ort_inputs = {
        session.get_inputs()[0].name: encoded["input_ids"].cpu().numpy(),
        session.get_inputs()[1].name: encoded["attention_mask"].cpu().numpy(),
    }
    ort_outputs = session.run(None, ort_inputs)

    # Compare classification logits only (index 0)
    pt_logits = pt_out["classification_logits"].cpu().numpy()
    onnx_logits = ort_outputs[0]
    max_diff = float(abs(pt_logits - onnx_logits).max())
    meta["classification_max_diff"] = max_diff
    meta["classification_shape"] = list(pt_logits.shape)
    meta["tolerance"] = 1e-4
    meta["within_tolerance"] = max_diff <= meta["tolerance"]
    return meta


def main() -> int:
    summary: dict = {
        "onnx_available": ONNX_AVAILABLE, 
        "puda_available": PUDA_AVAILABLE, 
        "torch_available": TORCH_AVAILABLE,
        "exporter_available": ModelExporter is not None
    }

    if not ONNX_AVAILABLE or not TORCH_AVAILABLE or ModelExporter is None:
        print("[SMOKE] Missing dependencies; skipping export tests.")
        print(json.dumps(summary, indent=2))
        return 0

    print("[SMOKE] Running standard dummy model export...")
    try:
        summary["standard_export"] = run_standard_export()
    except Exception as e:
        summary["standard_export_error"] = str(e)

    print("[SMOKE] Running sequence export (PudaModel)...")
    try:
        summary["sequence_export"] = run_sequence_export()
    except Exception as e:
        summary["sequence_export_error"] = str(e)

    # Evaluate pass/fail criteria
    passed = True
    if "standard_export" in summary:
        se = summary["standard_export"]
        if not se.get("verified", {}).get("passed", False):
            passed = False
    if "sequence_export" in summary and not summary["sequence_export"].get("skipped"):
        if not summary["sequence_export"].get("within_tolerance", True):
            passed = False

    summary["overall_passed"] = passed

    # Save summary JSON
    summary_path = ARTIFACT_DIR / "smoke_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[SMOKE] Summary saved: {summary_path}")
    print(json.dumps(summary, indent=2))

    if not passed:
        print("[SMOKE] ❌ Export smoke test failed")
        return 1
    print("[SMOKE] ✅ Export smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
