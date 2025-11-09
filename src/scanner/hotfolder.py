"""Hot Folder Scanner Placeholder

Purpose:
    Simulate external scanner software that drops image/PDF files into a
    designated "hot" folder which we monitor. Real implementation would
    integrate with vendor SDKs or OS-level file system events.

Current Capabilities:
    - Poll a directory for new files matching allowed extensions.
    - Generate a logical paper/page identity.
    - Hand off bytes to the ingestion layer.

Usage (placeholder):
    from src.scanner.hotfolder import HotFolderWatcher
    from src.ingestion.ingestion import IngestionManager

    ingestion = IngestionManager()
    watcher = HotFolderWatcher(path="./_hot", ingestion=ingestion)
    watcher.scan_once()  # or watcher.run(interval=2.0)

Notes:
    This is synchronous and not optimized. Replace with watchdog / async
    implementation for production.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import List, Set, Optional, Callable
import hashlib
import uuid
from pathlib import Path

from src.ingestion.ingestion import IngestionManager
from src.scanner.validation import FileValidator
from src.staging.staging import StagingStore

ALLOWED_EXTENSIONS: Set[str] = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".pdf"}


@dataclass
class HotFolderWatcher:
    path: str
    ingestion: IngestionManager
    processed: Set[str] = field(default_factory=set)
    allowed_extensions: Set[str] = field(default_factory=lambda: ALLOWED_EXTENSIONS)
    operator_id_provider: Callable[[], Optional[str]] = lambda: None
    validator: FileValidator = field(default_factory=FileValidator)
    staging: Optional[StagingStore] = None  # if provided, files are copied into staging first

    def _hash_bytes(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _rename_with_hash(self, entry: Path, sha256: str) -> Path:
        new_name = f"{entry.stem}__{sha256[:12]}{entry.suffix.lower()}"
        new_path = entry.with_name(new_name)
        try:
            entry.rename(new_path)
            return new_path
        except OSError:
            return entry  # Fallback: keep original

    def scan_once(self, batch_id: Optional[str] = None) -> List[str]:
        """Scan folder once for new files, ingest them, return list of ingested file paths.

        Args:
            batch_id: Optional external batch identifier; auto-generated if absent.
        """
        ingested: List[str] = []
        folder = Path(self.path)
        if not folder.exists():
            return ingested
        batch_id = batch_id or f"BATCH-{uuid.uuid4().hex[:8]}"
        operator_id = self.operator_id_provider() or "UNKNOWN"
        for entry in folder.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in self.allowed_extensions:
                continue
            if entry.name in self.processed:
                continue
            try:
                content = entry.read_bytes()
            except OSError:
                continue
            # Validate file (hash + potential page count + duplicate detection)
            validation = self.validator.validate(str(entry))
            sha256 = validation.sha256
            renamed_path = self._rename_with_hash(entry, sha256)
            original_filename = entry.name if renamed_path.name != entry.name else None
            paper_id, page_number = self._derive_identity(entry.stem)
            # Stage file if staging store is provided
            storage_ref = str(renamed_path)
            if self.staging is not None:
                staged = self.staging.stage_file(str(renamed_path), batch_id=batch_id, notes="hotfolder staged")
                storage_ref = str(staged.stored_path)
            self.ingestion.capture_page(
                paper_id,
                page_number,
                content,
                storage_ref,
                batch_id=batch_id,
                operator_id=operator_id,
                original_filename=original_filename,
                page_count=validation.page_count,
                is_duplicate=validation.is_duplicate,
                notes=f"ingested from hotfolder; sha256={sha256[:12]} duplicate={validation.is_duplicate}"
            )
            self.processed.add(renamed_path.name)
            ingested.append(str(renamed_path))
        return ingested

    def run(self, interval: float = 1.0, stop_after: Optional[int] = None, batch_id: Optional[str] = None) -> None:
        """Continuously poll at interval seconds. Optional stop_after loop count for testing.

        Each run cycle reuses provided batch_id or creates one per invocation.
        """
        loops = 0
        while True:
            self.scan_once(batch_id=batch_id)
            loops += 1
            if stop_after is not None and loops >= stop_after:
                break
            time.sleep(interval)

    @staticmethod
    def _derive_identity(stem: str) -> tuple[str, int]:
        """Parse file stem to (paper_id, page_number). Fallbacks if pattern missing.

        Expected pattern: PAPER-XYZ_p12 -> paper_id=PAPER-XYZ, page_number=12
        """
        if "_p" in stem:
            base, page = stem.rsplit("_p", 1)
            if page.isdigit():
                return base, int(page)
        # Fallback: entire stem as paper id, page=1 always increments versions
        return stem, 1
