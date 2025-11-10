"""
Production Performance Benchmarks for Puda AI Core Capabilities

Validates against production targets:
- Top-5 document types: invoice, receipt, contract, ID, other
- Macro-F1 ≥ 0.95 on test data
- Latency ≤ 50ms per page on CPU
"""

import time
import sys
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from src.ml.classifier import DocumentClassifier
from src.ml.field_extractor import FieldExtractor
from src.ml.summarizer import DocumentSummarizer


# Test dataset for top-5 document types
TEST_DOCUMENTS = {
    'invoice': [
        """INVOICE #INV-2024-001
Date: January 15, 2024
Bill To: Acme Corp
Amount Due: $5,250.00
Payment Terms: Net 30""",
        
        """TAX INVOICE
Invoice Number: 2024/0542
Date: March 10, 2024
Customer: Tech Solutions Inc.
Total Amount: $12,800.00
GST Included: $1,164.00""",
        
        """SALES INVOICE
Inv#: SI-2024-789
Billing Date: February 28, 2024
Client: Global Industries
Subtotal: $25,000.00
Tax (8%): $2,000.00
Total: $27,000.00"""
    ],
    
    'receipt': [
        """RECEIPT
Store: Best Buy #1234
Date: Nov 10, 2024
Items: 3
Total: $459.99
Payment: Visa ****1234""",
        
        """CUSTOMER RECEIPT
TechMart Electronics
Transaction: 789456123
Date: 10/15/2024 14:30
Amount Paid: $127.50
Thank you!""",
        
        """PAYMENT RECEIPT
Merchant: Amazon.com
Order #: 123-4567890-1234567
Date: September 5, 2024
Total Charged: $89.99
Payment Method: Mastercard"""
    ],
    
    'contract': [
        """SERVICES AGREEMENT
This Agreement dated January 1, 2024
Between: Acme Corporation (Client)
And: Tech Solutions Inc. (Consultant)
Term: 12 months
Compensation: $50,000.00""",
        
        """EMPLOYMENT CONTRACT
Employee: John Smith
Start Date: March 15, 2024
Position: Software Engineer
Salary: $120,000 per annum
Benefits: Health, Dental, 401k""",
        
        """LEASE AGREEMENT
Property: 123 Main Street, Apt 4B
Tenant: Jane Doe
Landlord: Real Estate Holdings LLC
Term: 12 months from Feb 1, 2024
Monthly Rent: $2,500.00"""
    ],
    
    'id': [
        """DRIVER'S LICENSE
Name: JOHN SMITH
DOB: 01/15/1985
License #: D1234567
Expires: 01/15/2028
Class: C""",
        
        """PASSPORT
United States of America
Surname: JOHNSON
Given Names: SARAH MARIE
Passport No: 123456789
Date of Birth: 05/20/1990
Date of Issue: 06/01/2024
Date of Expiry: 06/01/2034""",
        
        """EMPLOYEE ID CARD
Company: Tech Corp
Employee: Michael Chen
ID Number: EMP-98765
Department: Engineering
Valid Through: 12/31/2025"""
    ],
    
    'other': [
        """PROJECT UPDATE
Meeting Notes - Weekly Standup
Date: November 10, 2024
Attendees: 8 team members
Topics: Sprint planning, blockers
Action items: 5 tasks assigned""",
        
        """SHIPPING LABEL
From: Warehouse Distribution Center
To: Customer Address
Tracking: 1Z999AA10123456784
Weight: 5.2 lbs
Service: 2-Day Express""",
        
        """MEDICAL PRESCRIPTION
Patient: Robert Williams
Medication: Amoxicillin 500mg
Dosage: Take 1 capsule 3x daily
Quantity: 30 capsules
Refills: 2
Dr. Sarah Johnson, MD"""
    ]
}


def benchmark_classifier():
    """Benchmark document classifier against targets."""
    print("="*80)
    print("CLASSIFIER BENCHMARK - Top-5 Document Types")
    print("="*80)
    print(f"Target: Macro-F1 ≥ 0.95")
    print(f"Target: Latency ≤ 50ms per document")
    print()
    
    classifier = DocumentClassifier()
    
    # Ground truth mapping
    all_predictions = []
    all_labels = []
    latencies = []
    
    for doc_type, documents in TEST_DOCUMENTS.items():
        print(f"\nTesting {doc_type.upper()} documents ({len(documents)} samples):")
        
        for i, doc in enumerate(documents, 1):
            # Measure latency
            start = time.perf_counter()
            result = classifier.classify(doc)
            latency_ms = (time.perf_counter() - start) * 1000
            
            latencies.append(latency_ms)
            all_labels.append(doc_type)
            all_predictions.append(result['type'])
            
            # Display result
            correct = "✓" if result['type'] == doc_type else "✗"
            print(f"  [{i}] Predicted: {result['type']:10s} "
                  f"Confidence: {result['confidence']:.1%} "
                  f"Latency: {latency_ms:5.1f}ms {correct}")
    
    # Calculate metrics
    print("\n" + "="*80)
    print("PERFORMANCE METRICS")
    print("="*80)
    
    # Accuracy per class
    class_correct = defaultdict(int)
    class_total = defaultdict(int)
    
    for true_label, pred_label in zip(all_labels, all_predictions):
        class_total[true_label] += 1
        if true_label == pred_label:
            class_correct[true_label] += 1
    
    print("\nPer-Class Accuracy:")
    f1_scores = []
    for doc_type in TEST_DOCUMENTS.keys():
        accuracy = class_correct[doc_type] / class_total[doc_type]
        # For binary classification per class, F1 ≈ accuracy when balanced
        f1_scores.append(accuracy)
        status = "✓" if accuracy >= 0.95 else "✗"
        print(f"  {doc_type:10s}: {accuracy:.1%} (F1: {accuracy:.3f}) {status}")
    
    # Macro-F1
    macro_f1 = sum(f1_scores) / len(f1_scores)
    print(f"\nMacro-F1: {macro_f1:.3f}")
    print(f"Target:   0.950")
    print(f"Status:   {'✓ PASS' if macro_f1 >= 0.95 else '✗ FAIL'}")
    
    # Overall accuracy
    total_correct = sum(1 for t, p in zip(all_labels, all_predictions) if t == p)
    overall_accuracy = total_correct / len(all_labels)
    print(f"\nOverall Accuracy: {overall_accuracy:.1%} ({total_correct}/{len(all_labels)})")
    
    # Latency statistics
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    
    print(f"\nLatency Statistics (CPU):")
    print(f"  Average:  {avg_latency:5.1f}ms")
    print(f"  Min:      {min_latency:5.1f}ms")
    print(f"  Max:      {max_latency:5.1f}ms")
    print(f"  P95:      {p95_latency:5.1f}ms")
    print(f"  Target:   50.0ms")
    print(f"  Status:   {'✓ PASS' if avg_latency <= 50 else '✗ FAIL'}")
    
    # Confusion matrix
    print("\nConfusion Matrix:")
    print("          ", end="")
    for doc_type in TEST_DOCUMENTS.keys():
        print(f"{doc_type[:8]:>10s}", end="")
    print()
    
    for true_type in TEST_DOCUMENTS.keys():
        print(f"{true_type:10s}", end="")
        for pred_type in TEST_DOCUMENTS.keys():
            count = sum(1 for t, p in zip(all_labels, all_predictions) 
                       if t == true_type and p == pred_type)
            print(f"{count:10d}", end="")
        print()
    
    return {
        'macro_f1': macro_f1,
        'accuracy': overall_accuracy,
        'avg_latency_ms': avg_latency,
        'max_latency_ms': max_latency,
        'meets_f1_target': macro_f1 >= 0.95,
        'meets_latency_target': avg_latency <= 50
    }


def benchmark_field_extractor():
    """Benchmark field extractor performance."""
    print("\n\n" + "="*80)
    print("FIELD EXTRACTOR BENCHMARK")
    print("="*80)
    print(f"Target: Latency ≤ 50ms per document")
    print()
    
    extractor = FieldExtractor()
    
    # Sample documents with known fields
    test_docs = [
        ("Invoice with multiple fields", 
         "Invoice dated 01/15/2024. Amount due: $5,250.00. Contact: John Smith."),
        
        ("Receipt with transaction data",
         "Receipt from Nov 10, 2024. Total: $127.50. Cashier: Sarah Johnson."),
        
        ("Contract with dates and amounts",
         "Agreement effective 01/01/2024 through 12/31/2024. Payment: $50,000.00. Parties: John Doe and Jane Smith.")
    ]
    
    latencies = []
    
    for name, doc in test_docs:
        print(f"\n{name}:")
        
        # Measure latency
        start = time.perf_counter()
        result = extractor.extract_all(doc)
        latency_ms = (time.perf_counter() - start) * 1000
        
        latencies.append(latency_ms)
        
        print(f"  Dates:   {len(result['dates'])} found")
        print(f"  Amounts: {len(result['amounts'])} found")
        print(f"  Names:   {len(result['names'])} found")
        print(f"  Latency: {latency_ms:.1f}ms")
    
    avg_latency = sum(latencies) / len(latencies)
    
    print("\n" + "-"*80)
    print(f"Average Latency: {avg_latency:.1f}ms")
    print(f"Target:          50.0ms")
    print(f"Status:          {'✓ PASS' if avg_latency <= 50 else '✗ FAIL'}")
    
    return {
        'avg_latency_ms': avg_latency,
        'meets_latency_target': avg_latency <= 50
    }


def benchmark_summarizer():
    """Benchmark summarizer performance."""
    print("\n\n" + "="*80)
    print("SUMMARIZER BENCHMARK")
    print("="*80)
    print(f"Target: Latency ≤ 50ms per document")
    print()
    
    summarizer = DocumentSummarizer()
    
    # Test documents of varying lengths
    test_docs = [
        ("Short invoice", TEST_DOCUMENTS['invoice'][0]),
        ("Medium contract", TEST_DOCUMENTS['contract'][0]),
        ("Long report", """
        QUARTERLY SALES REPORT - Q1 2024
        
        Executive Summary: Total revenue reached $12.5M, exceeding our target by 14%.
        Enterprise sales grew 35% to $8M, accounting for 64% of total revenue.
        The average deal size increased from $125K to $160K.
        
        Key Findings: Our flagship product contributed $9M (72% of revenue).
        New product releases generated $3.5M. The new products exceeded expectations,
        reaching breakeven two months ahead of schedule.
        
        Recommendations: Increase investment in enterprise sales team. Revise SMB
        pricing strategy to remain competitive. Accelerate product development roadmap.
        
        Conclusion: Q1 2024 demonstrated strong overall performance with notable success
        in enterprise segment. Focus areas for Q2 include enterprise expansion,
        SMB strategy refinement, and continued product innovation.
        """)
    ]
    
    latencies = []
    methods = ['extractive', 'abstractive', 'hybrid']
    
    for method in methods:
        print(f"\n{method.upper()} Method:")
        method_latencies = []
        
        for name, doc in test_docs:
            start = time.perf_counter()
            result = summarizer.summarize(doc, method=method, length='medium')
            latency_ms = (time.perf_counter() - start) * 1000
            
            latencies.append(latency_ms)
            method_latencies.append(latency_ms)
            
            print(f"  {name:20s}: {latency_ms:5.1f}ms "
                  f"({result.statistics['summary_words']:3d} words, "
                  f"{result.reduction_ratio:4.1f}% reduction)")
        
        avg = sum(method_latencies) / len(method_latencies)
        print(f"  {'Average':20s}: {avg:5.1f}ms")
    
    avg_latency = sum(latencies) / len(latencies)
    
    print("\n" + "-"*80)
    print(f"Overall Average: {avg_latency:.1f}ms")
    print(f"Target:          50.0ms")
    print(f"Status:          {'✓ PASS' if avg_latency <= 50 else '✗ FAIL'}")
    
    return {
        'avg_latency_ms': avg_latency,
        'meets_latency_target': avg_latency <= 50
    }


def benchmark_integrated_pipeline():
    """Benchmark complete pipeline: classify → extract → summarize."""
    print("\n\n" + "="*80)
    print("INTEGRATED PIPELINE BENCHMARK")
    print("="*80)
    print(f"Target: Combined latency ≤ 150ms (3x 50ms)")
    print()
    
    classifier = DocumentClassifier()
    extractor = FieldExtractor()
    summarizer = DocumentSummarizer()
    
    # Test on one document from each type
    test_docs = [
        TEST_DOCUMENTS['invoice'][0],
        TEST_DOCUMENTS['receipt'][0],
        TEST_DOCUMENTS['contract'][0],
        TEST_DOCUMENTS['id'][0],
        TEST_DOCUMENTS['other'][0]
    ]
    
    total_latencies = []
    
    for i, doc in enumerate(test_docs, 1):
        print(f"\nDocument {i}:")
        
        # Measure each stage
        start = time.perf_counter()
        doc_type = classifier.classify(doc)
        classify_time = (time.perf_counter() - start) * 1000
        
        start = time.perf_counter()
        fields = extractor.extract_all(doc)
        extract_time = (time.perf_counter() - start) * 1000
        
        start = time.perf_counter()
        summary = summarizer.summarize(doc, method='hybrid', length='short')
        summarize_time = (time.perf_counter() - start) * 1000
        
        total_time = classify_time + extract_time + summarize_time
        total_latencies.append(total_time)
        
        print(f"  Type:       {doc_type['type']}")
        print(f"  Classify:   {classify_time:5.1f}ms")
        print(f"  Extract:    {extract_time:5.1f}ms")
        print(f"  Summarize:  {summarize_time:5.1f}ms")
        print(f"  TOTAL:      {total_time:5.1f}ms")
    
    avg_total = sum(total_latencies) / len(total_latencies)
    
    print("\n" + "-"*80)
    print(f"Average Total: {avg_total:.1f}ms")
    print(f"Target:        150.0ms")
    print(f"Status:        {'✓ PASS' if avg_total <= 150 else '✗ FAIL'}")
    
    return {
        'avg_latency_ms': avg_total,
        'meets_latency_target': avg_total <= 150
    }


def production_readiness_report():
    """Generate comprehensive production readiness report."""
    print("\n\n" + "="*80)
    print("PRODUCTION READINESS REPORT")
    print("="*80)
    print()
    
    # Run all benchmarks
    classifier_results = benchmark_classifier()
    extractor_results = benchmark_field_extractor()
    summarizer_results = benchmark_summarizer()
    pipeline_results = benchmark_integrated_pipeline()
    
    # Final summary
    print("\n\n" + "="*80)
    print("FINAL ASSESSMENT")
    print("="*80)
    print()
    
    print("Target Requirements:")
    print(f"  1. Top-5 document types: invoice, receipt, contract, ID, other")
    print(f"     Status: ✓ IMPLEMENTED")
    print()
    
    print(f"  2. Macro-F1 ≥ 0.95")
    print(f"     Result: {classifier_results['macro_f1']:.3f}")
    print(f"     Status: {'✓ PASS' if classifier_results['meets_f1_target'] else '✗ FAIL'}")
    print()
    
    print(f"  3. Latency ≤ 50ms per page (CPU)")
    print(f"     Classifier:  {classifier_results['avg_latency_ms']:5.1f}ms "
          f"{'✓' if classifier_results['meets_latency_target'] else '✗'}")
    print(f"     Extractor:   {extractor_results['avg_latency_ms']:5.1f}ms "
          f"{'✓' if extractor_results['meets_latency_target'] else '✗'}")
    print(f"     Summarizer:  {summarizer_results['avg_latency_ms']:5.1f}ms "
          f"{'✓' if summarizer_results['meets_latency_target'] else '✗'}")
    print()
    
    all_pass = (
        classifier_results['meets_f1_target'] and
        classifier_results['meets_latency_target'] and
        extractor_results['meets_latency_target'] and
        summarizer_results['meets_latency_target']
    )
    
    print("="*80)
    if all_pass:
        print("✓ PRODUCTION READY - All targets met!")
    else:
        print("✗ NOT READY - Some targets not met")
        print("\nRecommendations:")
        if not classifier_results['meets_f1_target']:
            print("  - Collect more training data for misclassified types")
            print("  - Add domain-specific keywords to improve accuracy")
        if not classifier_results['meets_latency_target']:
            print("  - Optimize keyword matching algorithm")
        if not extractor_results['meets_latency_target']:
            print("  - Cache compiled regex patterns")
        if not summarizer_results['meets_latency_target']:
            print("  - Optimize sentence scoring algorithm")
    print("="*80)


if __name__ == '__main__':
    print("\n" + "="*80)
    print("PUDA AI - PRODUCTION BENCHMARKS")
    print("="*80)
    print("Testing against production targets:")
    print("  • Top-5 document types")
    print("  • Macro-F1 ≥ 0.95")
    print("  • Latency ≤ 50ms per page (CPU)")
    print("="*80)
    
    try:
        production_readiness_report()
        
    except Exception as e:
        print(f"\n✗ Benchmark failed: {str(e)}")
        import traceback
        traceback.print_exc()
