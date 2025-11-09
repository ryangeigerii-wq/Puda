import json
from pathlib import Path
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


def test_audit_log_qc_route(tmp_path):
    """Verify qc route writes audit entry."""
    audit_log = tmp_path / "routing_audit.jsonl"
    ocr_file = tmp_path / "inv_partial_ocr.txt"
    # Missing total_amount => triggers qc_queue
    ocr_file.write_text("Invoice Number: INV-999", encoding="utf-8")
    artifact = RawArtifact(page_id="inv-qc", storage_ref=str(tmp_path / "inv.png"))
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
            RoutingProcessor(audit_log_path=str(audit_log)),
        ],
        structurer=DummyClassifier(),
    )
    ctx = ProcessingContext(batch_id="batch-qc", operator_id="op-qc")
    structured = pipeline.run([artifact], ctx)[0]
    routing = structured.raw_metadata["processing"]["routing"]
    assert routing["severity"] in {"qc", "manual"}
    assert audit_log.exists()
    lines = audit_log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["page_id"] == "inv-qc"
    assert entry["route"] in {"qc_queue", "manual_review"}
    assert entry["severity"] in {"qc", "manual"}
    assert entry["batch_id"] == "batch-qc"


def test_audit_log_auto_route_no_log(tmp_path):
    """Verify auto route does not write audit entry."""
    audit_log = tmp_path / "routing_audit_auto.jsonl"
    ocr_file = tmp_path / "inv_full_ocr.txt"
    ocr_file.write_text("Invoice Number: INV-123\nTotal: $999.99\n2025-11-08", encoding="utf-8")
    artifact = RawArtifact(page_id="inv-auto", storage_ref=str(tmp_path / "inv.png"))
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
            RoutingProcessor(audit_log_path=str(audit_log)),
        ],
        structurer=DummyClassifier(),
    )
    ctx = ProcessingContext(batch_id="batch-auto", operator_id="op-auto")
    structured = pipeline.run([artifact], ctx)[0]
    routing = structured.raw_metadata["processing"]["routing"]
    assert routing["severity"] == "auto"
    assert not audit_log.exists()


def test_audit_log_manual_route(tmp_path):
    """Verify manual_review route writes audit entry."""
    audit_log = tmp_path / "routing_audit_manual.jsonl"
    ocr_file = tmp_path / "unknown_ocr.txt"
    ocr_file.write_text("Random text with no clear signals", encoding="utf-8")
    artifact = RawArtifact(page_id="manual-1", storage_ref=str(tmp_path / "unknown.png"))
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
            RoutingProcessor(audit_log_path=str(audit_log)),
        ],
        structurer=DummyClassifier(),
    )
    ctx = ProcessingContext(batch_id="batch-manual", operator_id="op-manual")
    structured = pipeline.run([artifact], ctx)[0]
    routing = structured.raw_metadata["processing"]["routing"]
    assert routing["severity"] == "manual"
    assert audit_log.exists()
    lines = audit_log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["page_id"] == "manual-1"
    assert entry["route"] == "manual_review"
    assert entry["severity"] == "manual"
