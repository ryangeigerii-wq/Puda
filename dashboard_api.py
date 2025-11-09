#!/usr/bin/env python3
"""
Routing Dashboard API Server

Purpose:
    Lightweight REST API for real-time monitoring of routing audit logs.
    Provides JSON endpoints for summary stats, doc type breakdowns, severity trends.

Endpoints:
    GET /api/routing/summary?days=7&doc_type=invoice&severity=qc
    GET /api/routing/recent?limit=50
    GET /api/health

Usage:
    python dashboard_api.py --port 8080 --audit-dir data
"""
import argparse
import json
import glob
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import Counter

try:
    from flask import Flask, jsonify, request, send_from_directory
    FLASK_AVAILABLE = True
except ImportError as e:
    FLASK_AVAILABLE = False
    print("Flask not installed. Install via: pip install flask")
    print(f"ImportError: {e}")
    exit(1)

try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError as e:
    CORS_AVAILABLE = False
    print("Warning: Flask-CORS not installed. Cross-origin requests disabled.")
    print(f"Detail: {e}")

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    LIMITER_AVAILABLE = True
except ImportError as e:
    LIMITER_AVAILABLE = False
    print("Warning: Flask-Limiter not installed. Rate limiting disabled.")
    print("Install via: pip install Flask-Limiter")
    print(f"Detail: {e}")

try:
    from src.qc.queue import QCQueue
    from src.qc.feedback import FeedbackCollector
    QC_AVAILABLE = True
except ImportError as e:
    QC_AVAILABLE = False
    print("Warning: QC modules not available")
    print(f"Detail: {e}")
except Exception as e:
    QC_AVAILABLE = False
    print("Error loading QC modules (non-import error).")
    traceback.print_exc()

try:
    from src.organization.archive import ArchiveManager
    from src.organization.indexer import ArchiveIndexer, SearchQuery
    from src.organization.pdf_merger import PDFMerger
    from src.organization.thumbnails import ThumbnailGenerator
    ORGANIZATION_AVAILABLE = True
except ImportError as e:
    ORGANIZATION_AVAILABLE = False
    print("Warning: Organization modules not available")
    print(f"Detail: {e}")
except Exception as e:
    ORGANIZATION_AVAILABLE = False
    print("Error loading Organization modules (non-import error).")
    traceback.print_exc()

try:
    from src.authorization import UserManager, PolicyEngine, AuditLogger, AuditAction
    from functools import wraps
    AUTHORIZATION_AVAILABLE = True
except ImportError as e:
    AUTHORIZATION_AVAILABLE = False
    print("Warning: Authorization modules not available")
    print(f"Detail: {e}")
except Exception:
    AUTHORIZATION_AVAILABLE = False
    print("Error loading Authorization modules (non-import error).")
    traceback.print_exc()

app = Flask(__name__, static_folder='static')

if CORS_AVAILABLE:
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=False
    )
else:
    print("CORS disabled: install flask-cors to allow cross-origin dashboard access.")

# Initialize rate limiter
limiter = None
if LIMITER_AVAILABLE:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
        headers_enabled=True
    )

# Global config (set at runtime)
AUDIT_DIR = Path("data")
qc_queue = None
feedback_collector = None
archive_manager = None
archive_indexer = None  # Will be created per-request
archive_indexer_db_path = None  # Store path instead
pdf_merger = None
thumbnail_generator = None
user_manager = None
policy_engine = None
audit_logger = None


def get_archive_indexer():
    """Get or create archive indexer for current thread."""
    global archive_indexer_db_path
    if not ORGANIZATION_AVAILABLE or not archive_indexer_db_path:
        return None
    # Create new connection for this thread
    from src.organization.indexer import ArchiveIndexer
    return ArchiveIndexer(archive_indexer_db_path)


def rate_limit(limit_string):
    """
    Decorator to apply rate limiting if available.
    
    Args:
        limit_string: Rate limit string (e.g., "5 per minute")
    """
    def decorator(f):
        if limiter:
            return limiter.limit(limit_string)(f)
        return f
    return decorator


def requires_auth(f):
    """Decorator to require authentication for endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTHORIZATION_AVAILABLE or not user_manager:
            # If authorization not available, allow access (backward compatibility)
            return f(*args, **kwargs)
        
        # Get session token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
        
        if not token:
            return jsonify({"error": "No authorization token provided"}), 401
        
        # Validate session
        try:
            user = user_manager.validate_session(token)
            request.user = user  # Attach user to request context
            
            # Log access attempt
            if audit_logger:
                audit_logger.log_access(
                    user_id=user.user_id,
                    username=user.username,
                    action=AuditAction.VIEW.value,
                    document_id=request.path,
                    ip_address=request.remote_addr,
                    session_id=token,
                    user_agent=request.headers.get('User-Agent'),
                    metadata={"method": request.method, "endpoint": request.endpoint}
                )
            
            return f(*args, **kwargs)
        except Exception as e:
            if audit_logger:
                audit_logger.log_access(
                    user_id="unknown",
                    username="unknown",
                    action=AuditAction.VIEW.value,
                    document_id=request.path,
                    allowed=False,
                    ip_address=request.remote_addr,
                    metadata={"error": str(e), "method": request.method}
                )
            return jsonify({"error": "Invalid or expired session", "detail": str(e)}), 401
    
    return decorated


def check_document_access(user, document):
    """Check if user has access to a document using ABAC policy."""
    if not AUTHORIZATION_AVAILABLE or not policy_engine:
        return True, "Authorization not enabled"
    
    user_context = {
        "user_id": user.user_id,
        "clearance_level": user.clearance_level,
        "department": user.department,
        "roles": user.roles
    }
    
    doc_context = {
        "confidentiality": document.get("confidentiality", 0),
        "department": document.get("department"),
        "owner_id": document.get("owner_id")
    }
    
    return policy_engine.check_access(user_context, doc_context)


def load_audit_entries(days: Optional[int] = None, pattern: str = "routing_audit_*.jsonl") -> List[Dict[str, Any]]:
    """Load audit entries from JSONL files, optionally filtered by date range."""
    entries = []
    cutoff = None
    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=days)
    
    files = sorted(AUDIT_DIR.glob(pattern))
    for fpath in files:
        try:
            with fpath.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if cutoff:
                        ts = datetime.fromisoformat(entry.get("timestamp", ""))
                        if ts < cutoff:
                            continue
                    entries.append(entry)
        except Exception:
            continue
    return entries


def compute_summary(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary statistics from audit entries."""
    if not entries:
        return {
            "total": 0,
            "severity": {},
            "routes": {},
            "doc_types": {},
            "operators": {},
            "avg_classification_confidence": None,
            "avg_field_confidence": None,
            "top_reasons": [],
        }
    
    total = len(entries)
    severity_counts = Counter(e.get("severity") for e in entries)
    route_counts = Counter(e.get("route") for e in entries)
    doc_type_counts = Counter(e.get("doc_type") for e in entries)
    operator_counts = Counter(e.get("operator_id") for e in entries)
    
    class_confs = [e.get("classification_confidence") for e in entries if e.get("classification_confidence") is not None]
    field_confs = [e.get("avg_field_confidence") for e in entries if e.get("avg_field_confidence") is not None]
    avg_class = sum(float(c) for c in class_confs) / len(class_confs) if class_confs else None  # type: ignore[arg-type]
    avg_field = sum(float(c) for c in field_confs) / len(field_confs) if field_confs else None  # type: ignore[arg-type]
    
    reason_counter: Counter = Counter()
    for e in entries:
        reasons = e.get("reasons", [])
        if isinstance(reasons, list):
            reason_counter.update(reasons)
    
    return {
        "total": total,
        "severity": dict(severity_counts),
        "routes": dict(route_counts),
        "doc_types": dict(doc_type_counts),
        "operators": dict(operator_counts),
        "avg_classification_confidence": round(avg_class, 4) if avg_class is not None else None,
        "avg_field_confidence": round(avg_field, 4) if avg_field is not None else None,
        "top_reasons": [{"reason": r, "count": c} for r, c in reason_counter.most_common(10)],
    }


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "routing_dashboard_api"})


# ==================== Authentication Endpoints ====================

@app.route('/api/auth/login', methods=['POST'])
@rate_limit("5 per minute")
def auth_login():
    """
    User login endpoint with rate limiting.
    Rate limit: 5 attempts per minute per IP address.
    
    JSON body:
        username (str): Username
        password (str): Password
    
    Returns:
        session_token (str): Session token for authentication
        user (dict): User information
    """
    if not AUTHORIZATION_AVAILABLE or not user_manager:
        return jsonify({"error": "Authorization not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    try:
        # Authenticate user
        user = user_manager.authenticate(username, password)
        
        # Create session
        session_token = user_manager.create_session(
            user,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Log login
        if audit_logger:
            audit_logger.log_access(
                user_id=user.user_id,
                username=user.username,
                action=AuditAction.VIEW.value,
                document_id="auth:login",
                ip_address=request.remote_addr,
                session_id=session_token,
                user_agent=request.headers.get('User-Agent'),
                metadata={"action": "login"}
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
    except Exception as e:
        # Log failed login attempt
        if audit_logger:
            audit_logger.log_access(
                user_id="unknown",
                username=username,
                action=AuditAction.VIEW.value,
                document_id="auth:login",
                allowed=False,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                metadata={"action": "login_failed", "error": str(e)}
            )
        return jsonify({"error": "Authentication failed", "detail": str(e)}), 401


@app.route('/api/auth/logout', methods=['POST'])
@requires_auth
def auth_logout():
    """
    User logout endpoint.
    
    Requires: Authorization header with Bearer token
    """
    user = getattr(request, 'user', None)
    
    if audit_logger and user:
        audit_logger.log_access(
            user_id=user.user_id,
            username=user.username,
            action=AuditAction.VIEW.value,
            document_id="auth:logout",
            ip_address=request.remote_addr,
            metadata={"action": "logout"}
        )
    
    # Session cleanup happens automatically via expiration
    # Could also manually invalidate session here if needed
    return jsonify({"status": "ok", "message": "Logged out successfully"})


@app.route('/api/auth/me', methods=['GET'])
@requires_auth
def auth_me():
    """
    Get current user information.
    
    Requires: Authorization header with Bearer token
    """
    user = request.user
    
    return jsonify({
        "status": "ok",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "department": user.department,
            "clearance_level": user.clearance_level,
            "roles": user.roles,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login
        }
    })


@app.route("/", methods=["GET"])
@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Serve the dashboard HTML page."""
    return send_from_directory(app.static_folder, "dashboard.html")

@app.route("/login.html", methods=["GET"])
@app.route("/login", methods=["GET"])
def login_page():
    """Serve the login page (compat aliases)."""
    # app.static_folder can be None if Flask was initialized without a static folder.
    # Fallback: serve from default 'static' directory relative to current file.
    static_dir = app.static_folder or str(Path(__file__).parent / 'static')
    return send_from_directory(static_dir, "login.html")


@app.route("/api/routing/summary", methods=["GET"])
def routing_summary():
    """
    Get summary statistics for routing audit logs.
    
    Query params:
        days (int): Filter to entries from last N days (default: 7)
        doc_type (str): Filter to specific document type
        severity (str): Filter to specific severity level (qc, manual)
        operator (str): Filter to specific operator ID
    """
    days = request.args.get("days", default=7, type=int)
    doc_type_filter = request.args.get("doc_type")
    severity_filter = request.args.get("severity")
    operator_filter = request.args.get("operator")
    
    entries = load_audit_entries(days=days)
    
    # Apply filters
    if doc_type_filter:
        entries = [e for e in entries if e.get("doc_type") == doc_type_filter]
    if severity_filter:
        entries = [e for e in entries if e.get("severity") == severity_filter]
    if operator_filter:
        entries = [e for e in entries if e.get("operator_id") == operator_filter]
    
    summary = compute_summary(entries)
    summary["query"] = {
        "days": days,
        "doc_type_filter": doc_type_filter,
        "severity_filter": severity_filter,
        "operator_filter": operator_filter,
    }
    return jsonify(summary)


@app.route("/api/routing/recent", methods=["GET"])
def routing_recent():
    """
    Get most recent routing decisions.
    
    Query params:
        limit (int): Max number of entries to return (default: 50, max: 500)
    """
    limit = request.args.get("limit", default=50, type=int)
    limit = min(limit, 500)
    
    entries = load_audit_entries()
    # Sort by timestamp descending
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return jsonify({"count": len(entries[:limit]), "entries": entries[:limit]})


@app.route("/api/routing/trends", methods=["GET"])
def routing_trends():
    """
    Get daily routing trends over time.
    
    Query params:
        days (int): Number of days to analyze (default: 30)
    """
    days = request.args.get("days", default=30, type=int)
    entries = load_audit_entries(days=days)
    
    # Group by date
    daily_stats: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        ts = e.get("timestamp", "")
        date = ts.split("T")[0] if "T" in ts else ts[:10]
        if date not in daily_stats:
            daily_stats[date] = {"total": 0, "qc": 0, "manual": 0, "auto": 0}
        daily_stats[date]["total"] += 1
        severity = e.get("severity", "auto")
        if severity in daily_stats[date]:
            daily_stats[date][severity] += 1
    
    # Convert to sorted list
    trend_data = [{"date": k, **v} for k, v in sorted(daily_stats.items())]
    return jsonify({"days": days, "trends": trend_data})


@app.route('/api/qc/queue/stats')
@requires_auth
def qc_queue_stats():
    """Get QC queue statistics."""
    if not QC_AVAILABLE or not qc_queue:
        return jsonify({"error": "QC not available"}), 503
    
    stats = qc_queue.get_queue_stats()
    return jsonify({
        "status": "ok",
        "queue_stats": stats
    })


@app.route('/api/qc/queue/pending')
@requires_auth
def qc_pending_tasks():
    """Get pending QC tasks."""
    if not QC_AVAILABLE or not qc_queue:
        return jsonify({"error": "QC not available"}), 503
    
    severity = request.args.get("severity")
    doc_type = request.args.get("doc_type")
    limit = int(request.args.get("limit", 20))
    
    tasks = qc_queue.get_pending_tasks(
        severity=severity,
        doc_type=doc_type,
        limit=limit
    )
    
    return jsonify({
        "status": "ok",
        "count": len(tasks),
        "tasks": [
            {
                "task_id": t.task_id,
                "page_id": t.page_id,
                "doc_type": t.doc_type,
                "severity": t.severity,
                "priority": t.priority.name,
                "status": t.status.value,
                "created_at": datetime.fromtimestamp(t.created_at).isoformat(),
                "assigned_to": t.assigned_to,
                "locked_by": t.locked_by,
            }
            for t in tasks
        ]
    })


@app.route('/api/qc/feedback/stats')
@requires_auth
def qc_feedback_stats():
    """Get QC feedback statistics."""
    if not QC_AVAILABLE or not feedback_collector:
        return jsonify({"error": "QC not available"}), 503
    
    days = int(request.args.get("days", 30))
    stats = feedback_collector.get_global_stats(days=days)
    
    return jsonify({
        "status": "ok",
        "period_days": days,
        "feedback_stats": stats
    })


@app.route('/api/qc/operator/<operator_id>/stats')
@requires_auth
def qc_operator_stats(operator_id: str):
    """Get operator performance statistics."""
    if not QC_AVAILABLE or not feedback_collector:
        return jsonify({"error": "QC not available"}), 503
    
    days = int(request.args.get("days", 30))
    stats = feedback_collector.get_operator_stats(operator_id, days=days)
    
    return jsonify({
        "status": "ok",
        "period_days": days,
        "operator_stats": stats
    })


# ==================== Archive / Organization Endpoints ====================

@app.route('/api/archive/stats', methods=['GET'])
@requires_auth
def archive_stats():
    """
    Get archive statistics.
    
    Query params:
        owner (str): Filter by owner
        doc_type (str): Filter by document type
        year (int): Filter by year
    """
    if not ORGANIZATION_AVAILABLE:
        return jsonify({"error": "Organization modules not available"}), 503
    
    indexer = get_archive_indexer()
    if not indexer:
        return jsonify({"error": "Archive indexer not available"}), 503
    
    owner = request.args.get("owner")
    doc_type = request.args.get("doc_type")
    year = request.args.get("year", type=int)
    
    try:
        stats = indexer.get_statistics()
        
        # Apply filters if provided
        filtered_stats = {
            'total_documents': stats['total_documents'],
            'by_owner': stats['by_owner'],
            'by_year': stats['by_year'],
            'by_doc_type': stats['by_doc_type'],
            'by_qc_status': stats.get('by_qc_status', {})
        }
        
        # Filter by parameters if specified
        if owner:
            filtered_stats['by_owner'] = {owner: stats['by_owner'].get(owner, 0)}
        if doc_type:
            filtered_stats['by_doc_type'] = {doc_type: stats['by_doc_type'].get(doc_type, 0)}
        if year:
            year_str = str(year)
            filtered_stats['by_year'] = {year_str: stats['by_year'].get(year_str, 0)}
        
        indexer.close()
        
        return jsonify({
            "status": "ok",
            "statistics": filtered_stats
        })
    except Exception as e:
        if indexer:
            indexer.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive/search', methods=['GET'])
@requires_auth
def archive_search():
    """
    Search archived documents.
    
    Query params:
        text (str): Full-text search query
        owner (str): Filter by owner
        doc_type (str): Filter by document type
        year (int): Filter by year
        qc_status (str): Filter by QC status
        has_ocr (bool): Filter by OCR presence
        min_confidence (float): Minimum classification confidence
        limit (int): Max results (default: 50, max: 500)
        offset (int): Results offset for pagination
    """
    if not ORGANIZATION_AVAILABLE:
        return jsonify({"error": "Organization modules not available"}), 503
    
    indexer = get_archive_indexer()
    if not indexer:
        return jsonify({"error": "Archive indexer not available"}), 503
    
    # Build search query
    from src.organization.indexer import SearchQuery
    query = SearchQuery(
        text_search=request.args.get("text"),
        owner=request.args.get("owner"),
        doc_type=request.args.get("doc_type"),
        year=request.args.get("year"),
        qc_status=request.args.get("qc_status"),
        limit=min(int(request.args.get("limit", 50)), 500),
        offset=int(request.args.get("offset", 0))
    )
    
    try:
        results = indexer.search(query)
        indexer.close()
        
        return jsonify({
            "status": "ok",
            "query": {
                "text": query.text_search,
                "owner": query.owner,
                "doc_type": query.doc_type,
                "year": query.year,
                "qc_status": query.qc_status,
                "limit": query.limit,
                "offset": query.offset
            },
            "count": len(results),
            "results": results
        })
    except Exception as e:
        if indexer:
            indexer.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive/document/<page_id>', methods=['GET'])
@requires_auth
def archive_document(page_id: str):
    """Get detailed information about a specific archived document."""
    if not ORGANIZATION_AVAILABLE:
        return jsonify({"error": "Organization modules not available"}), 503
    
    indexer = get_archive_indexer()
    if not indexer:
        return jsonify({"error": "Archive indexer not available"}), 503
    
    try:
        # Search by page_id
        from src.organization.indexer import SearchQuery
        query = SearchQuery(text_search=page_id, limit=1)
        results = indexer.search(query)
        
        indexer.close()
        
        if not results:
            return jsonify({"error": "Document not found"}), 404
        
        doc = results[0]
        
        # Check access with ABAC
        user = getattr(request, 'user', None)
        if user and AUTHORIZATION_AVAILABLE:
            allowed, reason = check_document_access(user, doc)
            
            # Log access attempt
            if audit_logger:
                audit_logger.log_access(
                    user_id=user.user_id,
                    username=user.username,
                    action=AuditAction.VIEW.value,
                    document_id=page_id,
                    allowed=allowed,
                    ip_address=request.remote_addr,
                    metadata={"reason": reason, "doc_type": doc.get("doc_type")}
                )
            
            if not allowed:
                return jsonify({"error": "Access denied", "reason": reason}), 403
        
        return jsonify({
            "status": "ok",
            "document": doc
        })
    except Exception as e:
        if indexer:
            indexer.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive/thumbnail/<page_id>', methods=['GET'])
@requires_auth
def archive_thumbnail(page_id: str):
    """
    Get thumbnail for a document page.
    
    Query params:
        size (str): Thumbnail size (icon, small, medium, large) - default: small
    """
    if not ORGANIZATION_AVAILABLE or not thumbnail_generator:
        return jsonify({"error": "Organization modules not available"}), 503
    
    size = request.args.get("size", "small")
    if size not in ["icon", "small", "medium", "large"]:
        return jsonify({"error": f"Invalid size: {size}. Must be icon, small, medium, or large"}), 400
    
    try:
        # Get thumbnail path
        thumbnail_path = thumbnail_generator.get_thumbnail(page_id, size)
        
        if not thumbnail_path or not thumbnail_path.exists():
            return jsonify({"error": "Thumbnail not found"}), 404
        
        # Serve the thumbnail image
        return send_from_directory(thumbnail_path.parent, thumbnail_path.name, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive/thumbnail/cache/stats', methods=['GET'])
def archive_thumbnail_stats():
    """Get thumbnail cache statistics."""
    if not ORGANIZATION_AVAILABLE or not thumbnail_generator:
        return jsonify({"error": "Organization modules not available"}), 503
    
    try:
        stats = thumbnail_generator.get_cache_stats()
        
        return jsonify({
            "status": "ok",
            "cache_stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive/merge', methods=['POST'])
@requires_auth
def archive_merge():
    """
    Trigger PDF merge for a batch.
    
    JSON body:
        owner (str): Owner name
        year (int): Year
        doc_type (str): Document type
        batch_id (str): Batch ID
    """
    if not ORGANIZATION_AVAILABLE or not pdf_merger:
        return jsonify({"error": "Organization modules not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    owner = data.get("owner")
    year = data.get("year")
    doc_type = data.get("doc_type")
    batch_id = data.get("batch_id")
    
    if not all([owner, year, doc_type, batch_id]):
        return jsonify({"error": "Missing required fields: owner, year, doc_type, batch_id"}), 400
    
    try:
        pdf_path = pdf_merger.merge_batch(owner, str(year), doc_type, batch_id)
        
        # Count pages from batch folder
        batch_folder = Path("data/archive") / owner / str(year) / doc_type / batch_id
        page_count = len(list(batch_folder.glob("*.png"))) + len(list(batch_folder.glob("*.jpg")))
        
        # Check if metadata files exist
        metadata_json = pdf_path.parent / f"{pdf_path.stem}_metadata.json"
        metadata_csv = pdf_path.parent / f"{pdf_path.stem}_metadata.csv"
        metadata_written = metadata_json.exists() and metadata_csv.exists()
        
        return jsonify({
            "status": "ok",
            "result": {
                "pdf_path": str(pdf_path),
                "page_count": page_count,
                "metadata_written": metadata_written
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive/thumbnails/generate', methods=['POST'])
@requires_auth
def archive_thumbnails_generate():
    """
    Trigger thumbnail generation for a batch.
    
    JSON body:
        owner (str): Owner name
        year (int): Year
        doc_type (str): Document type
        batch_id (str): Batch ID
        force (bool): Force regeneration (default: false)
    """
    if not ORGANIZATION_AVAILABLE or not thumbnail_generator:
        return jsonify({"error": "Organization modules not available"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    owner = data.get("owner")
    year = data.get("year")
    doc_type = data.get("doc_type")
    batch_id = data.get("batch_id")
    force = data.get("force", False)
    
    if not all([owner, year, doc_type, batch_id]):
        return jsonify({"error": "Missing required fields: owner, year, doc_type, batch_id"}), 400
    
    try:
        # Build batch folder path
        archive_dir = Path("data/archive")
        # Navigate to batch folder: archive_dir / owner / year / doc_type / batch_id
        batch_folder = archive_dir / owner / str(year) / doc_type / batch_id
        
        if not batch_folder.exists():
            return jsonify({"error": f"Batch folder not found: {batch_folder}"}), 404
        
        result = thumbnail_generator.generate_batch_thumbnails(
            owner=owner,
            year=str(year),
            doc_type=doc_type,
            batch_id=batch_id,
            force_regenerate=force
        )
        
        return jsonify({
            "status": "ok",
            "result": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive/owners', methods=['GET'])
def archive_owners():
    """Get list of all owners in the archive."""
    if not ORGANIZATION_AVAILABLE:
        return jsonify({"error": "Organization modules not available"}), 503
    
    indexer = get_archive_indexer()
    if not indexer:
        return jsonify({"error": "Archive indexer not available"}), 503
    
    try:
        # Use statistics to get unique owners
        stats = indexer.get_statistics()
        owners = list(stats.get("by_owner", {}).keys())
        
        indexer.close()
        
        return jsonify({
            "status": "ok",
            "owners": sorted(owners)
        })
    except Exception as e:
        if indexer:
            indexer.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive/doc_types', methods=['GET'])
def archive_doc_types():
    """Get list of all document types in the archive."""
    if not ORGANIZATION_AVAILABLE:
        return jsonify({"error": "Organization modules not available"}), 503
    
    indexer = get_archive_indexer()
    if not indexer:
        return jsonify({"error": "Archive indexer not available"}), 503
    
    try:
        # Use statistics to get unique doc types
        stats = indexer.get_statistics()
        doc_types = list(stats.get("by_doc_type", {}).keys())
        
        indexer.close()
        
        return jsonify({
            "status": "ok",
            "doc_types": sorted(doc_types)
        })
    except Exception as e:
        if indexer:
            indexer.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/archive/years', methods=['GET'])
def archive_years():
    """Get list of all years in the archive."""
    if not ORGANIZATION_AVAILABLE:
        return jsonify({"error": "Organization modules not available"}), 503
    
    indexer = get_archive_indexer()
    if not indexer:
        return jsonify({"error": "Archive indexer not available"}), 503
    
    try:
        # Use statistics to get unique years
        stats = indexer.get_statistics()
        years = list(stats.get("by_year", {}).keys())
        
        indexer.close()
        
        return jsonify({
            "status": "ok",
            "years": sorted(years, reverse=True)
        })
    except Exception as e:
        if indexer:
            indexer.close()
        return jsonify({"error": str(e)}), 500


def main():
    parser = argparse.ArgumentParser(description="Routing Dashboard API Server")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--audit-dir", "-d", default="data", help="Directory containing audit JSONL files")
    parser.add_argument("--archive-dir", default="data/archive", help="Directory for document archive")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    # New safety/diagnostic flags to allow starting in minimal mode if optional subsystems crash
    parser.add_argument("--no-qc", action="store_true", help="Disable QC subsystem initialization")
    parser.add_argument("--no-org", action="store_true", help="Disable Organization/Archive subsystem initialization")
    parser.add_argument("--no-auth", action="store_true", help="Disable Authorization subsystem initialization")
    parser.add_argument("--minimal", action="store_true", help="Disable all optional subsystems (equivalent to --no-qc --no-org --no-auth)")
    parser.add_argument("--safe", action="store_true", help="Force safe startup (ignore exceptions in optional init and continue)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose diagnostic logging")
    args = parser.parse_args()
    
    global AUDIT_DIR, qc_queue, feedback_collector
    global archive_manager, archive_indexer_db_path, pdf_merger, thumbnail_generator
    global user_manager, policy_engine, audit_logger
    AUDIT_DIR = Path(args.audit_dir)
    
    if not AUDIT_DIR.exists():
        print(f"Warning: Audit directory {AUDIT_DIR} does not exist. Creating...")
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize QC components if available
    effective_no_qc = args.no_qc or args.minimal
    if QC_AVAILABLE and not effective_no_qc:
        try:
            qc_queue = QCQueue()
            feedback_collector = FeedbackCollector()
            print(f"[OK] QC modules loaded")
        except Exception as e:
            print(f"Warning: Could not initialize QC modules: {e}")
            if args.verbose:
                traceback.print_exc()
            if not args.safe:
                print("Use --safe or --no-qc to suppress this failure.")
                return
    elif effective_no_qc:
        print("[SKIP] QC subsystem disabled by flag")
    
    # Initialize Organization components if available
    effective_no_org = args.no_org or args.minimal
    if ORGANIZATION_AVAILABLE and not effective_no_org:
        try:
            archive_dir = Path(args.archive_dir)
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_manager = ArchiveManager(str(archive_dir))
            archive_indexer_db_path = "data/archive_index.db"
            pdf_merger = PDFMerger(str(archive_dir))
            thumbnail_generator = ThumbnailGenerator(str(archive_dir))
            print(f"[OK] Organization modules loaded")
            print(f"  Archive directory: {archive_dir.absolute()}")
        except Exception as e:
            print(f"Warning: Could not initialize Organization modules: {e}")
            if args.verbose:
                traceback.print_exc()
            if not args.safe:
                print("Use --safe or --no-org to suppress this failure.")
                return
    elif effective_no_org:
        print("[SKIP] Organization subsystem disabled by flag")
    
    # Initialize Authorization components if available
    effective_no_auth = args.no_auth or args.minimal
    if AUTHORIZATION_AVAILABLE and not effective_no_auth:
        try:
            from src.authorization import UserManager, PolicyEngine, AuditLogger
            data_dir = Path("data")
            data_dir.mkdir(parents=True, exist_ok=True)
            user_manager = UserManager(str(data_dir / "users.db"))
            policy_engine = PolicyEngine()
            audit_logger = AuditLogger(str(data_dir / "audit_log.db"))
            print(f"[OK] Authorization modules loaded")
            print(f"  User database: {data_dir / 'users.db'}")
            print(f"  Audit log: {data_dir / 'audit_log.db'}")
            print(f"  Default admin credentials: admin:admin")
        except Exception as e:
            print(f"Warning: Could not initialize Authorization modules: {e}")
            if args.verbose:
                traceback.print_exc()
            if not args.safe:
                print("Use --safe or --no-auth to suppress this failure.")
                return
    elif effective_no_auth:
        print("[SKIP] Authorization subsystem disabled by flag")
    
    print(f"Starting Routing Dashboard API on {args.host}:{args.port}")
    print(f"Audit log directory: {AUDIT_DIR.absolute()}")
    print(f"Endpoints:")
    print(f"  Dashboard UI: http://{args.host}:{args.port}/")
    print(f"  Health: http://{args.host}:{args.port}/api/health")
    print(f"  Routing Summary: http://{args.host}:{args.port}/api/routing/summary?days=7")
    print(f"  Routing Recent: http://{args.host}:{args.port}/api/routing/recent?limit=50")
    print(f"  Routing Trends: http://{args.host}:{args.port}/api/routing/trends?days=30")
    if QC_AVAILABLE:
        print(f"  QC Queue Stats: http://{args.host}:{args.port}/api/qc/queue/stats")
        print(f"  QC Pending Tasks: http://{args.host}:{args.port}/api/qc/queue/pending")
        print(f"  QC Feedback Stats: http://{args.host}:{args.port}/api/qc/feedback/stats")
        print(f"  QC Operator Stats: http://{args.host}:{args.port}/api/qc/operator/<id>/stats")
    if ORGANIZATION_AVAILABLE:
        print(f"  Archive Stats: http://{args.host}:{args.port}/api/archive/stats")
        print(f"  Archive Search: http://{args.host}:{args.port}/api/archive/search?text=invoice")
        print(f"  Archive Document: http://{args.host}:{args.port}/api/archive/document/<page_id>")
        print(f"  Archive Thumbnail: http://{args.host}:{args.port}/api/archive/thumbnail/<page_id>?size=small")
        print(f"  Archive Owners: http://{args.host}:{args.port}/api/archive/owners")
        print(f"  Archive Doc Types: http://{args.host}:{args.port}/api/archive/doc_types")
        print(f"  Archive Years: http://{args.host}:{args.port}/api/archive/years")
        print(f"  Archive Merge (POST): http://{args.host}:{args.port}/api/archive/merge")
        print(f"  Archive Thumbnails (POST): http://{args.host}:{args.port}/api/archive/thumbnails/generate")
        print(f"  Thumbnail Stats: http://{args.host}:{args.port}/api/archive/thumbnail/cache/stats")
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        print(f"Fatal error starting Flask server: {e}")
        if args.verbose:
            traceback.print_exc()
        if not args.safe:
            raise
        print("Continuing under --safe; server not started.")


if __name__ == "__main__":
    main()

