# AI Paper Reader - Physical Paper Processing System

An intelligent system for processing physical papers with OCR, classification, and authorization.

## 🚀 Quick Start (Docker)

```powershell
# Build and start
.\docker-helper.ps1 build
.\docker-helper.ps1 up

# View workflow (NEW!)
.\docker-helper.ps1 workflow  # Visual flow diagram

# Test the system
.\docker-helper.ps1 shell
python test_flow_system.py    # Test unidirectional flow

# Run zones
.\docker-helper.ps1 intake   # Intake Zone
.\docker-helper.ps1 prep     # Prep Zone  
.\docker-helper.ps1 scan     # Scanning Zone
.\docker-helper.ps1 qc       # QC Zone
.\docker-helper.ps1 output   # Output Rack
```

See [QUICKREF.md](QUICKREF.md) for commands | [FLOW_SYSTEM.md](FLOW_SYSTEM.md) for flow details

## 🔄 Unidirectional Flow System

**Left-to-Right Only** - No backwards movement, prevents mix-ups:

```
➊ 📥      →      ➋ 🔧      →      ➌ 📸      →      ➍ ✅      →      ➎ 📤
INTAKE          PREP         SCANNING         QC           OUTPUT
```

- ✅ Papers move forward only (left to right)
- ❌ No backwards movement (except QC rescan)
- 🎯 Clear visual indicators at each step
- 🔒 Enforced at code level

See [FLOW_SYSTEM.md](FLOW_SYSTEM.md) for complete documentation.

## Purpose
Move and control paper safely through automated zones with proper logging and tracking.

## Core Elements

### Zones
- **Intake Zone**: Receiving and logging boxes of physical papers
- **Prep Zone**: Unboxing, sorting, and removing staples to prepare papers for scanning
- **Scanning Zone**: ADF and workstation scanning to digitize papers
- **QC Zone**: Visual quality checks and rescan management
- **Output Rack**: Processed papers awaiting return, shredding, or archiving

## Project Structure
```
Puda/
├── src/
│   ├── physical/          # Physical paper handling
│   │   ├── zones.py       # Zone management (intake, scanning, etc.)
│   │   └── control.py     # Paper movement control system
│   ├── scanner/           # OCR and image processing (coming soon)
│   ├── classifier/        # ML-based classification (coming soon)
│   └── auth/              # Authorization system (coming soon)
├── intake_cli.py          # Command-line interface for intake zone
├── prep_cli.py            # Command-line interface for prep zone
├── scan_cli.py            # Command-line interface for scanning zone
├── qc_cli.py              # Command-line interface for QC zone
├── output_cli.py          # Command-line interface for output rack
└── requirements.txt       # Python dependencies
```

## Features

### Intake Zone
- **Receive boxes**: Register new boxes arriving at the facility
- **Log details**: Record paper count and notes for each box
- **Track status**: Monitor box status through the workflow
- **Movement history**: Audit trail of all box movements
- **Capacity management**: Track available space in the zone

### Prep Zone
- **Unboxing**: Extract individual papers from boxes
- **Staple removal**: Remove staples from papers for safe scanning
- **Sorting**: Organize papers during prep process
- **Quality control**: Mark papers ready when prep is complete
- **Capacity management**: Track papers and boxes in prep (30 box capacity)

### Scanning Zone
- **Multiple stations**: 2 ADF scanners + 1 workstation by default
- **Auto-assignment**: Automatically assign papers to available stations
- **Queue management**: Track papers waiting for scan (100 paper capacity)
- **Scan tracking**: Monitor active scans in real-time
- **Success/failure handling**: Retry failed scans automatically
- **Daily metrics**: Track papers scanned per station

### QC Zone
- **Visual inspection**: Manual quality checks on scanned documents
- **Issue tracking**: Categorize problems (blurry, missing pages, misaligned, etc.)
- **Pass/fail workflow**: Clear approval or rejection process
- **Rescan management**: Send failed papers back to scanning
- **Statistics**: Track pass rates and common issues
- **Audit trail**: Complete QC history per paper

### Output Rack
- **Disposition management**: Organize papers by return, shred, or archive
- **Bin automation**: Automatically create and manage bins per disposition
- **Batch processing**: Process entire bins at once for efficiency
- **Status tracking**: Monitor papers awaiting return or shredding
- **Completion records**: Track returned and shredded papers
- **Capacity**: 500 papers across multiple bins (100 per bin)

## Quick Start

### Option 1: Docker (Recommended)

```powershell
# Build and start
.\docker-helper.ps1 build
.\docker-helper.ps1 up

# Run CLI tools
.\docker-helper.ps1 intake
.\docker-helper.ps1 prep
.\docker-helper.ps1 scan

# Or manually
docker-compose up -d
docker-compose exec puda-app python intake_cli.py
```

See [DOCKER.md](DOCKER.md) for detailed Docker instructions.

### Option 2: Local Installation
```bash
# Clone or navigate to project directory
cd Puda

# Install dependencies (Python 3.9+)
pip install -r requirements.txt
```

### Running the CLI Tools
```bash
python intake_cli.py
```

The CLI provides:
1. **Receive Box** - Register new box arrivals
2. **Log Box Details** - Record paper count and notes
3. **View Intake Status** - Check zone capacity and readiness
4. **View Box Info** - Get details about specific boxes
5. **View Movement History** - Audit trail of activities

**Prep Zone:**
```bash
python prep_cli.py
```

The CLI provides:
1. **Move Box to Prep** - Transfer box from intake
2. **Start Unboxing** - Begin unboxing process
3. **Add Paper** - Add individual paper from box
4. **Remove Staples** - Remove staples from paper
5. **Mark Paper Ready** - Mark paper ready for scanning
6. **Complete Box Prep** - Finish entire box
7. **View Prep Status** - Check zone status
8. **View Paper Info** - Get paper details

**Scanning Zone:**
```bash
python scan_cli.py
```

The CLI provides:
1. **Move Papers to Scanning** - Transfer from prep zone
2. **View Scanning Status** - Check zone and stations
3. **View Available Stations** - See ready stations
4. **Start Scan** - Begin scanning a paper
5. **Complete Scan** - Finish scanning (success/fail)
6. **View Station Details** - Check specific station
7. **View Queue** - See papers waiting

**QC Zone:**
```bash
python qc_cli.py
```

The CLI provides:
1. **Move Papers to QC** - Transfer from scanning
2. **View QC Status** - Check zone and statistics
3. **Start QC Check** - Begin checking a paper
4. **Pass QC Check** - Mark paper as passed
5. **Fail QC Check** - Mark paper as failed (with issues)
6. **Send for Rescan** - Send failed paper back
7. **View QC Result** - Check specific paper result
8. **View Statistics** - QC pass/fail rates

**Output Rack:**
```bash
python output_cli.py
```

The CLI provides:
1. **View Output Status** - Check rack capacity and statistics
2. **Move Paper to Output** - Transfer from QC with disposition
3. **View Active Bins** - See unprocessed bins
4. **View Bins by Disposition** - Filter by return/shred/archive
5. **Mark Bin as Returned** - Complete return processing
6. **Mark Bin as Shredded** - Complete shred processing
7. **View Papers Awaiting Return** - List return papers
8. **View Papers Awaiting Shredding** - List shred papers

## Usage Example

```python
from src.physical.control import PaperControlSystem

# Initialize the control system
control = PaperControlSystem()

# INTAKE ZONE
# Receive a box
result = control.receive_box("BOX-2025-001")
print(f"Box received: {result['box_id']}")

# Log box details
result = control.log_box_details(
    box_id="BOX-2025-001",
    paper_count=150,
    notes="Urgent documents from finance dept"
)

# PREP ZONE
# Move box to prep
result = control.move_box_to_prep("BOX-2025-001")

# Start unboxing
result = control.start_unboxing("BOX-2025-001")

# Add papers from box
for i in range(1, 4):
    paper_id = f"PAPER-{i:03d}"
    result = control.add_paper(
        box_id="BOX-2025-001",
        paper_id=paper_id,
        has_staples=True,
        pages=3
    )
    
    # Remove staples
    control.remove_staples(paper_id)
    
    # Mark ready
    control.mark_paper_ready(paper_id)

# Complete box prep
result = control.complete_box_prep("BOX-2025-001")

# SCANNING ZONE
# Move papers to scanning
result = control.move_papers_to_scanning("BOX-2025-001")
print(f"Moved {result['papers_moved']} papers to scanning")

# Check available stations
available = control.get_available_stations()
print(f"Available stations: {len(available)}")

# Start scanning papers
for paper_id in result['paper_ids']:
    # Auto-assign to available station
    scan_result = control.start_scan(paper_id)
    print(f"Scanning {paper_id} at {scan_result['station_id']}")
    
    # Complete scan
    control.complete_scan(
        paper_id=paper_id,
        success=True,
        output_file=f"scans/{paper_id}.pdf"
    )

# Check scanning status
status = control.get_scanning_status()
print(f"Papers scanned today: {status['papers_scanned_today']}")
print(f"Available stations: {status['available_stations']}/{status['total_stations']}")

# QC ZONE
# Move papers to QC
result = control.move_papers_to_qc()
print(f"Moved {result['papers_moved']} papers to QC")

# Start QC check
for paper_id in result['paper_ids']:
    control.start_qc_check(paper_id, "QC_Operator_1")
    
    # Pass or fail
    qc_result = control.complete_qc_check(
        paper_id=paper_id,
        checked_by="QC_Operator_1",
        passed=True,  # or False with issues
        notes="Good quality scan"
    )
    
    # If failed and needs rescan
    if not qc_result.get('passed') and qc_result.get('needs_rescan'):
        control.send_for_rescan(paper_id)

# Check QC stats
status = control.get_qc_status()
print(f"QC pass rate: {status['statistics']['pass_rate']:.1f}%")
```

## Box Status Flow
```
RECEIVED → LOGGED → IN_QUEUE → UNBOXING → SORTING_PREP → 
STAPLE_REMOVAL → PREP_COMPLETE → IN_QUEUE → SCANNING → 
SCAN_COMPLETE → QC_REVIEW → QC_PASSED/QC_FAILED → 
PROCESSING → SORTED → COMPLETE
```

## QC Issue Types
- **poor_quality**: Low scan quality
- **missing_pages**: Incomplete document
- **blurry**: Unclear or out of focus
- **misaligned**: Pages not properly aligned
- **incomplete**: Document cut off
- **other**: Other issues

## Scanning Stations
- **ADF (Automatic Document Feeder)**: High-speed batch scanning
- **Workstation**: Manual scanning for delicate/special documents

## Safety Features
- Capacity limits to prevent overflow
- Status validation before movement
- Complete audit trail
- Error handling and logging

## Next Steps (Coming Soon)
- [ ] Scanning zone integration
- [ ] OCR processing with Tesseract
- [ ] Document classification
- [ ] Authorization system
- [ ] REST API endpoints
- [ ] Database persistence

## Requirements
- Python 3.9+
- Docker & Docker Compose (for containerized deployment)
- See `requirements.txt` for full dependency list

## Docker Deployment

The application is fully containerized for easy deployment:

```powershell
# Quick start with helper script
.\docker-helper.ps1 build    # Build image
.\docker-helper.ps1 up       # Start container
.\docker-helper.ps1 status   # Check status
.\docker-helper.ps1 shell    # Access container

# Or use docker-compose directly
docker-compose up -d
docker-compose exec puda-app bash
```

**Features:**
- Pre-configured with Tesseract OCR
- Persistent data volumes
- Development mode with live code mounting
- Easy scaling for production

See [DOCKER.md](DOCKER.md) for complete Docker documentation.

## Development
Follow PEP 8 style guidelines and include type hints for all functions.

## License
MIT
