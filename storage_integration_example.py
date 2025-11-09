#!/usr/bin/env python3
"""
Storage Integration Example

Demonstrates PostgreSQL database integration with S3 and Local storage backends.
Shows complete workflow: upload, metadata recording, version tracking, and audit logging.
"""

import os
import json
from datetime import datetime
from pathlib import Path

# Import storage components
from src.storage import (
    PostgreSQLStorageDB,
    S3StorageManager,
    LocalStorageManager,
    VersionManager,
    IntegrationHookManager,
    HookEvent
)


class StorageWithDatabase:
    """
    Integrated storage system with PostgreSQL metadata database.
    
    Combines object storage (S3 or Local) with PostgreSQL for:
    - Metadata indexing and search
    - Version history tracking
    - Access audit logging
    - Integration hook tracking
    """
    
    def __init__(
        self,
        storage_backend="local",
        storage_path="data/storage",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="puda_storage",
        postgres_user="puda",
        postgres_password="puda"
    ):
        """
        Initialize integrated storage system.
        
        Args:
            storage_backend: "local" or "s3"
            storage_path: Path for local storage or S3 bucket name
            postgres_*: PostgreSQL connection parameters
        """
        # Initialize PostgreSQL database
        self.db = PostgreSQLStorageDB(
            host=postgres_host,
            port=postgres_port,
            database=postgres_db,
            user=postgres_user,
            password=postgres_password
        )
        
        # Initialize storage backend
        if storage_backend == "local":
            self.storage = LocalStorageManager(
                base_path=storage_path,
                enable_versioning=True
            )
        else:  # s3
            # Get S3 credentials from environment
            self.storage = S3StorageManager(
                bucket_name=storage_path,
                endpoint_url=os.getenv("S3_ENDPOINT"),
                aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
                enable_versioning=True
            )
        
        # Initialize version manager
        self.version_manager = VersionManager(self.storage)
        
        # Initialize hook manager
        self.hook_manager = IntegrationHookManager()
        
        print(f"Storage initialized: {storage_backend}")
        print(f"Database: {postgres_host}:{postgres_port}/{postgres_db}")
    
    def upload_document(
        self,
        file_path: str,
        object_key: str,
        metadata: dict = None,
        user_id: str = None,
        user_name: str = None
    ) -> dict:
        """
        Upload document with full metadata tracking.
        
        Args:
            file_path: Local file to upload
            object_key: Storage key (e.g., "documents/invoice.pdf")
            metadata: Custom metadata dict
            user_id: User performing upload
            user_name: Username
        
        Returns:
            Upload result dict with object_id, version_id, etc.
        """
        # Read file
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Determine content type
        content_type = "application/octet-stream"
        if file_path.endswith('.pdf'):
            content_type = "application/pdf"
        elif file_path.endswith('.json'):
            content_type = "application/json"
        elif file_path.endswith('.txt'):
            content_type = "text/plain"
        
        # Upload to storage backend
        result = self.storage.put_object(
            key=object_key,
            data=data,
            content_type=content_type,
            metadata=metadata
        )
        
        # Record in PostgreSQL
        object_id = self.db.record_object(
            object_key=object_key,
            size=len(data),
            content_type=content_type,
            etag=result.etag,
            version_id=result.version_id,
            storage_backend=self.storage.get_storage_info()['backend'].value,
            metadata=metadata
        )
        
        # Record version
        self.db.record_version(
            object_key=object_key,
            version_id=result.version_id,
            size=len(data),
            etag=result.etag,
            is_latest=True,
            created_by=user_name or user_id,
            comment=f"Uploaded from {file_path}"
        )
        
        # Log audit
        self.db.log_audit(
            action="UPLOAD",
            object_key=object_key,
            user_id=user_id,
            username=user_name,
            version_id=result.version_id,
            success=True,
            metadata={"file_path": file_path, "size": len(data)}
        )
        
        # Fire integration hook
        self.hook_manager.fire_event(
            event=HookEvent.DOCUMENT_ARCHIVED,
            data={
                "object_key": object_key,
                "size": len(data),
                "version_id": result.version_id,
                "metadata": metadata
            }
        )
        
        return {
            "object_id": object_id,
            "object_key": object_key,
            "version_id": result.version_id,
            "etag": result.etag,
            "size": len(data),
            "content_type": content_type
        }
    
    def download_document(
        self,
        object_key: str,
        output_path: str = None,
        version_id: str = None,
        user_id: str = None,
        user_name: str = None
    ) -> bytes:
        """
        Download document with audit logging.
        
        Args:
            object_key: Storage key
            output_path: Optional path to save file
            version_id: Optional specific version
            user_id: User performing download
            user_name: Username
        
        Returns:
            Document data as bytes
        """
        # Download from storage
        data = self.storage.get_object(object_key, version_id=version_id)
        
        # Save to file if requested
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(data)
        
        # Log audit
        self.db.log_audit(
            action="DOWNLOAD",
            object_key=object_key,
            user_id=user_id,
            username=user_name,
            version_id=version_id,
            success=True,
            metadata={"output_path": output_path, "size": len(data)}
        )
        
        # Fire integration hook
        self.hook_manager.fire_event(
            event=HookEvent.DOCUMENT_RETRIEVED,
            data={
                "object_key": object_key,
                "version_id": version_id,
                "size": len(data)
            }
        )
        
        return data
    
    def search_documents(
        self,
        search_query: str = None,
        prefix: str = None,
        metadata_filters: dict = None,
        limit: int = 100
    ) -> list:
        """
        Search documents using PostgreSQL full-text search.
        
        Args:
            search_query: Full-text search query
            prefix: Key prefix filter
            metadata_filters: Metadata filters (not implemented yet)
            limit: Maximum results
        
        Returns:
            List of matching documents
        """
        if search_query:
            # Full-text search
            return self.db.search_objects(search_query, limit=limit)
        else:
            # Prefix listing
            return self.db.list_objects(prefix=prefix, limit=limit)
    
    def get_version_history(self, object_key: str) -> list:
        """Get complete version history for document."""
        return self.db.list_versions(object_key)
    
    def get_audit_trail(
        self,
        object_key: str = None,
        user_id: str = None,
        limit: int = 1000
    ) -> list:
        """Get audit trail for document or user."""
        return self.db.get_audit_logs(
            object_key=object_key,
            user_id=user_id,
            limit=limit
        )
    
    def get_statistics(self) -> dict:
        """Get overall storage statistics."""
        return self.db.get_statistics()


def main():
    """Example usage of integrated storage system."""
    
    print("=" * 70)
    print("Storage Integration Example with PostgreSQL")
    print("=" * 70)
    
    # Initialize storage (use environment variables or defaults)
    storage = StorageWithDatabase(
        storage_backend=os.getenv("STORAGE_BACKEND", "local"),
        storage_path=os.getenv("STORAGE_PATH", "data/storage"),
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", 5432)),
        postgres_db=os.getenv("POSTGRES_DB", "puda_storage"),
        postgres_user=os.getenv("POSTGRES_USER", "puda"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "puda")
    )
    
    print("\n1. Upload Test Document")
    print("-" * 70)
    
    # Create test file
    test_file = "test_document.txt"
    with open(test_file, 'w') as f:
        f.write("This is a test document for storage integration.\n")
        f.write(f"Created at: {datetime.now().isoformat()}\n")
    
    # Upload document
    result = storage.upload_document(
        file_path=test_file,
        object_key="test/integration/document.txt",
        metadata={
            "owner": "ACME Corp",
            "department": "Engineering",
            "doc_type": "Test",
            "confidentiality": "internal"
        },
        user_id="user123",
        user_name="john@example.com"
    )
    
    print(f"Uploaded: {result['object_key']}")
    print(f"Object ID: {result['object_id']}")
    print(f"Version: {result['version_id']}")
    print(f"Size: {result['size']} bytes")
    print(f"ETag: {result['etag']}")
    
    print("\n2. Search Documents")
    print("-" * 70)
    
    # Full-text search
    results = storage.search_documents(
        search_query="test & integration",
        limit=10
    )
    
    print(f"Found {len(results)} documents:")
    for doc in results:
        print(f"  - {doc['object_key']}")
        print(f"    Size: {doc['size']} bytes")
        print(f"    Modified: {doc['last_modified']}")
        if 'rank' in doc:
            print(f"    Search rank: {doc['rank']:.4f}")
    
    print("\n3. List Documents by Prefix")
    print("-" * 70)
    
    results = storage.search_documents(prefix="test/", limit=10)
    print(f"Found {len(results)} documents with prefix 'test/':")
    for doc in results:
        print(f"  - {doc['object_key']}")
    
    print("\n4. Version History")
    print("-" * 70)
    
    versions = storage.get_version_history("test/integration/document.txt")
    print(f"Found {len(versions)} versions:")
    for ver in versions:
        print(f"  Version: {ver['version_id']}")
        print(f"  Created: {ver['last_modified']}")
        print(f"  Latest: {ver['is_latest']}")
        print(f"  By: {ver['created_by']}")
        print(f"  Comment: {ver['comment']}")
        print()
    
    print("\n5. Audit Trail")
    print("-" * 70)
    
    audit_logs = storage.get_audit_trail(
        object_key="test/integration/document.txt"
    )
    print(f"Found {len(audit_logs)} audit events:")
    for log in audit_logs:
        print(f"  {log['timestamp']}: {log['action']}")
        print(f"    User: {log['username']} ({log['user_id']})")
        print(f"    Success: {log['success']}")
        print()
    
    print("\n6. Download Document")
    print("-" * 70)
    
    data = storage.download_document(
        object_key="test/integration/document.txt",
        output_path="downloaded_document.txt",
        user_id="user456",
        user_name="jane@example.com"
    )
    
    print(f"Downloaded {len(data)} bytes")
    print("Content:")
    print(data.decode('utf-8'))
    
    print("\n7. Storage Statistics")
    print("-" * 70)
    
    stats = storage.get_statistics()
    print("Storage Statistics:")
    
    if stats['objects']:
        for obj_stat in stats['objects']:
            if isinstance(obj_stat, tuple):
                total, size, backend, count = obj_stat
                print(f"  {backend}:")
                print(f"    Objects: {total}")
                print(f"    Size: {size / 1024 / 1024:.2f} MB")
    
    print(f"\nTotal versions: {stats['total_versions']}")
    print(f"Audit logs (24h): {stats['recent_audits_24h']}")
    print(f"Hook executions (24h): {stats['recent_hooks_24h']}")
    
    print("\n" + "=" * 70)
    print("Integration example completed successfully!")
    print("=" * 70)
    
    # Cleanup test files
    if os.path.exists(test_file):
        os.remove(test_file)
    if os.path.exists("downloaded_document.txt"):
        os.remove("downloaded_document.txt")


if __name__ == "__main__":
    main()
