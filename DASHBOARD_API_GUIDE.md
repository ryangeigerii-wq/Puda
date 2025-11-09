# Dashboard API Guide

Complete documentation for the Puda Paper Reader Dashboard API, including Organization Layer integration.

## Overview

The Dashboard API provides REST endpoints for:
- **Routing & QC Monitoring**: Real-time audit logs, queue stats, operator performance
- **Archive Management**: Search, retrieval, statistics for organized documents
- **Document Operations**: PDF merging, thumbnail generation, metadata export
- **System Health**: Health checks and service status

## Quick Start

### Starting the API Server

```bash
# Basic start
python dashboard_api.py

# Custom configuration
python dashboard_api.py --port 8080 --host 0.0.0.0 --archive-dir data/archive --debug
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | 8080 | Server port |
| `--host` | 127.0.0.1 | Server host (use 0.0.0.0 for external access) |
| `--audit-dir` | data | Directory for audit logs |
| `--archive-dir` | data/archive | Archive directory |
| `--debug` | False | Enable Flask debug mode |

## API Endpoints

### Health & Status

#### GET /api/health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "routing_dashboard_api"
}
```

---

### Archive Statistics

#### GET /api/archive/stats
Get archive statistics with optional filtering.

**Query Parameters:**
- `owner` (string, optional): Filter by owner
- `doc_type` (string, optional): Filter by document type
- `year` (integer, optional): Filter by year

**Example:**
```bash
curl "http://localhost:8080/api/archive/stats"
curl "http://localhost:8080/api/archive/stats?owner=Acme&year=2024"
```

**Response:**
```json
{
  "status": "ok",
  "statistics": {
    "total_documents": 150,
    "by_owner": {
      "Acme": 75,
      "TechCorp": 50,
      "SampleCorp": 25
    },
    "by_year": {
      "2024": 100,
      "2023": 50
    },
    "by_doc_type": {
      "Invoice": 80,
      "Receipt": 40,
      "Contract": 30
    },
    "by_qc_status": {
      "approved": 140,
      "rejected": 10
    }
  }
}
```

---

### Archive Search

#### GET /api/archive/search
Search archived documents with filters.

**Query Parameters:**
- `text` (string, optional): Full-text search query
- `owner` (string, optional): Filter by owner
- `doc_type` (string, optional): Filter by document type
- `year` (integer, optional): Filter by year
- `qc_status` (string, optional): Filter by QC status
- `limit` (integer, optional): Max results (default: 50, max: 500)
- `offset` (integer, optional): Results offset for pagination

**Example:**
```bash
# Search all documents
curl "http://localhost:8080/api/archive/search"

# Full-text search
curl "http://localhost:8080/api/archive/search?text=invoice"

# Filtered search with pagination
curl "http://localhost:8080/api/archive/search?owner=Acme&doc_type=Invoice&year=2024&limit=20&offset=0"
```

**Response:**
```json
{
  "status": "ok",
  "query": {
    "text": "invoice",
    "owner": "Acme",
    "doc_type": "Invoice",
    "year": 2024,
    "qc_status": null,
    "limit": 20,
    "offset": 0
  },
  "count": 15,
  "results": [
    {
      "page_id": "INV_001",
      "owner": "Acme",
      "year": "2024",
      "doc_type": "Invoice",
      "batch_id": "batch_001",
      "qc_status": "approved",
      "has_ocr": true,
      "classification_confidence": 0.98,
      "indexed_at": 1699401234.56
    }
  ]
}
```

---

### Document Retrieval

#### GET /api/archive/document/{page_id}
Get detailed information about a specific document.

**Example:**
```bash
curl "http://localhost:8080/api/archive/document/INV_001"
```

**Response:**
```json
{
  "status": "ok",
  "document": {
    "page_id": "INV_001",
    "owner": "Acme",
    "year": "2024",
    "doc_type": "Invoice",
    "batch_id": "batch_001",
    "image_path": "/path/to/image.png",
    "qc_status": "approved",
    "has_ocr": true,
    "ocr_text": "Invoice #12345...",
    "classification_confidence": 0.98,
    "indexed_at": 1699401234.56
  }
}
```

---

### Thumbnail Access

#### GET /api/archive/thumbnail/{page_id}
Retrieve thumbnail image for a document page.

**Query Parameters:**
- `size` (string, optional): Thumbnail size - `icon`, `small`, `medium`, `large` (default: small)

**Sizes:**
- `icon`: 64x64 px
- `small`: 150x200 px
- `medium`: 300x400 px
- `large`: 600x800 px

**Example:**
```bash
# Get small thumbnail
curl "http://localhost:8080/api/archive/thumbnail/INV_001?size=small" -o thumbnail.jpg

# Get large preview
curl "http://localhost:8080/api/archive/thumbnail/INV_001?size=large" -o preview.jpg
```

**Response:**
- Content-Type: `image/jpeg`
- Binary JPEG image data

---

### Thumbnail Cache Stats

#### GET /api/archive/thumbnail/cache/stats
Get thumbnail cache statistics.

**Example:**
```bash
curl "http://localhost:8080/api/archive/thumbnail/cache/stats"
```

**Response:**
```json
{
  "status": "ok",
  "cache_stats": {
    "thumbnails": 120,
    "manifests": 10,
    "total_size_mb": 5.42,
    "cache_directory": "data/archive/.thumbnails"
  }
}
```

---

### List Owners

#### GET /api/archive/owners
Get list of all owners in the archive.

**Example:**
```bash
curl "http://localhost:8080/api/archive/owners"
```

**Response:**
```json
{
  "status": "ok",
  "owners": ["Acme", "SampleCorp", "TechCorp"]
}
```

---

### List Document Types

#### GET /api/archive/doc_types
Get list of all document types in the archive.

**Example:**
```bash
curl "http://localhost:8080/api/archive/doc_types"
```

**Response:**
```json
{
  "status": "ok",
  "doc_types": ["Contract", "Invoice", "Receipt"]
}
```

---

### List Years

#### GET /api/archive/years
Get list of all years in the archive.

**Example:**
```bash
curl "http://localhost:8080/api/archive/years"
```

**Response:**
```json
{
  "status": "ok",
  "years": ["2024", "2023", "2022"]
}
```

---

### PDF Merge

#### POST /api/archive/merge
Trigger PDF merge for a batch.

**Request Body (JSON):**
```json
{
  "owner": "Acme",
  "year": 2024,
  "doc_type": "Invoice",
  "batch_id": "batch_001"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8080/api/archive/merge" \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "Acme",
    "year": 2024,
    "doc_type": "Invoice",
    "batch_id": "batch_001"
  }'
```

**Response:**
```json
{
  "status": "ok",
  "result": {
    "pdf_path": "data/archive/Acme/2024/Invoice/batch_001/Invoice_batch_001.pdf",
    "page_count": 5,
    "metadata_written": true
  }
}
```

---

### Thumbnail Generation

#### POST /api/archive/thumbnails/generate
Trigger thumbnail generation for a batch.

**Request Body (JSON):**
```json
{
  "owner": "Acme",
  "year": 2024,
  "doc_type": "Invoice",
  "batch_id": "batch_001",
  "force": false
}
```

**Example:**
```bash
curl -X POST "http://localhost:8080/api/archive/thumbnails/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "Acme",
    "year": 2024,
    "doc_type": "Invoice",
    "batch_id": "batch_001",
    "force": true
  }'
```

**Response:**
```json
{
  "status": "ok",
  "result": {
    "total_images": 5,
    "generated": 5,
    "skipped": 0,
    "failed": 0,
    "cache_size_mb": 0.25
  }
}
```

---

## QC Endpoints

### GET /api/qc/queue/stats
Get QC queue statistics.

**Response:**
```json
{
  "status": "ok",
  "queue_stats": {
    "total_tasks": 25,
    "pending": 15,
    "in_progress": 5,
    "completed": 5,
    "by_severity": {
      "qc": 10,
      "manual": 5
    }
  }
}
```

### GET /api/qc/queue/pending
Get pending QC tasks.

**Query Parameters:**
- `severity` (string, optional): Filter by severity
- `doc_type` (string, optional): Filter by document type
- `limit` (integer, optional): Max results (default: 20)

**Response:**
```json
{
  "status": "ok",
  "count": 15,
  "tasks": [
    {
      "task_id": "qc_001",
      "page_id": "INV_001",
      "doc_type": "Invoice",
      "severity": "qc",
      "priority": "HIGH",
      "status": "pending",
      "created_at": "2024-11-08T10:00:00",
      "assigned_to": null,
      "locked_by": null
    }
  ]
}
```

### GET /api/qc/feedback/stats
Get QC feedback statistics.

**Query Parameters:**
- `days` (integer, optional): Period in days (default: 30)

**Response:**
```json
{
  "status": "ok",
  "period_days": 30,
  "feedback_stats": {
    "total_reviews": 150,
    "approved": 140,
    "rejected": 10,
    "accuracy_rate": 0.93
  }
}
```

---

## Routing Endpoints

### GET /api/routing/summary
Get routing audit summary.

**Query Parameters:**
- `days` (integer, optional): Filter to last N days (default: 7)
- `doc_type` (string, optional): Filter by document type
- `severity` (string, optional): Filter by severity
- `operator` (string, optional): Filter by operator ID

### GET /api/routing/recent
Get recent routing decisions.

**Query Parameters:**
- `limit` (integer, optional): Max entries (default: 50, max: 500)

### GET /api/routing/trends
Get daily routing trends.

**Query Parameters:**
- `days` (integer, optional): Days to analyze (default: 30)

---

## Integration Examples

### Python Client

```python
import requests

BASE_URL = "http://localhost:8080"

# Search for documents
response = requests.get(
    f"{BASE_URL}/api/archive/search",
    params={"owner": "Acme", "doc_type": "Invoice", "limit": 10}
)
documents = response.json()["results"]

# Get thumbnail for first document
if documents:
    page_id = documents[0]["page_id"]
    response = requests.get(
        f"{BASE_URL}/api/archive/thumbnail/{page_id}",
        params={"size": "medium"}
    )
    with open(f"{page_id}_thumb.jpg", "wb") as f:
        f.write(response.content)

# Trigger PDF merge
response = requests.post(
    f"{BASE_URL}/api/archive/merge",
    json={
        "owner": "Acme",
        "year": 2024,
        "doc_type": "Invoice",
        "batch_id": "batch_001"
    }
)
result = response.json()
print(f"PDF created: {result['result']['pdf_path']}")
```

### JavaScript/Fetch

```javascript
const BASE_URL = 'http://localhost:8080';

// Search documents
async function searchDocuments(owner, docType) {
  const response = await fetch(
    `${BASE_URL}/api/archive/search?owner=${owner}&doc_type=${docType}`
  );
  const data = await response.json();
  return data.results;
}

// Get thumbnail URL
function getThumbnailURL(pageId, size = 'small') {
  return `${BASE_URL}/api/archive/thumbnail/${pageId}?size=${size}`;
}

// Generate thumbnails
async function generateThumbnails(owner, year, docType, batchId) {
  const response = await fetch(`${BASE_URL}/api/archive/thumbnails/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner, year, doc_type: docType, batch_id: batchId })
  });
  return await response.json();
}
```

### cURL Examples

```bash
# Get archive statistics
curl "http://localhost:8080/api/archive/stats" | jq

# Search with filters
curl "http://localhost:8080/api/archive/search?owner=Acme&year=2024" | jq

# Download thumbnail
curl "http://localhost:8080/api/archive/thumbnail/INV_001?size=large" -o preview.jpg

# Merge batch into PDF
curl -X POST "http://localhost:8080/api/archive/merge" \
  -H "Content-Type: application/json" \
  -d '{"owner":"Acme","year":2024,"doc_type":"Invoice","batch_id":"batch_001"}' | jq

# Generate thumbnails
curl -X POST "http://localhost:8080/api/archive/thumbnails/generate" \
  -H "Content-Type: application/json" \
  -d '{"owner":"Acme","year":2024,"doc_type":"Invoice","batch_id":"batch_001","force":false}' | jq
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message describing what went wrong"
}
```

HTTP Status Codes:
- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Module not available

---

## Testing

Run integration tests:

```bash
# Start the API server in one terminal
python dashboard_api.py --port 8080

# Run tests in another terminal
python test_dashboard_integration.py
```

---

## Performance Considerations

### Caching
- Thumbnails are cached in `.thumbnails` directory
- Use appropriate thumbnail sizes for different use cases
- Clear cache periodically if disk space is limited

### Search Optimization
- Full-text search uses SQLite FTS5 for fast queries
- Add indexes for frequently filtered fields
- Use pagination (`limit` and `offset`) for large result sets

### Concurrent Access
- Flask development server is single-threaded
- For production, use WSGI server (gunicorn, uwsgi)
- Archive operations are file-based and thread-safe

---

## Deployment

### Production Setup

```bash
# Install production WSGI server
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 dashboard_api:app

# With more workers and timeout
gunicorn -w 8 -b 0.0.0.0:8080 --timeout 120 dashboard_api:app
```

### Docker Deployment

Add to existing Dockerfile or docker-compose.yml:

```yaml
services:
  dashboard-api:
    build: .
    command: python dashboard_api.py --host 0.0.0.0 --port 8080
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    environment:
      - PYTHONUNBUFFERED=1
```

### Nginx Reverse Proxy

```nginx
location /api/ {
    proxy_pass http://localhost:8080/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

---

## Troubleshooting

### Module Not Available Errors

**Error:** `{"error": "Organization modules not available"}`

**Solution:**
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check import paths in `dashboard_api.py`
- Verify `src/organization/` directory exists

### Database Locked Errors

**Error:** Database locked during concurrent operations

**Solution:**
- Use WAL mode for SQLite (enabled by default)
- Reduce concurrent write operations
- Consider PostgreSQL for high-concurrency deployments

### Thumbnail Not Found

**Error:** `{"error": "Thumbnail not found"}`

**Solution:**
- Generate thumbnails first: POST to `/api/archive/thumbnails/generate`
- Check cache directory: `data/archive/.thumbnails/`
- Verify batch folder exists and contains images

---

## API Changelog

### Version 1.1 (Current)
- ✅ Added Organization Layer endpoints
- ✅ Archive statistics, search, and retrieval
- ✅ Thumbnail generation and serving
- ✅ PDF merge automation
- ✅ Owner/DocType/Year listing endpoints

### Version 1.0
- Initial routing and QC endpoints
- Health check
- Audit log summaries

---

## Support

For issues or questions:
1. Check this documentation
2. Review error messages and logs
3. Run integration tests
4. Check GitHub issues

---

**Last Updated:** November 8, 2024
