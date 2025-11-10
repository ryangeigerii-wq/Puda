# ONNX Export Smoke Test

Quick validation test for model export functionality.

## What it Tests

1. **Standard Export**: Exports a dummy CNN model to ONNX format and verifies output
2. **Sequence Export**: Exports PudaModel (transformer-based) with multi-output support
3. **Runtime Verification**: Compares PyTorch vs ONNX Runtime inference outputs

## Running Locally

### PowerShell (Recommended)
```powershell
. .\Makefile.ps1
Invoke-ExportSmoke
```

### Direct Python
```powershell
$env:PYTHONPATH = $PWD
python tests/test_export_smoke.py
```

## Dependencies

The test gracefully skips if dependencies are missing:
- `torch` (CPU version recommended for local dev)
- `transformers`
- `numpy<2.0` (compatibility with torch 2.2.0)
- `onnx`
- `onnxruntime`

### Known Issues - Windows DLL Errors

If you see `DLL initialization routine failed` errors with onnxruntime on Windows:

**Option 1: Skip local test, rely on CI**
The GitHub Actions workflow runs on Linux and handles dependencies cleanly.

**Option 2: Use Docker**
```powershell
docker-compose run puda-app python tests/test_export_smoke.py
```

**Option 3: Fresh venv**
```powershell
# Remove existing venv
Remove-Item -Recurse -Force .venv
# Create fresh environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# Install in specific order
pip install torch==2.2.0+cpu --index-url https://download.pytorch.org/whl/cpu
pip install "numpy<2.0"
pip install transformers onnx onnxruntime
```

## CI Integration

The test runs automatically on:
- Push to `main` or `develop` branches
- Pull requests
- When ML code or test files change

See `.github/workflows/ml-tests.yml` for configuration.

## Output

Test generates artifacts in `artifacts/export_smoke/`:
- `dummy_model.onnx` - Simple CNN export
- `puda_sequence.onnx` - Multi-task transformer export (if available)
- `smoke_summary.json` - Test results and metrics

## Interpreting Results

```json
{
  "onnx_available": true,
  "torch_available": true,
  "puda_available": true,
  "exporter_available": true,
  "standard_export": {
    "format": "onnx",
    "file_size_mb": 5.2,
    "verified": {
      "passed": true,
      "max_difference": 1.2e-7
    }
  },
  "overall_passed": true
}
```

- `overall_passed`: All exports succeeded and verified within tolerance
- `max_difference`: Maximum absolute difference between PyTorch and ONNX outputs (should be < 1e-4)
- `skipped`: Test component was skipped due to missing dependencies
