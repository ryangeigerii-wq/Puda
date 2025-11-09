# Frontend Authentication Guide

Complete guide for the Dashboard UI authentication system integration.

## Overview

The Dashboard UI now includes a complete authentication flow with:
- **Login page** with modern gradient UI
- **Session management** using localStorage
- **Token-based authentication** with Bearer tokens
- **Auto-redirect** for protected pages
- **Rate limiting** protection (5 login attempts per minute)
- **User info display** showing clearance level and roles
- **Logout functionality** with session cleanup

---

## Architecture

```
┌─────────────┐
│   Browser   │
│             │
│ localStorage│ ← stores session_token + user object
└──────┬──────┘
       │
       │ HTTP/HTTPS
       │
┌──────▼──────────────────────────────────────┐
│         Flask Dashboard API                  │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  Rate Limiter (Flask-Limiter)          │ │
│  │  5 login attempts per minute per IP    │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  Auth Endpoints                         │ │
│  │  POST /api/auth/login                  │ │
│  │  POST /api/auth/logout                 │ │
│  │  GET  /api/auth/me                     │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  @requires_auth Middleware             │ │
│  │  Validates Bearer tokens               │ │
│  │  Attaches user to request context      │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │  Protected Endpoints                    │ │
│  │  12 endpoints require authentication   │ │
│  └────────────────────────────────────────┘ │
└──────────────┬───────────────────────────────┘
               │
       ┌───────▼──────────┐
       │  UserManager     │
       │  data/users.db   │
       │  SHA-256 hashing │
       │  24h sessions    │
       └──────────────────┘
```

---

## File Structure

```
Puda/
├── static/
│   ├── login.html          # Login page (313 lines)
│   └── dashboard.html      # Main dashboard (now with auth check)
├── src/
│   └── authorization/
│       ├── user_manager.py   # User authentication
│       ├── policy_engine.py  # ABAC authorization
│       └── audit_logger.py   # Access logging
├── dashboard_api.py        # Flask API with auth middleware
└── data/
    ├── users.db            # User accounts and sessions
    └── audit_log.db        # Authentication events
```

---

## User Flow

### 1. Initial Access (Not Authenticated)

```
User → /dashboard.html
  ↓ checkAuth() runs on page load
  ↓ No session_token in localStorage
  ↓ Redirect to /login.html
User → /login.html
```

### 2. Login Flow

```
User enters credentials
  ↓ JavaScript validates form
  ↓ POST /api/auth/login
  ↓ Rate limiter checks: max 5 attempts/minute
  ↓ UserManager.authenticate(username, password)
  ↓ SHA-256 password verification
  ↓ Create session (24h expiry)
  ↓ Return {session_token, user}
  ↓ Store in localStorage
  ↓ Redirect to /dashboard.html
```

### 3. Dashboard Access (Authenticated)

```
User → /dashboard.html
  ↓ checkAuth() runs
  ↓ Read session_token from localStorage
  ↓ GET /api/auth/me (validate token)
  ↓ Token valid → display user info
  ↓ Fetch dashboard data with Bearer token
```

### 4. Logout Flow

```
User clicks "Logout" button
  ↓ POST /api/auth/logout (with Bearer token)
  ↓ UserManager.invalidate_session(token)
  ↓ Clear localStorage
  ↓ Redirect to /login.html
```

---

## Code Implementation

### Login Page (`static/login.html`)

**Key Features:**
- Modern gradient UI (purple/blue theme)
- Client-side validation
- Auto-redirect if already logged in
- Error handling for rate limiting (429)
- Loading state with spinner

**JavaScript Functions:**

```javascript
// Auto-redirect if already logged in
const token = localStorage.getItem('session_token');
if (token) {
    fetch(`/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
    }).then(response => {
        if (response.ok) {
            window.location.href = '/dashboard.html';
        }
    });
}

// Login form submission
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (response.status === 429) {
            showAlert('Too many login attempts. Please try again later.', 'error');
            return;
        }
        
        if (!response.ok) {
            showAlert('Invalid username or password', 'error');
            return;
        }
        
        const data = await response.json();
        
        // Store credentials
        localStorage.setItem('session_token', data.session_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // Redirect to dashboard
        window.location.href = '/dashboard.html';
    } catch (error) {
        showAlert('Network error. Please try again.', 'error');
    }
});
```

**Error Handling:**
- **401 Unauthorized**: Invalid credentials
- **429 Too Many Requests**: Rate limit exceeded (show "try again later")
- **503 Service Unavailable**: Authorization module not available
- **Network errors**: Connection issues

---

### Dashboard Authentication (`static/dashboard.html`)

**Key Functions:**

#### 1. `checkAuth()` - Validate Session on Page Load

```javascript
function checkAuth() {
    sessionToken = localStorage.getItem('session_token');
    const userStr = localStorage.getItem('user');
    
    if (!sessionToken) {
        // No token, redirect to login
        window.location.href = '/login.html';
        return false;
    }
    
    if (userStr) {
        currentUser = JSON.parse(userStr);
        displayUserInfo();
    }
    
    // Verify token is still valid
    fetch(`${API_BASE}/api/auth/me`, {
        headers: {
            'Authorization': `Bearer ${sessionToken}`
        }
    })
    .then(response => {
        if (!response.ok) {
            // Token invalid, redirect to login
            localStorage.removeItem('session_token');
            localStorage.removeItem('user');
            window.location.href = '/login.html';
        }
        return response.json();
    })
    .then(data => {
        if (data && data.user) {
            currentUser = data.user;
            localStorage.setItem('user', JSON.stringify(data.user));
            displayUserInfo();
        }
    })
    .catch(() => {
        // Network error or invalid token
        localStorage.removeItem('session_token');
        localStorage.removeItem('user');
        window.location.href = '/login.html';
    });
    
    return true;
}
```

#### 2. `displayUserInfo()` - Show User in Header

```javascript
function displayUserInfo() {
    if (!currentUser) return;
    
    const userInfo = document.getElementById('userInfo');
    const userDisplay = document.getElementById('userDisplay');
    
    const clearanceBadge = `<span class="badge">Clearance ${currentUser.clearance_level}</span>`;
    const roleBadges = currentUser.roles.map(role => 
        `<span class="badge">${role}</span>`
    ).join(' ');
    
    userDisplay.innerHTML = `
        <div><strong>${currentUser.username}</strong> - ${currentUser.department}</div>
        <div>${clearanceBadge} ${roleBadges}</div>
    `;
    userInfo.style.display = 'block';
}
```

#### 3. `logout()` - Clear Session

```javascript
async function logout() {
    if (!sessionToken) return;
    
    try {
        await fetch(`${API_BASE}/api/auth/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${sessionToken}`
            }
        });
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    // Clear local storage
    localStorage.removeItem('session_token');
    localStorage.removeItem('user');
    
    // Redirect to login
    window.location.href = '/login.html';
}
```

#### 4. Automatic Bearer Token Injection

```javascript
// Add authorization header to all fetch requests
const originalFetch = window.fetch;
window.fetch = function(...args) {
    if (sessionToken && args[0].includes('/api/')) {
        args[1] = args[1] || {};
        args[1].headers = args[1].headers || {};
        args[1].headers['Authorization'] = `Bearer ${sessionToken}`;
    }
    return originalFetch.apply(this, args);
};
```

**HTML Header Update:**

```html
<div class="header">
    <div class="header-content">
        <h1>📊 Routing Dashboard</h1>
        <p>Real-time monitoring of document routing decisions</p>
    </div>
    <div class="user-info" id="userInfo" style="display: none;">
        <div class="username" id="userDisplay"></div>
        <button class="btn-logout" onclick="logout()">Logout</button>
    </div>
</div>
```

**CSS Styles:**

```css
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.user-info {
    text-align: right;
}

.user-info .badge {
    background: rgba(255, 255, 255, 0.2);
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.85em;
    margin-left: 5px;
}

.btn-logout {
    background: rgba(255, 255, 255, 0.2);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.3);
    padding: 8px 20px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s;
}

.btn-logout:hover {
    background: rgba(255, 255, 255, 0.3);
}
```

---

### Backend API (`dashboard_api.py`)

#### Rate Limiting Setup

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    headers_enabled=True
)

def rate_limit(limit_string):
    """Decorator to apply rate limiting if available."""
    def decorator(f):
        if limiter:
            return limiter.limit(limit_string)(f)
        return f
    return decorator
```

#### Authentication Endpoints

**1. Login Endpoint:**

```python
@app.route('/api/auth/login', methods=['POST'])
@rate_limit("5 per minute")
def auth_login():
    """
    User login endpoint with rate limiting.
    Rate limit: 5 attempts per minute per IP address.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # Authenticate user
    user = user_manager.authenticate(username, password)
    
    # Create session
    session_token = user_manager.create_session(
        user,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    # Log login
    audit_logger.log_access(
        user_id=user.user_id,
        username=user.username,
        action=AuditAction.VIEW.value,
        document_id="auth:login",
        ip_address=request.remote_addr,
        session_id=session_token
    )
    
    return jsonify({
        "status": "ok",
        "session_token": session_token,
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "department": user.department,
            "clearance_level": user.clearance_level,
            "roles": user.roles,
            "email": user.email
        }
    })
```

**2. Logout Endpoint:**

```python
@app.route('/api/auth/logout', methods=['POST'])
@requires_auth
def auth_logout():
    """User logout endpoint."""
    user = request.user
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    
    # Invalidate session
    user_manager.invalidate_session(token)
    
    # Log logout
    audit_logger.log_access(
        user_id=user.user_id,
        username=user.username,
        action=AuditAction.VIEW.value,
        document_id="auth:logout",
        ip_address=request.remote_addr,
        metadata={"action": "logout"}
    )
    
    return jsonify({"status": "ok", "message": "Logged out successfully"})
```

**3. Current User Endpoint:**

```python
@app.route('/api/auth/me', methods=['GET'])
@requires_auth
def auth_me():
    """Get current user information."""
    user = request.user
    return jsonify({
        "status": "ok",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "department": user.department,
            "clearance_level": user.clearance_level,
            "roles": user.roles,
            "email": user.email
        }
    })
```

#### Protected Endpoints

All protected endpoints use the `@requires_auth` decorator:

```python
@app.route('/api/qc/queue/stats', methods=['GET'])
@requires_auth
def qc_queue_stats():
    """Get QC queue statistics."""
    # Endpoint logic...

@app.route('/api/archive/document/<page_id>', methods=['GET'])
@requires_auth
def get_archive_document(page_id):
    """Get archive document with ABAC check."""
    user = request.user
    
    # Check authorization
    doc = archive_manager.get_document(page_id)
    allowed = check_document_access(user, doc)
    
    if not allowed:
        audit_logger.log_access(
            user_id=user.user_id,
            username=user.username,
            action=AuditAction.VIEW.value,
            document_id=page_id,
            allowed=False,
            metadata={"reason": "Insufficient clearance"}
        )
        return jsonify({"error": "Access denied"}), 403
    
    # Return document...
```

---

## Security Features

### 1. Rate Limiting

**Configuration:**
- **Login endpoint**: 5 attempts per minute per IP
- **Default limits**: 200 requests per day, 50 per hour
- **Storage**: In-memory (for single-instance deployments)

**Response on Rate Limit:**
```json
{
  "error": "Too many login attempts. Please try again later.",
  "retry_after": 60
}
```

**HTTP Status**: `429 Too Many Requests`

**Headers Returned:**
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1234567890
Retry-After: 60
```

### 2. Session Management

**Session Properties:**
- **Duration**: 24 hours from creation
- **Storage**: SQLite database (`data/users.db`)
- **Token**: 32-character random hex string
- **Validation**: On every request with `@requires_auth`

**Session Table Schema:**
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

**Automatic Cleanup:**
Sessions are automatically invalidated after 24 hours. Expired sessions are cleaned up on validation attempts.

### 3. Audit Logging

**Logged Events:**
- ✅ Successful logins
- ✅ Failed login attempts
- ✅ Logouts
- ✅ Protected endpoint access
- ✅ Authorization failures (403)
- ✅ Document access (with ABAC decisions)

**Audit Log Schema:**
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    username TEXT,
    action TEXT NOT NULL,
    document_id TEXT,
    ip_address TEXT,
    session_id TEXT,
    user_agent TEXT,
    allowed BOOLEAN DEFAULT 1,
    metadata TEXT
);
```

**Retention**: 365 days (configurable)

### 4. Password Security

**Hashing:**
- Algorithm: SHA-256 with salt
- Salt: 32-character random hex per user
- Hash stored: `sha256(password + salt)`

**Default Admin Account:**
- Username: `admin`
- Password: `admin`
- ⚠️ **CHANGE IN PRODUCTION!**

### 5. HTTPS Enforcement (Production)

See `TLS_SSL_SETUP.md` for full guide.

**Quick Setup:**
```bash
# Development: Self-signed certificate
python dashboard_api.py --enable-ssl

# Production: Nginx + Let's Encrypt
sudo certbot --nginx -d yourdomain.com
```

---

## Testing Guide

### 1. Test Login Flow

```bash
# Test successful login
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Expected response:
{
  "status": "ok",
  "session_token": "abc123...",
  "user": {
    "user_id": "1",
    "username": "admin",
    "department": "IT",
    "clearance_level": 3,
    "roles": ["admin", "operator", "viewer"],
    "email": "admin@example.com"
  }
}

# Test invalid credentials
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrong"}'

# Expected: 401 Unauthorized
```

### 2. Test Rate Limiting

```powershell
# PowerShell: Try 6 login attempts in 1 minute
for ($i=1; $i -le 6; $i++) {
    Write-Host "Attempt $i"
    curl -X POST http://localhost:8080/api/auth/login `
      -H "Content-Type: application/json" `
      -d '{"username":"test","password":"test"}'
}

# Expected: First 5 succeed/fail normally, 6th returns 429
```

### 3. Test Protected Endpoints

```bash
# Without token (should fail)
curl http://localhost:8080/api/qc/queue/stats

# Expected: 401 Unauthorized

# With token (should succeed)
TOKEN="abc123..."
curl http://localhost:8080/api/qc/queue/stats \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with data
```

### 4. Test Session Validation

```bash
# Get current user
curl http://localhost:8080/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Expected: User object

# Test expired/invalid token
curl http://localhost:8080/api/auth/me \
  -H "Authorization: Bearer invalid_token"

# Expected: 401 Unauthorized
```

### 5. Test Logout

```bash
# Logout
curl -X POST http://localhost:8080/api/auth/logout \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK

# Try to use token again (should fail)
curl http://localhost:8080/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Expected: 401 Unauthorized
```

### 6. Test Frontend Flow (Browser)

1. **Navigate to http://localhost:8080/dashboard.html**
   - Should redirect to `/login.html`

2. **Enter credentials: admin / admin**
   - Should redirect to `/dashboard.html`
   - User info displayed in header
   - Dashboard data loads

3. **Click "Logout" button**
   - Should redirect to `/login.html`
   - localStorage cleared

4. **Try 6 login attempts with wrong password**
   - First 5: Show "Invalid username or password"
   - 6th attempt: Show "Too many login attempts. Please try again later."

---

## Troubleshooting

### Issue: Dashboard keeps redirecting to login

**Possible Causes:**
1. Session token expired (24 hours)
2. Token invalid/corrupted in localStorage
3. Backend API not running

**Solution:**
```javascript
// Check localStorage in browser console
console.log(localStorage.getItem('session_token'));
console.log(localStorage.getItem('user'));

// Clear and try again
localStorage.clear();
```

### Issue: Login returns 429 (Rate Limit)

**Cause:** More than 5 login attempts in 1 minute

**Solution:**
- Wait 60 seconds
- Or restart API server to clear in-memory limiter

```bash
# Check rate limit headers in response
curl -v -X POST http://localhost:8080/api/auth/login ...

# Headers:
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
Retry-After: 60
```

### Issue: Protected endpoints return 401

**Possible Causes:**
1. No Authorization header
2. Invalid token format
3. Token expired/invalidated

**Solution:**
```bash
# Check token format
echo "Bearer $TOKEN"
# Should be: Bearer abc123def456...

# Verify token in database
sqlite3 data/users.db "SELECT * FROM sessions WHERE session_id = '$TOKEN';"

# Check expiration
sqlite3 data/users.db "SELECT session_id, expires_at FROM sessions WHERE session_id = '$TOKEN';"
```

### Issue: Rate limiter not working

**Cause:** Flask-Limiter not installed or limiter is None

**Solution:**
```bash
# Install Flask-Limiter
pip install Flask-Limiter

# Check in dashboard_api.py
python -c "from dashboard_api import limiter; print(limiter is not None)"
```

### Issue: CORS errors in browser

**Cause:** Frontend served from different origin than API

**Solution:**
Add CORS headers in `dashboard_api.py`:

```python
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

---

## Default Credentials

**⚠️ IMPORTANT: Change in production!**

| Username | Password | Clearance | Roles | Department |
|----------|----------|-----------|-------|------------|
| `admin` | `admin` | 3 (Confidential) | admin, operator, viewer | IT |

**To create new users:**

```python
from src.authorization import UserManager

user_manager = UserManager()
user_manager.create_user(
    username="operator1",
    password="secure_password",
    department="Operations",
    clearance_level=2,
    roles=["operator", "viewer"],
    email="operator1@example.com"
)
```

---

## API Reference

### Authentication Endpoints

#### `POST /api/auth/login`

**Rate Limit**: 5 per minute per IP

**Request:**
```json
{
  "username": "admin",
  "password": "admin"
}
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "session_token": "abc123def456...",
  "user": {
    "user_id": "1",
    "username": "admin",
    "department": "IT",
    "clearance_level": 3,
    "roles": ["admin", "operator", "viewer"],
    "email": "admin@example.com"
  }
}
```

**Errors:**
- `400`: Missing username/password
- `401`: Invalid credentials
- `429`: Too many attempts (rate limit)
- `503`: Authorization module not available

---

#### `POST /api/auth/logout`

**Requires**: Bearer token in Authorization header

**Request:**
```
Authorization: Bearer abc123def456...
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "message": "Logged out successfully"
}
```

**Errors:**
- `401`: No token or invalid token

---

#### `GET /api/auth/me`

**Requires**: Bearer token in Authorization header

**Request:**
```
Authorization: Bearer abc123def456...
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "user": {
    "user_id": "1",
    "username": "admin",
    "department": "IT",
    "clearance_level": 3,
    "roles": ["admin", "operator", "viewer"],
    "email": "admin@example.com"
  }
}
```

**Errors:**
- `401`: No token or invalid token

---

## Summary

**✅ Completed Features:**
1. **Login Page**: Modern UI, client-side validation, error handling
2. **Dashboard Auth**: Auto-redirect, user display, logout button
3. **Rate Limiting**: 5 login attempts per minute
4. **Session Management**: 24-hour tokens, automatic validation
5. **Audit Logging**: All auth events logged to database
6. **Bearer Token Auth**: Automatic injection in all API requests

**📋 Next Steps:**
1. Change default admin password in production
2. Set up HTTPS with TLS/SSL (see `TLS_SSL_SETUP.md`)
3. Configure Nginx reverse proxy for production
4. Set up automated certificate renewal
5. Monitor audit logs for security events

**📚 Related Documentation:**
- `TLS_SSL_SETUP.md` - Production HTTPS configuration
- `AUTHORIZATION_LAYER.md` - Backend authorization system
- `QUICKREF.md` - Quick reference for all features
