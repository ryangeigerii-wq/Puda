# ML Inference API

FastAPI REST endpoints for document intelligence pipeline.

## Endpoints

### Health Check
```bash
GET /health
```

### OCR - Extract Text from Images
```bash
POST /ocr
Content-Type: multipart/form-data

file: <image/pdf file>
```

**Response:**
```json
{
  "text": "Invoice from ACME Corp...",
  "confidence": 0.94,
  "language": "en",
  "word_count": 150
}
```

### Classification - Document Type
```bash
POST /classify
Content-Type: application/json

{
  "text": "Invoice from ACME Corp dated Nov 10, 2025 for $1,500.00"
}
```

**Response:**
```json
{
  "doc_type": "invoice",
  "confidence": 0.95,
  "all_scores": {
    "invoice": 0.95,
    "receipt": 0.03,
    "contract": 0.01,
    ...
  }
}
```

### Extraction - Field Extraction (NER)
```bash
POST /extract
Content-Type: application/json

{
  "text": "Invoice #INV-2025-001 dated 2025-11-10 total $1,500.00"
}
```

**Response:**
```json
{
  "fields": {
    "DATE": [
      {"text": "2025-11-10", "confidence": 0.98, "source": "pattern"}
    ],
    "AMOUNT": [
      {"text": "$1,500.00", "confidence": 0.97, "source": "pattern"}
    ],
    "INVOICE": [
      {"text": "INV-2025-001", "confidence": 0.99, "source": "pattern"}
    ]
  },
  "count": 3
}
```

### Summarization - Text Summary
```bash
POST /summarize
Content-Type: application/json

{
  "text": "<long document text>"
}
```

**Response:**
```json
{
  "summary": "Invoice from ACME Corp for $1,500.00 dated Nov 10, 2025...",
  "method": "heuristic"
}
```

### Full Analysis Pipeline
```bash
POST /analyze
Content-Type: multipart/form-data

file: <image/pdf file>  (or)
text: "document text"
```

**Response:**
```json
{
  "ocr": { ... },  // if image provided
  "classification": { ... },
  "extraction": { ... },
  "summary": { ... },
  "routing": {
    "confidence_weighted": 0.92,
    "entity_count": 5,
    "has_summary": true
  },
  "metrics": {
    "tokens_count": 150,
    "device": "cpu",
    "cache_hits": {"tokenizer": 0, "summary": 0}
  }
}
```

### Feedback - Submit Corrections
```bash
POST /feedback
Content-Type: application/json

{
  "text": "original document text",
  "corrected_type": "invoice",
  "corrected_fields": {
    "amount": 1500.00,
    "date": "2025-11-10"
  },
  "notes": "Amount was incorrectly extracted"
}
```

**Response:**
```json
{
  "status": "received",
  "message": "Feedback stored for learning. Thank you!",
  "feedback_id": "fb_12345"
}
```

## Running the API

### Development
```bash
# Direct run
cd src/inference
python api.py

# Or with uvicorn
uvicorn src.inference.api:app --reload --port 8001
```

### Production
```bash
uvicorn src.inference.api:app --host 0.0.0.0 --port 8001 --workers 4
```

### Docker
```bash
# Add to docker-compose.yml
docker-compose up ml-api
```

## Features

- **Lazy Loading**: Models loaded on first request
- **CPU Optimized**: Automatic quantization and thread tuning
- **CORS Enabled**: Ready for web UI integration
- **Error Handling**: Graceful degradation with helpful errors
- **Metrics**: Runtime metrics for monitoring
- **Hot Reload**: `/reload` endpoint for model updates

## Integration with UI

The API is CORS-enabled and ready to be called from the web UI (`process.html`):

```javascript
// Full pipeline
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8001/analyze', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result.classification.doc_type);  // "invoice"
console.log(result.extraction.fields.AMOUNT);  // ["$1,500.00"]
```

## API Documentation

Interactive API docs available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- OpenAPI JSON: `http://localhost:8001/openapi.json`

## Dependencies

```bash
pip install fastapi uvicorn python-multipart
```

All ML dependencies already in `requirements.txt`.

## Environment Variables

```bash
# Optional overrides
ML_MODEL_PATH=/path/to/models
ML_DEVICE=cpu  # or cuda
ML_NUM_THREADS=4
```

## Monitoring

Health check for monitoring systems:
```bash
curl http://localhost:8001/health
```

Returns model load status and availability.
