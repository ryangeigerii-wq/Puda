"""
Audit Logger - Document Access Audit Trail

Tracks all document access events for compliance and security monitoring.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum


class AuditAction(Enum):
    """Types of auditable actions."""
    VIEW = "view"
    DOWNLOAD = "download"
    SEARCH = "search"
    EDIT = "edit"
    DELETE = "delete"
    UPLOAD = "upload"
    SHARE = "share"
    PRINT = "print"
    EXPORT = "export"


class AuditLogger:
    """
    Audit logger for tracking document access and operations.
    
    Features:
    - Comprehensive event logging
    - User action tracking
    - IP address and metadata capture
    - Retention policy management
    - Query and reporting capabilities
    """
    
    def __init__(
        self,
        db_path: str = "data/audit_log.db",
        retention_days: int = 365
    ):
        """
        Initialize audit logger.
        
        Args:
            db_path: Path to SQLite database
            retention_days: Days to retain audit logs
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables."""
        cursor = self.conn.cursor()
        
        # Audit events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT DEFAULT 'document',
                resource_id TEXT NOT NULL,
                allowed INTEGER NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                session_id TEXT,
                metadata TEXT,
                created_at REAL NOT NULL
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
            ON audit_events(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_user 
            ON audit_events(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_resource 
            ON audit_events(resource_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_action 
            ON audit_events(action)
        """)
        
        self.conn.commit()
    
    def log_access(
        self,
        user_id: str,
        username: str,
        action: str,
        document_id: str,
        allowed: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log document access event.
        
        Args:
            user_id: User ID
            username: Username
            action: Action performed (view, download, etc.)
            document_id: Document/page ID
            allowed: Whether access was allowed
            ip_address: Client IP address
            user_agent: Client user agent
            session_id: Session ID
            metadata: Additional metadata
            
        Returns:
            Event ID
        """
        timestamp = datetime.utcnow().timestamp()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_events (
                timestamp, user_id, username, action, resource_type,
                resource_id, allowed, ip_address, user_agent,
                session_id, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            user_id,
            username,
            action,
            'document',
            document_id,
            int(allowed),
            ip_address,
            user_agent,
            session_id,
            json.dumps(metadata) if metadata else None,
            timestamp
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def log_search(
        self,
        user_id: str,
        username: str,
        search_query: str,
        results_count: int,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log search operation.
        
        Args:
            user_id: User ID
            username: Username
            search_query: Search query string
            results_count: Number of results returned
            ip_address: Client IP address
            metadata: Additional metadata
            
        Returns:
            Event ID
        """
        if metadata is None:
            metadata = {}
        
        metadata['search_query'] = search_query
        metadata['results_count'] = results_count
        
        return self.log_access(
            user_id=user_id,
            username=username,
            action=AuditAction.SEARCH.value,
            document_id='search',
            allowed=True,
            ip_address=ip_address,
            metadata=metadata
        )
    
    def get_user_activity(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get user activity history.
        
        Args:
            user_id: User ID
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results
            
        Returns:
            List of audit events
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM audit_events WHERE user_id = ?"
        params = [user_id]
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.timestamp())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.timestamp())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            if event['metadata']:
                event['metadata'] = json.loads(event['metadata'])
            events.append(event)
        
        return events
    
    def get_document_access_history(
        self,
        document_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get document access history.
        
        Args:
            document_id: Document/page ID
            limit: Maximum results
            
        Returns:
            List of audit events for document
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM audit_events 
            WHERE resource_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (document_id, limit))
        
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            if event['metadata']:
                event['metadata'] = json.loads(event['metadata'])
            events.append(event)
        
        return events
    
    def get_recent_events(
        self,
        hours: int = 24,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent audit events.
        
        Args:
            hours: Hours to look back
            action: Filter by action type
            limit: Maximum results
            
        Returns:
            List of recent audit events
        """
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).timestamp()
        
        cursor = self.conn.cursor()
        
        if action:
            cursor.execute("""
                SELECT * FROM audit_events 
                WHERE timestamp >= ? AND action = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (cutoff, action, limit))
        else:
            cursor.execute("""
                SELECT * FROM audit_events 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (cutoff, limit))
        
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            if event['metadata']:
                event['metadata'] = json.loads(event['metadata'])
            events.append(event)
        
        return events
    
    def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit statistics.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Dictionary with statistics
        """
        cursor = self.conn.cursor()
        
        query_filter = ""
        params = []
        
        if start_date:
            query_filter += " WHERE timestamp >= ?"
            params.append(start_date.timestamp())
            if end_date:
                query_filter += " AND timestamp <= ?"
                params.append(end_date.timestamp())
        elif end_date:
            query_filter += " WHERE timestamp <= ?"
            params.append(end_date.timestamp())
        
        # Total events
        cursor.execute(f"SELECT COUNT(*) as count FROM audit_events{query_filter}", params)
        total_events = cursor.fetchone()['count']
        
        # Events by action
        cursor.execute(f"""
            SELECT action, COUNT(*) as count 
            FROM audit_events{query_filter}
            GROUP BY action
        """, params)
        by_action = {row['action']: row['count'] for row in cursor.fetchall()}
        
        # Events by user
        cursor.execute(f"""
            SELECT username, COUNT(*) as count 
            FROM audit_events{query_filter}
            GROUP BY username
            ORDER BY count DESC
            LIMIT 10
        """, params)
        top_users = {row['username']: row['count'] for row in cursor.fetchall()}
        
        # Access denied events
        cursor.execute(f"""
            SELECT COUNT(*) as count 
            FROM audit_events 
            WHERE allowed = 0{' AND ' + query_filter[7:] if query_filter else ''}
        """, params)
        denied_count = cursor.fetchone()['count']
        
        # Most accessed documents
        cursor.execute(f"""
            SELECT resource_id, COUNT(*) as count 
            FROM audit_events{query_filter}
            GROUP BY resource_id
            ORDER BY count DESC
            LIMIT 10
        """, params)
        top_documents = {row['resource_id']: row['count'] for row in cursor.fetchall()}
        
        return {
            'total_events': total_events,
            'by_action': by_action,
            'top_users': top_users,
            'denied_count': denied_count,
            'denied_percentage': (denied_count / total_events * 100) if total_events > 0 else 0,
            'top_documents': top_documents
        }
    
    def cleanup_old_events(self) -> int:
        """
        Remove events older than retention period.
        
        Returns:
            Number of events deleted
        """
        cutoff = (datetime.utcnow() - timedelta(days=self.retention_days)).timestamp()
        
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM audit_events WHERE timestamp < ?", (cutoff,))
        deleted = cursor.rowcount
        self.conn.commit()
        
        return deleted
    
    def export_events(
        self,
        output_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        """
        Export audit events to JSON file.
        
        Args:
            output_path: Output file path
            start_date: Start date filter
            end_date: End date filter
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM audit_events"
        params = []
        conditions = []
        
        if start_date:
            conditions.append("timestamp >= ?")
            params.append(start_date.timestamp())
        
        if end_date:
            conditions.append("timestamp <= ?")
            params.append(end_date.timestamp())
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp"
        
        cursor.execute(query, params)
        
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            if event['metadata']:
                event['metadata'] = json.loads(event['metadata'])
            events.append(event)
        
        with open(output_path, 'w') as f:
            json.dump(events, f, indent=2)
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
