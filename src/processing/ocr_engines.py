"""OCR Engines Abstraction

Provides a common interface for OCR so we can swap Tesseract / PaddleOCR.
This initial implementation favors graceful degradation: if dependencies
aren't present, we fall back to a stub engine that returns empty text.

Future Enhancements:
- Language pack management and auto-download.
- Confidence scoring aggregation.
- Layout / orientation detection.
- Caching repeated OCR on identical images.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore

try:
    from paddleocr import PaddleOCR  # type: ignore
except Exception:  # pragma: no cover
    PaddleOCR = None  # type: ignore

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore


@dataclass
class OcrResult:
    text: str
    engine: str
    language: str
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = None  # assigned in __post_init__ for safety

    def __post_init__(self):
        if not isinstance(self.metadata, dict):
            self.metadata = {}


class BaseOcrEngine:
    name: str = "base"

    def extract_text(self, image_path: str, language: str = "eng") -> OcrResult:
        raise NotImplementedError


class TesseractOcrEngine(BaseOcrEngine):
    name = "tesseract"

    def __init__(self, config: str = ""):
        self.config = config

    def extract_text(self, image_path: str, language: str = "eng") -> OcrResult:
        if pytesseract is None or Image is None:
            return OcrResult(text="", engine=self.name, language=language, confidence=None, metadata={"status": "unavailable"})
        path = Path(image_path)
        if not path.exists():
            return OcrResult(text="", engine=self.name, language=language, metadata={"status": "missing"})
        try:
            img = Image.open(path)
            raw_text = pytesseract.image_to_string(img, lang=language, config=self.config)
            return OcrResult(text=raw_text, engine=self.name, language=language, confidence=None, metadata={"status": "ok"})
        except Exception as e:
            return OcrResult(text="", engine=self.name, language=language, metadata={"status": f"error:{e.__class__.__name__}"})


class PaddleOcrEngine(BaseOcrEngine):
    name = "paddleocr"

    def __init__(self, language: str = "en", use_angle_cls: bool = True):
        self.language = language
        self.use_angle_cls = use_angle_cls
        self._client = None
        if PaddleOCR is not None:
            try:
                self._client = PaddleOCR(lang=self.language, use_angle_cls=self.use_angle_cls, show_log=False)
            except Exception:
                self._client = None

    def extract_text(self, image_path: str, language: str = "eng") -> OcrResult:
        if self._client is None:
            return OcrResult(text="", engine=self.name, language=language, metadata={"status": "unavailable"})
        path = Path(image_path)
        if not path.exists():
            return OcrResult(text="", engine=self.name, language=language, metadata={"status": "missing"})
        try:
            result = self._client.ocr(str(image_path), cls=True)
            # result is list of lines [[box, (text, confidence)]]
            lines = []
            confidences = []
            for line in result:
                if len(line) >= 1 and len(line[0]) >= 2:
                    text = line[0][1][0]
                    conf = line[0][1][1]
                    lines.append(text)
                    confidences.append(conf)
            merged = "\n".join(lines)
            avg_conf = sum(confidences) / len(confidences) if confidences else None
            return OcrResult(text=merged, engine=self.name, language=language, confidence=avg_conf, metadata={"status": "ok"})
        except Exception as e:
            return OcrResult(text="", engine=self.name, language=language, metadata={"status": f"error:{e.__class__.__name__}"})


class StubOcrEngine(BaseOcrEngine):
    name = "stub"

    def extract_text(self, image_path: str, language: str = "eng") -> OcrResult:
        return OcrResult(text="", engine=self.name, language=language, metadata={"status": "stub"})


def build_engine(preferred: str = "tesseract", language: str = "eng") -> BaseOcrEngine:
    if preferred == "paddle" and PaddleOCR is not None:
        return PaddleOcrEngine(language=language)
    if preferred == "tesseract":
        return TesseractOcrEngine()
    return StubOcrEngine()
