#!/usr/bin/env python3
"""
Storage API Test Client

Demonstrates usage of the Storage API with comprehensive examples.
"""

import requests
import json
import time
from pathlib import Path
from typing import Optional

class StorageAPIClient:
    """Client for interacting with Storage API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the API
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    def health_check(self) -> dict:
        """Check API health."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def get_storage_info(self) -> dict:
        """Get storage backend information."""
        response = requests.get(
            f"{self.base_url}/api/storage/info",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def upload_file(
        self,
        key: str,
        file_path: str,
        metadata: Optional[dict] = None,
        storage_class: Optional[str] = None
    ) -> dict:
        """
        Upload file to storage.
        
        Args:
            key: Object key/path
            file_path: Local file to upload
            metadata: Optional metadata dict
            storage_class: Optional storage class
        
        Returns:
            Upload response dict
        """
        params = {"key": key}
        if metadata:
            params["metadata"] = json.dumps(metadata)
        if storage_class:
            params["storage_class"] = storage_class
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                f"{self.base_url}/api/storage/objects",
                headers=self.headers,
                params=params,
                files=files
            )
        
        response.raise_for_status()
        return response.json()
    
    def download_file(
        self,
        key: str,
        output_path: str,
        version_id: Optional[str] = None
    ) -> dict:
        """
        Download file from storage.
        
        Args:
            key: Object key/path
            output_path: Local path to save file
            version_id: Optional specific version
        
        Returns:
            Response headers as dict
        """
        params = {}
        if version_id:
            params["version_id"] = version_id
        
        response = requests.get(
            f"{self.base_url}/api/storage/objects/{key}",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return {
            "etag": response.headers.get("ETag"),
            "version_id": response.headers.get("X-Version-ID"),
            "content_type": response.headers.get("Content-Type"),
            "size": len(response.content)
        }
    
    def get_metadata(self, key: str, version_id: Optional[str] = None) -> dict:
        """Get object metadata."""
        params = {}
        if version_id:
            params["version_id"] = version_id
        
        response = requests.get(
            f"{self.base_url}/api/storage/objects/{key}/metadata",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def delete_object(self, key: str, version_id: Optional[str] = None) -> dict:
        """Delete object."""
        params = {}
        if version_id:
            params["version_id"] = version_id
        
        response = requests.delete(
            f"{self.base_url}/api/storage/objects/{key}",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def list_objects(
        self,
        prefix: Optional[str] = None,
        storage_backend: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict:
        """List objects with filters."""
        params = {"limit": limit, "offset": offset}
        if prefix:
            params["prefix"] = prefix
        if storage_backend:
            params["storage_backend"] = storage_backend
        
        response = requests.get(
            f"{self.base_url}/api/storage/objects",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def search_objects(
        self,
        query: Optional[str] = None,
        prefix: Optional[str] = None,
        limit: int = 100
    ) -> dict:
        """Search objects (requires PostgreSQL)."""
        search_request = {
            "query": query,
            "prefix": prefix,
            "limit": limit
        }
        
        response = requests.post(
            f"{self.base_url}/api/storage/search",
            headers=self.headers,
            json=search_request
        )
        response.raise_for_status()
        return response.json()
    
    def list_versions(self, key: str, limit: int = 100) -> list:
        """List all versions of an object."""
        response = requests.get(
            f"{self.base_url}/api/storage/objects/{key}/versions",
            headers=self.headers,
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()
    
    def rollback_version(
        self,
        key: str,
        version_id: str,
        comment: Optional[str] = None
    ) -> dict:
        """Rollback object to previous version."""
        params = {"version_id": version_id}
        if comment:
            params["comment"] = comment
        
        response = requests.post(
            f"{self.base_url}/api/storage/objects/{key}/rollback",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def register_webhook(
        self,
        name: str,
        url: str,
        events: list,
        method: str = "POST",
        headers: Optional[dict] = None,
        retry_count: int = 3,
        timeout: int = 30
    ) -> dict:
        """Register webhook."""
        webhook = {
            "name": name,
            "url": url,
            "method": method,
            "headers": headers or {},
            "events": events,
            "retry_count": retry_count,
            "timeout": timeout
        }
        
        response = requests.post(
            f"{self.base_url}/api/webhooks",
            headers=self.headers,
            json=webhook
        )
        response.raise_for_status()
        return response.json()
    
    def list_webhooks(self) -> dict:
        """List registered webhooks."""
        response = requests.get(
            f"{self.base_url}/api/webhooks",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_analytics(self, hours: int = 24) -> dict:
        """Get storage analytics."""
        response = requests.get(
            f"{self.base_url}/api/analytics",
            headers=self.headers,
            params={"hours": hours}
        )
        response.raise_for_status()
        return response.json()
    
    def get_audit_logs(
        self,
        object_key: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> list:
        """Query audit logs."""
        params = {"hours": hours, "limit": limit}
        if object_key:
            params["object_key"] = object_key
        if user_id:
            params["user_id"] = user_id
        if action:
            params["action"] = action
        
        response = requests.get(
            f"{self.base_url}/api/audit",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()


def main():
    """Run API test examples."""
    print("=" * 70)
    print("Storage API Test Client")
    print("=" * 70)
    
    # Initialize client
    client = StorageAPIClient(
        base_url="http://localhost:8000",
        api_key=None  # Set API key if authentication is enabled
    )
    
    # Test 1: Health Check
    print("\n1. Health Check")
    print("-" * 70)
    try:
        health = client.health_check()
        print(f"Status: {health['status']}")
        print(f"Storage backend: {health['storage_backend']}")
        print(f"PostgreSQL: {'enabled' if health['postgres_enabled'] else 'disabled'}")
        print(f"Webhooks: {'enabled' if health['webhooks_enabled'] else 'disabled'}")
    except requests.exceptions.ConnectionError:
        print("❌ API server not running!")
        print("\nStart the server with:")
        print("  python -m src.storage.storage_api")
        print("  or")
        print("  uvicorn src.storage.storage_api:app --reload")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 2: Storage Info
    print("\n2. Storage Info")
    print("-" * 70)
    try:
        info = client.get_storage_info()
        print(f"Backend: {info['backend']}")
        print(f"Versioning: {info['versioning_enabled']}")
        print(f"Info: {info['additional_info']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Upload File
    print("\n3. Upload File")
    print("-" * 70)
    
    # Create test file
    test_file = "test_api_upload.txt"
    with open(test_file, "w") as f:
        f.write(f"Test file uploaded via API at {time.time()}\n")
        f.write("This is a test document for the Storage API.\n")
    
    try:
        result = client.upload_file(
            key="test/api/document.txt",
            file_path=test_file,
            metadata={
                "owner": "API Test",
                "department": "Engineering",
                "test": "true"
            }
        )
        print(f"✓ Uploaded: {result['object_key']}")
        print(f"  Size: {result['size']} bytes")
        print(f"  ETag: {result['etag']}")
        print(f"  Version: {result['version_id']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Get Metadata
    print("\n4. Get Metadata")
    print("-" * 70)
    try:
        metadata = client.get_metadata("test/api/document.txt")
        print(f"Key: {metadata['key']}")
        print(f"Size: {metadata['size']} bytes")
        print(f"Content-Type: {metadata['content_type']}")
        print(f"Last Modified: {metadata['last_modified']}")
        print(f"Metadata: {metadata.get('metadata')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: List Objects
    print("\n5. List Objects")
    print("-" * 70)
    try:
        objects = client.list_objects(prefix="test/", limit=10)
        print(f"Found {objects['count']} objects:")
        for obj in objects['objects'][:5]:
            if isinstance(obj, dict):
                print(f"  - {obj.get('object_key', obj.get('key', 'unknown'))}")
            else:
                print(f"  - {obj}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: Search (if PostgreSQL available)
    print("\n6. Search Objects")
    print("-" * 70)
    try:
        results = client.search_objects(query="test", limit=10)
        print(f"Found {results['count']} results")
        for result in results['results'][:3]:
            print(f"  - {result.get('object_key', result.get('key', 'unknown'))}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 501:
            print("⚠ Search requires PostgreSQL (not enabled)")
        else:
            print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 7: Download File
    print("\n7. Download File")
    print("-" * 70)
    try:
        download_path = "downloaded_api_test.txt"
        result = client.download_file(
            key="test/api/document.txt",
            output_path=download_path
        )
        print(f"✓ Downloaded to: {download_path}")
        print(f"  Size: {result['size']} bytes")
        print(f"  ETag: {result['etag']}")
        
        # Read and display content
        with open(download_path, "r") as f:
            content = f.read()
            print(f"  Content preview: {content[:100]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 8: List Versions
    print("\n8. List Versions")
    print("-" * 70)
    try:
        versions = client.list_versions("test/api/document.txt")
        print(f"Found {len(versions)} version(s):")
        for version in versions[:3]:
            print(f"  Version: {version['version_id']}")
            print(f"    Latest: {version['is_latest']}")
            print(f"    Modified: {version['last_modified']}")
            print(f"    Size: {version['size']} bytes")
            print()
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 9: Analytics
    print("\n9. Analytics")
    print("-" * 70)
    try:
        analytics = client.get_analytics(hours=24)
        print(f"Total objects: {analytics['total_objects']}")
        print(f"Total size: {analytics['total_size'] / 1024 / 1024:.2f} MB")
        print(f"Total versions: {analytics['total_versions']}")
        print(f"Recent uploads (24h): {analytics['recent_uploads']}")
        print(f"Recent downloads (24h): {analytics['recent_downloads']}")
        
        if analytics.get('storage_backends'):
            print("\nStorage backends:")
            for backend, stats in analytics['storage_backends'].items():
                print(f"  {backend}: {stats['object_count']} objects")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 501:
            print("⚠ Analytics requires PostgreSQL (not enabled)")
        else:
            print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 10: Audit Logs
    print("\n10. Audit Logs")
    print("-" * 70)
    try:
        logs = client.get_audit_logs(
            object_key="test/api/document.txt",
            hours=24,
            limit=10
        )
        print(f"Found {len(logs)} audit log(s):")
        for log in logs[:5]:
            print(f"  {log['timestamp']}: {log['action']}")
            if log.get('username'):
                print(f"    User: {log['username']}")
            print()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 501:
            print("⚠ Audit logs require PostgreSQL (not enabled)")
        else:
            print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 11: Webhook Registration (optional)
    print("\n11. Webhook Registration")
    print("-" * 70)
    try:
        # Register test webhook (to a dummy URL)
        webhook = client.register_webhook(
            name="test_webhook",
            url="https://webhook.site/unique-id",
            events=["DOCUMENT_ARCHIVED", "DOCUMENT_UPDATED"],
            retry_count=3
        )
        print(f"✓ Registered webhook: {webhook}")
        
        # List webhooks
        webhooks = client.list_webhooks()
        print(f"Total webhooks: {len(webhooks.get('webhooks', []))}")
    except Exception as e:
        print(f"⚠ Webhook registration: {e}")
    
    # Cleanup
    print("\n12. Cleanup")
    print("-" * 70)
    try:
        # Delete test file
        client.delete_object("test/api/document.txt")
        print("✓ Deleted test object")
    except Exception as e:
        print(f"⚠ Cleanup: {e}")
    
    # Remove local test files
    for file in [test_file, "downloaded_api_test.txt"]:
        if Path(file).exists():
            Path(file).unlink()
            print(f"✓ Removed local file: {file}")
    
    print("\n" + "=" * 70)
    print("✓ API Test Complete!")
    print("=" * 70)
    print("\nFor interactive API documentation, visit:")
    print("  http://localhost:8000/docs")


if __name__ == "__main__":
    main()
