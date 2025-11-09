# OCR Layer

Provides text extraction from cleaned page images via pluggable engines.

## Engines Supported
- Tesseract (default) via `pytesseract`
- PaddleOCR (optional, heavier dependency) – uncomment in `requirements.txt` to enable
- Stub (fallback) returns empty text and allows pipeline continuity

## Configuration
Use `build_default_pipeline(engine_preference="tesseract", language="eng")` to set engine and language.

Tesseract language codes can be combined: `eng+spa+fra`. Ensure corresponding language data files are installed in Tesseract `tessdata` directory.

PaddleOCR language codes differ (e.g., `en`, `ch`, `fr`). Only one primary language at init.

### Windows Tesseract Path
If Tesseract isn't on PATH, set before pipeline creation:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
```

## Processor Behavior
`OcrProcessor` runs after image cleanup:
1. Chooses cleaned image if available, else original.
2. Invokes engine with specified `language`.
3. Persists sidecar UTF-8 text file `<image_stem>_ocr.txt`.
4. Stores metadata under `artifact.metadata["processing"]["ocr"]`:
   - `engine`, `language`, `duration_ms`, `status`, `char_count`, optional `confidence`.

Statuses:
- `ok` – extraction succeeded
- `missing` – image path absent
- `unavailable` – engine dependency not installed
- `stub` – stub engine used
- `error:<Type>` – unexpected engine error
- `skipped_existing` – artifact already had OCR text
- `skipped_missing_image` – no image to process

## Multilingual Support
Tesseract: combine codes with `+`. Install language packs from official releases.
PaddleOCR: initialize with single `lang` parameter; multilingual extension requires separate passes.

## Extending
Add new engine: implement `BaseOcrEngine.extract_text` returning `OcrResult`.
Register via logic in `build_engine` (in `src/processing/ocr_engines.py`).

## Testing
`test_ocr_processor.py` uses stub engine to avoid external dependencies. Real engine tests can be added with small synthetic images and assertions on non-empty output.

## Roadmap
- Confidence normalization across engines
- Block/line bounding box metadata
- Automatic orientation detection & re-run
- Caching repeated pages by content hash
- Language auto-detection fallback
