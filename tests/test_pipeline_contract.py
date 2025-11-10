import pytest
import json
from src.ml.models.pipeline import DocumentProcessor


def test_pipeline_basic_text():
    processor = DocumentProcessor()
    text = "Invoice INV-1234 dated Nov 8, 2025 total $1,250.00 email billing@example.com"
    result = processor.process_text(text, include_embeddings=False)

    # Required top-level keys
    for key in ["text", "classification", "extraction", "summary", "confidence"]:
        assert key in result, f"Missing key: {key}"

    assert isinstance(result["classification"]["doc_type"], str)
    assert 0.0 <= result["classification"]["confidence"] <= 1.0

    # Extraction should have some entities (pattern-based even if model untrained)
    assert any(len(v) > 0 for v in result["extraction"].values())

    # Summary structure
    assert set(["text", "confidence", "method"]).issubset(result["summary"].keys())

    # JSON serializable
    json.dumps(result)


def test_pipeline_empty_text():
    processor = DocumentProcessor()
    result = processor.process_text("", include_embeddings=False)
    assert result["classification"]["doc_type"] in processor.model.DOC_TYPES
    assert result["summary"]["text"] == "" or result["summary"]["method"] in ("fallback", "none")
    json.dumps(result)
