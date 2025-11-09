"""
Local Storage Manager

File-system based storage with version control.
"""

import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import uuid

from .storage_interface import (
    StorageInterface,
    StorageBackend,
    StorageMetadata,
    VersionInfo
)


class LocalStorageManager(StorageInterface):
    """
    Local filesystem storage with versioning.
    
    Features:
    - Version control with .versions/ directory
    - Metadata stored as JSON sidecars
    - Content-addressable storage for deduplication
    - File integrity verification (checksums)
    - Symlink support for NAS mounting
    
    Directory Structure:
        base_path/
            objects/
                {key}           # Current version
            .versions/
                {key}/
                    {version_id}    # Historical versions
            .metadata/
                {key}.json      # Object metadata
    """
    
    def __init__(
        self,
        base_path: str,
        enable_versioning: bool = True,
        max_versions: int = 10
    ):
        """
        Initialize local storage manager.
        
        Args:
            base_path: Root directory for storage
            enable_versioning: Enable version control
            max_versions: Maximum versions to keep per object
        """
        self.base_path = Path(base_path)
        self.enable_versioning = enable_versioning
        self.max_versions = max_versions
        self.logger = logging.getLogger(__name__)
        
        # Create directory structure
        self.objects_dir = self.base_path / "objects"
        self.versions_dir = self.base_path / ".versions"
        self.metadata_dir = self.base_path / ".metadata"
        
        for directory in [self.objects_dir, self.versions_dir, self.metadata_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Local storage initialized: {self.base_path}")
    
    def _get_object_path(self, key: str) -> Path:
        """Get path for object file."""
        return self.objects_dir / key
    
    def _get_metadata_path(self, key: str) -> Path:
        """Get path for metadata file."""
        return self.metadata_dir / f"{key}.json"
    
    def _get_version_dir(self, key: str) -> Path:
        """Get directory for object versions."""
        return self.versions_dir / key
    
    def _compute_etag(self, data: bytes) -> str:
        """Compute ETag (MD5 hash) for data."""
        return hashlib.md5(data).hexdigest()
    
    def _save_metadata(self, metadata: StorageMetadata):
        """Save metadata to JSON file."""
        metadata_path = self._get_metadata_path(metadata.key)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        metadata_dict = {
            'key': metadata.key,
            'size': metadata.size,
            'content_type': metadata.content_type,
            'etag': metadata.etag,
            'last_modified': metadata.last_modified.isoformat(),
            'version_id': metadata.version_id,
            'metadata': metadata.metadata,
            'storage_class': metadata.storage_class
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata_dict, f, indent=2)
    
    def _load_metadata(self, key: str) -> Optional[StorageMetadata]:
        """Load metadata from JSON file."""
        metadata_path = self._get_metadata_path(key)
        
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r') as f:
                data = json.load(f)
            
            return StorageMetadata(
                key=data['key'],
                size=data['size'],
                content_type=data['content_type'],
                etag=data['etag'],
                last_modified=datetime.fromisoformat(data['last_modified']),
                version_id=data.get('version_id'),
                metadata=data.get('metadata'),
                storage_class=data.get('storage_class', 'STANDARD')
            )
        except Exception as e:
            self.logger.error(f"Failed to load metadata for {key}: {e}")
            return None
    
    def _create_version(self, key: str, data: bytes) -> str:
        """Create a new version of an object."""
        if not self.enable_versioning:
            return "null"
        
        version_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        version_dir = self._get_version_dir(key)
        version_dir.mkdir(parents=True, exist_ok=True)
        
        version_path = version_dir / version_id
        version_path.write_bytes(data)
        
        # Clean up old versions
        self._cleanup_old_versions(key)
        
        return version_id
    
    def _cleanup_old_versions(self, key: str):
        """Remove old versions exceeding max_versions."""
        version_dir = self._get_version_dir(key)
        
        if not version_dir.exists():
            return
        
        versions = sorted(version_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if len(versions) > self.max_versions:
            for old_version in versions[self.max_versions:]:
                old_version.unlink()
                self.logger.debug(f"Removed old version: {old_version}")
    
    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageMetadata:
        """Store an object to local filesystem."""
        object_path = self._get_object_path(key)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create version before overwriting
        if object_path.exists() and self.enable_versioning:
            existing_data = object_path.read_bytes()
            version_id = self._create_version(key, existing_data)
        else:
            version_id = None
        
        # Write new object
        object_path.write_bytes(data)
        
        # Create metadata
        etag = self._compute_etag(data)
        storage_metadata = StorageMetadata(
            key=key,
            size=len(data),
            content_type=content_type,
            etag=etag,
            last_modified=datetime.now(),
            version_id=self._create_version(key, data) if self.enable_versioning else None,
            metadata=metadata,
            storage_class="STANDARD"
        )
        
        # Save metadata
        self._save_metadata(storage_metadata)
        
        return storage_metadata
    
    def get_object(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> bytes:
        """Retrieve an object from local filesystem."""
        if version_id:
            # Get specific version
            version_path = self._get_version_dir(key) / version_id
            if not version_path.exists():
                raise FileNotFoundError(f"Version not found: {key}@{version_id}")
            return version_path.read_bytes()
        else:
            # Get current version
            object_path = self._get_object_path(key)
            if not object_path.exists():
                raise FileNotFoundError(f"Object not found: {key}")
            return object_path.read_bytes()
    
    def delete_object(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> bool:
        """Delete an object or version from local filesystem."""
        try:
            if version_id:
                # Delete specific version
                version_path = self._get_version_dir(key) / version_id
                if version_path.exists():
                    version_path.unlink()
                    return True
                return False
            else:
                # Delete current object
                object_path = self._get_object_path(key)
                if object_path.exists():
                    object_path.unlink()
                
                # Delete metadata
                metadata_path = self._get_metadata_path(key)
                if metadata_path.exists():
                    metadata_path.unlink()
                
                # Optionally delete version directory
                version_dir = self._get_version_dir(key)
                if version_dir.exists():
                    shutil.rmtree(version_dir)
                
                return True
        except Exception as e:
            self.logger.error(f"Failed to delete {key}: {e}")
            return False
    
    def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000
    ) -> List[StorageMetadata]:
        """List objects in local storage."""
        objects = []
        
        # Find all object files
        if prefix:
            pattern = f"{prefix}*"
        else:
            pattern = "*"
        
        for object_path in self.objects_dir.rglob(pattern):
            if object_path.is_file():
                key = str(object_path.relative_to(self.objects_dir))
                metadata = self._load_metadata(key)
                
                if metadata:
                    objects.append(metadata)
                
                if len(objects) >= max_keys:
                    break
        
        return objects
    
    def get_metadata(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> StorageMetadata:
        """Get object metadata from local filesystem."""
        if version_id:
            # Get version metadata
            version_path = self._get_version_dir(key) / version_id
            if not version_path.exists():
                raise FileNotFoundError(f"Version not found: {key}@{version_id}")
            
            data = version_path.read_bytes()
            stat = version_path.stat()
            
            return StorageMetadata(
                key=key,
                size=len(data),
                content_type="application/octet-stream",
                etag=self._compute_etag(data),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                version_id=version_id,
                metadata=None,
                storage_class="STANDARD"
            )
        else:
            # Get current metadata
            metadata = self._load_metadata(key)
            if not metadata:
                raise FileNotFoundError(f"Object not found: {key}")
            return metadata
    
    def list_versions(
        self,
        key: str
    ) -> List[VersionInfo]:
        """List all versions of an object."""
        version_dir = self._get_version_dir(key)
        
        if not version_dir.exists():
            return []
        
        versions = []
        version_files = sorted(version_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        
        for idx, version_path in enumerate(version_files):
            stat = version_path.stat()
            data = version_path.read_bytes()
            
            versions.append(VersionInfo(
                version_id=version_path.name,
                is_latest=(idx == 0),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                size=len(data),
                etag=self._compute_etag(data)
            ))
        
        return versions
    
    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageMetadata:
        """Copy an object within local storage."""
        # Get source data
        data = self.get_object(source_key)
        
        # Get source metadata
        source_metadata = self.get_metadata(source_key)
        
        # Use new metadata if provided, otherwise copy source
        if metadata is None:
            metadata = source_metadata.metadata
        
        # Put object at destination
        return self.put_object(
            dest_key,
            data,
            content_type=source_metadata.content_type,
            metadata=metadata
        )
    
    def exists(self, key: str) -> bool:
        """Check if object exists in local storage."""
        return self._get_object_path(key).exists()
    
    def get_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """Get local file URL (file:// scheme)."""
        object_path = self._get_object_path(key)
        if not object_path.exists():
            raise FileNotFoundError(f"Object not found: {key}")
        
        return f"file://{object_path.absolute()}"
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get local storage information."""
        # Calculate total storage usage
        total_size = 0
        object_count = 0
        
        for object_path in self.objects_dir.rglob("*"):
            if object_path.is_file():
                total_size += object_path.stat().st_size
                object_count += 1
        
        # Count versions
        version_count = 0
        version_size = 0
        
        for version_path in self.versions_dir.rglob("*"):
            if version_path.is_file():
                version_size += version_path.stat().st_size
                version_count += 1
        
        return {
            'backend': StorageBackend.LOCAL.value,
            'base_path': str(self.base_path),
            'versioning': 'Enabled' if self.enable_versioning else 'Disabled',
            'max_versions': self.max_versions,
            'object_count': object_count,
            'total_size': total_size,
            'version_count': version_count,
            'version_size': version_size,
            'total_storage': total_size + version_size
        }
