#!/usr/bin/env python3
"""
Test thumbnail generation

Generates thumbnails for the sample batch
"""

import sys
from pathlib import Path

try:
    from src.organization import ThumbnailGenerator, ThumbnailAutomation
    print("✓ Thumbnail modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def test_thumbnail_generation():
    """Test thumbnail generation for sample batch."""
    print("\n=== Testing Thumbnail Generation ===\n")
    
    # Check if sample batch exists
    batch_folder = Path("data/archive/SampleCorp/2024/Invoice/batch_test_001")
    if not batch_folder.exists():
        print("Sample batch not found. Run test_metadata.py first.")
        return False
    
    try:
        # Create generator
        generator = ThumbnailGenerator()
        
        # Generate thumbnails
        print("Generating thumbnails...")
        stats = generator.generate_batch_thumbnails(
            owner="SampleCorp",
            year="2024",
            doc_type="Invoice",
            batch_id="batch_test_001"
        )
        
        print(f"\n✓ Thumbnail Generation Complete:")
        print(f"  Total Images: {stats['total_images']}")
        print(f"  Generated: {stats['generated']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")
        
        # Show generated thumbnails
        if stats['thumbnails']:
            print(f"\n✓ Generated Sizes:")
            first_page = list(stats['thumbnails'].values())[0]
            for size in first_page.keys():
                print(f"  - {size}")
        
        # Get cache stats
        cache_stats = generator.get_cache_stats()
        print(f"\n✓ Cache Statistics:")
        print(f"  Thumbnail Count: {cache_stats['thumbnail_count']}")
        print(f"  Total Size: {cache_stats['total_size_mb']:.2f} MB")
        print(f"  Cache Directory: {cache_stats['cache_dir']}")
        
        # Test thumbnail retrieval
        print(f"\n✓ Testing Thumbnail Retrieval:")
        for size in ['icon', 'small', 'medium', 'large']:
            thumb = generator.get_thumbnail('INV_001', size)
            if thumb:
                print(f"  {size}: {thumb.name} ({thumb.stat().st_size / 1024:.1f} KB)")
        
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_automation():
    """Test thumbnail automation."""
    print("\n=== Testing Thumbnail Automation ===\n")
    
    try:
        automation = ThumbnailAutomation(auto_generate=True)
        
        # Process all batches
        print("Scanning archive for batches...")
        count = automation.scan_and_generate()
        
        print(f"\n✓ Processed {count} batch(es)")
        
        # Get statistics
        stats = automation.get_statistics()
        print(f"\n✓ Automation Statistics:")
        print(f"  Total Processed: {stats['total_processed']}")
        print(f"  Auto-Generate: {stats['auto_generate_enabled']}")
        print(f"  Cache: {stats['cache_stats']['thumbnail_count']} thumbnails")
        print(f"  Size: {stats['cache_stats']['total_size_mb']:.2f} MB")
        
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def show_thumbnails():
    """Show how to view thumbnails."""
    print("\n=== Viewing Thumbnails ===\n")
    
    cache_dir = Path("data/archive/.thumbnails")
    
    if cache_dir.exists():
        thumbnails = list(cache_dir.glob("*.jpg"))
        manifests = list(cache_dir.glob("*.json"))
        
        print(f"Cache directory: {cache_dir}")
        print(f"Thumbnails: {len(thumbnails)}")
        print(f"Manifests: {len(manifests)}")
        
        if thumbnails:
            print(f"\nSample thumbnails:")
            for thumb in sorted(thumbnails)[:8]:
                size_kb = thumb.stat().st_size / 1024
                print(f"  {thumb.name} ({size_kb:.1f} KB)")
    
    print("\n=== CLI Commands ===")
    print("Generate thumbnails:")
    print("  python archive_cli.py thumbnails SampleCorp 2024 Invoice batch_test_001")
    print("\nAuto-generate all:")
    print("  python archive_cli.py thumbnails-auto --once")
    print("\nView cache stats:")
    print("  python archive_cli.py thumbnails-stats")
    print("\nClear cache:")
    print("  python archive_cli.py thumbnails-clear --all")


def main():
    """Run tests."""
    print("Thumbnail Generation Test")
    print("=" * 50)
    
    results = []
    
    # Test 1: Thumbnail generation
    results.append(("Thumbnail Generation", test_thumbnail_generation()))
    
    # Test 2: Automation
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
        show_thumbnails()
    else:
        print("\n✗ Some tests failed")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
