# 📋 Phase 1: Document and Text Intelligence

**Status:** Implementation Ready  
**Date:** November 8, 2025  
**Version:** 1.0

---

## 🎯 Functional Scope

**Core Pipeline:**
```
OCR Text In → Classify → Extract Key Data → Summarize
```

**Key Features:**
- ✅ Multilingual support: **English + French + Arabic**
- ✅ Document classification (invoice, receipt, contract, etc.)
- ✅ Key data extraction (dates, amounts, names, addresses)
- ✅ Automatic summarization
- ✅ Learning from corrected outputs

---

## 📊 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Phase 1: Document Intelligence               │
└─────────────────────────────────────────────────────────────────┘

   ┌───────────────┐
   │  Physical     │
   │  Document     │
   └───────┬───────┘
           │
           ▼
   ┌───────────────────────────────────────────────┐
   │  Step 1: OCR (Tesseract)                      │
   │  • Languages: eng+fra+ara                     │
   │  • Preprocessing: deskew, denoise, contrast   │
   │  • Output: Raw text + confidence + layout     │
   └───────┬───────────────────────────────────────┘
           │
           ▼
   ┌───────────────────────────────────────────────┐
   │  Step 2: Classify Document Type               │
   │  • Types: invoice, receipt, contract, form,   │
   │    letter, memo, report, other                │
   │  • Model: MobileNetV3 (image) + DistilBERT    │
   │    (text)                                     │
   │  • Confidence threshold: 0.7                  │
   └───────┬───────────────────────────────────────┘
           │
           ▼
   ┌───────────────────────────────────────────────┐
   │  Step 3: Extract Key Data                     │
   │  • Dates: 2025-11-08, Nov 8 2025, etc.        │
   │  • Amounts: $1,500.00, €500, 200 د.إ         │
   │  • Names: Person/company names                │
   │  • Addresses: Street, city, postal code       │
   │  • Custom fields per doc type                 │
   └───────┬───────────────────────────────────────┘
           │
           ▼
   ┌───────────────────────────────────────────────┐
   │  Step 4: Summarize                            │
   │  • Generate 2-3 sentence summary              │
   │  • Model: mT5-small (multilingual)            │
   │  • Preserve key information                   │
   └───────┬───────────────────────────────────────┘
           │
           ▼
   ┌───────────────────────────────────────────────┐
   │  Output: Structured Document                  │
   │  {                                            │
   │    "text": "Invoice for...",                  │
   │    "doc_type": "invoice",                     │
   │    "confidence": 0.95,                        │
   │    "extracted": {                             │
   │      "date": "2025-11-08",                    │
   │      "amount": "$1,500.00",                   │
   │      "vendor": "ACME Corp"                    │
   │    },                                         │
   │    "summary": "Invoice from ACME Corp for..."│
   │  }                                            │
   └───────────────────────────────────────────────┘
           │
           ▼
   ┌───────────────────────────────────────────────┐
   │  Learning Loop: User Corrections              │
   │  • User corrects extracted data               │
   │  • Store correction in feedback DB            │
   │  • Retrain models weekly/monthly              │
   │  • Track accuracy improvements                │
   └───────────────────────────────────────────────┘
```

---

## 🔤 Multilingual Support

### Languages

| Language | Tesseract Code | Script | Support Level |
|----------|---------------|--------|---------------|
| English  | `eng`         | Latin  | Full          |
| French   | `fra`         | Latin  | Full          |
| Arabic   | `ara`         | Arabic | Basic (RTL)   |

### OCR Configuration
```python
# Tesseract multi-language OCR
tesseract_config = "--psm 1 -l eng+fra+ara"

# PSM 1: Automatic page segmentation with OSD
# Detects orientation and script for mixed documents
```

### Text Processing
```python
# Language detection
from langdetect import detect

text = "Facture pour €500"
lang = detect(text)  # 'fr'

# Handle RTL (Arabic)
if lang == 'ar':
    text = apply_rtl_formatting(text)
```

### Extraction Patterns

**Dates (Multilingual):**
- English: `Nov 8, 2025`, `11/08/2025`, `2025-11-08`
- French: `8 novembre 2025`, `08/11/2025`
- Arabic: `٨ نوفمبر ٢٠٢٥`, `٢٠٢٥/١١/٠٨`

**Currency:**
- USD: `$1,500.00`, `USD 1500`
- EUR: `€500,00`, `500 EUR`
- AED: `1500 د.إ`, `AED 1500` (Arabic Dirham)

**Names:**
- Latin script: Regex `([A-Z][a-z]+ )+[A-Z][a-z]+`
- Arabic script: NER model with Arabic support

---

## 📦 Document Types

### Classification Labels

1. **Invoice** — Bill for goods/services
   - Key fields: vendor, amount, date, invoice_number
   - Confidence > 0.8 → auto-route
   
2. **Receipt** — Proof of payment
   - Key fields: vendor, amount, date, payment_method
   - Confidence > 0.8 → auto-route
   
3. **Contract** — Legal agreement
   - Key fields: parties, date, terms, signatures
   - Confidence > 0.6 → manual review (legal sensitivity)
   
4. **Form** — Structured questionnaire
   - Key fields: form_type, fields, signatures
   - Confidence > 0.7 → auto-route
   
5. **Letter** — Correspondence
   - Key fields: sender, recipient, date, subject
   - Confidence > 0.7 → auto-route
   
6. **Memo** — Internal communication
   - Key fields: from, to, date, subject
   - Confidence > 0.7 → auto-route
   
7. **Report** — Analytical document
   - Key fields: title, date, author, summary
   - Confidence > 0.6 → manual review
   
8. **Other** — Unclassified
   - Confidence < 0.6 → QC review

### Routing Rules

```python
def route_document(doc_type: str, confidence: float) -> str:
    """Determine routing based on type and confidence."""
    
    # High confidence → automatic
    if confidence > 0.9:
        return "auto"
    
    # Legal/sensitive documents → manual review
    if doc_type in ["contract", "report"] and confidence > 0.6:
        return "manual"
    
    # Medium confidence → manual review
    if confidence > 0.7:
        return "manual"
    
    # Low confidence → QC
    return "qc"
```

---

## 🔍 Key Data Extraction

### Extraction Engine

**Architecture:**
```
Input Text → Language Detection → Entity Recognition → Pattern Matching → Structured Output
```

**Methods:**

1. **NER (Named Entity Recognition)**
   - Use Transformers NER models
   - Multilingual: `bert-base-multilingual-cased`
   - Extract: PERSON, ORG, LOCATION, DATE, MONEY

2. **Pattern Matching**
   - Regex for structured data (dates, amounts, IDs)
   - Locale-aware formatting
   - Validation and normalization

3. **Layout Analysis**
   - Key-value pair extraction (OCR coordinates)
   - Table extraction
   - Form field detection

### Extracted Fields

**Universal Fields (All Documents):**
```json
{
  "language": "en",
  "date": "2025-11-08",
  "text_length": 1234,
  "word_count": 200,
  "confidence": 0.95
}
```

**Invoice-Specific:**
```json
{
  "invoice_number": "INV-2025-001",
  "vendor": "ACME Corporation",
  "amount": 1500.00,
  "currency": "USD",
  "due_date": "2025-12-08",
  "line_items": [
    {"description": "Services", "amount": 1500.00}
  ]
}
```

**Receipt-Specific:**
```json
{
  "vendor": "Coffee Shop",
  "amount": 5.50,
  "currency": "USD",
  "payment_method": "Credit Card",
  "items": ["Latte", "Croissant"]
}
```

**Contract-Specific:**
```json
{
  "parties": ["Company A", "Company B"],
  "effective_date": "2025-11-08",
  "expiration_date": "2026-11-08",
  "contract_type": "Service Agreement",
  "key_terms": ["Payment terms", "Termination clause"]
}
```

### Extraction Confidence

```python
class ExtractionResult:
    field: str
    value: Any
    confidence: float  # 0.0 to 1.0
    method: str        # "ner", "regex", "layout"
    requires_review: bool  # True if confidence < 0.8
```

---

## 📝 Summarization

### Summarization Engine

**Model:** `google/mt5-small` (Multilingual T5)
- Parameters: ~300M
- Languages: 101+ languages including EN, FR, AR
- Task: Abstractive summarization

**Configuration:**
```python
from transformers import MT5ForConditionalGeneration, T5Tokenizer

model = MT5ForConditionalGeneration.from_pretrained("google/mt5-small")
tokenizer = T5Tokenizer.from_pretrained("google/mt5-small")

def summarize(text: str, max_length: int = 100) -> str:
    """Generate 2-3 sentence summary."""
    
    # Prefix for summarization task
    input_text = f"summarize: {text}"
    
    inputs = tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True)
    outputs = model.generate(
        inputs.input_ids,
        max_length=max_length,
        min_length=20,
        length_penalty=2.0,
        num_beams=4,
        early_stopping=True
    )
    
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return summary
```

### Summary Types

**Short Summary (2-3 sentences):**
- Who: Parties involved
- What: Document purpose
- When: Date/timeframe
- How much: Key amounts

**Example:**
> Invoice from ACME Corp dated Nov 8, 2025 for $1,500.00. Services rendered include consulting and development. Payment due Dec 8, 2025.

**Keywords Extraction:**
- Top 5-10 keywords from document
- Used for search indexing
- Multilingual support

---

## 🎓 Learning from Corrections

### Feedback Loop Architecture

```
User Correction → Store in DB → Aggregate Corrections → Retrain Model → Deploy Updated Model
```

### Feedback Database Schema

```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY,
    document_id TEXT NOT NULL,
    field_name TEXT NOT NULL,           -- "doc_type", "amount", etc.
    predicted_value TEXT,               -- Original ML prediction
    corrected_value TEXT NOT NULL,      -- User's correction
    confidence FLOAT,                   -- Original confidence
    user_id TEXT,                       -- Who made correction
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    model_version TEXT,                 -- Which model version predicted
    language TEXT                       -- Document language
);

CREATE INDEX idx_field_corrections ON feedback(field_name);
CREATE INDEX idx_timestamp ON feedback(timestamp);
```

### Learning Strategies

**1. Online Learning (Immediate)**
- Update extraction patterns based on corrections
- Add new regex patterns for missed entities
- Update validation rules

**2. Periodic Retraining (Weekly/Monthly)**
- Aggregate all corrections
- Fine-tune classification model on corrected data
- Retrain NER model with corrected entities
- Validate on test set before deployment

**3. Active Learning**
- Identify low-confidence predictions
- Prioritize for human review
- Use corrections to improve uncertain cases

### Retraining Pipeline

```python
def retrain_classifier(feedback_data: pd.DataFrame):
    """Retrain document classifier with corrections."""
    
    # Load corrections
    corrections = feedback_data[feedback_data['field_name'] == 'doc_type']
    
    # Create training data
    X = load_document_features(corrections['document_id'])
    y = corrections['corrected_value']
    
    # Fine-tune model
    model = load_model("classifier.pt")
    optimizer = Adam(model.parameters(), lr=1e-5)
    
    for epoch in range(5):
        for batch in create_batches(X, y):
            loss = train_step(model, batch, optimizer)
    
    # Validate
    accuracy = validate(model, test_data)
    
    if accuracy > previous_accuracy:
        # Deploy new model
        save_model(model, f"classifier_v{version}.pt")
        export_model(model, f"classifier_v{version}.onnx")
    
    return accuracy
```

### Tracking Improvements

```python
# Accuracy metrics over time
metrics = {
    "classification_accuracy": [
        {"date": "2025-11-01", "accuracy": 0.85},
        {"date": "2025-11-08", "accuracy": 0.89},  # After retraining
        {"date": "2025-11-15", "accuracy": 0.91}
    ],
    "extraction_precision": {
        "dates": 0.95,
        "amounts": 0.92,
        "names": 0.88
    },
    "corrections_per_week": 45,
    "auto_routing_rate": 0.78  # Percentage sent to auto vs manual
}
```

---

## 🚀 FastAPI Endpoints

### API Structure

```python
from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel

app = FastAPI(title="Puda ML API - Phase 1")

# ============================================
# Models
# ============================================

class OCRResponse(BaseModel):
    text: str
    language: str
    confidence: float
    layout: dict

class ClassificationResponse(BaseModel):
    doc_type: str
    confidence: float
    routing: str  # "auto", "manual", "qc"

class ExtractionResponse(BaseModel):
    fields: dict
    confidence_scores: dict
    requires_review: list[str]

class SummaryResponse(BaseModel):
    summary: str
    keywords: list[str]
    length_reduction: float  # e.g., 0.85 = 85% shorter

class FeedbackRequest(BaseModel):
    document_id: str
    field_name: str
    predicted_value: str
    corrected_value: str

# ============================================
# Endpoints
# ============================================

@app.post("/api/v1/ocr", response_model=OCRResponse)
async def ocr_document(
    file: UploadFile = File(...),
    languages: str = "eng+fra+ara"
):
    """
    Extract text from document image using OCR.
    
    Supports: English, French, Arabic
    """
    # Load image
    image = await file.read()
    
    # Run OCR
    result = ocr_engine.extract_text(image, languages=languages)
    
    return OCRResponse(
        text=result['text'],
        language=result['detected_language'],
        confidence=result['confidence'],
        layout=result['layout']
    )


@app.post("/api/v1/classify", response_model=ClassificationResponse)
async def classify_document(
    file: UploadFile = File(None),
    text: str = Form(None)
):
    """
    Classify document type.
    
    Input: Image or text
    Output: doc_type, confidence, routing
    """
    if file:
        # Image classification
        image = await file.read()
        result = classifier.predict_from_image(image)
    else:
        # Text classification
        result = classifier.predict_from_text(text)
    
    routing = route_document(result['doc_type'], result['confidence'])
    
    return ClassificationResponse(
        doc_type=result['doc_type'],
        confidence=result['confidence'],
        routing=routing
    )


@app.post("/api/v1/extract", response_model=ExtractionResponse)
async def extract_data(
    text: str = Form(...),
    doc_type: str = Form(...),
    language: str = Form("en")
):
    """
    Extract key data from document text.
    
    Extracts: dates, amounts, names, addresses, custom fields
    """
    # Run extraction
    result = extractor.extract(text, doc_type=doc_type, language=language)
    
    # Identify low-confidence fields
    review_needed = [
        field for field, conf in result['confidence_scores'].items()
        if conf < 0.8
    ]
    
    return ExtractionResponse(
        fields=result['fields'],
        confidence_scores=result['confidence_scores'],
        requires_review=review_needed
    )


@app.post("/api/v1/summarize", response_model=SummaryResponse)
async def summarize_document(
    text: str = Form(...),
    max_length: int = Form(100)
):
    """
    Generate summary of document text.
    
    Output: 2-3 sentence summary + keywords
    """
    # Generate summary
    summary = summarizer.summarize(text, max_length=max_length)
    
    # Extract keywords
    keywords = keyword_extractor.extract(text, top_k=10)
    
    # Calculate reduction
    reduction = 1 - (len(summary) / len(text))
    
    return SummaryResponse(
        summary=summary,
        keywords=keywords,
        length_reduction=reduction
    )


@app.post("/api/v1/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit user correction for learning.
    
    Stores correction in database for model retraining.
    """
    # Store in database
    feedback_db.insert({
        "document_id": feedback.document_id,
        "field_name": feedback.field_name,
        "predicted_value": feedback.predicted_value,
        "corrected_value": feedback.corrected_value,
        "timestamp": datetime.now(),
        "model_version": current_model_version
    })
    
    return {"status": "success", "message": "Feedback recorded"}


@app.post("/api/v1/process")
async def process_document_full(file: UploadFile = File(...)):
    """
    Full pipeline: OCR → Classify → Extract → Summarize
    
    Returns complete document analysis.
    """
    image = await file.read()
    
    # Step 1: OCR
    ocr_result = ocr_engine.extract_text(image)
    text = ocr_result['text']
    language = ocr_result['detected_language']
    
    # Step 2: Classify
    classification = classifier.predict_from_text(text)
    doc_type = classification['doc_type']
    
    # Step 3: Extract
    extraction = extractor.extract(text, doc_type=doc_type, language=language)
    
    # Step 4: Summarize
    summary = summarizer.summarize(text)
    
    # Combine results
    return {
        "ocr": ocr_result,
        "classification": classification,
        "extraction": extraction,
        "summary": summary,
        "routing": route_document(doc_type, classification['confidence'])
    }


@app.get("/api/v1/metrics")
async def get_metrics():
    """Get model performance metrics."""
    return {
        "classification_accuracy": get_classification_accuracy(),
        "extraction_precision": get_extraction_precision(),
        "corrections_this_week": count_recent_corrections(),
        "documents_processed": count_processed_documents(),
        "auto_routing_rate": calculate_auto_routing_rate()
    }
```

### API Usage Example

```python
import requests

# Full document processing
with open("invoice.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8081/api/v1/process",
        files={"file": f}
    )

result = response.json()
print(f"Type: {result['classification']['doc_type']}")
print(f"Amount: {result['extraction']['fields']['amount']}")
print(f"Summary: {result['summary']['summary']}")

# Submit correction
requests.post(
    "http://localhost:8081/api/v1/feedback",
    json={
        "document_id": "doc_12345",
        "field_name": "amount",
        "predicted_value": "$1,500.00",
        "corrected_value": "$1,550.00"
    }
)
```

---

## 🗄️ Data Storage

### Document Processing Database

```sql
-- Processed documents
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    filename TEXT,
    upload_date DATETIME,
    ocr_text TEXT,
    language TEXT,
    doc_type TEXT,
    classification_confidence FLOAT,
    routing TEXT,
    extracted_data JSON,
    summary TEXT,
    status TEXT,  -- "processed", "reviewing", "approved"
    user_id TEXT
);

-- OCR results
CREATE TABLE ocr_results (
    id INTEGER PRIMARY KEY,
    document_id TEXT,
    raw_text TEXT,
    confidence FLOAT,
    language TEXT,
    layout_data JSON,
    processing_time_ms FLOAT,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- Extractions
CREATE TABLE extractions (
    id INTEGER PRIMARY KEY,
    document_id TEXT,
    field_name TEXT,
    value TEXT,
    confidence FLOAT,
    extraction_method TEXT,
    requires_review BOOLEAN,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- Processing metrics
CREATE TABLE processing_metrics (
    id INTEGER PRIMARY KEY,
    date DATE,
    documents_processed INTEGER,
    avg_classification_confidence FLOAT,
    avg_extraction_confidence FLOAT,
    auto_routed INTEGER,
    manual_routed INTEGER,
    qc_routed INTEGER
);
```

---

## 🏗️ File Structure

```
Puda/
├── src/
│   ├── ml/
│   │   ├── ocr/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py          # Tesseract OCR wrapper
│   │   │   ├── preprocessor.py    # Image preprocessing
│   │   │   └── layout.py          # Layout analysis
│   │   │
│   │   ├── classification/
│   │   │   ├── __init__.py
│   │   │   ├── classifier.py      # Document classifier
│   │   │   └── router.py          # Routing logic
│   │   │
│   │   ├── extraction/
│   │   │   ├── __init__.py
│   │   │   ├── extractor.py       # Main extraction engine
│   │   │   ├── ner.py             # Named entity recognition
│   │   │   ├── patterns.py        # Regex patterns
│   │   │   └── multilingual.py    # Language-specific logic
│   │   │
│   │   ├── summarization/
│   │   │   ├── __init__.py
│   │   │   ├── summarizer.py      # Text summarization
│   │   │   └── keywords.py        # Keyword extraction
│   │   │
│   │   └── feedback/
│   │       ├── __init__.py
│   │       ├── storage.py         # Feedback database
│   │       └── retrainer.py       # Model retraining
│   │
│   └── api/
│       ├── ml_api.py              # FastAPI Phase 1 endpoints
│       └── dashboard_api.py       # Existing Flask dashboard
│
├── models/
│   ├── classifier_v1.onnx
│   ├── ner_model.onnx
│   └── summarizer/               # MT5 model
│
├── data/
│   ├── feedback.db               # Corrections database
│   ├── documents.db              # Processed documents
│   └── training/                 # Training data
│
├── tests/
│   ├── test_ocr.py
│   ├── test_classification.py
│   ├── test_extraction.py
│   ├── test_summarization.py
│   └── test_feedback.py
│
└── PHASE1_SPEC.md                # This document
```

---

## 📈 Success Metrics

### Phase 1 Goals

| Metric | Target | Measurement |
|--------|--------|-------------|
| Classification Accuracy | >85% | Validated on test set |
| Extraction Precision | >90% | Per-field accuracy |
| OCR Confidence | >95% | Average confidence score |
| Auto-routing Rate | >70% | Documents sent to auto |
| User Corrections | <10%/doc | Fields requiring correction |
| Summarization Quality | ROUGE >0.4 | Compared to human summaries |
| Processing Speed | <5s/doc | End-to-end pipeline |
| Multilingual Accuracy | >80% | FR/AR performance vs EN |

### Performance Tracking

```python
# Weekly metrics report
{
    "week": "2025-11-08",
    "documents_processed": 1250,
    "classification_accuracy": 0.87,
    "extraction_precision": {
        "dates": 0.95,
        "amounts": 0.92,
        "names": 0.88,
        "addresses": 0.85
    },
    "routing": {
        "auto": 875,    # 70%
        "manual": 250,  # 20%
        "qc": 125       # 10%
    },
    "languages": {
        "en": 800,      # 64%
        "fr": 350,      # 28%
        "ar": 100       # 8%
    },
    "corrections_submitted": 95,
    "avg_processing_time": 4.2  # seconds
}
```

---

## 🚦 Implementation Phases

### Phase 1a: Core Pipeline (Week 1-2)
- ✅ OCR engine with multilingual support
- ✅ Document classifier (8 types)
- ✅ Basic extraction (dates, amounts, names)
- ✅ Simple summarization
- ✅ FastAPI endpoints

### Phase 1b: Learning System (Week 3-4)
- ✅ Feedback database
- ✅ Correction UI in process.html
- ✅ Retraining pipeline
- ✅ Metrics tracking

### Phase 1c: Optimization (Week 5-6)
- ✅ Model fine-tuning on corrections
- ✅ Improved extraction patterns
- ✅ ONNX export for production
- ✅ Performance optimization (<3s/doc)

### Phase 1d: Multilingual Enhancement (Week 7-8)
- ✅ Arabic RTL support
- ✅ French locale handling
- ✅ Cross-lingual entity matching
- ✅ Language-specific validation

---

## 🎓 Training Data Requirements

### Initial Dataset

| Document Type | Quantity | Languages |
|--------------|----------|-----------|
| Invoices | 500 | EN: 300, FR: 150, AR: 50 |
| Receipts | 400 | EN: 250, FR: 100, AR: 50 |
| Contracts | 200 | EN: 150, FR: 40, AR: 10 |
| Forms | 300 | EN: 200, FR: 80, AR: 20 |
| Letters | 200 | EN: 120, FR: 60, AR: 20 |
| Other | 400 | Mixed |

**Total:** 2,000 documents

### Data Augmentation
- Rotation: ±5 degrees
- Noise: Gaussian noise
- Brightness: ±20%
- Contrast: ±20%
- Synthetic generation: 20% of dataset

### Annotation
- Document type labels
- Bounding boxes for key fields
- Ground truth text for OCR validation
- Human-written summaries for evaluation

---

## 🔐 Integration with Existing System

### Authentication
- Use existing user_manager.py authorization
- ML API requires valid session token
- Role-based access: operators can process, admins can retrain

### Dashboard Integration
```javascript
// process.html - Call ML API
async function processDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Call ML API
    const response = await fetch('http://localhost:8081/api/v1/process', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${sessionToken}`
        },
        body: formData
    });
    
    const result = await response.json();
    
    // Display results
    displayClassification(result.classification);
    displayExtraction(result.extraction);
    displaySummary(result.summary);
    
    // Allow corrections
    enableCorrectionUI(result);
}
```

### Physical Flow Integration
- Processed documents route to appropriate physical zone
- QC queue for low-confidence predictions
- Feedback from QC operators stored in learning system

---

## 📚 Dependencies

### New Requirements

```txt
# OCR
pytesseract>=0.3.10
tesseract>=5.3.0  # System dependency
Pillow>=10.0.0

# Language Detection
langdetect>=1.0.9

# NER and Extraction
spacy>=3.7.0
spacy-transformers>=1.3.0

# Multilingual Models
# (Already in requirements.txt)
transformers>=4.35.0

# Summarization (already included via transformers)
# MT5 model loaded via transformers

# Additional
python-dateutil>=2.8.2  # Date parsing
phonenumbers>=8.13.0    # Phone number extraction
```

---

## ✅ Next Steps

1. **Install Tesseract OCR** (system dependency)
   ```powershell
   # Windows: Download from GitHub
   # https://github.com/UB-Mannheim/tesseract/wiki
   
   # Add language data
   # Download eng.traineddata, fra.traineddata, ara.traineddata
   ```

2. **Create OCR Module** (`src/ml/ocr/engine.py`)

3. **Build Document Classifier** (fine-tune MobileNetV3 or ViT)

4. **Implement Extraction Engine** (NER + patterns)

5. **Add Summarization** (load MT5-small)

6. **Create FastAPI Endpoints** (`ml_api.py`)

7. **Update UI** (process.html with correction interface)

8. **Test Full Pipeline** (end-to-end)

---

**Phase 1 Status:** Ready for implementation 🚀
