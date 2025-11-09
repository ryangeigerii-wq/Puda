import os
from pathlib import Path
from src.processing.processing import RawArtifact, ProcessingContext, build_default_pipeline

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore


def test_ocr_stub_processor_creates_sidecar(tmp_path):
    # Skip if Pillow not available
    if Image is None:
        return
    img_path = tmp_path / "stub_img.png"
    Image.new("RGB", (40, 40), color=(255, 255, 255)).save(img_path)

    artifact = RawArtifact(page_id="paper1:1", storage_ref=str(img_path))
    pipeline = build_default_pipeline(engine_preference="stub", language="eng")
    ctx = ProcessingContext(batch_id="batchX", operator_id="alice")
    result = pipeline.run([artifact], ctx)[0]

    assert result.page_id == "paper1:1"
    ocr_meta = artifact.metadata["processing"]["ocr"]
    assert ocr_meta["engine"] == "stub"
    assert ocr_meta["char_count"] == 0
    assert ocr_meta["status"] in {"stub", "ok", "stub"}  # status from stub engine
    assert "text_path" in ocr_meta
    text_path = Path(ocr_meta["text_path"])
    assert text_path.exists()
    assert text_path.read_text(encoding="utf-8") == ""


def test_ocr_missing_image(tmp_path):
    missing = tmp_path / "does_not_exist.png"
    artifact = RawArtifact(page_id="paper2:1", storage_ref=str(missing))
    pipeline = build_default_pipeline(engine_preference="stub", language="eng")
    ctx = ProcessingContext(batch_id="batchY", operator_id="bob")
    pipeline.run([artifact], ctx)
    ocr_meta = artifact.metadata["processing"]["ocr"]
    assert ocr_meta["status"] == "skipped_missing_image"
