# PostgreSQL Storage Database Setup

Complete guide for setting up PostgreSQL as the metadata and audit log database for the storage layer.

## Overview

PostgreSQL provides enterprise-grade features for storage metadata:

- **Scalability**: Handle millions of documents with efficient indexing
- **Concurrency**: Connection pooling for multi-user access
- **Full-Text Search**: Fast document search with tsvector
- **JSONB Support**: Flexible metadata storage
- **Replication**: High availability with streaming replication
- **Partitioning**: Time-based partitioning for audit logs
- **ACID Compliance**: Strong data integrity guarantees

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                Storage Layer                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐      ┌──────────────┐           │
│  │ S3 Storage   │      │ Local Storage│           │
│  │  (Objects)   │      │  (Objects)   │           │
│  └──────┬───────┘      └──────┬───────┘           │
│         │                     │                    │
│         └─────────┬───────────┘                    │
│                   │                                │
│         ┌─────────▼─────────┐                      │
│         │ PostgreSQL DB     │                      │
│         ├───────────────────┤                      │
│         │ • Object Metadata │                      │
│         │ • Version History │                      │
│         │ • Audit Logs      │                      │
│         │ • Hook Execution  │                      │
│         │ • Full-Text Index │                      │
│         └───────────────────┘                      │
└─────────────────────────────────────────────────────┘
```

## Installation

### Option 1: Docker PostgreSQL

```bash
# Pull PostgreSQL image
docker pull postgres:16

# Run PostgreSQL container
docker run -d \
  --name puda-postgres \
  -e POSTGRES_DB=puda_storage \
  -e POSTGRES_USER=puda \
  -e POSTGRES_PASSWORD=puda \
  -p 5432:5432 \
  -v puda-postgres-data:/var/lib/postgresql/data \
  postgres:16

# Verify running
docker ps | grep puda-postgres
```

### Option 2: Local PostgreSQL Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Windows:**
Download and install from https://www.postgresql.org/download/windows/

### Create Database and User

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE puda_storage;
CREATE USER puda WITH PASSWORD 'puda';
GRANT ALL PRIVILEGES ON DATABASE puda_storage TO puda;

# Grant schema privileges
\c puda_storage
GRANT ALL ON SCHEMA public TO puda;
GRANT ALL ON ALL TABLES IN SCHEMA public TO puda;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO puda;

# Exit
\q
```

### Install Python Dependencies

```bash
pip install psycopg2-binary
```

## Database Schema

The system automatically creates these tables:

### storage_objects
Stores current object metadata with full-text search.

```sql
CREATE TABLE storage_objects (
    id SERIAL PRIMARY KEY,
    object_key TEXT NOT NULL UNIQUE,
    size BIGINT NOT NULL,
    content_type TEXT NOT NULL,
    etag TEXT NOT NULL,
    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version_id TEXT,
    storage_backend TEXT NOT NULL,
    storage_class TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    search_vector tsvector
);

-- Indexes for performance
CREATE INDEX idx_storage_objects_key ON storage_objects(object_key);
CREATE INDEX idx_storage_objects_backend ON storage_objects(storage_backend);
CREATE INDEX idx_storage_objects_modified ON storage_objects(last_modified DESC);
CREATE INDEX idx_storage_objects_metadata ON storage_objects USING gin(metadata);
CREATE INDEX idx_storage_objects_search ON storage_objects USING gin(search_vector);
```

### storage_versions
Version history with tagging and comments.

```sql
CREATE TABLE storage_versions (
    id SERIAL PRIMARY KEY,
    object_key TEXT NOT NULL,
    version_id TEXT NOT NULL,
    size BIGINT NOT NULL,
    etag TEXT NOT NULL,
    last_modified TIMESTAMP NOT NULL,
    is_latest BOOLEAN NOT NULL DEFAULT FALSE,
    created_by TEXT,
    comment TEXT,
    tags JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(object_key, version_id)
);
```

### storage_audit
Access audit trail with user tracking.

```sql
CREATE TABLE storage_audit (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    username TEXT,
    action TEXT NOT NULL,
    object_key TEXT,
    version_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    metadata JSONB
);
```

### storage_hooks
Integration hook execution logs.

```sql
CREATE TABLE storage_hooks (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    hook_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    object_key TEXT,
    execution_time FLOAT,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    response JSONB,
    payload JSONB
);
```

## Configuration

### Environment Variables

```bash
# PostgreSQL connection
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=puda_storage
export POSTGRES_USER=puda
export POSTGRES_PASSWORD=puda

# Connection pool
export POSTGRES_MIN_CONN=2
export POSTGRES_MAX_CONN=20
```

### Python Configuration

```python
from src.storage import PostgreSQLStorageDB

# Basic connection
db = PostgreSQLStorageDB(
    host="localhost",
    port=5432,
    database="puda_storage",
    user="puda",
    password="puda"
)

# With connection pool tuning
db = PostgreSQLStorageDB(
    host="localhost",
    port=5432,
    database="puda_storage",
    user="puda",
    password="puda",
    min_connections=5,
    max_connections=50
)
```

## Usage Examples

### Record Object Metadata

```python
from src.storage import PostgreSQLStorageDB

db = PostgreSQLStorageDB()

# Record object
object_id = db.record_object(
    object_key="documents/invoice-2024-001.pdf",
    size=524288,
    content_type="application/pdf",
    etag="d8e8fca2dc0f896fd7cb4cb0031ba249",
    version_id="v1",
    storage_backend="s3",
    storage_class="STANDARD",
    metadata={
        "owner": "ACME Corp",
        "department": "Finance",
        "doc_type": "Invoice"
    }
)

print(f"Object recorded with ID: {object_id}")
```

### Query Object Metadata

```python
# Get single object
metadata = db.get_object_metadata("documents/invoice-2024-001.pdf")
print(f"Object size: {metadata['size']} bytes")
print(f"Content type: {metadata['content_type']}")
print(f"Custom metadata: {metadata['metadata']}")

# List objects with prefix
objects = db.list_objects(prefix="documents/", limit=100)
for obj in objects:
    print(f"{obj['object_key']}: {obj['size']} bytes")

# List objects by backend
s3_objects = db.list_objects(storage_backend="s3", limit=1000)
print(f"Found {len(s3_objects)} S3 objects")
```

### Full-Text Search

```python
# Search across object keys, content types, and metadata
results = db.search_objects(
    search_query="invoice & finance",
    limit=50
)

for result in results:
    print(f"Rank: {result['rank']:.4f}")
    print(f"Key: {result['object_key']}")
    print(f"Metadata: {result['metadata']}")
    print("---")
```

### Version Management

```python
# Record new version
db.record_version(
    object_key="documents/invoice-2024-001.pdf",
    version_id="v2",
    size=524500,
    etag="new-etag-here",
    is_latest=True,
    created_by="john@example.com",
    comment="Updated with corrected amounts",
    tags={"reviewed": "true", "approved": "true"}
)

# List all versions
versions = db.list_versions("documents/invoice-2024-001.pdf")
for ver in versions:
    print(f"Version: {ver['version_id']}")
    print(f"Created: {ver['last_modified']}")
    print(f"Latest: {ver['is_latest']}")
    print(f"Comment: {ver['comment']}")
    print(f"Tags: {ver['tags']}")
    print("---")
```

### Audit Logging

```python
# Log access
db.log_audit(
    action="DOWNLOAD",
    object_key="documents/invoice-2024-001.pdf",
    user_id="user123",
    username="john@example.com",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0...",
    success=True
)

# Query audit logs
logs = db.get_audit_logs(
    object_key="documents/invoice-2024-001.pdf",
    limit=100
)

for log in logs:
    print(f"{log['timestamp']}: {log['username']} - {log['action']}")

# Get user activity
user_logs = db.get_audit_logs(
    user_id="user123",
    start_date=datetime.now() - timedelta(days=7),
    limit=1000
)

print(f"User performed {len(user_logs)} actions in last 7 days")
```

### Hook Execution Tracking

```python
# Log hook execution
db.log_hook_execution(
    hook_name="erp_sync",
    event_type="DOCUMENT_ARCHIVED",
    object_key="documents/invoice-2024-001.pdf",
    execution_time=0.342,
    success=True,
    response={"status": "synced", "erp_id": "INV-2024-001"}
)

# Get hook statistics
stats = db.get_hook_statistics(hours=24)
for stat in stats:
    print(f"Hook: {stat['hook_name']}")
    print(f"Event: {stat['event_type']}")
    print(f"Total: {stat['total_executions']}")
    print(f"Success: {stat['successful']}")
    print(f"Failed: {stat['failed']}")
    print(f"Avg Time: {stat['avg_execution_time']:.3f}s")
    print("---")
```

### Statistics and Monitoring

```python
# Get overall statistics
stats = db.get_statistics()

print("Storage Statistics:")
for backend_stat in stats['objects']:
    total, size, backend, count = backend_stat
    print(f"  {backend}: {total} objects, {size/1024/1024:.2f} MB")

print(f"\nTotal versions: {stats['total_versions']}")
print(f"Audits (24h): {stats['recent_audits_24h']}")
print(f"Hooks (24h): {stats['recent_hooks_24h']}")
```

### Cleanup Operations

```python
# Remove old audit logs (older than 1 year)
deleted = db.cleanup_old_audits(days=365)
print(f"Deleted {deleted} old audit records")

# Delete object metadata
db.delete_object("documents/old-invoice.pdf")
```

## Integration with Storage Backends

### With S3 Storage

```python
from src.storage import S3StorageManager, PostgreSQLStorageDB

# Initialize both
s3 = S3StorageManager(bucket_name="archive", enable_versioning=True)
db = PostgreSQLStorageDB()

# Upload and record
def upload_with_metadata(key, data, metadata=None):
    # Upload to S3
    result = s3.put_object(key, data, metadata=metadata)
    
    # Record in PostgreSQL
    db.record_object(
        object_key=key,
        size=len(data),
        content_type=result.get('ContentType', 'application/octet-stream'),
        etag=result['ETag'].strip('"'),
        version_id=result.get('VersionId'),
        storage_backend="s3",
        metadata=metadata
    )
    
    # Log audit
    db.log_audit(
        action="UPLOAD",
        object_key=key,
        success=True
    )
    
    return result

# Use it
upload_with_metadata(
    key="documents/report.pdf",
    data=b"PDF content here...",
    metadata={"owner": "ACME", "type": "Report"}
)
```

### With Local Storage

```python
from src.storage import LocalStorageManager, PostgreSQLStorageDB

local = LocalStorageManager("data/storage", enable_versioning=True)
db = PostgreSQLStorageDB()

# Upload and record
result = local.put_object("documents/file.txt", b"content", metadata={"type": "text"})

db.record_object(
    object_key="documents/file.txt",
    size=len(b"content"),
    content_type="text/plain",
    etag=result.etag,
    version_id=result.version_id,
    storage_backend="local",
    metadata={"type": "text"}
)
```

## Performance Optimization

### Connection Pool Tuning

```python
# For high-concurrency workloads
db = PostgreSQLStorageDB(
    min_connections=10,
    max_connections=100  # Adjust based on server capacity
)
```

### Batch Operations

```python
# Use transactions for bulk inserts
conn = db._get_connection()
try:
    with conn.cursor() as cur:
        for obj in objects_to_insert:
            cur.execute("""
                INSERT INTO storage_objects (object_key, size, ...) 
                VALUES (%s, %s, ...)
            """, (obj['key'], obj['size'], ...))
    conn.commit()
finally:
    db._put_connection(conn)
```

### Indexing Strategy

```sql
-- Add custom indexes for specific query patterns
CREATE INDEX idx_custom_owner ON storage_objects ((metadata->>'owner'));
CREATE INDEX idx_custom_type ON storage_objects ((metadata->>'doc_type'));

-- Partial indexes for frequently queried subsets
CREATE INDEX idx_recent_objects ON storage_objects(last_modified DESC) 
    WHERE last_modified > CURRENT_DATE - INTERVAL '30 days';
```

## Monitoring and Maintenance

### Database Size Monitoring

```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('puda_storage'));

-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Query Performance

```sql
-- Enable query statistics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### Vacuum and Analyze

```sql
-- Regular maintenance
VACUUM ANALYZE storage_objects;
VACUUM ANALYZE storage_versions;
VACUUM ANALYZE storage_audit;

-- Auto-vacuum configuration (postgresql.conf)
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min
```

## High Availability

### Streaming Replication

**Primary Server (postgresql.conf):**
```ini
wal_level = replica
max_wal_senders = 3
wal_keep_size = 64MB
```

**Primary Server (pg_hba.conf):**
```
host replication puda 192.168.1.0/24 md5
```

**Standby Server:**
```bash
# Create standby from primary backup
pg_basebackup -h primary-host -D /var/lib/postgresql/data -U puda -v -P

# standby.signal file
touch /var/lib/postgresql/data/standby.signal

# postgresql.auto.conf
primary_conninfo = 'host=primary-host port=5432 user=puda password=puda'
```

### Connection Failover

```python
# Primary and standby configuration
from src.storage import PostgreSQLStorageDB

try:
    db = PostgreSQLStorageDB(host="primary-host")
except Exception:
    # Failover to standby
    db = PostgreSQLStorageDB(host="standby-host")
```

## Backup and Recovery

### Automated Backups

```bash
#!/bin/bash
# backup_postgres.sh

BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Full backup
pg_dump -h localhost -U puda puda_storage \
    > "$BACKUP_DIR/puda_storage_$TIMESTAMP.sql"

# Compress
gzip "$BACKUP_DIR/puda_storage_$TIMESTAMP.sql"

# Remove old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

### Restore from Backup

```bash
# Restore database
gunzip -c /backups/postgres/puda_storage_20241108.sql.gz | \
    psql -h localhost -U puda puda_storage
```

## Security Best Practices

### SSL/TLS Connection

```python
db = PostgreSQLStorageDB(
    host="postgres.example.com",
    sslmode="require",
    sslrootcert="/path/to/ca.crt"
)
```

### Row-Level Security

```sql
-- Enable RLS
ALTER TABLE storage_objects ENABLE ROW LEVEL SECURITY;

-- Policy: users can only see their own documents
CREATE POLICY user_objects ON storage_objects
    FOR SELECT
    USING (metadata->>'owner' = current_user);
```

### Audit Logging

```sql
-- Enable pgaudit extension
CREATE EXTENSION pgaudit;

-- Configure auditing (postgresql.conf)
pgaudit.log = 'all'
pgaudit.log_catalog = off
```

## Troubleshooting

### Connection Issues

```python
# Test connection
from src.storage import PostgreSQLStorageDB

try:
    db = PostgreSQLStorageDB(host="localhost")
    print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Check PostgreSQL Logs

```bash
# Ubuntu/Debian
sudo tail -f /var/log/postgresql/postgresql-16-main.log

# Docker
docker logs puda-postgres -f
```

### Common Errors

**"FATAL: database does not exist"**
```bash
createdb -U postgres puda_storage
```

**"FATAL: role does not exist"**
```bash
createuser -U postgres puda
```

**"connection refused"**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check pg_hba.conf allows connections
sudo vim /etc/postgresql/16/main/pg_hba.conf
```

## Migration from SQLite

```python
# Export from SQLite
import sqlite3
conn = sqlite3.connect("storage.db")
cursor = conn.execute("SELECT * FROM storage_objects")
objects = cursor.fetchall()

# Import to PostgreSQL
from src.storage import PostgreSQLStorageDB
db = PostgreSQLStorageDB()

for obj in objects:
    db.record_object(
        object_key=obj[1],
        size=obj[2],
        # ... other fields
    )
```

## Next Steps

1. **Install PostgreSQL**: Choose Docker or native installation
2. **Create Database**: Set up `puda_storage` database and user
3. **Install psycopg2**: `pip install psycopg2-binary`
4. **Test Connection**: Run example code to verify setup
5. **Integrate**: Use PostgreSQLStorageDB with storage backends
6. **Configure Backups**: Set up automated backup script
7. **Monitor**: Use pg_stat_statements and custom dashboards
8. **Scale**: Add read replicas as needed

For production deployments, consider:
- Connection pooling (PgBouncer)
- Monitoring (pg_stat_monitor, Prometheus)
- High availability (Patroni, repmgr)
- Backup verification and disaster recovery testing
