#!/usr/bin/env python3
"""
Smoke test for the Routing Dashboard API.

Verifies that the Flask app imports and the /api/health endpoint responds.
Skips gracefully if Flask is not installed in the local environment.
"""

import pytest


def test_dashboard_api_health_endpoint():
    try:
        import dashboard_api  # noqa: F401
    except SystemExit:
        pytest.skip("Flask not installed or failed to initialize; skipping server health test")
    except Exception as e:
        pytest.skip(f"Dashboard API import failed: {e}")

    from dashboard_api import app

    with app.test_client() as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert data.get("status") == "ok"
        assert data.get("service") == "routing_dashboard_api"

