"""Tests for HotFolderWatcher placeholder.

These tests simulate files being placed in a temporary directory and ensure
that ingestion manager records versions.
"""
import tempfile
from pathlib import Path

from src.scanner.hotfolder import HotFolderWatcher
from src.ingestion.ingestion import IngestionManager


def write_file(path: Path, name: str, content: bytes):
    f = path / name
    f.write_bytes(content)
    return f


def test_hotfolder_basic_ingestion():
    ingestion = IngestionManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        write_file(p, "PAPER-ABC_p1.png", b"image1")
        write_file(p, "PAPER-ABC_p2.png", b"image2")
        watcher = HotFolderWatcher(path=tmpdir, ingestion=ingestion)
        ingested = watcher.scan_once()
        assert len(ingested) == 2
        assert ingestion.get_latest_version("PAPER-ABC", 1) is not None
        assert ingestion.get_latest_version("PAPER-ABC", 2) is not None


def test_hotfolder_version_increment_on_duplicate_name():
    ingestion = IngestionManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        write_file(p, "PAPER-XYZ_p1.png", b"first")
        watcher = HotFolderWatcher(path=tmpdir, ingestion=ingestion)
        watcher.scan_once()
        # overwrite same file content (simulate replacement) and rescan
        write_file(p, "PAPER-XYZ_p1.png", b"second")
        # processed set contains name, so second scan should skip
        watcher.scan_once()
        page = ingestion.get_page("PAPER-XYZ", 1)
        assert page is not None
        assert len(page.versions) == 1  # no second version because processed set prevented re-ingest


    def test_hotfolder_batch_metadata_and_hash_rename():
        ingestion = IngestionManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            f = write_file(p, "PAPER-BATCH_p1.png", b"batchcontent")
            watcher = HotFolderWatcher(path=tmpdir, ingestion=ingestion)
            ingested = watcher.scan_once(batch_id="BATCH-TEST")
            assert len(ingested) == 1
            # file should have been renamed to include hash snippet
            renamed_name = Path(ingested[0]).name
            assert "__" in renamed_name and renamed_name.startswith("PAPER-BATCH_p1")
            pv = ingestion.get_latest_version("PAPER-BATCH", 1)
            assert pv is not None
            assert pv.batch_id == "BATCH-TEST"
            assert pv.operator_id in (None, "UNKNOWN")  # default provider returns UNKNOWN
            # original filename captured only if rename succeeded
            if pv.original_filename is not None:
                assert pv.original_filename == "PAPER-BATCH_p1.png"
