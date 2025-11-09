# PDF/A Merge Automation - Quick Reference

## Overview
Automatically merge document page images into searchable PDF/A files with embedded OCR text layers. PDF/A format ensures long-term archival quality.

**New:** Metadata files (JSON + CSV) are automatically written alongside each merged PDF.

## Installation

```powershell
pip install Pillow img2pdf pypdf
```

## Features

- **PDF/A Format**: Archival-quality PDFs meeting ISO 19005 standards
- **Searchable Text**: Embedded OCR text layer for full-text search
- **Batch Processing**: Merge all pages in a batch into single PDF
- **Metadata Embedding**: Title, author, keywords automatically embedded
- **JSON Metadata**: Complete batch metadata with page inventory and statistics
- **CSV Export**: Page-level data in spreadsheet format for analysis
- **Compression**: Optimized file size without quality loss
- **Automation**: Auto-merge completed batches

## Metadata Files

When a batch is merged, three files are created:

1. **PDF File**: `{DocType}_{BatchID}.pdf`
   - Merged pages with embedded OCR text layer
   - Searchable, archival-quality PDF/A-2b

2. **JSON Metadata**: `{DocType}_{BatchID}_metadata.json`
   - Complete batch information
   - Page inventory with extracted fields
   - QC statistics and summary
   - Machine-readable format

3. **CSV Inventory**: `{DocType}_{BatchID}_pages.csv`
   - Page-level data in tabular format
   - All extracted fields as columns
   - Easy to import into Excel/databases
   - Suitable for reporting and analysis

### JSON Metadata Structure

```json
{
  "batch": {
    "owner": "JohnDoe",
    "year": "2024",
    "doc_type": "Invoice",
    "batch_id": "batch_001",
    "created_at": "2025-11-08T18:15:44",
    "page_count": 10,
    "pdf_file": "Invoice_batch_001.pdf"
  },
  "pages": [
    {
      "page_id": "INV_001",
      "image_file": "INV_001.png",
      "qc_status": "pass",
      "fields": {
        "invoice_number": "INV-2024-001",
        "customer_name": "ACME Corp",
        "invoice_date": "2024-01-15",
        "total_amount": "1250.00"
      },
      "has_ocr": true,
      "ocr_length": 280
    }
    // ... more pages
  ],
  "summary": {
    "total_pages": 10,
    "qc_passed": 9,
    "qc_failed": 1,
    "qc_pending": 0,
    "fields_extracted": {
      "invoice_number": 10,
      "customer_name": 10,
      "total_amount": 10
    }
  }
}
```

### CSV Format

```csv
page_id,image_file,qc_status,has_ocr,ocr_length,invoice_number,customer_name,total_amount
INV_001,INV_001.png,pass,True,280,INV-2024-001,ACME Corp,1250.00
INV_002,INV_002.png,pass,True,285,INV-2024-002,ACME Corp,1500.00
```

## CLI Commands

### Merge Specific Batch
```powershell
# Merge a specific batch
python archive_cli.py merge --owner JohnDoe --year 2024 --doc-type Invoice --batch-id batch_001

# Result: Creates JohnDoe/2024/Invoice/batch_001/Invoice_batch_001.pdf
```

### Merge All Batches (Filtered)
```powershell
# Merge all batches for an owner
python archive_cli.py merge --owner JohnDoe

# Merge all invoices for 2024
python archive_cli.py merge --year 2024 --doc-type Invoice

# Merge everything
python archive_cli.py merge
```

### Auto-Merge Automation
```powershell
# Scan and merge all eligible batches once
python archive_cli.py merge-auto --once

# Only merge batches with 5+ pages
python archive_cli.py merge-auto --once --min-pages 5
```

### Batch Information
```powershell
# Get batch details before merging
python archive_cli.py batch-info JohnDoe 2024 Invoice batch_001

# Output:
# === Batch Info ===
# Folder: data/archive/JohnDoe/2024/Invoice/batch_001
# Pages: 10
# Size: 12.5 MB
# Has PDF: No
# Page IDs: [list of pages]
```

### View Metadata
```powershell
# View batch metadata (JSON summary)
python archive_cli.py metadata JohnDoe 2024 Invoice batch_001

# Show page-level details
python archive_cli.py metadata JohnDoe 2024 Invoice batch_001 --show-pages

# Show CSV data preview
python archive_cli.py metadata JohnDoe 2024 Invoice batch_001 --show-csv

# Output:
# === Metadata: Invoice_batch_001_metadata.json ===
# Owner: JohnDoe
# Year: 2024
# Document Type: Invoice
# Pages: 10
# QC Passed: 9
# QC Failed: 1
# Extracted Fields: invoice_number, customer_name, total_amount
```

## Programmatic Usage

### Basic Merge
```python
from src.organization import PDFMerger

merger = PDFMerger()

# Merge specific batch
pdf_path = merger.merge_batch(
    owner="JohnDoe",
    year="2024",
    doc_type="Invoice",
    batch_id="batch_001"
)

print(f"Created: {pdf_path}")
```

### Merge with Filters
```python
# Merge all batches for owner
pdfs = merger.merge_all_batches(owner="JohnDoe")

# Merge all invoices
pdfs = merger.merge_all_batches(doc_type="Invoice")

# Merge all 2024 documents
pdfs = merger.merge_all_batches(year="2024")
```

### Get Batch Info
```python
info = merger.get_batch_info(
    owner="JohnDoe",
    year="2024",
    doc_type="Invoice",
    batch_id="batch_001"
)

print(f"Pages: {info['page_count']}")
print(f"Size: {info['total_size_mb']:.2f} MB")
print(f"Has PDF: {info['has_pdf']}")
```

### Automated Merging
```python
from src.organization import PDFMergeAutomation

automation = PDFMergeAutomation(
    auto_merge=True,
    min_pages=1  # Minimum pages to trigger merge
)

# Scan and merge all eligible batches
count = automation.scan_and_merge()
print(f"Merged {count} batches")

# Get statistics
stats = automation.get_statistics()
print(f"Total merged: {stats['total_merged']}")
```

## PDF Features

### What Gets Merged
- All page images (PNG, JPG) in the batch folder
- Sorted alphabetically by filename
- Maintains original image quality (no recompression)

### Embedded Metadata
```python
# Automatically embedded in PDF:
{
    'Title': 'Invoice - JohnDoe - 2024',
    'Author': 'JohnDoe',
    'Subject': 'Invoice documents for 2024',
    'Creator': 'PUDA Paper Reader',
    'Keywords': 'Invoice, JohnDoe, 2024, batch_001',
    'CreationDate': 'D:20250108120000'
}
```

### OCR Text Layer
- Embedded as invisible text overlay (searchable)
- Preserves visual quality of original images
- Enables text search within PDF readers
- Supports copy/paste of recognized text

## Workflow Integration

### Complete Pipeline
1. **Scan** → Pages captured as images
2. **Process** → OCR and classification
3. **QC** → Human verification
4. **Organize** → Archived to structured folders
5. **Merge** → Pages merged into PDF/A ← **NEW**

### Automation Flow
```
QC Approved → Archive → Auto-Merge → Searchable PDF
```

### Example: Full Automation
```python
# 1. Archive automation (from QC results)
from src.organization import OrganizationAutomation
archive_automation = OrganizationAutomation(auto_archive_approved=True)
archive_automation.scan_and_process()

# 2. PDF merge automation (from archived batches)
from src.organization import PDFMergeAutomation
merge_automation = PDFMergeAutomation(auto_merge=True)
merge_automation.scan_and_merge()
```

## Output Structure

```
data/archive/
├── JohnDoe/
│   ├── 2024/
│   │   ├── Invoice/
│   │   │   ├── batch_001/
│   │   │   │   ├── INV_001.png
│   │   │   │   ├── INV_001.json
│   │   │   │   ├── INV_001_ocr.txt
│   │   │   │   ├── INV_002.png
│   │   │   │   ├── INV_002.json
│   │   │   │   ├── INV_002_ocr.txt
│   │   │   │   ├── Invoice_batch_001.pdf              ← Merged PDF
│   │   │   │   ├── Invoice_batch_001_metadata.json    ← JSON metadata
│   │   │   │   └── Invoice_batch_001_pages.csv        ← CSV inventory
```

## Use Cases

### Data Analysis
```python
import pandas as pd

# Load CSV for analysis
df = pd.read_csv('data/archive/JohnDoe/2024/Invoice/batch_001/Invoice_batch_001_pages.csv')

# Analyze totals
print(f"Total invoices: {len(df)}")
print(f"Total amount: ${df['total_amount'].astype(float).sum():.2f}")
print(f"QC pass rate: {(df['qc_status'] == 'pass').sum() / len(df) * 100:.1f}%")

# Filter by customer
customer_invoices = df[df['customer_name'] == 'ACME Corp']
```

### Batch Processing
```python
import json

# Load JSON metadata for programmatic access
with open('Invoice_batch_001_metadata.json', 'r') as f:
    metadata = json.load(f)

# Check QC status
if metadata['summary']['qc_failed'] > 0:
    print(f"Warning: {metadata['summary']['qc_failed']} pages failed QC")

# Extract all invoice numbers
invoice_numbers = [
    page['fields']['invoice_number']
    for page in metadata['pages']
    if 'invoice_number' in page['fields']
]
```

### Export to Database
```python
import sqlite3
import csv

conn = sqlite3.connect('invoices.db')
cursor = conn.cursor()

# Create table from CSV structure
cursor.execute('''
    CREATE TABLE IF NOT EXISTS invoice_pages (
        page_id TEXT PRIMARY KEY,
        invoice_number TEXT,
        customer_name TEXT,
        invoice_date TEXT,
        total_amount REAL,
        qc_status TEXT
    )
''')

# Import CSV data
with open('Invoice_batch_001_pages.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute('''
            INSERT OR REPLACE INTO invoice_pages VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            row['page_id'],
            row['invoice_number'],
            row['customer_name'],
            row['invoice_date'],
            float(row['total_amount']),
            row['qc_status']
        ))

conn.commit()
```

## Technical Details

### PDF/A Compliance
- PDF/A-2b format (ISO 19005-2)
- All fonts embedded
- No external dependencies
- Self-contained document
- Long-term archival quality

### Image Handling
- Uses `img2pdf` for efficient conversion
- No recompression (preserves quality)
- Maintains original DPI
- Supports PNG and JPEG formats

### Text Layer Implementation
- OCR text embedded using pypdf
- Invisible text overlay
- Searchable in PDF readers
- Maintains visual fidelity

### Performance
- Typical merge speed: 1-2 pages/second
- Minimal memory usage (streaming)
- No temporary files created
- Efficient batch processing

## Common Patterns

### Merge After QC Approval
```python
# In your workflow automation
if qc_status['passed']:
    # Archive document
    archive_manager.archive_document(...)
    
    # Check if batch complete (e.g., 10 pages)
    if batch_page_count >= 10:
        # Merge into PDF
        merger.merge_batch(owner, year, doc_type, batch_id)
```

### Nightly Batch Job
```python
# Scheduled task (cron/Task Scheduler)
from src.organization import PDFMergeAutomation

automation = PDFMergeAutomation(min_pages=5)
count = automation.scan_and_merge()

print(f"Nightly merge: {count} batches processed")
```

### On-Demand Retrieval
```python
# User requests documents for date range
# 1. Search archive
results = indexer.search(SearchQuery(
    owner="JohnDoe",
    year="2024",
    doc_type="Invoice"
))

# 2. Merge into PDF if not exists
for result in results:
    batch = result['batch_id']
    info = merger.get_batch_info(owner, year, doc_type, batch)
    
    if not info['has_pdf']:
        pdf = merger.merge_batch(owner, year, doc_type, batch)
        send_to_user(pdf)
```

## Troubleshooting

### Import Error
```
Error: PIL and img2pdf required
Solution: pip install Pillow img2pdf pypdf
```

### No Pages Found
```
Error: No pages found in batch
Solution: Check batch folder contains .png or .jpg files
```

### PDF Already Exists
```
Note: Batch already has PDF
Solution: Delete existing PDF to regenerate, or skip
```

### Large File Size
```
Issue: PDF larger than expected
Solution: Page images may be high DPI - consider resizing before archival
```

## Next Steps

1. **Install dependencies**: `pip install Pillow img2pdf pypdf`
2. **Test merge**: `python archive_cli.py batch-info [owner] [year] [doc_type] [batch]`
3. **Merge batch**: `python archive_cli.py merge --batch-id [batch]`
4. **Enable automation**: `python archive_cli.py merge-auto --once`

## API Integration (Future)

Coming soon - Dashboard endpoints:
- `POST /api/archive/merge` - Trigger batch merge
- `GET /api/archive/batch/<batch_id>/pdf` - Download merged PDF
- `GET /api/archive/merge/status` - Check merge status
