"""Tests for processing pipeline skeleton."""
from src.processing.processing import (
    RawArtifact,
    ProcessingContext,
    build_default_pipeline,
    structured_to_json,
)


def test_pipeline_runs_and_structures():
    pipeline = build_default_pipeline()
    artifacts = [RawArtifact(page_id="PAPER-1:1", storage_ref="/tmp/file1"), RawArtifact(page_id="PAPER-1:2", storage_ref="/tmp/file2")]
    ctx = ProcessingContext(batch_id="BATCH-XYZ", operator_id="OP-1")
    structured = pipeline.run(artifacts, ctx)
    assert len(structured) == 2
    for s in structured:
        assert s.page_id.startswith("PAPER-1:")
        assert s.classification == "unknown"
        assert "enriched_at" in s.raw_metadata.get("processing", {})
    js = structured_to_json(structured)
    assert "PAPER-1:1" in js and "PAPER-1:2" in js
