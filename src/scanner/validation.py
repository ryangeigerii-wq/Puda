"""File validation utilities.

Features:
- Checksum (SHA256) computation
- Page count extraction for PDF (optional dependency)
- Duplicate detection within a validation session

Design:
- Stateless helper functions plus a FileValidator class maintaining seen hashes.
- Duplicate detection is hash-based (exact content match).
- Page count is best-effort: only for PDFs if PyPDF2 available.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict
import hashlib
import os

try:  # optional PDF support
    import PyPDF2  # type: ignore
except Exception:  # pragma: no cover
    PyPDF2 = None  # type: ignore


@dataclass
class FileValidationResult:
    path: str
    sha256: str
    page_count: Optional[int]
    is_duplicate: bool
    error: Optional[str] = None


class FileValidator:
    def __init__(self):
        self._seen_hashes: Dict[str, int] = {}

    def _compute_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _pdf_page_count(self, data: bytes) -> Optional[int]:
        if PyPDF2 is None:
            return None
        try:
            from io import BytesIO
            reader = PyPDF2.PdfReader(BytesIO(data))  # type: ignore
            return len(reader.pages)
        except Exception:
            return None

    def validate(self, path: str) -> FileValidationResult:
        if not os.path.isfile(path):
            return FileValidationResult(path=path, sha256="", page_count=None, is_duplicate=False, error="not_found")
        try:
            data = open(path, "rb").read()
        except OSError as e:
            return FileValidationResult(path=path, sha256="", page_count=None, is_duplicate=False, error=str(e))
        sha256 = self._compute_hash(data)
        ext = os.path.splitext(path)[1].lower()
        page_count = None
        if ext == ".pdf":
            page_count = self._pdf_page_count(data)
        prior = self._seen_hashes.get(sha256, 0)
        is_duplicate = prior > 0
        self._seen_hashes[sha256] = prior + 1
        return FileValidationResult(path=path, sha256=sha256, page_count=page_count, is_duplicate=is_duplicate)

    def seen_hashes(self) -> int:
        return len(self._seen_hashes)
