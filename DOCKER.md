# AI Paper Reader - Docker Setup

## Quick Start with Docker

### Prerequisites
- Docker Desktop installed
- Docker Compose installed

### Build and Run

```powershell
# Build the Docker image
docker-compose build

# Start the container
docker-compose up -d

# Access the container shell
docker-compose exec puda-app bash

# Inside the container, run any CLI
python intake_cli.py
python prep_cli.py
python scan_cli.py
```

### Docker Commands

```powershell
# Build image
docker-compose build

# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Execute commands in container
docker-compose exec puda-app python intake_cli.py

# Restart services
docker-compose restart

# Remove everything (including volumes)
docker-compose down -v
```

### Running CLI Tools in Docker

```powershell
# Intake Zone
docker-compose exec puda-app python intake_cli.py

# Prep Zone
docker-compose exec puda-app python prep_cli.py

# Scanning Zone
docker-compose exec puda-app python scan_cli.py
```

### Development Workflow

The container mounts your local code directory, so changes are reflected immediately:

```powershell
# Start container with live code mounting
docker-compose up -d

# Edit code on your local machine
# Changes are immediately available in container

# Test in container
docker-compose exec puda-app python -m pytest
```

### Data Persistence

Data is persisted in Docker volumes:
- `puda-data`: Application data and logs
- `puda-scans`: Scanned documents

```powershell
# List volumes
docker volume ls | Select-String puda

# Inspect volume
docker volume inspect puda_puda-scans

# Backup volume
docker run --rm -v puda_puda-scans:/data -v ${PWD}:/backup alpine tar czf /backup/scans-backup.tar.gz -C /data .

# Restore volume
docker run --rm -v puda_puda-scans:/data -v ${PWD}:/backup alpine tar xzf /backup/scans-backup.tar.gz -C /data
```

### Environment Variables

Create a `.env` file for custom configuration:

```env
# .env
ENVIRONMENT=production
LOG_LEVEL=INFO
INTAKE_CAPACITY=50
PREP_CAPACITY=30
SCAN_CAPACITY=100
```

Then reference in docker-compose.yml:
```yaml
env_file:
  - .env
```

### Troubleshooting

```powershell
# Check container status
docker-compose ps

# View container logs
docker-compose logs puda-app

# Enter container for debugging
docker-compose exec puda-app /bin/bash

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Production Deployment

For production, modify `docker-compose.yml`:

```yaml
services:
  puda-app:
    restart: always
    environment:
      - ENVIRONMENT=production
    # Remove stdin_open and tty
    # Add actual command instead of bash
    command: python api/server.py
```

## Docker Container Includes

- Python 3.11
- Tesseract OCR (for future scanning features)
- OpenCV dependencies
- All Python packages from requirements.txt
- Pre-created directories for data, scans, logs

## Next Steps

1. Start container: `docker-compose up -d`
2. Access shell: `docker-compose exec puda-app bash`
3. Run CLI tools inside container
4. Add database service when needed (uncomment in docker-compose.yml)
