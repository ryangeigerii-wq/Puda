"""
Storage API Layer

FastAPI-based REST API for storage operations, webhook triggers, and analytics.
Provides secure access to storage backends with authentication and monitoring.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import json

try:
    from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query, Header, Request
    from fastapi.responses import StreamingResponse, JSONResponse, Response
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("Warning: FastAPI not installed. Install via: pip install fastapi uvicorn")

from .storage_interface import StorageBackend
from .s3_storage import S3StorageManager
from .local_storage import LocalStorageManager
from .version_manager import VersionManager
from .integration_hooks import IntegrationHookManager, HookEvent

try:
    from .postgres_storage import PostgreSQLStorageDB
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


# Pydantic Models for Request/Response

class ObjectMetadataRequest(BaseModel):
    """Request model for object metadata."""
    metadata: Dict[str, str] = Field(default_factory=dict, description="Custom metadata key-value pairs")
    content_type: Optional[str] = Field(None, description="MIME type of the object")
    storage_class: Optional[str] = Field(None, description="Storage class (STANDARD, GLACIER, etc.)")


class ObjectUploadResponse(BaseModel):
    """Response model for object upload."""
    object_key: str
    size: int
    etag: str
    version_id: Optional[str] = None
    content_type: str
    upload_time: str


class ObjectMetadataResponse(BaseModel):
    """Response model for object metadata."""
    key: str
    size: int
    content_type: str
    etag: str
    last_modified: str
    version_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    storage_class: Optional[str] = None


class VersionInfoResponse(BaseModel):
    """Response model for version information."""
    version_id: str
    is_latest: bool
    last_modified: str
    size: int
    etag: str
    created_by: Optional[str] = None
    comment: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class SearchRequest(BaseModel):
    """Request model for search operations."""
    query: Optional[str] = Field(None, description="Full-text search query")
    prefix: Optional[str] = Field(None, description="Key prefix filter")
    storage_backend: Optional[str] = Field(None, description="Filter by storage backend")
    metadata_filters: Optional[Dict[str, str]] = Field(None, description="Metadata filters")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class WebhookRequest(BaseModel):
    """Request model for webhook registration."""
    name: str = Field(..., description="Unique webhook name")
    url: str = Field(..., description="Webhook URL")
    method: str = Field("POST", description="HTTP method (POST or PUT)")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers")
    events: List[str] = Field(..., description="List of events to trigger on")
    retry_count: int = Field(3, ge=0, le=10, description="Number of retries on failure")
    timeout: int = Field(30, ge=1, le=300, description="Request timeout in seconds")


class AnalyticsResponse(BaseModel):
    """Response model for analytics."""
    total_objects: int
    total_size: int
    total_versions: int
    storage_backends: Dict[str, Dict[str, Any]]
    recent_uploads: int
    recent_downloads: int
    recent_audits: int
    hook_statistics: List[Dict[str, Any]]


class AuditLogResponse(BaseModel):
    """Response model for audit logs."""
    timestamp: str
    user_id: Optional[str]
    username: Optional[str]
    action: str
    object_key: Optional[str]
    version_id: Optional[str]
    ip_address: Optional[str]
    success: bool
    error_message: Optional[str]


# Storage API Application

class StorageAPI:
    """
    FastAPI application for storage operations.
    
    Features:
    - RESTful API for storage CRUD operations
    - Webhook management
    - Analytics and monitoring
    - Audit trail queries
    - Version management
    - PostgreSQL metadata integration
    """
    
    def __init__(
        self,
        storage_backend: str = "local",
        storage_path: str = "data/storage",
        enable_postgres: bool = True,
        postgres_config: Optional[Dict[str, Any]] = None,
        enable_webhooks: bool = True,
        api_key: Optional[str] = None
    ):
        """
        Initialize Storage API.
        
        Args:
            storage_backend: "local" or "s3"
            storage_path: Path for local storage or S3 bucket name
            enable_postgres: Enable PostgreSQL metadata storage
            postgres_config: PostgreSQL connection config
            enable_webhooks: Enable webhook functionality
            api_key: API key for authentication (optional)
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI not installed. Install via: pip install fastapi uvicorn")
        
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or os.getenv("STORAGE_API_KEY")
        
        # Initialize storage backend
        if storage_backend == "local":
            self.storage = LocalStorageManager(
                base_path=storage_path,
                enable_versioning=True
            )
        else:  # s3
            self.storage = S3StorageManager(
                bucket_name=storage_path,
                endpoint_url=os.getenv("S3_ENDPOINT"),
                aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
                enable_versioning=True
            )
        
        # Initialize version manager
        self.version_manager = VersionManager(self.storage)
        
        # Initialize PostgreSQL (if available and enabled)
        self.db = None
        if enable_postgres and POSTGRES_AVAILABLE:
            pg_config = postgres_config or {}
            try:
                self.db = PostgreSQLStorageDB(
                    host=pg_config.get("host", os.getenv("POSTGRES_HOST", "localhost")),
                    port=pg_config.get("port", int(os.getenv("POSTGRES_PORT", 5432))),
                    database=pg_config.get("database", os.getenv("POSTGRES_DB", "puda_storage")),
                    user=pg_config.get("user", os.getenv("POSTGRES_USER", "puda")),
                    password=pg_config.get("password", os.getenv("POSTGRES_PASSWORD", "puda"))
                )
                self.logger.info("PostgreSQL metadata storage enabled")
            except Exception as e:
                self.logger.warning(f"PostgreSQL not available: {e}")
        
        # Initialize webhook manager
        self.hook_manager = None
        if enable_webhooks:
            self.hook_manager = IntegrationHookManager(async_execution=True)
            self.logger.info("Webhook integration enabled")
        
        # Create FastAPI app
        self.app = self._create_app()
    
    def _verify_api_key(self, x_api_key: Optional[str] = Header(None)):
        """Verify API key if authentication is enabled."""
        if self.api_key and x_api_key != self.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return True
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        app = FastAPI(
            title="Storage API",
            description="RESTful API for storage operations with webhooks and analytics",
            version="1.0.0"
        )
        
        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Health check endpoint
        @app.get("/health", tags=["Health"])
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "storage_backend": self.storage.get_storage_info()["backend"].value,
                "postgres_enabled": self.db is not None,
                "webhooks_enabled": self.hook_manager is not None
            }
        
        # Storage Info
        @app.get("/api/storage/info", tags=["Storage"])
        async def get_storage_info(authenticated: bool = Depends(self._verify_api_key)):
            """Get storage backend information."""
            info = self.storage.get_storage_info()
            return {
                "backend": info["backend"].value,
                "versioning_enabled": info["versioning_enabled"],
                "additional_info": info["info"]
            }
        
        # Upload Object
        @app.post("/api/storage/objects", response_model=ObjectUploadResponse, tags=["Objects"])
        async def upload_object(
            key: str = Query(..., description="Object key/path"),
            file: UploadFile = File(...),
            metadata: Optional[str] = Query(None, description="JSON metadata"),
            storage_class: Optional[str] = Query(None, description="Storage class"),
            authenticated: bool = Depends(self._verify_api_key),
            request: Request = None
        ):
            """Upload object to storage."""
            try:
                # Read file data
                data = await file.read()
                
                # Parse metadata
                meta_dict = json.loads(metadata) if metadata else {}
                
                # Upload to storage
                result = self.storage.put_object(
                    key=key,
                    data=data,
                    content_type=file.content_type or "application/octet-stream",
                    metadata=meta_dict,
                    storage_class=storage_class
                )
                
                # Record in PostgreSQL
                if self.db:
                    self.db.record_object(
                        object_key=key,
                        size=len(data),
                        content_type=file.content_type or "application/octet-stream",
                        etag=result.etag,
                        version_id=result.version_id,
                        storage_backend=self.storage.get_storage_info()["backend"].value,
                        storage_class=storage_class,
                        metadata=meta_dict
                    )
                    
                    # Log audit
                    self.db.log_audit(
                        action="UPLOAD",
                        object_key=key,
                        version_id=result.version_id,
                        ip_address=request.client.host if request else None,
                        success=True,
                        metadata={"size": len(data), "content_type": file.content_type}
                    )
                
                # Fire webhook
                if self.hook_manager:
                    self.hook_manager.fire_event(
                        event=HookEvent.DOCUMENT_ARCHIVED,
                        data={
                            "object_key": key,
                            "size": len(data),
                            "version_id": result.version_id,
                            "content_type": file.content_type
                        }
                    )
                
                return ObjectUploadResponse(
                    object_key=key,
                    size=len(data),
                    etag=result.etag,
                    version_id=result.version_id,
                    content_type=file.content_type or "application/octet-stream",
                    upload_time=datetime.now().isoformat()
                )
            
            except Exception as e:
                self.logger.error(f"Upload failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Download Object
        @app.get("/api/storage/objects/{key:path}", tags=["Objects"])
        async def download_object(
            key: str,
            version_id: Optional[str] = Query(None, description="Specific version ID"),
            authenticated: bool = Depends(self._verify_api_key),
            request: Request = None
        ):
            """Download object from storage."""
            try:
                # Get object data
                data = self.storage.get_object(key, version_id=version_id)
                
                # Get metadata
                metadata = self.storage.get_metadata(key, version_id=version_id)
                
                # Log audit
                if self.db:
                    self.db.log_audit(
                        action="DOWNLOAD",
                        object_key=key,
                        version_id=version_id,
                        ip_address=request.client.host if request else None,
                        success=True,
                        metadata={"size": len(data)}
                    )
                
                # Fire webhook
                if self.hook_manager:
                    self.hook_manager.fire_event(
                        event=HookEvent.DOCUMENT_RETRIEVED,
                        data={"object_key": key, "version_id": version_id, "size": len(data)}
                    )
                
                return Response(
                    content=data,
                    media_type=metadata.content_type,
                    headers={
                        "Content-Disposition": f'attachment; filename="{Path(key).name}"',
                        "ETag": metadata.etag,
                        "X-Version-ID": metadata.version_id or ""
                    }
                )
            
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail=f"Object not found: {key}")
            except Exception as e:
                self.logger.error(f"Download failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Get Object Metadata
        @app.get("/api/storage/objects/{key:path}/metadata", response_model=ObjectMetadataResponse, tags=["Objects"])
        async def get_object_metadata(
            key: str,
            version_id: Optional[str] = Query(None, description="Specific version ID"),
            authenticated: bool = Depends(self._verify_api_key)
        ):
            """Get object metadata."""
            try:
                if self.db:
                    # Get from PostgreSQL
                    meta = self.db.get_object_metadata(key)
                    if meta:
                        return ObjectMetadataResponse(
                            key=meta["object_key"],
                            size=meta["size"],
                            content_type=meta["content_type"],
                            etag=meta["etag"],
                            last_modified=meta["last_modified"].isoformat(),
                            version_id=meta.get("version_id"),
                            metadata=meta.get("metadata"),
                            storage_class=meta.get("storage_class")
                        )
                
                # Fallback to storage backend
                metadata = self.storage.get_metadata(key, version_id=version_id)
                return ObjectMetadataResponse(
                    key=metadata.key,
                    size=metadata.size,
                    content_type=metadata.content_type,
                    etag=metadata.etag,
                    last_modified=metadata.last_modified.isoformat(),
                    version_id=metadata.version_id,
                    metadata=metadata.metadata,
                    storage_class=metadata.storage_class
                )
            
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail=f"Object not found: {key}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Delete Object
        @app.delete("/api/storage/objects/{key:path}", tags=["Objects"])
        async def delete_object(
            key: str,
            version_id: Optional[str] = Query(None, description="Specific version to delete"),
            authenticated: bool = Depends(self._verify_api_key),
            request: Request = None
        ):
            """Delete object from storage."""
            try:
                self.storage.delete_object(key, version_id=version_id)
                
                # Update PostgreSQL
                if self.db:
                    if version_id:
                        # Delete specific version
                        pass  # PostgreSQL tracks versions separately
                    else:
                        # Delete object metadata
                        self.db.delete_object(key)
                    
                    # Log audit
                    self.db.log_audit(
                        action="DELETE",
                        object_key=key,
                        version_id=version_id,
                        ip_address=request.client.host if request else None,
                        success=True
                    )
                
                # Fire webhook
                if self.hook_manager:
                    self.hook_manager.fire_event(
                        event=HookEvent.DOCUMENT_DELETED,
                        data={"object_key": key, "version_id": version_id}
                    )
                
                return {"status": "deleted", "object_key": key, "version_id": version_id}
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # List Objects
        @app.get("/api/storage/objects", tags=["Objects"])
        async def list_objects(
            prefix: Optional[str] = Query(None, description="Key prefix filter"),
            storage_backend: Optional[str] = Query(None, description="Filter by backend"),
            limit: int = Query(100, ge=1, le=1000),
            offset: int = Query(0, ge=0),
            authenticated: bool = Depends(self._verify_api_key)
        ):
            """List objects with filters."""
            try:
                if self.db:
                    # Use PostgreSQL for listing
                    objects = self.db.list_objects(
                        prefix=prefix,
                        storage_backend=storage_backend,
                        limit=limit,
                        offset=offset
                    )
                    return {"objects": objects, "count": len(objects)}
                else:
                    # Use storage backend
                    objects = self.storage.list_objects(prefix=prefix or "")
                    # Apply pagination
                    paginated = objects[offset:offset+limit]
                    return {"objects": [obj.key for obj in paginated], "count": len(paginated)}
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Search Objects (PostgreSQL only)
        @app.post("/api/storage/search", tags=["Search"])
        async def search_objects(
            search: SearchRequest,
            authenticated: bool = Depends(self._verify_api_key)
        ):
            """Search objects using full-text search (PostgreSQL required)."""
            if not self.db:
                raise HTTPException(status_code=501, detail="Search requires PostgreSQL")
            
            try:
                if search.query:
                    # Full-text search
                    results = self.db.search_objects(search.query, limit=search.limit)
                else:
                    # List with filters
                    results = self.db.list_objects(
                        prefix=search.prefix,
                        storage_backend=search.storage_backend,
                        limit=search.limit,
                        offset=search.offset
                    )
                
                return {"results": results, "count": len(results)}
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Version Management
        @app.get("/api/storage/objects/{key:path}/versions", response_model=List[VersionInfoResponse], tags=["Versions"])
        async def list_versions(
            key: str,
            limit: int = Query(100, ge=1, le=1000),
            authenticated: bool = Depends(self._verify_api_key)
        ):
            """List all versions of an object."""
            try:
                if self.db:
                    versions = self.db.list_versions(key, limit=limit)
                    return [
                        VersionInfoResponse(
                            version_id=v["version_id"],
                            is_latest=v["is_latest"],
                            last_modified=v["last_modified"].isoformat(),
                            size=v["size"],
                            etag=v["etag"],
                            created_by=v.get("created_by"),
                            comment=v.get("comment"),
                            tags=v.get("tags")
                        )
                        for v in versions
                    ]
                else:
                    versions = self.storage.list_versions(key)
                    return [
                        VersionInfoResponse(
                            version_id=v.version_id,
                            is_latest=v.is_latest,
                            last_modified=v.last_modified.isoformat(),
                            size=v.size,
                            etag=v.etag
                        )
                        for v in versions
                    ]
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Rollback Version
        @app.post("/api/storage/objects/{key:path}/rollback", tags=["Versions"])
        async def rollback_version(
            key: str,
            version_id: str = Query(..., description="Version to rollback to"),
            comment: Optional[str] = Query(None, description="Rollback comment"),
            authenticated: bool = Depends(self._verify_api_key),
            request: Request = None
        ):
            """Rollback object to a previous version."""
            try:
                result = self.version_manager.rollback(key, version_id, comment=comment)
                
                # Fire webhook
                if self.hook_manager:
                    self.hook_manager.fire_event(
                        event=HookEvent.VERSION_ROLLED_BACK,
                        data={
                            "object_key": key,
                            "old_version": version_id,
                            "new_version": result.version_id
                        }
                    )
                
                return {
                    "status": "rolled_back",
                    "object_key": key,
                    "new_version": result.version_id,
                    "comment": comment
                }
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Webhook Management
        @app.post("/api/webhooks", tags=["Webhooks"])
        async def register_webhook(
            webhook: WebhookRequest,
            authenticated: bool = Depends(self._verify_api_key)
        ):
            """Register a new webhook."""
            if not self.hook_manager:
                raise HTTPException(status_code=501, detail="Webhooks not enabled")
            
            try:
                from .integration_hooks import WebhookHook
                
                hook = WebhookHook(
                    name=webhook.name,
                    url=webhook.url,
                    method=webhook.method,
                    headers=webhook.headers,
                    retry_count=webhook.retry_count,
                    timeout=webhook.timeout,
                    events=[HookEvent[e] for e in webhook.events]
                )
                
                self.hook_manager.register_hook(hook)
                
                return {"status": "registered", "webhook": webhook.name}
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # List Webhooks
        @app.get("/api/webhooks", tags=["Webhooks"])
        async def list_webhooks(authenticated: bool = Depends(self._verify_api_key)):
            """List all registered webhooks."""
            if not self.hook_manager:
                raise HTTPException(status_code=501, detail="Webhooks not enabled")
            
            try:
                hooks = self.hook_manager.list_hooks()
                return {"webhooks": hooks}
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Analytics
        @app.get("/api/analytics", response_model=AnalyticsResponse, tags=["Analytics"])
        async def get_analytics(
            hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
            authenticated: bool = Depends(self._verify_api_key)
        ):
            """Get storage analytics and statistics."""
            try:
                analytics = {
                    "total_objects": 0,
                    "total_size": 0,
                    "total_versions": 0,
                    "storage_backends": {},
                    "recent_uploads": 0,
                    "recent_downloads": 0,
                    "recent_audits": 0,
                    "hook_statistics": []
                }
                
                if self.db:
                    stats = self.db.get_statistics()
                    
                    # Process object statistics
                    if stats.get('objects'):
                        for obj_stat in stats['objects']:
                            if isinstance(obj_stat, tuple):
                                total, size, backend, count = obj_stat
                                analytics["total_objects"] += total
                                analytics["total_size"] += size or 0
                                analytics["storage_backends"][backend] = {
                                    "object_count": total,
                                    "total_size": size or 0
                                }
                    
                    analytics["total_versions"] = stats.get("total_versions", 0)
                    analytics["recent_audits"] = stats.get("recent_audits_24h", 0)
                    
                    # Get audit statistics for uploads/downloads
                    cutoff = datetime.now() - timedelta(hours=hours)
                    logs = self.db.get_audit_logs(start_date=cutoff, limit=10000)
                    analytics["recent_uploads"] = sum(1 for log in logs if log.get("action") == "UPLOAD")
                    analytics["recent_downloads"] = sum(1 for log in logs if log.get("action") == "DOWNLOAD")
                    
                    # Hook statistics
                    if self.hook_manager:
                        hook_stats = self.db.get_hook_statistics(hours=hours)
                        analytics["hook_statistics"] = hook_stats
                
                return analytics
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Audit Logs
        @app.get("/api/audit", response_model=List[AuditLogResponse], tags=["Audit"])
        async def get_audit_logs(
            object_key: Optional[str] = Query(None, description="Filter by object key"),
            user_id: Optional[str] = Query(None, description="Filter by user ID"),
            action: Optional[str] = Query(None, description="Filter by action"),
            hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
            limit: int = Query(100, ge=1, le=1000),
            authenticated: bool = Depends(self._verify_api_key)
        ):
            """Query audit logs."""
            if not self.db:
                raise HTTPException(status_code=501, detail="Audit logs require PostgreSQL")
            
            try:
                cutoff = datetime.now() - timedelta(hours=hours)
                logs = self.db.get_audit_logs(
                    object_key=object_key,
                    user_id=user_id,
                    action=action,
                    start_date=cutoff,
                    limit=limit
                )
                
                return [
                    AuditLogResponse(
                        timestamp=log["timestamp"].isoformat(),
                        user_id=log.get("user_id"),
                        username=log.get("username"),
                        action=log["action"],
                        object_key=log.get("object_key"),
                        version_id=log.get("version_id"),
                        ip_address=log.get("ip_address"),
                        success=log["success"],
                        error_message=log.get("error_message")
                    )
                    for log in logs
                ]
            
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        return app
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the API server."""
        try:
            import uvicorn
            uvicorn.run(self.app, host=host, port=port)
        except ImportError:
            raise ImportError("uvicorn not installed. Install via: pip install uvicorn")


def create_app(
    storage_backend: str = "local",
    storage_path: str = "data/storage",
    enable_postgres: bool = True,
    enable_webhooks: bool = True,
    api_key: Optional[str] = None
) -> FastAPI:
    """
    Factory function to create Storage API app.
    
    Usage:
        app = create_app()
        # Run with: uvicorn storage_api:app --reload
    """
    api = StorageAPI(
        storage_backend=storage_backend,
        storage_path=storage_path,
        enable_postgres=enable_postgres,
        enable_webhooks=enable_webhooks,
        api_key=api_key
    )
    return api.app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Storage API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--backend", choices=["local", "s3"], default="local", help="Storage backend")
    parser.add_argument("--path", default="data/storage", help="Storage path or bucket name")
    parser.add_argument("--no-postgres", action="store_true", help="Disable PostgreSQL")
    parser.add_argument("--no-webhooks", action="store_true", help="Disable webhooks")
    parser.add_argument("--api-key", help="API key for authentication")
    
    args = parser.parse_args()
    
    api = StorageAPI(
        storage_backend=args.backend,
        storage_path=args.path,
        enable_postgres=not args.no_postgres,
        enable_webhooks=not args.no_webhooks,
        api_key=args.api_key
    )
    
    print(f"Starting Storage API on {args.host}:{args.port}")
    print(f"Storage backend: {args.backend}")
    print(f"PostgreSQL: {'enabled' if not args.no_postgres else 'disabled'}")
    print(f"Webhooks: {'enabled' if not args.no_webhooks else 'disabled'}")
    print(f"API docs: http://{args.host}:{args.port}/docs")
    
    api.run(host=args.host, port=args.port)
