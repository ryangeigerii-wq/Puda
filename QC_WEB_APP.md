# QC Web Application

## Overview
Interactive web-based interface for document verification with image display, text overlay, field correction, and comprehensive feedback logging.

## Features

### 🖼️ Image Viewer
- **Full document display** with canvas-based rendering
- **Zoom controls** (in/out/reset)
- **Pan navigation** (drag to move)
- **Text overlay** visualization (toggle on/off)
- **Field highlighting** with confidence indicators

### ✏️ Interactive Corrections
- **Field-by-field editing** with real-time validation
- **Confidence indicators** for each field
- **Document type correction** if misclassified
- **Issue categorization** (9 categories)
- **Notes** for detailed feedback

### ⌨️ Keyboard Shortcuts
- `A` - Approve task
- `R` - Reject task
- `E` - Escalate task
- `S` - Skip task
- `N` - Next field
- `?` - Show help

### 📊 Real-time Metrics
- **Task timer** (tracks time spent)
- **Operator badge** (shows current user)
- **Confidence bars** (classification & field levels)
- **Routing reasons** (why sent to QC)

### 💾 Comprehensive Logging
All corrections logged for ML retraining:
- **Before/after values** for each field
- **Operator confidence** in corrections
- **Issue categories** identified
- **Time spent** on verification
- **Pass/fail status** written to metadata

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   QC Web Interface                      │
│  (HTML/CSS/JS - static/qc/qc_interface.html)           │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP API
┌────────────────▼────────────────────────────────────────┐
│              qc_app.py (Flask Server)                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Routes:                                          │  │
│  │  GET  /                    → Serve UI            │  │
│  │  GET  /api/qc/task/next    → Get next task      │  │
│  │  GET  /api/qc/task/<id>    → Get task details   │  │
│  │  GET  /api/qc/image/<path> → Serve image        │  │
│  │  POST /api/qc/task/<id>/submit → Submit verify  │  │
│  │  POST /api/qc/task/<id>/release → Release task  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│              QCInterface (src/qc/interface.py)          │
│  - Task retrieval (priority-based)                     │
│  - Verification submission                             │
│  - Metadata updates                                    │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  QCQueue           FeedbackCollector                    │
│  (queue.py)        (feedback.py)                        │
│  - Task storage    - Feedback JSONL logs               │
│  - Status tracking - ML training export                 │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Create Sample Tasks
```bash
python test_qc_web.py
```
Creates 3 sample tasks:
- Invoice with low field confidence
- ID document with classification uncertainty
- Form with missing fields

### 2. Start QC Application
```bash
python qc_app.py --port 8081
```

### 3. Open Interface
Navigate to: `http://127.0.0.1:8081`

Enter your operator ID when prompted.

## API Endpoints

### Get Next Task
```http
GET /api/qc/task/next?operator_id=alice
```
Response:
```json
{
  "status": "ok",
  "task": {
    "task_id": "test_invoice_001",
    "page_id": "page_invoice_001",
    "doc_type": "invoice",
    "severity": "qc",
    "classification_confidence": 0.82,
    "avg_field_confidence": 0.61,
    "extracted_fields": {
      "invoice_number": "INV-2024-001",
      "total_amount": "1,234.56"
    },
    "field_confidences": {
      "invoice_number": 0.85,
      "total_amount": 0.42
    },
    "routing_reasons": [
      "field_conf_low:0.61",
      "missing_fields:vendor_name"
    ],
    "image_path": "data/scans/test_invoice.png",
    "ocr_text": "INVOICE\nInvoice Number: INV-2024-001..."
  }
}
```

### Submit Verification
```http
POST /api/qc/task/{task_id}/submit
Content-Type: application/json

{
  "operator_id": "alice",
  "approved": true,
  "field_corrections": [
    {
      "field_name": "total_amount",
      "original_value": "1,234.56",
      "corrected_value": "1234.56",
      "confidence_rating": 1.0,
      "notes": "Removed comma separator"
    }
  ],
  "issue_categories": ["field_parsing_error"],
  "operator_confidence": 0.95,
  "time_spent_seconds": 45,
  "notes": "Amount format needed correction"
}
```

Response:
```json
{
  "status": "ok",
  "message": "Verification submitted successfully"
}
```

### Serve Image
```http
GET /api/qc/image/data/scans/test_invoice.png
```
Returns: PNG image file

### Get Issue Categories
```http
GET /api/qc/issue_categories
```
Response:
```json
{
  "status": "ok",
  "categories": [
    {"value": "ocr_error", "label": "OCR Error"},
    {"value": "classification_error", "label": "Classification Error"},
    {"value": "field_extraction_error", "label": "Field Extraction Error"},
    ...
  ]
}
```

## Verification Workflow

### 1. Task Display
When operator loads interface:
1. Fetches next available task (assigned or highest priority)
2. Acquires task lock (prevents concurrent edits)
3. Displays document image in canvas
4. Shows extracted fields with confidence indicators
5. Lists routing reasons (why sent to QC)
6. Starts verification timer

### 2. Operator Review
Operator examines:
- **Document image** (zoom/pan as needed)
- **OCR text** (review accuracy)
- **Extracted fields** (check values and confidence)
- **Routing reasons** (understand issues)
- **Classification** (verify document type)

### 3. Corrections
Operator can:
- **Edit field values** (marks field as modified)
- **Change document type** (if misclassified)
- **Select issue categories** (what went wrong)
- **Add notes** (detailed feedback)

### 4. Submit Decision
Four actions available:
- **Approve** (✅) - Correct with optional corrections
- **Reject** (❌) - Flag for reprocessing
- **Escalate** (⚠️) - Promote to CRITICAL priority
- **Skip** (⏭️) - Release back to queue

### 5. Metadata & Logging
On submission:
1. **Field corrections** logged to `data/feedback/qc_feedback_YYYY-MM-DD.jsonl`
2. **QC status** written to document metadata JSON
3. **Pass/fail tag** added to artifact metadata
4. **QC result** written to `data/qc_results/{page_id}_qc.json`
5. Task status updated (completed/rejected/escalated)
6. Task lock released
7. Next task automatically loaded

## Metadata Structure

### Document Metadata JSON
Located at: `{image_path}.json` (e.g., `test_invoice.png.json`)

```json
{
  "processing": {
    "qc_verification": {
      "passed": true,
      "verified_at": "2025-11-08T22:30:15",
      "verified_by": "alice",
      "task_id": "test_invoice_001",
      "time_spent_seconds": 45,
      "operator_confidence": 0.95,
      "corrections_made": 1,
      "escalated": false,
      "notes": "Amount format needed correction",
      "corrected_doc_type": null,
      "issue_categories": ["field_parsing_error"]
    }
  }
}
```

### QC Result File
Located at: `data/qc_results/{page_id}_qc.json`

```json
{
  "page_id": "page_invoice_001",
  "task_id": "test_invoice_001",
  "doc_type": "invoice",
  "qc_status": {
    "passed": true,
    "verified_at": "2025-11-08T22:30:15",
    "verified_by": "alice",
    ...
  },
  "original_fields": {
    "invoice_number": "INV-2024-001",
    "total_amount": "1,234.56"
  },
  "corrected_fields": {
    "invoice_number": "INV-2024-001",
    "total_amount": "1234.56"
  },
  "field_corrections": [
    {
      "field": "total_amount",
      "original": "1,234.56",
      "corrected": "1234.56",
      "confidence": 1.0
    }
  ]
}
```

### Feedback Log Entry
Located at: `data/feedback/qc_feedback_2025-11-08.jsonl`

```json
{
  "timestamp": 1699488015.0,
  "task_id": "test_invoice_001",
  "page_id": "page_invoice_001",
  "operator_id": "alice",
  "original_doc_type": "invoice",
  "corrected_doc_type": "invoice",
  "original_fields": {"total_amount": "1,234.56"},
  "corrected_fields": {"total_amount": "1234.56"},
  "field_corrections": [
    {
      "field": "total_amount",
      "original": "1,234.56",
      "corrected": "1234.56",
      "confidence": 1.0,
      "notes": null
    }
  ],
  "issue_categories": ["field_parsing_error"],
  "classification_confidence": 0.82,
  "avg_field_confidence": 0.61,
  "operator_confidence": 0.95,
  "time_spent_seconds": 45,
  "severity": "qc",
  "notes": "Amount format needed correction",
  "approved": true,
  "escalated": false
}
```

## ML Training Integration

### Export Corrections for Training
```python
from src.qc.feedback import FeedbackCollector

collector = FeedbackCollector()

# Export high-quality verifications
collector.export_for_training(
    output_path="data/training/qc_corrections.jsonl",
    min_operator_confidence=0.8,
    approved_only=True
)
```

Training data format:
```json
{
  "page_id": "page_invoice_001",
  "doc_type": "invoice",
  "fields": {
    "invoice_number": "INV-2024-001",
    "total_amount": "1234.56"
  },
  "classification_was_correct": true,
  "field_corrections_made": true,
  "operator_confidence": 0.95,
  "original_classification_confidence": 0.82,
  "original_field_confidence": 0.61
}
```

### Use Cases for Training
1. **Classification Model**: Learn from corrected document types
2. **Field Extraction**: Improve parsing patterns from corrections
3. **OCR Post-processing**: Fix common OCR errors
4. **Confidence Calibration**: Align model confidence with accuracy
5. **Error Pattern Analysis**: Identify systematic issues

## Configuration

### Port and Host
```bash
python qc_app.py --port 8081 --host 0.0.0.0
```

### Debug Mode
```bash
python qc_app.py --debug
```

### Integration with Main Dashboard
Run both servers:
```bash
# Terminal 1: Main routing dashboard
python dashboard_api.py --port 8080

# Terminal 2: QC verification interface
python qc_app.py --port 8081
```

## Security Considerations

### Current Implementation (Development)
- No authentication required
- Operator ID stored in localStorage
- All endpoints publicly accessible

### Production Recommendations
1. **Authentication**: Add JWT or session-based auth
2. **Authorization**: Verify operator permissions per task
3. **HTTPS**: Use TLS for encrypted connections
4. **Rate Limiting**: Prevent abuse
5. **Input Validation**: Sanitize all user inputs
6. **CORS**: Restrict cross-origin requests
7. **Audit Logging**: Track all actions by operator

## Performance Tips

### Image Optimization
- Use compressed PNG or JPEG formats
- Consider serving thumbnails for preview
- Implement lazy loading for large batches

### Database Migration
Current: JSONL files (simple, portable)
Consider: PostgreSQL/MongoDB for production scale

### Caching
- Cache loaded images in browser
- Use Redis for task queue (high concurrency)
- Pre-load next task while operator reviews current

## Troubleshooting

### "No tasks available"
```bash
# Check queue
python -c "from src.qc.queue import QCQueue; print(QCQueue().get_queue_stats())"

# Create sample tasks
python test_qc_web.py
```

### Image not loading
- Verify `image_path` in task metadata
- Check file exists: `ls data/scans/`
- Ensure Flask has read permissions

### Task stuck "in progress"
Tasks auto-release after 30 min. Manual release:
```python
from src.qc.queue import QCQueue
queue = QCQueue()
task = queue.get_task("task_id")
task.release_lock("operator_id")
queue._save_task(task)
```

## Future Enhancements

- [ ] Text overlay visualization on image
- [ ] Bounding box drawing for fields
- [ ] Side-by-side comparison (original vs corrected)
- [ ] Batch processing mode
- [ ] Mobile-responsive design
- [ ] Real-time collaboration
- [ ] Undo/redo corrections
- [ ] Auto-save draft corrections
- [ ] Image annotation tools
- [ ] OCR re-run capability
- [ ] Task assignment dashboard
- [ ] Performance analytics dashboard
