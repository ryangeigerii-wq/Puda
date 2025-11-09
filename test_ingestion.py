"""Tests for ingestion layer (basic functionality)

NOTE: Lightweight tests focusing on version increments and integrity logic.
"""
from src.ingestion.ingestion import IngestionManager


def test_capture_and_version_increment():
    mgr = IngestionManager()
    v1 = mgr.capture_page("PAPER-1", 1, b"hello world", "path/to/file1")
    v2 = mgr.capture_page("PAPER-1", 1, b"hello world again", "path/to/file2")
    assert v1.version == 1
    assert v2.version == 2
    latest = mgr.get_latest_version("PAPER-1", 1)
    assert latest is not None and latest.version == 2


def test_audit_trail_and_stats():
    mgr = IngestionManager()
    mgr.capture_page("PAPER-2", 1, b"a", "ref/a")
    mgr.capture_page("PAPER-2", 2, b"b", "ref/b")
    mgr.capture_page("PAPER-2", 2, b"b2", "ref/b2")
    trail = mgr.audit_trail("PAPER-2")
    assert trail == [
        {'page_number': 1, 'latest_version': 1},
        {'page_number': 2, 'latest_version': 2},
    ]
    stats = mgr.stats()
    assert stats['total_pages'] == 2
    assert stats['total_versions'] == 3
