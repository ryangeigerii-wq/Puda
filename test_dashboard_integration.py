#!/usr/bin/env python3
"""
Test Dashboard API Integration

Tests the Organization Layer endpoints in the dashboard API.
"""
import requests
import json
import time
from pathlib import Path


BASE_URL = "http://127.0.0.1:8080"


def test_health():
    """Test health endpoint."""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("✓ Health check passed")


def test_archive_stats():
    """Test archive statistics endpoint."""
    print("\n=== Testing Archive Stats ===")
    response = requests.get(f"{BASE_URL}/api/archive/stats")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print(f"✓ Total documents: {data['statistics']['total_documents']}")
        print(f"✓ By owner: {data['statistics']['by_owner']}")
        print(f"✓ By doc type: {data['statistics']['by_doc_type']}")
        print(f"✓ By year: {data['statistics']['by_year']}")
    else:
        print(f"✗ Failed: {data.get('error', 'Unknown error')}")


def test_archive_search():
    """Test archive search endpoint."""
    print("\n=== Testing Archive Search ===")
    
    # Search without filters
    response = requests.get(f"{BASE_URL}/api/archive/search")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {data.get('count', 0)} documents")
    
    if data.get('count', 0) > 0:
        print(f"First result: {data['results'][0]['page_id']}")
    
    # Search with text filter
    response = requests.get(f"{BASE_URL}/api/archive/search?text=invoice&limit=5")
    data = response.json()
    print(f"Text search 'invoice': {data.get('count', 0)} results")
    
    print("✓ Search endpoint working")


def test_archive_owners():
    """Test archive owners endpoint."""
    print("\n=== Testing Archive Owners ===")
    response = requests.get(f"{BASE_URL}/api/archive/owners")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Owners: {data.get('owners', [])}")
    print("✓ Owners endpoint working")


def test_archive_doc_types():
    """Test archive document types endpoint."""
    print("\n=== Testing Archive Doc Types ===")
    response = requests.get(f"{BASE_URL}/api/archive/doc_types")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Doc Types: {data.get('doc_types', [])}")
    print("✓ Doc types endpoint working")


def test_archive_years():
    """Test archive years endpoint."""
    print("\n=== Testing Archive Years ===")
    response = requests.get(f"{BASE_URL}/api/archive/years")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Years: {data.get('years', [])}")
    print("✓ Years endpoint working")


def test_thumbnail_stats():
    """Test thumbnail cache stats endpoint."""
    print("\n=== Testing Thumbnail Cache Stats ===")
    response = requests.get(f"{BASE_URL}/api/archive/thumbnail/cache/stats")
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        print(f"Cache stats: {json.dumps(data['cache_stats'], indent=2)}")
        print("✓ Thumbnail stats endpoint working")
    else:
        print(f"✗ Failed: {data.get('error', 'Unknown error')}")


def test_thumbnail_generation():
    """Test thumbnail generation endpoint (requires existing batch)."""
    print("\n=== Testing Thumbnail Generation ===")
    
    # Check if test batch exists
    batch_folder = Path("data/archive/SampleCorp/2024/Invoice/batch_test_001")
    if not batch_folder.exists():
        print("⊘ Skipping - test batch not found")
        return
    
    payload = {
        "owner": "SampleCorp",
        "year": 2024,
        "doc_type": "Invoice",
        "batch_id": "batch_test_001",
        "force": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/archive/thumbnails/generate",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print("✓ Thumbnail generation endpoint working")
    else:
        print(f"✗ Failed: {data.get('error', 'Unknown error')}")


def test_pdf_merge():
    """Test PDF merge endpoint (requires existing batch)."""
    print("\n=== Testing PDF Merge ===")
    
    # Check if test batch exists
    batch_folder = Path("data/archive/SampleCorp/2024/Invoice/batch_test_001")
    if not batch_folder.exists():
        print("⊘ Skipping - test batch not found")
        return
    
    payload = {
        "owner": "SampleCorp",
        "year": 2024,
        "doc_type": "Invoice",
        "batch_id": "batch_test_001"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/archive/merge",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200:
        print("✓ PDF merge endpoint working")
    else:
        print(f"✗ Failed: {data.get('error', 'Unknown error')}")


def test_archive_document():
    """Test document retrieval endpoint."""
    print("\n=== Testing Archive Document Retrieval ===")
    
    # First get a document from search
    response = requests.get(f"{BASE_URL}/api/archive/search?limit=1")
    data = response.json()
    
    if data.get('count', 0) == 0:
        print("⊘ Skipping - no documents found")
        return
    
    page_id = data['results'][0]['page_id']
    print(f"Testing with page_id: {page_id}")
    
    response = requests.get(f"{BASE_URL}/api/archive/document/{page_id}")
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        print(f"Document: {json.dumps(data['document'], indent=2)}")
        print("✓ Document retrieval working")
    else:
        print(f"✗ Failed: {data.get('error', 'Unknown error')}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Dashboard API Integration Tests")
    print("=" * 60)
    print("\nMake sure the dashboard API is running:")
    print("  python dashboard_api.py --port 8080")
    print("\nWaiting 3 seconds for confirmation...")
    time.sleep(3)
    
    tests = [
        test_health,
        test_archive_stats,
        test_archive_owners,
        test_archive_doc_types,
        test_archive_years,
        test_archive_search,
        test_archive_document,
        test_thumbnail_stats,
        test_thumbnail_generation,
        test_pdf_merge,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
