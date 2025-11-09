"""
S3-Compatible Storage Manager

Supports AWS S3, MinIO, Wasabi, Backblaze B2, and other S3-compatible services.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, BinaryIO
import logging

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    from botocore.config import Config
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

from .storage_interface import (
    StorageInterface,
    StorageBackend,
    StorageMetadata,
    VersionInfo
)


class S3StorageManager(StorageInterface):
    """
    S3-compatible storage manager.
    
    Features:
    - Versioning support
    - Server-side encryption (SSE-S3, SSE-KMS)
    - Multipart uploads for large files
    - Presigned URLs
    - Storage classes (STANDARD, INTELLIGENT_TIERING, GLACIER)
    - Cross-region replication compatible
    
    Configuration:
        AWS S3:
            endpoint_url=None (uses AWS defaults)
        MinIO:
            endpoint_url="http://localhost:9000"
        Wasabi:
            endpoint_url="https://s3.wasabisys.com"
        Backblaze B2:
            endpoint_url="https://s3.us-west-000.backblazeb2.com"
    """
    
    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        enable_versioning: bool = True,
        storage_class: str = "STANDARD",
        encryption: str = "AES256"
    ):
        """
        Initialize S3 storage manager.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region (e.g., us-east-1)
            endpoint_url: Custom S3 endpoint (None = AWS S3)
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            enable_versioning: Enable bucket versioning
            storage_class: Default storage class
            encryption: Server-side encryption (AES256 or aws:kms)
        """
        if not S3_AVAILABLE:
            raise ImportError("boto3 not installed. Install via: pip install boto3")
        
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url
        self.storage_class = storage_class
        self.encryption = encryption
        self.logger = logging.getLogger(__name__)
        
        # Configure boto3 client
        config = Config(
            region_name=region,
            signature_version='s3v4',
            retries={'max_attempts': 3, 'mode': 'standard'}
        )
        
        # Create S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=config
        )
        
        # Create bucket if it doesn't exist
        self._ensure_bucket_exists()
        
        # Enable versioning if requested
        if enable_versioning:
            self._enable_versioning()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.logger.info(f"Bucket exists: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    self.logger.info(f"Created bucket: {self.bucket_name}")
                except ClientError as create_error:
                    self.logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                raise
    
    def _enable_versioning(self):
        """Enable versioning on bucket."""
        try:
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            self.logger.info(f"Versioning enabled: {self.bucket_name}")
        except ClientError as e:
            self.logger.warning(f"Failed to enable versioning: {e}")
    
    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageMetadata:
        """Store an object in S3."""
        try:
            # Prepare put_object parameters
            put_params = {
                'Bucket': self.bucket_name,
                'Key': key,
                'Body': data,
                'ContentType': content_type,
                'StorageClass': self.storage_class,
                'ServerSideEncryption': self.encryption
            }
            
            if metadata:
                put_params['Metadata'] = metadata
            
            # Upload object
            response = self.s3_client.put_object(**put_params)
            
            # Return metadata
            return StorageMetadata(
                key=key,
                size=len(data),
                content_type=content_type,
                etag=response['ETag'].strip('"'),
                last_modified=datetime.now(),
                version_id=response.get('VersionId'),
                metadata=metadata,
                storage_class=self.storage_class
            )
        except ClientError as e:
            self.logger.error(f"Failed to put object {key}: {e}")
            raise
    
    def get_object(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> bytes:
        """Retrieve an object from S3."""
        try:
            get_params = {
                'Bucket': self.bucket_name,
                'Key': key
            }
            
            if version_id:
                get_params['VersionId'] = version_id
            
            response = self.s3_client.get_object(**get_params)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"Object not found: {key}")
            self.logger.error(f"Failed to get object {key}: {e}")
            raise
    
    def delete_object(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> bool:
        """Delete an object or version from S3."""
        try:
            delete_params = {
                'Bucket': self.bucket_name,
                'Key': key
            }
            
            if version_id:
                delete_params['VersionId'] = version_id
            
            self.s3_client.delete_object(**delete_params)
            return True
        except ClientError as e:
            self.logger.error(f"Failed to delete object {key}: {e}")
            return False
    
    def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000
    ) -> List[StorageMetadata]:
        """List objects in S3 bucket."""
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                PaginationConfig={'MaxItems': max_keys}
            )
            
            objects = []
            for page in pages:
                for obj in page.get('Contents', []):
                    objects.append(StorageMetadata(
                        key=obj['Key'],
                        size=obj['Size'],
                        content_type='',  # Not available in list
                        etag=obj['ETag'].strip('"'),
                        last_modified=obj['LastModified'],
                        version_id=None,  # Use list_object_versions for versions
                        metadata=None,
                        storage_class=obj.get('StorageClass', 'STANDARD')
                    ))
            
            return objects
        except ClientError as e:
            self.logger.error(f"Failed to list objects: {e}")
            raise
    
    def get_metadata(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> StorageMetadata:
        """Get object metadata from S3."""
        try:
            head_params = {
                'Bucket': self.bucket_name,
                'Key': key
            }
            
            if version_id:
                head_params['VersionId'] = version_id
            
            response = self.s3_client.head_object(**head_params)
            
            return StorageMetadata(
                key=key,
                size=response['ContentLength'],
                content_type=response['ContentType'],
                etag=response['ETag'].strip('"'),
                last_modified=response['LastModified'],
                version_id=response.get('VersionId'),
                metadata=response.get('Metadata'),
                storage_class=response.get('StorageClass', 'STANDARD')
            )
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"Object not found: {key}")
            self.logger.error(f"Failed to get metadata for {key}: {e}")
            raise
    
    def list_versions(
        self,
        key: str
    ) -> List[VersionInfo]:
        """List all versions of an object."""
        try:
            response = self.s3_client.list_object_versions(
                Bucket=self.bucket_name,
                Prefix=key
            )
            
            versions = []
            for version in response.get('Versions', []):
                if version['Key'] == key:  # Exact match
                    versions.append(VersionInfo(
                        version_id=version['VersionId'],
                        is_latest=version['IsLatest'],
                        last_modified=version['LastModified'],
                        size=version['Size'],
                        etag=version['ETag'].strip('"')
                    ))
            
            # Sort by last modified, newest first
            versions.sort(key=lambda v: v.last_modified, reverse=True)
            return versions
        except ClientError as e:
            self.logger.error(f"Failed to list versions for {key}: {e}")
            raise
    
    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageMetadata:
        """Copy an object within S3."""
        try:
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_key
            }
            
            copy_params = {
                'Bucket': self.bucket_name,
                'CopySource': copy_source,
                'Key': dest_key,
                'StorageClass': self.storage_class,
                'ServerSideEncryption': self.encryption
            }
            
            if metadata:
                copy_params['Metadata'] = metadata
                copy_params['MetadataDirective'] = 'REPLACE'
            
            response = self.s3_client.copy_object(**copy_params)
            
            # Get full metadata of destination
            return self.get_metadata(dest_key)
        except ClientError as e:
            self.logger.error(f"Failed to copy {source_key} to {dest_key}: {e}")
            raise
    
    def exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def get_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> str:
        """Generate presigned URL for object access."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            self.logger.error(f"Failed to generate URL for {key}: {e}")
            raise
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get S3 storage information."""
        try:
            # Get bucket versioning status
            versioning = self.s3_client.get_bucket_versioning(Bucket=self.bucket_name)
            
            # Get bucket location
            location = self.s3_client.get_bucket_location(Bucket=self.bucket_name)
            
            return {
                'backend': StorageBackend.S3.value,
                'bucket': self.bucket_name,
                'region': location.get('LocationConstraint', 'us-east-1'),
                'endpoint': self.endpoint_url or 'AWS S3',
                'versioning': versioning.get('Status', 'Disabled'),
                'storage_class': self.storage_class,
                'encryption': self.encryption
            }
        except ClientError as e:
            self.logger.error(f"Failed to get storage info: {e}")
            return {
                'backend': StorageBackend.S3.value,
                'bucket': self.bucket_name,
                'error': str(e)
            }
    
    def upload_file(
        self,
        file_path: Path,
        key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageMetadata:
        """
        Upload a file to S3 with automatic multipart for large files.
        
        Args:
            file_path: Local file path
            key: S3 object key
            metadata: Custom metadata
            
        Returns:
            StorageMetadata
        """
        try:
            # Determine content type
            import mimetypes
            content_type, _ = mimetypes.guess_type(str(file_path))
            content_type = content_type or 'application/octet-stream'
            
            # Prepare upload parameters
            extra_args = {
                'ContentType': content_type,
                'StorageClass': self.storage_class,
                'ServerSideEncryption': self.encryption
            }
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload file (boto3 automatically uses multipart for large files)
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )
            
            # Get metadata
            return self.get_metadata(key)
        except ClientError as e:
            self.logger.error(f"Failed to upload file {file_path}: {e}")
            raise
    
    def download_file(
        self,
        key: str,
        file_path: Path,
        version_id: Optional[str] = None
    ):
        """
        Download S3 object to local file.
        
        Args:
            key: S3 object key
            file_path: Local destination path
            version_id: Specific version
        """
        try:
            extra_args = {}
            if version_id:
                extra_args['VersionId'] = version_id
            
            self.s3_client.download_file(
                self.bucket_name,
                key,
                str(file_path),
                ExtraArgs=extra_args if extra_args else None
            )
        except ClientError as e:
            self.logger.error(f"Failed to download {key}: {e}")
            raise
