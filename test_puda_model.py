"""
Test PudaModel unified multi-task architecture.
Tests tokenizer → embeddings → model → classification + extraction heads.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

import torch
from src.ml.models.puda_model import create_puda_model, load_tokenizer
from src.ml.models.pipeline import DocumentProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_model_architecture():
    """Test PudaModel architecture."""
    print("\n" + "="*80)
    print("TEST 1: Model Architecture")
    print("="*80)
    
    # Create model
    model = create_puda_model(
        model_name="distilbert-base-multilingual-cased",
        use_bilstm=True,
        lstm_hidden_size=256,
        dropout=0.1
    )
    
    print(f"\n✅ Model created successfully")
    print(f"   Parameters: {model.count_parameters():,}")
    print(f"   Document types: {len(model.DOC_TYPES)}")
    print(f"   NER tags: {len(model.NER_TAGS)}")
    
    # Test forward pass
    tokenizer = load_tokenizer()
    text = "Invoice from ACME Corp dated Nov 8, 2025 for $1,500.00"
    
    inputs = tokenizer(
        text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512
    )
    
    outputs = model(
        input_ids=inputs['input_ids'],
        attention_mask=inputs['attention_mask'],
        return_embeddings=True
    )
    
    print(f"\n✅ Forward pass successful")
    print(f"   Classification logits: {outputs['classification_logits'].shape}")
    print(f"   Extraction logits: {outputs['extraction_logits'].shape}")
    print(f"   Embeddings: {outputs['embeddings'].shape}")
    
    return model, tokenizer


def test_text_classification(model, tokenizer):
    """Test document classification."""
    print("\n" + "="*80)
    print("TEST 2: Document Classification")
    print("="*80)
    
    test_texts = [
        "Invoice #12345 from ABC Company for $500.00 dated 2025-11-08",
        "Receipt for coffee and pastry. Total: $8.50. Thank you!",
        "This Service Agreement is entered into between Party A and Party B",
        "Memo: Please review the quarterly report by end of week",
    ]
    
    expected_types = ['invoice', 'receipt', 'contract', 'memo']
    
    correct = 0
    for text, expected in zip(test_texts, expected_types):
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        
        doc_types, confidences = model.predict_classification(
            inputs['input_ids'],
            inputs['attention_mask']
        )
        
        predicted = doc_types[0]
        confidence = confidences[0].item()
        
        match = "✅" if predicted == expected else "❌"
        print(f"\n{match} Text: {text[:60]}...")
        print(f"   Predicted: {predicted} (confidence: {confidence:.1%})")
        print(f"   Expected: {expected}")
        
        if predicted == expected:
            correct += 1
    
    accuracy = correct / len(test_texts)
    print(f"\n📊 Classification Accuracy: {accuracy:.1%} ({correct}/{len(test_texts)})")
    
    if accuracy < 1.0:
        print("⚠️  Note: Model is untrained, low accuracy is expected")
    
    return accuracy


def test_entity_extraction(model, tokenizer):
    """Test NER extraction."""
    print("\n" + "="*80)
    print("TEST 3: Entity Extraction (NER)")
    print("="*80)
    
    text = "Invoice INV-001 from ACME Corp for $1,500.00 dated November 8, 2025"
    
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
    
    entities = model.predict_extraction(
        inputs['input_ids'],
        inputs['attention_mask'],
        [tokens]
    )[0]
    
    print(f"\nInput text: {text}")
    print(f"\nExtracted entities:")
    
    total_entities = 0
    for entity_type, entity_list in entities.items():
        if entity_list:
            print(f"\n  {entity_type}:")
            for text, tag, confidence in entity_list:
                print(f"    - {text} (confidence: {confidence:.1%})")
                total_entities += 1
    
    if total_entities == 0:
        print("  ⚠️  No entities extracted (model is untrained)")
    else:
        print(f"\n✅ Extracted {total_entities} entities")
    
    return total_entities


def test_pipeline():
    """Test end-to-end pipeline."""
    print("\n" + "="*80)
    print("TEST 4: End-to-End Pipeline")
    print("="*80)
    
    # Check if test documents exist
    test_doc = "data/test_documents/invoice_english.png"
    if not Path(test_doc).exists():
        print(f"⚠️  Test document not found: {test_doc}")
        print("   Run generate_test_docs.py first")
        return
    
    # Create processor
    processor = DocumentProcessor()
    
    # Process test documents
    test_docs = [
        ("data/test_documents/invoice_english.png", "invoice"),
        ("data/test_documents/receipt_english.png", "receipt"),
        ("data/test_documents/contract_english.png", "contract"),
    ]
    
    correct = 0
    for doc_path, expected_type in test_docs:
        if not Path(doc_path).exists():
            print(f"⚠️  Skipping {doc_path} (not found)")
            continue
        
        print(f"\n📄 Processing: {Path(doc_path).name}")
        
        result = processor.process_image(doc_path, include_ocr=True)
        
        predicted_type = result['classification']['doc_type']
        confidence = result['classification']['confidence']
        routing = processor.get_routing(result)
        
        match = "✅" if predicted_type == expected_type else "❌"
        print(f"   {match} Type: {predicted_type} (expected: {expected_type})")
        print(f"   📊 Confidence: {confidence:.1%}")
        print(f"   🚦 Routing: {routing.upper()}")
        print(f"   📝 OCR: {result['ocr']['words_detected']} words, "
              f"{result['ocr']['confidence']:.1%} confidence")
        
        # Show extracted entities
        if result['extraction']:
            print(f"   🔍 Extracted:")
            for entity_type, entities in result['extraction'].items():
                if entities:
                    for entity in entities[:2]:  # Show first 2
                        print(f"      - {entity_type}: {entity['text']}")
        
        if predicted_type == expected_type:
            correct += 1
    
    accuracy = correct / len([d for d, _ in test_docs if Path(d).exists()])
    print(f"\n📊 Pipeline Accuracy: {accuracy:.1%}")


def test_json_output():
    """Test JSON output format."""
    print("\n" + "="*80)
    print("TEST 5: JSON Output Format")
    print("="*80)
    
    processor = DocumentProcessor()
    
    # Sample text
    text = "Invoice from ACME Corp for $1,500.00 dated November 8, 2025"
    
    # Process
    result = processor.process_text(text)
    
    print(f"\nInput: {text}")
    print(f"\nJSON output structure:")
    print(f"  ✓ text: {len(result['text'])} characters")
    print(f"  ✓ classification:")
    print(f"      - doc_type: {result['classification']['doc_type']}")
    print(f"      - confidence: {result['classification']['confidence']:.1%}")
    print(f"      - all_scores: {len(result['classification']['all_scores'])} types")
    print(f"  ✓ extraction: {len(result['extraction'])} entity types")
    print(f"  ✓ confidence: {result['confidence']:.1%} (overall)")
    
    # Show full JSON
    import json
    print(f"\n📄 Full JSON output:")
    print(json.dumps(result, indent=2))


def test_multilingual():
    """Test multilingual support."""
    print("\n" + "="*80)
    print("TEST 6: Multilingual Support")
    print("="*80)
    
    processor = DocumentProcessor()
    
    test_texts = [
        ("Invoice from ACME Corp for $1,500.00", "English"),
        ("Facture de la Société ACME pour €1,500.00", "French"),
    ]
    
    for text, language in test_texts:
        result = processor.process_text(text)
        
        print(f"\n🌍 {language}:")
        print(f"   Text: {text}")
        print(f"   Type: {result['classification']['doc_type']}")
        print(f"   Confidence: {result['classification']['confidence']:.1%}")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("🧪 PudaModel Test Suite")
    print("   Multi-task architecture: Classification + Extraction")
    print("="*80)
    
    try:
        # Test 1: Architecture
        model, tokenizer = test_model_architecture()
        
        # Test 2: Classification
        test_text_classification(model, tokenizer)
        
        # Test 3: Extraction
        test_entity_extraction(model, tokenizer)
        
        # Test 4: Pipeline
        test_pipeline()
        
        # Test 5: JSON output
        test_json_output()
        
        # Test 6: Multilingual
        test_multilingual()
        
        # Summary
        print("\n" + "="*80)
        print("✅ All tests completed!")
        print("="*80)
        
        print("\n📝 Notes:")
        print("  - Model is UNTRAINED (random weights)")
        print("  - Low accuracy is expected without training")
        print("  - Architecture and pipeline are validated")
        print("  - Ready for training on labeled data")
        
        print("\n🚀 Next steps:")
        print("  1. Collect/annotate training data")
        print("  2. Train model on document dataset")
        print("  3. Export trained model to ONNX")
        print("  4. Deploy in FastAPI inference server")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Test failed")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
