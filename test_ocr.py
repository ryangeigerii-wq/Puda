"""
Test OCR engine with generated ghost data.
Validates multilingual OCR, preprocessing, and layout analysis.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ml.ocr import OCREngine
from generate_test_docs import DocumentGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_ocr_on_document(engine: OCREngine, filepath: str, expected_lang: str):
    """Test OCR on a single document."""
    print(f"\n{'='*80}")
    print(f"Testing: {Path(filepath).name}")
    print(f"{'='*80}")
    
    try:
        # Run OCR
        result = engine.extract_text_from_file(filepath)
        
        # Display results
        print(f"\n📝 OCR Results:")
        print(f"  Language: {result.language} (expected: {expected_lang})")
        print(f"  Confidence: {result.confidence:.1%}")
        print(f"  Processing time: {result.processing_time_ms:.1f}ms")
        print(f"  Words detected: {len(result.layout['words'])}")
        print(f"  Lines detected: {len(result.layout['lines'])}")
        
        # Show confidence distribution
        if result.word_confidences:
            avg_conf = sum(result.word_confidences) / len(result.word_confidences)
            min_conf = min(result.word_confidences)
            max_conf = max(result.word_confidences)
            print(f"\n📊 Confidence Stats:")
            print(f"  Average: {avg_conf:.1f}%")
            print(f"  Min: {min_conf:.1f}%")
            print(f"  Max: {max_conf:.1f}%")
        
        # Show extracted text (first 500 chars)
        print(f"\n📄 Extracted Text (preview):")
        print("-" * 80)
        preview = result.text[:500] if len(result.text) > 500 else result.text
        print(preview)
        if len(result.text) > 500:
            print(f"\n... ({len(result.text) - 500} more characters)")
        print("-" * 80)
        
        # Validate language detection
        lang_match = "✅" if result.language == expected_lang else "❌"
        print(f"\n{lang_match} Language detection: {result.language} (expected {expected_lang})")
        
        # Check confidence threshold
        conf_ok = "✅" if result.confidence > 0.7 else "⚠️"
        print(f"{conf_ok} Confidence: {result.confidence:.1%} (target >70%)")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("OCR failed")
        return None


def main():
    """Run OCR tests on ghost data."""
    print("\n" + "="*80)
    print("🧪 Puda OCR Engine Test Suite")
    print("="*80)
    
    # Step 1: Generate test documents
    print("\n📝 Step 1: Generating test documents...")
    generator = DocumentGenerator()
    test_files = generator.generate_all()
    print(f"✅ Generated {len(test_files)} test documents")
    
    # Step 2: Initialize OCR engine
    print("\n🚀 Step 2: Initializing OCR engine...")
    print("  Languages: English, French, Arabic")
    print("  Preprocessing: Enabled")
    
    # Set Tesseract path for Windows
    tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    engine = OCREngine(
        languages='eng+fra+ara',
        preprocess=True,
        tesseract_cmd=tesseract_cmd
    )
    print("✅ OCR engine initialized")
    
    # Step 3: Test each document
    print("\n🔍 Step 3: Testing OCR on documents...")
    
    test_cases = [
        ("data/test_documents/invoice_english.png", "en"),
        ("data/test_documents/invoice_french.png", "fr"),
        ("data/test_documents/receipt_english.png", "en"),
        ("data/test_documents/contract_english.png", "en"),
    ]
    
    results = []
    for filepath, expected_lang in test_cases:
        result = test_ocr_on_document(engine, filepath, expected_lang)
        if result:
            results.append((filepath, result))
    
    # Step 4: Summary
    print(f"\n{'='*80}")
    print("📊 Test Summary")
    print(f"{'='*80}")
    
    if results:
        avg_confidence = sum(r.confidence for _, r in results) / len(results)
        avg_time = sum(r.processing_time_ms for _, r in results) / len(results)
        
        print(f"\n✅ Successfully processed {len(results)}/{len(test_cases)} documents")
        print(f"\n📈 Performance Metrics:")
        print(f"  Average confidence: {avg_confidence:.1%}")
        print(f"  Average processing time: {avg_time:.1f}ms")
        print(f"  Total words extracted: {sum(len(r.layout['words']) for _, r in results)}")
        
        # Language breakdown
        print(f"\n🌍 Language Distribution:")
        lang_counts = {}
        for _, result in results:
            lang_counts[result.language] = lang_counts.get(result.language, 0) + 1
        
        for lang, count in sorted(lang_counts.items()):
            lang_name = {'en': 'English', 'fr': 'French', 'ar': 'Arabic'}.get(lang, lang)
            print(f"  {lang_name}: {count} document(s)")
        
        # Quality assessment
        print(f"\n✨ Quality Assessment:")
        high_conf = sum(1 for _, r in results if r.confidence > 0.9)
        med_conf = sum(1 for _, r in results if 0.7 <= r.confidence <= 0.9)
        low_conf = sum(1 for _, r in results if r.confidence < 0.7)
        
        print(f"  High confidence (>90%): {high_conf} documents")
        print(f"  Medium confidence (70-90%): {med_conf} documents")
        print(f"  Low confidence (<70%): {low_conf} documents")
        
        if low_conf > 0:
            print(f"\n⚠️  Warning: {low_conf} document(s) with low confidence")
            print("  Consider improving image quality or preprocessing")
        else:
            print("\n✅ All documents meet confidence threshold!")
        
    else:
        print("\n❌ No documents processed successfully")
    
    print(f"\n{'='*80}")
    print("🎉 Test completed!")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
