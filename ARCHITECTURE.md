# 🏗️ Puda AI - Core Architecture Documentation

**Puda** (Paper Understanding & Document Automation) is a homebrew AI system for physical paper processing with OCR, classification, and intelligent routing.

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Core API Components](#core-api-components)
4. [Module Documentation](#module-documentation)
5. [Data Flow](#data-flow)
6. [API Endpoints](#api-endpoints)
7. [Security & Authorization](#security--authorization)
8. [Physical Paper Flow](#physical-paper-flow)
9. [Storage Architecture](#storage-architecture)
10. [Technology Stack](#technology-stack)

---

## 🎯 System Overview

### Purpose
Puda automates the complete lifecycle of physical document processing:
- **Physical handling**: Track paper movement through physical zones
- **Digitization**: OCR scanning with Tesseract
- **Intelligence**: ML-based document classification and routing
- **Security**: ABAC authorization with PII detection
- **Organization**: Archive management with search and retrieval

### Design Principles
1. **Unidirectional Flow**: Papers move left-to-right only (no backtracking except QC rescan)
2. **Zone-Based Processing**: Each zone has specific capacity and responsibilities
3. **API-First**: RESTful API for all operations
4. **Security-By-Design**: Authorization, encryption, and audit logging built-in
5. **Scalability**: Modular architecture supports independent scaling

---

## 🏛️ Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
│  Dashboard UI │ Processing UI │ CLI Tools │ External Apps   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  API LAYER (Flask)                           │
│  Authentication │ Routing │ QC │ Archive │ Health           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 BUSINESS LOGIC LAYER                         │
│  ┌─────────────┬──────────────┬──────────────┬───────────┐  │
│  │ Physical    │ Authorization│ Organization │ QC System │  │
│  │ Control     │ & Security   │ & Archive    │ & Routing │  │
│  └─────────────┴──────────────┴──────────────┴───────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  DATA LAYER                                  │
│  SQLite │ PostgreSQL │ S3 │ Local FS │ Audit Logs          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Core API Components

### 1. **Dashboard API Server** (`dashboard_api.py`)
Flask-based REST API serving as the system's central nervous system.

**Key Features:**
- Session-based authentication with Bearer tokens
- Rate limiting (Flask-Limiter)
- Modular subsystem initialization
- Static file serving for web UIs
- Comprehensive endpoint routing

**Configuration:**
```python
# Server initialization
python dashboard_api.py --host 0.0.0.0 --port 8080 --verbose
```

**CLI Flags:**
- `--verbose`: Enable detailed logging
- `--safe`: Continue on subsystem failure
- `--minimal`: Minimal initialization
- `--no-qc`: Disable QC modules
- `--no-org`: Disable organization modules
- `--no-auth`: Disable authorization
- `--debug`: Flask debug mode

### 2. **Authorization System** (`src/authorization/`)
Attribute-Based Access Control (ABAC) with enterprise security features.

**Components:**
- `user_manager.py`: User authentication, session management
- `policy_engine.py`: ABAC policy evaluation
- `pii_detector.py`: Detect and redact PII (SSN, credit cards, etc.)
- `audit_logger.py`: Comprehensive audit trail
- `encryption.py`: Data encryption at rest

**User Model:**
```python
@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    department: str = "general"
    clearance_level: int = 1  # 0=public, 1=internal, 2=confidential, 3=restricted
    roles: List[str] = ["viewer"]
    email: Optional[str] = None
    attributes: Dict[str, Any] = {}
```

**Default Users:**
- **Admin**: `admin/admin` - Full access (clearance 3, roles: admin/operator/viewer)
- **Ryan**: `ryan/password` - Standard user (clearance 1, roles: operator/viewer)

### 3. **Physical Control System** (`src/physical/`)
Manages physical paper movement through processing zones.

**Zones:**
- **Intake**: Receive boxes (capacity: unlimited)
- **Prep**: Unbox and remove staples (capacity: 30 boxes)
- **Scanning**: Digitize papers (capacity: 100 papers, 2 ADF + 1 workstation)
- **QC**: Quality control checks (capacity: 50 papers)
- **Output**: Disposition management (capacity: 500 papers)

**CLI Tools:**
- `intake_cli.py`: Receive and log boxes
- `prep_cli.py`: Unbox and prepare papers
- `scan_cli.py`: Manage scanning stations
- `qc_cli.py`: Quality control operations
- `output_cli.py`: Process output bins

### 4. **QC System** (`src/qc/`)
Quality control and routing intelligence.

**Components:**
- `queue.py`: QC task queue management
- `feedback.py`: Operator feedback collection
- Severity-based routing (qc, manual, auto)
- Issue categorization (blurry, missing pages, etc.)

### 5. **Organization System** (`src/organization/`)
Document archive, search, and retrieval.

**Components:**
- `archive.py`: Archive management
- `indexer.py`: Full-text search with SQLite FTS5
- `pdf_merger.py`: Merge multi-page PDFs
- `thumbnails.py`: Generate preview thumbnails

### 6. **Storage Layer** (`src/storage/`)
Multi-backend storage abstraction.

**Backends:**
- `local_storage.py`: Local filesystem
- `postgres_storage.py`: PostgreSQL
- `s3_storage.py`: AWS S3
- `storage_interface.py`: Unified interface
- `version_manager.py`: Document versioning

---

## 📦 Module Documentation

### Authorization Module

#### User Manager
```python
from src.authorization import UserManager

# Initialize
user_manager = UserManager(db_path="data/users.db")

# Authenticate
user = user_manager.authenticate("admin", "admin")

# Create session
session_token = user_manager.create_session(user, ip_address="127.0.0.1")

# Validate session
user = user_manager.validate_session(session_token)

# Create new user
user = user_manager.create_user(
    username="operator1",
    password="secret123",
    department="operations",
    clearance_level=2,
    roles=["operator", "viewer"]
)
```

#### Policy Engine
```python
from src.authorization import PolicyEngine

policy_engine = PolicyEngine()

# Check document access
allowed = policy_engine.check_document_access(
    user=user,
    document={"owner": "finance", "classification": "confidential"}
)
```

#### Audit Logger
```python
from src.authorization import AuditLogger, AuditAction

audit_logger = AuditLogger(db_path="data/audit_log.db")

# Log action
audit_logger.log(
    user_id="user123",
    action=AuditAction.ACCESS,
    resource_type="document",
    resource_id="DOC-001",
    details={"ip": "127.0.0.1"}
)
```

### Physical Control Module

#### Control System
```python
from src.physical.control import PaperControlSystem

control = PaperControlSystem()

# Intake workflow
control.receive_box("BOX-001")
control.log_box_details("BOX-001", paper_count=100, notes="Urgent")

# Prep workflow
control.move_box_to_prep("BOX-001")
control.start_unboxing("BOX-001")
control.add_paper("BOX-001", "PAPER-001", has_staples=True, pages=3)
control.remove_staples("PAPER-001")
control.mark_paper_ready("PAPER-001")
control.complete_box_prep("BOX-001")

# Scanning workflow
control.move_papers_to_scanning("BOX-001")
control.start_scan("PAPER-001")
control.complete_scan("PAPER-001", success=True, output_file="scan.pdf")

# QC workflow
control.move_papers_to_qc()
control.start_qc_check("PAPER-001", "QC_OP_1")
control.complete_qc_check("PAPER-001", "QC_OP_1", passed=True)

# Output workflow
control.move_paper_to_output("PAPER-001", disposition="return")
control.process_bin("BIN-001", action="return")
```

### QC Module

#### Queue Management
```python
from src.qc.queue import QCQueue

qc_queue = QCQueue()

# Add to queue
qc_queue.add_to_queue(
    doc_id="DOC-001",
    severity="manual",
    reason="Complex document",
    metadata={"pages": 10}
)

# Get statistics
stats = qc_queue.get_stats()
# Returns: {total: 50, qc: 10, manual: 20, auto: 20}
```

#### Feedback Collection
```python
from src.qc.feedback import FeedbackCollector

feedback = FeedbackCollector()

# Submit feedback
feedback.submit_feedback(
    doc_id="DOC-001",
    operator_id="OP-123",
    rating=4,
    issue_type="formatting",
    notes="Minor alignment issue"
)

# Get stats
stats = feedback.get_stats()
operator_stats = feedback.get_operator_stats("OP-123")
```

### Organization Module

#### Archive Manager
```python
from src.organization.archive import ArchiveManager

archive = ArchiveManager("data/archive")

# Archive document
page_id = archive.archive_page(
    image_path="scan.jpg",
    box_id="BOX-001",
    owner="John Doe",
    doc_type="invoice",
    year=2025,
    metadata={"amount": 1500.00}
)

# Get statistics
stats = archive.get_archive_stats()
```

#### Search Indexer
```python
from src.organization.indexer import ArchiveIndexer, SearchQuery

indexer = ArchiveIndexer("data/index.db")

# Index document
indexer.index_page(
    page_id="PAGE-001",
    box_id="BOX-001",
    text="Invoice for services...",
    metadata={"owner": "John", "doc_type": "invoice"}
)

# Search
query = SearchQuery(
    text="invoice services",
    owner="John",
    doc_type="invoice",
    year=2025
)
results = indexer.search(query, limit=10)
```

---

## 🔄 Data Flow

### Document Processing Flow

```
┌──────────────┐
│  Physical    │ ➊ Receive box
│  Intake      │ ➋ Log details
└──────┬───────┘
       │
       ↓ Box moves to prep
┌──────────────┐
│  Prep Zone   │ ➌ Unbox papers
│              │ ➍ Remove staples
│              │ ➎ Mark ready
└──────┬───────┘
       │
       ↓ Papers to scanning
┌──────────────┐
│  Scanning    │ ➏ Auto-assign station
│  Zone        │ ➐ OCR extraction
│              │ ➑ Generate PDF
└──────┬───────┘
       │
       ↓ Papers to QC
┌──────────────┐
│  QC Zone     │ ➒ Visual check
│              │ ➓ Pass/Fail
│              │   └─→ Rescan if failed
└──────┬───────┘
       │
       ↓ Papers to output
┌──────────────┐
│  Output      │ ⓫ Assign disposition
│  Rack        │    (return/shred/archive)
│              │ ⓬ Process bin
└──────────────┘
```

### API Request Flow

```
Client Request
     ↓
Flask Route Handler
     ↓
Authentication Check (@requires_auth)
     ↓
Authorization Check (PolicyEngine)
     ↓
Business Logic Execution
     ↓
Data Layer Access (Storage/DB)
     ↓
Audit Log Entry
     ↓
JSON Response
```

---

## 🔌 API Endpoints

### Authentication Endpoints

#### POST `/api/auth/login`
Login with username/password, returns session token.

**Request:**
```json
{
  "username": "admin",
  "password": "admin"
}
```

**Response:**
```json
{
  "session_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "user_id": "abc123",
    "username": "admin",
    "department": "administration",
    "clearance_level": 3,
    "roles": ["admin", "operator", "viewer"]
  }
}
```

**Rate Limit:** 5 requests per minute per IP

#### POST `/api/auth/logout`
Invalidate current session token.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

#### GET `/api/auth/me`
Get current user information.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Response:**
```json
{
  "user_id": "abc123",
  "username": "admin",
  "department": "administration",
  "clearance_level": 3,
  "roles": ["admin", "operator", "viewer"],
  "email": "admin@localhost",
  "last_login": 1699484821.5
}
```

### Routing & Monitoring Endpoints

#### GET `/api/routing/summary`
Get routing statistics summary.

**Query Parameters:**
- `days` (int): Filter last N days (default: 7)
- `doc_type` (string): Filter by document type
- `severity` (string): Filter by severity (qc, manual, auto)
- `operator` (string): Filter by operator ID

**Response:**
```json
{
  "total_documents": 1250,
  "qc_count": 150,
  "manual_count": 400,
  "auto_count": 700,
  "qc_percentage": 12.0,
  "manual_percentage": 32.0,
  "auto_percentage": 56.0,
  "by_doc_type": {
    "invoice": 500,
    "receipt": 300,
    "contract": 450
  },
  "by_severity": {
    "qc": 150,
    "manual": 400,
    "auto": 700
  }
}
```

#### GET `/api/routing/recent`
Get recent routing entries.

**Query Parameters:**
- `limit` (int): Number of entries (default: 50, max: 1000)

**Response:**
```json
{
  "entries": [
    {
      "timestamp": "2025-11-08T21:30:45",
      "doc_id": "DOC-12345",
      "doc_type": "invoice",
      "severity": "manual",
      "reason": "Complex layout requires review",
      "operator_id": "OP-001"
    }
  ]
}
```

#### GET `/api/routing/trends`
Get routing trends over time.

**Query Parameters:**
- `days` (int): Number of days (default: 30)

**Response:**
```json
{
  "trends": [
    {
      "date": "2025-11-08",
      "total": 85,
      "qc": 10,
      "manual": 30,
      "auto": 45
    }
  ]
}
```

### QC Endpoints

#### GET `/api/qc/queue/stats`
Get QC queue statistics.

**Response:**
```json
{
  "total": 45,
  "qc": 8,
  "manual": 22,
  "auto": 15,
  "oldest_timestamp": "2025-11-08T10:15:30"
}
```

#### GET `/api/qc/queue/pending`
Get pending QC tasks.

**Query Parameters:**
- `severity` (string): Filter by severity
- `limit` (int): Max results

**Response:**
```json
{
  "tasks": [
    {
      "doc_id": "DOC-001",
      "severity": "qc",
      "queued_at": "2025-11-08T14:20:00",
      "reason": "Quality check required"
    }
  ]
}
```

#### GET `/api/qc/feedback/stats`
Get feedback statistics.

**Response:**
```json
{
  "total_feedback": 234,
  "average_rating": 4.2,
  "by_issue_type": {
    "poor_quality": 45,
    "missing_pages": 12,
    "blurry": 23
  }
}
```

#### GET `/api/qc/operator/<operator_id>/stats`
Get operator-specific statistics.

**Response:**
```json
{
  "operator_id": "OP-123",
  "total_reviews": 156,
  "average_rating": 4.5,
  "recent_feedback": [...]
}
```

### Archive Endpoints

#### GET `/api/archive/stats`
Get archive statistics.

**Response:**
```json
{
  "total_pages": 12450,
  "total_boxes": 89,
  "storage_used_mb": 3456.78,
  "by_doc_type": {
    "invoice": 5000,
    "receipt": 3000,
    "contract": 4450
  },
  "by_year": {
    "2023": 4000,
    "2024": 5000,
    "2025": 3450
  }
}
```

#### GET `/api/archive/search`
Full-text search in archive.

**Query Parameters:**
- `text` (string): Search query
- `owner` (string): Filter by owner
- `doc_type` (string): Filter by document type
- `year` (int): Filter by year
- `box_id` (string): Filter by box ID
- `limit` (int): Max results (default: 50)

**Response:**
```json
{
  "results": [
    {
      "page_id": "PAGE-001",
      "box_id": "BOX-045",
      "owner": "John Doe",
      "doc_type": "invoice",
      "year": 2025,
      "rank": 0.85,
      "snippet": "...invoice for services rendered..."
    }
  ],
  "total": 15,
  "query": "invoice services"
}
```

#### GET `/api/archive/document/<page_id>`
Get document metadata and image.

**Response:**
```json
{
  "page_id": "PAGE-001",
  "box_id": "BOX-045",
  "image_path": "/archive/2025/BOX-045/PAGE-001.jpg",
  "owner": "John Doe",
  "doc_type": "invoice",
  "year": 2025,
  "archived_at": "2025-11-08T15:30:00"
}
```

#### GET `/api/archive/thumbnail/<page_id>`
Get thumbnail image.

**Query Parameters:**
- `size` (string): Thumbnail size (small=150px, medium=300px, large=600px)

**Response:** JPEG image

#### POST `/api/archive/merge`
Merge multiple pages into single PDF.

**Request:**
```json
{
  "page_ids": ["PAGE-001", "PAGE-002", "PAGE-003"],
  "output_filename": "merged_invoice.pdf"
}
```

**Response:**
```json
{
  "pdf_path": "/archive/merged/merged_invoice.pdf",
  "page_count": 3
}
```

### Health & System Endpoints

#### GET `/api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "routing_dashboard_api",
  "timestamp": "2025-11-08T21:45:30"
}
```

---

## 🔐 Security & Authorization

### Authentication Flow

1. **Login**: User submits credentials to `/api/auth/login`
2. **Validation**: UserManager verifies password hash
3. **Session Creation**: Generate secure token (urlsafe 32 bytes)
4. **Token Storage**: Client stores token in localStorage
5. **Request Authentication**: Client sends `Authorization: Bearer <token>` header
6. **Token Validation**: Server validates token on each request

### Authorization Levels

**Clearance Levels:**
- **0 - Public**: No restrictions
- **1 - Internal**: Internal documents only
- **2 - Confidential**: Restricted to authorized personnel
- **3 - Restricted**: Highest clearance, admin access

**Roles:**
- **viewer**: Read-only access
- **operator**: Process documents, submit feedback
- **admin**: Full system access, user management

### Security Features

1. **Password Hashing**: SHA-256 with random salt
2. **Session Expiration**: 24-hour default timeout
3. **Rate Limiting**: 5 login attempts per minute
4. **Audit Logging**: All actions logged with timestamp, user, action, resource
5. **PII Detection**: Automatic detection and redaction of sensitive data
6. **Encryption**: Data encryption at rest (optional)

### Audit Trail

All actions are logged to `data/audit_log.db`:

```python
audit_logger.log(
    user_id="user123",
    action=AuditAction.ACCESS,  # CREATE, ACCESS, MODIFY, DELETE, EXPORT
    resource_type="document",
    resource_id="DOC-001",
    details={"ip": "127.0.0.1", "result": "success"}
)
```

---

## 📄 Physical Paper Flow

### Zone Capacity Management

| Zone | Capacity | Purpose |
|------|----------|---------|
| Intake | Unlimited | Receive and log boxes |
| Prep | 30 boxes | Unbox and remove staples |
| Scanning | 100 papers | Digitize with OCR |
| QC | 50 papers | Quality control checks |
| Output | 500 papers | Disposition management |

### Status Transitions

**Box Statuses:**
```
RECEIVED → LOGGED → IN_QUEUE → UNBOXING → SORTING_PREP → 
STAPLE_REMOVAL → PREP_COMPLETE → COMPLETE
```

**Paper Statuses:**
```
IN_BOX → EXTRACTED → STAPLED → STAPLES_REMOVED → READY → 
IN_QUEUE → SCANNING → SCAN_COMPLETE → QC_PENDING → QC_IN_PROGRESS → 
QC_PASSED/QC_FAILED → IN_OUTPUT → DISPOSED
```

### Scanning Stations

**Station Types:**
- **ADF (Automatic Document Feeder)**: High-speed batch scanning
- **Workstation**: Manual scanning for delicate documents

**Station Status:**
- `available`: Ready for new scan
- `scanning`: Currently processing
- `maintenance`: Offline for maintenance

---

## 💾 Storage Architecture

### Storage Abstraction Layer

Unified interface supporting multiple backends:

```python
from src.storage import StorageInterface

# Initialize with backend
storage = StorageInterface.create("postgres")  # or "local", "s3"

# Store document
doc_id = storage.store_document(
    data={"title": "Invoice", "amount": 1500},
    metadata={"owner": "John", "type": "invoice"}
)

# Retrieve document
doc = storage.retrieve_document(doc_id)

# Search documents
results = storage.search_documents(query={"owner": "John"})
```

### Backend Comparison

| Feature | Local FS | PostgreSQL | AWS S3 |
|---------|----------|------------|--------|
| Performance | Fast | Medium | Slow |
| Scalability | Limited | High | Very High |
| Cost | Low | Medium | Variable |
| Durability | Single point | Replicated | 99.999999999% |
| Search | Limited | Full SQL | Limited |

### Database Schema

**Users Table:**
```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    department TEXT DEFAULT 'general',
    clearance_level INTEGER DEFAULT 1,
    roles TEXT NOT NULL,  -- JSON array
    email TEXT,
    created_at REAL NOT NULL,
    last_login REAL,
    is_active INTEGER DEFAULT 1,
    attributes TEXT  -- JSON object
);
```

**Sessions Table:**
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

**Audit Log Table:**
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,  -- CREATE, ACCESS, MODIFY, DELETE, EXPORT
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    details TEXT,  -- JSON object
    ip_address TEXT,
    result TEXT DEFAULT 'success'
);
```

---

## 🛠️ Technology Stack

### Backend
- **Python 3.9+**: Core language
- **Flask 3.0**: Web framework
- **Flask-Limiter 3.5**: Rate limiting
- **SQLite 3**: Embedded database (users, sessions, audit logs)
- **PostgreSQL**: Optional production database
- **Tesseract OCR**: Text extraction
- **OpenCV**: Image preprocessing
- **Pillow (PIL)**: Image manipulation

### Frontend
- **HTML5 + CSS3**: Static pages
- **Vanilla JavaScript**: No framework dependencies
- **Chart.js 4.4**: Data visualization
- **Fetch API**: RESTful API calls

### Storage
- **Local Filesystem**: Development and small deployments
- **AWS S3**: Cloud storage (optional)
- **PostgreSQL**: Structured data storage

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **PowerShell**: Automation scripts (Windows)
- **Bash**: Automation scripts (Linux)

### Security
- **SHA-256**: Password hashing
- **UUID v4**: Secure token generation
- **secrets module**: Cryptographically secure random

### Testing
- **pytest**: Unit and integration testing
- **Flask test_client**: API endpoint testing

---

## 📊 Performance Characteristics

### API Response Times (Typical)

| Endpoint | Avg Response Time | Notes |
|----------|-------------------|-------|
| `/api/health` | <10ms | Simple status check |
| `/api/auth/login` | 50-100ms | Password hashing overhead |
| `/api/routing/summary` | 100-300ms | Depends on log volume |
| `/api/archive/search` | 200-500ms | Full-text search |
| `/api/archive/thumbnail` | 50-150ms | Image resize + cache |

### Capacity Limits

| Resource | Limit | Configurable |
|----------|-------|--------------|
| Session tokens | Unlimited | ✅ Expires after 24h |
| API rate limit | 50/hour | ✅ Via Flask-Limiter |
| Login attempts | 5/min/IP | ✅ Via Flask-Limiter |
| File upload size | 50MB | ✅ Flask config |
| Archive pages | Unlimited | ❌ Storage dependent |

---

## 🚀 Deployment Guide

### Development Setup

```powershell
# Clone repository
git clone https://github.com/yourusername/puda.git
cd puda

# Install dependencies
pip install -r requirements.txt

# Start server
python dashboard_api.py --host 0.0.0.0 --port 8080 --verbose
```

### Docker Deployment

```powershell
# Build image
docker build -t puda:latest .

# Run container
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  --name puda-app \
  puda:latest

# Or use docker-compose
docker-compose up -d
```

### Production Considerations

1. **Web Server**: Replace Flask dev server with Gunicorn/uWSGI
2. **Database**: Migrate to PostgreSQL for production
3. **Storage**: Use S3 for scalable document storage
4. **SSL/TLS**: Enable HTTPS with valid certificates
5. **Load Balancing**: Use nginx or cloud load balancer
6. **Monitoring**: Integrate with Prometheus/Grafana
7. **Backup**: Implement regular database backups

---

## 🔧 Configuration

### Environment Variables

```bash
# Server configuration
PUDA_HOST=0.0.0.0
PUDA_PORT=8080
PUDA_DEBUG=false

# Database paths
PUDA_USER_DB=data/users.db
PUDA_AUDIT_DB=data/audit_log.db
PUDA_ARCHIVE_DIR=data/archive

# Session configuration
PUDA_SESSION_DURATION=24  # hours
PUDA_SESSION_CLEANUP=1    # hours

# Rate limiting
PUDA_RATE_LIMIT_ENABLED=true
PUDA_RATE_LIMIT_LOGIN=5/minute
PUDA_RATE_LIMIT_GLOBAL=200/day

# Storage backend
PUDA_STORAGE_BACKEND=local  # local, postgres, s3
PUDA_S3_BUCKET=my-puda-bucket
PUDA_S3_REGION=us-east-1
```

### File Locations

```
data/
├── users.db              # User database
├── audit_log.db          # Audit trail
├── qc_queue.json         # QC queue (ephemeral)
├── feedback.json         # QC feedback (ephemeral)
├── archive/              # Document archive
│   ├── 2023/
│   ├── 2024/
│   └── 2025/
│       └── BOX-001/
│           ├── PAGE-001.jpg
│           └── PAGE-002.jpg
├── thumbnails/           # Thumbnail cache
└── merged_pdfs/          # Merged PDF output
```

---

## 📚 Additional Resources

- **[README.md](README.md)**: Quick start and overview
- **[QUICKREF.md](QUICKREF.md)**: Command reference
- **[FLOW_SYSTEM.md](FLOW_SYSTEM.md)**: Physical flow details
- **[DOCKER.md](DOCKER.md)**: Docker deployment guide
- **[FLOW_IMPLEMENTATION.md](FLOW_IMPLEMENTATION.md)**: Implementation details
- **[OUTPUT_ZONE.md](OUTPUT_ZONE.md)**: Output zone documentation

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 💡 Next Steps

### Planned Features
- [ ] Real Tesseract OCR integration (currently simulated)
- [ ] ML document classification
- [ ] Webhook notifications
- [ ] Multi-language OCR support
- [ ] Mobile app for on-the-go QC
- [ ] Real-time WebSocket updates
- [ ] Export to popular formats (Excel, CSV, JSON)
- [ ] Advanced analytics dashboard

### Integration Opportunities
- **ERP Systems**: SAP, Oracle, NetSuite
- **Document Management**: SharePoint, Alfresco
- **Workflow**: Zapier, n8n, IFTTT
- **Cloud Storage**: Dropbox, Google Drive, OneDrive
- **Analytics**: Power BI, Tableau

---

**Version**: 1.0.0  
**Last Updated**: November 8, 2025  
**Authors**: Puda Development Team
