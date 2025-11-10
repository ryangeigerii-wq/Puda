"""
Document Classifier for Puda AI

Specialized classifier for identifying document types:
- Invoice
- Receipt  
- Contract
- ID/Identity Document (driver's license, passport, etc.)
- Form (generic forms)
- Letter
- Memo
- Report
- Other

Uses PudaModel's classification head with optimized confidence scoring.
"""

import torch
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path

try:
    from src.ml.models.puda_model import PudaModel, load_tokenizer
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    PudaModel = None
    load_tokenizer = None

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """
    Document type classifier.
    
    Identifies document types with confidence scores.
    Optimized for common business documents.
    """
    
    # Document type descriptions for better classification
    DOC_TYPE_DESCRIPTIONS = {
        'invoice': [
            'invoice', 'bill', 'billing', 'payment due', 'amount owed',
            'invoice number', 'invoice date', 'total amount', 'subtotal',
            'tax', 'payment terms', 'net', 'remit to', 'vendor'
        ],
        'receipt': [
            'receipt', 'payment received', 'thank you for your purchase',
            'transaction', 'paid', 'card ending', 'visa', 'mastercard',
            'cash', 'change', 'subtotal', 'total', 'store', 'cashier'
        ],
        'contract': [
            'contract', 'agreement', 'terms and conditions', 'whereas',
            'party', 'parties', 'effective date', 'term', 'termination',
            'obligations', 'warranty', 'indemnity', 'governing law',
            'signature', 'witness', 'notary', 'executed'
        ],
        'form': [
            'form', 'application', 'id', 'identification', 'license',
            'passport', 'driver', 'social security', 'date of birth',
            'expires', 'issued', 'signature', 'photo', 'height', 'weight',
            'address', 'nationality', 'citizenship'
        ],
        'letter': [
            'dear', 'sincerely', 'yours truly', 'regards', 'to whom it may concern',
            'letter', 'correspondence', 'dated', 're:', 'subject:'
        ],
        'memo': [
            'memo', 'memorandum', 'to:', 'from:', 'date:', 'subject:', 're:',
            'internal', 'department', 'notice'
        ],
        'report': [
            'report', 'analysis', 'summary', 'findings', 'conclusion',
            'recommendations', 'executive summary', 'introduction',
            'methodology', 'results', 'discussion', 'appendix'
        ],
        'other': []
    }
    
    def __init__(
        self,
        model: Optional[PudaModel] = None,
        tokenizer = None,
        model_path: Optional[Path] = None,
        device: str = "cpu"
    ):
        """
        Initialize document classifier.
        
        Args:
            model: Pretrained PudaModel (if None, will initialize new)
            tokenizer: Tokenizer (if None, will load default)
            model_path: Path to trained model checkpoint
            device: Device for inference ('cpu' or 'cuda')
        """
        self.device = device
        
        # Load or initialize model
        if model is not None:
            self.model = model
        else:
            if not MODELS_AVAILABLE:
                raise ImportError("PudaModel not available")
            
            logger.info("Initializing PudaModel for classification...")
            self.model = PudaModel(
                model_name="distilbert-base-multilingual-cased",
                use_bilstm=False,  # Faster for classification-only
                dropout=0.0,       # No dropout at inference
                freeze_backbone=False
            )
            
            # Load trained weights if provided
            if model_path and model_path.exists():
                logger.info(f"Loading model from {model_path}")
                checkpoint = torch.load(model_path, map_location=device)
                self.model.load_state_dict(checkpoint['model_state_dict'])
        
        self.model.to(device)
        self.model.eval()
        
        # Load tokenizer
        if tokenizer is not None:
            self.tokenizer = tokenizer
        else:
            if not MODELS_AVAILABLE:
                raise ImportError("Tokenizer not available")
            logger.info("Loading tokenizer...")
            self.tokenizer = load_tokenizer("distilbert-base-multilingual-cased")
    
    @torch.no_grad()
    def classify(
        self,
        text: str,
        return_all_scores: bool = True,
        confidence_threshold: float = 0.5
    ) -> Dict:
        """
        Classify document type.
        
        Args:
            text: Document text
            return_all_scores: Return scores for all document types
            confidence_threshold: Minimum confidence for positive classification
            
        Returns:
            Dictionary with:
            - doc_type: Predicted document type
            - confidence: Confidence score (0-1)
            - all_scores: Scores for all types (if return_all_scores=True)
            - needs_review: Boolean flag if confidence is low
        """
        # Tokenize input
        inputs = self.tokenizer(
            text,
            padding='max_length',
            truncation=True,
            max_length=512,
            return_tensors='pt'
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Forward pass
        class_logits, _ = self.model(
            input_ids=inputs['input_ids'],
            attention_mask=inputs['attention_mask']
        )
        
        # Get probabilities
        probs = torch.softmax(class_logits, dim=-1)[0]
        
        # Get top prediction
        confidence, pred_idx = torch.max(probs, dim=0)
        doc_type = self.model.DOC_TYPES[pred_idx.item()]
        confidence = confidence.item()
        
        result = {
            'doc_type': doc_type,
            'confidence': confidence,
            'needs_review': confidence < confidence_threshold
        }
        
        # Add all scores if requested
        if return_all_scores:
            result['all_scores'] = {
                doc_type: float(prob)
                for doc_type, prob in zip(self.model.DOC_TYPES, probs.cpu().numpy())
            }
        
        return result
    
    def classify_batch(
        self,
        texts: List[str],
        batch_size: int = 8,
        confidence_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Classify multiple documents in batches.
        
        Args:
            texts: List of document texts
            batch_size: Batch size for processing
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            List of classification results
        """
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch_texts,
                padding='max_length',
                truncation=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Forward pass
            with torch.no_grad():
                class_logits, _ = self.model(
                    input_ids=inputs['input_ids'],
                    attention_mask=inputs['attention_mask']
                )
            
            # Get probabilities
            probs = torch.softmax(class_logits, dim=-1)
            
            # Process each result
            for j in range(len(batch_texts)):
                confidence, pred_idx = torch.max(probs[j], dim=0)
                doc_type = self.model.DOC_TYPES[pred_idx.item()]
                confidence = confidence.item()
                
                result = {
                    'doc_type': doc_type,
                    'confidence': confidence,
                    'needs_review': confidence < confidence_threshold,
                    'all_scores': {
                        dt: float(probs[j][k].item())
                        for k, dt in enumerate(self.model.DOC_TYPES)
                    }
                }
                results.append(result)
        
        return results
    
    def explain_classification(self, text: str, top_k: int = 3) -> Dict:
        """
        Provide explanation for classification decision.
        
        Args:
            text: Document text
            top_k: Number of top predictions to explain
            
        Returns:
            Dictionary with classification and explanation
        """
        result = self.classify(text, return_all_scores=True)
        
        # Sort scores
        sorted_scores = sorted(
            result['all_scores'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        # Find matching keywords for top predictions
        text_lower = text.lower()
        explanations = []
        
        for doc_type, score in sorted_scores:
            keywords = self.DOC_TYPE_DESCRIPTIONS.get(doc_type, [])
            found_keywords = [kw for kw in keywords if kw.lower() in text_lower]
            
            explanations.append({
                'doc_type': doc_type,
                'score': score,
                'confidence': f"{score * 100:.2f}%",
                'keywords_found': found_keywords[:5]  # Top 5 matching keywords
            })
        
        return {
            'prediction': result['doc_type'],
            'confidence': result['confidence'],
            'needs_review': result['needs_review'],
            'explanations': explanations
        }
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported document types."""
        return self.model.DOC_TYPES.copy()


def classify_document(text: str, model_path: Optional[Path] = None) -> Dict:
    """
    Convenience function for quick document classification.
    
    Args:
        text: Document text
        model_path: Optional path to trained model
        
    Returns:
        Classification result dictionary
    """
    classifier = DocumentClassifier(model_path=model_path)
    return classifier.classify(text)


# Example usage
if __name__ == "__main__":
    # Sample documents
    invoice_text = """
    ACME Corporation
    Invoice #INV-2024-12345
    Date: January 15, 2024
    
    Bill To: Tech Solutions Inc.
    
    Description                 Amount
    Consulting Services        $1,234.56
    Software License            $500.00
    
    Subtotal:                  $1,734.56
    Tax (8%):                    $138.76
    Total Amount Due:          $1,873.32
    
    Payment Terms: Net 30
    """
    
    receipt_text = """
    Best Buy Store #1234
    Receipt
    
    Date: 11/10/2024 2:45 PM
    Transaction #: 5678-9012-3456
    
    Items:
    Laptop Computer    $899.99
    Wireless Mouse      $29.99
    
    Subtotal:          $929.98
    Tax:                $74.40
    TOTAL:           $1,004.38
    
    Payment: Visa ****1234
    Thank you for shopping with us!
    """
    
    contract_text = """
    SOFTWARE LICENSE AGREEMENT
    
    This Agreement is entered into as of January 1, 2024
    by and between ACME Corp (the "Licensor") and 
    XYZ Company (the "Licensee").
    
    WHEREAS, Licensor owns certain proprietary software;
    WHEREAS, Licensee desires to license such software;
    
    NOW THEREFORE, the parties agree as follows:
    
    1. GRANT OF LICENSE
    Licensor hereby grants to Licensee a non-exclusive,
    non-transferable license to use the Software.
    
    2. TERM AND TERMINATION
    This Agreement shall commence on the Effective Date
    and continue for a period of one (1) year.
    
    3. WARRANTIES AND INDEMNIFICATION
    Licensor warrants that it has full right and authority
    to enter into this Agreement.
    
    IN WITNESS WHEREOF, the parties have executed this
    Agreement as of the date first written above.
    
    _____________________        _____________________
    Licensor Signature            Licensee Signature
    """
    
    id_text = """
    DRIVER LICENSE
    
    State of California
    
    DL: D1234567
    Expires: 01/15/2028
    Issued: 01/15/2024
    
    Name: SMITH, JOHN DAVID
    Address: 123 Main Street
             Los Angeles, CA 90001
    
    DOB: 05/12/1985
    Sex: M
    Height: 5-10
    Weight: 175
    Eyes: BRN
    Hair: BRN
    
    Class C - Passenger Vehicle
    """
    
    # Test classification
    print("Document Classification Examples")
    print("=" * 70)
    
    for name, text in [
        ("Invoice", invoice_text),
        ("Receipt", receipt_text),
        ("Contract", contract_text),
        ("ID Document", id_text)
    ]:
        print(f"\n{name}:")
        print("-" * 70)
        
        try:
            classifier = DocumentClassifier()
            result = classifier.explain_classification(text)
            
            print(f"Predicted Type: {result['prediction']}")
            print(f"Confidence: {result['confidence']:.4f}")
            print(f"Needs Review: {result['needs_review']}")
            print(f"\nTop Predictions:")
            
            for exp in result['explanations']:
                print(f"  {exp['doc_type']}: {exp['confidence']}")
                if exp['keywords_found']:
                    print(f"    Keywords: {', '.join(exp['keywords_found'][:3])}")
        
        except Exception as e:
            print(f"Error: {e}")
            print("Note: Requires trained model to run")
