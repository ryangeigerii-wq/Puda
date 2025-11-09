"""
Storage Interface

Abstract interface for storage backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, BinaryIO
from pathlib import Path


class StorageBackend(Enum):
    """Supported storage backend types."""
    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"
    NAS = "nas"


@dataclass
class StorageMetadata:
    """Metadata for stored objects."""
    key: str
    size: int
    content_type: str
    etag: str
    last_modified: datetime
    version_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    storage_class: Optional[str] = None


@dataclass
class VersionInfo:
    """Information about object version."""
    version_id: str
    is_latest: bool
    last_modified: datetime
    size: int
    etag: str


class StorageInterface(ABC):
    """
    Abstract interface for storage backends.
    
    Supports local filesystem, S3-compatible object storage,
    Azure Blob Storage, Google Cloud Storage, and NAS.
    """
    
    @abstractmethod
    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageMetadata:
        """
        Store an object.
        
        Args:
            key: Object key/path
            data: Object data
            content_type: MIME type
            metadata: Custom metadata
            
        Returns:
            StorageMetadata with version information
        """
        pass
    
    @abstractmethod
    def get_object(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> bytes:
        """
        Retrieve an object.
        
        Args:
            key: Object key/path
            version_id: Specific version (None = latest)
            
        Returns:
            Object data
            
        Raises:
            FileNotFoundError: Object not found
        """
        pass
    
    @abstractmethod
    def delete_object(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> bool:
        """
        Delete an object or version.
        
        Args:
            key: Object key/path
            version_id: Specific version (None = delete marker)
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000
    ) -> List[StorageMetadata]:
        """
        List objects with optional prefix filter.
        
        Args:
            prefix: Key prefix filter
            max_keys: Maximum results
            
        Returns:
            List of StorageMetadata
        """
        pass
    
    @abstractmethod
    def get_metadata(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> StorageMetadata:
        """
        Get object metadata without downloading.
        
        Args:
            key: Object key/path
            version_id: Specific version
            
        Returns:
            StorageMetadata
            
        Raises:
            FileNotFoundError: Object not found
        """
        pass
    
    @abstractmethod
    def list_versions(
        self,
        key: str
    ) -> List[VersionInfo]:
        """
        List all versions of an object.
        
        Args:
            key: Object key/path
            
        Returns:
            List of VersionInfo, newest first
        """
        pass
    
    @abstractmethod
    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageMetadata:
        """
        Copy an object.
        
        Args:
            source_key: Source object key
            dest_key: Destination object key
            metadata: New metadata (None = copy source metadata)
            
        Returns:
            StorageMetadata of destination
        """
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if object exists.
        
        Args:
            key: Object key/path
            
        Returns:
            True if exists
        """
        pass
    
    @abstractmethod
    def get_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """
        Get presigned URL for object access.
        
        Args:
            key: Object key/path
            expires_in: URL expiration in seconds
            
        Returns:
            Presigned URL
        """
        pass
    
    @abstractmethod
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage backend information.
        
        Returns:
            Dict with backend type, versioning status, etc.
        """
        pass
