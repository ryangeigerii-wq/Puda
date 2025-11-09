"""Tests for ImageCleanupProcessor focusing on metadata presence rather than image fidelity."""
from pathlib import Path
import tempfile
from PIL import Image

from src.processing.processing import (
    RawArtifact,
    ProcessingContext,
    ProcessingPipeline,
    ImageCleanupProcessor,
    MetadataEnrichmentProcessor,
    DummyClassifier,
)


def _make_dummy_image(path: Path):
    img = Image.new("RGB", (200, 100), (255, 255, 255))
    img.save(path, format="PNG")


def test_image_cleanup_metadata_added():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "scan.png"
        _make_dummy_image(p)
        artifact = RawArtifact(page_id="PAPER-IMG:1", storage_ref=str(p))
        ctx = ProcessingContext(batch_id="BATCH-CLEAN", operator_id="OP-IMG")
        pipeline = ProcessingPipeline(
            processors=[MetadataEnrichmentProcessor(), ImageCleanupProcessor()],
            structurer=DummyClassifier()
        )
        result = pipeline.run([artifact], ctx)[0]
        cleanup_meta = result.raw_metadata.get("processing", {}).get("image_cleanup", {})
        assert cleanup_meta.get("status") in {"ok", "skipped_no_image_lib_or_missing"}
        # If ok, cleaned_path should exist
        cleaned_path = cleanup_meta.get("cleaned_path")
        if cleaned_path:
            assert Path(cleaned_path).exists()
