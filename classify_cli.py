"""
Document Classifier CLI

Command-line tool for classifying documents.

Usage:
    # Classify text directly
    python classify_cli.py --text "Invoice text here..."
    
    # Classify from file
    python classify_cli.py --file document.txt
    
    # Classify with explanation
    python classify_cli.py --file document.txt --explain
    
    # Batch classify multiple files
    python classify_cli.py --batch documents/ --output results.csv
    
    # Use trained model
    python classify_cli.py --file doc.txt --model models/puda_trained.pt
"""

import argparse
import sys
from pathlib import Path
import json
import csv

try:
    from src.ml.classifier import DocumentClassifier
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    print("Warning: Classifier module not available", file=sys.stderr)


def classify_text(text: str, model_path: Path = None, explain: bool = False):
    """Classify text and print results."""
    try:
        classifier = DocumentClassifier(model_path=model_path)
        
        if explain:
            result = classifier.explain_classification(text)
            print(json.dumps(result, indent=2))
        else:
            result = classifier.classify(text)
            print(json.dumps(result, indent=2))
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def classify_file(file_path: Path, model_path: Path = None, explain: bool = False):
    """Classify document from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f"Classifying: {file_path}")
        print("=" * 70)
        classify_text(text, model_path, explain)
    
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)


def classify_batch(directory: Path, output: Path = None, model_path: Path = None):
    """Classify all documents in directory."""
    try:
        classifier = DocumentClassifier(model_path=model_path)
        
        # Find all text files
        text_files = list(directory.glob("*.txt"))
        if not text_files:
            print(f"No .txt files found in {directory}", file=sys.stderr)
            sys.exit(1)
        
        print(f"Found {len(text_files)} documents to classify")
        print("=" * 70)
        
        results = []
        
        for i, file_path in enumerate(text_files, 1):
            print(f"[{i}/{len(text_files)}] {file_path.name}...", end=" ")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                result = classifier.classify(text, return_all_scores=False)
                result['file'] = file_path.name
                results.append(result)
                
                print(f"✓ {result['doc_type']} ({result['confidence']:.2%})")
            
            except Exception as e:
                print(f"✗ Error: {e}")
                results.append({
                    'file': file_path.name,
                    'doc_type': 'error',
                    'confidence': 0.0,
                    'needs_review': True
                })
        
        # Export results
        if output:
            if output.suffix == '.csv':
                export_csv(results, output)
            elif output.suffix == '.json':
                export_json(results, output)
            else:
                print(f"Unsupported output format: {output.suffix}", file=sys.stderr)
        else:
            # Print summary
            print("\n" + "=" * 70)
            print("Classification Summary:")
            print("-" * 70)
            
            # Count by type
            type_counts = {}
            for r in results:
                doc_type = r['doc_type']
                type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
            for doc_type, count in sorted(type_counts.items()):
                print(f"  {doc_type}: {count}")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def export_csv(results, output_path):
    """Export results to CSV."""
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['file', 'doc_type', 'confidence', 'needs_review']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\n✓ Exported to {output_path}")
    
    except Exception as e:
        print(f"Error exporting CSV: {e}", file=sys.stderr)


def export_json(results, output_path):
    """Export results to JSON."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Exported to {output_path}")
    
    except Exception as e:
        print(f"Error exporting JSON: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Classify documents by type (invoice, receipt, contract, ID, etc.)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Classify text
  python classify_cli.py --text "Invoice #12345 Amount: $100"
  
  # Classify file with explanation
  python classify_cli.py --file invoice.txt --explain
  
  # Batch classify with CSV export
  python classify_cli.py --batch documents/ --output results.csv
  
  # Use trained model
  python classify_cli.py --file doc.txt --model models/puda_trained.pt
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--text', type=str, help="Text to classify")
    input_group.add_argument('--file', type=Path, help="File to classify")
    input_group.add_argument('--batch', type=Path, help="Directory for batch classification")
    
    # Options
    parser.add_argument('--model', type=Path, help="Path to trained model checkpoint")
    parser.add_argument('--explain', action='store_true', help="Provide explanation for classification")
    parser.add_argument('--output', '-o', type=Path, help="Output file for batch results (.csv or .json)")
    
    args = parser.parse_args()
    
    # Check if classifier available
    if not CLASSIFIER_AVAILABLE:
        print("Error: Classifier not available. Install required dependencies.", file=sys.stderr)
        sys.exit(1)
    
    # Process input
    if args.text:
        classify_text(args.text, args.model, args.explain)
    
    elif args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        classify_file(args.file, args.model, args.explain)
    
    elif args.batch:
        if not args.batch.is_dir():
            print(f"Error: Not a directory: {args.batch}", file=sys.stderr)
            sys.exit(1)
        classify_batch(args.batch, args.output, args.model)


if __name__ == "__main__":
    main()
