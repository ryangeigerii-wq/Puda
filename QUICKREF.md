# Quick Reference - AI Paper Reader

## Docker Commands (PowerShell)

### Setup & Management
```powershell
.\docker-helper.ps1 build     # Build Docker image
.\docker-helper.ps1 up        # Start containers (app, postgres, minio)
.\docker-helper.ps1 down      # Stop containers
.\docker-helper.ps1 status    # Show status
.\docker-helper.ps1 logs      # View logs
.\docker-helper.ps1 shell     # Access container shell
.\docker-helper.ps1 clean     # Clean everything (WARNING: deletes data)
```

### Database & Storage Services
```powershell
# Start PostgreSQL + MinIO
docker-compose up -d puda-postgres puda-minio

# Check services
docker ps

# PostgreSQL access
docker exec -it puda-postgres psql -U puda -d puda_storage

# MinIO console
# Open browser: http://localhost:9001
# Username: minioadmin, Password: minioadmin
```

### Run CLI Tools
```powershell
.\docker-helper.ps1 workflow  # View workflow diagram (NEW!)
.\docker-helper.ps1 intake    # Intake Zone CLI
.\docker-helper.ps1 prep      # Prep Zone CLI
.\docker-helper.ps1 scan      # Scanning Zone CLI
.\docker-helper.ps1 qc        # QC Zone CLI
.\docker-helper.ps1 output    # Output Rack CLI
```

## Unidirectional Flow (Left to Right)

```
➊ 📥      →      ➋ 🔧      →      ➌ 📸      →      ➍ ✅      →      ➎ 📤
INTAKE          PREP         SCANNING         QC           OUTPUT
```

**Rules:**
- ✅ Always move LEFT → RIGHT
- ❌ No backwards movement (except QC rescan)
- ❌ Cannot skip zones
- ➎ Output is final destination

### Manual Docker Commands
```powershell
docker-compose up -d                              # Start
docker-compose down                               # Stop
docker-compose exec puda-app bash                 # Shell
docker-compose exec puda-app python intake_cli.py # Run CLI
docker-compose logs -f                            # View logs
docker-compose ps                                 # Status
```

## System Test
```powershell
# In container
docker-compose exec puda-app python test_system.py

# Or from helper
.\docker-helper.ps1 shell
python test_system.py
```

## Workflow

### 1. Intake Zone
```
Receive Box → Log Details (paper count) → Ready for Prep
```

### 2. Prep Zone
```
Move to Prep → Unbox → Add Papers → Remove Staples → Mark Ready → Complete Box
```

### 3. Scanning Zone
```
Move to Scanning → Assign Station → Start Scan → Complete Scan → Processing
```

### 4. QC Zone
```
Move to QC → Start Check → Pass/Fail → Rescan if needed → Ready for Output
```

### 5. Output Rack
```
Move to Output → Assign Disposition (Return/Shred/Archive) → Mark Returned/Shredded
```

## Paper Status Flow
```
RECEIVED → LOGGED → IN_QUEUE → UNBOXING → SORTING_PREP → 
STAPLE_REMOVAL → PREP_COMPLETE → IN_QUEUE → SCANNING → 
SCAN_COMPLETE → QC_REVIEW → QC_PASSED/QC_FAILED → 
PROCESSED → AWAITING_RETURN/AWAITING_SHREDDING → 
RETURNED/SHREDDED
```

## Zone Capacities
- **Intake**: 50 boxes
- **Prep**: 30 boxes, unlimited papers
- **Scanning**: 100 papers queue
- **QC**: 50 papers
- **Output**: 500 papers (binned by disposition)

## Scanning Stations
- **ADF-01**: Automatic Document Feeder
- **ADF-02**: Automatic Document Feeder
- **WS-01**: Manual Workstation

## Data Locations (in Docker)
- Application: `/app`
- Scans: `/app/data/scans`
- Logs: `/app/data/logs`
- Output: `/app/data/output`

## Volumes
- `puda-data`: Application data
- `puda-scans`: Scanned documents

## Troubleshooting

### Container won't start
```powershell
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### View errors
```powershell
docker-compose logs puda-app
```

### Clean restart
```powershell
docker-compose down -v  # WARNING: Deletes data
docker-compose build
docker-compose up -d
```

### Access files from host
```powershell
# Backup scans
docker run --rm -v puda_puda-scans:/data -v ${PWD}:/backup alpine tar czf /backup/scans-backup.tar.gz -C /data .

# Copy file from container
docker cp puda-paper-reader:/app/data/scans/file.pdf ./
```

## Python API Examples

```python
from src.physical.control import PaperControlSystem

control = PaperControlSystem()

# Intake
control.receive_box("BOX-001")
control.log_box_details("BOX-001", 50, "Finance docs")

# Prep
control.move_box_to_prep("BOX-001")
control.start_unboxing("BOX-001")
control.add_paper("BOX-001", "PAPER-001", has_staples=True)
control.remove_staples("PAPER-001")
control.mark_paper_ready("PAPER-001")
control.complete_box_prep("BOX-001")

# Scanning
control.move_papers_to_scanning("BOX-001")
control.start_scan("PAPER-001")
control.complete_scan("PAPER-001", success=True, output_file="scan.pdf")

# QC
control.move_papers_to_qc()  # Move all scanned papers
control.start_qc_check("PAPER-001", "QC_Operator_1")
control.complete_qc_check("PAPER-001", "QC_Operator_1", passed=True)
# Or fail with issues
control.complete_qc_check("PAPER-001", "QC_Operator_1", passed=False, 
                         issues=["blurry"], needs_rescan=True)
control.send_for_rescan("PAPER-001")

# Output
from src.physical.zones import OutputDisposition
control.move_paper_to_output("PAPER-001", OutputDisposition.RETURN)
control.mark_bin_returned("BIN-RETURN-001")
control.mark_bin_shredded("BIN-SHRED-001")

# Status
control.get_intake_status()
control.get_prep_status()
control.get_scanning_status()
control.get_qc_status()
control.get_output_status()
```


## Storage & Database

### PostgreSQL Setup
```powershell
# Install dependency
pip install psycopg2-binary

# Run setup script
python setup_postgres.py

# Test integration
python storage_integration_example.py
```

### Storage Commands
```powershell
# Local storage
python storage_cli.py --backend local --path data/storage info
python storage_cli.py --backend local put document.pdf --file document.pdf
python storage_cli.py --backend local list

# S3 (MinIO)
python storage_cli.py --backend s3 --bucket archive --endpoint http://localhost:9000 --access-key minioadmin --secret-key minioadmin info
```

### PostgreSQL Usage
```python
from src.storage import PostgreSQLStorageDB

# Connect
db = PostgreSQLStorageDB()

# Record object
db.record_object(
    object_key="documents/file.pdf",
    size=524288,
    content_type="application/pdf",
    etag="abc123",
    version_id="v1",
    storage_backend="s3"
)

# Search
results = db.search_objects("invoice & finance")

# Audit
db.log_audit(action="DOWNLOAD", object_key="file.pdf", user_id="user123")
logs = db.get_audit_logs(object_key="file.pdf")
```


## Storage API (FastAPI)

### Start API Server
```powershell
# Basic (local storage)
python -m src.storage.storage_api

# With options
python -m src.storage.storage_api --host 0.0.0.0 --port 8000 --backend s3 --path archive --api-key secret123

# Production (multiple workers)
uvicorn src.storage.storage_api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Test API
```powershell
# Run test client
python test_storage_api.py

# Interactive docs
Start-Process "http://localhost:8000/docs"  # Swagger UI
Start-Process "http://localhost:8000/redoc" # ReDoc
```

### API Examples
```powershell
# Upload file
curl -X POST "http://localhost:8000/api/storage/objects?key=test.pdf" -F "file=@test.pdf"

# Download file
curl -X GET "http://localhost:8000/api/storage/objects/test.pdf" -o downloaded.pdf

# List objects
curl -X GET "http://localhost:8000/api/storage/objects?prefix=documents/"

# Get analytics
curl -X GET "http://localhost:8000/api/analytics?hours=24"
```
