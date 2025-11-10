"""
Warehouse Data Export Utility

Fetches analyzed documents from Puda AI /analyze endpoint and exports to CSV/Excel.
Designed for warehouse scanner integration.

Usage:
    # Export single document
    python export_warehouse_data.py --text "Invoice text here" --output warehouse_data.csv
    
    # Export from file
    python export_warehouse_data.py --file scanned_doc.txt --output results.xlsx
    
    # Batch export from directory
    python export_warehouse_data.py --batch scans/ --output batch_results.csv
"""

import requests
import json
import csv
import argparse
from pathlib import Path
from typing import List, Dict, Any
import sys

# API Configuration
API_BASE_URL = "http://localhost:8001"
ANALYZE_ENDPOINT = f"{API_BASE_URL}/analyze"


def analyze_text(text: str) -> Dict[str, Any]:
    """
    Send text to /analyze endpoint and get structured data.
    
    Args:
        text: Document text to analyze
        
    Returns:
        Structured data dictionary ready for export
    """
    try:
        response = requests.post(ANALYZE_ENDPOINT, json={"text": text})
        response.raise_for_status()
        
        result = response.json()
        return result.get("structured_data", {})
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}", file=sys.stderr)
        return {}


def analyze_file(file_path: Path) -> Dict[str, Any]:
    """
    Send file to /analyze endpoint (OCR + analysis).
    
    Args:
        file_path: Path to image or text file
        
    Returns:
        Structured data dictionary ready for export
    """
    try:
        if file_path.suffix.lower() in ['.txt']:
            # Text file - read and send as text
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return analyze_text(text)
        else:
            # Image file - send as multipart file upload
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'image/jpeg')}
                response = requests.post(ANALYZE_ENDPOINT, files=files)
                response.raise_for_status()
                
                result = response.json()
                return result.get("structured_data", {})
                
    except Exception as e:
        print(f"Error processing file {file_path}: {e}", file=sys.stderr)
        return {}


def export_to_csv(data: List[Dict[str, Any]], output_path: Path):
    """
    Export structured data to CSV file.
    
    Args:
        data: List of structured data dictionaries
        output_path: Output CSV file path
    """
    if not data:
        print("No data to export", file=sys.stderr)
        return
    
    # Get all unique field names (union of all keys)
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())
    
    fieldnames = sorted(all_keys)
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"✓ Exported {len(data)} records to {output_path}")
        
    except Exception as e:
        print(f"Error writing CSV: {e}", file=sys.stderr)


def export_to_excel(data: List[Dict[str, Any]], output_path: Path):
    """
    Export structured data to Excel file (requires openpyxl or pandas).
    
    Args:
        data: List of structured data dictionaries
        output_path: Output Excel file path
    """
    try:
        import pandas as pd
        
        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        print(f"✓ Exported {len(data)} records to {output_path}")
        
    except ImportError:
        print("Error: pandas and openpyxl required for Excel export", file=sys.stderr)
        print("Install with: pip install pandas openpyxl", file=sys.stderr)
    except Exception as e:
        print(f"Error writing Excel: {e}", file=sys.stderr)


def batch_process(directory: Path) -> List[Dict[str, Any]]:
    """
    Process all text/image files in directory.
    
    Args:
        directory: Directory containing files to process
        
    Returns:
        List of structured data dictionaries
    """
    results = []
    
    # Supported file types
    text_extensions = {'.txt'}
    image_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
    supported_extensions = text_extensions | image_extensions
    
    files = [f for f in directory.iterdir() if f.suffix.lower() in supported_extensions]
    
    print(f"Processing {len(files)} files from {directory}...")
    
    for i, file_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Processing {file_path.name}...", end=" ")
        
        structured = analyze_file(file_path)
        
        if structured:
            # Add source file info
            structured["source_file"] = file_path.name
            results.append(structured)
            print("✓")
        else:
            print("✗ (failed)")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Export warehouse scanner data from Puda AI to CSV/Excel"
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--text', type=str, help="Direct text input")
    input_group.add_argument('--file', type=Path, help="Single file to process")
    input_group.add_argument('--batch', type=Path, help="Directory for batch processing")
    
    # Output options
    parser.add_argument('--output', '-o', type=Path, required=True,
                       help="Output file path (.csv or .xlsx)")
    
    # API options
    parser.add_argument('--api-url', type=str, default=API_BASE_URL,
                       help=f"API base URL (default: {API_BASE_URL})")
    
    args = parser.parse_args()
    
    # Update API URL if provided
    global API_BASE_URL, ANALYZE_ENDPOINT
    if args.api_url:
        API_BASE_URL = args.api_url
        ANALYZE_ENDPOINT = f"{API_BASE_URL}/analyze"
    
    # Process input
    results = []
    
    if args.text:
        # Single text input
        print("Analyzing text...")
        structured = analyze_text(args.text)
        if structured:
            results.append(structured)
            
    elif args.file:
        # Single file input
        print(f"Analyzing file: {args.file}")
        structured = analyze_file(args.file)
        if structured:
            structured["source_file"] = args.file.name
            results.append(structured)
            
    elif args.batch:
        # Batch processing
        if not args.batch.is_dir():
            print(f"Error: {args.batch} is not a directory", file=sys.stderr)
            sys.exit(1)
        results = batch_process(args.batch)
    
    # Export results
    if not results:
        print("No data to export", file=sys.stderr)
        sys.exit(1)
    
    output_ext = args.output.suffix.lower()
    
    if output_ext == '.csv':
        export_to_csv(results, args.output)
    elif output_ext in ['.xlsx', '.xls']:
        export_to_excel(results, args.output)
    else:
        print(f"Error: Unsupported output format {output_ext}", file=sys.stderr)
        print("Supported formats: .csv, .xlsx", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
