# Warehouse Scanner Integration Guide

## Overview

The `/analyze` endpoint processes warehouse scanner outputs (OCR'd text or raw text) and returns structured JSON optimized for CSV/Excel export. Perfect for integrating with warehouse management systems, inventory tracking, and document processing pipelines.

## API Endpoint

**URL:** `POST http://localhost:8001/analyze`

**Input Options:**
- **Text input:** Send pre-extracted text (from your scanner/OCR)
- **File upload:** Send image for OCR + analysis

## Response Structure

### Structured Data Format (CSV/Excel Ready)

The `structured_data` field provides a **flattened, single-level dictionary** with all values as primitive types (str, float, int). No nested objects - ready for immediate CSV/Excel export.

```json
{
  "structured_data": {
    "scan_timestamp": "2025-11-10T13:00:00.123456",
    "document_type": "invoice",
    "classification_confidence": 0.9547,
    
    "text_preview": "ACME Corporation Invoice #12345 Date: 2024-01-15...",
    "full_text": "Complete document text...",
    "summary": "Invoice from ACME Corporation dated 2024-01-15 for $1,234.56",
    
    "date": "2024-01-15",
    "date_confidence": 0.98,
    
    "amount": "$1,234.56",
    "amount_confidence": 0.95,
    
    "invoice_number": "INV-12345",
    "invoice_confidence": 0.99,
    
    "organization": "ACME Corporation",
    "organization_confidence": 0.97,
    
    "contact_name": "John Smith",
    "name_confidence": 0.92,
    
    "address": "123 Main St, City, ST 12345",
    "address_confidence": 0.88,
    
    "email": "john@acme.com",
    "phone": "+1-555-0123",
    
    "total_dates": 1,
    "total_amounts": 1,
    "total_organizations": 1,
    "total_entities": 8,
    
    "processing_status": "completed",
    "requires_review": "no",
    
    "ocr_confidence": 0.96,
    "ocr_language": "eng",
    "ocr_word_count": 156
  }
}
```

### Key Features

✅ **Single-level structure** - No nested objects  
✅ **Primitive types only** - strings, floats, integers  
✅ **Empty field handling** - Empty strings (not null) for missing data  
✅ **Confidence scores** - ML confidence for each extracted field  
✅ **Warehouse-optimized** - First occurrence of key fields (invoice#, date, amount)  
✅ **Review flags** - Automatic flagging of low-confidence documents  
✅ **Timestamps** - ISO format timestamps for audit trails  

## Usage Examples

### 1. Direct Text Input (Pre-OCR'd)

If your scanner already performs OCR, send the text directly:

```bash
curl -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "ACME Corporation\nInvoice #12345\nDate: 2024-01-15\nAmount: $1,234.56"}'
```

**Response:**
```json
{
  "classification": {...},
  "extraction": {...},
  "summary": {...},
  "structured_data": {
    "document_type": "invoice",
    "invoice_number": "INV-12345",
    "date": "2024-01-15",
    "amount": "$1,234.56",
    ...
  }
}
```

### 2. Image Upload (With OCR)

Send scanned images for OCR + analysis:

```bash
curl -X POST http://localhost:8001/analyze \
  -F "file=@scanned_invoice.jpg"
```

### 3. Python Integration

```python
import requests

# Analyze text
response = requests.post(
    "http://localhost:8001/analyze",
    json={"text": "Your document text here"}
)

data = response.json()
structured = data["structured_data"]

# Access fields
print(f"Invoice: {structured['invoice_number']}")
print(f"Amount: {structured['amount']}")
print(f"Date: {structured['date']}")
```

### 4. Export to CSV

Use the provided export utility:

```bash
# Single document
python export_warehouse_data.py \
  --text "Invoice text..." \
  --output results.csv

# Single file
python export_warehouse_data.py \
  --file scanned_doc.jpg \
  --output results.csv

# Batch processing
python export_warehouse_data.py \
  --batch /path/to/scans/ \
  --output batch_results.xlsx
```

### 5. Excel Export (with pandas)

```python
import requests
import pandas as pd

# Process multiple documents
documents = [
    "Invoice text 1...",
    "Receipt text 2...",
    "Contract text 3..."
]

results = []
for text in documents:
    response = requests.post(
        "http://localhost:8001/analyze",
        json={"text": text}
    )
    structured = response.json()["structured_data"]
    results.append(structured)

# Export to Excel
df = pd.DataFrame(results)
df.to_excel("warehouse_data.xlsx", index=False)
print(f"Exported {len(results)} documents")
```

## Field Reference

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `scan_timestamp` | str | Processing timestamp (ISO format) | `2025-11-10T13:00:00.123456` |
| `document_type` | str | Classified document type | `invoice`, `receipt`, `contract` |
| `classification_confidence` | float | Classification confidence (0-1) | `0.9547` |
| `text_preview` | str | First 200 chars of text | `ACME Corporation Invoice...` |
| `full_text` | str | Complete document text | `Full text here...` |
| `summary` | str | Generated summary | `Invoice from ACME...` |
| `date` | str | First extracted date | `2024-01-15` |
| `date_confidence` | float | Date extraction confidence | `0.98` |
| `amount` | str | First extracted amount | `$1,234.56` |
| `amount_confidence` | float | Amount extraction confidence | `0.95` |
| `invoice_number` | str | Invoice/document number | `INV-12345` |
| `invoice_confidence` | float | Invoice# extraction confidence | `0.99` |
| `organization` | str | First organization name | `ACME Corporation` |
| `organization_confidence` | float | Org extraction confidence | `0.97` |
| `contact_name` | str | First person name | `John Smith` |
| `name_confidence` | float | Name extraction confidence | `0.92` |
| `address` | str | First address | `123 Main St, City, ST 12345` |
| `address_confidence` | float | Address extraction confidence | `0.88` |
| `email` | str | First email address | `john@acme.com` |
| `phone` | str | First phone number | `+1-555-0123` |
| `total_dates` | int | Count of all dates found | `1` |
| `total_amounts` | int | Count of all amounts found | `1` |
| `total_organizations` | int | Count of all orgs found | `1` |
| `total_entities` | int | Total entities extracted | `8` |
| `processing_status` | str | Processing status | `completed`, `failed` |
| `requires_review` | str | Review flag (confidence < 0.7) | `yes`, `no` |
| `ocr_confidence` | float | OCR confidence (if image input) | `0.96` |
| `ocr_language` | str | Detected language | `eng`, `fra`, `ara` |
| `ocr_word_count` | int | Words extracted by OCR | `156` |

## Warehouse Integration Patterns

### Pattern 1: Real-time Scanner Integration

```python
# Scanner callback function
def process_scanned_document(image_path):
    with open(image_path, 'rb') as f:
        response = requests.post(
            "http://localhost:8001/analyze",
            files={'file': f}
        )
    
    data = response.json()["structured_data"]
    
    # Auto-route based on confidence
    if data["requires_review"] == "yes":
        send_to_manual_review(data)
    else:
        auto_process_document(data)
```

### Pattern 2: Batch Processing Pipeline

```python
import pandas as pd
from pathlib import Path

def batch_process_warehouse_scans(scan_dir):
    results = []
    
    for scan_file in Path(scan_dir).glob("*.jpg"):
        with open(scan_file, 'rb') as f:
            response = requests.post(
                "http://localhost:8001/analyze",
                files={'file': f}
            )
        
        structured = response.json()["structured_data"]
        structured["source_file"] = scan_file.name
        results.append(structured)
    
    # Export to Excel
    df = pd.DataFrame(results)
    df.to_excel("daily_scans.xlsx", index=False)
    
    return df

# Run nightly batch
df = batch_process_warehouse_scans("/scans/today/")
print(f"Processed {len(df)} documents")
```

### Pattern 3: Database Integration

```python
import sqlite3

def store_analyzed_document(text):
    # Analyze
    response = requests.post(
        "http://localhost:8001/analyze",
        json={"text": text}
    )
    data = response.json()["structured_data"]
    
    # Store in database
    conn = sqlite3.connect("warehouse_docs.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO documents (
            timestamp, doc_type, confidence,
            invoice_number, date, amount, organization,
            requires_review, full_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["scan_timestamp"],
        data["document_type"],
        data["classification_confidence"],
        data["invoice_number"],
        data["date"],
        data["amount"],
        data["organization"],
        data["requires_review"],
        data["full_text"]
    ))
    
    conn.commit()
    conn.close()
```

## Performance Tips

1. **Batch Processing:** Process multiple documents in parallel for higher throughput
2. **Text Input:** If you have existing OCR, send text directly (faster than image OCR)
3. **Confidence Thresholds:** Adjust `requires_review` threshold based on your accuracy needs
4. **Field Priorities:** Use first occurrence fields for standard warehouse docs (single invoice#, date, amount)
5. **API Caching:** Cache model in API server for consistent latency (~100-500ms per document)

## Error Handling

```python
try:
    response = requests.post(
        "http://localhost:8001/analyze",
        json={"text": text},
        timeout=30
    )
    response.raise_for_status()
    
    data = response.json()["structured_data"]
    
except requests.exceptions.Timeout:
    print("API timeout - document too large?")
except requests.exceptions.HTTPError as e:
    print(f"API error: {e.response.status_code}")
except KeyError:
    print("Missing structured_data in response")
```

## Next Steps

1. **Test the endpoint:** Use the provided examples to test with your data
2. **Integrate with your scanner:** Connect your warehouse scanner output to `/analyze`
3. **Export data:** Use `export_warehouse_data.py` for CSV/Excel export
4. **Fine-tune model:** Use `/feedback` endpoint to improve accuracy on your specific documents
5. **Scale up:** Deploy API server for production use

## Support

- API Docs: http://localhost:8001/docs (Interactive Swagger UI)
- Redoc: http://localhost:8001/redoc (Alternative docs)
- Health Check: http://localhost:8001/health
