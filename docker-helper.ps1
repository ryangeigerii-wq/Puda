# PowerShell script to manage Docker environment for AI Paper Reader

param(
    [Parameter(Position=0)]
    [ValidateSet("build", "up", "down", "logs", "shell", "intake", "prep", "scan", "qc", "output", "workflow", "status", "clean", "help")]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "`n============================================" -ForegroundColor Cyan
    Write-Host "AI Paper Reader - Docker Helper" -ForegroundColor Cyan
    Write-Host "============================================`n" -ForegroundColor Cyan
    
    Write-Host "Usage: .\docker-helper.ps1 [command]`n" -ForegroundColor Yellow
    
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  build    - Build Docker image"
    Write-Host "  up       - Start containers"
    Write-Host "  down     - Stop containers"
    Write-Host "  logs     - View container logs"
    Write-Host "  shell    - Open bash shell in container"
    Write-Host "  workflow - View unidirectional flow diagram"
    Write-Host "  intake   - Run intake CLI"
    Write-Host "  prep     - Run prep CLI"
    Write-Host "  scan     - Run scanning CLI"
    Write-Host "  qc       - Run QC CLI"
    Write-Host "  output   - Run output CLI"
    Write-Host "  status   - Show container status"
    Write-Host "  clean    - Remove containers and volumes"
    Write-Host "  help     - Show this help message"
    Write-Host ""
}

function Build-Image {
    Write-Host "`n🔨 Building Docker image..." -ForegroundColor Cyan
    docker-compose build
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Build complete!" -ForegroundColor Green
    } else {
        Write-Host "❌ Build failed!" -ForegroundColor Red
    }
}

function Start-Containers {
    Write-Host "`n🚀 Starting containers..." -ForegroundColor Cyan
    docker-compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Containers started!" -ForegroundColor Green
        Start-Sleep -Seconds 2
        Show-Status
    } else {
        Write-Host "❌ Failed to start containers!" -ForegroundColor Red
    }
}

function Stop-Containers {
    Write-Host "`n🛑 Stopping containers..." -ForegroundColor Cyan
    docker-compose down
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Containers stopped!" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to stop containers!" -ForegroundColor Red
    }
}

function Show-Logs {
    Write-Host "`n📜 Showing logs (Ctrl+C to exit)..." -ForegroundColor Cyan
    docker-compose logs -f
}

function Open-Shell {
    Write-Host "`n💻 Opening container shell..." -ForegroundColor Cyan
    docker-compose exec puda-app bash
}

function Run-IntakeCLI {
    Write-Host "`n📥 Starting Intake Zone CLI..." -ForegroundColor Cyan
    docker-compose exec puda-app python intake_cli.py
}

function Run-PrepCLI {
    Write-Host "`n🔧 Starting Prep Zone CLI..." -ForegroundColor Cyan
    docker-compose exec puda-app python prep_cli.py
}

function Run-ScanCLI {
    Write-Host "`n📸 Starting Scanning Zone CLI..." -ForegroundColor Cyan
    docker-compose exec puda-app python scan_cli.py
}

function Run-QCCLI {
    Write-Host "`n✅ Starting QC Zone CLI..." -ForegroundColor Cyan
    docker-compose exec puda-app python qc_cli.py
}

function Run-OutputCLI {
    Write-Host "`n📤 Starting Output Rack CLI..." -ForegroundColor Cyan
    docker-compose exec puda-app python output_cli.py
}

function Run-WorkflowCLI {
    Write-Host "`n📋 Starting Workflow Visualizer..." -ForegroundColor Cyan
    docker-compose exec puda-app python workflow_cli.py
}

function Show-Status {
    Write-Host "`n📊 Container Status:" -ForegroundColor Cyan
    docker-compose ps
    
    Write-Host "`n📦 Volumes:" -ForegroundColor Cyan
    docker volume ls | Select-String "puda"
}

function Clean-All {
    Write-Host "`n🧹 Cleaning up (this will remove volumes)..." -ForegroundColor Yellow
    $confirm = Read-Host "Are you sure? This will delete all data! (yes/no)"
    if ($confirm -eq "yes") {
        docker-compose down -v
        Write-Host "✅ Cleanup complete!" -ForegroundColor Green
    } else {
        Write-Host "❌ Cleanup cancelled" -ForegroundColor Red
    }
}

# Main execution
switch ($Command) {
    "build"    { Build-Image }
    "up"       { Start-Containers }
    "down"     { Stop-Containers }
    "logs"     { Show-Logs }
    "shell"    { Open-Shell }
    "workflow" { Run-WorkflowCLI }
    "intake"   { Run-IntakeCLI }
    "prep"     { Run-PrepCLI }
    "scan"     { Run-ScanCLI }
    "qc"       { Run-QCCLI }
    "output"   { Run-OutputCLI }
    "status"   { Show-Status }
    "clean"    { Clean-All }
    "help"     { Show-Help }
    default    { Show-Help }
}
