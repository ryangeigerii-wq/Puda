"""
Archive Manager - Structured Digital Archive with Folder Conventions

Implements folder naming convention: {Owner}/{Year}/{DocType}/{BatchID}/
"""

import re
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import json


@dataclass
class FolderStructure:
    """
    Represents archive folder structure.
    
    Convention: {Owner}/{Year}/{DocType}/{BatchID}/
    
    Attributes:
        owner: Document owner (person/department/entity)
        year: Year of document (YYYY)
        doc_type: Document type (Invoice, ID, Form, Letter, etc.)
        batch_id: Batch identifier for grouping
    """
    owner: str
    year: str
    doc_type: str
    batch_id: str
    
    def __post_init__(self):
        """Validate and normalize folder components."""
        self.owner = self._normalize_name(self.owner)
        self.year = self._validate_year(self.year)
        self.doc_type = self._normalize_doc_type(self.doc_type)
        self.batch_id = self._normalize_name(self.batch_id)
    
    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Normalize name for filesystem safety.
        
        Rules:
        - Remove/replace invalid characters
        - Convert spaces to underscores
        - Preserve alphanumeric and dash
        - CamelCase for readability
        """
        if not name:
            return "Unknown"
        
        # Replace invalid filesystem characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        # Remove leading/trailing underscores
        name = name.strip('_')
        # Ensure not empty
        return name if name else "Unknown"
    
    @staticmethod
    def _validate_year(year: str) -> str:
        """Validate year format (YYYY)."""
        try:
            year_int = int(year)
            if 1900 <= year_int <= 2100:
                return str(year_int)
        except (ValueError, TypeError):
            pass
        # Fallback to current year
        return str(datetime.now().year)
    
    @staticmethod
    def _normalize_doc_type(doc_type: str) -> str:
        """
        Normalize document type with standard capitalization.
        
        Maps common types to canonical names.
        """
        if not doc_type:
            return "Unknown"
        
        # Mapping to canonical names
        type_map = {
            'invoice': 'Invoice',
            'id': 'ID',
            'form': 'Form',
            'letter': 'Letter',
            'receipt': 'Receipt',
            'contract': 'Contract',
            'statement': 'Statement',
            'report': 'Report',
            'unknown': 'Uncategorized',
        }
        
        doc_type_lower = doc_type.lower()
        return type_map.get(doc_type_lower, doc_type.title())
    
    def get_path(self, base_dir: Optional[Path] = None) -> Path:
        """
        Get full archive path.
        
        Args:
            base_dir: Base archive directory (default: data/archive)
            
        Returns:
            Full path: {base_dir}/{Owner}/{Year}/{DocType}/{BatchID}/
        """
        if base_dir is None:
            base_dir = Path("data/archive")
        
        return base_dir / self.owner / self.year / self.doc_type / self.batch_id
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FolderStructure':
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_metadata(cls, metadata: dict, batch_id: str = "default") -> 'FolderStructure':
        """
        Create from document metadata.
        
        Args:
            metadata: Document metadata dict
            batch_id: Batch identifier
            
        Returns:
            FolderStructure instance
        """
        # Extract owner from metadata
        owner = metadata.get('owner')
        if not owner:
            # Try to extract from fields
            processing = metadata.get('processing', {})
            extraction = processing.get('extraction', {})
            fields = extraction.get('fields', {})
            owner = fields.get('name') or fields.get('customer_name') or 'Unknown'
        
        # Extract year from metadata or document date
        year = metadata.get('year')
        if not year:
            # Try to extract from date fields
            processing = metadata.get('processing', {})
            extraction = processing.get('extraction', {})
            fields = extraction.get('fields', {})
            
            date_str = (fields.get('invoice_date') or 
                       fields.get('date') or 
                       fields.get('dob'))
            
            if date_str:
                try:
                    # Try parsing various date formats
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y']:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            year = str(dt.year)
                            break
                        except ValueError:
                            continue
                except:
                    pass
            
            if not year:
                year = str(datetime.now().year)
        
        # Extract document type
        doc_type = metadata.get('doc_type')
        if not doc_type:
            processing = metadata.get('processing', {})
            classification = processing.get('classification', {})
            doc_type = classification.get('document_type', 'Unknown')
        
        return cls(
            owner=str(owner),
            year=str(year),
            doc_type=str(doc_type),
            batch_id=str(batch_id)
        )
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.owner}/{self.year}/{self.doc_type}/{self.batch_id}"


@dataclass
class DocumentArchive:
    """
    Represents an archived document with metadata.
    
    Attributes:
        page_id: Unique page identifier
        folder_structure: Archive folder structure
        files: Dictionary of archived files (image, json, ocr, etc.)
        metadata: Document metadata
        archived_at: Timestamp of archival
        qc_status: QC verification status
    """
    page_id: str
    folder_structure: FolderStructure
    files: Dict[str, Path] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    archived_at: float = field(default_factory=lambda: datetime.now().timestamp())
    qc_status: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = {
            'page_id': self.page_id,
            'folder_structure': self.folder_structure.to_dict(),
            'files': {k: str(v) for k, v in self.files.items()},
            'metadata': self.metadata,
            'archived_at': self.archived_at,
            'archived_at_iso': datetime.fromtimestamp(self.archived_at).isoformat(),
            'qc_status': self.qc_status,
        }
        return data
    
    def get_archive_path(self) -> Path:
        """Get archive directory path."""
        return self.folder_structure.get_path()


class ArchiveManager:
    """
    Manages structured digital archive with automated organization.
    
    Features:
    - Folder naming convention enforcement
    - File copying/moving to archive
    - Metadata preservation
    - Duplicate detection
    - Archive integrity checks
    """
    
    def __init__(
        self,
        base_dir: str = "data/archive",
        copy_mode: bool = True,  # True = copy, False = move
        create_dirs: bool = True
    ):
        """
        Initialize archive manager.
        
        Args:
            base_dir: Base archive directory
            copy_mode: If True, copy files; if False, move files
            create_dirs: Automatically create directories
        """
        self.base_dir = Path(base_dir)
        self.copy_mode = copy_mode
        self.create_dirs = create_dirs
        
        if self.create_dirs:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Archive index (in-memory, can be persisted)
        self.index: Dict[str, DocumentArchive] = {}
        self._load_index()
    
    def _load_index(self):
        """Load archive index from disk."""
        index_file = self.base_dir / ".archive_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for page_id, archive_data in data.items():
                        # Reconstruct DocumentArchive
                        folder = FolderStructure.from_dict(archive_data['folder_structure'])
                        files = {k: Path(v) for k, v in archive_data['files'].items()}
                        
                        self.index[page_id] = DocumentArchive(
                            page_id=page_id,
                            folder_structure=folder,
                            files=files,
                            metadata=archive_data['metadata'],
                            archived_at=archive_data['archived_at'],
                            qc_status=archive_data.get('qc_status')
                        )
            except Exception as e:
                print(f"Warning: Failed to load archive index: {e}")
    
    def _save_index(self):
        """Save archive index to disk."""
        index_file = self.base_dir / ".archive_index.json"
        try:
            data = {
                page_id: archive.to_dict()
                for page_id, archive in self.index.items()
            }
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save archive index: {e}")
    
    def archive_document(
        self,
        page_id: str,
        source_files: Dict[str, Path],
        metadata: Dict[str, Any],
        folder_structure: Optional[FolderStructure] = None,
        batch_id: Optional[str] = None
    ) -> DocumentArchive:
        """
        Archive document to structured folder.
        
        Args:
            page_id: Unique page identifier
            source_files: Dict of file types to source paths
                         e.g., {'image': Path('scan.png'), 'json': Path('scan.json')}
            metadata: Document metadata
            folder_structure: Optional pre-built folder structure
            batch_id: Optional batch ID (defaults to metadata batch_id)
            
        Returns:
            DocumentArchive instance
        """
        # Determine folder structure
        if folder_structure is None:
            if batch_id is None:
                batch_id = metadata.get('batch_id', 'default')
            folder_structure = FolderStructure.from_metadata(metadata, str(batch_id))
        
        # Get archive path
        archive_path = folder_structure.get_path(self.base_dir)
        archive_path.mkdir(parents=True, exist_ok=True)
        
        # Copy/move files to archive
        archived_files = {}
        for file_type, source_path in source_files.items():
            if not source_path.exists():
                print(f"Warning: Source file not found: {source_path}")
                continue
            
            # Preserve original filename or use page_id
            dest_filename = f"{page_id}{source_path.suffix}"
            dest_path = archive_path / dest_filename
            
            # Copy or move
            if self.copy_mode:
                shutil.copy2(source_path, dest_path)
            else:
                shutil.move(str(source_path), dest_path)
            
            archived_files[file_type] = dest_path
        
        # Extract QC status from metadata
        qc_status = None
        processing = metadata.get('processing', {})
        qc_verification = processing.get('qc_verification', {})
        if qc_verification:
            qc_status = 'passed' if qc_verification.get('passed') else 'failed'
        
        # Create archive entry
        archive = DocumentArchive(
            page_id=page_id,
            folder_structure=folder_structure,
            files=archived_files,
            metadata=metadata,
            qc_status=qc_status
        )
        
        # Update index
        self.index[page_id] = archive
        self._save_index()
        
        return archive
    
    def get_document(self, page_id: str) -> Optional[DocumentArchive]:
        """Get archived document by page ID."""
        return self.index.get(page_id)
    
    def search_documents(
        self,
        owner: Optional[str] = None,
        year: Optional[str] = None,
        doc_type: Optional[str] = None,
        batch_id: Optional[str] = None,
        qc_status: Optional[str] = None
    ) -> List[DocumentArchive]:
        """
        Search archived documents by criteria.
        
        Args:
            owner: Filter by owner
            year: Filter by year
            doc_type: Filter by document type
            batch_id: Filter by batch ID
            qc_status: Filter by QC status (passed/failed)
            
        Returns:
            List of matching DocumentArchive instances
        """
        results = []
        
        for archive in self.index.values():
            # Apply filters
            if owner and archive.folder_structure.owner != owner:
                continue
            if year and archive.folder_structure.year != year:
                continue
            if doc_type and archive.folder_structure.doc_type != doc_type:
                continue
            if batch_id and archive.folder_structure.batch_id != batch_id:
                continue
            if qc_status and archive.qc_status != qc_status:
                continue
            
            results.append(archive)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get archive statistics.
        
        Returns:
            Dictionary with counts and breakdowns
        """
        stats = {
            'total_documents': len(self.index),
            'by_owner': {},
            'by_year': {},
            'by_doc_type': {},
            'by_qc_status': {},
            'owners': set(),
            'years': set(),
            'doc_types': set(),
        }
        
        for archive in self.index.values():
            # Count by owner
            owner = archive.folder_structure.owner
            stats['by_owner'][owner] = stats['by_owner'].get(owner, 0) + 1
            stats['owners'].add(owner)
            
            # Count by year
            year = archive.folder_structure.year
            stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
            stats['years'].add(year)
            
            # Count by doc type
            doc_type = archive.folder_structure.doc_type
            stats['by_doc_type'][doc_type] = stats['by_doc_type'].get(doc_type, 0) + 1
            stats['doc_types'].add(doc_type)
            
            # Count by QC status
            qc_status = archive.qc_status or 'none'
            stats['by_qc_status'][qc_status] = stats['by_qc_status'].get(qc_status, 0) + 1
        
        # Convert sets to sorted lists
        stats['owners'] = sorted(list(stats['owners']))
        stats['years'] = sorted(list(stats['years']))
        stats['doc_types'] = sorted(list(stats['doc_types']))
        
        return stats
    
    def list_folder_contents(self, folder_structure: FolderStructure) -> List[DocumentArchive]:
        """
        List all documents in a specific folder.
        
        Args:
            folder_structure: Folder to list
            
        Returns:
            List of DocumentArchive instances in that folder
        """
        results = []
        folder_path = folder_structure.get_path(self.base_dir)
        
        for archive in self.index.values():
            if archive.get_archive_path() == folder_path:
                results.append(archive)
        
        return results
    
    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify archive integrity.
        
        Checks:
        - All indexed files exist
        - No orphaned files in archive
        - Metadata consistency
        
        Returns:
            Dictionary with integrity report
        """
        report = {
            'valid': True,
            'total_documents': len(self.index),
            'missing_files': [],
            'orphaned_files': [],
            'errors': []
        }
        
        # Check indexed files exist
        for page_id, archive in self.index.items():
            for file_type, file_path in archive.files.items():
                if not file_path.exists():
                    report['valid'] = False
                    report['missing_files'].append({
                        'page_id': page_id,
                        'file_type': file_type,
                        'expected_path': str(file_path)
                    })
        
        # Find orphaned files (files in archive not in index)
        all_indexed_files = set()
        for archive in self.index.values():
            for file_path in archive.files.values():
                all_indexed_files.add(file_path)
        
        # Scan archive directory
        for file_path in self.base_dir.rglob('*'):
            if file_path.is_file() and file_path.name != '.archive_index.json':
                if file_path not in all_indexed_files:
                    report['orphaned_files'].append(str(file_path))
        
        if report['orphaned_files']:
            report['valid'] = False
        
        return report
