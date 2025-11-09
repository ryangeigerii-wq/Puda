from pathlib import Path
from src.processing.processing import RawArtifact, ProcessingContext, ClassificationProcessor


def test_classification_invoice(tmp_path):
    # Create fake OCR text file
    ocr_path = tmp_path / "page1_ocr.txt"
    ocr_path.write_text("INVOICE\nTotal Amount Due: 123.45\n", encoding="utf-8")
    artifact = RawArtifact(page_id="p1", storage_ref=str(tmp_path / "dummy.png"), ocr_text_ref=str(ocr_path), metadata={"processing": {"layout": {"regions": [{"type": "table", "bbox": [0,0,100,100]}]}}})
    proc = ClassificationProcessor()
    ctx = ProcessingContext(batch_id="B1", operator_id="tester")
    proc.process(artifact, ctx)
    doc_type = artifact.metadata["processing"]["classification"]["document_type"]
    assert doc_type == "invoice"


def test_classification_id(tmp_path):
    ocr_path = tmp_path / "page2_ocr.txt"
    ocr_path.write_text("DRIVER LICENSE\nDOB: 1990-01-01\n", encoding="utf-8")
    artifact = RawArtifact(page_id="p2", storage_ref=str(tmp_path / "dummy.png"), ocr_text_ref=str(ocr_path), metadata={"processing": {"layout": {"regions": [{"type": "text_block", "bbox": [0,0,10,10]}]}}})
    proc = ClassificationProcessor()
    ctx = ProcessingContext(batch_id="B2", operator_id="tester")
    proc.process(artifact, ctx)
    doc_type = artifact.metadata["processing"]["classification"]["document_type"]
    assert doc_type == "id" or doc_type == "id"  # flexible


def test_classification_form(tmp_path):
    ocr_path = tmp_path / "page3_ocr.txt"
    ocr_path.write_text("Form 123 Section A\n", encoding="utf-8")
    artifact = RawArtifact(page_id="p3", storage_ref=str(tmp_path / "dummy.png"), ocr_text_ref=str(ocr_path), metadata={"processing": {"layout": {"regions": [{"type": "table", "bbox": [0,0,100,100]}, {"type": "table", "bbox": [0,110,100,100]}]}}})
    proc = ClassificationProcessor()
    ctx = ProcessingContext(batch_id="B3", operator_id="tester")
    proc.process(artifact, ctx)
    doc_type = artifact.metadata["processing"]["classification"]["document_type"]
    assert doc_type == "form"
