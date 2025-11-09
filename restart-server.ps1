#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick restart script for the Puda Dashboard API server.

.DESCRIPTION
    Stops any running dashboard_api processes, then starts a fresh server instance
    on 0.0.0.0:8080 with verbose logging enabled.

.PARAMETER Port
    Server port (default: 8080)

.PARAMETER HostAddress
    Server host binding (default: 0.0.0.0)

.PARAMETER Minimal
    Start in minimal mode (disable all optional subsystems)

.PARAMETER NoQC
    Disable QC subsystem only

.PARAMETER NoOrg
    Disable Organization subsystem only

.PARAMETER NoAuth
    Disable Authorization subsystem only

.PARAMETER Safe
    Continue on subsystem init failures

.PARAMETER FlaskDebug
    Enable Flask debug mode

.EXAMPLE
    .\restart-server.ps1
    Restart with default settings (all subsystems, verbose, 0.0.0.0:8080)

.EXAMPLE
    .\restart-server.ps1 -Port 5000 -HostAddress 127.0.0.1
    Restart on localhost:5000

.EXAMPLE
    .\restart-server.ps1 -Minimal
    Restart with all optional subsystems disabled
#>

[CmdletBinding()]
param(
    [int]$Port = 8080,
    [string]$HostAddress = "0.0.0.0",
    [switch]$Minimal,
    [switch]$NoQC,
    [switch]$NoOrg,
    [switch]$NoAuth,
    [switch]$Safe,
    [switch]$FlaskDebug
)

$ErrorActionPreference = "Stop"

Write-Host "🔄 Restarting Puda Dashboard API Server..." -ForegroundColor Cyan
Write-Host ""

# Stop any existing dashboard_api processes
Write-Host "📋 Checking for existing server processes..." -ForegroundColor Yellow
$existingProcesses = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -like 'python*' -and $_.CommandLine -like '*dashboard_api*'
}

if ($existingProcesses) {
    Write-Host "⚠️  Found $($existingProcesses.Count) running server process(es). Stopping..." -ForegroundColor Yellow
    $existingProcesses | Stop-Process -Force
    Start-Sleep -Seconds 1
    Write-Host "✅ Stopped existing processes" -ForegroundColor Green
} else {
    Write-Host "✅ No existing processes found" -ForegroundColor Green
}

Write-Host ""

# Build command arguments
$args = @(
    "dashboard_api.py",
    "--host", $HostAddress,
    "--port", $Port,
    "--audit-dir", "data",
    "--verbose"
)

if ($Minimal) { $args += "--minimal" }
if ($NoQC) { $args += "--no-qc" }
if ($NoOrg) { $args += "--no-org" }
if ($NoAuth) { $args += "--no-auth" }
if ($Safe) { $args += "--safe" }
if ($FlaskDebug) { $args += "--debug" }

# Display startup info
Write-Host "🚀 Starting server with configuration:" -ForegroundColor Cyan
Write-Host "   Host:     $HostAddress" -ForegroundColor White
Write-Host "   Port:     $Port" -ForegroundColor White
Write-Host "   Verbose:  Enabled" -ForegroundColor White
Write-Host "   Minimal:  $(if ($Minimal) { 'Yes' } else { 'No' })" -ForegroundColor White
Write-Host "   Safe:     $(if ($Safe) { 'Yes' } else { 'No' })" -ForegroundColor White
Write-Host "   Debug:    $(if ($FlaskDebug) { 'Yes' } else { 'No' })" -ForegroundColor White
Write-Host ""
Write-Host "📍 Access points:" -ForegroundColor Cyan
Write-Host "   Dashboard:  http://$($HostAddress):$Port/" -ForegroundColor White
Write-Host "   Health:     http://$($HostAddress):$Port/api/health" -ForegroundColor White
Write-Host "   Login:      http://$($HostAddress):$Port/login.html" -ForegroundColor White
Write-Host "   API Docs:   http://$($HostAddress):$Port/api/" -ForegroundColor White
Write-Host ""
Write-Host "🔑 Default credentials: admin / admin" -ForegroundColor Yellow
Write-Host ""
Write-Host "💡 Press CTRL+C to stop the server" -ForegroundColor Gray
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host ""

# Start the server
try {
    & python @args
} catch {
    Write-Host ""
    Write-Host "❌ Server failed to start: $_" -ForegroundColor Red
    exit 1
}
