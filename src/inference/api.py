"""
FastAPI ML Inference Endpoints

Provides REST API for document intelligence:
- /ocr - Extract text from images
- /classify - Document type classification
- /extract - Field extraction (NER)
- /summarize - Text summarization
- /analyze - Full pipeline (OCR → classify → extract → summarize)
- /feedback - Submit corrections for learning

Philosophy: Single model, multiple tasks, unified API.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
import logging
import io
from pathlib import Path
import torch

# Import ML modules
try:
    from src.ml.models.puda_model import PudaModel, load_tokenizer
    from src.ml.models.pipeline import DocumentProcessor
    from src.ml.ocr.engine import extract_text_from_file
    MODELS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"ML modules not available: {e}")
    MODELS_AVAILABLE = False
    # Define placeholder types when modules unavailable
    PudaModel = type(None)  # type: ignore
    DocumentProcessor = type(None)  # type: ignore
    load_tokenizer = None  # type: ignore
    extract_text_from_file = None  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Puda ML API",
    description="Document intelligence API: OCR, classification, extraction, summarization",
    version="1.0.0"
)

# CORS middleware for web UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instances (lazy-loaded)
_model: Optional[PudaModel] = None
_tokenizer = None
_processor: Optional[DocumentProcessor] = None


def get_model() -> PudaModel:
    """Lazy-load model on first request."""
    global _model
    if _model is None:
        if not MODELS_AVAILABLE:
            raise HTTPException(status_code=503, detail="ML models not available")
        logger.info("Loading PudaModel...")
        _model = PudaModel(
            model_name="distilbert-base-multilingual-cased",
            use_bilstm=False,  # Faster inference
            dropout=0.0,
            freeze_backbone=False
        )
        _model.eval()
        _model.optimize_for_cpu()  # Apply CPU optimizations
        logger.info(f"Model loaded with {_model.count_parameters():,} parameters")
    return _model


def get_tokenizer():
    """Lazy-load tokenizer on first request."""
    global _tokenizer
    if _tokenizer is None:
        if not MODELS_AVAILABLE:
            raise HTTPException(status_code=503, detail="Tokenizer not available")
        logger.info("Loading tokenizer...")
        _tokenizer = load_tokenizer("distilbert-base-multilingual-cased")
    return _tokenizer


def get_processor() -> DocumentProcessor:
    """Lazy-load processor on first request."""
    global _processor
    if _processor is None:
        if not MODELS_AVAILABLE:
            raise HTTPException(status_code=503, detail="Processor not available")
        logger.info("Loading DocumentProcessor...")
        _processor = DocumentProcessor(
            model=get_model(),
            tokenizer=get_tokenizer(),
            cpu_optimize=True
        )
        logger.info("Processor loaded")
    return _processor


# ==================== Request/Response Models ====================

class TextRequest(BaseModel):
    """Request with pre-extracted text."""
    text: str = Field(..., description="Document text content")
    language: Optional[str] = Field(None, description="Language hint (en, fr, ar)")


class ClassifyResponse(BaseModel):
    """Document classification response."""
    doc_type: str = Field(..., description="Document type (invoice, receipt, etc.)")
    confidence: float = Field(..., description="Classification confidence (0-1)")
    all_scores: Dict[str, float] = Field(..., description="All type probabilities")


class ExtractResponse(BaseModel):
    """Field extraction response."""
    fields: Dict[str, List[Dict[str, Any]]] = Field(..., description="Extracted entities by type")
    count: int = Field(..., description="Total entities extracted")


class SummarizeResponse(BaseModel):
    """Text summarization response."""
    summary: str = Field(..., description="Generated summary")
    method: str = Field(..., description="Summarization method used")


class OCRResponse(BaseModel):
    """OCR extraction response."""
    text: str = Field(..., description="Extracted text")
    confidence: float = Field(..., description="Average OCR confidence")
    language: str = Field(..., description="Detected language")
    word_count: int = Field(..., description="Number of words extracted")


class AnalyzeResponse(BaseModel):
    """Full pipeline analysis response."""
    ocr: Optional[OCRResponse] = Field(None, description="OCR results (if image)")
    classification: ClassifyResponse = Field(..., description="Document classification")
    extraction: ExtractResponse = Field(..., description="Field extraction")
    summary: SummarizeResponse = Field(..., description="Text summary")
    routing: Dict[str, Any] = Field(..., description="Routing decision metrics")
    metrics: Dict[str, Any] = Field(..., description="Processing metrics")


class FeedbackRequest(BaseModel):
    """Correction feedback for learning."""
    text: str = Field(..., description="Original document text")
    corrected_type: Optional[str] = Field(None, description="Corrected document type")
    corrected_fields: Optional[Dict[str, Any]] = Field(None, description="Corrected extracted fields")
    notes: Optional[str] = Field(None, description="Additional feedback notes")


# ==================== Health Check ====================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "models_available": MODELS_AVAILABLE,
        "model_loaded": _model is not None,
        "processor_loaded": _processor is not None
    }


# ==================== OCR Endpoint ====================

@app.post("/ocr", response_model=OCRResponse)
async def ocr_endpoint(
    file: UploadFile = File(..., description="Image file (PNG, JPG, PDF)")
):
    """
    Extract text from image using OCR.
    
    Supports: PNG, JPG, JPEG, PDF
    Languages: English, French, Arabic (auto-detected)
    """
    try:
        # Read uploaded file
        contents = await file.read()
        
        # Save temporarily
        temp_path = Path(f"/tmp/{file.filename}")
        temp_path.write_bytes(contents)
        
        # Extract text
        logger.info(f"Processing OCR for {file.filename}")
        result = extract_text_from_file(str(temp_path))
        
        # Clean up
        temp_path.unlink()
        
        return OCRResponse(
            text=result["text"],
            confidence=result["confidence"],
            language=result.get("language", "unknown"),
            word_count=len(result["text"].split())
        )
        
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


# ==================== Classification Endpoint ====================

@app.post("/classify", response_model=ClassifyResponse)
def classify_endpoint(req: TextRequest):
    """
    Classify document type.
    
    Returns document type (invoice, receipt, contract, etc.) with confidence scores.
    """
    try:
        model = get_model()
        tokenizer = get_tokenizer()
        
        # Tokenize
        inputs = tokenizer(
            req.text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        # Predict
        doc_types, confidences = model.predict_classification(
            inputs["input_ids"],
            inputs["attention_mask"]
        )
        
        # Get all scores
        with torch.no_grad():
            outputs = model(inputs["input_ids"], inputs["attention_mask"])
            probs = torch.softmax(outputs["classification_logits"], dim=-1)[0]
            all_scores = {
                doc_type: float(prob)
                for doc_type, prob in zip(model.DOC_TYPES, probs)
            }
        
        return ClassifyResponse(
            doc_type=doc_types[0],
            confidence=float(confidences[0]),
            all_scores=all_scores
        )
        
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


# ==================== Extraction Endpoint ====================

@app.post("/extract", response_model=ExtractResponse)
def extract_endpoint(req: TextRequest):
    """
    Extract structured fields from text.
    
    Extracts: dates, amounts, invoice numbers, names, organizations, addresses, emails, phones.
    Combines pattern matching + NER model predictions.
    """
    try:
        processor = get_processor()
        
        # Process text (extraction only)
        result = processor.process_text(req.text)
        
        # Format response
        fields = result["extraction"]["entities"]
        total_count = sum(len(entities) for entities in fields.values())
        
        return ExtractResponse(
            fields=fields,
            count=total_count
        )
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


# ==================== Summarization Endpoint ====================

@app.post("/summarize", response_model=SummarizeResponse)
def summarize_endpoint(req: TextRequest):
    """
    Generate text summary.
    
    Uses transformer model if available, otherwise heuristic extraction.
    """
    try:
        processor = get_processor()
        
        # Process text (for summarization)
        result = processor.process_text(req.text)
        
        return SummarizeResponse(
            summary=result["summary"]["text"],
            method=result["summary"]["method"]
        )
        
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")


# ==================== Full Pipeline Endpoint ====================

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(
    text: Optional[str] = None,
    file: Optional[UploadFile] = File(None)
):
    """
    Full document analysis pipeline.
    
    If file provided: OCR → classify → extract → summarize
    If text provided: classify → extract → summarize
    
    Returns comprehensive analysis with routing confidence.
    """
    try:
        processor = get_processor()
        
        # Handle image input
        ocr_result = None
        if file:
            # Process OCR
            ocr_response = await ocr_endpoint(file)
            ocr_result = ocr_response
            text = ocr_response.text
        
        if not text:
            raise HTTPException(status_code=400, detail="Either text or file must be provided")
        
        # Run full pipeline
        logger.info("Running full pipeline analysis")
        result = processor.process_text(text)
        
        # Format classification response
        classification = ClassifyResponse(
            doc_type=result["classification"]["doc_type"],
            confidence=result["classification"]["confidence"],
            all_scores=result["classification"].get("all_scores", {})
        )
        
        # Format extraction response
        extraction = ExtractResponse(
            fields=result["extraction"]["entities"],
            count=sum(len(v) for v in result["extraction"]["entities"].values())
        )
        
        # Format summary response
        summary = SummarizeResponse(
            summary=result["summary"]["text"],
            method=result["summary"]["method"]
        )
        
        return AnalyzeResponse(
            ocr=ocr_result,
            classification=classification,
            extraction=extraction,
            summary=summary,
            routing=result.get("routing", {}),
            metrics=result.get("metrics", {})
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


# ==================== Feedback Endpoint ====================

@app.post("/feedback")
def feedback_endpoint(req: FeedbackRequest):
    """
    Submit correction feedback for model learning.
    
    Stores corrections for future retraining cycles.
    """
    try:
        # TODO: Implement feedback storage
        # For now, just log and acknowledge
        logger.info(f"Received feedback: type={req.corrected_type}, fields={len(req.corrected_fields or {})}")
        
        # Store feedback to database/file for learning system
        feedback_data = {
            "text": req.text,
            "corrected_type": req.corrected_type,
            "corrected_fields": req.corrected_fields,
            "notes": req.notes,
            "timestamp": None  # Add timestamp
        }
        
        # TODO: Save to feedback storage
        # feedback_storage.save(feedback_data)
        
        return {
            "status": "received",
            "message": "Feedback stored for learning. Thank you!",
            "feedback_id": "placeholder"  # TODO: Generate ID
        }
        
    except Exception as e:
        logger.error(f"Feedback storage failed: {e}")
        raise HTTPException(status_code=500, detail=f"Feedback storage failed: {str(e)}")


# ==================== Model Management ====================

@app.post("/reload")
def reload_models():
    """
    Reload models (for updates/retraining).
    
    Admin endpoint to refresh model weights without restarting server.
    """
    global _model, _tokenizer, _processor
    
    try:
        logger.info("Reloading models...")
        _model = None
        _tokenizer = None
        _processor = None
        
        # Force reload
        get_model()
        get_tokenizer()
        get_processor()
        
        return {
            "status": "reloaded",
            "message": "Models successfully reloaded"
        }
        
    except Exception as e:
        logger.error(f"Model reload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reload failed: {str(e)}")


# ==================== Startup/Shutdown ====================

@app.on_event("startup")
async def startup_event():
    """Warm up models on server start."""
    logger.info("Starting Puda ML API...")
    if MODELS_AVAILABLE:
        try:
            # Pre-load models
            logger.info("Pre-loading models...")
            get_processor()
            logger.info("Models ready")
        except Exception as e:
            logger.warning(f"Model pre-load failed (will lazy-load): {e}")
    else:
        logger.warning("ML modules not available - API running in limited mode")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Puda ML API...")


if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
