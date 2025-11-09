# Organization Layer - Quick Start Guide

## Overview
The Organization Layer automatically organizes QC-verified documents into a structured digital archive using folder conventions: `{Owner}/{Year}/{DocType}/{BatchID}/`

## Key Components

### 1. Archive Manager (`src/organization/archive.py`)
- Manages folder structure and document filing
- Handles copy/move operations
- Maintains JSON-based archive index
- Performs integrity verification

### 2. Archive Indexer (`src/organization/indexer.py`)
- SQLite database with full-text search (FTS5)
- Fast filtering by owner, year, doc_type, batch, QC status
- Statistics and analytics

### 3. Organization Automation (`src/organization/automation.py`)
- Monitors QC results directory
- Auto-archives approved documents
- Conflict resolution and retry logic
- Daemon mode for continuous operation

## Quick Start

### 1. Start Automation Daemon
```powershell
# Auto-organize approved documents
python archive_cli.py auto

# Run once instead of continuous daemon
python archive_cli.py auto --once

# Custom polling interval (60 seconds)
python archive_cli.py auto --interval 60

# Also archive failed documents
python archive_cli.py auto --include-failed
```

### 2. Search Archive
```powershell
# Search all documents
python archive_cli.py search

# Filter by owner
python archive_cli.py search --owner JohnDoe

# Filter by year and document type
python archive_cli.py search --year 2024 --doc-type Invoice

# Full-text search in OCR content
python archive_cli.py search --text "total amount"

# Filter by QC status
python archive_cli.py search --qc-status pass

# Combine filters with pagination
python archive_cli.py search --owner JohnDoe --year 2024 --limit 20 --offset 0
```

### 3. Retrieve Document Details
```powershell
# Get document details
python archive_cli.py retrieve PAGE_001

# Show full metadata
python archive_cli.py retrieve PAGE_001 --show-metadata

# Show file contents (JSON, OCR text)
python archive_cli.py retrieve PAGE_001 --show-content
```

### 4. View Statistics
```powershell
# Archive and index statistics
python archive_cli.py stats
```

### 5. Integrity Check
```powershell
# Verify archive integrity (check for missing/orphaned files)
python archive_cli.py integrity
```

### 6. Rebuild Index
```powershell
# Incremental reindex
python archive_cli.py reindex

# Full reindex (clear and rebuild)
python archive_cli.py reindex --full
```

## Programmatic Usage

### Archive a Document
```python
from src.organization import ArchiveManager, FolderStructure

manager = ArchiveManager(base_dir="data/archive")

# Define folder structure
folder = FolderStructure(
    owner="JohnDoe",
    year="2024",
    doc_type="Invoice",
    batch_id="batch_001"
)

# Archive document
archive = manager.archive_document(
    page_id="PAGE_001",
    source_files={
        'image': Path("data/scans/PAGE_001.png"),
        'json': Path("data/scans/PAGE_001.json"),
        'ocr': Path("data/scans/PAGE_001_ocr.txt")
    },
    metadata={'owner': 'JohnDoe', 'year': '2024'},
    folder_structure=folder
)
```

### Search Archive
```python
from src.organization import ArchiveIndexer, SearchQuery

indexer = ArchiveIndexer()

# Build search query
query = SearchQuery(
    owner="JohnDoe",
    year="2024",
    doc_type="Invoice",
    text="total amount",  # Full-text search
    limit=20,
    offset=0
)

# Execute search
results = indexer.search(query)

for doc in results:
    print(f"{doc['page_id']}: {doc['folder_path']}")

indexer.close()
```

### Run Automation
```python
from src.organization import OrganizationAutomation

automation = OrganizationAutomation(
    auto_archive_approved=True,
    auto_archive_failed=False
)

# Process all pending QC results
count = automation.scan_and_process()
print(f"Processed {count} documents")

# Or run as daemon
automation.run_daemon(interval_seconds=30)
```

## Folder Structure

Documents are organized as:
```
data/archive/
├── JohnDoe/
│   ├── 2024/
│   │   ├── Invoice/
│   │   │   ├── batch_001/
│   │   │   │   ├── INV_001.png
│   │   │   │   ├── INV_001.json
│   │   │   │   └── INV_001_ocr.txt
│   │   │   └── batch_002/
│   │   └── Receipt/
│   └── 2023/
└── JaneSmith/
```

## Database Schema

**documents** table:
- page_id (PRIMARY KEY)
- owner, year, doc_type, batch_id (indexed)
- folder_path
- archived_at (indexed)
- qc_status (indexed)
- metadata (JSON)

**files** table:
- id (PRIMARY KEY)
- page_id (FOREIGN KEY)
- file_type
- file_path

**documents_fts** (FTS5 virtual table):
- Full-text search on ocr_text

## Workflow Integration

The Organization Layer integrates with the QC system:

1. **Document Processing** → Scan → Extract → Classify → Route
2. **QC Verification** → Human review → Pass/Fail decision
3. **Auto-Organization** → Daemon monitors QC results → Archives approved docs
4. **Retrieval** → Search archive → Retrieve documents

## Configuration

Default directories:
- Archive: `data/archive/`
- QC Results: `data/qc_results/`
- Database: `data/organization/archive.db`

## Troubleshooting

### Documents not being auto-archived
- Check automation daemon is running: `python archive_cli.py auto`
- Verify QC results exist: `ls data/qc_results/*_qc.json`
- Check processed results: `cat data/qc_results/.processed_qc_results.json`

### Search returns no results
- Rebuild index: `python archive_cli.py reindex --full`
- Check database exists: `ls data/organization/archive.db`
- Verify documents are archived: `python archive_cli.py stats`

### Missing files
- Run integrity check: `python archive_cli.py integrity`
- Check source files exist before archiving
- Verify folder permissions

## API Endpoints (Future)

Coming soon - dashboard integration:
- `GET /api/archive/stats` - Archive statistics
- `GET /api/archive/search` - Search with filters
- `GET /api/archive/document/<page_id>` - Retrieve document
- `POST /api/archive/organize` - Trigger organization
