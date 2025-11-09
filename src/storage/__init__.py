"""
Storage Layer

Provides persistent archive storage with S3-compatible backends,
versioning, and integration hooks for external systems.
"""

from .s3_storage import S3StorageManager
from .local_storage import LocalStorageManager
from .storage_interface import StorageInterface, StorageBackend
from .version_manager import VersionManager
from .integration_hooks import IntegrationHookManager, HookEvent, HookResult
from .postgres_storage import PostgreSQLStorageDB
from .storage_api import StorageAPI, create_app

__all__ = [
    'S3StorageManager',
    'LocalStorageManager',
    'StorageInterface',
    'StorageBackend',
    'VersionManager',
    'IntegrationHookManager',
    'HookEvent',
    'HookResult',
    'PostgreSQLStorageDB',
    'StorageAPI',
    'create_app'
]
