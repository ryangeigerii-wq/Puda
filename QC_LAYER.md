# Quality Control (QC) Layer

## Purpose
Human-in-the-loop verification layer for documents routed to QC queue or manual review. Captures operator feedback for model improvement and provides structured correction workflow.

## Architecture

### Components

1. **QC Queue** (`src/qc/queue.py`)
   - Task queue management with priority ordering
   - Task assignment and locking (prevents concurrent edits)
   - Status tracking (pending → assigned → in_progress → completed/rejected/escalated)
   - Operator workload management
   - JSONL persistence (`data/qc_queue.jsonl`)

2. **QC Interface** (`src/qc/interface.py`)
   - Operator task retrieval (priority-based)
   - Field correction submission
   - Document type corrections
   - Issue categorization
   - Performance metrics

3. **Feedback Collector** (`src/qc/feedback.py`)
   - Structured feedback storage (JSONL with daily rotation)
   - Operator performance statistics
   - Global quality metrics
   - ML training data export

4. **CLI Tool** (`qc_verify_cli.py`)
   - Interactive verification interface
   - Keyboard-driven workflow
   - Real-time statistics
   - Queue visibility

5. **Dashboard Integration** (`dashboard_api.py`)
   - QC queue statistics endpoint
   - Pending tasks API
   - Feedback statistics
   - Operator performance tracking

## Workflow

### 1. Task Creation
Documents routed to `qc_queue` or `manual_review` severity automatically create QC tasks:

```python
from src.processing.processing import build_default_pipeline

# Pipeline with QC enabled (default)
pipeline = build_default_pipeline()

# Process document - creates QC task if routed to qc/manual
result = pipeline.process(artifact, context)
```

### 2. Operator Verification

#### Interactive CLI
```bash
python qc_verify_cli.py --operator alice

# Commands:
#   next, n       - Get next task
#   stats         - Show your statistics
#   queue         - Show queue statistics
#   help          - Show help
#   quit, q       - Exit
```

#### Verification Process
1. System fetches highest priority unassigned task
2. Operator reviews:
   - Document image
   - OCR text
   - Extracted fields with confidence scores
   - Routing reasons (why sent to QC)
3. Operator actions:
   - **Approve**: Accept with optional corrections
   - **Reject**: Flag for re-processing
   - **Escalate**: Promote to CRITICAL priority
   - **Skip**: Release back to queue
4. Operator provides:
   - Field corrections (with confidence ratings)
   - Corrected document type (if misclassified)
   - Issue categories (OCR error, extraction error, etc.)
   - Notes
5. Feedback stored for ML retraining

### 3. Feedback Collection

Feedback stored in `data/feedback/qc_feedback_YYYY-MM-DD.jsonl`:

```json
{
  "timestamp": 1699488000.0,
  "task_id": "page_001_1699488000000",
  "page_id": "page_001",
  "operator_id": "alice",
  "original_doc_type": "invoice",
  "corrected_doc_type": "invoice",
  "field_corrections": [
    {
      "field": "total_amount",
      "original": "1,23.45",
      "corrected": "123.45",
      "confidence": 1.0,
      "notes": "OCR comma instead of decimal"
    }
  ],
  "issue_categories": ["ocr_error"],
  "operator_confidence": 0.95,
  "time_spent_seconds": 45,
  "approved": true
}
```

## Data Models

### QCTask
```python
@dataclass
class QCTask:
    task_id: str
    page_id: str
    batch_id: str
    doc_type: str
    severity: str                    # qc_queue | manual_review
    status: TaskStatus               # pending | assigned | in_progress | completed
    priority: TaskPriority           # LOW | MEDIUM | HIGH | CRITICAL
    created_at: float
    assigned_to: Optional[str]
    locked_by: Optional[str]         # Prevents concurrent edits
    metadata: Dict[str, Any]         # Confidences, reasons, thresholds
    image_path: str
    ocr_text: str
    extracted_fields: Dict[str, Any]
    operator_notes: Optional[str]
```

### FeedbackEntry
```python
@dataclass
class FeedbackEntry:
    timestamp: float
    task_id: str
    operator_id: str
    original_doc_type: str
    corrected_doc_type: str
    original_fields: Dict[str, Any]
    corrected_fields: Dict[str, Any]
    field_corrections: List[Dict]    # Detailed corrections
    issue_categories: List[IssueCategory]
    classification_confidence: float
    avg_field_confidence: float
    operator_confidence: float
    time_spent_seconds: int
    approved: bool
    escalated: bool
```

## Issue Categories

```python
class IssueCategory(Enum):
    OCR_ERROR = "ocr_error"
    CLASSIFICATION_ERROR = "classification_error"
    FIELD_EXTRACTION_ERROR = "field_extraction_error"
    FIELD_PARSING_ERROR = "field_parsing_error"
    LAYOUT_DETECTION_ERROR = "layout_detection_error"
    IMAGE_QUALITY = "image_quality"
    DOCUMENT_VARIATION = "document_variation"
    MULTI_PAGE_ERROR = "multi_page_error"
    OTHER = "other"
```

## API Endpoints

### QC Queue Stats
```
GET /api/qc/queue/stats
```
Response:
```json
{
  "status": "ok",
  "queue_stats": {
    "total": 150,
    "pending": 42,
    "assigned": 18,
    "in_progress": 5,
    "completed": 85,
    "by_severity": {"qc": 30, "manual": 12},
    "by_doc_type": {"invoice": 25, "id": 10, "form": 7},
    "by_priority": {"HIGH": 12, "MEDIUM": 30}
  }
}
```

### Pending Tasks
```
GET /api/qc/queue/pending?severity=manual&limit=10
```

### Feedback Statistics
```
GET /api/qc/feedback/stats?days=30
```
Response:
```json
{
  "status": "ok",
  "period_days": 30,
  "feedback_stats": {
    "total_entries": 250,
    "approved_rate": 0.92,
    "escalated_rate": 0.03,
    "avg_time_seconds": 52,
    "classification_errors": 12,
    "field_extraction_errors": 45,
    "issue_categories": {
      "ocr_error": 38,
      "field_extraction_error": 45,
      "classification_error": 12
    }
  }
}
```

### Operator Stats
```
GET /api/qc/operator/alice/stats?days=7
```

## ML Training Export

Export high-quality verified feedback for model retraining:

```python
from src.qc.feedback import FeedbackCollector

collector = FeedbackCollector()

# Export only approved verifications with high operator confidence
collector.export_for_training(
    output_path="data/training/qc_corrections.jsonl",
    min_operator_confidence=0.8,
    approved_only=True
)
```

Training format:
```json
{
  "page_id": "page_001",
  "doc_type": "invoice",
  "fields": {
    "invoice_number": "INV-2024-001",
    "total_amount": "123.45"
  },
  "classification_was_correct": true,
  "field_corrections_made": true,
  "operator_confidence": 0.95,
  "original_classification_confidence": 0.62,
  "original_field_confidence": 0.71
}
```

## Performance Metrics

### Queue Metrics
- Total tasks by status
- Average time in queue
- Tasks by severity/priority
- Completion rate

### Operator Metrics
- Tasks completed per day
- Average verification time
- Correction accuracy
- Approval/rejection rates
- Field correction frequency
- Issue category distribution

### Feedback Quality
- Operator confidence trends
- Classification error rates
- Field extraction error rates
- Most common issues
- Time-to-verify by doc type

## Configuration

### Enable/Disable QC

```python
# In RoutingProcessor initialization
processor = RoutingProcessor(
    enable_qc=True  # Creates QC tasks (default)
)

# Or disable for testing
processor = RoutingProcessor(
    enable_qc=False  # Only audit logs, no QC tasks
)
```

### Task Priority Mapping

- `severity="manual"` → `TaskPriority.HIGH`
- `severity="qc"` → `TaskPriority.MEDIUM`
- Escalated tasks → `TaskPriority.CRITICAL`

### Lock Timeout

Tasks auto-release after 30 minutes of inactivity to prevent stuck locks.

## Testing

```bash
# Run QC tests
python -m pytest test_qc_*.py -v

# Test CLI (dry run)
python qc_verify_cli.py --operator test_user --stats

# Check queue stats
python qc_verify_cli.py --queue-stats
```

## Integration Points

### 1. Processing Pipeline
`RoutingProcessor` automatically creates QC tasks for documents with `severity >= qc`.

### 2. Dashboard
Extended with QC-specific endpoints and UI views (queue status, operator workload).

### 3. Audit Logs
QC feedback linked to routing audit logs via `task_id` and `page_id`.

### 4. ML Pipeline
Training export provides ground truth for improving classification and extraction models.

## Best Practices

### For Operators
1. Review routing reasons first (explains why sent to QC)
2. Check confidence scores (highlights uncertain fields)
3. Verify OCR text matches image
4. Provide clear notes for patterns/issues
5. Use appropriate issue categories
6. Rate your own confidence honestly

### For Administrators
1. Monitor queue depth (pending tasks)
2. Track operator throughput
3. Review escalated tasks regularly
4. Analyze feedback trends for system improvements
5. Export training data monthly
6. Adjust routing thresholds based on QC load

### For ML Engineers
1. Use operator confidence >= 0.8 for training
2. Focus on frequently corrected fields
3. Analyze issue categories for feature engineering
4. Monitor classification error patterns
5. Correlate confidence scores with accuracy

## Future Enhancements

- [ ] Batch assignment (assign N tasks to operator)
- [ ] Task reassignment (supervisor override)
- [ ] Image annotation UI (mark regions)
- [ ] Keyboard shortcuts for faster verification
- [ ] Mobile-friendly verification interface
- [ ] Real-time collaboration (multiple operators)
- [ ] Auto-escalation rules (time-based, error patterns)
- [ ] Gamification (leaderboards, accuracy scores)
- [ ] Integration with external review tools
- [ ] Automated pre-population of corrections (suggested fixes)
