import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta

# Mock Flask if not installed for testing purposes
try:
    from dashboard_api import app, load_audit_entries, compute_summary, AUDIT_DIR
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Flask not installed")


def create_sample_audit_log(tmp_path: Path, filename: str, entries: list) -> Path:
    """Helper to create sample audit JSONL file."""
    log_path = tmp_path / filename
    with log_path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return log_path


@pytest.fixture
def sample_logs(tmp_path, monkeypatch):
    """Create sample audit logs for testing."""
    if not FLASK_AVAILABLE:
        return
    # Mock AUDIT_DIR to tmp_path
    import dashboard_api
    monkeypatch.setattr(dashboard_api, "AUDIT_DIR", tmp_path)
    
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    
    # Today's log
    today_entries = [
        {
            "timestamp": now.isoformat(),
            "page_id": "p1",
            "batch_id": "b1",
            "operator_id": "op1",
            "route": "qc_queue",
            "severity": "qc",
            "doc_type": "invoice",
            "classification_confidence": 0.5,
            "avg_field_confidence": 0.6,
            "reasons": ["classification_conf_low:0.5"],
        },
        {
            "timestamp": now.isoformat(),
            "page_id": "p2",
            "batch_id": "b1",
            "operator_id": "op2",
            "route": "manual_review",
            "severity": "manual",
            "doc_type": "unknown",
            "classification_confidence": 0.3,
            "avg_field_confidence": None,
            "reasons": ["doc_type_unknown"],
        },
    ]
    create_sample_audit_log(tmp_path, f"routing_audit_{now.strftime('%Y-%m-%d')}.jsonl", today_entries)
    
    # Yesterday's log
    yesterday_entries = [
        {
            "timestamp": yesterday.isoformat(),
            "page_id": "p3",
            "batch_id": "b2",
            "operator_id": "op1",
            "route": "qc_queue",
            "severity": "qc",
            "doc_type": "invoice",
            "classification_confidence": 0.48,
            "avg_field_confidence": 0.55,
            "reasons": ["field_conf_low:0.55"],
        },
    ]
    create_sample_audit_log(tmp_path, f"routing_audit_{yesterday.strftime('%Y-%m-%d')}.jsonl", yesterday_entries)
    
    return tmp_path


@pytest.mark.skipif(not FLASK_AVAILABLE, reason="Flask not installed")
def test_health_endpoint(sample_logs):
    """Test /api/health endpoint."""
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["service"] == "routing_dashboard_api"


@pytest.mark.skipif(not FLASK_AVAILABLE, reason="Flask not installed")
def test_summary_endpoint(sample_logs):
    """Test /api/routing/summary endpoint."""
    client = app.test_client()
    response = client.get("/api/routing/summary?days=2")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 3
    assert data["severity"]["qc"] == 2
    assert data["severity"]["manual"] == 1
    assert data["doc_types"]["invoice"] == 2
    assert data["doc_types"]["unknown"] == 1
    assert data["avg_classification_confidence"] is not None


@pytest.mark.skipif(not FLASK_AVAILABLE, reason="Flask not installed")
def test_summary_with_filters(sample_logs):
    """Test /api/routing/summary with filters."""
    client = app.test_client()
    response = client.get("/api/routing/summary?days=2&doc_type=invoice")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 2
    assert all(dt == "invoice" for dt in data["doc_types"].keys())


@pytest.mark.skipif(not FLASK_AVAILABLE, reason="Flask not installed")
def test_recent_endpoint(sample_logs):
    """Test /api/routing/recent endpoint."""
    client = app.test_client()
    response = client.get("/api/routing/recent?limit=10")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] <= 10
    assert len(data["entries"]) <= 10
    # Entries should be sorted by timestamp descending
    if len(data["entries"]) > 1:
        ts1 = data["entries"][0]["timestamp"]
        ts2 = data["entries"][1]["timestamp"]
        assert ts1 >= ts2


@pytest.mark.skipif(not FLASK_AVAILABLE, reason="Flask not installed")
def test_trends_endpoint(sample_logs):
    """Test /api/routing/trends endpoint."""
    client = app.test_client()
    response = client.get("/api/routing/trends?days=7")
    assert response.status_code == 200
    data = response.get_json()
    assert "trends" in data
    assert isinstance(data["trends"], list)
    # Should have entries for today and yesterday
    assert len(data["trends"]) == 2
    for trend in data["trends"]:
        assert "date" in trend
        assert "total" in trend
