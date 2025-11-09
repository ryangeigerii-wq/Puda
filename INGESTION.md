# Data Ingestion Layer

Purpose: Capture and version every page produced by scanning.

## Concepts
- **PageCapture**: Logical page (paper_id + page_number).
- **PageVersion**: Immutable version artifact with hash and storage reference.
- **IngestionManager**: API facade to create and query versions.

## Features
- Version auto-increment per (paper_id, page_number)
- SHA256 integrity hashing
- Audit trail generation
- Statistics (total pages, total versions)

## Usage
```python
from src.ingestion.ingestion import IngestionManager

mgr = IngestionManager()
version1 = mgr.capture_page("PAPER-123", 1, b"raw bytes", "store/scan1.png")
version2 = mgr.capture_page("PAPER-123", 1, b"raw bytes modified", "store/scan1_v2.png")
latest = mgr.get_latest_version("PAPER-123", 1)
trail = mgr.audit_trail("PAPER-123")
stats = mgr.stats()
```

## Integrity Verification
You can verify a version's integrity by recomputing hash:
```python
page = mgr.get_page("PAPER-123", 1)
assert page.verify_integrity()  # latest exists
assert page.verify_integrity(content_bytes=b"raw bytes modified") is False
```

## Future Enhancements
- Persistent backing store (SQLite/PostgreSQL)
- Binary content streaming interface
- OCR text ingestion pipeline integration
- Retention policies (keep last N versions, archive old)
- Event hooks (on version created)

## Testing
See `test_ingestion.py` for basic examples.
