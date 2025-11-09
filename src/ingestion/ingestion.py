"""Ingestion module

Captures and versions every scanned page.

Design Goals:
- Immutable page versions
- Integrity verification via SHA256 hash
- Lightweight in-memory index (can be replaced with DB later)
- Clear API for capture, update (new version), retrieval, and audit trail

Core Concepts:
- PageCapture: Logical document page identity (paper_id + page_number)
- PageVersion: Specific version of the page with binary content reference
- IngestionManager: Orchestrates creation and versioning
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib


@dataclass(frozen=True)
class PageVersion:
    """A single immutable version of a page.

    Added metadata fields for batching and operational traceability.
    """
    version: int
    captured_at: datetime
    sha256: str
    storage_ref: str  # e.g., file path, object storage key
    batch_id: Optional[str] = None
    operator_id: Optional[str] = None
    original_filename: Optional[str] = None
    page_count: Optional[int] = None
    is_duplicate: bool = False
    ocr_text_ref: Optional[str] = None  # reference to OCR text artifact
    notes: str = ""


@dataclass
class PageCapture:
    """Represents a logical page that can have multiple versions."""
    paper_id: str
    page_number: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    versions: List[PageVersion] = field(default_factory=list)
    latest_version: Optional[PageVersion] = None

    def add_version(self, content_bytes: bytes, storage_ref: str, *, ocr_text_ref: Optional[str] = None,
                    notes: str = "", batch_id: Optional[str] = None, operator_id: Optional[str] = None,
                    original_filename: Optional[str] = None, page_count: Optional[int] = None,
                    is_duplicate: bool = False) -> PageVersion:
        """Add a new version for this page.

        Args:
            content_bytes: Raw binary content of the page (e.g., image/PDF bytes)
            storage_ref: Reference for stored binary content
            ocr_text_ref: Optional reference to OCR text content
            notes: Additional notes about this capture

        Returns:
            The created PageVersion instance
        """
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        version_number = (self.latest_version.version + 1) if self.latest_version else 1
        pv = PageVersion(
            version=version_number,
            captured_at=datetime.utcnow(),
            sha256=sha256,
            storage_ref=storage_ref,
            batch_id=batch_id,
            operator_id=operator_id,
            original_filename=original_filename,
            page_count=page_count,
            is_duplicate=is_duplicate,
            ocr_text_ref=ocr_text_ref,
            notes=notes,
        )
        self.versions.append(pv)
        self.latest_version = pv
        return pv

    def get_version(self, version: int) -> Optional[PageVersion]:
        """Retrieve a specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def verify_integrity(self, version: Optional[int] = None, content_bytes: Optional[bytes] = None) -> bool:
        """Verify stored hash matches provided content.

        Args:
            version: Version number to verify (defaults to latest)
            content_bytes: Raw bytes to hash and compare; if omitted returns True if version exists
        """
        target = self.latest_version if version is None else self.get_version(version)
        if target is None:
            return False
        if content_bytes is None:
            return True
        return hashlib.sha256(content_bytes).hexdigest() == target.sha256


class IngestionManager:
    """Coordinates page capture and versioning.

    This is intentionally in-memory for now. Replace internal dictionaries
    with persistent storage as needed (SQLite/PostgreSQL).
    """

    def __init__(self):
        self._pages: Dict[Tuple[str, int], PageCapture] = {}

    def capture_page(self, paper_id: str, page_number: int, content_bytes: bytes, storage_ref: str, *, ocr_text_ref: Optional[str] = None,
                     notes: str = "", batch_id: Optional[str] = None, operator_id: Optional[str] = None,
                     original_filename: Optional[str] = None, page_count: Optional[int] = None,
                     is_duplicate: bool = False) -> PageVersion:
        """Capture a page (creates PageCapture if first time, else adds new version).

        Supports operational metadata (batch_id, operator_id, original_filename).
        """
        key = (paper_id, page_number)
        if key not in self._pages:
            self._pages[key] = PageCapture(paper_id=paper_id, page_number=page_number)
        return self._pages[key].add_version(
            content_bytes,
            storage_ref,
            ocr_text_ref=ocr_text_ref,
            notes=notes,
            batch_id=batch_id,
            operator_id=operator_id,
            original_filename=original_filename,
            page_count=page_count,
            is_duplicate=is_duplicate,
        )

    def get_page(self, paper_id: str, page_number: int) -> Optional[PageCapture]:
        return self._pages.get((paper_id, page_number))

    def get_latest_version(self, paper_id: str, page_number: int) -> Optional[PageVersion]:
        pc = self.get_page(paper_id, page_number)
        return pc.latest_version if pc else None

    def list_pages_for_paper(self, paper_id: str) -> List[PageCapture]:
        return [pc for (pid, _), pc in self._pages.items() if pid == paper_id]

    def audit_trail(self, paper_id: str) -> List[Dict[str, int]]:
        """Produce a lightweight audit trail: page_number + latest version."""
        trail = []
        for (pid, page_num), capture in self._pages.items():
            if pid == paper_id:
                trail.append({
                    'page_number': page_num,
                    'latest_version': capture.latest_version.version if capture.latest_version else 0
                })
        return sorted(trail, key=lambda x: x['page_number'])

    def verify_all(self, paper_id: str) -> bool:
        """Verify integrity existence for all pages of a paper (doesn't rehash content)."""
        pages = self.list_pages_for_paper(paper_id)
        return all(p.latest_version is not None for p in pages)

    def stats(self) -> Dict[str, int]:
        """Basic statistics."""
        return {
            'total_pages': len(self._pages),
            'total_versions': sum(len(pc.versions) for pc in self._pages.values())
        }
