from pathlib import Path
from src.processing.processing import RawArtifact, ProcessingContext, build_default_pipeline, RoutingProcessor, ProcessingPipeline, MetadataEnrichmentProcessor, ImageCleanupProcessor, LayoutDetectionProcessor, OcrProcessor, ClassificationProcessor, FieldExtractionProcessor, TableExtractionProcessor


def build_pipeline_with_config(config_path: str):
    return ProcessingPipeline([
        MetadataEnrichmentProcessor(),
        ImageCleanupProcessor(),
        LayoutDetectionProcessor(),
        OcrProcessor(engine_preference="stub", language="eng"),
        ClassificationProcessor(),
        FieldExtractionProcessor(),
        TableExtractionProcessor(engine_preference="stub", language="eng"),
        RoutingProcessor(config_path=config_path)
    ], structurer=RoutingProcessor)  # incorrect structurer placeholder on purpose? will not be used


def test_invoice_threshold_override(tmp_path):
    # custom config lowering invoice classification_threshold to force qc route
    cfg = tmp_path / "routing_thresholds.json"
    cfg.write_text('{"default":{"classification_threshold":0.55,"classification_manual_threshold":0.35,"field_threshold":0.65,"field_manual_threshold":0.45},"invoice":{"classification_threshold":0.9}}', encoding="utf-8")

    text = "Invoice Number: INV-1111\nTotal: $10.00"  # would normally classify invoice with moderate confidence
    ocr_file = tmp_path / "inv_ocr.txt"
    ocr_file.write_text(text, encoding="utf-8")
    artifact = RawArtifact(page_id="test-inv", storage_ref=str(ocr_file.with_name("inv.png")))
    artifact.ocr_text_ref = str(ocr_file)

    pipeline = build_default_pipeline(engine_preference="stub")
    # Replace routing processor with configured one
    pipeline.processors[-1] = RoutingProcessor(config_path=str(cfg))
    ctx = ProcessingContext(batch_id="b", operator_id="op")
    structured = pipeline.run([artifact], ctx)[0]
    routing = structured.raw_metadata.get("processing", {}).get("routing", {})
    assert routing.get("thresholds_used", {}).get("classification_threshold") == 0.9
    # confidence likely < 0.9 so should route qc or manual but not auto
    assert routing.get("route") in {"qc_queue", "manual_review"}
