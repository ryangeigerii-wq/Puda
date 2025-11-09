"""Processing Layer (HomeBrew AI Core - Initial Skeleton)

Purpose:
    Transform raw scans (or ingested page artifacts) into structured data.
    This initial version provides a pluggable pipeline architecture where
    processors can be chained. Future expansions will add ML models,
    semantic extraction, classification, OCR enrichment, and normalization.

Design Goals:
    - Minimal, testable core.
    - Processor interface with clear contract.
    - Pipeline orchestrator applying processors sequentially.
    - Data containers (RawArtifact, StructuredArtifact, ProcessingContext).

Future Layers (Roadmap, 7+ additional phases):
    1. OCR Text Normalization
    2. Document Type Classification
    3. Field Extraction / Entity Tagging
    4. Sensitive Data Redaction
    5. Quality Metrics & Confidence Scoring
    6. Aggregation / Cross-Doc Linking
    7. Export Formatting (JSON, XML, DB Records)
    8. (Bonus) Feedback Loop / Active Learning Hooks

"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Protocol, runtime_checkable, Optional, Tuple
import re
import json
import time
import json
from pathlib import Path
try:
    from PIL import Image, ImageOps, ImageEnhance, ImageChops  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageOps = None  # type: ignore
    ImageEnhance = None  # type: ignore
    ImageChops = None  # type: ignore
try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    np = None  # type: ignore


@dataclass
class RawArtifact:
    page_id: str  # e.g., paper_id:page_number
    storage_ref: str  # path or key to raw file
    ocr_text_ref: Optional[str] = None  # optional reference to OCR output
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuredArtifact:
    page_id: str
    extracted_fields: Dict[str, Any]
    classification: Optional[str] = None
    confidence: Optional[float] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProcessingContext:
    batch_id: Optional[str]
    operator_id: Optional[str]
    started_at: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""


@runtime_checkable
class Processor(Protocol):
    name: str

    def process(self, artifact: RawArtifact, ctx: ProcessingContext) -> RawArtifact:
        """May modify artifact metadata or attach intermediate data.
        Returns the (possibly mutated) artifact for next processor.
        """
        ...


@runtime_checkable
class StructuringProcessor(Protocol):
    name: str

    def build_structured(self, artifact: RawArtifact, ctx: ProcessingContext) -> StructuredArtifact:
        """Convert a fully prepared RawArtifact into a StructuredArtifact."""
        ...


from .instrumentation import instrument_class


@instrument_class
class MetadataEnrichmentProcessor:
    name = "metadata_enrichment"

    def process(self, artifact: RawArtifact, ctx: ProcessingContext) -> RawArtifact:
        artifact.metadata.setdefault("processing", {})
        artifact.metadata["processing"]["enriched_at"] = datetime.utcnow().isoformat()
        artifact.metadata["processing"]["batch_id"] = ctx.batch_id
        return artifact


class DummyClassifier(StructuringProcessor):
    name = "dummy_classifier"

    def build_structured(self, artifact: RawArtifact, ctx: ProcessingContext) -> StructuredArtifact:
        # Use classification from prior processor if available
        processing_meta = artifact.metadata.get("processing", {})
        class_meta = processing_meta.get("classification", {})
        extraction_meta = processing_meta.get("extraction", {})
        classification = class_meta.get("document_type", "unknown")
        extracted_fields = extraction_meta.get("fields", {}) or {"placeholder": True}
        # Attach field confidence inline if available (shallow merge under _confidence map)
        field_conf = extraction_meta.get("field_confidence", {})
        if field_conf:
            # Represent confidence as parallel map to keep original plain values
            extracted_fields = {**extracted_fields, "_field_confidence": field_conf}
        confidence = class_meta.get("confidence")
        return StructuredArtifact(
            page_id=artifact.page_id,
            classification=classification,
            extracted_fields=extracted_fields,
            confidence=confidence,
            raw_metadata=artifact.metadata,
        )


class ProcessingPipeline:
    def __init__(self, processors: List[Processor], structurer: StructuringProcessor):
        self.processors = processors
        self.structurer = structurer

    def run(self, artifacts: List[RawArtifact], ctx: ProcessingContext) -> List[StructuredArtifact]:
        structured: List[StructuredArtifact] = []
        for artifact in artifacts:
            current = artifact
            for proc in self.processors:
                current = proc.process(current, ctx)
            structured.append(self.structurer.build_structured(current, ctx))
        return structured


# Convenience builder

def build_default_pipeline(engine_preference: str = "tesseract", language: str = "eng") -> ProcessingPipeline:
    """Build the default processing pipeline.

    Order:
      1. Metadata enrichment
      2. Image cleanup
      3. OCR (configurable engine)
      4. Structuring (dummy classifier placeholder)

    Parameters
    ----------
    engine_preference: str
        Preferred OCR engine name ("tesseract", "paddle", "stub"). Falls back to stub if unavailable.
    language: str
        Language code(s) for OCR (e.g. "eng", "eng+spa" for Tesseract; "en" for PaddleOCR).
    """
    return ProcessingPipeline(
        processors=[
            MetadataEnrichmentProcessor(),
            ImageCleanupProcessor(),
            LayoutDetectionProcessor(),
            OcrProcessor(engine_preference=engine_preference, language=language),
            ClassificationProcessor(),
            FieldExtractionProcessor(),
            TableExtractionProcessor(engine_preference=engine_preference, language=language),
            RoutingProcessor(),
        ],
        structurer=DummyClassifier(),
    )


# Simple serialization helpers

def structured_to_json(items: List[StructuredArtifact]) -> str:
    return json.dumps([
        {
            "page_id": i.page_id,
            "classification": i.classification,
            "confidence": i.confidence,
            "extracted_fields": i.extracted_fields,
            "created_at": i.created_at.isoformat(),
        } for i in items
    ], indent=2)


# ---------------- Image Cleanup Processor -----------------

@instrument_class
class ImageCleanupProcessor:
    """Perform basic image cleanup: crop borders, deskew (if possible), de-shadow, normalize contrast.

    Steps (best-effort, conditional on library availability):
      1. Load image from storage_ref (skip if not an image or missing libs).
      2. Auto-crop using Pillow (border detection via ImageOps) or simple trim of uniform edges.
      3. Deskew using OpenCV (Hough transform on edges) if cv2 available.
      4. De-shadow via morphological operations / background subtraction.
      5. Contrast normalization using Pillow ImageEnhance.
      6. Save cleaned image alongside original ("*_cleaned.png").
      7. Record cleanup metadata.

    Non-fatal failures are captured in metadata and original artifact is passed through unchanged.
    """
    name = "image_cleanup"

    def process(self, artifact: RawArtifact, ctx: ProcessingContext) -> RawArtifact:
        path = Path(artifact.storage_ref)
        artifact.metadata.setdefault("processing", {})
        clean_meta = artifact.metadata["processing"].setdefault("image_cleanup", {})
        if Image is None or not path.exists():
            clean_meta["status"] = "skipped_no_image_lib_or_missing"
            return artifact
        # Attempt load
        try:
            img = Image.open(path)
            img.load()
        except Exception as e:
            clean_meta["status"] = f"load_failed:{e.__class__.__name__}"
            return artifact
        original_size = img.size
        clean_meta["original_size"] = original_size

        # 1. Auto-crop simple: trim uniform borders
        try:
            img = self._auto_crop(img)
            clean_meta["cropped_size"] = img.size
        except Exception:
            clean_meta["crop_error"] = True

        # 2. Deskew (OpenCV) if available
        if cv2 is not None and np is not None:
            try:
                img = self._deskew_opencv(img, clean_meta)
            except Exception:
                clean_meta["deskew_error"] = True
        else:
            clean_meta["deskew_skipped"] = True

        # 3. De-shadow (OpenCV) if available
        if cv2 is not None and np is not None:
            try:
                img = self._deshadow(img, clean_meta)
            except Exception:
                clean_meta["deshadow_error"] = True
        else:
            clean_meta["deshadow_skipped"] = True

        # 4. Contrast normalization
        try:
            if ImageEnhance is not None:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)
                clean_meta["contrast_enhanced"] = True
            else:
                clean_meta["contrast_skipped"] = True
        except Exception:
            clean_meta["contrast_error"] = True

        # Save cleaned image
        cleaned_path = path.with_name(f"{path.stem}_cleaned.png")
        try:
            img.save(cleaned_path, format="PNG")
            clean_meta["cleaned_path"] = str(cleaned_path)
            clean_meta["status"] = "ok"
        except Exception as e:
            clean_meta["status"] = f"save_failed:{e.__class__.__name__}"

        return artifact

    # --------------- Helper Methods ---------------
    def _auto_crop(self, img):  # type: ignore[no-untyped-def]
        if Image is None or ImageOps is None or ImageChops is None:
            return img
        try:
            bg_color = img.getpixel((0, 0))
            bg = Image.new(img.mode, img.size, bg_color)
            diff = ImageChops.difference(img, bg)
            bbox = diff.getbbox()
            if bbox:
                return img.crop(bbox)
        except Exception:
            return img
        return img

    def _deskew_opencv(self, img, meta: Dict[str, Any]):  # type: ignore[no-untyped-def]
        # Convert PIL to OpenCV
        if cv2 is None or np is None:
            return img
        arr = np.array(img.convert('L'))
        edges = cv2.Canny(arr, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        angle = 0.0
        if lines is not None:
            for rho, theta in lines[:,0]:
                # capture first significant line
                angle = (theta * 180 / np.pi) - 90
                break
        if abs(angle) > 0.1:
            meta["deskew_angle"] = angle
            # Rotate via OpenCV
            (h, w) = arr.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(arr, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            if Image is not None:
                return Image.fromarray(rotated).convert(img.mode)
            return img
        meta["deskew_angle"] = 0.0
        return img

    def _deshadow(self, img, meta: Dict[str, Any]):  # type: ignore[no-untyped-def]
        if cv2 is None or np is None:
            return img
        arr = np.array(img.convert('L'))
        # Use morphological open to approximate background then subtract
        kernel = np.ones((15,15), np.uint8)
        background = cv2.morphologyEx(arr, cv2.MORPH_OPEN, kernel)
        diff = cv2.subtract(arr, background)
        norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        meta["deshadow_applied"] = True
        if Image is not None:
            return Image.fromarray(norm).convert(img.mode)
        return img

@instrument_class
class LayoutDetectionProcessor:
    """Detect layout regions (text blocks, tables, signatures) heuristically.

    Adds metadata under processing.layout with list of regions:
      {"bbox": [x,y,w,h], "type": "text_block"|"table"|"signature"}
    """
    name = "layout_detection"

    def process(self, artifact: RawArtifact, ctx: ProcessingContext) -> RawArtifact:  # type: ignore[override]
        artifact.metadata.setdefault("processing", {})
        layout_meta = artifact.metadata["processing"].setdefault("layout", {})
        cleaned = artifact.metadata.get("processing", {}).get("image_cleanup", {}).get("cleaned_path")
        image_path = cleaned or artifact.storage_ref
        path = Path(image_path)
        if cv2 is None or np is None or not path.exists():
            layout_meta["status"] = "skipped_no_cv_or_missing"
            return artifact
        try:
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                layout_meta["status"] = "load_failed"
                return artifact
            h, w = img.shape[:2]
            layout_meta["image_size"] = [w, h]
            bin_img = cv2.adaptiveThreshold(img,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY_INV,25,15)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
            morph = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, kernel, iterations=1)
            contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            regions = []
            for c in contours:
                x,y,wc,hc = cv2.boundingRect(c)
                if wc < 30 or hc < 15:
                    continue
                area = wc * hc
                aspect = wc / max(hc,1)
                region_type = "text_block"
                # Table heuristic
                if wc > 150 and hc > 80:
                    sub = img[y:y+hc, x:x+wc]
                    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, wc//20),1))
                    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,max(10, hc//20)))
                    bin_sub = cv2.adaptiveThreshold(sub,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY_INV,15,10)
                    horiz = cv2.erode(bin_sub, horiz_kernel, iterations=1)
                    horiz = cv2.dilate(horiz, horiz_kernel, iterations=1)
                    vert = cv2.erode(bin_sub, vert_kernel, iterations=1)
                    vert = cv2.dilate(vert, vert_kernel, iterations=1)
                    line_pixels = int((horiz>0).sum() + (vert>0).sum())
                    density = line_pixels / max(area,1)
                    if density > 0.02:
                        region_type = "table"
                # Signature heuristic
                if y > h*0.6 and 80 < wc < 400 and hc < 120 and aspect > 2.5:
                    sub = img[y:y+hc, x:x+wc]
                    edges = cv2.Canny(sub,50,150)
                    edge_density = edges.sum() / (255 * max(area,1))
                    if edge_density > 0.005:
                        region_type = "signature"
                regions.append({"bbox": [int(x), int(y), int(wc), int(hc)], "area": int(area), "type": region_type})
            layout_meta["regions"] = regions
            layout_meta["region_count"] = len(regions)
            layout_meta["status"] = "ok"
        except Exception as e:
            layout_meta["status"] = f"error:{e.__class__.__name__}"
        return artifact


# ---------------- OCR Processor -----------------
from .ocr_engines import build_engine, OcrResult  # local import to avoid circular at module import time


@instrument_class
class OcrProcessor:
    """Attach OCR text to artifact if not already present.

    Strategy:
      1. Determine image path: prefer cleaned image if available in metadata; else original storage_ref.
      2. Invoke chosen OCR engine (graceful fallback handled by build_engine).
      3. Persist OCR text to sidecar UTF-8 file (<stem>_ocr.txt) alongside image.
      4. Record metrics & engine status in artifact.metadata["processing"]["ocr"].
      5. Non-fatal errors captured in metadata; pipeline continues.
    """
    name = "ocr"

    def __init__(self, engine_preference: str = "tesseract", language: str = "eng"):
        self.engine_preference = engine_preference
        self.language = language
        self._engine = build_engine(preferred=engine_preference, language=language)

    def process(self, artifact: RawArtifact, ctx: ProcessingContext) -> RawArtifact:  # type: ignore[override]
        artifact.metadata.setdefault("processing", {})
        ocr_meta = artifact.metadata["processing"].setdefault("ocr", {})
        # Skip if OCR already done
        if artifact.ocr_text_ref:
            ocr_meta["status"] = "skipped_existing"
            return artifact
        # Determine image path (prefer cleaned)
        cleaned = artifact.metadata.get("processing", {}).get("image_cleanup", {}).get("cleaned_path")
        image_path = cleaned or artifact.storage_ref
        path = Path(image_path)
        if not path.exists():
            ocr_meta["status"] = "skipped_missing_image"
            return artifact
        start = datetime.utcnow()
        try:
            result: OcrResult = self._engine.extract_text(str(path), language=self.language)
            duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
            ocr_meta.update({
                "engine": result.engine,
                "language": result.language,
                "duration_ms": duration_ms,
                "status": result.metadata.get("status", "ok"),
                "char_count": len(result.text or ""),
            })
            if result.confidence is not None:
                ocr_meta["confidence"] = result.confidence
            # Persist sidecar file if we have any text (including empty for audit)
            sidecar = path.with_name(f"{path.stem}_ocr.txt")
            try:
                sidecar.write_text(result.text or "", encoding="utf-8")
                artifact.ocr_text_ref = str(sidecar)
                ocr_meta["text_path"] = str(sidecar)
            except Exception as e:
                ocr_meta["persist_error"] = e.__class__.__name__
        except Exception as e:  # catch unexpected engine failure
            ocr_meta["status"] = f"error:{e.__class__.__name__}"
        return artifact

@instrument_class
class ClassificationProcessor:
    """Assign document type using simple heuristics over OCR text & layout metadata.

    Heuristics:
      invoice: invoice|total|amount due|due date|balance (+ table strengthens).
      id: driver license|passport|id#|dob if few text blocks.
      form: >=2 table regions.
      letter: signature region present & at least one text block.
    """
    name = "classification"
    INVOICE_KW = {"invoice", "amount due", "total", "due date", "balance"}
    ID_KW = {"driver license", "passport", "id#", "date of birth", "dob"}

    def process(self, artifact: RawArtifact, ctx: ProcessingContext) -> RawArtifact:  # type: ignore[override]
        artifact.metadata.setdefault("processing", {})
        class_meta = artifact.metadata["processing"].setdefault("classification", {})
        text = ""
        if artifact.ocr_text_ref:
            try:
                text = Path(artifact.ocr_text_ref).read_text(encoding="utf-8").lower()
            except Exception:
                class_meta["status"] = "ocr_read_failed"
        layout = artifact.metadata.get("processing", {}).get("layout", {})
        regions = layout.get("regions", []) if isinstance(layout.get("regions"), list) else []
        types = [r.get("type") for r in regions]
        table_count = sum(1 for t in types if t == "table")
        signature_present = any(t == "signature" for t in types)
        text_blocks = sum(1 for t in types if t == "text_block")
        doc_type = "unknown"
        matches: List[str] = []
        if text:
            if any(kw in text for kw in self.INVOICE_KW):
                doc_type = "invoice"
                matches.append("invoice_kw")
                if table_count >= 1:
                    matches.append("table")
            elif any(kw in text for kw in self.ID_KW):
                doc_type = "id"
                matches.append("id_kw")
        if doc_type == "unknown" and table_count >= 2:
            doc_type = "form"
            matches.append("multi_table")
        if doc_type == "unknown" and signature_present and text_blocks >= 1:
            doc_type = "letter"
            matches.append("signature")
        # Confidence scoring heuristic
        feature_weights = {
            "invoice_kw": 0.5,
            "table": 0.2,
            "id_kw": 0.6,
            "multi_table": 0.5,
            "signature": 0.4,
        }
        base = 0.0 if doc_type == "unknown" else 0.2
        score = base + sum(feature_weights.get(m, 0.0) for m in matches)
        confidence = round(min(1.0, score), 4)
        class_meta.update({
            "document_type": doc_type,
            "matched_features": matches,
            "table_regions": table_count,
            "signature_present": signature_present,
            "text_block_count": text_blocks,
            "status": class_meta.get("status", "ok"),
            "confidence": confidence,
        })
        return artifact

@instrument_class
class FieldExtractionProcessor:
    """Extract key fields from OCR text based on document type heuristics.

    Invoice fields: invoice_number, total_amount, invoice_date
    ID fields: id_number, name, dob
    Letter: date, signature_name
    Form: form_id (first token 'form XYZ')
    Stores results under processing.extraction.fields
    """
    name = "field_extraction"

    INVOICE_NUMBER_RE = re.compile(r"invoice\s*(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9\-]+)", re.IGNORECASE)
    TOTAL_AMOUNT_RE = re.compile(r"(?:total|amount due|balance due|balance)\s*[:$]?\s*\$?([0-9]{1,6}(?:[,0-9]{0,6})?(?:\.[0-9]{2})?)", re.IGNORECASE)
    DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})")
    ID_NUMBER_RE = re.compile(r"(?:id#|license|passport)\s*[:#]?\s*([A-Z0-9\-]+)", re.IGNORECASE)
    DOB_RE = re.compile(r"(?:dob|date of birth)\s*[:]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", re.IGNORECASE)
    FORM_ID_RE = re.compile(r"form\s+([A-Z0-9\-]+)", re.IGNORECASE)

    def process(self, artifact: RawArtifact, ctx: ProcessingContext) -> RawArtifact:  # type: ignore[override]
        artifact.metadata.setdefault("processing", {})
        extraction_meta = artifact.metadata["processing"].setdefault("extraction", {})
        fields = {}
        doc_type = artifact.metadata.get("processing", {}).get("classification", {}).get("document_type", "unknown")
        text = ""
        if artifact.ocr_text_ref:
            try:
                text = Path(artifact.ocr_text_ref).read_text(encoding="utf-8")
            except Exception:
                extraction_meta["status"] = "ocr_read_failed"
        lower = text.lower()
        if doc_type == "invoice" and text:
            inv_match = self.INVOICE_NUMBER_RE.search(text)
            if inv_match:
                fields["invoice_number"] = inv_match.group(1)
            total_match = self.TOTAL_AMOUNT_RE.search(text)
            if total_match:
                fields["total_amount"] = total_match.group(1)
            date_match = self.DATE_RE.search(text)
            if date_match:
                fields["invoice_date"] = date_match.group(1)
        elif doc_type == "id" and text:
            id_match = self.ID_NUMBER_RE.search(text)
            if id_match:
                fields["id_number"] = id_match.group(1)
            dob_match = self.DOB_RE.search(text)
            if dob_match:
                fields["dob"] = dob_match.group(1)
            # Naive name line: first line containing 'license' not used; fallback to first line with 2+ words
            for line in text.splitlines():
                if len(line.split()) >= 2 and not any(k in line.lower() for k in ["driver", "license", "dob", "id", "passport"]):
                    fields["name"] = line.strip()
                    break
        elif doc_type == "letter" and text:
            # Date line near top
            for line in text.splitlines()[:10]:
                dm = self.DATE_RE.search(line)
                if dm:
                    fields["date"] = dm.group(1)
                    break
            # Signature: last non-empty line with >1 word
            for line in reversed(text.splitlines()):
                if len(line.strip().split()) >= 2:
                    fields["signature_name"] = line.strip()
                    break
        elif doc_type == "form" and text:
            fm = self.FORM_ID_RE.search(text)
            if fm:
                fields["form_id"] = fm.group(1)
        # Compute per-field confidence heuristics
        field_conf: Dict[str, float] = extraction_meta.setdefault("field_confidence", {})
        def _conf(name: str, value: Any) -> float:
            if name == "invoice_number":
                return 0.9 if 4 <= len(str(value)) <= 20 else 0.7
            if name == "total_amount":
                try:
                    digits = len(str(int(float(str(value).replace(",","")))))
                    return min(0.95, 0.6 + digits * 0.05)
                except Exception:
                    return 0.5
            if name in {"invoice_date", "dob", "date"}:
                return 0.85 if len(str(value)) in (8,10,10) else 0.7
            if name == "id_number":
                return 0.85
            if name in {"name", "signature_name"}:
                return 0.6
            if name == "form_id":
                return 0.8
            return 0.5
        existing_fields = extraction_meta.setdefault("fields", {})
        for k, v in fields.items():
            existing_fields[k] = v
            field_conf[k] = round(_conf(k, v), 4)
        if field_conf:
            extraction_meta["avg_field_confidence"] = round(sum(field_conf.values()) / max(len(field_conf),1), 4)
        extraction_meta["status"] = extraction_meta.get("status", "ok")
        return artifact

@instrument_class
class TableExtractionProcessor:
    """Extract table regions into CSV sidecar files.

    For each layout table region:
      - Crop image region.
      - OCR (best-effort) that crop using selected engine.
      - Convert lines to CSV rows splitting on 2+ spaces.
      - Store CSV path in processing.extraction.tables list.
    """
    name = "table_extraction"

    def __init__(self, engine_preference: str = "tesseract", language: str = "eng"):
        self.engine_preference = engine_preference
        self.language = language
        try:
            from .ocr_engines import build_engine  # local import
            self._engine = build_engine(preferred=engine_preference, language=language)
        except Exception:
            self._engine = None

    def process(self, artifact: RawArtifact, ctx: ProcessingContext) -> RawArtifact:  # type: ignore[override]
        artifact.metadata.setdefault("processing", {})
        extraction_meta = artifact.metadata["processing"].setdefault("extraction", {})
        tables_meta = extraction_meta.setdefault("tables", [])
        layout = artifact.metadata.get("processing", {}).get("layout", {})
        regions = [r for r in layout.get("regions", []) if r.get("type") == "table"] if isinstance(layout.get("regions"), list) else []
        if not regions:
            extraction_meta["tables_status"] = "no_tables"
            return artifact
        cleaned = artifact.metadata.get("processing", {}).get("image_cleanup", {}).get("cleaned_path")
        image_path = cleaned or artifact.storage_ref
        path = Path(image_path)
        if Image is None or not path.exists():
            extraction_meta["tables_status"] = "skipped_no_image"
            return artifact
        try:
            base_img = Image.open(path)
        except Exception:
            extraction_meta["tables_status"] = "load_failed"
            return artifact
        for idx, region in enumerate(regions):
            x,y,wc,hc = region.get("bbox", [0,0,0,0])
            crop = base_img.crop((x, y, x+wc, y+hc))
            crop_path = path.with_name(f"{path.stem}_table{idx}_crop.png")
            try:
                crop.save(crop_path, format="PNG")
            except Exception:
                continue
            ocr_text = ""
            if self._engine is not None:
                try:
                    # Reuse OCR engine on crop (PIL already imported globally)
                    ocr_text = self._engine.extract_text(str(crop_path), language=self.language).text
                except Exception:
                    ocr_text = ""
            # Fallback: attempt to reuse full artifact OCR text subset (not implemented) if empty
            lines = [l.strip() for l in ocr_text.splitlines() if l.strip()] if ocr_text else []
            rows = []
            for line in lines:
                # Split on 2+ spaces as naive column separator
                cells = [c.strip() for c in re.split(r"\s{2,}", line)]
                rows.append(cells)
            csv_path = path.with_name(f"{path.stem}_table{idx}.csv")
            try:
                with csv_path.open("w", encoding="utf-8") as f:
                    for r in rows:
                        f.write(",".join(r).replace("\n"," ") + "\n")
                tables_meta.append({"csv": str(csv_path), "crop": str(crop_path), "rows": len(rows)})
            except Exception:
                continue
        extraction_meta["tables_status"] = "ok" if tables_meta else extraction_meta.get("tables_status", "empty")
        return artifact

@instrument_class
class RoutingProcessor:
    """Decide routing (auto vs QC queue vs manual review) based on confidence tiers.

    Rules (heuristic initial version):
      - classification confidence < manual_classification_threshold => manual_review
      - avg field confidence (if any fields) < field_manual_threshold => manual_review
      - missing all required fields for known doc type => manual_review
      - classification confidence < classification_threshold => qc_queue
      - avg field confidence < field_threshold => qc_queue
      - missing some (but not all) required fields => qc_queue
      - else route auto

    Adds metadata under processing.routing: {"route": "manual_review"|"qc_queue"|"auto", ...}.
    Creates QC tasks for documents routed to qc_queue or manual_review.
    """

    name = "routing"

    def __init__(
        self,
        config_path: Optional[str] = None,
        audit_log_path: Optional[str] = None,
        daily_rotation: bool = True,
        enable_qc: bool = True
    ):
        # Load thresholds from JSON config or fallback to internal defaults.
        self._config_path = config_path or str(Path("config") / "routing_thresholds.json")
        self._cfg = self._load_config()
        self._audit_log_base = audit_log_path or str(Path("data") / "routing_audit.jsonl")
        self._daily_rotation = daily_rotation
        self._enable_qc = enable_qc
        self._qc_queue = None
        
        # Initialize QC queue if enabled
        if self._enable_qc:
            try:
                from src.qc.queue import QCQueue, QCTask, TaskStatus, TaskPriority
                self._qc_queue = QCQueue()
                self._QCTask = QCTask
                self._TaskStatus = TaskStatus
                self._TaskPriority = TaskPriority
            except ImportError:
                self._enable_qc = False

    def _load_config(self) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        try:
            path = Path(self._config_path)
            if path.exists():
                import json as _json
                return _json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        # Fallback default structure
        return {
            "default": {
                "classification_threshold": 0.55,
                "classification_manual_threshold": 0.35,
                "field_threshold": 0.65,
                "field_manual_threshold": 0.45,
            }
        }

    def _get_thresholds(self, doc_type: str) -> Dict[str, float]:  # type: ignore[no-untyped-def]
        base = self._cfg.get("default", {})
        specific = self._cfg.get(doc_type, {})
        merged = {**base, **specific}
        return {
            "classification_threshold": merged.get("classification_threshold", 0.55),
            "classification_manual_threshold": merged.get("classification_manual_threshold", 0.35),
            "field_threshold": merged.get("field_threshold", 0.65),
            "field_manual_threshold": merged.get("field_manual_threshold", 0.45),
        }

    REQUIRED_FIELDS: Dict[str, List[str]] = {
        "invoice": ["invoice_number", "total_amount"],
        "id": ["id_number", "dob"],
        "letter": [],  # letters may not have mandatory structured fields
        "form": ["form_id"],
    }

    def process(self, artifact: RawArtifact, ctx: ProcessingContext) -> RawArtifact:  # type: ignore[override]
        artifact.metadata.setdefault("processing", {})
        routing_meta = artifact.metadata["processing"].setdefault("routing", {})
        class_meta = artifact.metadata["processing"].get("classification", {})
        extraction_meta = artifact.metadata["processing"].get("extraction", {})
        qc_reasons: List[str] = []
        manual_reasons: List[str] = []
        doc_type = class_meta.get("document_type", "unknown")
        class_conf = class_meta.get("confidence", 0.0) or 0.0
        avg_field_conf = extraction_meta.get("avg_field_confidence")
        fields = extraction_meta.get("fields", {})
        required = self.REQUIRED_FIELDS.get(doc_type, [])
        # Evaluate classification confidence tiers
        th = self._get_thresholds(doc_type)
        if class_conf < th["classification_manual_threshold"]:
            manual_reasons.append(f"classification_conf_very_low:{class_conf}")
        elif doc_type != "unknown" and class_conf < th["classification_threshold"]:
            qc_reasons.append(f"classification_conf_low:{class_conf}")
        if required:
            missing = [r for r in required if r not in fields]
            if missing:
                if len(missing) == len(required):
                    manual_reasons.append("missing_all_required_fields")
                else:
                    qc_reasons.append("missing_fields:" + ",".join(missing))
        if avg_field_conf is not None:
            if avg_field_conf < th["field_manual_threshold"]:
                manual_reasons.append(f"field_conf_very_low:{avg_field_conf}")
            elif avg_field_conf < th["field_threshold"]:
                qc_reasons.append(f"field_conf_low:{avg_field_conf}")
        if doc_type == "unknown" and class_conf < th["classification_threshold"]:
            manual_reasons.append("doc_type_unknown")
        if manual_reasons:
            route = "manual_review"
            reasons = manual_reasons + qc_reasons
            severity = "manual"
        elif qc_reasons:
            route = "qc_queue"
            reasons = qc_reasons
            severity = "qc"
        else:
            route = "auto"
            reasons: List[str] = []
            severity = "auto"
        routing_meta.update({
            "route": route,
            "reasons": reasons,
            "classification_confidence": class_conf,
            "avg_field_confidence": avg_field_conf,
            "doc_type": doc_type,
            "severity": severity,
            "thresholds_used": th,
            "config_path": self._config_path,
        })
        # Emit audit log for qc or manual review (severity >= qc)
        if severity in {"qc", "manual"}:
            self._emit_audit_log(artifact, routing_meta, ctx)
            # Create QC task if enabled
            if self._enable_qc and self._qc_queue:
                self._create_qc_task(artifact, routing_meta, ctx)
        return artifact

    def _emit_audit_log(self, artifact: RawArtifact, routing_meta: Dict[str, Any], ctx: ProcessingContext) -> None:  # type: ignore[no-untyped-def]
        """Write a JSONL record to audit log for downstream ML training and dashboard monitoring."""
        try:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "page_id": artifact.page_id,
                "batch_id": ctx.batch_id,
                "operator_id": ctx.operator_id,
                "route": routing_meta.get("route"),
                "severity": routing_meta.get("severity"),
                "doc_type": routing_meta.get("doc_type"),
                "classification_confidence": routing_meta.get("classification_confidence"),
                "avg_field_confidence": routing_meta.get("avg_field_confidence"),
                "reasons": routing_meta.get("reasons"),
                "thresholds_used": routing_meta.get("thresholds_used"),
            }
            # Apply daily rotation if enabled
            if self._daily_rotation:
                base_path = Path(self._audit_log_base)
                date_suffix = datetime.utcnow().strftime("%Y-%m-%d")
                log_path = base_path.with_name(f"{base_path.stem}_{date_suffix}{base_path.suffix}")
            else:
                log_path = Path(self._audit_log_base)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry) + "\n")
        except Exception:
            # Non-fatal: do not block pipeline if audit log write fails
            pass
    
    def _create_qc_task(self, artifact: RawArtifact, routing_meta: Dict[str, Any], ctx: ProcessingContext) -> None:  # type: ignore[no-untyped-def]
        """Create QC task for documents requiring human verification."""
        if not self._qc_queue:
            return
        
        try:
            # Determine priority based on severity
            if routing_meta.get("severity") == "manual":
                priority = self._TaskPriority.HIGH
            else:
                priority = self._TaskPriority.MEDIUM
            
            # Extract fields from metadata
            extraction_meta = artifact.metadata.get("processing", {}).get("extraction", {})
            fields = extraction_meta.get("fields", {})
            field_confidences = extraction_meta.get("field_confidence", {})
            
            # Create task
            task = self._QCTask(
                task_id=f"{artifact.page_id}_{int(time.time() * 1000)}",
                page_id=artifact.page_id,
                batch_id=ctx.batch_id or "unknown",
                doc_type=routing_meta.get("doc_type", "unknown"),
                severity=routing_meta.get("severity", "qc"),
                status=self._TaskStatus.PENDING,
                priority=priority,
                created_at=time.time(),
                metadata={
                    "original_doc_type": routing_meta.get("doc_type"),
                    "original_fields": fields.copy(),
                    "classification_confidence": routing_meta.get("classification_confidence"),
                    "avg_field_confidence": routing_meta.get("avg_field_confidence"),
                    "field_confidences": field_confidences,
                    "reasons": routing_meta.get("reasons", []),
                    "thresholds_used": routing_meta.get("thresholds_used", {}),
                },
                image_path=artifact.storage_ref,
                ocr_text=Path(artifact.ocr_text_ref).read_text(encoding="utf-8") if artifact.ocr_text_ref else None,
                extracted_fields=fields.copy(),
            )
            
            self._qc_queue.add_task(task)
        except Exception as e:
            # Non-fatal: log error but don't block pipeline
            print(f"Warning: Failed to create QC task: {e}")
            pass
