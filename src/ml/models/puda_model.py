"""
PudaModel: Unified multi-task model for document intelligence.

Architecture:
    [OCR Text/JSON] 
         ↓
    Tokenizer → Embeddings
         ↓
    PudaModel (Transformer / BiLSTM hybrid)
         ↓
    Classification head → doc type
    Extraction head → field tokens (NER)
    Summarization head (optional)
         ↓
    JSON output + confidence

Design:
- Single shared backbone for efficiency
- Multi-task learning improves all tasks
- Lightweight: DistilBERT base (~66M params)
- Exportable to ONNX for production
"""

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel, AutoConfig
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PudaModel(nn.Module):
    """
    Unified multi-task model for document processing.
    
    Tasks:
    1. Classification: Document type (invoice, receipt, contract, etc.)
    2. Extraction: Named entity recognition for key fields
    3. Summarization: Optional text summarization (can use separate model)
    
    Architecture:
    - Tokenizer: Pretrained tokenizer (distilbert-base-multilingual-cased)
    - Embeddings: Token embeddings + position embeddings
    - Backbone: DistilBERT transformer encoder (6 layers)
    - BiLSTM: Optional bidirectional LSTM for sequence modeling
    - Task Heads: Separate linear layers for each task
    """
    
    # Document types
    DOC_TYPES = [
        'invoice',
        'receipt',
        'contract',
        'form',
        'letter',
        'memo',
        'report',
        'other'
    ]
    
    # NER tags for extraction (BIO format)
    NER_TAGS = [
        'O',           # Outside
        'B-DATE',      # Begin date
        'I-DATE',      # Inside date
        'B-AMOUNT',    # Begin amount
        'I-AMOUNT',    # Inside amount
        'B-NAME',      # Begin name/person
        'I-NAME',      # Inside name/person
        'B-ORG',       # Begin organization
        'I-ORG',       # Inside organization
        'B-ADDR',      # Begin address
        'I-ADDR',      # Inside address
        'B-INVOICE',   # Begin invoice number
        'I-INVOICE',   # Inside invoice number
        'B-PHONE',     # Begin phone number
        'I-PHONE',     # Inside phone number
        'B-EMAIL',     # Begin email
        'I-EMAIL',     # Inside email
    ]
    
    def __init__(
        self,
        model_name: str = "distilbert-base-multilingual-cased",
        use_bilstm: bool = True,
        lstm_hidden_size: int = 256,
        dropout: float = 0.1,
        freeze_backbone: bool = False
    ):
        """
        Initialize PudaModel.
        
        Args:
            model_name: Pretrained transformer model name
            use_bilstm: Add BiLSTM layer after transformer
            lstm_hidden_size: Hidden size for BiLSTM
            dropout: Dropout rate
            freeze_backbone: Freeze transformer weights (only train heads)
        """
        super().__init__()
        
        self.model_name = model_name
        self.use_bilstm = use_bilstm
        self.num_doc_types = len(self.DOC_TYPES)
        self.num_ner_tags = len(self.NER_TAGS)
        
        logger.info(f"Initializing PudaModel with backbone: {model_name}")
        
        # Load pretrained transformer
        self.config = AutoConfig.from_pretrained(model_name)
        self.transformer = AutoModel.from_pretrained(model_name)
        
        # Optionally freeze transformer weights
        if freeze_backbone:
            for param in self.transformer.parameters():
                param.requires_grad = False
            logger.info("Frozen transformer backbone weights")
        
        hidden_size = self.config.hidden_size  # 768 for DistilBERT
        
        # BiLSTM layer (optional)
        if use_bilstm:
            self.bilstm = nn.LSTM(
                input_size=hidden_size,
                hidden_size=lstm_hidden_size,
                num_layers=1,
                batch_first=True,
                bidirectional=True,
                dropout=0.0  # No dropout in LSTM (only 1 layer)
            )
            # Hidden size after BiLSTM is 2 * lstm_hidden_size
            classifier_input_size = lstm_hidden_size * 2
        else:
            self.bilstm = None
            classifier_input_size = hidden_size
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
        # Task 1: Document classification head
        self.classification_head = nn.Sequential(
            nn.Linear(classifier_input_size, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, self.num_doc_types)
        )
        
        # Task 2: NER extraction head (token-level classification)
        self.extraction_head = nn.Sequential(
            nn.Linear(classifier_input_size, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, self.num_ner_tags)
        )
        
        # Task 3: Summarization (optional - can use separate seq2seq model)
        # For now, we'll use a separate model (mT5) for summarization
        # This head is reserved for future use
        
        logger.info(f"Initialized PudaModel:")
        logger.info(f"  - Document types: {self.num_doc_types}")
        logger.info(f"  - NER tags: {self.num_ner_tags}")
        logger.info(f"  - BiLSTM: {use_bilstm}")
        logger.info(f"  - Parameters: {self.count_parameters():,}")
    
    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        return_embeddings: bool = False
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass through the model.
        
        Args:
            input_ids: Token IDs (batch_size, seq_len)
            attention_mask: Attention mask (batch_size, seq_len)
            return_embeddings: Return intermediate embeddings
        
        Returns:
            Dictionary with task outputs:
            - classification_logits: (batch_size, num_doc_types)
            - extraction_logits: (batch_size, seq_len, num_ner_tags)
            - embeddings: (batch_size, hidden_size) [optional]
        """
        # Get transformer outputs
        outputs = self.transformer(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        
        # Last hidden state: (batch_size, seq_len, hidden_size)
        hidden_states = outputs.last_hidden_state
        
        # Apply BiLSTM if enabled
        if self.bilstm is not None:
            hidden_states, _ = self.bilstm(hidden_states)
        
        # Apply dropout
        hidden_states = self.dropout(hidden_states)
        
        # Get [CLS] token embedding for classification
        # (first token in sequence)
        cls_embedding = hidden_states[:, 0, :]  # (batch_size, hidden_size)
        
        # Task 1: Document classification
        classification_logits = self.classification_head(cls_embedding)
        
        # Task 2: NER extraction (token-level)
        extraction_logits = self.extraction_head(hidden_states)
        
        result = {
            'classification_logits': classification_logits,
            'extraction_logits': extraction_logits
        }
        
        if return_embeddings:
            result['embeddings'] = cls_embedding
        
        return result
    
    def predict_classification(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor
    ) -> Tuple[List[str], torch.Tensor]:
        """
        Predict document type.
        
        Args:
            input_ids: Token IDs
            attention_mask: Attention mask
        
        Returns:
            Tuple of (predicted_types, confidences)
        """
        self.eval()
        with torch.no_grad():
            outputs = self.forward(input_ids, attention_mask)
            logits = outputs['classification_logits']
            
            # Apply softmax to get probabilities
            probs = torch.softmax(logits, dim=-1)
            confidences, predicted = torch.max(probs, dim=-1)
            
            # Convert to document type names
            doc_types = [self.DOC_TYPES[idx] for idx in predicted.cpu().numpy()]
            
            return doc_types, confidences
    
    def predict_extraction(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        tokens: List[List[str]]
    ) -> List[Dict[str, List[Tuple[str, str, float]]]]:
        """
        Predict NER tags for extraction.
        
        Args:
            input_ids: Token IDs
            attention_mask: Attention mask
            tokens: Original tokens for each sequence
        
        Returns:
            List of dictionaries with extracted entities per batch item:
            {
                'DATE': [(text, tag, confidence), ...],
                'AMOUNT': [...],
                'NAME': [...],
                ...
            }
        """
        self.eval()
        with torch.no_grad():
            outputs = self.forward(input_ids, attention_mask)
            logits = outputs['extraction_logits']
            
            # Apply softmax to get probabilities
            probs = torch.softmax(logits, dim=-1)
            confidences, predicted = torch.max(probs, dim=-1)
            
            # Process each sequence in batch
            results = []
            for batch_idx in range(len(tokens)):
                entities = self._extract_entities(
                    tokens[batch_idx],
                    predicted[batch_idx].cpu().numpy(),
                    confidences[batch_idx].cpu().numpy(),
                    attention_mask[batch_idx].cpu().numpy()
                )
                results.append(entities)
            
            return results
    
    def _extract_entities(
        self,
        tokens: List[str],
        predicted_tags: list,
        confidences: list,
        attention_mask: list
    ) -> Dict[str, List[Tuple[str, str, float]]]:
        """
        Extract entities from BIO tags.
        
        Args:
            tokens: Token strings
            predicted_tags: Predicted tag indices
            confidences: Confidence scores
            attention_mask: Mask for valid tokens
        
        Returns:
            Dictionary of entity type to list of (text, tag, confidence)
        """
        entities = {
            'DATE': [],
            'AMOUNT': [],
            'NAME': [],
            'ORG': [],
            'ADDR': [],
            'INVOICE': [],
            'PHONE': [],
            'EMAIL': []
        }
        
        current_entity = None
        current_tokens = []
        current_confidences = []
        
        for i, (token, tag_idx, conf, mask) in enumerate(
            zip(tokens, predicted_tags, confidences, attention_mask)
        ):
            if mask == 0:  # Skip padding tokens
                continue
            
            tag = self.NER_TAGS[tag_idx]
            
            if tag == 'O':
                # End current entity if any
                if current_entity:
                    self._add_entity(
                        entities,
                        current_entity,
                        current_tokens,
                        current_confidences
                    )
                    current_entity = None
                    current_tokens = []
                    current_confidences = []
            
            elif tag.startswith('B-'):
                # Begin new entity
                if current_entity:
                    # Save previous entity
                    self._add_entity(
                        entities,
                        current_entity,
                        current_tokens,
                        current_confidences
                    )
                
                # Start new entity
                entity_type = tag[2:]  # Remove 'B-' prefix
                current_entity = entity_type
                current_tokens = [token]
                current_confidences = [conf]
            
            elif tag.startswith('I-'):
                # Continue current entity
                entity_type = tag[2:]  # Remove 'I-' prefix
                if current_entity == entity_type:
                    current_tokens.append(token)
                    current_confidences.append(conf)
                else:
                    # Mismatched entity type, start new one
                    if current_entity:
                        self._add_entity(
                            entities,
                            current_entity,
                            current_tokens,
                            current_confidences
                        )
                    current_entity = entity_type
                    current_tokens = [token]
                    current_confidences = [conf]
        
        # Add final entity if any
        if current_entity:
            self._add_entity(
                entities,
                current_entity,
                current_tokens,
                current_confidences
            )
        
        return entities
    
    def _add_entity(
        self,
        entities: Dict,
        entity_type: str,
        tokens: List[str],
        confidences: List[float]
    ):
        """Add extracted entity to results."""
        text = ' '.join(tokens)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        if entity_type in entities:
            entities[entity_type].append((text, entity_type, avg_confidence))
    
    def count_parameters(self) -> int:
        """Count trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_config(self) -> Dict:
        """Get model configuration."""
        return {
            'model_name': self.model_name,
            'use_bilstm': self.use_bilstm,
            'num_doc_types': self.num_doc_types,
            'num_ner_tags': self.num_ner_tags,
            'doc_types': self.DOC_TYPES,
            'ner_tags': self.NER_TAGS
        }


def load_tokenizer(model_name: str = "distilbert-base-multilingual-cased"):
    """
    Load tokenizer for PudaModel.
    
    Args:
        model_name: Pretrained model name
    
    Returns:
        Tokenizer instance
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    logger.info(f"Loaded tokenizer: {model_name}")
    return tokenizer


def create_puda_model(**kwargs) -> PudaModel:
    """
    Create PudaModel instance.
    
    Args:
        **kwargs: Arguments for PudaModel
    
    Returns:
        PudaModel instance
    """
    model = PudaModel(**kwargs)
    return model


# Example usage
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Create model
    model = create_puda_model(
        model_name="distilbert-base-multilingual-cased",
        use_bilstm=True,
        lstm_hidden_size=256,
        dropout=0.1
    )
    
    # Load tokenizer
    tokenizer = load_tokenizer()
    
    # Test with sample text
    text = "Invoice from ACME Corp dated Nov 8, 2025 for $1,500.00"
    
    # Tokenize
    inputs = tokenizer(
        text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512
    )
    
    # Forward pass
    outputs = model(
        input_ids=inputs['input_ids'],
        attention_mask=inputs['attention_mask'],
        return_embeddings=True
    )
    
    print("\n=== PudaModel Test ===")
    print(f"Input text: {text}")
    print(f"\nModel outputs:")
    print(f"  Classification logits shape: {outputs['classification_logits'].shape}")
    print(f"  Extraction logits shape: {outputs['extraction_logits'].shape}")
    print(f"  Embeddings shape: {outputs['embeddings'].shape}")
    
    # Test prediction
    doc_types, confidences = model.predict_classification(
        inputs['input_ids'],
        inputs['attention_mask']
    )
    
    print(f"\nPredicted document type: {doc_types[0]} (confidence: {confidences[0]:.2%})")
    print(f"\nModel has {model.count_parameters():,} trainable parameters")
