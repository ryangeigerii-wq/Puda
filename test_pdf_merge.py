#!/usr/bin/env python3
"""
Quick test for PDF merge functionality

Creates sample batch and merges into PDF/A
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.organization import PDFMerger, PDFMergeAutomation
    print("✓ PDF merge modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nInstall required packages:")
    print("  pip install Pillow img2pdf pypdf")
    sys.exit(1)


def test_batch_info():
    """Test batch information retrieval."""
    print("\n=== Testing Batch Info ===")
    
    merger = PDFMerger()
    
    # Try to find any existing batch
    batches = merger._find_batch_folders(None, None, None)
    
    if not batches:
        print("No batches found in archive")
        print("Run archive automation first to create batches")
        return False
    
    print(f"Found {len(batches)} batch(es) in archive")
    
    # Get info for first batch
    batch = batches[0]
    print(f"\nChecking batch: {batch['owner']}/{batch['year']}/{batch['doc_type']}/{batch['batch_id']}")
    
    try:
        info = merger.get_batch_info(
            batch['owner'],
            batch['year'],
            batch['doc_type'],
            batch['batch_id']
        )
        
        print(f"✓ Batch info:")
        print(f"  Pages: {info['page_count']}")
        print(f"  Size: {info['total_size_mb']:.2f} MB")
        print(f"  Has PDF: {info['has_pdf']}")
        
        if info['page_count'] > 0:
            print(f"  Page IDs: {', '.join(info['pages'][:5])}")
            if len(info['pages']) > 5:
                print(f"    ... and {len(info['pages']) - 5} more")
        
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_merge_capabilities():
    """Test merge capabilities without actually creating PDF."""
    print("\n=== Testing Merge Capabilities ===")
    
    merger = PDFMerger()
    
    # Check if we can find batches to merge
    batches = merger._find_batch_folders(None, None, None)
    
    print(f"Found {len(batches)} batch(es) eligible for merging:")
    
    merge_count = 0
    for batch in batches[:5]:  # Show first 5
        info = merger.get_batch_info(
            batch['owner'],
            batch['year'],
            batch['doc_type'],
            batch['batch_id']
        )
        
        status = "✓ Ready" if info['page_count'] > 0 else "✗ No pages"
        if info['has_pdf']:
            status = "⊙ Has PDF"
        
        print(f"  {status} {batch['owner']}/{batch['year']}/{batch['doc_type']}/{batch['batch_id']} ({info['page_count']} pages)")
        
        if info['page_count'] > 0 and not info['has_pdf']:
            merge_count += 1
    
    if len(batches) > 5:
        print(f"  ... and {len(batches) - 5} more")
    
    print(f"\n{merge_count} batch(es) ready for merging")
    return merge_count > 0


def test_automation():
    """Test automation statistics."""
    print("\n=== Testing PDF Merge Automation ===")
    
    try:
        automation = PDFMergeAutomation(auto_merge=True, min_pages=1)
        
        stats = automation.get_statistics()
        print(f"✓ Automation configured:")
        print(f"  Total merged: {stats['total_merged']}")
        print(f"  Auto-merge: {stats['auto_merge_enabled']}")
        print(f"  Min pages: {stats['min_pages']}")
        
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("PDF/A Merge - Functionality Test")
    print("=" * 50)
    
    results = []
    
    # Test 1: Batch info
    results.append(("Batch Info", test_batch_info()))
    
    # Test 2: Merge capabilities
    results.append(("Merge Capabilities", test_merge_capabilities()))
    
    # Test 3: Automation
    results.append(("Automation", test_automation()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results:")
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        print("\nTo merge a batch, run:")
        print("  python archive_cli.py merge --batch-id [batch_id]")
        print("\nOr merge all batches:")
        print("  python archive_cli.py merge-auto --once")
    else:
        print("\n⚠ Some tests failed")
        print("\nMake sure:")
        print("  1. Dependencies installed: pip install Pillow img2pdf pypdf")
        print("  2. Archive has batches: python archive_cli.py stats")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
