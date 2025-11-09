"""Tests for staging storage abstraction."""
import tempfile
from pathlib import Path

from src.staging.staging import StagingStore


def test_stage_and_export_and_purge():
    with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as staging_dir:
        src_root = Path(tmpdir)
        staging = StagingStore(root=staging_dir, max_bytes=5_000_000, retention_hours=0)  # immediate purge eligibility after export
        f = src_root / "sample.bin"
        f.write_bytes(b"data123")
        staged = staging.stage_file(str(f), batch_id="BATCH-1", notes="test file")
        assert staged.file_id in staging._files
        assert staging.stats()['active_files'] == 1
        staging.mark_exported(staged.file_id)
        purged = staging.purge_old()
        assert staged.file_id in purged
        assert staging.stats()['purged_files'] == 1


def test_capacity_enforcement():
    with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as staging_dir:
        src_root = Path(tmpdir)
        staging = StagingStore(root=staging_dir, max_bytes=10)  # very small capacity
        small = src_root / "small.bin"
        small.write_bytes(b"12345")
        staging.stage_file(str(small))
        large = src_root / "large.bin"
        large.write_bytes(b"x" * 100)
        try:
            staging.stage_file(str(large))
            assert False, "Expected capacity error"
        except RuntimeError:
            pass
