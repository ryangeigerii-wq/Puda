#!/usr/bin/env python3
"""
Test metadata generation for PDF merge

Creates sample batch and demonstrates metadata writing
"""

import json
import csv
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None


def create_sample_batch():
    """Create a sample batch for testing."""
    print("Creating sample batch...")
    
    if not Image:
        print("Warning: PIL not available, cannot create sample images")
        print("Install: pip install Pillow")
        return None
    
    # Create batch folder
    batch_folder = Path("data/archive/SampleCorp/2024/Invoice/batch_test_001")
    batch_folder.mkdir(parents=True, exist_ok=True)
    
    # Create sample pages
    for i in range(1, 4):
        page_id = f"INV_{i:03d}"
        
        # Create actual PNG image
        image_file = batch_folder / f"{page_id}.png"
        img = Image.new('RGB', (800, 1000), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw sample invoice content
        y_pos = 50
        draw.text((50, y_pos), "INVOICE", fill='black')
        y_pos += 50
        draw.text((50, y_pos), f"Invoice Number: INV-2024-{i:03d}", fill='black')
        y_pos += 30
        draw.text((50, y_pos), "Date: January 15, 2024", fill='black')
        y_pos += 30
        draw.text((50, y_pos), "Customer: SampleCorp", fill='black')
        y_pos += 50
        draw.text((50, y_pos), "Items:", fill='black')
        y_pos += 30
        draw.text((70, y_pos), "- Product A: $500.00", fill='black')
        y_pos += 30
        draw.text((70, y_pos), f"- Product B: ${250 + i * 250}.00", fill='black')
        y_pos += 50
        draw.text((50, y_pos), f"Total Amount: ${1000 + i * 250}.00", fill='black')
        y_pos += 30
        draw.text((50, y_pos), "Due Date: February 15, 2024", fill='black')
        
        img.save(image_file)
        
        # Create JSON metadata
        json_file = batch_folder / f"{page_id}.json"
        metadata = {
            'page_id': page_id,
            'doc_type': 'Invoice',
            'owner': 'SampleCorp',
            'year': '2024',
            'processing': {
                'extraction': {
                    'fields': {
                        'invoice_number': f'INV-2024-{i:03d}',
                        'customer_name': 'SampleCorp',
                        'invoice_date': '2024-01-15',
                        'total_amount': f'{1000 + i * 250}.00',
                        'due_date': '2024-02-15'
                    }
                },
                'classification': {
                    'document_type': 'Invoice',
                    'confidence': 0.95 + i * 0.01
                },
                'qc_verification': {
                    'passed': True if i != 2 else False,  # Second page fails QC
                    'verified_at': datetime.now().isoformat(),
                    'verified_by': 'test_operator'
                }
            }
        }
        json_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        
        # Create OCR text
        ocr_file = batch_folder / f"{page_id}_ocr.txt"
        ocr_text = f"""
        INVOICE
        Invoice Number: INV-2024-{i:03d}
        Date: January 15, 2024
        Customer: SampleCorp
        
        Items:
        - Product A: $500.00
        - Product B: ${250 + i * 250}.00
        
        Total Amount: ${1000 + i * 250}.00
        Due Date: February 15, 2024
        """
        ocr_file.write_text(ocr_text, encoding='utf-8')
        
        print(f"  ✓ Created {page_id}")
    
    print(f"\n✓ Sample batch created: {batch_folder}")
    return batch_folder


def test_metadata_generation():
    """Test metadata file generation."""
    print("\n=== Testing Metadata Generation ===\n")
    
    # Import after creating sample data
    try:
        from src.organization import PDFMerger
    except ImportError as e:
        print(f"Error: {e}")
        return False
    
    try:
        # Ensure sample batch exists
        batch_folder = Path("data/archive/SampleCorp/2024/Invoice/batch_test_001")
        if not batch_folder.exists():
            batch_folder = create_sample_batch()
        
        # Create merger
        merger = PDFMerger()
        
        # Merge batch (this will create PDF + metadata)
        print("Merging batch and generating metadata...\n")
        pdf_path = merger.merge_batch(
            owner="SampleCorp",
            year="2024",
            doc_type="Invoice",
            batch_id="batch_test_001"
        )
        
        print(f"\n✓ PDF created: {pdf_path}")
        
        # Check for metadata files
        json_file = pdf_path.parent / f"{pdf_path.stem}_metadata.json"
        csv_file = pdf_path.parent / f"{pdf_path.stem}_pages.csv"
        
        if json_file.exists():
            print(f"✓ JSON metadata: {json_file}")
            
            # Display JSON content
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            print(f"\n=== JSON Metadata ===")
            print(f"Batch: {metadata['batch']['batch_id']}")
            print(f"Pages: {metadata['batch']['page_count']}")
            print(f"QC Passed: {metadata['summary']['qc_passed']}")
            print(f"QC Failed: {metadata['summary']['qc_failed']}")
            print(f"Fields: {', '.join(metadata['summary']['fields_extracted'].keys())}")
        
        if csv_file.exists():
            print(f"\n✓ CSV inventory: {csv_file}")
            
            # Display CSV content
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            print(f"\n=== CSV Inventory ===")
            print(f"Columns: {len(reader.fieldnames or [])}")
            print(f"Rows: {len(rows)}")
            
            if rows:
                print(f"\nSample row:")
                for key, value in list(rows[0].items())[:5]:
                    print(f"  {key}: {value}")
        
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def view_metadata():
    """View metadata using CLI command."""
    print("\n=== Viewing Metadata via CLI ===\n")
    print("To view metadata, run:")
    print("  python archive_cli.py metadata SampleCorp 2024 Invoice batch_test_001")
    print("\nWith page details:")
    print("  python archive_cli.py metadata SampleCorp 2024 Invoice batch_test_001 --show-pages")
    print("\nWith CSV data:")
    print("  python archive_cli.py metadata SampleCorp 2024 Invoice batch_test_001 --show-csv")


def main():
    """Run test."""
    print("PDF Metadata Generation Test")
    print("=" * 50)
    
    # Create sample batch
    create_sample_batch()
    
    # Test metadata generation
    if test_metadata_generation():
        print("\n" + "=" * 50)
        print("✓ Metadata generation successful!")
        
        # Show how to view metadata
        view_metadata()
    else:
        print("\n✗ Metadata generation failed")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
