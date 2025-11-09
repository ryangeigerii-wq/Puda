#!/usr/bin/env pwsh
# Quick Start Script for QC Web Application

Write-Host "================================" -ForegroundColor Cyan
Write-Host "QC Web Application - Quick Start" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
}

# Create sample tasks
Write-Host "[1/3] Creating sample QC tasks..." -ForegroundColor Yellow
python test_qc_web.py
Write-Host ""

# Start QC application
Write-Host "[2/3] Starting QC Web Application..." -ForegroundColor Yellow
Write-Host "Server will run on http://127.0.0.1:8081" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

Start-Sleep -Seconds 2

# Launch browser after 3 seconds
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 3
    Start-Process "http://127.0.0.1:8081"
} | Out-Null

# Start server
python qc_app.py --port 8081 --host 127.0.0.1
