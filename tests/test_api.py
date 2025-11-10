"""Quick test script for ML API endpoints"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_health():
    """Test health check"""
    print("\n=== Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(json.dumps(response.json(), indent=2))

def test_classify():
    """Test classification endpoint"""
    print("\n=== Classification ===")
    data = {
        "text": "Invoice from ACME Corp dated Nov 10, 2025 for $1,500.00. Payment due in 30 days."
    }
    response = requests.post(f"{BASE_URL}/classify", json=data)
    print(json.dumps(response.json(), indent=2))

def test_extract():
    """Test extraction endpoint"""
    print("\n=== Extraction ===")
    data = {
        "text": "Invoice #INV-2025-001 dated 2025-11-10 for $1,500.00. Contact: john@acme.com or +1-555-0123"
    }
    response = requests.post(f"{BASE_URL}/extract", json=data)
    print(json.dumps(response.json(), indent=2))

def test_summarize():
    """Test summarization endpoint"""
    print("\n=== Summarization ===")
    data = {
        "text": """
        Invoice from ACME Corporation
        Date: November 10, 2025
        Invoice Number: INV-2025-001
        
        Items:
        - Professional Services: $1,200.00
        - Consulting Fee: $300.00
        
        Total Amount Due: $1,500.00
        Payment Terms: Net 30 days
        
        Please remit payment to:
        ACME Corp, 123 Business St, New York, NY 10001
        """
    }
    response = requests.post(f"{BASE_URL}/summarize", json=data)
    print(json.dumps(response.json(), indent=2))

def test_analyze():
    """Test full pipeline"""
    print("\n=== Full Analysis ===")
    # Using text input
    response = requests.post(
        f"{BASE_URL}/analyze",
        params={"text": "Invoice #INV-001 dated 2025-11-10 total $1,500.00"}
    )
    result = response.json()
    
    print(f"Doc Type: {result['classification']['doc_type']} ({result['classification']['confidence']:.2%})")
    print(f"Extracted Fields: {result['extraction']['count']}")
    print(f"Summary: {result['summary']['summary'][:100]}...")
    print(f"Metrics: {json.dumps(result['metrics'], indent=2)}")

def main():
    """Run all tests"""
    print("Testing ML API...")
    print("Make sure API is running: python src/inference/api.py")
    
    try:
        test_health()
        test_classify()
        test_extract()
        test_summarize()
        test_analyze()
        
        print("\n✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to API. Is it running?")
        print("Start it with: python src/inference/api.py")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()
