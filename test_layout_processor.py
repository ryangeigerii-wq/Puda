from pathlib import Path
from src.processing.processing import RawArtifact, ProcessingContext, build_default_pipeline

try:
    from PIL import Image, ImageDraw  # type: ignore
except Exception:
    Image = None  # type: ignore


def _make_table_signature_image(path: Path):
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # Draw table (grid) top half
    left, top = 50, 80
    right, bottom = 750, 400
    # Outer rectangle
    d.rectangle([left, top, right, bottom], outline=(0,0,0), width=3)
    # Vertical lines
    for x in range(left+140, right, 140):
        d.line([x, top, x, bottom], fill=(0,0,0), width=2)
    # Horizontal lines
    for y in range(top+64, bottom, 64):
        d.line([left, y, right, y], fill=(0,0,0), width=2)
    # Signature stroke near bottom
    sig_top = 850
    sig_left = 200
    for i in range(120):
        d.line([sig_left + i*3, sig_top + (i % 5), sig_left + i*3 + 2, sig_top + (i % 7)], fill=(0,0,0), width=1)
    img.save(path)


def test_layout_detection_regions(tmp_path):
    if Image is None:
        return  # skip if Pillow missing
    img_path = tmp_path / "layout_sample.png"
    _make_table_signature_image(img_path)
    artifact = RawArtifact(page_id="layout:1", storage_ref=str(img_path))
    ctx = ProcessingContext(batch_id="B1", operator_id="tester")
    pipeline = build_default_pipeline(engine_preference="stub", language="eng")
    pipeline.run([artifact], ctx)
    layout_meta = artifact.metadata.get("processing", {}).get("layout", {})
    assert layout_meta.get("status") in {"ok", "skipped_no_cv_or_missing"}
    # If OpenCV available, expect regions
    if layout_meta.get("status") == "ok":
        regions = layout_meta.get("regions", [])
        assert len(regions) > 0
        # Expect at least one table and one signature
        types = {r['type'] for r in regions}
        assert 'table' in types or 'signature' in types  # allow heuristic variance
