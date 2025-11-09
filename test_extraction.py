from pathlib import Path
from src.processing.processing import RawArtifact, ProcessingContext, FieldExtractionProcessor, TableExtractionProcessor


def make_artifact(tmp_path, text: str, regions=None):
    ocr_path = tmp_path / "sample_ocr.txt"
    ocr_path.write_text(text, encoding="utf-8")
    # Dummy image path (not used by field extraction)
    img_path = tmp_path / "sample.png"
    img_path.write_text("fake", encoding="utf-8")
    metadata = {"processing": {"classification": {"document_type": "invoice" if "invoice" in text.lower() else "id" if "license" in text.lower() else "form" if "form" in text.lower() else "letter" if "dear" in text.lower() else "unknown"}, "layout": {"regions": regions or []}}}
    return RawArtifact(page_id="test:1", storage_ref=str(img_path), ocr_text_ref=str(ocr_path), metadata=metadata)


def test_field_extraction_invoice(tmp_path):
    text = "Invoice Number: INV-12345\nTotal Amount Due: $456.78\n2025-11-08"
    artifact = make_artifact(tmp_path, text)
    proc = FieldExtractionProcessor()
    ctx = ProcessingContext(batch_id="B1", operator_id="tester")
    proc.process(artifact, ctx)
    fields = artifact.metadata["processing"]["extraction"]["fields"]
    assert fields.get("invoice_number") == "INV-12345"
    assert fields.get("total_amount") == "456.78"
    assert fields.get("invoice_date") == "2025-11-08"


def test_field_extraction_id(tmp_path):
    text = "DRIVER LICENSE ID# A12345\nDOB: 1990-01-01\nJohn Q Public"
    artifact = make_artifact(tmp_path, text)
    artifact.metadata["processing"]["classification"]["document_type"] = "id"
    proc = FieldExtractionProcessor()
    ctx = ProcessingContext(batch_id="B2", operator_id="tester")
    proc.process(artifact, ctx)
    fields = artifact.metadata["processing"]["extraction"]["fields"]
    assert fields.get("id_number") == "A12345"
    assert fields.get("dob") == "1990-01-01"
    assert fields.get("name") == "John Q Public"
