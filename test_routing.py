from pathlib import Path
from src.processing.processing import RawArtifact, ProcessingContext, build_default_pipeline


def make_artifact(tmp_path: Path, text: str, page_id: str):
    ocr_file = tmp_path / f"{page_id}_ocr.txt"
    ocr_file.write_text(text, encoding="utf-8")
    art = RawArtifact(page_id=page_id, storage_ref=str(ocr_file.with_name(f"{page_id}.png")))
    art.ocr_text_ref = str(ocr_file)
    return art


def test_routing_invoice_high_conf(tmp_path):
    text = "Invoice Number: INV-9999\nTotal: $123.45\n2025-11-08"  # strong invoice signals
    art = make_artifact(tmp_path, text, "p_inv_high")
    pipeline = build_default_pipeline(engine_preference="stub")
    ctx = ProcessingContext(batch_id="b", operator_id="op")
    structured = pipeline.run([art], ctx)[0]
    routing = structured.raw_metadata.get("processing", {}).get("routing", {})
    assert routing.get("route") == "auto"
    assert (routing.get("classification_confidence") or 0) >= 0.55
    assert not routing.get("reasons")
    assert routing.get("severity") == "auto"


def test_routing_invoice_low_conf_missing_fields(tmp_path):
    # Missing total amount, minimal text -> lower confidence
    text = "Invoice\nINV-ABCD"  # invoice keyword but no amount/date
    art = make_artifact(tmp_path, text, "p_inv_low")
    pipeline = build_default_pipeline(engine_preference="stub")
    ctx = ProcessingContext(batch_id="b", operator_id="op")
    structured = pipeline.run([art], ctx)[0]
    routing = structured.raw_metadata.get("processing", {}).get("routing", {})
    assert routing.get("route") == "manual_review"
    reasons = routing.get("reasons", [])
    assert "missing_all_required_fields" in reasons
    assert routing.get("severity") == "manual"


def test_routing_unknown_doc(tmp_path):
    text = "Random content without strong signals"  # no classification keywords
    art = make_artifact(tmp_path, text, "p_unknown")
    pipeline = build_default_pipeline(engine_preference="stub")
    ctx = ProcessingContext(batch_id="b", operator_id="op")
    structured = pipeline.run([art], ctx)[0]
    routing = structured.raw_metadata.get("processing", {}).get("routing", {})
    assert routing.get("route") == "manual_review"
    reasons = routing.get("reasons", [])
    assert any("classification_conf_very_low" in r for r in reasons)
    assert routing.get("severity") == "manual"
