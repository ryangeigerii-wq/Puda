import os
from pathlib import Path
from src.processing.processing import RawArtifact, ProcessingContext, build_default_pipeline


def make_dummy_ocr_file(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "sample_cleaned.png"  # pretend cleaned image exists for path coherence
    p.write_bytes(b"PNG")  # minimal placeholder bytes
    ocr = tmp_path / "sample_cleaned_ocr.txt"
    ocr.write_text(text, encoding="utf-8")
    return ocr


def test_confidence_invoice(tmp_path):
    text = "Invoice Number: INV-1234\nTotal: $123.45\n2025-11-08\nThank you"  # invoice keywords
    ocr_path = make_dummy_ocr_file(tmp_path, text)
    artifact = RawArtifact(page_id="p1", storage_ref=str(ocr_path.with_name("sample.png")))
    artifact.ocr_text_ref = str(ocr_path)
    pipeline = build_default_pipeline(engine_preference="stub")
    ctx = ProcessingContext(batch_id="b1", operator_id="op1")
    structured = pipeline.run([artifact], ctx)[0]
    class_meta = structured.raw_metadata.get("processing", {}).get("classification", {})
    assert class_meta.get("confidence") is not None
    assert 0 <= class_meta.get("confidence") <= 1
    fields_conf = structured.extracted_fields.get("_field_confidence", {})
    assert fields_conf, "field confidence mapping should exist"
    for v in fields_conf.values():
        assert 0 <= v <= 1


def test_confidence_id(tmp_path):
    text = "Passport ID#: P-998877\nDOB: 1990-01-02\nJane Doe"  # id keywords
    ocr_path = make_dummy_ocr_file(tmp_path, text)
    artifact = RawArtifact(page_id="p2", storage_ref=str(ocr_path.with_name("sample2.png")))
    artifact.ocr_text_ref = str(ocr_path)
    pipeline = build_default_pipeline(engine_preference="stub")
    ctx = ProcessingContext(batch_id="b2", operator_id="op2")
    structured = pipeline.run([artifact], ctx)[0]
    class_meta = structured.raw_metadata.get("processing", {}).get("classification", {})
    assert class_meta.get("document_type") == "id"
    assert class_meta.get("confidence") >= 0.2  # base + id_kw weight
    fields_conf = structured.extracted_fields.get("_field_confidence", {})
    assert fields_conf.get("id_number") is not None
    assert fields_conf.get("dob") is not None
    assert fields_conf.get("name") is not None
