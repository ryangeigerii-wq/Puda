"""
Archive Indexer - Fast Search and Retrieval

Provides SQLite-based indexing for quick document search and retrieval.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json


@dataclass
class SearchQuery:
    """Search query parameters."""
    owner: Optional[str] = None
    year: Optional[str] = None
    doc_type: Optional[str] = None
    batch_id: Optional[str] = None
    qc_status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    text_search: Optional[str] = None  # Full-text search in OCR
    limit: int = 100
    offset: int = 0


class ArchiveIndexer:
    """
    SQLite-based archive indexer for fast search.
    
    Features:
    - Full-text search
    - Filtered queries
    - Statistics aggregation
    - Performance optimization
    """
    
    def __init__(self, db_path: str = "data/archive_index.db"):
        """
        Initialize archive indexer.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables."""
        cursor = self.conn.cursor()
        
        # Main documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                page_id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                year TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                folder_path TEXT NOT NULL,
                archived_at REAL NOT NULL,
                qc_status TEXT,
                metadata_json TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_owner ON documents(owner)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_year ON documents(year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(doc_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_batch ON documents(batch_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_qc_status ON documents(qc_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_archived ON documents(archived_at)")
        
        # Files table (one-to-many relationship)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                FOREIGN KEY (page_id) REFERENCES documents(page_id) ON DELETE CASCADE
            )
        """)
        
        # Create index for files table
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_id ON files(page_id)")
        
        # Full-text search table for OCR text
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                page_id UNINDEXED,
                ocr_text,
                content=''
            )
        """)
        
        self.conn.commit()
    
    def index_document(
        self,
        page_id: str,
        owner: str,
        year: str,
        doc_type: str,
        batch_id: str,
        folder_path: str,
        archived_at: float,
        qc_status: Optional[str],
        metadata: Dict[str, Any],
        files: Dict[str, str],
        ocr_text: Optional[str] = None
    ):
        """
        Index a document.
        
        Args:
            page_id: Unique page identifier
            owner: Document owner
            year: Year
            doc_type: Document type
            batch_id: Batch ID
            folder_path: Archive folder path
            archived_at: Archive timestamp
            qc_status: QC status (passed/failed/none)
            metadata: Full metadata dict
            files: Dict of file types to paths
            ocr_text: OCR text for full-text search
        """
        cursor = self.conn.cursor()
        
        try:
            # Insert/update document
            cursor.execute("""
                INSERT OR REPLACE INTO documents 
                (page_id, owner, year, doc_type, batch_id, folder_path, 
                 archived_at, qc_status, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                page_id, owner, year, doc_type, batch_id, folder_path,
                archived_at, qc_status, json.dumps(metadata)
            ))
            
            # Delete old files
            cursor.execute("DELETE FROM files WHERE page_id = ?", (page_id,))
            
            # Insert files
            for file_type, file_path in files.items():
                cursor.execute("""
                    INSERT INTO files (page_id, file_type, file_path)
                    VALUES (?, ?, ?)
                """, (page_id, file_type, file_path))
            
            # Index OCR text for full-text search
            if ocr_text:
                # Delete old FTS entry
                cursor.execute("""
                    DELETE FROM documents_fts WHERE page_id = ?
                """, (page_id,))
                
                # Insert new FTS entry
                cursor.execute("""
                    INSERT INTO documents_fts (page_id, ocr_text)
                    VALUES (?, ?)
                """, (page_id, ocr_text))
            
            self.conn.commit()
        
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to index document: {e}")
    
    def search(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """
        Search documents.
        
        Args:
            query: Search query parameters
            
        Returns:
            List of document dictionaries
        """
        cursor = self.conn.cursor()
        
        # Build SQL query
        sql = "SELECT * FROM documents WHERE 1=1"
        params = []
        
        if query.owner:
            sql += " AND owner = ?"
            params.append(query.owner)
        
        if query.year:
            sql += " AND year = ?"
            params.append(query.year)
        
        if query.doc_type:
            sql += " AND doc_type = ?"
            params.append(query.doc_type)
        
        if query.batch_id:
            sql += " AND batch_id = ?"
            params.append(query.batch_id)
        
        if query.qc_status:
            sql += " AND qc_status = ?"
            params.append(query.qc_status)
        
        if query.date_from:
            sql += " AND archived_at >= ?"
            params.append(query.date_from.timestamp())
        
        if query.date_to:
            sql += " AND archived_at <= ?"
            params.append(query.date_to.timestamp())
        
        # Full-text search
        if query.text_search:
            sql = """
                SELECT d.* FROM documents d
                INNER JOIN documents_fts fts ON d.page_id = fts.page_id
                WHERE fts.ocr_text MATCH ?
            """
            params = [query.text_search] + params
            
            # Add other filters
            for i, param in enumerate(params[1:], 1):
                if i == 1 and query.owner:
                    sql += " AND d.owner = ?"
                elif i == 2 and query.year:
                    sql += " AND d.year = ?"
                # ... etc
        
        # Add ordering and pagination
        sql += " ORDER BY archived_at DESC"
        sql += f" LIMIT {query.limit} OFFSET {query.offset}"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # Convert to dictionaries
        results = []
        for row in rows:
            doc = dict(row)
            # Parse metadata JSON
            doc['metadata'] = json.loads(doc['metadata_json'])
            del doc['metadata_json']
            
            # Fetch files
            cursor.execute("""
                SELECT file_type, file_path FROM files WHERE page_id = ?
            """, (doc['page_id'],))
            doc['files'] = {
                file_row['file_type']: file_row['file_path']
                for file_row in cursor.fetchall()
            }
            
            results.append(doc)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get archive statistics.
        
        Returns:
            Dictionary with aggregated statistics
        """
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Total documents
        cursor.execute("SELECT COUNT(*) as count FROM documents")
        stats['total_documents'] = cursor.fetchone()['count']
        
        # By owner
        cursor.execute("""
            SELECT owner, COUNT(*) as count 
            FROM documents 
            GROUP BY owner 
            ORDER BY count DESC
        """)
        stats['by_owner'] = {row['owner']: row['count'] for row in cursor.fetchall()}
        
        # By year
        cursor.execute("""
            SELECT year, COUNT(*) as count 
            FROM documents 
            GROUP BY year 
            ORDER BY year DESC
        """)
        stats['by_year'] = {row['year']: row['count'] for row in cursor.fetchall()}
        
        # By doc type
        cursor.execute("""
            SELECT doc_type, COUNT(*) as count 
            FROM documents 
            GROUP BY doc_type 
            ORDER BY count DESC
        """)
        stats['by_doc_type'] = {row['doc_type']: row['count'] for row in cursor.fetchall()}
        
        # By QC status
        cursor.execute("""
            SELECT qc_status, COUNT(*) as count 
            FROM documents 
            GROUP BY qc_status
        """)
        stats['by_qc_status'] = {row['qc_status']: row['count'] for row in cursor.fetchall()}
        
        return stats
    
    def delete_document(self, page_id: str):
        """Delete document from index."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM documents WHERE page_id = ?", (page_id,))
        cursor.execute("DELETE FROM documents_fts WHERE page_id = ?", (page_id,))
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
