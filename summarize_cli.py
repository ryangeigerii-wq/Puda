"""
Command-line interface for document summarization.

Usage:
    python summarize_cli.py --text "Your document text here"
    python summarize_cli.py --file document.txt
    python summarize_cli.py --batch documents/ --output summaries.csv
    python summarize_cli.py --file doc.txt --method hybrid --length short
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict
import csv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.ml.summarizer import DocumentSummarizer, SummaryResult


def summarize_text(
    text: str,
    method: str = 'extractive',
    length: str = 'medium',
    format_type: str = 'text',
    include_stats: bool = False,
    include_bullets: bool = True
) -> str:
    """
    Summarize text and return formatted output.
    
    Args:
        text: Text to summarize
        method: Summarization method
        length: Summary length
        format_type: Output format ('text' or 'json')
        include_stats: Include statistics in output
        include_bullets: Include bullet points in output
        
    Returns:
        Formatted summary
    """
    summarizer = DocumentSummarizer()
    result = summarizer.summarize(text, method=method, length=length, include_bullets=include_bullets)
    
    if format_type == 'json':
        return format_json(result, include_stats)
    else:
        return format_text(result, include_stats, include_bullets)


def format_text(result: SummaryResult, include_stats: bool, include_bullets: bool) -> str:
    """Format summary as human-readable text."""
    output = []
    
    output.append("=" * 70)
    output.append("DOCUMENT SUMMARY")
    output.append("=" * 70)
    output.append("")
    output.append(result.summary)
    output.append("")
    
    if include_bullets and result.bullet_points:
        output.append("-" * 70)
        output.append("KEY POINTS:")
        output.append("-" * 70)
        for i, bullet in enumerate(result.bullet_points, 1):
            output.append(f"{i}. {bullet}")
        output.append("")
    
    if include_stats:
        output.append("-" * 70)
        output.append("SUMMARY STATISTICS:")
        output.append("-" * 70)
        output.append(f"Method:           {result.method.title()}")
        output.append(f"Length:           {result.length.title()}")
        output.append(f"Confidence:       {result.confidence:.1%}")
        output.append(f"Document Type:    {result.statistics.get('document_type', 'unknown').title()}")
        output.append(f"Original Words:   {result.statistics.get('original_words', 0)}")
        output.append(f"Summary Words:    {result.statistics.get('summary_words', 0)}")
        output.append(f"Reduction:        {result.reduction_ratio:.1f}%")
        output.append(f"Sentences:        {result.statistics.get('summary_sentences', 0)}/{result.statistics.get('original_sentences', 0)}")
        output.append("")
    
    return "\n".join(output)


def format_json(result: SummaryResult, include_stats: bool) -> str:
    """Format summary as JSON."""
    data = {
        'summary': result.summary,
        'method': result.method,
        'length': result.length,
        'confidence': round(result.confidence, 3)
    }
    
    if result.bullet_points:
        data['bullet_points'] = result.bullet_points
    
    if include_stats:
        data['statistics'] = result.statistics
        data['reduction_ratio'] = round(result.reduction_ratio, 1)
    
    return json.dumps(data, indent=2, ensure_ascii=False)


def summarize_file(
    file_path: str,
    method: str = 'extractive',
    length: str = 'medium',
    format_type: str = 'text',
    include_stats: bool = False,
    include_bullets: bool = True
) -> str:
    """Summarize a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        if not text.strip():
            return f"Error: File '{file_path}' is empty"
        
        return summarize_text(text, method, length, format_type, include_stats, include_bullets)
    
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found"
    except Exception as e:
        return f"Error processing file: {str(e)}"


def batch_summarize(
    directory: str,
    method: str = 'extractive',
    length: str = 'medium',
    output_file: str = None,
    recursive: bool = False,
    include_bullets: bool = True
) -> List[Dict]:
    """
    Summarize all text files in a directory.
    
    Args:
        directory: Path to directory
        method: Summarization method
        length: Summary length
        output_file: Optional CSV output file
        recursive: Search subdirectories
        include_bullets: Include bullet points
        
    Returns:
        List of summary results
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: Directory '{directory}' not found")
        return []
    
    # Find text files
    if recursive:
        text_files = list(dir_path.rglob('*.txt'))
    else:
        text_files = list(dir_path.glob('*.txt'))
    
    if not text_files:
        print(f"No .txt files found in '{directory}'")
        return []
    
    print(f"Found {len(text_files)} text files")
    print()
    
    summarizer = DocumentSummarizer()
    results = []
    
    for i, file_path in enumerate(text_files, 1):
        print(f"[{i}/{len(text_files)}] Processing: {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if not text.strip():
                print(f"  ⚠️  Skipping empty file")
                continue
            
            result = summarizer.summarize(text, method=method, length=length, include_bullets=include_bullets)
            
            results.append({
                'file': str(file_path),
                'filename': file_path.name,
                'summary': result.summary,
                'method': result.method,
                'length': result.length,
                'confidence': result.confidence,
                'doc_type': result.statistics.get('document_type', 'unknown'),
                'original_words': result.statistics.get('original_words', 0),
                'summary_words': result.statistics.get('summary_words', 0),
                'reduction': result.reduction_ratio,
                'bullet_points': '; '.join(result.bullet_points) if result.bullet_points else ''
            })
            
            print(f"  ✓ Summarized ({result.statistics.get('summary_words', 0)} words, "
                  f"{result.confidence:.1%} confidence)")
        
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
    
    print()
    print(f"Processed {len(results)} files successfully")
    
    # Save to CSV if requested
    if output_file and results:
        save_to_csv(results, output_file)
    
    return results


def save_to_csv(results: List[Dict], output_file: str):
    """Save batch results to CSV file."""
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
        
        print(f"✓ Results saved to: {output_file}")
    
    except Exception as e:
        print(f"✗ Error saving CSV: {str(e)}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Summarize documents using extractive or abstractive methods',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Summarize text directly
  python summarize_cli.py --text "Long document text here..."
  
  # Summarize a file with statistics
  python summarize_cli.py --file invoice.txt --stats
  
  # Use hybrid method with short summary
  python summarize_cli.py --file report.txt --method hybrid --length short
  
  # JSON output format
  python summarize_cli.py --file doc.txt --format json
  
  # Batch summarization with CSV export
  python summarize_cli.py --batch documents/ --output summaries.csv
  
  # Recursive batch processing
  python summarize_cli.py --batch documents/ --recursive --output all_summaries.csv

Methods:
  extractive   - Select most important sentences (fast, accurate)
  abstractive  - Generate new concise text (more readable)
  hybrid       - Combine both approaches (best quality)

Lengths:
  short   - 1-2 sentences (quick overview)
  medium  - 3-5 sentences (balanced)
  long    - 5-8 sentences (detailed)
        """
    )
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--text', type=str, help='Text to summarize')
    input_group.add_argument('--file', type=str, help='File to summarize')
    input_group.add_argument('--batch', type=str, help='Directory of files to summarize')
    
    # Summarization options
    parser.add_argument(
        '--method',
        type=str,
        choices=['extractive', 'abstractive', 'hybrid'],
        default='extractive',
        help='Summarization method (default: extractive)'
    )
    parser.add_argument(
        '--length',
        type=str,
        choices=['short', 'medium', 'long'],
        default='medium',
        help='Summary length (default: medium)'
    )
    
    # Output options
    parser.add_argument(
        '--format',
        type=str,
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Include statistics in output'
    )
    parser.add_argument(
        '--no-bullets',
        action='store_true',
        help='Exclude bullet points from output'
    )
    
    # Batch options
    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV file for batch results'
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Process subdirectories recursively'
    )
    
    args = parser.parse_args()
    
    # Process based on input type
    if args.text:
        # Summarize text directly
        output = summarize_text(
            args.text,
            method=args.method,
            length=args.length,
            format_type=args.format,
            include_stats=args.stats,
            include_bullets=not args.no_bullets
        )
        print(output)
    
    elif args.file:
        # Summarize single file
        output = summarize_file(
            args.file,
            method=args.method,
            length=args.length,
            format_type=args.format,
            include_stats=args.stats,
            include_bullets=not args.no_bullets
        )
        print(output)
    
    elif args.batch:
        # Batch summarization
        results = batch_summarize(
            args.batch,
            method=args.method,
            length=args.length,
            output_file=args.output,
            recursive=args.recursive,
            include_bullets=not args.no_bullets
        )
        
        if not args.output:
            # Display summary statistics
            print()
            print("=" * 70)
            print("BATCH SUMMARY")
            print("=" * 70)
            if results:
                avg_confidence = sum(r['confidence'] for r in results) / len(results)
                avg_reduction = sum(r['reduction'] for r in results) / len(results)
                
                print(f"Files processed:    {len(results)}")
                print(f"Avg confidence:     {avg_confidence:.1%}")
                print(f"Avg reduction:      {avg_reduction:.1f}%")
                
                # Document type distribution
                doc_types = {}
                for r in results:
                    dt = r['doc_type']
                    doc_types[dt] = doc_types.get(dt, 0) + 1
                
                print(f"Document types:     {', '.join(f'{k}({v})' for k, v in doc_types.items())}")


if __name__ == '__main__':
    main()
