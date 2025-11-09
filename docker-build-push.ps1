#!/usr/bin/env pwsh
# Docker Build and Push Script for Puda AI Paper Reader
# Usage: .\docker-build-push.ps1 [-Registry "your-registry"] [-Tag "version"]

param(
    [string]$Registry = "",
    [string]$Tag = "latest",
    [switch]$NoPush,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Docker Build and Push Script
=============================

Usage:
  .\docker-build-push.ps1 [options]

Options:
  -Registry <name>    Docker registry (e.g., docker.io/username, ghcr.io/username)
  -Tag <version>      Image tag (default: latest)
  -NoPush             Build only, don't push to registry
  -Help               Show this help message

Examples:
  .\docker-build-push.ps1 -Registry "docker.io/myuser" -Tag "v1.0.0"
  .\docker-build-push.ps1 -Registry "ghcr.io/myorg" -Tag "latest"
  .\docker-build-push.ps1 -NoPush
  
Local testing:
  docker-compose up -d
  Open http://localhost:8080 in browser
  
"@
    exit 0
}

$ImageName = "puda-paper-reader"
$FullImageName = if ($Registry) { "$Registry/$ImageName" } else { $ImageName }

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Puda AI Paper Reader - Docker Build" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Build the image
Write-Host ""
Write-Host "[2/6] Building Docker image..." -ForegroundColor Yellow
Write-Host "Image: $FullImageName`:$Tag" -ForegroundColor Cyan
$buildCmd = "docker build -t ${FullImageName}:${Tag} ."
Write-Host "Command: $buildCmd" -ForegroundColor Gray
Invoke-Expression $buildCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Build successful" -ForegroundColor Green

# Tag as latest if not already
if ($Tag -ne "latest") {
    Write-Host ""
    Write-Host "[3/6] Tagging as latest..." -ForegroundColor Yellow
    docker tag "${FullImageName}:${Tag}" "${FullImageName}:latest"
    Write-Host "✓ Tagged as latest" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[3/6] Already tagged as latest" -ForegroundColor Green
}

# Show image info
Write-Host ""
Write-Host "[4/6] Image information:" -ForegroundColor Yellow
docker images $FullImageName --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Test the image locally
Write-Host ""
Write-Host "[5/6] Testing image locally..." -ForegroundColor Yellow
Write-Host "Starting container on port 8888..." -ForegroundColor Gray
$testContainer = docker run -d -p 8888:8080 --name puda-test "${FullImageName}:${Tag}"

if ($LASTEXITCODE -eq 0) {
    Start-Sleep -Seconds 3
    Write-Host "Testing health endpoint..." -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8888/api/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Container is healthy" -ForegroundColor Green
            Write-Host "  Dashboard: http://localhost:8888/" -ForegroundColor Cyan
        }
    } catch {
        Write-Host "⚠ Health check failed (may need more time to start)" -ForegroundColor Yellow
    }
    
    Write-Host "Stopping test container..." -ForegroundColor Gray
    docker stop puda-test | Out-Null
    docker rm puda-test | Out-Null
    Write-Host "✓ Test complete" -ForegroundColor Green
} else {
    Write-Host "✗ Test container failed to start" -ForegroundColor Red
}

# Push to registry
if (-not $NoPush) {
    Write-Host ""
    Write-Host "[6/6] Pushing to registry..." -ForegroundColor Yellow
    
    if (-not $Registry) {
        Write-Host "⚠ No registry specified. Skipping push." -ForegroundColor Yellow
        Write-Host "  To push, use: -Registry 'docker.io/username' or 'ghcr.io/username'" -ForegroundColor Gray
    } else {
        Write-Host "Pushing ${FullImageName}:${Tag}..." -ForegroundColor Gray
        docker push "${FullImageName}:${Tag}"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Pushed ${Tag}" -ForegroundColor Green
            
            if ($Tag -ne "latest") {
                Write-Host "Pushing ${FullImageName}:latest..." -ForegroundColor Gray
                docker push "${FullImageName}:latest"
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✓ Pushed latest" -ForegroundColor Green
                }
            }
        } else {
            Write-Host "✗ Push failed. You may need to login:" -ForegroundColor Red
            Write-Host "  docker login $Registry" -ForegroundColor Yellow
            exit 1
        }
    }
} else {
    Write-Host ""
    Write-Host "[6/6] Skipping push (--NoPush specified)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  Local testing:" -ForegroundColor Cyan
Write-Host "    docker-compose up -d" -ForegroundColor White
Write-Host "    Open http://localhost:8080" -ForegroundColor White
Write-Host ""
Write-Host "  Run standalone:" -ForegroundColor Cyan
Write-Host "    docker run -p 8080:8080 -v puda-data:/app/data ${FullImageName}:${Tag}" -ForegroundColor White
Write-Host ""
if ($Registry) {
    Write-Host "  Pull from registry:" -ForegroundColor Cyan
    Write-Host "    docker pull ${FullImageName}:${Tag}" -ForegroundColor White
    Write-Host ""
}
Write-Host "  View logs:" -ForegroundColor Cyan
Write-Host "    docker logs puda-paper-reader" -ForegroundColor White
Write-Host ""
