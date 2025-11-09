# Storage API Documentation

FastAPI-based REST API for storage operations, webhook triggers, and analytics.

## Overview

The Storage API provides a production-ready RESTful interface to the storage layer with:

- **RESTful Endpoints**: Complete CRUD operations for objects
- **File Upload/Download**: Multipart file upload with streaming responses
- **Version Management**: List versions, rollback to previous versions
- **Full-Text Search**: PostgreSQL-powered search (when enabled)
- **Webhook Management**: Register and manage integration webhooks
- **Analytics**: Storage statistics and usage metrics
- **Audit Logs**: Query access audit trail
- **Authentication**: Optional API key authentication
- **Auto Documentation**: Interactive Swagger/ReDoc documentation

## Quick Start

### Installation

```bash
# Install dependencies
pip install fastapi uvicorn python-multipart

# Install PostgreSQL support (optional)
pip install psycopg2-binary

# Install storage dependencies
pip install boto3
```

### Start API Server

```bash
# Basic usage (local storage)
python -m src.storage.storage_api

# With options
python -m src.storage.storage_api \
    --host 0.0.0.0 \
    --port 8000 \
    --backend local \
    --path data/storage \
    --api-key your-secret-key

# With S3 backend
export S3_ENDPOINT=http://localhost:9000
export S3_ACCESS_KEY=minioadmin
export S3_SECRET_KEY=minioadmin

python -m src.storage.storage_api \
    --backend s3 \
    --path archive \
    --api-key your-secret-key
```

### Using uvicorn directly

```bash
# Development mode with auto-reload
uvicorn src.storage.storage_api:app --reload --port 8000

# Production mode
uvicorn src.storage.storage_api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
```

### Access API Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Health Check

**GET** `/health`

Check API health and configuration.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-11-08T10:30:00",
  "storage_backend": "local",
  "postgres_enabled": true,
  "webhooks_enabled": true
}
```

### Storage Info

**GET** `/api/storage/info`

Get storage backend information.

**Headers:**
```
X-API-Key: your-api-key
```

**Response:**
```json
{
  "backend": "local",
  "versioning_enabled": true,
  "additional_info": {
    "base_path": "/app/data/storage",
    "max_versions": 10
  }
}
```

### Upload Object

**POST** `/api/storage/objects`

Upload file to storage.

**Headers:**
```
X-API-Key: your-api-key
Content-Type: multipart/form-data
```

**Query Parameters:**
- `key` (required): Object key/path (e.g., "documents/invoice.pdf")
- `metadata` (optional): JSON metadata (e.g., '{"owner":"ACME","type":"Invoice"}')
- `storage_class` (optional): Storage class (STANDARD, GLACIER, etc.)

**Body:**
- `file`: File to upload (multipart/form-data)

**Example with curl:**
```bash
curl -X POST "http://localhost:8000/api/storage/objects?key=documents/test.pdf" \
  -H "X-API-Key: your-api-key" \
  -F "file=@test.pdf" \
  -F 'metadata={"owner":"ACME","department":"Finance"}'
```

**Response:**
```json
{
  "object_key": "documents/test.pdf",
  "size": 524288,
  "etag": "d8e8fca2dc0f896fd7cb4cb0031ba249",
  "version_id": "v1",
  "content_type": "application/pdf",
  "upload_time": "2024-11-08T10:30:00"
}
```

### Download Object

**GET** `/api/storage/objects/{key:path}`

Download file from storage.

**Headers:**
```
X-API-Key: your-api-key
```

**Query Parameters:**
- `version_id` (optional): Specific version to download

**Example:**
```bash
curl -X GET "http://localhost:8000/api/storage/objects/documents/test.pdf" \
  -H "X-API-Key: your-api-key" \
  -o downloaded.pdf
```

**Response:**
- File content as binary stream
- Headers: `Content-Disposition`, `ETag`, `X-Version-ID`

### Get Object Metadata

**GET** `/api/storage/objects/{key:path}/metadata`

Get object metadata without downloading.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/storage/objects/documents/test.pdf/metadata" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "key": "documents/test.pdf",
  "size": 524288,
  "content_type": "application/pdf",
  "etag": "d8e8fca2dc0f896fd7cb4cb0031ba249",
  "last_modified": "2024-11-08T10:30:00",
  "version_id": "v1",
  "metadata": {
    "owner": "ACME",
    "department": "Finance"
  },
  "storage_class": "STANDARD"
}
```

### Delete Object

**DELETE** `/api/storage/objects/{key:path}`

Delete object from storage.

**Query Parameters:**
- `version_id` (optional): Delete specific version (otherwise deletes all)

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/storage/objects/documents/test.pdf" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "status": "deleted",
  "object_key": "documents/test.pdf",
  "version_id": null
}
```

### List Objects

**GET** `/api/storage/objects`

List objects with filters and pagination.

**Query Parameters:**
- `prefix` (optional): Key prefix filter
- `storage_backend` (optional): Filter by backend (local, s3)
- `limit` (default: 100, max: 1000): Maximum results
- `offset` (default: 0): Pagination offset

**Example:**
```bash
curl -X GET "http://localhost:8000/api/storage/objects?prefix=documents/&limit=50" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "objects": [
    {
      "object_key": "documents/invoice-001.pdf",
      "size": 524288,
      "last_modified": "2024-11-08T10:30:00"
    }
  ],
  "count": 1
}
```

### Search Objects

**POST** `/api/storage/search`

Full-text search (requires PostgreSQL).

**Request Body:**
```json
{
  "query": "invoice & finance",
  "prefix": "documents/",
  "storage_backend": "s3",
  "limit": 100,
  "offset": 0
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/storage/search" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query":"invoice & finance","limit":50}'
```

**Response:**
```json
{
  "results": [
    {
      "object_key": "documents/invoice-2024-001.pdf",
      "size": 524288,
      "rank": 0.8745,
      "metadata": {"owner": "ACME"}
    }
  ],
  "count": 1
}
```

### List Versions

**GET** `/api/storage/objects/{key:path}/versions`

List all versions of an object.

**Query Parameters:**
- `limit` (default: 100, max: 1000): Maximum versions

**Example:**
```bash
curl -X GET "http://localhost:8000/api/storage/objects/documents/test.pdf/versions" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
[
  {
    "version_id": "v2",
    "is_latest": true,
    "last_modified": "2024-11-08T11:00:00",
    "size": 524500,
    "etag": "new-etag",
    "created_by": "john@example.com",
    "comment": "Updated amounts",
    "tags": {"approved": "true"}
  },
  {
    "version_id": "v1",
    "is_latest": false,
    "last_modified": "2024-11-08T10:00:00",
    "size": 524288,
    "etag": "old-etag",
    "created_by": null,
    "comment": null,
    "tags": null
  }
]
```

### Rollback Version

**POST** `/api/storage/objects/{key:path}/rollback`

Rollback object to a previous version.

**Query Parameters:**
- `version_id` (required): Version to rollback to
- `comment` (optional): Rollback comment

**Example:**
```bash
curl -X POST "http://localhost:8000/api/storage/objects/documents/test.pdf/rollback?version_id=v1&comment=Reverting%20changes" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "status": "rolled_back",
  "object_key": "documents/test.pdf",
  "new_version": "v3",
  "comment": "Reverting changes"
}
```

### Register Webhook

**POST** `/api/webhooks`

Register integration webhook.

**Request Body:**
```json
{
  "name": "erp_sync",
  "url": "https://erp.example.com/webhook",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer token123"
  },
  "events": [
    "DOCUMENT_ARCHIVED",
    "DOCUMENT_UPDATED",
    "DOCUMENT_DELETED"
  ],
  "retry_count": 3,
  "timeout": 30
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/webhooks" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d @webhook.json
```

**Response:**
```json
{
  "status": "registered",
  "webhook": "erp_sync"
}
```

### List Webhooks

**GET** `/api/webhooks`

List all registered webhooks.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/webhooks" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "webhooks": [
    {
      "name": "erp_sync",
      "url": "https://erp.example.com/webhook",
      "events": ["DOCUMENT_ARCHIVED"]
    }
  ]
}
```

### Get Analytics

**GET** `/api/analytics`

Get storage analytics and statistics.

**Query Parameters:**
- `hours` (default: 24, max: 168): Time window for statistics

**Example:**
```bash
curl -X GET "http://localhost:8000/api/analytics?hours=24" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "total_objects": 1523,
  "total_size": 15234567890,
  "total_versions": 3045,
  "storage_backends": {
    "local": {
      "object_count": 1000,
      "total_size": 10000000000
    },
    "s3": {
      "object_count": 523,
      "total_size": 5234567890
    }
  },
  "recent_uploads": 45,
  "recent_downloads": 234,
  "recent_audits": 450,
  "hook_statistics": [
    {
      "hook_name": "erp_sync",
      "event_type": "DOCUMENT_ARCHIVED",
      "total_executions": 45,
      "successful": 44,
      "failed": 1,
      "avg_execution_time": 0.342
    }
  ]
}
```

### Query Audit Logs

**GET** `/api/audit`

Query access audit logs.

**Query Parameters:**
- `object_key` (optional): Filter by object key
- `user_id` (optional): Filter by user ID
- `action` (optional): Filter by action (UPLOAD, DOWNLOAD, DELETE, etc.)
- `hours` (default: 24, max: 168): Time window
- `limit` (default: 100, max: 1000): Maximum logs

**Example:**
```bash
curl -X GET "http://localhost:8000/api/audit?object_key=documents/test.pdf&hours=24&limit=50" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
[
  {
    "timestamp": "2024-11-08T10:30:00",
    "user_id": "user123",
    "username": "john@example.com",
    "action": "DOWNLOAD",
    "object_key": "documents/test.pdf",
    "version_id": "v1",
    "ip_address": "192.168.1.100",
    "success": true,
    "error_message": null
  }
]
```

## Python Client Examples

### Basic Upload/Download

```python
import requests

API_URL = "http://localhost:8000"
API_KEY = "your-api-key"
HEADERS = {"X-API-Key": API_KEY}

# Upload file
with open("document.pdf", "rb") as f:
    response = requests.post(
        f"{API_URL}/api/storage/objects",
        headers=HEADERS,
        params={
            "key": "documents/document.pdf",
            "metadata": '{"owner":"ACME","type":"Invoice"}'
        },
        files={"file": f}
    )
    print(response.json())

# Download file
response = requests.get(
    f"{API_URL}/api/storage/objects/documents/document.pdf",
    headers=HEADERS
)
with open("downloaded.pdf", "wb") as f:
    f.write(response.content)
```

### Search and Analytics

```python
# Search documents
response = requests.post(
    f"{API_URL}/api/storage/search",
    headers=HEADERS,
    json={"query": "invoice & finance", "limit": 50}
)
results = response.json()["results"]

# Get analytics
response = requests.get(
    f"{API_URL}/api/analytics",
    headers=HEADERS,
    params={"hours": 24}
)
analytics = response.json()
print(f"Total objects: {analytics['total_objects']}")
print(f"Recent uploads: {analytics['recent_uploads']}")
```

### Version Management

```python
# List versions
response = requests.get(
    f"{API_URL}/api/storage/objects/documents/document.pdf/versions",
    headers=HEADERS
)
versions = response.json()

# Rollback to previous version
response = requests.post(
    f"{API_URL}/api/storage/objects/documents/document.pdf/rollback",
    headers=HEADERS,
    params={
        "version_id": "v1",
        "comment": "Reverting to original"
    }
)
print(response.json())
```

### Webhook Management

```python
# Register webhook
webhook = {
    "name": "slack_notifier",
    "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "method": "POST",
    "events": ["DOCUMENT_ARCHIVED", "DOCUMENT_DELETED"],
    "retry_count": 3,
    "timeout": 30
}

response = requests.post(
    f"{API_URL}/api/webhooks",
    headers=HEADERS,
    json=webhook
)
print(response.json())

# List webhooks
response = requests.get(f"{API_URL}/api/webhooks", headers=HEADERS)
print(response.json())
```

## Configuration

### Environment Variables

```bash
# Storage Backend
export STORAGE_BACKEND=local  # or s3
export STORAGE_PATH=data/storage  # or bucket name

# S3 Configuration (if using S3)
export S3_ENDPOINT=http://localhost:9000
export S3_ACCESS_KEY=minioadmin
export S3_SECRET_KEY=minioadmin

# PostgreSQL Configuration
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=puda_storage
export POSTGRES_USER=puda
export POSTGRES_PASSWORD=puda

# API Configuration
export STORAGE_API_KEY=your-secret-key
```

### Python Configuration

```python
from src.storage import StorageAPI

api = StorageAPI(
    storage_backend="s3",
    storage_path="archive",
    enable_postgres=True,
    postgres_config={
        "host": "localhost",
        "port": 5432,
        "database": "puda_storage",
        "user": "puda",
        "password": "puda"
    },
    enable_webhooks=True,
    api_key="your-secret-key"
)

# Run server
api.run(host="0.0.0.0", port=8000)
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.storage.storage_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  storage-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - STORAGE_BACKEND=s3
      - S3_ENDPOINT=http://minio:9000
      - S3_ACCESS_KEY=minioadmin
      - S3_SECRET_KEY=minioadmin
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=puda_storage
      - POSTGRES_USER=puda
      - POSTGRES_PASSWORD=puda
      - STORAGE_API_KEY=your-secret-key
    depends_on:
      - postgres
      - minio
    volumes:
      - ./data:/app/data
```

## Security

### API Key Authentication

Enable API key authentication:

```python
api = StorageAPI(api_key="your-secret-key")
```

All requests must include the API key:

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/storage/info
```

### HTTPS/TLS

Run behind a reverse proxy (nginx, Caddy) for TLS:

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### CORS Configuration

CORS is enabled by default for all origins. Restrict in production:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

## Performance

### Production Deployment

```bash
# Multiple workers
uvicorn src.storage.storage_api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info

# With Gunicorn
gunicorn src.storage.storage_api:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
```

### Connection Pooling

PostgreSQL connection pooling is automatic (2-20 connections). Tune as needed:

```python
api = StorageAPI(
    postgres_config={
        "min_connections": 5,
        "max_connections": 50
    }
)
```

### Caching

Implement caching for metadata queries:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_metadata(key: str):
    return storage.get_metadata(key)
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics Endpoint (Custom)

```python
@app.get("/metrics")
async def metrics():
    return {
        "requests_total": request_counter,
        "requests_per_second": calculate_rps(),
        "storage_operations": storage_ops_counter
    }
```

### Logging

Configure logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Troubleshooting

### FastAPI Not Installed

```bash
pip install fastapi uvicorn python-multipart
```

### PostgreSQL Connection Failed

Check environment variables and PostgreSQL service:

```bash
docker ps | grep postgres
python setup_postgres.py
```

### S3 Connection Failed

Verify S3 credentials and endpoint:

```bash
export S3_ENDPOINT=http://localhost:9000
export S3_ACCESS_KEY=minioadmin
export S3_SECRET_KEY=minioadmin
```

### File Upload Issues

Ensure `python-multipart` is installed:

```bash
pip install python-multipart
```

## Next Steps

1. **Deploy API**: Start the FastAPI server
2. **Test Endpoints**: Use Swagger UI at `/docs`
3. **Integrate Webhooks**: Register webhooks for external systems
4. **Monitor Analytics**: Track usage with `/api/analytics`
5. **Set Up Authentication**: Configure API key authentication
6. **Enable HTTPS**: Deploy behind reverse proxy
7. **Scale**: Add workers for high-traffic scenarios

## Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Source Code**: `src/storage/storage_api.py`
