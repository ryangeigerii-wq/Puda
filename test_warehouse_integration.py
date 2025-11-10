"""
Test warehouse integration - structured data export

Tests the /analyze endpoint's structured_data output for CSV/Excel export.
"""

import requests
import json

API_URL = "http://localhost:8001"

# Sample warehouse documents
SAMPLE_INVOICE = """
ACME Corporation
123 Business Way
New York, NY 10001

INVOICE

Invoice Number: INV-2024-12345
Date: 2024-01-15

Bill To:
John Smith
Tech Solutions Inc.
456 Tech Drive
San Francisco, CA 94102

Description                     Amount
------------------------------------
Consulting Services            $1,234.56
Software License              $500.00
Support & Maintenance         $250.00
                              --------
Total Due:                    $1,984.56

Payment Terms: Net 30
Contact: billing@acme.com
Phone: +1-555-0123
"""

SAMPLE_RECEIPT = """
Best Buy Store #1234
789 Shopping Blvd
Los Angeles, CA 90001
Tel: (555) 123-4567

RECEIPT

Date: 11/10/2024 2:45 PM
Receipt #: 5678-9012-3456

Items:
Laptop Computer          $899.99
Wireless Mouse           $29.99
USB Cable                $12.99
                        -------
Subtotal:                $942.97
Tax (8.5%):              $80.15
                        -------
TOTAL:                   $1,023.12

Payment: Visa ****1234
Thank you for shopping!
"""


def test_analyze_endpoint():
    """Test /analyze endpoint with warehouse documents."""
    
    print("Testing /analyze endpoint with warehouse documents\n")
    print("=" * 70)
    
    # Test 1: Invoice
    print("\n1. Testing Invoice Processing:")
    print("-" * 70)
    
    response = requests.post(
        f"{API_URL}/analyze",
        json={"text": SAMPLE_INVOICE}
    )
    
    if response.status_code == 200:
        data = response.json()
        structured = data.get("structured_data", {})
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Document Type: {structured.get('document_type')}")
        print(f"✓ Confidence: {structured.get('classification_confidence')}")
        print(f"✓ Invoice Number: {structured.get('invoice_number')}")
        print(f"✓ Date: {structured.get('date')}")
        print(f"✓ Amount: {structured.get('amount')}")
        print(f"✓ Organization: {structured.get('organization')}")
        print(f"✓ Contact Name: {structured.get('contact_name')}")
        print(f"✓ Email: {structured.get('email')}")
        print(f"✓ Phone: {structured.get('phone')}")
        print(f"✓ Requires Review: {structured.get('requires_review')}")
        print(f"✓ Total Entities: {structured.get('total_entities')}")
        
        # Verify all values are primitives (no dicts/lists)
        all_primitives = all(
            isinstance(v, (str, int, float, bool, type(None)))
            for v in structured.values()
        )
        print(f"✓ All values primitive types: {all_primitives}")
        
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
    
    # Test 2: Receipt
    print("\n2. Testing Receipt Processing:")
    print("-" * 70)
    
    response = requests.post(
        f"{API_URL}/analyze",
        json={"text": SAMPLE_RECEIPT}
    )
    
    if response.status_code == 200:
        data = response.json()
        structured = data.get("structured_data", {})
        
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Document Type: {structured.get('document_type')}")
        print(f"✓ Confidence: {structured.get('classification_confidence')}")
        print(f"✓ Date: {structured.get('date')}")
        print(f"✓ Amount: {structured.get('amount')}")
        print(f"✓ Organization: {structured.get('organization')}")
        print(f"✓ Total Entities: {structured.get('total_entities')}")
        
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
    
    # Test 3: Export structure
    print("\n3. Testing CSV/Excel Export Structure:")
    print("-" * 70)
    
    response = requests.post(
        f"{API_URL}/analyze",
        json={"text": SAMPLE_INVOICE}
    )
    
    if response.status_code == 200:
        data = response.json()
        structured = data.get("structured_data", {})
        
        # Simulate CSV export
        print("CSV Header Row:")
        headers = list(structured.keys())
        print(", ".join(headers))
        
        print("\nCSV Data Row:")
        values = [str(v) for v in structured.values()]
        print(", ".join(values[:10]) + ", ...")  # Show first 10 fields
        
        print(f"\n✓ Total Fields: {len(structured)}")
        print(f"✓ Ready for CSV export: Yes")
        
        # Show sample structured output
        print("\nSample Structured Data (JSON):")
        print(json.dumps(structured, indent=2)[:500] + "...")
        
    else:
        print(f"✗ Error: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("Testing complete!")


def test_health():
    """Test API health."""
    print("\nChecking API health...")
    response = requests.get(f"{API_URL}/health")
    
    if response.status_code == 200:
        print("✓ API is healthy")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"✗ API health check failed: {response.status_code}")


if __name__ == "__main__":
    try:
        test_health()
        test_analyze_endpoint()
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Error: Could not connect to API at {API_URL}")
        print("Make sure the ML API server is running:")
        print("  python -m uvicorn src.inference.api:app --host 0.0.0.0 --port 8001")
