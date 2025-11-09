"""
Document intelligence pipeline using PudaModel.

Combines OCR → Tokenization → PudaModel → JSON output with confidence scores.
"""

import torch
from typing import Dict, List, Optional, Union
import logging
from pathlib import Path
import json
import numpy as np

from ..ocr import OCREngine, OCRResult
from .puda_model import PudaModel, load_tokenizer

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    End-to-end document processing pipeline.
    
    Pipeline:
        [Image/PDF] → OCR → Tokenization → PudaModel → JSON output
    """
    
    def __init__(
        self,
        model: Optional[PudaModel] = None,
        tokenizer = None,
        ocr_engine: Optional[OCREngine] = None,
        device: str = 'cpu'
    ):
        """
        Initialize document processor.
        
        Args:
            model: PudaModel instance (creates default if None)
            tokenizer: Tokenizer instance (loads default if None)
            ocr_engine: OCR engine (creates default if None)
            device: Device to run model on ('cpu' or 'cuda')
        """
        self.device = device
        
        # Load or create model
        if model is None:
            from .puda_model import create_puda_model
            model = create_puda_model()
            logger.info("Created default PudaModel")
        
        self.model = model.to(device)
        self.model.eval()
        
        # Load tokenizer
        if tokenizer is None:
            tokenizer = load_tokenizer()
        self.tokenizer = tokenizer
        
        # Load OCR engine
        if ocr_engine is None:
            ocr_engine = OCREngine(
                languages='eng+fra+ara',
                preprocess=True,
                tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )
        self.ocr_engine = ocr_engine
        
        logger.info(f"Initialized DocumentProcessor on device: {device}")
    
    def process_image(
        self,
        image_path: str,
        include_ocr: bool = True,
        include_embeddings: bool = False
    ) -> Dict:
        """
        Process document image through full pipeline.
        
        Args:
            image_path: Path to image file
            include_ocr: Include OCR results in output
            include_embeddings: Include model embeddings in output
        
        Returns:
            Dictionary with:
            - ocr: OCR results (if include_ocr=True)
            - text: Extracted text
            - classification: Document type classification
            - extraction: Extracted entities
            - embeddings: Model embeddings (if include_embeddings=True)
            - confidence: Overall confidence score
        """
        logger.info(f"Processing image: {image_path}")
        
        # Step 1: OCR
        ocr_result = self.ocr_engine.extract_text_from_file(image_path)
        text = ocr_result.text
        
        logger.info(f"OCR extracted {len(text)} characters")
        
        # Step 2: Process text through model
        result = self.process_text(
            text,
            include_embeddings=include_embeddings
        )
        
        # Add OCR results if requested
        if include_ocr:
            result['ocr'] = {
                'text': ocr_result.text,
                'confidence': float(ocr_result.confidence),
                'language': ocr_result.language,
                'words_detected': len(ocr_result.layout['words']),
                'processing_time_ms': ocr_result.processing_time_ms
            }
        
        return result
    
    def process_text(
        self,
        text: str,
        include_embeddings: bool = False
    ) -> Dict:
        """
        Process text through PudaModel.
        
        Args:
            text: Input text (from OCR or direct input)
            include_embeddings: Include model embeddings
        
        Returns:
            Dictionary with classification, extraction, and confidence
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        # Move to device
        input_ids = inputs['input_ids'].to(self.device)
        attention_mask = inputs['attention_mask'].to(self.device)
        
        # Get tokens for extraction
        tokens = self.tokenizer.convert_ids_to_tokens(input_ids[0])
        
        # Forward pass
        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                return_embeddings=include_embeddings
            )
        
        # Classification
        classification_logits = outputs['classification_logits']
        probs = torch.softmax(classification_logits, dim=-1)
        confidence, predicted = torch.max(probs, dim=-1)
        
        doc_type = self.model.DOC_TYPES[predicted[0].item()]
        doc_confidence = confidence[0].item()
        
        # Extraction
        extraction_logits = outputs['extraction_logits']
        extraction_probs = torch.softmax(extraction_logits, dim=-1)
        extraction_confidence, extraction_predicted = torch.max(extraction_probs, dim=-1)
        
        entities = self.model._extract_entities(
            tokens,
            extraction_predicted[0].cpu().numpy(),
            extraction_confidence[0].cpu().numpy(),
            attention_mask[0].cpu().numpy()
        )
        
        # Calculate overall confidence (weighted average)
        # Classification has higher weight since it's more reliable
        overall_confidence = (doc_confidence * 0.7) + (
            float(np.mean([c for ents in entities.values() for _, _, c in ents])) * 0.3
            if any(entities.values()) else 0.0
        )
        
        result = {
            'text': text,
            'classification': {
                'doc_type': doc_type,
                'confidence': float(doc_confidence),
                'all_scores': {
                    self.model.DOC_TYPES[i]: float(probs[0][i])
                    for i in range(len(self.model.DOC_TYPES))
                }
            },
            'extraction': {
                entity_type: [
                    {'text': txt, 'confidence': float(conf)}
                    for txt, _, conf in entity_list
                ]
                for entity_type, entity_list in entities.items()
                if entity_list  # Only include non-empty
            },
            'confidence': float(overall_confidence)
        }
        
        # Add embeddings if requested
        if include_embeddings:
            result['embeddings'] = outputs['embeddings'][0].cpu().numpy().tolist()
        
        return result
    
    def process_batch(
        self,
        texts: List[str],
        batch_size: int = 8
    ) -> List[Dict]:
        """
        Process multiple texts in batches.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
        
        Returns:
            List of result dictionaries
        """
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch_texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            
            input_ids = inputs['input_ids'].to(self.device)
            attention_mask = inputs['attention_mask'].to(self.device)
            
            # Forward pass
            with torch.no_grad():
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
            
            # Process each item in batch
            for j, text in enumerate(batch_texts):
                # Classification
                classification_logits = outputs['classification_logits'][j]
                probs = torch.softmax(classification_logits, dim=0)
                confidence, predicted = torch.max(probs, dim=0)
                
                doc_type = self.model.DOC_TYPES[predicted.item()]
                doc_confidence = confidence.item()
                
                result = {
                    'text': text,
                    'classification': {
                        'doc_type': doc_type,
                        'confidence': float(doc_confidence)
                    }
                }
                
                results.append(result)
        
        return results
    
    def save_result(self, result: Dict, output_path: str):
        """
        Save processing result to JSON file.
        
        Args:
            result: Result dictionary
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved result to {output_path}")
    
    def get_routing(self, result: Dict) -> str:
        """
        Determine routing based on confidence scores.
        
        Args:
            result: Processing result
        
        Returns:
            Routing decision: 'auto', 'manual', or 'qc'
        """
        confidence = result['confidence']
        doc_type = result['classification']['doc_type']
        
        # High confidence → auto
        if confidence > 0.9:
            return 'auto'
        
        # Legal/sensitive documents → manual review
        if doc_type in ['contract', 'report'] and confidence > 0.6:
            return 'manual'
        
        # Medium confidence → manual
        if confidence > 0.7:
            return 'manual'
        
        # Low confidence → QC
        return 'qc'


# Convenience function
def process_document(
    image_path: str,
    model_path: Optional[str] = None,
    device: str = 'cpu'
) -> Dict:
    """
    Quick function to process a document.
    
    Args:
        image_path: Path to document image
        model_path: Path to saved model (optional)
        device: Device to run on
    
    Returns:
        Processing result dictionary
    """
    # Create processor
    processor = DocumentProcessor(device=device)
    
    # Load model if path provided
    if model_path:
        processor.model.load_state_dict(torch.load(model_path, map_location=device))
        logger.info(f"Loaded model from {model_path}")
    
    # Process image
    result = processor.process_image(image_path, include_ocr=True)
    
    # Add routing
    result['routing'] = processor.get_routing(result)
    
    return result


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # Process document
    result = process_document(image_path)
    
    # Display results
    print("\n" + "="*80)
    print("DOCUMENT PROCESSING RESULT")
    print("="*80)
    print(f"\nDocument Type: {result['classification']['doc_type']}")
    print(f"Confidence: {result['classification']['confidence']:.1%}")
    print(f"Overall Confidence: {result['confidence']:.1%}")
    print(f"Routing: {result['routing'].upper()}")
    
    print(f"\nExtracted Entities:")
    for entity_type, entities in result['extraction'].items():
        if entities:
            print(f"  {entity_type}:")
            for entity in entities:
                print(f"    - {entity['text']} (confidence: {entity['confidence']:.1%})")
    
    print(f"\nOCR Info:")
    print(f"  Language: {result['ocr']['language']}")
    print(f"  Confidence: {result['ocr']['confidence']:.1%}")
    print(f"  Words: {result['ocr']['words_detected']}")
    
    print("\n" + "="*80)
