# Makefile-style commands for AI Paper Reader (Windows PowerShell)
# Usage: . .\Makefile.ps1; Invoke-Build

function Show-Menu {
    Write-Host "`n╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   AI Paper Reader - Development Commands          ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan
}

# Docker commands
function Invoke-Build {
    "Building Docker image..."
    docker-compose build
}

function Invoke-Up {
    "Starting containers..."
    docker-compose up -d
    "Containers started. Run 'docker-compose ps' to check status"
}

function Invoke-Down {
    "Stopping containers..."
    docker-compose down
}

function Invoke-Restart {
    "Restarting containers..."
    docker-compose restart
}

function Invoke-Shell {
    "Opening container shell..."
    docker-compose exec puda-app bash
}

function Invoke-Test {
    "Running system tests..."
    docker-compose exec puda-app python test_system.py
}

function Invoke-Logs {
    "Showing logs (Ctrl+C to exit)..."
    docker-compose logs -f
}

function Invoke-Clean {
    "Cleaning up Docker resources..."
    $confirm = Read-Host "Remove volumes? (y/n)"
    if ($confirm -eq 'y') {
        docker-compose down -v
        "Cleaned with volumes removed"
    } else {
        docker-compose down
        "Cleaned (volumes preserved)"
    }
}

function Invoke-Status {
    "Container Status:"
    docker-compose ps
    ""
    "Docker Volumes:"
    docker volume ls | Select-String "puda"
}

# Development commands
function Invoke-Install {
    "Installing Python dependencies locally..."
    if (Test-Path ".venv") {
        .\.venv\Scripts\Activate.ps1
    }
    pip install -r requirements.txt
}

function Invoke-Lint {
    "Running code linting..."
    docker-compose exec puda-app python -m pylint src/
}

function Invoke-Format {
    "Formatting code..."
    docker-compose exec puda-app python -m black src/
}

# Quick access to CLIs
function Invoke-Intake {
    docker-compose exec puda-app python intake_cli.py
}

function Invoke-Prep {
    docker-compose exec puda-app python prep_cli.py
}

function Invoke-Scan {
    docker-compose exec puda-app python scan_cli.py
}

# Help
function Show-Help {
    Show-Menu
    Write-Host "Available commands:" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Docker Management:" -ForegroundColor Yellow
    Write-Host "    Invoke-Build       - Build Docker image"
    Write-Host "    Invoke-Up          - Start containers"
    Write-Host "    Invoke-Down        - Stop containers"
    Write-Host "    Invoke-Restart     - Restart containers"
    Write-Host "    Invoke-Shell       - Open container shell"
    Write-Host "    Invoke-Status      - Show container status"
    Write-Host "    Invoke-Logs        - View container logs"
    Write-Host "    Invoke-Clean       - Clean up containers/volumes"
    Write-Host ""
    Write-Host "  Application:" -ForegroundColor Yellow
    Write-Host "    Invoke-Test        - Run system tests"
    Write-Host "    Invoke-Intake      - Run intake CLI"
    Write-Host "    Invoke-Prep        - Run prep CLI"
    Write-Host "    Invoke-Scan        - Run scan CLI"
    Write-Host ""
    Write-Host "  Development:" -ForegroundColor Yellow
    Write-Host "    Invoke-Install     - Install dependencies locally"
    Write-Host "    Invoke-Lint        - Run linting"
    Write-Host "    Invoke-Format      - Format code"
    Write-Host ""
    Write-Host "Usage: . .\Makefile.ps1; <command>" -ForegroundColor Gray
    Write-Host "Example: . .\Makefile.ps1; Invoke-Build" -ForegroundColor Gray
    Write-Host ""
}

# Default action
Show-Help
