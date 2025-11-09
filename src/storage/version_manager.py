"""
Version Manager

Unified versioning interface across storage backends.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from .storage_interface import StorageInterface, VersionInfo


@dataclass
class VersionMetadata:
    """Extended version metadata."""
    version_id: str
    key: str
    size: int
    etag: str
    last_modified: datetime
    is_latest: bool
    created_by: Optional[str] = None
    comment: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['last_modified'] = self.last_modified.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionMetadata':
        """Create from dictionary."""
        data['last_modified'] = datetime.fromisoformat(data['last_modified'])
        return cls(**data)


class VersionManager:
    """
    Manages object versioning across storage backends.
    
    Features:
    - Version comparison and diff
    - Rollback to previous versions
    - Version tagging and comments
    - Retention policies
    - Audit trail for version changes
    """
    
    def __init__(
        self,
        storage: StorageInterface,
        version_metadata_dir: Optional[Path] = None
    ):
        """
        Initialize version manager.
        
        Args:
            storage: Storage backend interface
            version_metadata_dir: Directory for extended version metadata
        """
        self.storage = storage
        self.version_metadata_dir = version_metadata_dir or Path("data/.version_metadata")
        self.version_metadata_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def _get_version_metadata_path(self, key: str, version_id: str) -> Path:
        """Get path for version metadata file."""
        safe_key = key.replace('/', '_')
        return self.version_metadata_dir / f"{safe_key}_{version_id}.json"
    
    def list_versions(
        self,
        key: str,
        limit: Optional[int] = None
    ) -> List[VersionMetadata]:
        """
        List all versions of an object with extended metadata.
        
        Args:
            key: Object key
            limit: Maximum number of versions
            
        Returns:
            List of VersionMetadata, newest first
        """
        # Get versions from storage
        storage_versions = self.storage.list_versions(key)
        
        if limit:
            storage_versions = storage_versions[:limit]
        
        # Enhance with extended metadata
        versions = []
        for storage_version in storage_versions:
            version_metadata = self._load_version_metadata(key, storage_version.version_id)
            
            if version_metadata:
                versions.append(version_metadata)
            else:
                # Create basic version metadata
                versions.append(VersionMetadata(
                    version_id=storage_version.version_id,
                    key=key,
                    size=storage_version.size,
                    etag=storage_version.etag,
                    last_modified=storage_version.last_modified,
                    is_latest=storage_version.is_latest
                ))
        
        return versions
    
    def get_version(
        self,
        key: str,
        version_id: str
    ) -> bytes:
        """
        Get specific version of an object.
        
        Args:
            key: Object key
            version_id: Version identifier
            
        Returns:
            Object data
        """
        return self.storage.get_object(key, version_id=version_id)
    
    def rollback(
        self,
        key: str,
        version_id: str,
        comment: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> VersionMetadata:
        """
        Rollback object to a previous version.
        
        Args:
            key: Object key
            version_id: Version to rollback to
            comment: Rollback reason
            created_by: User performing rollback
            
        Returns:
            New version metadata
        """
        # Get the target version data
        data = self.storage.get_object(key, version_id=version_id)
        
        # Get original metadata
        original_metadata = self.storage.get_metadata(key, version_id=version_id)
        
        # Put as new current version
        new_metadata = self.storage.put_object(
            key,
            data,
            content_type=original_metadata.content_type,
            metadata=original_metadata.metadata
        )
        
        # Save extended metadata
        version_metadata = VersionMetadata(
            version_id=new_metadata.version_id or "null",
            key=key,
            size=new_metadata.size,
            etag=new_metadata.etag,
            last_modified=new_metadata.last_modified,
            is_latest=True,
            created_by=created_by,
            comment=comment or f"Rolled back to version {version_id}",
            tags={'rollback_from': version_id}
        )
        
        self._save_version_metadata(version_metadata)
        
        self.logger.info(f"Rolled back {key} to version {version_id}")
        return version_metadata
    
    def tag_version(
        self,
        key: str,
        version_id: str,
        tags: Dict[str, str]
    ):
        """
        Add tags to a version.
        
        Args:
            key: Object key
            version_id: Version identifier
            tags: Tags to add
        """
        version_metadata = self._load_version_metadata(key, version_id)
        
        if not version_metadata:
            # Create new metadata
            storage_version = self.storage.get_metadata(key, version_id=version_id)
            version_metadata = VersionMetadata(
                version_id=version_id,
                key=key,
                size=storage_version.size,
                etag=storage_version.etag,
                last_modified=storage_version.last_modified,
                is_latest=False,
                tags=tags
            )
        else:
            # Update tags
            if version_metadata.tags:
                version_metadata.tags.update(tags)
            else:
                version_metadata.tags = tags
        
        self._save_version_metadata(version_metadata)
    
    def add_comment(
        self,
        key: str,
        version_id: str,
        comment: str,
        created_by: Optional[str] = None
    ):
        """
        Add comment to a version.
        
        Args:
            key: Object key
            version_id: Version identifier
            comment: Comment text
            created_by: User adding comment
        """
        version_metadata = self._load_version_metadata(key, version_id)
        
        if not version_metadata:
            # Create new metadata
            storage_version = self.storage.get_metadata(key, version_id=version_id)
            version_metadata = VersionMetadata(
                version_id=version_id,
                key=key,
                size=storage_version.size,
                etag=storage_version.etag,
                last_modified=storage_version.last_modified,
                is_latest=False,
                comment=comment,
                created_by=created_by
            )
        else:
            # Update comment
            version_metadata.comment = comment
            if created_by:
                version_metadata.created_by = created_by
        
        self._save_version_metadata(version_metadata)
    
    def compare_versions(
        self,
        key: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two versions of an object.
        
        Args:
            key: Object key
            version1: First version
            version2: Second version
            
        Returns:
            Comparison result
        """
        # Get metadata for both versions
        meta1 = self.storage.get_metadata(key, version_id=version1)
        meta2 = self.storage.get_metadata(key, version_id=version2)
        
        # Calculate differences
        size_diff = meta2.size - meta1.size
        time_diff = (meta2.last_modified - meta1.last_modified).total_seconds()
        
        return {
            'key': key,
            'version1': {
                'version_id': version1,
                'size': meta1.size,
                'etag': meta1.etag,
                'last_modified': meta1.last_modified.isoformat()
            },
            'version2': {
                'version_id': version2,
                'size': meta2.size,
                'etag': meta2.etag,
                'last_modified': meta2.last_modified.isoformat()
            },
            'differences': {
                'size_diff': size_diff,
                'size_change_pct': (size_diff / meta1.size * 100) if meta1.size > 0 else 0,
                'time_diff_seconds': time_diff,
                'content_changed': meta1.etag != meta2.etag
            }
        }
    
    def prune_versions(
        self,
        key: str,
        keep_count: int = 5,
        keep_tagged: bool = True
    ) -> int:
        """
        Remove old versions based on retention policy.
        
        Args:
            key: Object key
            keep_count: Number of versions to keep
            keep_tagged: Keep tagged versions regardless of age
            
        Returns:
            Number of versions deleted
        """
        versions = self.list_versions(key)
        
        if len(versions) <= keep_count:
            return 0
        
        deleted_count = 0
        
        for version in versions[keep_count:]:
            # Skip tagged versions if keep_tagged is True
            if keep_tagged and version.tags:
                continue
            
            # Delete version
            self.storage.delete_object(key, version_id=version.version_id)
            
            # Delete extended metadata
            metadata_path = self._get_version_metadata_path(key, version.version_id)
            if metadata_path.exists():
                metadata_path.unlink()
            
            deleted_count += 1
        
        self.logger.info(f"Pruned {deleted_count} versions of {key}")
        return deleted_count
    
    def get_version_history(
        self,
        key: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get version history with changes.
        
        Args:
            key: Object key
            limit: Maximum history entries
            
        Returns:
            List of version history entries
        """
        versions = self.list_versions(key, limit=limit)
        
        history = []
        for idx, version in enumerate(versions):
            entry = {
                'version_id': version.version_id,
                'timestamp': version.last_modified.isoformat(),
                'size': version.size,
                'etag': version.etag,
                'is_latest': version.is_latest,
                'created_by': version.created_by,
                'comment': version.comment,
                'tags': version.tags
            }
            
            # Add comparison with previous version
            if idx < len(versions) - 1:
                prev_version = versions[idx + 1]
                size_diff = version.size - prev_version.size
                time_diff = (version.last_modified - prev_version.last_modified).total_seconds()
                
                entry['changes'] = {
                    'size_diff': size_diff,
                    'time_since_previous': time_diff,
                    'content_changed': version.etag != prev_version.etag
                }
            
            history.append(entry)
        
        return history
    
    def _save_version_metadata(self, version_metadata: VersionMetadata):
        """Save extended version metadata."""
        metadata_path = self._get_version_metadata_path(
            version_metadata.key,
            version_metadata.version_id
        )
        
        with open(metadata_path, 'w') as f:
            json.dump(version_metadata.to_dict(), f, indent=2)
    
    def _load_version_metadata(
        self,
        key: str,
        version_id: str
    ) -> Optional[VersionMetadata]:
        """Load extended version metadata."""
        metadata_path = self._get_version_metadata_path(key, version_id)
        
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r') as f:
                data = json.load(f)
            return VersionMetadata.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load version metadata: {e}")
            return None
