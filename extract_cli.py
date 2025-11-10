"""
Field Extractor CLI

Command-line tool for extracting dates, amounts, and names from documents.

Usage:
    # Extract from text
    python extract_cli.py --text "Invoice dated 01/15/2024 for $1,234.56"
    
    # Extract from file
    python extract_cli.py --file invoice.txt
    
    # Extract specific field types
    python extract_cli.py --file doc.txt --fields dates amounts
    
    # Batch extraction with CSV output
    python extract_cli.py --batch documents/ --output results.csv
    
    # JSON output
    python extract_cli.py --file doc.txt --format json
"""

import argparse
import sys
from pathlib import Path
import json
import csv

try:
    from src.ml.field_extractor import FieldExtractor
    EXTRACTOR_AVAILABLE = True
except ImportError:
    EXTRACTOR_AVAILABLE = False
    print("Warning: Field extractor module not available", file=sys.stderr)


def extract_from_text(text: str, field_types: list = None):
    """Extract fields from text and print results."""
    try:
        extractor = FieldExtractor()
        
        if field_types is None:
            field_types = ['dates', 'amounts', 'names']
        
        print("Field Extraction Results")
        print("=" * 70)
        print()
        
        if 'dates' in field_types:
            dates = extractor.extract_dates(text)
            print(f"Dates Found: {len(dates)}")
            print("-" * 70)
            for i, date in enumerate(dates[:10], 1):  # Show top 10
                print(f"{i}. {date['text']}")
                if date.get('normalized'):
                    print(f"   Normalized: {date['normalized']}")
                print(f"   Confidence: {date['confidence']:.2%}")
                print(f"   Context: {date['context'][:60]}...")
                print()
        
        if 'amounts' in field_types:
            amounts = extractor.extract_amounts(text)
            print(f"\nAmounts Found: {len(amounts)}")
            print("-" * 70)
            for i, amount in enumerate(amounts[:10], 1):  # Show top 10
                print(f"{i}. {amount['text']} = {amount['currency']} {amount['value']:,.2f}")
                print(f"   Type: {amount['type']}")
                print(f"   Confidence: {amount['confidence']:.2%}")
                print(f"   Context: {amount['context'][:60]}...")
                print()
        
        if 'names' in field_types:
            names = extractor.extract_names(text)
            print(f"\nNames Found: {len(names)}")
            print("-" * 70)
            for i, name in enumerate(names[:10], 1):  # Show top 10
                print(f"{i}. {name['text']}")
                print(f"   Role: {name['role']}")
                print(f"   Confidence: {name['confidence']:.2%}")
                print(f"   Context: {name['context'][:60]}...")
                print()
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def extract_from_file(file_path: Path, field_types: list = None, output_format: str = 'text'):
    """Extract fields from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        extractor = FieldExtractor()
        results = extractor.extract_all(text)
        
        # Filter field types if specified
        if field_types:
            results = {k: v for k, v in results.items() if k in field_types}
        
        if output_format == 'json':
            print(json.dumps(results, indent=2))
        else:
            print(f"File: {file_path}")
            print("=" * 70)
            print()
            
            for field_type, items in results.items():
                print(f"{field_type.upper()}: {len(items)} found")
                print("-" * 70)
                for i, item in enumerate(items[:5], 1):  # Show top 5
                    print(f"{i}. {item['text']}")
                    if field_type == 'dates' and item.get('normalized'):
                        print(f"   Normalized: {item['normalized']}")
                    elif field_type == 'amounts':
                        print(f"   Value: {item['currency']} {item['value']:,.2f}")
                        print(f"   Type: {item['type']}")
                    elif field_type == 'names':
                        print(f"   Role: {item['role']}")
                    print(f"   Confidence: {item['confidence']:.2%}")
                print()
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def batch_extract(directory: Path, output: Path = None, field_types: list = None):
    """Extract fields from all files in directory."""
    try:
        extractor = FieldExtractor()
        
        # Find all text files
        text_files = list(directory.glob("*.txt"))
        if not text_files:
            print(f"No .txt files found in {directory}", file=sys.stderr)
            sys.exit(1)
        
        print(f"Processing {len(text_files)} documents...")
        print("=" * 70)
        
        all_results = []
        
        for i, file_path in enumerate(text_files, 1):
            print(f"[{i}/{len(text_files)}] {file_path.name}...", end=" ")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                results = extractor.extract_all(text)
                
                # Filter field types
                if field_types:
                    results = {k: v for k, v in results.items() if k in field_types}
                
                # Flatten for CSV
                file_result = {
                    'file': file_path.name,
                    'dates_count': len(results.get('dates', [])),
                    'amounts_count': len(results.get('amounts', [])),
                    'names_count': len(results.get('names', [])),
                }
                
                # Add first date if available
                if results.get('dates'):
                    first_date = results['dates'][0]
                    file_result['first_date'] = first_date['text']
                    file_result['first_date_normalized'] = first_date.get('normalized', '')
                    file_result['first_date_confidence'] = first_date['confidence']
                
                # Add first amount if available
                if results.get('amounts'):
                    first_amount = results['amounts'][0]
                    file_result['first_amount'] = first_amount['text']
                    file_result['first_amount_value'] = first_amount['value']
                    file_result['first_amount_type'] = first_amount['type']
                    file_result['first_amount_confidence'] = first_amount['confidence']
                
                # Add first name if available
                if results.get('names'):
                    first_name = results['names'][0]
                    file_result['first_name'] = first_name['text']
                    file_result['first_name_role'] = first_name['role']
                    file_result['first_name_confidence'] = first_name['confidence']
                
                all_results.append(file_result)
                
                print(f"✓ (D:{file_result['dates_count']} A:{file_result['amounts_count']} N:{file_result['names_count']})")
            
            except Exception as e:
                print(f"✗ Error: {e}")
                all_results.append({
                    'file': file_path.name,
                    'dates_count': 0,
                    'amounts_count': 0,
                    'names_count': 0,
                    'error': str(e)
                })
        
        # Export results
        if output:
            if output.suffix == '.csv':
                export_csv(all_results, output)
            elif output.suffix == '.json':
                export_json(all_results, output)
            else:
                print(f"Unsupported output format: {output.suffix}", file=sys.stderr)
        else:
            # Print summary
            print("\n" + "=" * 70)
            print("Extraction Summary:")
            print("-" * 70)
            total_dates = sum(r['dates_count'] for r in all_results)
            total_amounts = sum(r['amounts_count'] for r in all_results)
            total_names = sum(r['names_count'] for r in all_results)
            print(f"Total Dates: {total_dates}")
            print(f"Total Amounts: {total_amounts}")
            print(f"Total Names: {total_names}")
            print(f"Average per document: D:{total_dates/len(all_results):.1f} "
                  f"A:{total_amounts/len(all_results):.1f} "
                  f"N:{total_names/len(all_results):.1f}")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def export_csv(results, output_path):
    """Export results to CSV."""
    try:
        if not results:
            print("No results to export", file=sys.stderr)
            return
        
        # Get all possible fieldnames
        fieldnames = set()
        for r in results:
            fieldnames.update(r.keys())
        fieldnames = sorted(fieldnames)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\n✓ Exported {len(results)} results to {output_path}")
    
    except Exception as e:
        print(f"Error exporting CSV: {e}", file=sys.stderr)


def export_json(results, output_path):
    """Export results to JSON."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Exported {len(results)} results to {output_path}")
    
    except Exception as e:
        print(f"Error exporting JSON: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Extract dates, amounts, and names from documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all fields from text
  python extract_cli.py --text "Invoice dated 01/15/2024 for $1,234.56"
  
  # Extract from file with JSON output
  python extract_cli.py --file invoice.txt --format json
  
  # Extract only dates and amounts
  python extract_cli.py --file doc.txt --fields dates amounts
  
  # Batch extract with CSV output
  python extract_cli.py --batch documents/ --output results.csv
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--text', type=str, help="Text to extract from")
    input_group.add_argument('--file', type=Path, help="File to extract from")
    input_group.add_argument('--batch', type=Path, help="Directory for batch extraction")
    
    # Options
    parser.add_argument(
        '--fields',
        nargs='+',
        choices=['dates', 'amounts', 'names'],
        help="Specific field types to extract (default: all)"
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help="Output format (default: text)"
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help="Output file for batch results (.csv or .json)"
    )
    
    args = parser.parse_args()
    
    # Check if extractor available
    if not EXTRACTOR_AVAILABLE:
        print("Error: Field extractor not available. Install required dependencies.", file=sys.stderr)
        sys.exit(1)
    
    # Process input
    if args.text:
        extract_from_text(args.text, args.fields)
    
    elif args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        extract_from_file(args.file, args.fields, args.format)
    
    elif args.batch:
        if not args.batch.is_dir():
            print(f"Error: Not a directory: {args.batch}", file=sys.stderr)
            sys.exit(1)
        batch_extract(args.batch, args.output, args.fields)


if __name__ == "__main__":
    main()
