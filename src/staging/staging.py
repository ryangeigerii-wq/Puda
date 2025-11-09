"""Temporary Staging Storage Abstraction

Purpose:
    Provide a fast intermediate landing zone (SSD or NAS) for newly scanned
    artifacts prior to AI pipeline pickup. Handles capacity management,
    lifecycle state (ready/exported/purged), and optional retention policy.

Design:
    - StagedFile: metadata about a stored file.
    - StagingStore: orchestrates file placement, indexing, and housekeeping.

Future Enhancements:
    - Persistent index (SQLite) for crash resilience.
    - Tiered storage migration (SSD -> NAS -> Archive).
    - Async export hooks to AI pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import shutil
import uuid


@dataclass
class StagedFile:
    file_id: str
    original_name: str
    stored_path: Path
    size_bytes: int
    added_at: datetime
    exported_at: Optional[datetime] = None
    purged_at: Optional[datetime] = None
    batch_id: Optional[str] = None
    notes: str = ""

    @property
    def is_exported(self) -> bool:
        return self.exported_at is not None

    @property
    def is_purged(self) -> bool:
        return self.purged_at is not None

    @property
    def age_seconds(self) -> float:
        return (datetime.utcnow() - self.added_at).total_seconds()


class StagingStore:
    def __init__(self, root: str, max_bytes: int = 10 * 1024 * 1024 * 1024, retention_hours: int = 24):
        self.root = Path(root)
        self.max_bytes = max_bytes
        self.retention = timedelta(hours=retention_hours)
        self.root.mkdir(parents=True, exist_ok=True)
        self._files: Dict[str, StagedFile] = {}
        self._current_bytes: int = 0

    # ---------------- Capacity & Stats -----------------
    def stats(self) -> Dict[str, int]:
        return {
            'total_files': len(self._files),
            'active_files': len([f for f in self._files.values() if not f.is_purged]),
            'exported_files': len([f for f in self._files.values() if f.is_exported]),
            'purged_files': len([f for f in self._files.values() if f.is_purged]),
            'used_bytes': self._current_bytes,
            'max_bytes': self.max_bytes,
            'available_bytes': max(self.max_bytes - self._current_bytes, 0),
        }

    def _ensure_capacity(self, size: int) -> bool:
        return (self._current_bytes + size) <= self.max_bytes

    # ---------------- Core Operations ------------------
    def stage_file(self, source_path: str, *, batch_id: Optional[str] = None, notes: str = "") -> StagedFile:
        src = Path(source_path)
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Source path missing: {source_path}")
        size = src.stat().st_size
        if not self._ensure_capacity(size):
            raise RuntimeError("Staging capacity exceeded")
        file_id = uuid.uuid4().hex[:16]
        target_name = f"{file_id}_{src.name}"
        target_path = self.root / target_name
        shutil.copy2(src, target_path)
        staged = StagedFile(
            file_id=file_id,
            original_name=src.name,
            stored_path=target_path,
            size_bytes=size,
            added_at=datetime.utcnow(),
            batch_id=batch_id,
            notes=notes,
        )
        self._files[file_id] = staged
        self._current_bytes += size
        return staged

    def list_ready(self) -> List[StagedFile]:
        return [f for f in self._files.values() if not f.is_exported and not f.is_purged]

    def mark_exported(self, file_id: str) -> StagedFile:
        staged = self._files.get(file_id)
        if staged is None:
            raise KeyError(file_id)
        if staged.is_purged:
            raise RuntimeError("Cannot export purged file")
        staged.exported_at = datetime.utcnow()
        return staged

    def purge_old(self) -> List[str]:
        purged: List[str] = []
        now = datetime.utcnow()
        for file_id, staged in list(self._files.items()):
            if staged.is_purged:
                continue
            if staged.exported_at and (now - staged.exported_at) > self.retention:
                try:
                    staged.stored_path.unlink(missing_ok=True)
                except Exception:
                    pass
                staged.purged_at = now
                self._current_bytes -= staged.size_bytes
                purged.append(file_id)
        return purged

    def get(self, file_id: str) -> Optional[StagedFile]:
        return self._files.get(file_id)

    def remove(self, file_id: str) -> bool:
        staged = self._files.get(file_id)
        if staged is None or staged.is_purged:
            return False
        try:
            staged.stored_path.unlink(missing_ok=True)
        except Exception:
            pass
        staged.purged_at = datetime.utcnow()
        self._current_bytes -= staged.size_bytes
        return True
