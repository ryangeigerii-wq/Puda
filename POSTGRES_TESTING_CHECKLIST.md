# PostgreSQL Integration - Testing Checklist

## Prerequisites

- [ ] Python 3.9+ installed
- [ ] Docker installed (for PostgreSQL and MinIO)
- [ ] Git repository cloned
- [ ] Virtual environment activated

## Installation Steps

### 1. Install Python Dependencies

```powershell
# Install PostgreSQL adapter
pip install psycopg2-binary

# Verify installation
python -c "import psycopg2; print('psycopg2 version:', psycopg2.__version__)"
```

- [ ] psycopg2-binary installed successfully
- [ ] No import errors

### 2. Start PostgreSQL with Docker

```powershell
# Start PostgreSQL and MinIO
docker-compose up -d puda-postgres puda-minio

# Wait for services to be healthy (30 seconds)
Start-Sleep -Seconds 30

# Verify services are running
docker ps
```

- [ ] puda-postgres container running
- [ ] puda-minio container running
- [ ] Both services healthy

### 3. Verify PostgreSQL Connection

```powershell
# Test connection with psql
docker exec -it puda-postgres psql -U puda -d puda_storage -c "SELECT version();"
```

- [ ] PostgreSQL responds with version info
- [ ] Database `puda_storage` exists
- [ ] User `puda` can connect

### 4. Run Setup Script

```powershell
# Run automated setup
python setup_postgres.py
```

Expected output:
```
✓ psycopg2 is installed
✓ Storage module imported successfully
✓ Connection successful
✓ Database schema initialized
✓ Object recorded with ID: 1
✓ Metadata retrieved
✓ Version recorded
✓ Found 1 version(s)
✓ Audit logged
✓ Found 1 audit log(s)
✓ Search returned X result(s)
✓ Statistics retrieved
✓ All basic operations passed
PostgreSQL Storage Database Setup Complete!
```

- [ ] All checks pass (✓)
- [ ] No errors reported
- [ ] Database tables created
- [ ] Basic operations work

## Functional Testing

### 5. Test Storage Integration

```powershell
# Run integration example
python storage_integration_example.py
```

Expected workflow:
1. Upload test document
2. Search documents (full-text)
3. List documents by prefix
4. View version history
5. Query audit trail
6. Download document
7. Display statistics

- [ ] Document uploaded successfully
- [ ] Search returns results
- [ ] Prefix listing works
- [ ] Version history available
- [ ] Audit logs recorded
- [ ] Download successful
- [ ] Statistics displayed

### 6. Test Storage CLI

```powershell
# Test local storage with PostgreSQL metadata
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:POSTGRES_DB="puda_storage"
$env:POSTGRES_USER="puda"
$env:POSTGRES_PASSWORD="puda"

# Upload file
python storage_cli.py --backend local --path data/storage put test.txt --file test.txt

# List files
python storage_cli.py --backend local --path data/storage list

# Get metadata
python storage_cli.py --backend local --path data/storage metadata test.txt

# Get version history
python storage_cli.py --backend local --path data/storage versions test.txt
```

- [ ] File upload works
- [ ] File listing works
- [ ] Metadata retrieval works
- [ ] Version history available

### 7. Test MinIO S3 Storage

```powershell
# Test S3-compatible storage
python storage_cli.py --backend s3 --bucket archive `
    --endpoint http://localhost:9000 `
    --access-key minioadmin --secret-key minioadmin `
    info

# Upload to S3
python storage_cli.py --backend s3 --bucket archive `
    --endpoint http://localhost:9000 `
    --access-key minioadmin --secret-key minioadmin `
    put test.txt --file test.txt

# List S3 objects
python storage_cli.py --backend s3 --bucket archive `
    --endpoint http://localhost:9000 `
    --access-key minioadmin --secret-key minioadmin `
    list
```

- [ ] MinIO info displayed
- [ ] File uploaded to S3
- [ ] Objects listed successfully

### 8. Test Database Operations

```powershell
# Test database directly with Python
python -c "
from src.storage import PostgreSQLStorageDB
db = PostgreSQLStorageDB()

# Test search
results = db.search_objects('test', limit=10)
print(f'Search found {len(results)} results')

# Test statistics
stats = db.get_statistics()
print(f'Total versions: {stats[\"total_versions\"]}')
print(f'Recent audits: {stats[\"recent_audits_24h\"]}')

# Test audit logs
logs = db.get_audit_logs(limit=10)
print(f'Found {len(logs)} audit logs')

db.close()
print('All database operations successful!')
"
```

- [ ] Search returns results
- [ ] Statistics available
- [ ] Audit logs accessible
- [ ] No errors

### 9. Test PostgreSQL Admin

```powershell
# Connect to database
docker exec -it puda-postgres psql -U puda -d puda_storage

# Run queries
\dt                                    # List tables
\d storage_objects                     # Describe table
SELECT COUNT(*) FROM storage_objects;  # Count objects
SELECT COUNT(*) FROM storage_audit;    # Count audits
\q                                     # Quit
```

- [ ] Tables exist (storage_objects, storage_versions, storage_audit, storage_hooks)
- [ ] Data inserted correctly
- [ ] Indexes created

### 10. Test MinIO Console

```powershell
# Open MinIO console in browser
Start-Process "http://localhost:9001"
```

Login credentials:
- Username: `minioadmin`
- Password: `minioadmin`

- [ ] MinIO console accessible
- [ ] Can login successfully
- [ ] Bucket `archive` exists (or can be created)
- [ ] Can browse objects

## Performance Testing

### 11. Test Concurrent Access

```powershell
# Run multiple instances simultaneously (3 terminals)
# Terminal 1
python storage_integration_example.py

# Terminal 2 (different session)
python storage_integration_example.py

# Terminal 3 (different session)
python storage_integration_example.py
```

- [ ] All instances complete successfully
- [ ] No connection errors
- [ ] Connection pooling works
- [ ] No deadlocks

### 12. Test Large Dataset

```powershell
# Create test script for bulk inserts
python -c "
from src.storage import PostgreSQLStorageDB
import time

db = PostgreSQLStorageDB()

start = time.time()
for i in range(1000):
    db.record_object(
        object_key=f'test/bulk/file_{i:04d}.txt',
        size=1024,
        content_type='text/plain',
        etag=f'etag_{i}',
        version_id=f'v{i}',
        storage_backend='local'
    )
    if (i + 1) % 100 == 0:
        print(f'Inserted {i + 1} objects...')

elapsed = time.time() - start
print(f'Inserted 1000 objects in {elapsed:.2f} seconds')
print(f'Rate: {1000/elapsed:.2f} objects/sec')

db.close()
"
```

- [ ] 1000+ objects inserted
- [ ] No timeout errors
- [ ] Acceptable performance (>10 objects/sec)

### 13. Test Full-Text Search Performance

```powershell
python -c "
from src.storage import PostgreSQLStorageDB
import time

db = PostgreSQLStorageDB()

queries = ['test', 'bulk', 'file', 'test & bulk', 'file | bulk']

for query in queries:
    start = time.time()
    results = db.search_objects(query, limit=100)
    elapsed = time.time() - start
    print(f'Query \"{query}\": {len(results)} results in {elapsed*1000:.2f}ms')

db.close()
"
```

- [ ] All searches complete quickly (<100ms)
- [ ] Results returned correctly
- [ ] Search ranking works

## Integration Testing

### 14. Test with Archive Manager

```python
# Test integration with existing archive system
from src.storage import PostgreSQLStorageDB, LocalStorageManager
from src.organization.archive import ArchiveManager
import json

# Initialize
db = PostgreSQLStorageDB()
storage = LocalStorageManager("data/storage")
archive = ArchiveManager("data/qc_results")

# Archive document to storage
def archive_to_storage(page_id):
    doc = archive.get_document(page_id)
    key = f"{doc['owner']}/{doc['year']}/{doc['doc_type']}/{page_id}.json"
    
    # Store in filesystem
    data = json.dumps(doc).encode('utf-8')
    storage.put_object(key, data)
    
    # Record metadata in PostgreSQL
    db.record_object(
        object_key=key,
        size=len(data),
        content_type="application/json",
        etag="computed-etag",
        version_id="v1",
        storage_backend="local",
        metadata={
            "owner": doc['owner'],
            "doc_type": doc['doc_type'],
            "year": doc['year']
        }
    )
    
    print(f"Archived {page_id} to {key}")

# Test if archive system exists
try:
    docs = archive.search_documents(limit=1)
    if docs:
        archive_to_storage(docs[0]['page_id'])
        print("✓ Integration with Archive Manager successful")
except Exception as e:
    print(f"⚠ Archive Manager not available: {e}")
```

- [ ] Archive integration works
- [ ] Metadata preserved
- [ ] Documents retrievable

## Cleanup and Verification

### 15. Verify Data Persistence

```powershell
# Stop containers
docker-compose down

# Start again
docker-compose up -d puda-postgres puda-minio

# Wait for startup
Start-Sleep -Seconds 30

# Verify data still exists
python -c "
from src.storage import PostgreSQLStorageDB
db = PostgreSQLStorageDB()
stats = db.get_statistics()
print(f'Objects after restart: {stats[\"objects\"]}')
print(f'Versions: {stats[\"total_versions\"]}')
db.close()
"
```

- [ ] Data persists across restarts
- [ ] Volumes working correctly

### 16. Test Backup and Restore

```powershell
# Create backup
docker exec puda-postgres pg_dump -U puda puda_storage > backup_test.sql

# Verify backup file
Get-Item backup_test.sql
```

- [ ] Backup file created
- [ ] Backup contains data

### 17. Cleanup Test Data (Optional)

```powershell
# Remove test data
python -c "
from src.storage import PostgreSQLStorageDB
db = PostgreSQLStorageDB()

# Clean up test objects
conn = db._get_connection()
try:
    with conn.cursor() as cur:
        cur.execute(\"DELETE FROM storage_objects WHERE object_key LIKE 'test/%'\")
        cur.execute(\"DELETE FROM storage_versions WHERE object_key LIKE 'test/%'\")
        cur.execute(\"DELETE FROM storage_audit WHERE object_key LIKE 'test/%'\")
        conn.commit()
        print('Test data cleaned up')
finally:
    db._put_connection(conn)

db.close()
"
```

- [ ] Test data removed
- [ ] No errors during cleanup

## Final Verification

### 18. Documentation Check

- [ ] `POSTGRES_SETUP.md` exists and is complete
- [ ] `POSTGRES_INTEGRATION_SUMMARY.md` exists
- [ ] `storage_integration_example.py` runs successfully
- [ ] `setup_postgres.py` passes all tests
- [ ] `QUICKREF.md` updated with PostgreSQL commands
- [ ] `docker-compose.yml` includes PostgreSQL and MinIO services

### 19. Code Quality Check

```powershell
# Check for import errors
python -c "from src.storage import PostgreSQLStorageDB; print('✓ Import successful')"

# Check requirements
pip list | Select-String "psycopg2-binary"
pip list | Select-String "boto3"
```

- [ ] All imports work
- [ ] Dependencies installed
- [ ] No deprecation warnings

### 20. Production Readiness

- [ ] Connection pooling configured (2-20 connections)
- [ ] Indexes created on all tables
- [ ] Full-text search trigger active
- [ ] Audit logging functional
- [ ] Statistics queries optimized
- [ ] Error handling implemented
- [ ] Documentation complete

## Test Results Summary

### Passed: ____ / 20

### Notes:
- Any issues encountered:
  
- Performance observations:
  
- Recommendations:
  

## Next Steps

After passing all tests:

1. **Production Configuration**:
   - Update connection pool size based on expected load
   - Configure backup schedule
   - Set up monitoring (pg_stat_monitor, Prometheus)
   - Enable SSL/TLS for production

2. **Integration**:
   - Integrate with Dashboard API
   - Connect to Archive Manager
   - Set up webhook notifications
   - Configure audit retention policies

3. **Scaling**:
   - Set up read replicas if needed
   - Configure connection pooler (PgBouncer)
   - Implement table partitioning for large datasets
   - Set up streaming replication for HA

4. **Monitoring**:
   - Set up Grafana dashboards
   - Configure alerting
   - Monitor query performance
   - Track storage growth

## Resources

- **Documentation**: `POSTGRES_SETUP.md`
- **Examples**: `storage_integration_example.py`
- **Setup**: `setup_postgres.py`
- **Summary**: `POSTGRES_INTEGRATION_SUMMARY.md`
- **Quick Reference**: `QUICKREF.md`
- **Docker**: `docker-compose.yml`

---

**Testing Date**: _______________
**Tested By**: _______________
**Environment**: _______________
**Result**: PASS / FAIL
