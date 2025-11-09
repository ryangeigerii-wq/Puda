"""
Storage Management CLI

Command-line interface for storage operations.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.storage import (
    S3StorageManager,
    LocalStorageManager,
    VersionManager,
    IntegrationHookManager,
    HookEvent,
    WebhookHook,
    FileLogHook
)


def cmd_storage_info(args):
    """Display storage backend information."""
    storage = _create_storage(args)
    info = storage.get_storage_info()
    
    print("\n=== Storage Information ===")
    for key, value in info.items():
        print(f"{key}: {value}")
    print()


def cmd_put(args):
    """Upload object to storage."""
    storage = _create_storage(args)
    
    # Read file or stdin
    if args.file:
        data = Path(args.file).read_bytes()
    else:
        data = sys.stdin.buffer.read()
    
    # Parse metadata
    metadata = {}
    if args.metadata:
        for item in args.metadata:
            key, value = item.split('=', 1)
            metadata[key] = value
    
    # Upload
    result = storage.put_object(
        args.key,
        data,
        content_type=args.content_type,
        metadata=metadata if metadata else None
    )
    
    print(f"[OK] Uploaded: {args.key}")
    print(f"  Size: {result.size} bytes")
    print(f"  ETag: {result.etag}")
    print(f"  Version: {result.version_id or 'N/A'}")


def cmd_get(args):
    """Download object from storage."""
    storage = _create_storage(args)
    
    data = storage.get_object(args.key, version_id=args.version)
    
    if args.output:
        Path(args.output).write_bytes(data)
        print(f"[OK] Downloaded to: {args.output}")
    else:
        sys.stdout.buffer.write(data)


def cmd_delete(args):
    """Delete object from storage."""
    storage = _create_storage(args)
    
    success = storage.delete_object(args.key, version_id=args.version)
    
    if success:
        print(f"[OK] Deleted: {args.key}")
    else:
        print(f"[ERROR] Failed to delete: {args.key}")
        sys.exit(1)


def cmd_list(args):
    """List objects in storage."""
    storage = _create_storage(args)
    
    objects = storage.list_objects(prefix=args.prefix, max_keys=args.limit)
    
    print(f"\n=== Objects (prefix: {args.prefix or 'all'}) ===")
    print(f"{'Key':<50} {'Size':>10} {'Last Modified':<20}")
    print("-" * 82)
    
    for obj in objects:
        print(f"{obj.key:<50} {obj.size:>10} {obj.last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\nTotal: {len(objects)} objects")


def cmd_metadata(args):
    """Get object metadata."""
    storage = _create_storage(args)
    
    metadata = storage.get_metadata(args.key, version_id=args.version)
    
    print(f"\n=== Metadata: {args.key} ===")
    print(f"Size: {metadata.size} bytes")
    print(f"Content-Type: {metadata.content_type}")
    print(f"ETag: {metadata.etag}")
    print(f"Last Modified: {metadata.last_modified}")
    print(f"Version: {metadata.version_id or 'N/A'}")
    print(f"Storage Class: {metadata.storage_class or 'N/A'}")
    
    if metadata.metadata:
        print("\nCustom Metadata:")
        for key, value in metadata.metadata.items():
            print(f"  {key}: {value}")
    print()


def cmd_versions(args):
    """List object versions."""
    storage = _create_storage(args)
    version_manager = VersionManager(storage)
    
    versions = version_manager.list_versions(args.key, limit=args.limit)
    
    print(f"\n=== Versions: {args.key} ===")
    print(f"{'Version ID':<30} {'Size':>10} {'Modified':<20} {'Latest'}")
    print("-" * 72)
    
    for version in versions:
        latest_mark = " *" if version.is_latest else ""
        print(f"{version.version_id:<30} {version.size:>10} "
              f"{version.last_modified.strftime('%Y-%m-%d %H:%M:%S')}{latest_mark}")
        
        if version.comment:
            print(f"  Comment: {version.comment}")
        if version.tags:
            print(f"  Tags: {version.tags}")
    
    print(f"\nTotal: {len(versions)} versions")


def cmd_rollback(args):
    """Rollback to previous version."""
    storage = _create_storage(args)
    version_manager = VersionManager(storage)
    
    result = version_manager.rollback(
        args.key,
        args.version,
        comment=args.comment,
        created_by=args.user
    )
    
    print(f"[OK] Rolled back {args.key} to version {args.version}")
    print(f"  New version: {result.version_id}")


def cmd_compare(args):
    """Compare two versions."""
    storage = _create_storage(args)
    version_manager = VersionManager(storage)
    
    comparison = version_manager.compare_versions(args.key, args.version1, args.version2)
    
    print(f"\n=== Version Comparison: {args.key} ===")
    print(f"\nVersion 1: {args.version1}")
    print(f"  Size: {comparison['version1']['size']} bytes")
    print(f"  Modified: {comparison['version1']['last_modified']}")
    
    print(f"\nVersion 2: {args.version2}")
    print(f"  Size: {comparison['version2']['size']} bytes")
    print(f"  Modified: {comparison['version2']['last_modified']}")
    
    print(f"\nDifferences:")
    print(f"  Size change: {comparison['differences']['size_diff']:+d} bytes "
          f"({comparison['differences']['size_change_pct']:+.1f}%)")
    print(f"  Time difference: {comparison['differences']['time_diff_seconds']:.1f} seconds")
    print(f"  Content changed: {comparison['differences']['content_changed']}")
    print()


def cmd_history(args):
    """Show version history."""
    storage = _create_storage(args)
    version_manager = VersionManager(storage)
    
    history = version_manager.get_version_history(args.key, limit=args.limit)
    
    print(f"\n=== Version History: {args.key} ===")
    
    for entry in history:
        print(f"\n[{entry['timestamp']}] Version: {entry['version_id']}")
        print(f"  Size: {entry['size']} bytes")
        
        if entry.get('created_by'):
            print(f"  Created by: {entry['created_by']}")
        
        if entry.get('comment'):
            print(f"  Comment: {entry['comment']}")
        
        if entry.get('tags'):
            print(f"  Tags: {entry['tags']}")
        
        if entry.get('changes'):
            changes = entry['changes']
            print(f"  Changes: {changes['size_diff']:+d} bytes, "
                  f"{changes['time_since_previous']:.1f}s since previous")


def cmd_webhook_add(args):
    """Add webhook integration."""
    config_file = Path("data/integration_hooks.json")
    
    # Load existing config
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        config = {'webhooks': [], 'file_logs': []}
    
    # Add webhook
    webhook_config = {
        'name': args.name,
        'url': args.url,
        'method': args.method,
        'events': args.events or [],
        'enabled': True
    }
    
    config['webhooks'].append(webhook_config)
    
    # Save config
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"[OK] Added webhook: {args.name}")
    print(f"  URL: {args.url}")
    print(f"  Method: {args.method}")
    print(f"  Events: {args.events or 'all'}")


def cmd_webhook_list(args):
    """List webhook integrations."""
    config_file = Path("data/integration_hooks.json")
    
    if not config_file.exists():
        print("No webhooks configured")
        return
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    print("\n=== Webhooks ===")
    for webhook in config.get('webhooks', []):
        status = "enabled" if webhook.get('enabled', True) else "disabled"
        print(f"\n{webhook['name']} [{status}]")
        print(f"  URL: {webhook['url']}")
        print(f"  Method: {webhook['method']}")
        print(f"  Events: {webhook.get('events') or 'all'}")


def _create_storage(args):
    """Create storage instance from arguments."""
    if args.backend == 's3':
        return S3StorageManager(
            bucket_name=args.bucket,
            region=args.region,
            endpoint_url=args.endpoint,
            aws_access_key_id=args.access_key,
            aws_secret_access_key=args.secret_key,
            enable_versioning=args.versioning
        )
    elif args.backend == 'local':
        return LocalStorageManager(
            base_path=args.path,
            enable_versioning=args.versioning
        )
    else:
        print(f"Unknown backend: {args.backend}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Storage Management CLI")
    
    # Global options
    parser.add_argument('--backend', choices=['s3', 'local'], default='local',
                        help='Storage backend')
    parser.add_argument('--path', default='data/storage',
                        help='Local storage path')
    parser.add_argument('--bucket', help='S3 bucket name')
    parser.add_argument('--region', default='us-east-1', help='S3 region')
    parser.add_argument('--endpoint', help='S3 endpoint URL')
    parser.add_argument('--access-key', help='AWS access key')
    parser.add_argument('--secret-key', help='AWS secret key')
    parser.add_argument('--versioning', action='store_true', default=True,
                        help='Enable versioning')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # info command
    subparsers.add_parser('info', help='Display storage information')
    
    # put command
    put_parser = subparsers.add_parser('put', help='Upload object')
    put_parser.add_argument('key', help='Object key')
    put_parser.add_argument('--file', help='File to upload (stdin if not specified)')
    put_parser.add_argument('--content-type', default='application/octet-stream',
                            help='Content type')
    put_parser.add_argument('--metadata', nargs='*', help='Metadata (key=value)')
    
    # get command
    get_parser = subparsers.add_parser('get', help='Download object')
    get_parser.add_argument('key', help='Object key')
    get_parser.add_argument('--version', help='Specific version')
    get_parser.add_argument('--output', help='Output file (stdout if not specified)')
    
    # delete command
    delete_parser = subparsers.add_parser('delete', help='Delete object')
    delete_parser.add_argument('key', help='Object key')
    delete_parser.add_argument('--version', help='Specific version')
    
    # list command
    list_parser = subparsers.add_parser('list', help='List objects')
    list_parser.add_argument('--prefix', default='', help='Key prefix filter')
    list_parser.add_argument('--limit', type=int, default=1000, help='Maximum results')
    
    # metadata command
    metadata_parser = subparsers.add_parser('metadata', help='Get object metadata')
    metadata_parser.add_argument('key', help='Object key')
    metadata_parser.add_argument('--version', help='Specific version')
    
    # versions command
    versions_parser = subparsers.add_parser('versions', help='List object versions')
    versions_parser.add_argument('key', help='Object key')
    versions_parser.add_argument('--limit', type=int, default=20, help='Maximum versions')
    
    # rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback to version')
    rollback_parser.add_argument('key', help='Object key')
    rollback_parser.add_argument('version', help='Version to rollback to')
    rollback_parser.add_argument('--comment', help='Rollback comment')
    rollback_parser.add_argument('--user', help='User performing rollback')
    
    # compare command
    compare_parser = subparsers.add_parser('compare', help='Compare versions')
    compare_parser.add_argument('key', help='Object key')
    compare_parser.add_argument('version1', help='First version')
    compare_parser.add_argument('version2', help='Second version')
    
    # history command
    history_parser = subparsers.add_parser('history', help='Show version history')
    history_parser.add_argument('key', help='Object key')
    history_parser.add_argument('--limit', type=int, default=20, help='Maximum entries')
    
    # webhook-add command
    webhook_add_parser = subparsers.add_parser('webhook-add', help='Add webhook')
    webhook_add_parser.add_argument('name', help='Webhook name')
    webhook_add_parser.add_argument('url', help='Webhook URL')
    webhook_add_parser.add_argument('--method', default='POST', help='HTTP method')
    webhook_add_parser.add_argument('--events', nargs='*', help='Event filters')
    
    # webhook-list command
    subparsers.add_parser('webhook-list', help='List webhooks')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    command_handlers = {
        'info': cmd_storage_info,
        'put': cmd_put,
        'get': cmd_get,
        'delete': cmd_delete,
        'list': cmd_list,
        'metadata': cmd_metadata,
        'versions': cmd_versions,
        'rollback': cmd_rollback,
        'compare': cmd_compare,
        'history': cmd_history,
        'webhook-add': cmd_webhook_add,
        'webhook-list': cmd_webhook_list
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except Exception as e:
            print(f"[ERROR] {e}")
            sys.exit(1)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
