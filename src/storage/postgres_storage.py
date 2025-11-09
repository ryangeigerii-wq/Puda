"""
PostgreSQL Storage Backend

PostgreSQL database for metadata indexing, audit logs, and storage records.
Provides better scalability and concurrent access compared to SQLite.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

try:
    import psycopg2
    from psycopg2 import sql, extras
    from psycopg2.pool import ThreadedConnectionPool
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class PostgreSQLStorageDB:
    """
    PostgreSQL database for storage metadata and audit logs.
    
    Features:
    - Connection pooling for concurrent access
    - Full-text search with tsvector
    - JSON/JSONB support for flexible metadata
    - Partitioning support for large datasets
    - Replication-ready schemas
    - Transaction support
    
    Tables:
    - storage_objects: Object metadata
    - storage_versions: Version history
    - storage_audit: Access audit logs
    - storage_hooks: Integration hook execution logs
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "puda_storage",
        user: str = "puda",
        password: str = "puda",
        min_connections: int = 2,
        max_connections: int = 20
    ):
        """
        Initialize PostgreSQL storage database.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum pool connections
            max_connections: Maximum pool connections
        """
        if not POSTGRES_AVAILABLE:
            raise ImportError("psycopg2 not installed. Install via: pip install psycopg2-binary")
        
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.logger = logging.getLogger(__name__)
        
        # Create connection pool
        self.pool = ThreadedConnectionPool(
            min_connections,
            max_connections,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        # Initialize schema
        self._initialize_schema()
        
        self.logger.info(f"PostgreSQL storage initialized: {host}:{port}/{database}")
    
    def _get_connection(self):
        """Get connection from pool."""
        return self.pool.getconn()
    
    def _put_connection(self, conn):
        """Return connection to pool."""
        self.pool.putconn(conn)
    
    def _initialize_schema(self):
        """Create database schema if not exists."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Create storage_objects table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS storage_objects (
                        id SERIAL PRIMARY KEY,
                        object_key TEXT NOT NULL UNIQUE,
                        size BIGINT NOT NULL,
                        content_type TEXT NOT NULL,
                        etag TEXT NOT NULL,
                        last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        version_id TEXT,
                        storage_backend TEXT NOT NULL,
                        storage_class TEXT,
                        metadata JSONB,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        search_vector tsvector
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_storage_objects_key 
                        ON storage_objects(object_key);
                    CREATE INDEX IF NOT EXISTS idx_storage_objects_backend 
                        ON storage_objects(storage_backend);
                    CREATE INDEX IF NOT EXISTS idx_storage_objects_modified 
                        ON storage_objects(last_modified DESC);
                    CREATE INDEX IF NOT EXISTS idx_storage_objects_metadata 
                        ON storage_objects USING gin(metadata);
                    CREATE INDEX IF NOT EXISTS idx_storage_objects_search 
                        ON storage_objects USING gin(search_vector);
                """)
                
                # Create storage_versions table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS storage_versions (
                        id SERIAL PRIMARY KEY,
                        object_key TEXT NOT NULL,
                        version_id TEXT NOT NULL,
                        size BIGINT NOT NULL,
                        etag TEXT NOT NULL,
                        last_modified TIMESTAMP NOT NULL,
                        is_latest BOOLEAN NOT NULL DEFAULT FALSE,
                        created_by TEXT,
                        comment TEXT,
                        tags JSONB,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(object_key, version_id)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_storage_versions_key 
                        ON storage_versions(object_key);
                    CREATE INDEX IF NOT EXISTS idx_storage_versions_version 
                        ON storage_versions(version_id);
                    CREATE INDEX IF NOT EXISTS idx_storage_versions_latest 
                        ON storage_versions(object_key, is_latest);
                    CREATE INDEX IF NOT EXISTS idx_storage_versions_tags 
                        ON storage_versions USING gin(tags);
                """)
                
                # Create storage_audit table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS storage_audit (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        user_id TEXT,
                        username TEXT,
                        action TEXT NOT NULL,
                        object_key TEXT,
                        version_id TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        success BOOLEAN NOT NULL DEFAULT TRUE,
                        error_message TEXT,
                        metadata JSONB
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_storage_audit_timestamp 
                        ON storage_audit(timestamp DESC);
                    CREATE INDEX IF NOT EXISTS idx_storage_audit_user 
                        ON storage_audit(user_id);
                    CREATE INDEX IF NOT EXISTS idx_storage_audit_key 
                        ON storage_audit(object_key);
                    CREATE INDEX IF NOT EXISTS idx_storage_audit_action 
                        ON storage_audit(action);
                """)
                
                # Create storage_hooks table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS storage_hooks (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        hook_name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        object_key TEXT,
                        execution_time FLOAT,
                        success BOOLEAN NOT NULL,
                        error_message TEXT,
                        response JSONB,
                        payload JSONB
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_storage_hooks_timestamp 
                        ON storage_hooks(timestamp DESC);
                    CREATE INDEX IF NOT EXISTS idx_storage_hooks_name 
                        ON storage_hooks(hook_name);
                    CREATE INDEX IF NOT EXISTS idx_storage_hooks_event 
                        ON storage_hooks(event_type);
                    CREATE INDEX IF NOT EXISTS idx_storage_hooks_success 
                        ON storage_hooks(success);
                """)
                
                # Create trigger for search_vector update
                cur.execute("""
                    CREATE OR REPLACE FUNCTION storage_objects_search_trigger() 
                    RETURNS trigger AS $$
                    BEGIN
                        NEW.search_vector := 
                            setweight(to_tsvector('english', coalesce(NEW.object_key, '')), 'A') ||
                            setweight(to_tsvector('english', coalesce(NEW.content_type, '')), 'B') ||
                            setweight(to_tsvector('english', coalesce(NEW.metadata::text, '')), 'C');
                        RETURN NEW;
                    END
                    $$ LANGUAGE plpgsql;
                    
                    DROP TRIGGER IF EXISTS storage_objects_search_update ON storage_objects;
                    
                    CREATE TRIGGER storage_objects_search_update
                        BEFORE INSERT OR UPDATE ON storage_objects
                        FOR EACH ROW EXECUTE FUNCTION storage_objects_search_trigger();
                """)
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to initialize schema: {e}")
            raise
        finally:
            self._put_connection(conn)
    
    def record_object(
        self,
        object_key: str,
        size: int,
        content_type: str,
        etag: str,
        version_id: Optional[str],
        storage_backend: str,
        storage_class: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Record or update object in database.
        
        Returns:
            Object ID
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO storage_objects 
                        (object_key, size, content_type, etag, version_id, 
                         storage_backend, storage_class, metadata, last_modified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (object_key) DO UPDATE SET
                        size = EXCLUDED.size,
                        content_type = EXCLUDED.content_type,
                        etag = EXCLUDED.etag,
                        version_id = EXCLUDED.version_id,
                        storage_class = EXCLUDED.storage_class,
                        metadata = EXCLUDED.metadata,
                        last_modified = CURRENT_TIMESTAMP
                    RETURNING id
                """, (object_key, size, content_type, etag, version_id,
                      storage_backend, storage_class, json.dumps(metadata) if metadata else None))
                
                object_id = cur.fetchone()[0]
                conn.commit()
                return object_id
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to record object: {e}")
            raise
        finally:
            self._put_connection(conn)
    
    def get_object_metadata(self, object_key: str) -> Optional[Dict[str, Any]]:
        """Get object metadata from database."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM storage_objects WHERE object_key = %s
                """, (object_key,))
                
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put_connection(conn)
    
    def list_objects(
        self,
        prefix: Optional[str] = None,
        storage_backend: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List objects with optional filters."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                query = "SELECT * FROM storage_objects WHERE 1=1"
                params = []
                
                if prefix:
                    query += " AND object_key LIKE %s"
                    params.append(f"{prefix}%")
                
                if storage_backend:
                    query += " AND storage_backend = %s"
                    params.append(storage_backend)
                
                query += " ORDER BY last_modified DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        finally:
            self._put_connection(conn)
    
    def search_objects(
        self,
        search_query: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Full-text search on objects."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT *, ts_rank(search_vector, query) AS rank
                    FROM storage_objects, 
                         to_tsquery('english', %s) query
                    WHERE search_vector @@ query
                    ORDER BY rank DESC
                    LIMIT %s
                """, (search_query, limit))
                
                return [dict(row) for row in cur.fetchall()]
        finally:
            self._put_connection(conn)
    
    def delete_object(self, object_key: str) -> bool:
        """Delete object from database."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM storage_objects WHERE object_key = %s", (object_key,))
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to delete object: {e}")
            return False
        finally:
            self._put_connection(conn)
    
    def record_version(
        self,
        object_key: str,
        version_id: str,
        size: int,
        etag: str,
        is_latest: bool = False,
        created_by: Optional[str] = None,
        comment: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Record object version."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Mark all versions as not latest if this is latest
                if is_latest:
                    cur.execute("""
                        UPDATE storage_versions 
                        SET is_latest = FALSE 
                        WHERE object_key = %s
                    """, (object_key,))
                
                # Insert version
                cur.execute("""
                    INSERT INTO storage_versions
                        (object_key, version_id, size, etag, last_modified, 
                         is_latest, created_by, comment, tags)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s)
                    ON CONFLICT (object_key, version_id) DO UPDATE SET
                        is_latest = EXCLUDED.is_latest,
                        comment = EXCLUDED.comment,
                        tags = EXCLUDED.tags
                """, (object_key, version_id, size, etag, is_latest,
                      created_by, comment, json.dumps(tags) if tags else None))
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to record version: {e}")
            raise
        finally:
            self._put_connection(conn)
    
    def list_versions(self, object_key: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List all versions of an object."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM storage_versions 
                    WHERE object_key = %s 
                    ORDER BY last_modified DESC 
                    LIMIT %s
                """, (object_key, limit))
                
                return [dict(row) for row in cur.fetchall()]
        finally:
            self._put_connection(conn)
    
    def log_audit(
        self,
        action: str,
        object_key: Optional[str] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        version_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log audit event."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO storage_audit
                        (user_id, username, action, object_key, version_id,
                         ip_address, user_agent, success, error_message, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, username, action, object_key, version_id,
                      ip_address, user_agent, success, error_message,
                      json.dumps(metadata) if metadata else None))
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to log audit: {e}")
        finally:
            self._put_connection(conn)
    
    def get_audit_logs(
        self,
        object_key: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query audit logs with filters."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                query = "SELECT * FROM storage_audit WHERE 1=1"
                params = []
                
                if object_key:
                    query += " AND object_key = %s"
                    params.append(object_key)
                
                if user_id:
                    query += " AND user_id = %s"
                    params.append(user_id)
                
                if action:
                    query += " AND action = %s"
                    params.append(action)
                
                if start_date:
                    query += " AND timestamp >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= %s"
                    params.append(end_date)
                
                query += " ORDER BY timestamp DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        finally:
            self._put_connection(conn)
    
    def log_hook_execution(
        self,
        hook_name: str,
        event_type: str,
        object_key: Optional[str],
        execution_time: float,
        success: bool,
        error_message: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None
    ):
        """Log integration hook execution."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO storage_hooks
                        (hook_name, event_type, object_key, execution_time,
                         success, error_message, response, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (hook_name, event_type, object_key, execution_time,
                      success, error_message,
                      json.dumps(response) if response else None,
                      json.dumps(payload) if payload else None))
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to log hook execution: {e}")
        finally:
            self._put_connection(conn)
    
    def get_hook_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get hook execution statistics."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cutoff = datetime.now() - timedelta(hours=hours)
                
                cur.execute("""
                    SELECT 
                        hook_name,
                        event_type,
                        COUNT(*) as total_executions,
                        SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed,
                        AVG(execution_time) as avg_execution_time,
                        MAX(execution_time) as max_execution_time
                    FROM storage_hooks
                    WHERE timestamp >= %s
                    GROUP BY hook_name, event_type
                    ORDER BY total_executions DESC
                """, (cutoff,))
                
                return [dict(row) for row in cur.fetchall()]
        finally:
            self._put_connection(conn)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall storage statistics."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Object statistics
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_objects,
                        SUM(size) as total_size,
                        storage_backend,
                        COUNT(DISTINCT storage_backend) as backend_count
                    FROM storage_objects
                    GROUP BY storage_backend
                """)
                
                objects_stats = cur.fetchall()
                
                # Version statistics
                cur.execute("SELECT COUNT(*) FROM storage_versions")
                version_count = cur.fetchone()[0]
                
                # Audit statistics
                cur.execute("""
                    SELECT COUNT(*) FROM storage_audit 
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                """)
                recent_audits = cur.fetchone()[0]
                
                # Hook statistics
                cur.execute("""
                    SELECT COUNT(*) FROM storage_hooks 
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                """)
                recent_hooks = cur.fetchone()[0]
                
                return {
                    'objects': objects_stats,
                    'total_versions': version_count,
                    'recent_audits_24h': recent_audits,
                    'recent_hooks_24h': recent_hooks
                }
        finally:
            self._put_connection(conn)
    
    def cleanup_old_audits(self, days: int = 365) -> int:
        """Remove audit logs older than specified days."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cutoff = datetime.now() - timedelta(days=days)
                cur.execute("DELETE FROM storage_audit WHERE timestamp < %s", (cutoff,))
                deleted = cur.rowcount
                conn.commit()
                return deleted
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to cleanup audits: {e}")
            return 0
        finally:
            self._put_connection(conn)
    
    def close(self):
        """Close connection pool."""
        if self.pool:
            self.pool.closeall()
            self.logger.info("PostgreSQL connection pool closed")
