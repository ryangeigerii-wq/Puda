# Storage & Integration Layer

Complete persistent archive storage with versioning, PostgreSQL metadata, and external system integration.

## Overview

The Storage & Integration Layer provides:
- **S3-Compatible Storage**: AWS S3, MinIO, Wasabi, Backblaze B2, NAS
- **Local Filesystem Storage**: With built-in versioning
- **PostgreSQL Database**: Metadata indexing, audit logs, full-text search
- **Version Management**: Rollback, comparison, tagging, history
- **Integration Hooks**: Webhooks, callbacks, file logging for external systems
- **Unified Interface**: Abstract storage operations across all backends

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Storage & Integration Layer                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │          StorageInterface (Abstract)               │ │
│  │  put_object, get_object, delete_object,            │ │
│  │  list_objects, get_metadata, list_versions,        │ │
│  │  copy_object, exists, get_url                      │ │
│  └────────────────────────────────────────────────────┘ │
│                         │                                │
│           ┌─────────────┴──────────────┐                 │
│           │                            │                 │
│  ┌────────▼────────┐         ┌────────▼────────┐        │
│  │ S3StorageManager│         │LocalStorageManager│       │
│  │                 │         │                  │        │
│  │ • AWS S3        │         │ • Filesystem     │        │
│  │ • MinIO         │         │ • Versioning     │        │
│  │ • Wasabi        │         │ • Checksums      │        │
│  │ • Backblaze B2  │         │ • Deduplication  │        │
│  │ • SSE encryption│         │ • NAS support    │        │
│  │ • Versioning    │         │ • JSON metadata  │        │
│  │ • Presigned URLs│         │ • file:// URLs   │        │
│  └────────┬────────┘         └────────┬─────────┘        │
│           │                           │                  │
│           └─────────────┬─────────────┘                  │
│                         │                                │
│                ┌────────▼────────┐                        │
│                │ PostgreSQL DB   │                        │
│                │                 │                        │
│                │ • Object index  │                        │
│                │ • Version hist  │                        │
│                │ • Audit logs    │                        │
│                │ • Hook tracking │                        │
│                │ • Full-text FTS │                        │
│                └─────────────────┘                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │            VersionManager                          │ │
│  │  • Version history tracking                        │ │
│  │  • Rollback capabilities                           │ │
│  │  • Version comparison/diff                         │ │
│  │  • Tagging and comments                            │ │
│  │  • Retention policies                              │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │        IntegrationHookManager                      │ │
│  │  • Webhook integration (HTTP POST/PUT)             │ │
│  │  • Python callbacks                                │ │
│  │  • File logging (JSON/text)                        │ │
│  │  • Async execution with queue                      │ │
│  │  • Event filtering                                 │ │
│  │  • Retry logic                                     │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘

External Systems:
  • SFTP servers
  • Document management systems (SharePoint, Alfresco)
  • ERP systems (SAP, Oracle)
  • Backup systems
  • Monitoring/alerting (Slack, PagerDuty)
```

---

## Features

### S3-Compatible Storage

**Supported Services:**
- AWS S3 (production, all regions)
- MinIO (self-hosted, S3-compatible)
- Wasabi (cost-effective cloud storage)
- Backblaze B2 (affordable backup)
- Any S3-compatible API

**Capabilities:**
- ✅ Versioning with `VersionId`
- ✅ Server-side encryption (SSE-S3, SSE-KMS)
- ✅ Multipart uploads (automatic for large files)
- ✅ Presigned URLs (temporary access)
- ✅ Storage classes (STANDARD, INTELLIGENT_TIERING, GLACIER)
- ✅ Cross-region replication ready
- ✅ Lifecycle policies compatible
- ✅ Bucket policies and IAM

### Local Filesystem Storage

**Directory Structure:**
```
base_path/
  objects/
    invoices/2024/batch_001/page_001.pdf    # Current versions
    receipts/2024/batch_002/page_001.pdf
  .versions/
    invoices/2024/batch_001/page_001.pdf/
      20241108120000000001                   # Historical versions
      20241108130000000002
  .metadata/
    invoices_2024_batch_001_page_001.pdf.json  # Object metadata
```

**Capabilities:**
- ✅ Versioning with automatic cleanup (configurable max versions)
- ✅ Content-addressable storage (MD5 ETags)
- ✅ JSON metadata sidecars
- ✅ File integrity verification
- ✅ Symlink support for NAS mounting
- ✅ Deduplication-ready

### Version Management

**Operations:**
- `list_versions(key)`: Get all versions with metadata
- `get_version(key, version_id)`: Retrieve specific version
- `rollback(key, version_id)`: Restore previous version
- `compare_versions(key, v1, v2)`: Diff two versions
- `tag_version(key, version_id, tags)`: Add tags
- `add_comment(key, version_id, comment)`: Annotate version
- `prune_versions(key, keep_count)`: Clean up old versions
- `get_version_history(key)`: Full history with changes

**Version Metadata:**
```python
{
    "version_id": "20241108120000000001",
    "key": "invoices/2024/batch_001/page_001.pdf",
    "size": 524288,
    "etag": "a7c8e5b2d9f4a1c3e6b8d2f5a9c1e4b7",
    "last_modified": "2024-11-08T12:00:00",
    "is_latest": False,
    "created_by": "operator1",
    "comment": "Initial upload after QC approval",
    "tags": {
        "qc_status": "approved",
        "batch_id": "batch_001",
        "doc_type": "invoice"
    }
}
```

### Integration Hooks

**Hook Types:**

1. **WebhookHook**: HTTP POST/PUT to external endpoints
2. **CallbackHook**: Python function execution
3. **FileLogHook**: JSON or text log files

**Events:**
```python
HookEvent.DOCUMENT_ARCHIVED       # New document stored
HookEvent.DOCUMENT_UPDATED        # Document modified
HookEvent.DOCUMENT_DELETED        # Document removed
HookEvent.DOCUMENT_RETRIEVED      # Document accessed
HookEvent.BATCH_COMPLETED         # Batch processing done
HookEvent.QC_APPROVED             # QC approval
HookEvent.QC_REJECTED             # QC rejection
HookEvent.VERSION_CREATED         # New version
HookEvent.VERSION_ROLLED_BACK     # Rollback performed
```

**Execution:**
- Asynchronous with queue (default)
- Synchronous option available
- Retry logic with exponential backoff
- Error handling and logging
- Event filtering per hook

---

## Installation

```bash
# Install dependencies
pip install boto3  # For S3 support
pip install requests  # For webhooks

# Or use requirements.txt
pip install -r requirements.txt
```

---

## Configuration

### S3 Storage (AWS)

```python
from src.storage import S3StorageManager

storage = S3StorageManager(
    bucket_name="my-archive-bucket",
    region="us-east-1",
    enable_versioning=True,
    storage_class="INTELLIGENT_TIERING",
    encryption="AES256"
)
```

**Environment Variables:**
```bash
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="us-east-1"
```

### S3 Storage (MinIO Self-Hosted)

```python
storage = S3StorageManager(
    bucket_name="archive",
    region="us-east-1",
    endpoint_url="http://localhost:9000",  # MinIO endpoint
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    enable_versioning=True
)
```

**Run MinIO Locally:**
```bash
# Docker
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Access console: http://localhost:9001
```

### Local Storage

```python
from src.storage import LocalStorageManager

storage = LocalStorageManager(
    base_path="data/storage",
    enable_versioning=True,
    max_versions=10  # Keep last 10 versions
)
```

### Version Manager

```python
from src.storage import VersionManager

version_manager = VersionManager(
    storage=storage,
    version_metadata_dir=Path("data/.version_metadata")
)
```

### Integration Hooks

```python
from src.storage import (
    IntegrationHookManager,
    WebhookHook,
    CallbackHook,
    FileLogHook,
    HookEvent
)

# Create hook manager
hook_manager = IntegrationHookManager(async_execution=True)

# Add webhook for document archival
webhook = WebhookHook(
    name="erp_sync",
    url="https://erp.example.com/api/document-webhook",
    method="POST",
    headers={"Authorization": "Bearer secret-token"},
    timeout=30,
    retry_count=3
)
hook_manager.register_hook(webhook)

# Add file logging
file_log = FileLogHook(
    name="audit_log",
    log_file=Path("data/storage_events.jsonl"),
    format="json"
)
hook_manager.register_hook(file_log)

# Add Python callback
def notify_admin(payload):
    print(f"Event: {payload.event.value}")
    print(f"Data: {payload.data}")
    # Send email, Slack message, etc.

callback = CallbackHook(
    name="admin_notify",
    callback=notify_admin,
    events=[HookEvent.DOCUMENT_ARCHIVED, HookEvent.BATCH_COMPLETED]
)
hook_manager.register_hook(callback)
```

---

## CLI Usage

### Basic Operations

```bash
# Show storage information
python storage_cli.py --backend local --path data/storage info

# Upload file
python storage_cli.py --backend local put invoices/2024/inv_001.pdf --file invoice.pdf

# Upload with metadata
python storage_cli.py put documents/report.pdf \
  --file report.pdf \
  --content-type application/pdf \
  --metadata department=finance year=2024 confidential=true

# Download file
python storage_cli.py get invoices/2024/inv_001.pdf --output invoice.pdf

# List objects
python storage_cli.py list --prefix invoices/2024

# Get metadata
python storage_cli.py metadata invoices/2024/inv_001.pdf

# Delete object
python storage_cli.py delete invoices/2024/inv_001.pdf
```

### Version Management

```bash
# List all versions
python storage_cli.py versions invoices/2024/inv_001.pdf

# Get specific version
python storage_cli.py get invoices/2024/inv_001.pdf \
  --version 20241108120000000001 \
  --output invoice_v1.pdf

# Rollback to previous version
python storage_cli.py rollback invoices/2024/inv_001.pdf \
  20241108120000000001 \
  --comment "Reverting incorrect changes" \
  --user operator1

# Compare two versions
python storage_cli.py compare invoices/2024/inv_001.pdf \
  20241108120000000001 \
  20241108130000000002

# Show version history
python storage_cli.py history invoices/2024/inv_001.pdf --limit 10
```

### S3 Operations

```bash
# Using AWS S3
python storage_cli.py \
  --backend s3 \
  --bucket my-archive-bucket \
  --region us-east-1 \
  list --prefix invoices/2024

# Using MinIO
python storage_cli.py \
  --backend s3 \
  --bucket archive \
  --endpoint http://localhost:9000 \
  --access-key minioadmin \
  --secret-key minioadmin \
  put documents/report.pdf --file report.pdf

# Using Wasabi
python storage_cli.py \
  --backend s3 \
  --bucket my-bucket \
  --endpoint https://s3.wasabisys.com \
  --region us-east-1 \
  info
```

### Webhook Management

```bash
# Add webhook
python storage_cli.py webhook-add erp_sync \
  https://erp.example.com/api/webhook \
  --method POST \
  --events document.archived batch.completed

# List webhooks
python storage_cli.py webhook-list
```

---

## Python API Examples

### Basic Storage Operations

```python
from src.storage import LocalStorageManager
from pathlib import Path

# Initialize storage
storage = LocalStorageManager("data/storage", enable_versioning=True)

# Upload document
with open("invoice.pdf", "rb") as f:
    data = f.read()

metadata = storage.put_object(
    key="invoices/2024/batch_001/page_001.pdf",
    data=data,
    content_type="application/pdf",
    metadata={"batch_id": "batch_001", "qc_status": "approved"}
)

print(f"Uploaded: {metadata.key}")
print(f"Version: {metadata.version_id}")
print(f"Size: {metadata.size} bytes")

# Download document
data = storage.get_object("invoices/2024/batch_001/page_001.pdf")
Path("downloaded.pdf").write_bytes(data)

# List documents
objects = storage.list_objects(prefix="invoices/2024", max_keys=100)
for obj in objects:
    print(f"{obj.key} ({obj.size} bytes) - {obj.last_modified}")

# Check if exists
if storage.exists("invoices/2024/batch_001/page_001.pdf"):
    print("Document exists")

# Copy document
storage.copy_object(
    source_key="invoices/2024/batch_001/page_001.pdf",
    dest_key="backup/invoices/2024/batch_001/page_001.pdf"
)

# Delete document
storage.delete_object("backup/invoices/2024/batch_001/page_001.pdf")
```

### Version Management

```python
from src.storage import LocalStorageManager, VersionManager

storage = LocalStorageManager("data/storage")
version_manager = VersionManager(storage)

# List versions
versions = version_manager.list_versions("invoices/2024/batch_001/page_001.pdf")
for v in versions:
    print(f"Version {v.version_id}: {v.size} bytes, "
          f"modified {v.last_modified}, latest={v.is_latest}")
    if v.comment:
        print(f"  Comment: {v.comment}")

# Get specific version
old_data = version_manager.get_version(
    "invoices/2024/batch_001/page_001.pdf",
    "20241108120000000001"
)

# Rollback to previous version
result = version_manager.rollback(
    key="invoices/2024/batch_001/page_001.pdf",
    version_id="20241108120000000001",
    comment="Reverting accidental changes",
    created_by="admin"
)
print(f"Rolled back to version {result.version_id}")

# Compare versions
comparison = version_manager.compare_versions(
    key="invoices/2024/batch_001/page_001.pdf",
    version1="20241108120000000001",
    version2="20241108130000000002"
)
print(f"Size change: {comparison['differences']['size_diff']} bytes")
print(f"Content changed: {comparison['differences']['content_changed']}")

# Tag version
version_manager.tag_version(
    key="invoices/2024/batch_001/page_001.pdf",
    version_id="20241108120000000001",
    tags={"milestone": "production_release", "tested": "true"}
)

# Add comment
version_manager.add_comment(
    key="invoices/2024/batch_001/page_001.pdf",
    version_id="20241108120000000001",
    comment="This version passed QC audit",
    created_by="qc_supervisor"
)

# Get version history
history = version_manager.get_version_history(
    "invoices/2024/batch_001/page_001.pdf",
    limit=10
)
for entry in history:
    print(f"{entry['timestamp']}: {entry['version_id']}")
    if 'changes' in entry:
        print(f"  Changed: {entry['changes']['size_diff']:+d} bytes")

# Prune old versions (keep last 5)
deleted_count = version_manager.prune_versions(
    key="invoices/2024/batch_001/page_001.pdf",
    keep_count=5,
    keep_tagged=True  # Don't delete tagged versions
)
print(f"Deleted {deleted_count} old versions")
```

### Integration Hooks

```python
from src.storage import (
    IntegrationHookManager,
    WebhookHook,
    CallbackHook,
    FileLogHook,
    HookEvent
)
from pathlib import Path

# Create hook manager
hook_manager = IntegrationHookManager(
    async_execution=True,
    max_queue_size=1000
)

# Register webhook for ERP integration
erp_webhook = WebhookHook(
    name="erp_sync",
    url="https://erp.example.com/api/document-webhook",
    method="POST",
    headers={
        "Authorization": "Bearer secret-token",
        "Content-Type": "application/json"
    },
    timeout=30,
    retry_count=3
)
hook_manager.register_hook(erp_webhook)

# Register audit log
audit_log = FileLogHook(
    name="audit_trail",
    log_file=Path("data/storage_audit.jsonl"),
    format="json"
)
hook_manager.register_hook(audit_log)

# Register Python callback
def send_slack_notification(payload):
    import requests
    slack_webhook = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    message = {
        "text": f"Document event: {payload.event.value}",
        "attachments": [{
            "fields": [
                {"title": "Key", "value": payload.data.get('key', 'N/A')},
                {"title": "Size", "value": str(payload.data.get('size', 0))},
                {"title": "Timestamp", "value": payload.timestamp.isoformat()}
            ]
        }]
    }
    requests.post(slack_webhook, json=message)

slack_hook = CallbackHook(
    name="slack_notify",
    callback=send_slack_notification,
    events=[HookEvent.DOCUMENT_ARCHIVED, HookEvent.BATCH_COMPLETED]
)
hook_manager.register_hook(slack_hook)

# Fire event
hook_manager.fire_event(
    event=HookEvent.DOCUMENT_ARCHIVED,
    data={
        "key": "invoices/2024/batch_001/page_001.pdf",
        "size": 524288,
        "version_id": "20241108120000000001",
        "batch_id": "batch_001",
        "qc_status": "approved"
    },
    metadata={
        "user": "operator1",
        "ip_address": "192.168.1.100"
    }
)

# Get hook statistics
stats = hook_manager.get_statistics()
print(f"Events fired: {stats['events_fired']}")
print(f"Hooks executed: {stats['hooks_executed']}")
print(f"Failed: {stats['hooks_failed']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Avg execution time: {stats['avg_execution_time']:.3f}s")

# List registered hooks
hooks = hook_manager.list_hooks()
for hook in hooks:
    print(f"{hook['name']}: {hook['type']}")
```

### Integration with Archive System

```python
from src.storage import LocalStorageManager, IntegrationHookManager, HookEvent
from src.organization.archive import ArchiveManager
from pathlib import Path

# Initialize components
storage = LocalStorageManager("data/storage", enable_versioning=True)
hook_manager = IntegrationHookManager()
archive_manager = ArchiveManager("data/qc_results")

# Register hooks for archive events
# ... (webhooks, callbacks, etc.)

# Archive document with storage and hooks
def archive_with_storage(page_id: str):
    # Get document from archive
    doc = archive_manager.get_document(page_id)
    
    # Store in persistent storage
    key = f"{doc['owner']}/{doc['year']}/{doc['doc_type']}/{doc['batch_id']}/{page_id}.json"
    metadata = storage.put_object(
        key=key,
        data=json.dumps(doc).encode('utf-8'),
        content_type="application/json",
        metadata={
            "batch_id": doc['batch_id'],
            "qc_status": doc['qc_status'],
            "doc_type": doc['doc_type']
        }
    )
    
    # Fire integration event
    hook_manager.fire_event(
        event=HookEvent.DOCUMENT_ARCHIVED,
        data={
            "key": key,
            "page_id": page_id,
            "size": metadata.size,
            "version_id": metadata.version_id,
            **doc
        }
    )
    
    return metadata

# Use in automation
page_id = "20241108_120000_page_001"
result = archive_with_storage(page_id)
print(f"Archived to storage: {result.key}")
```

---

## Integration Examples

### 1. ERP System Integration (SAP, Oracle)

```python
# Webhook configuration for SAP integration
sap_webhook = WebhookHook(
    name="sap_invoice_sync",
    url="https://sap.company.com/api/invoices/import",
    method="POST",
    headers={
        "Authorization": "Bearer SAP_API_TOKEN",
        "Content-Type": "application/json",
        "X-System-ID": "archive-system"
    },
    timeout=60,
    retry_count=5
)

# Only trigger for approved invoices
class SAPInvoiceHook(WebhookHook):
    def should_process(self, event, payload):
        return (
            event == HookEvent.DOCUMENT_ARCHIVED and
            payload.data.get('doc_type') == 'invoice' and
            payload.data.get('qc_status') == 'approved'
        )

hook_manager.register_hook(SAPInvoiceHook(
    name="sap_invoice_sync",
    url="https://sap.company.com/api/invoices/import",
    headers={"Authorization": "Bearer token"}
))
```

### 2. SharePoint/OneDrive Integration

```python
def sync_to_sharepoint(payload):
    from office365.runtime.auth.authentication_context import AuthenticationContext
    from office365.sharepoint.client_context import ClientContext
    
    # SharePoint credentials
    site_url = "https://company.sharepoint.com/sites/archive"
    username = "user@company.com"
    password = "password"
    
    # Authenticate
    ctx = ClientContext(site_url).with_credentials(
        UserCredential(username, password)
    )
    
    # Get document from storage
    data = storage.get_object(payload.data['key'])
    
    # Upload to SharePoint
    target_folder = ctx.web.get_folder_by_server_relative_url("Shared Documents/Archive")
    target_folder.upload_file(payload.data['key'], data).execute_query()
    
    print(f"Synced to SharePoint: {payload.data['key']}")

sharepoint_hook = CallbackHook(
    name="sharepoint_sync",
    callback=sync_to_sharepoint,
    events=[HookEvent.DOCUMENT_ARCHIVED]
)
hook_manager.register_hook(sharepoint_hook)
```

### 3. Backup to S3 Glacier

```python
# Secondary storage for long-term backup
glacier_storage = S3StorageManager(
    bucket_name="archive-backup-glacier",
    region="us-east-1",
    storage_class="GLACIER_DEEP_ARCHIVE",  # Cheapest for long-term
    enable_versioning=True
)

def backup_to_glacier(payload):
    # Get document from primary storage
    data = storage.get_object(payload.data['key'])
    
    # Store in Glacier with same key
    glacier_storage.put_object(
        key=payload.data['key'],
        data=data,
        content_type=payload.data.get('content_type', 'application/octet-stream'),
        metadata=payload.metadata
    )
    
    print(f"Backed up to Glacier: {payload.data['key']}")

glacier_hook = CallbackHook(
    name="glacier_backup",
    callback=backup_to_glacier,
    events=[HookEvent.DOCUMENT_ARCHIVED]
)
hook_manager.register_hook(glacier_hook)
```

### 4. SFTP Server Integration

```python
def sync_to_sftp(payload):
    import paramiko
    
    # SFTP configuration
    sftp_host = "sftp.partner.com"
    sftp_port = 22
    sftp_username = "archive_user"
    sftp_password = "secure_password"
    
    # Connect to SFTP
    transport = paramiko.Transport((sftp_host, sftp_port))
    transport.connect(username=sftp_username, password=sftp_password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    # Get document
    data = storage.get_object(payload.data['key'])
    
    # Upload to SFTP
    remote_path = f"/incoming/{payload.data['key']}"
    with sftp.open(remote_path, 'wb') as f:
        f.write(data)
    
    # Close connection
    sftp.close()
    transport.close()
    
    print(f"Synced to SFTP: {remote_path}")

sftp_hook = CallbackHook(
    name="sftp_sync",
    callback=sync_to_sftp,
    events=[HookEvent.BATCH_COMPLETED]
)
hook_manager.register_hook(sftp_hook)
```

---

## Best Practices

### Storage Backend Selection

**Local Storage:**
- ✅ Small deployments (< 1TB)
- ✅ Single-server setups
- ✅ Development/testing
- ✅ NAS/SAN available
- ❌ Multi-server deployments
- ❌ Cloud-native applications

**S3 Storage:**
- ✅ Cloud deployments
- ✅ Multi-server/distributed systems
- ✅ Large-scale (> 1TB)
- ✅ Geographic replication needed
- ✅ Pay-per-use model acceptable
- ❌ Latency-critical applications (unless using edge locations)

**MinIO (Self-Hosted S3):**
- ✅ On-premise with S3 API benefits
- ✅ Cost control
- ✅ Data sovereignty requirements
- ✅ High-performance object storage
- ✅ Kubernetes-native deployments

### Versioning Strategy

```python
# Production: Keep 10 versions, prune monthly
version_manager = VersionManager(storage)

# Tag important versions
version_manager.tag_version(
    key=document_key,
    version_id=current_version,
    tags={"milestone": "production", "tested": "true"}
)

# Schedule pruning (keep 10 versions, preserve tagged)
def monthly_prune():
    for document in all_documents:
        deleted = version_manager.prune_versions(
            key=document,
            keep_count=10,
            keep_tagged=True
        )
        print(f"Pruned {deleted} versions of {document}")

# Run monthly via cron or scheduler
```

### Integration Hook Patterns

**Sync vs Async:**
```python
# Sync: Critical operations that must complete
hook_manager_sync = IntegrationHookManager(async_execution=False)

# Async: Non-critical notifications
hook_manager_async = IntegrationHookManager(async_execution=True)
```

**Error Handling:**
```python
# Webhook with retries
reliable_webhook = WebhookHook(
    name="critical_integration",
    url="https://api.example.com/webhook",
    retry_count=5,  # Retry 5 times
    timeout=60      # 60 second timeout
)

# Callback with error logging
def safe_callback(payload):
    try:
        # Your integration code
        external_system.send_data(payload.data)
    except Exception as e:
        logger.error(f"Integration failed: {e}")
        # Send alert to admin
        send_alert_email(f"Integration failed: {e}")
```

### Security

**S3 Encryption:**
```python
# Server-side encryption (recommended)
storage = S3StorageManager(
    bucket_name="secure-archive",
    encryption="AES256",  # or "aws:kms" for KMS keys
    enable_versioning=True
)

# Client-side encryption (before upload)
from cryptography.fernet import Fernet

key = Fernet.generate_key()
cipher = Fernet(key)

data = Path("document.pdf").read_bytes()
encrypted_data = cipher.encrypt(data)

storage.put_object("secure/document.pdf", encrypted_data)
```

**Presigned URLs:**
```python
# Temporary access (1 hour)
url = storage.get_url(
    key="invoices/2024/inv_001.pdf",
    expires_in=3600  # 1 hour
)

# Share with external user (no credentials needed)
print(f"Download link (expires in 1 hour): {url}")
```

**IAM Policies (AWS):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetObjectVersion",
      "s3:PutObjectVersionTagging"
    ],
    "Resource": [
      "arn:aws:s3:::archive-bucket/*",
      "arn:aws:s3:::archive-bucket"
    ]
  }]
}
```

---

## Performance Optimization

### Multipart Uploads (Automatic)

```python
# boto3 automatically uses multipart for files > 8MB
storage.upload_file(
    file_path=Path("large_document.pdf"),  # 500 MB
    key="documents/large_document.pdf"
)
# Uploads in parallel parts (5MB chunks by default)
```

### Batch Operations

```python
# Batch upload
files = list(Path("batch_001").glob("*.pdf"))

for file in files:
    storage.upload_file(
        file_path=file,
        key=f"batch_001/{file.name}",
        metadata={"batch_id": "batch_001"}
    )

# Parallel uploads (use ThreadPoolExecutor)
from concurrent.futures import ThreadPoolExecutor

def upload_file(file):
    storage.upload_file(
        file_path=file,
        key=f"batch_001/{file.name}"
    )

with ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(upload_file, files)
```

### Caching

```python
# Cache frequently accessed documents
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_document(key):
    return storage.get_object(key)

# Use cached version
data = get_cached_document("frequently_accessed.pdf")
```

---

## Monitoring & Observability

### Hook Statistics

```python
# Get statistics
stats = hook_manager.get_statistics()

print(f"Events fired: {stats['events_fired']}")
print(f"Hooks executed: {stats['hooks_executed']}")
print(f"Failed: {stats['hooks_failed']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Avg execution time: {stats['avg_execution_time']:.3f}s")
print(f"Queue size: {stats['async_queue_size']}")
```

### Storage Metrics

```python
# Local storage info
info = storage.get_storage_info()

print(f"Backend: {info['backend']}")
print(f"Object count: {info['object_count']}")
print(f"Total size: {info['total_size'] / 1024**3:.2f} GB")
print(f"Version count: {info['version_count']}")
print(f"Version size: {info['version_size'] / 1024**3:.2f} GB")
```

### Audit Trail

```python
# File log hook creates audit trail
audit_log = FileLogHook(
    name="audit",
    log_file=Path("data/storage_audit.jsonl"),
    format="json"
)

hook_manager.register_hook(audit_log)

# Query audit log
import json

with open("data/storage_audit.jsonl", 'r') as f:
    for line in f:
        event = json.loads(line)
        print(f"{event['timestamp']}: {event['event']} - {event['data']['key']}")
```

---

## Summary

The Storage & Integration Layer provides:

**✅ Completed:**
- S3-compatible storage (AWS, MinIO, Wasabi, B2)
- Local filesystem storage with versioning
- Unified storage interface
- Version management (rollback, compare, history)
- Integration hooks (webhook, callback, file log)
- CLI for storage operations
- Comprehensive documentation

**📋 Next Steps:**
1. Install boto3: `pip install boto3`
2. Configure storage backend (local or S3)
3. Set up integration hooks for external systems
4. Test with CLI: `python storage_cli.py info`
5. Integrate with Archive Layer
6. Deploy to production with monitoring

**🔗 Related Documentation:**
- `ORGANIZATION_LAYER.md` - Archive system integration
- `QC_IMPLEMENTATION.md` - Quality control workflow
- `AUTHORIZATION_LAYER.md` - Security and access control
