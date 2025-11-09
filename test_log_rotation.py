import json
from pathlib import Path
from datetime import datetime
from src.processing.processing import (
    RawArtifact,
    ProcessingContext,
    ProcessingPipeline,
    MetadataEnrichmentProcessor,
    ImageCleanupProcessor,
    LayoutDetectionProcessor,
    OcrProcessor,
    ClassificationProcessor,
    FieldExtractionProcessor,
    TableExtractionProcessor,
    RoutingProcessor,
    DummyClassifier,
)


def test_daily_rotation(tmp_path, monkeypatch):
    """Verify rotation appends to dated filename."""
    base_log = tmp_path / "routing_audit.jsonl"
    ocr_file = tmp_path / "qc_ocr.txt"
    ocr_file.write_text("Invoice Number: INV-001", encoding="utf-8")
    artifact = RawArtifact(page_id="rotation-test", storage_ref=str(tmp_path / "inv.png"))
    artifact.ocr_text_ref = str(ocr_file)

    # Mock datetime to control date suffix
    class MockDatetime:
        @staticmethod
        def utcnow():
            class dt:
                @staticmethod
                def isoformat():
                    return "2025-11-08T10:00:00"
                @staticmethod
                def strftime(fmt):
                    if fmt == "%Y-%m-%d":
                        return "2025-11-08"
                    return "2025-11-08T10:00:00"
            return dt

    import src.processing.processing as proc_module
    original_datetime = proc_module.datetime
    monkeypatch.setattr(proc_module, "datetime", MockDatetime)

    pipeline = ProcessingPipeline(
        [
            MetadataEnrichmentProcessor(),
            ImageCleanupProcessor(),
            LayoutDetectionProcessor(),
            OcrProcessor(engine_preference="stub", language="eng"),
            ClassificationProcessor(),
            FieldExtractionProcessor(),
            TableExtractionProcessor(engine_preference="stub", language="eng"),
            RoutingProcessor(audit_log_path=str(base_log), daily_rotation=True),
        ],
        structurer=DummyClassifier(),
    )
    ctx = ProcessingContext(batch_id="b", operator_id="op")
    pipeline.run([artifact], ctx)

    # Restore datetime
    monkeypatch.setattr(proc_module, "datetime", original_datetime)

    # Check dated file created
    dated_log = tmp_path / "routing_audit_2025-11-08.jsonl"
    assert dated_log.exists()
    lines = dated_log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["page_id"] == "rotation-test"


def test_no_rotation(tmp_path):
    """Verify daily_rotation=False writes to static file."""
    static_log = tmp_path / "routing_static.jsonl"
    ocr_file = tmp_path / "qc_static_ocr.txt"
    ocr_file.write_text("Invoice", encoding="utf-8")
    artifact = RawArtifact(page_id="static-test", storage_ref=str(tmp_path / "inv.png"))
    artifact.ocr_text_ref = str(ocr_file)

    pipeline = ProcessingPipeline(
        [
            MetadataEnrichmentProcessor(),
            ImageCleanupProcessor(),
            LayoutDetectionProcessor(),
            OcrProcessor(engine_preference="stub", language="eng"),
            ClassificationProcessor(),
            FieldExtractionProcessor(),
            TableExtractionProcessor(engine_preference="stub", language="eng"),
            RoutingProcessor(audit_log_path=str(static_log), daily_rotation=False),
        ],
        structurer=DummyClassifier(),
    )
    ctx = ProcessingContext(batch_id="b", operator_id="op")
    pipeline.run([artifact], ctx)

    assert static_log.exists()
    lines = static_log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["page_id"] == "static-test"
