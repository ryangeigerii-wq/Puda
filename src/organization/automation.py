"""
Organization Automation - Automatic Document Filing

Automatically organizes documents after QC approval.
Monitors QC results and triggers archival to structured folders.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

from .archive import ArchiveManager, FolderStructure
from .indexer import ArchiveIndexer


class OrganizationAutomation:
    """
    Automatic document organization after QC approval.
    
    Features:
    - Monitor QC results directory
    - Auto-archive approved documents
    - Conflict resolution (duplicate detection)
    - Error handling and retry logic
    """
    
    def __init__(
        self,
        archive_manager: Optional[ArchiveManager] = None,
        indexer: Optional[ArchiveIndexer] = None,
        qc_results_dir: str = "data/qc_results",
        auto_archive_approved: bool = True,
        auto_archive_failed: bool = False
    ):
        """
        Initialize organization automation.
        
        Args:
            archive_manager: Archive manager instance
            indexer: Archive indexer instance
            qc_results_dir: Directory containing QC result files
            auto_archive_approved: Auto-archive QC approved documents
            auto_archive_failed: Auto-archive QC failed documents
        """
        self.archive_manager = archive_manager or ArchiveManager()
        self.indexer = indexer or ArchiveIndexer()
        self.qc_results_dir = Path(qc_results_dir)
        self.auto_archive_approved = auto_archive_approved
        self.auto_archive_failed = auto_archive_failed
        
        # Track processed QC results
        self.processed_results: set = set()
        self._load_processed_results()
    
    def _load_processed_results(self):
        """Load list of already-processed QC results."""
        state_file = self.qc_results_dir / ".processed_qc_results.json"
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    self.processed_results = set(json.load(f))
            except:
                pass
    
    def _save_processed_results(self):
        """Save list of processed QC results."""
        state_file = self.qc_results_dir / ".processed_qc_results.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_results), f)
        except Exception as e:
            print(f"Warning: Failed to save processed results: {e}")
    
    def process_qc_result(self, qc_result_file: Path) -> bool:
        """
        Process a single QC result file and archive if approved.
        
        Args:
            qc_result_file: Path to QC result JSON file
            
        Returns:
            True if processed successfully
        """
        # Skip if already processed
        if str(qc_result_file) in self.processed_results:
            return False
        
        try:
            # Load QC result
            with open(qc_result_file, 'r', encoding='utf-8') as f:
                qc_result = json.load(f)
            
            qc_status = qc_result.get('qc_status', {})
            passed = qc_status.get('passed', False)
            
            # Check if should archive
            should_archive = (
                (passed and self.auto_archive_approved) or
                (not passed and self.auto_archive_failed)
            )
            
            if not should_archive:
                return False
            
            # Extract information
            page_id = qc_result.get('page_id')
            if not page_id:
                print(f"Warning: No page_id in {qc_result_file}")
                return False
            
            # Build metadata from QC result
            metadata = self._build_metadata(qc_result)
            
            # Find source files
            source_files = self._find_source_files(page_id, metadata)
            if not source_files:
                print(f"Warning: No source files found for {page_id}")
                return False
            
            # Determine folder structure
            folder_structure = self._determine_folder_structure(qc_result, metadata)
            
            # Archive document
            archive = self.archive_manager.archive_document(
                page_id=page_id,
                source_files=source_files,
                metadata=metadata,
                folder_structure=folder_structure
            )
            
            # Index document
            self._index_document(archive, qc_result)
            
            # Mark as processed
            self.processed_results.add(str(qc_result_file))
            self._save_processed_results()
            
            print(f"✓ Archived: {page_id} → {folder_structure}")
            return True
        
        except Exception as e:
            print(f"Error processing {qc_result_file}: {e}")
            return False
    
    def _build_metadata(self, qc_result: dict) -> dict:
        """Build comprehensive metadata from QC result."""
        metadata = {}
        
        # Copy basic fields
        metadata['page_id'] = qc_result.get('page_id')
        metadata['task_id'] = qc_result.get('task_id')
        metadata['doc_type'] = qc_result.get('doc_type')
        
        # Add QC status
        metadata['qc_status'] = qc_result.get('qc_status', {})
        
        # Add corrected fields
        corrected_fields = qc_result.get('corrected_fields', {})
        original_fields = qc_result.get('original_fields', {})
        
        metadata['processing'] = {
            'extraction': {
                'fields': corrected_fields
            },
            'classification': {
                'document_type': qc_result.get('doc_type')
            },
            'qc_verification': qc_result.get('qc_status', {})
        }
        
        # Extract owner from fields
        metadata['owner'] = (
            corrected_fields.get('name') or
            corrected_fields.get('customer_name') or
            original_fields.get('name') or
            'Unknown'
        )
        
        # Extract year from date fields
        date_str = (
            corrected_fields.get('invoice_date') or
            corrected_fields.get('date') or
            original_fields.get('invoice_date')
        )
        if date_str:
            try:
                from datetime import datetime
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        metadata['year'] = str(dt.year)
                        break
                    except:
                        continue
            except:
                pass
        
        if 'year' not in metadata:
            from datetime import datetime
            metadata['year'] = str(datetime.now().year)
        
        return metadata
    
    def _find_source_files(self, page_id: str, metadata: dict) -> Dict[str, Path]:
        """
        Find source files for a document.
        
        Searches common locations for image, JSON, and OCR text files.
        """
        source_files = {}
        
        # Search directories
        search_dirs = [
            Path("data/scans"),
            Path("data"),
            Path("data/qc_results"),
        ]
        
        # Common file patterns
        patterns = {
            'image': [f"{page_id}.png", f"{page_id}.jpg", f"{page_id}.pdf"],
            'json': [f"{page_id}.json"],
            'ocr': [f"{page_id}_ocr.txt", f"{page_id}.txt"],
        }
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            for file_type, file_patterns in patterns.items():
                if file_type in source_files:
                    continue  # Already found
                
                for pattern in file_patterns:
                    candidate = search_dir / pattern
                    if candidate.exists():
                        source_files[file_type] = candidate
                        break
        
        return source_files
    
    def _determine_folder_structure(
        self,
        qc_result: dict,
        metadata: dict
    ) -> FolderStructure:
        """Determine folder structure from QC result and metadata."""
        # Extract components
        owner = metadata.get('owner', 'Unknown')
        year = metadata.get('year', str(time.localtime().tm_year))
        doc_type = qc_result.get('doc_type', 'Unknown')
        
        # Determine batch ID from task or use date-based
        task_id = qc_result.get('task_id', '')
        if 'batch' in task_id.lower():
            # Extract batch from task ID
            import re
            match = re.search(r'batch[_-]?(\w+)', task_id, re.IGNORECASE)
            if match:
                batch_id = f"batch_{match.group(1)}"
            else:
                batch_id = "batch_default"
        else:
            # Use date-based batch ID
            from datetime import datetime
            batch_id = f"batch_{datetime.now().strftime('%Y%m')}"
        
        return FolderStructure(
            owner=owner,
            year=year,
            doc_type=doc_type,
            batch_id=batch_id
        )
    
    def _index_document(self, archive, qc_result: dict):
        """Index archived document in database."""
        try:
            # Load OCR text if available
            ocr_text = None
            if 'ocr' in archive.files:
                ocr_path = archive.files['ocr']
                try:
                    ocr_text = Path(ocr_path).read_text(encoding='utf-8')
                except:
                    pass
            
            # Index in database
            self.indexer.index_document(
                page_id=archive.page_id,
                owner=archive.folder_structure.owner,
                year=archive.folder_structure.year,
                doc_type=archive.folder_structure.doc_type,
                batch_id=archive.folder_structure.batch_id,
                folder_path=str(archive.get_archive_path()),
                archived_at=archive.archived_at,
                qc_status=archive.qc_status,
                metadata=archive.metadata,
                files={k: str(v) for k, v in archive.files.items()},
                ocr_text=ocr_text
            )
        except Exception as e:
            print(f"Warning: Failed to index document: {e}")
    
    def scan_and_process(self) -> int:
        """
        Scan QC results directory and process new results.
        
        Returns:
            Number of documents processed
        """
        if not self.qc_results_dir.exists():
            return 0
        
        processed_count = 0
        
        # Find all QC result files
        for qc_file in self.qc_results_dir.glob("*_qc.json"):
            if self.process_qc_result(qc_file):
                processed_count += 1
        
        return processed_count
    
    def run_daemon(self, interval_seconds: int = 30):
        """
        Run as daemon, continuously monitoring and processing.
        
        Args:
            interval_seconds: Polling interval
        """
        print(f"Starting organization automation daemon (polling every {interval_seconds}s)")
        print(f"Monitoring: {self.qc_results_dir}")
        print(f"Archive: {self.archive_manager.base_dir}")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                count = self.scan_and_process()
                if count > 0:
                    print(f"Processed {count} document(s)")
                
                time.sleep(interval_seconds)
        
        except KeyboardInterrupt:
            print("\nStopping daemon")
            self.indexer.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get automation statistics."""
        return {
            'total_processed': len(self.processed_results),
            'auto_archive_approved': self.auto_archive_approved,
            'auto_archive_failed': self.auto_archive_failed,
            'archive_stats': self.archive_manager.get_statistics(),
            'index_stats': self.indexer.get_statistics()
        }
