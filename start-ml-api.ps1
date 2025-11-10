# Start ML API Server
# Usage: .\start-ml-api.ps1

Write-Host "Starting Puda ML API Server..." -ForegroundColor Cyan
Write-Host ""

# Set PYTHONPATH
$env:PYTHONPATH = $PWD

# Activate venv if exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
}

# Check dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$packages = @("fastapi", "uvicorn", "torch", "transformers")
$missing = @()

foreach ($pkg in $packages) {
    $check = python -c "import $pkg" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $missing += $pkg
    }
}

if ($missing.Count -gt 0) {
    Write-Host "⚠️  Missing packages: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "Install with: pip install fastapi uvicorn python-multipart" -ForegroundColor Yellow
    Write-Host ""
}

# Start server
Write-Host "Starting server on http://localhost:8001" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8001/docs" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

if (Test-Path ".venv") {
    & .\.venv\Scripts\python.exe src/inference/api.py
} else {
    python src/inference/api.py
}
