#!/usr/bin/env python3
"""
Archive Management CLI - Manual document organization interface

Commands:
- search: Search archived documents with filters
- retrieve: Get document files and metadata
- stats: View archive statistics
- integrity: Check archive integrity
- reindex: Rebuild search index
- auto: Start automation daemon
"""

import sys
import json
import csv
from pathlib import Path
from typing import Optional
import argparse

from src.organization.archive import ArchiveManager, FolderStructure
from src.organization.indexer import ArchiveIndexer, SearchQuery
from src.organization.automation import OrganizationAutomation
from src.organization.pdf_merger import PDFMerger, PDFMergeAutomation
from src.organization.thumbnails import ThumbnailGenerator, ThumbnailAutomation


def cmd_search(args):
    """Search archived documents."""
    indexer = ArchiveIndexer()
    
    try:
        # Build search query
        query = SearchQuery(
            owner=args.owner,
            year=args.year,
            doc_type=args.doc_type,
            batch_id=args.batch,
            qc_status=args.qc_status,
            text_search=args.text,
            limit=args.limit,
            offset=args.offset
        )
        
        # Execute search
        results = indexer.search(query)
        
        if not results:
            print("No documents found")
            return
        
        # Display results
        print(f"\nFound {len(results)} document(s):\n")
        
        for doc in results:
            print(f"Page ID: {doc['page_id']}")
            print(f"  Owner: {doc['owner']}")
            print(f"  Year: {doc['year']}")
            print(f"  Type: {doc['doc_type']}")
            print(f"  Batch: {doc['batch_id']}")
            print(f"  QC Status: {doc['qc_status']}")
            print(f"  Folder: {doc['folder_path']}")
            print(f"  Archived: {doc['archived_at']}")
            
            # Show files
            files = json.loads(doc['files'])
            print(f"  Files: {', '.join(files.keys())}")
            print()
        
        print(f"Total: {len(results)} document(s)")
    
    finally:
        indexer.close()


def cmd_retrieve(args):
    """Retrieve document details."""
    manager = ArchiveManager()
    indexer = ArchiveIndexer()
    
    try:
        # Search by page ID
        query = SearchQuery(limit=1)
        results = indexer.search(query)
        
        # Filter by page_id (since SearchQuery doesn't have it)
        result = None
        for r in manager.search_documents():
            if r.page_id == args.page_id:
                result = r
                break
        
        if not result:
            print(f"Document not found: {args.page_id}")
            return
        
        # Display full details
        print(f"\n=== Document: {result.page_id} ===\n")
        print(f"Folder Structure:")
        print(f"  Owner: {result.folder_structure.owner}")
        print(f"  Year: {result.folder_structure.year}")
        print(f"  Type: {result.folder_structure.doc_type}")
        print(f"  Batch: {result.folder_structure.batch_id}")
        print(f"  Path: {result.folder_structure}")
        print()
        
        print(f"Archive Details:")
        print(f"  Archived At: {result.archived_at}")
        print(f"  QC Status: {result.qc_status}")
        print()
        
        print(f"Files:")
        for file_type, file_path in result.files.items():
            print(f"  {file_type}: {file_path}")
        print()
        
        if args.show_metadata:
            print(f"Metadata:")
            print(json.dumps(result.metadata, indent=2))
            print()
        
        # Show file contents if requested
        if args.show_content:
            for file_type, file_path in result.files.items():
                if file_type in ['image', 'pdf']:
                    continue  # Skip binary files
                
                print(f"\n--- {file_type.upper()} Content ---")
                try:
                    content = Path(file_path).read_text(encoding='utf-8')
                    print(content[:1000])  # First 1000 chars
                    if len(content) > 1000:
                        print("\n... (truncated)")
                except Exception as e:
                    print(f"Error reading file: {e}")
    
    finally:
        indexer.close()


def cmd_stats(args):
    """Display archive statistics."""
    manager = ArchiveManager()
    indexer = ArchiveIndexer()
    
    try:
        # Get statistics
        manager_stats = manager.get_statistics()
        indexer_stats = indexer.get_statistics()
        
        print("\n=== Archive Statistics ===\n")
        
        print(f"Total Documents: {manager_stats['total_documents']}")
        print()
        
        print("By Owner:")
        for owner, count in manager_stats['by_owner'].items():
            print(f"  {owner}: {count}")
        print()
        
        print("By Year:")
        for year, count in sorted(manager_stats['by_year'].items()):
            print(f"  {year}: {count}")
        print()
        
        print("By Document Type:")
        for doc_type, count in manager_stats['by_doc_type'].items():
            print(f"  {doc_type}: {count}")
        print()
        
        print("By QC Status:")
        for status, count in manager_stats['by_qc_status'].items():
            print(f"  {status}: {count}")
        print()
        
        print("\n=== Index Statistics ===\n")
        print(f"Total Indexed: {indexer_stats['total_documents']}")
        print()
        
        print("By Owner:")
        for owner, count in indexer_stats['by_owner'].items():
            print(f"  {owner}: {count}")
        print()
        
        print("By Document Type:")
        for doc_type, count in indexer_stats['by_doc_type'].items():
            print(f"  {doc_type}: {count}")
        print()
    
    finally:
        indexer.close()


def cmd_integrity(args):
    """Check archive integrity."""
    manager = ArchiveManager()
    
    issues = manager.verify_integrity()
    
    if not issues:
        print("✓ Archive integrity check passed")
        return
    
    print(f"⚠ Found {len(issues)} issue(s):\n")
    
    for issue in issues:
        print(f"- {issue}")


def cmd_reindex(args):
    """Rebuild search index."""
    manager = ArchiveManager()
    indexer = ArchiveIndexer()
    
    try:
        print("Rebuilding index...")
        
        # Clear existing index
        db_path = Path("data/organization/archive.db")
        if db_path.exists() and args.full:
            db_path.unlink()
            indexer = ArchiveIndexer()  # Recreate
            print("Cleared existing index")
        
        # Index all documents
        documents = manager.search_documents()
        count = 0
        
        for doc in documents:
            try:
                # Load OCR text if available
                ocr_text = None
                if 'ocr' in doc.files:
                    ocr_path = Path(doc.files['ocr'])
                    if ocr_path.exists():
                        ocr_text = ocr_path.read_text(encoding='utf-8')
                
                # Index document
                indexer.index_document(
                    page_id=doc.page_id,
                    owner=doc.folder_structure.owner,
                    year=doc.folder_structure.year,
                    doc_type=doc.folder_structure.doc_type,
                    batch_id=doc.folder_structure.batch_id,
                    folder_path=str(doc.get_archive_path()),
                    archived_at=doc.archived_at,
                    qc_status=doc.qc_status,
                    metadata=doc.metadata,
                    files={k: str(v) for k, v in doc.files.items()},
                    ocr_text=ocr_text
                )
                
                count += 1
                if count % 10 == 0:
                    print(f"  Indexed {count} documents...")
            
            except Exception as e:
                print(f"  Error indexing {doc.page_id}: {e}")
        
        print(f"\n✓ Reindexed {count} document(s)")
    
    finally:
        indexer.close()


def cmd_auto(args):
    """Start automation daemon."""
    automation = OrganizationAutomation(
        auto_archive_approved=not args.no_approved,
        auto_archive_failed=args.include_failed
    )
    
    if args.once:
        # Run once
        count = automation.scan_and_process()
        print(f"Processed {count} document(s)")
        
        # Show stats
        stats = automation.get_statistics()
        print(f"Total processed: {stats['total_processed']}")
    else:
        # Run as daemon
        automation.run_daemon(interval_seconds=args.interval)


def cmd_merge(args):
    """Merge pages into PDF/A."""
    try:
        merger = PDFMerger()
    except ImportError as e:
        print(f"Error: {e}")
        print("\nInstall required packages:")
        print("  pip install Pillow img2pdf pypdf")
        return
    
    if args.batch_id:
        # Merge specific batch
        try:
            pdf_path = merger.merge_batch(
                owner=args.owner,
                year=args.year,
                doc_type=args.doc_type,
                batch_id=args.batch_id
            )
            print(f"\n✓ Created: {pdf_path}")
        except Exception as e:
            print(f"Error: {e}")
    
    else:
        # Merge all matching batches
        pdfs = merger.merge_all_batches(
            owner=args.owner,
            year=args.year,
            doc_type=args.doc_type
        )
        
        if pdfs:
            print(f"\nCreated {len(pdfs)} PDF(s):")
            for pdf in pdfs:
                print(f"  {pdf}")


def cmd_merge_auto(args):
    """Start PDF merge automation."""
    try:
        automation = PDFMergeAutomation(
            auto_merge=True,
            min_pages=args.min_pages
        )
    except ImportError as e:
        print(f"Error: {e}")
        print("\nInstall required packages:")
        print("  pip install Pillow img2pdf pypdf")
        return
    
    if args.once:
        # Run once
        count = automation.scan_and_merge()
        print(f"\nMerged {count} batch(es)")
        
        # Show stats
        stats = automation.get_statistics()
        print(f"Total merged: {stats['total_merged']}")
    else:
        # Run as daemon
        print("PDF merge automation not yet implemented in daemon mode")
        print("Use --once for now")


def cmd_batch_info(args):
    """Show batch information."""
    try:
        merger = PDFMerger()
    except ImportError as e:
        print(f"Error: {e}")
        return
    
    try:
        info = merger.get_batch_info(
            owner=args.owner,
            year=args.year,
            doc_type=args.doc_type,
            batch_id=args.batch_id
        )
        
        print(f"\n=== Batch Info ===")
        print(f"Folder: {info['batch_folder']}")
        print(f"Pages: {info['page_count']}")
        print(f"Size: {info['total_size_mb']:.2f} MB")
        print(f"Has PDF: {'Yes' if info['has_pdf'] else 'No'}")
        
        if info['has_pdf']:
            print(f"Existing PDFs:")
            for pdf in info['existing_pdfs']:
                print(f"  {pdf}")
        
        print(f"\nPage IDs:")
        for page_id in info['pages']:
            print(f"  {page_id}")
    
    except Exception as e:
        print(f"Error: {e}")


def cmd_metadata(args):
    """View batch metadata (JSON/CSV)."""
    batch_folder = Path("data/archive") / args.owner / args.year / args.doc_type / args.batch_id
    
    if not batch_folder.exists():
        print(f"Error: Batch folder not found: {batch_folder}")
        return
    
    # Find metadata files
    json_files = list(batch_folder.glob("*_metadata.json"))
    csv_files = list(batch_folder.glob("*_pages.csv"))
    
    if not json_files and not csv_files:
        print("No metadata files found in batch folder")
        print("\nRun merge to generate metadata:")
        print(f"  python archive_cli.py merge --owner {args.owner} --year {args.year} --doc-type {args.doc_type} --batch-id {args.batch_id}")
        return
    
    # Display JSON metadata
    if json_files:
        json_file = json_files[0]
        print(f"\n=== Metadata: {json_file.name} ===\n")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Display batch info
            batch = metadata.get('batch', {})
            print(f"Owner: {batch.get('owner')}")
            print(f"Year: {batch.get('year')}")
            print(f"Document Type: {batch.get('doc_type')}")
            print(f"Batch ID: {batch.get('batch_id')}")
            print(f"Created: {batch.get('created_at')}")
            print(f"Pages: {batch.get('page_count')}")
            print(f"PDF: {batch.get('pdf_file')}")
            
            # Display summary
            summary = metadata.get('summary', {})
            print(f"\n=== Summary ===")
            print(f"Total Pages: {summary.get('total_pages')}")
            print(f"QC Passed: {summary.get('qc_passed')}")
            print(f"QC Failed: {summary.get('qc_failed')}")
            print(f"QC Pending: {summary.get('qc_pending')}")
            
            # Display extracted fields
            fields_extracted = summary.get('fields_extracted', {})
            if fields_extracted:
                print(f"\n=== Extracted Fields ===")
                for field_name, count in sorted(fields_extracted.items()):
                    print(f"  {field_name}: {count} page(s)")
            
            # Show page details if requested
            if args.show_pages:
                print(f"\n=== Pages ===")
                for page in metadata.get('pages', []):
                    print(f"\n  {page['page_id']}:")
                    print(f"    Image: {page['image_file']}")
                    print(f"    QC Status: {page['qc_status']}")
                    print(f"    Has OCR: {page['has_ocr']}")
                    if page['fields']:
                        print(f"    Fields:")
                        for field_name, field_value in page['fields'].items():
                            print(f"      {field_name}: {field_value}")
        
        except Exception as e:
            print(f"Error reading JSON: {e}")
    
    # Display CSV info
    if csv_files:
        csv_file = csv_files[0]
        print(f"\n=== CSV Inventory: {csv_file.name} ===")
        print(f"Location: {csv_file}")
        
        if args.show_csv:
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    if rows:
                        # Show headers
                        print(f"\nColumns: {', '.join(reader.fieldnames or [])}")
                        print(f"Rows: {len(rows)}")
                        
                        # Show first few rows
                        print(f"\nFirst {min(5, len(rows))} row(s):")
                        for i, row in enumerate(rows[:5], 1):
                            print(f"\n  Row {i}:")
                            for key, value in row.items():
                                if value:  # Only show non-empty values
                                    print(f"    {key}: {value}")
            except Exception as e:
                print(f"Error reading CSV: {e}")


def cmd_thumbnails(args):
    """Generate thumbnails for batch."""
    try:
        generator = ThumbnailGenerator()
    except ImportError as e:
        print(f"Error: {e}")
        return
    
    try:
        stats = generator.generate_batch_thumbnails(
            owner=args.owner,
            year=args.year,
            doc_type=args.doc_type,
            batch_id=args.batch_id,
            force_regenerate=args.force
        )
        
        print(f"\n=== Thumbnail Generation ===")
        print(f"Total Images: {stats['total_images']}")
        print(f"Generated: {stats['generated']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Failed: {stats['failed']}")
        
        if stats['thumbnails']:
            print(f"\nGenerated sizes: icon, small, medium, large")
            print(f"Cache location: data/archive/.thumbnails/")
    
    except Exception as e:
        print(f"Error: {e}")


def cmd_thumbnails_auto(args):
    """Auto-generate thumbnails for all batches."""
    try:
        automation = ThumbnailAutomation(auto_generate=True)
    except ImportError as e:
        print(f"Error: {e}")
        return
    
    if args.once:
        count = automation.scan_and_generate()
        print(f"\nProcessed {count} batch(es)")
        
        # Show stats
        stats = automation.get_statistics()
        print(f"Total processed: {stats['total_processed']}")
        print(f"Cache: {stats['cache_stats']['thumbnail_count']} thumbnails, {stats['cache_stats']['total_size_mb']:.2f} MB")
    else:
        print("Thumbnail automation daemon not yet implemented")
        print("Use --once for now")


def cmd_thumbnails_clear(args):
    """Clear thumbnail cache."""
    try:
        generator = ThumbnailGenerator()
    except ImportError as e:
        print(f"Error: {e}")
        return
    
    if args.all:
        confirm = input("Clear entire thumbnail cache? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled")
            return
        
        count = generator.clear_cache()
        print(f"Cleared {count} file(s)")
    else:
        count = generator.clear_cache(
            owner=args.owner,
            year=args.year,
            doc_type=args.doc_type
        )
        print(f"Cleared {count} file(s)")


def cmd_thumbnails_stats(args):
    """Show thumbnail cache statistics."""
    try:
        generator = ThumbnailGenerator()
    except ImportError as e:
        print(f"Error: {e}")
        return
    
    stats = generator.get_cache_stats()
    
    print(f"\n=== Thumbnail Cache Statistics ===")
    print(f"Thumbnails: {stats['thumbnail_count']}")
    print(f"Manifests: {stats['manifest_count']}")
    print(f"Total Size: {stats['total_size_mb']:.2f} MB")
    print(f"Cache Directory: {stats['cache_dir']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Archive Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search documents')
    search_parser.add_argument('--owner', help='Filter by owner')
    search_parser.add_argument('--year', help='Filter by year')
    search_parser.add_argument('--doc-type', help='Filter by document type')
    search_parser.add_argument('--batch', help='Filter by batch ID')
    search_parser.add_argument('--qc-status', choices=['pass', 'fail'], help='Filter by QC status')
    search_parser.add_argument('--text', help='Full-text search')
    search_parser.add_argument('--limit', type=int, default=50, help='Limit results')
    search_parser.add_argument('--offset', type=int, default=0, help='Results offset')
    search_parser.set_defaults(func=cmd_search)
    
    # Retrieve command
    retrieve_parser = subparsers.add_parser('retrieve', help='Retrieve document details')
    retrieve_parser.add_argument('page_id', help='Page ID to retrieve')
    retrieve_parser.add_argument('--show-metadata', action='store_true', help='Show full metadata')
    retrieve_parser.add_argument('--show-content', action='store_true', help='Show file contents')
    retrieve_parser.set_defaults(func=cmd_retrieve)
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='View statistics')
    stats_parser.set_defaults(func=cmd_stats)
    
    # Integrity command
    integrity_parser = subparsers.add_parser('integrity', help='Check integrity')
    integrity_parser.set_defaults(func=cmd_integrity)
    
    # Reindex command
    reindex_parser = subparsers.add_parser('reindex', help='Rebuild index')
    reindex_parser.add_argument('--full', action='store_true', help='Full reindex (clear existing)')
    reindex_parser.set_defaults(func=cmd_reindex)
    
    # Auto command
    auto_parser = subparsers.add_parser('auto', help='Start automation')
    auto_parser.add_argument('--once', action='store_true', help='Run once instead of daemon')
    auto_parser.add_argument('--interval', type=int, default=30, help='Polling interval (seconds)')
    auto_parser.add_argument('--no-approved', action='store_true', help='Disable auto-archive of approved docs')
    auto_parser.add_argument('--include-failed', action='store_true', help='Also archive failed docs')
    auto_parser.set_defaults(func=cmd_auto)
    
    # Merge command
    merge_parser = subparsers.add_parser('merge', help='Merge pages into PDF/A')
    merge_parser.add_argument('--owner', help='Filter by owner')
    merge_parser.add_argument('--year', help='Filter by year')
    merge_parser.add_argument('--doc-type', help='Filter by document type')
    merge_parser.add_argument('--batch-id', help='Specific batch ID to merge')
    merge_parser.set_defaults(func=cmd_merge)
    
    # Merge-auto command
    merge_auto_parser = subparsers.add_parser('merge-auto', help='Auto-merge batches')
    merge_auto_parser.add_argument('--once', action='store_true', help='Run once instead of daemon')
    merge_auto_parser.add_argument('--min-pages', type=int, default=1, help='Minimum pages to merge')
    merge_auto_parser.set_defaults(func=cmd_merge_auto)
    
    # Batch-info command
    batch_info_parser = subparsers.add_parser('batch-info', help='Show batch information')
    batch_info_parser.add_argument('owner', help='Document owner')
    batch_info_parser.add_argument('year', help='Year')
    batch_info_parser.add_argument('doc_type', help='Document type')
    batch_info_parser.add_argument('batch_id', help='Batch ID')
    batch_info_parser.set_defaults(func=cmd_batch_info)
    
    # Metadata command
    metadata_parser = subparsers.add_parser('metadata', help='View batch metadata')
    metadata_parser.add_argument('owner', help='Document owner')
    metadata_parser.add_argument('year', help='Year')
    metadata_parser.add_argument('doc_type', help='Document type')
    metadata_parser.add_argument('batch_id', help='Batch ID')
    metadata_parser.add_argument('--show-pages', action='store_true', help='Show page details')
    metadata_parser.add_argument('--show-csv', action='store_true', help='Show CSV data')
    metadata_parser.set_defaults(func=cmd_metadata)
    
    # Thumbnails command
    thumbnails_parser = subparsers.add_parser('thumbnails', help='Generate thumbnails')
    thumbnails_parser.add_argument('owner', help='Document owner')
    thumbnails_parser.add_argument('year', help='Year')
    thumbnails_parser.add_argument('doc_type', help='Document type')
    thumbnails_parser.add_argument('batch_id', help='Batch ID')
    thumbnails_parser.add_argument('--force', action='store_true', help='Force regenerate')
    thumbnails_parser.set_defaults(func=cmd_thumbnails)
    
    # Thumbnails-auto command
    thumbnails_auto_parser = subparsers.add_parser('thumbnails-auto', help='Auto-generate thumbnails')
    thumbnails_auto_parser.add_argument('--once', action='store_true', help='Run once instead of daemon')
    thumbnails_auto_parser.set_defaults(func=cmd_thumbnails_auto)
    
    # Thumbnails-clear command
    thumbnails_clear_parser = subparsers.add_parser('thumbnails-clear', help='Clear thumbnail cache')
    thumbnails_clear_parser.add_argument('--all', action='store_true', help='Clear entire cache')
    thumbnails_clear_parser.add_argument('--owner', help='Filter by owner')
    thumbnails_clear_parser.add_argument('--year', help='Filter by year')
    thumbnails_clear_parser.add_argument('--doc-type', help='Filter by document type')
    thumbnails_clear_parser.set_defaults(func=cmd_thumbnails_clear)
    
    # Thumbnails-stats command
    thumbnails_stats_parser = subparsers.add_parser('thumbnails-stats', help='Thumbnail cache stats')
    thumbnails_stats_parser.set_defaults(func=cmd_thumbnails_stats)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    args.func(args)


if __name__ == '__main__':
    main()
