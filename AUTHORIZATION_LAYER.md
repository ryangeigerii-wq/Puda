# Authorization Layer Implementation

## Overview

Comprehensive authorization and security layer for the document management system with Attribute-Based Access Control (ABAC), PII detection, audit trails, and encryption.

## Features

### 1. User Management
- **Storage**: SQLite database (`data/users.db`)
- **Authentication**: Username/password with SHA-256 hashing (salted)
- **Sessions**: Token-based sessions with 24-hour expiration
- **User Attributes**:
  - `user_id`: Unique identifier
  - `username`: Login name
  - `department`: Department (Finance, HR, IT, etc.)
  - `clearance_level`: 0-3 (Public, Internal, Confidential, Restricted)
  - `roles`: List of roles (admin, operator, viewer)
  - `email`: Contact email

**Default Credentials**:
- Username: `admin`
- Password: `admin`
- Clearance: 3 (full access)
- Department: administration

### 2. Attribute-Based Access Control (ABAC)

Policy-driven access control with flexible rule evaluation:

**Default Rules** (priority order):
1. **Admin Full Access** (1000): Users with 'admin' role can access everything
2. **Clearance Level** (900): `user.clearance_level >= document.confidentiality`
3. **Department Match** (800): `user.department == document.department`
4. **Owner Access** (700): `user.user_id == document.owner_id`
5. **Public Access** (600): Documents with confidentiality level 0 (PUBLIC)

**Confidentiality Levels**:
- 0: PUBLIC - Anyone can access
- 1: INTERNAL - Internal users only
- 2: CONFIDENTIAL - Requires clearance or department match
- 3: RESTRICTED - Admin or owner only

### 3. PII Detection

Automatic detection of 8 types of Personally Identifiable Information:

**Detected PII Types**:
- Social Security Numbers (SSN)
- Credit Card Numbers (with Luhn validation)
- Phone Numbers
- Email Addresses
- IP Addresses
- Date of Birth
- Passport Numbers
- Driver's License Numbers

**Features**:
- Regex pattern matching with validation
- Confidence scoring (0.6 to 0.95)
- **Auto-escalation**: Documents with high-confidence PII (≥0.8) automatically escalate to CONFIDENTIAL (level 2)
- PII redaction: Shows only first 2 + last 2 characters

**Example**:
```
SSN: 123-45-6789 → 12*******89
Email: john@example.com → jo************om
```

### 4. Audit Logging

Complete audit trail for compliance and security monitoring.

**Tracked Actions**:
- VIEW, DOWNLOAD, SEARCH, EDIT, DELETE, UPLOAD, SHARE, PRINT, EXPORT

**Captured Data**:
- User ID and username
- Action and timestamp
- Document ID
- IP address and user agent
- Session ID
- Access decision (allowed/denied)
- Custom metadata

**Features**:
- SQLite database (`data/audit_log.db`)
- Retention policy (default 365 days)
- Statistics and reporting
- JSON export capability
- Indexed for fast queries

### 5. Encryption

AES-256-CBC encryption for documents at rest.

**Specifications**:
- Algorithm: AES-256-CBC
- Key: 256-bit master key
- IV: Random 16-byte IV per file
- Padding: PKCS7
- Storage: Master key in `data/.encryption_key` (restricted permissions)

**Features**:
- File and text encryption/decryption
- Key derivation with context
- Entropy-based encryption detection
- Key rotation support

## Module Structure

```
src/authorization/
├── __init__.py              # Module exports
├── user_manager.py          # User authentication and sessions (531 lines)
├── policy_engine.py         # ABAC rules and enforcement (334 lines)
├── pii_detector.py          # PII detection and redaction (377 lines)
├── audit_logger.py          # Audit trail management (390 lines)
└── encryption.py            # AES-256 encryption (348 lines)
```

**Total**: 1,981 lines of code

## Usage Examples

### User Authentication

```python
from src.authorization import UserManager

# Initialize
user_mgr = UserManager("data/users.db")

# Authenticate (default admin)
user = user_mgr.authenticate("admin", "admin")
print(f"Authenticated: {user.username}, Clearance: {user.clearance_level}")

# Create session
session_token = user_mgr.create_session(user.user_id)

# Validate session
user = user_mgr.validate_session(session_token)
```

### Access Control

```python
from src.authorization import PolicyEngine, ConfidentialityLevel

# Initialize
policy = PolicyEngine()

# Define user and document context
user = {"user_id": "user123", "clearance_level": 2, "department": "Finance"}
document = {"confidentiality": 2, "department": "Finance"}

# Check access
allowed, reason = policy.check_access(user, document)
print(f"Access: {allowed}, Reason: {reason}")

# Explain decision
explanation = policy.explain_decision(user, document)
print(f"Matched rules: {explanation['matched_rules']}")
```

### PII Detection

```python
from src.authorization import PIIDetector

# Initialize
detector = PIIDetector()

# Detect PII in text
text = "Contact John at john@example.com or 555-123-4567"
matches = detector.detect(text)
for match in matches:
    print(f"{match.pii_type}: {match.value} (confidence: {match.confidence})")

# Scan document with auto-escalation
document = {
    "title": "Employee Record",
    "content": "SSN: 123-45-6789, DOB: 01/15/1990",
    "confidentiality": 1
}
pii_found, updated_doc = detector.scan_document(document)
print(f"New confidentiality: {updated_doc['confidentiality']}")  # 2 (CONFIDENTIAL)

# Redact PII
redacted = detector.redact_pii(text)
print(redacted)  # "Contact John at [REDACTED] or [REDACTED]"
```

### Audit Logging

```python
from src.authorization import AuditLogger, AuditAction

# Initialize
audit = AuditLogger("data/audit_log.db")

# Log access
audit.log_access(
    user_id="user123",
    username="john_doe",
    action=AuditAction.VIEW,
    resource_id="DOC001",
    ip_address="192.168.1.100",
    session_id="session123"
)

# Get statistics
stats = audit.get_statistics()
print(f"Total events: {stats['total_events']}")
print(f"By action: {stats['by_action']}")
print(f"Denied: {stats['denied_count']}")

# Get user activity
activity = audit.get_user_activity("user123")
for event in activity:
    print(f"{event['action']} on {event['resource_id']} at {event['timestamp']}")
```

### Encryption

```python
from src.authorization import EncryptionManager

# Initialize
mgr = EncryptionManager("data/.encryption_key")

# Encrypt text
text = "Sensitive information: SSN 123-45-6789"
encrypted = mgr.encrypt_text(text)
print(f"Encrypted: {encrypted[:50]}...")

# Decrypt text
decrypted = mgr.decrypt_text(encrypted)
print(f"Decrypted: {decrypted}")

# Encrypt file
mgr.encrypt_file("document.txt", "document.txt.enc")

# Decrypt file
mgr.decrypt_file("document.txt.enc", "document_decrypted.txt")
```

## Testing

Comprehensive test suite: `test_authorization.py`

Run tests:
```bash
python test_authorization.py
```

**Test Coverage**:
- User management (authentication, sessions, CRUD)
- Policy engine (ABAC rules, multiple users, confidentiality levels)
- PII detection (all 8 types, validation, escalation, redaction)
- Audit logging (events, statistics, history)
- Encryption (text, files, verification)

## Integration with Dashboard API

### Step 1: Add Authentication Middleware

```python
# dashboard_api.py

from src.authorization import UserManager, AuditLogger, AuditAction
from functools import wraps
from flask import request, jsonify

user_mgr = UserManager("data/users.db")
audit_logger = AuditLogger("data/audit_log.db")

def requires_auth(f):
    """Decorator to require authentication for endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get session token from header
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({"error": "No authorization token"}), 401
        
        # Validate session
        try:
            user = user_mgr.validate_session(token)
            request.user = user  # Attach user to request
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": "Invalid or expired session"}), 401
    
    return decorated
```

### Step 2: Add Login/Logout Endpoints

```python
@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    try:
        user = user_mgr.authenticate(username, password)
        session_token = user_mgr.create_session(user.user_id)
        
        # Log login
        audit_logger.log_access(
            user_id=user.user_id,
            username=user.username,
            action=AuditAction.VIEW,
            resource_id="login",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            "session_token": session_token,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "department": user.department,
                "clearance_level": user.clearance_level,
                "roles": user.roles
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route('/api/auth/logout', methods=['POST'])
@requires_auth
def logout():
    """User logout"""
    # Session cleanup happens automatically via expiration
    return jsonify({"message": "Logged out successfully"})

@app.route('/api/auth/me', methods=['GET'])
@requires_auth
def get_current_user():
    """Get current user info"""
    user = request.user
    return jsonify({
        "user_id": user.user_id,
        "username": user.username,
        "department": user.department,
        "clearance_level": user.clearance_level,
        "roles": user.roles,
        "email": user.email
    })
```

### Step 3: Protect Existing Endpoints

```python
@app.route('/api/archives/<archive_id>', methods=['GET'])
@requires_auth  # Add authentication
def get_archive(archive_id):
    """Get archive metadata"""
    user = request.user
    
    # Get archive
    archive = archive_indexer.get_archive(archive_id)
    if not archive:
        return jsonify({"error": "Archive not found"}), 404
    
    # Check access with ABAC
    from src.authorization import PolicyEngine
    policy = PolicyEngine()
    
    user_context = {
        "user_id": user.user_id,
        "clearance_level": user.clearance_level,
        "department": user.department,
        "roles": user.roles
    }
    
    doc_context = {
        "confidentiality": archive.get("confidentiality", 0),
        "department": archive.get("department"),
        "owner_id": archive.get("owner_id")
    }
    
    allowed, reason = policy.check_access(user_context, doc_context)
    
    # Log access attempt
    audit_logger.log_access(
        user_id=user.user_id,
        username=user.username,
        action=AuditAction.VIEW,
        resource_id=archive_id,
        allowed=allowed,
        ip_address=request.remote_addr,
        metadata={"reason": reason}
    )
    
    if not allowed:
        return jsonify({"error": "Access denied", "reason": reason}), 403
    
    return jsonify(archive)
```

## Security Considerations

### TLS Configuration (In Transit)

Add to documentation/deployment guide:

**For Production**:
1. Use HTTPS with valid SSL/TLS certificate
2. Configure Flask with SSL context:
   ```python
   app.run(ssl_context=('cert.pem', 'key.pem'))
   ```
3. Use reverse proxy (nginx/Apache) with TLS termination
4. Enforce HTTPS redirect

**Example nginx configuration**:
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### Password Hashing

Current implementation uses SHA-256 with salt (simplified). For production:

**Recommendation**: Use `bcrypt` or `argon2`:
```python
import bcrypt

# Hash password
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Verify password
if bcrypt.checkpw(password.encode(), hashed):
    # Valid
```

### Key Management

- Master encryption key stored in `data/.encryption_key`
- Set file permissions: `chmod 600` (Unix) or ACL (Windows)
- Consider using HSM or key management service for production
- Implement key rotation schedule

## Performance Considerations

### Database Indexes

All databases have appropriate indexes:
- `users`: username, email
- `sessions`: token, user_id, expiration
- `audit_events`: timestamp, user_id, resource_id, action

### Caching

Consider adding caching for:
- User sessions (Redis/Memcached)
- ABAC rules (in-memory)
- PII patterns (compiled regex)

### Scalability

For high-volume deployments:
- Use PostgreSQL instead of SQLite
- Separate audit log database
- Implement read replicas
- Use message queue for audit events

## Next Steps

1. ✅ **User Management** - Complete
2. ✅ **ABAC Policy Engine** - Complete
3. ✅ **PII Detection** - Complete
4. ✅ **Audit Logging** - Complete
5. ✅ **Encryption** - Complete
6. **API Integration** - Add middleware to dashboard_api.py
7. **Document Scanning** - Integrate PII detection into OCR pipeline
8. **Frontend** - Add login UI and session management
9. **Deployment** - TLS configuration and production setup
10. **Documentation** - API endpoints and security guide

## Files

- `src/authorization/__init__.py` - Module exports (31 lines)
- `src/authorization/user_manager.py` - User auth (531 lines)
- `src/authorization/policy_engine.py` - ABAC rules (334 lines)
- `src/authorization/pii_detector.py` - PII detection (377 lines)
- `src/authorization/audit_logger.py` - Audit trail (390 lines)
- `src/authorization/encryption.py` - AES-256 (348 lines)
- `test_authorization.py` - Test suite (331 lines)
- `AUTHORIZATION_LAYER.md` - This document

**Total**: 2,342 lines (including tests and docs)

## Dependencies

```
cryptography>=41.0.0  # For AES-256 encryption
```

Install: `pip install cryptography`
