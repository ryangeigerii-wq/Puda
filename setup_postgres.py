#!/usr/bin/env python3
"""
PostgreSQL Setup and Verification Script

Checks PostgreSQL connection, initializes schema, and verifies functionality.
"""

import sys
import os
from datetime import datetime

# Check if psycopg2 is available
try:
    import psycopg2
    from psycopg2 import sql
    print("✓ psycopg2 is installed")
except ImportError:
    print("✗ psycopg2 not found")
    print("\nInstall it with:")
    print("  pip install psycopg2-binary")
    sys.exit(1)

# Try to import storage module
try:
    from src.storage import PostgreSQLStorageDB
    print("✓ Storage module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import storage module: {e}")
    sys.exit(1)


def test_connection(host, port, database, user, password):
    """Test basic PostgreSQL connection."""
    print(f"\nTesting connection to {host}:{port}/{database}...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=5
        )
        print("✓ Connection successful")
        
        # Get version
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"  PostgreSQL version: {version.split(',')[0]}")
        
        conn.close()
        return True
    except psycopg2.OperationalError as e:
        print(f"✗ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def initialize_database(host, port, database, user, password):
    """Initialize PostgreSQL storage database."""
    print(f"\nInitializing database schema...")
    try:
        db = PostgreSQLStorageDB(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("✓ Database schema initialized")
        
        # Verify tables exist
        conn = db._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    ORDER BY tablename;
                """)
                tables = [row[0] for row in cur.fetchall()]
                
                expected_tables = [
                    'storage_objects',
                    'storage_versions',
                    'storage_audit',
                    'storage_hooks'
                ]
                
                print("\nDatabase tables:")
                for table in expected_tables:
                    if table in tables:
                        print(f"  ✓ {table}")
                    else:
                        print(f"  ✗ {table} (missing)")
        finally:
            db._put_connection(conn)
        
        return db
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        return None


def test_basic_operations(db):
    """Test basic database operations."""
    print("\nTesting basic operations...")
    
    try:
        # Test 1: Record object
        print("  Testing record_object...")
        object_id = db.record_object(
            object_key="test/setup_test.txt",
            size=1024,
            content_type="text/plain",
            etag="test-etag-123",
            version_id="v1",
            storage_backend="local",
            metadata={"test": "true", "created": datetime.now().isoformat()}
        )
        print(f"    ✓ Object recorded with ID: {object_id}")
        
        # Test 2: Get object metadata
        print("  Testing get_object_metadata...")
        metadata = db.get_object_metadata("test/setup_test.txt")
        if metadata and metadata['object_key'] == "test/setup_test.txt":
            print(f"    ✓ Metadata retrieved: {metadata['size']} bytes")
        else:
            print("    ✗ Metadata retrieval failed")
            return False
        
        # Test 3: Record version
        print("  Testing record_version...")
        db.record_version(
            object_key="test/setup_test.txt",
            version_id="v1",
            size=1024,
            etag="test-etag-123",
            is_latest=True,
            created_by="setup_script",
            comment="Setup test version"
        )
        print("    ✓ Version recorded")
        
        # Test 4: List versions
        print("  Testing list_versions...")
        versions = db.list_versions("test/setup_test.txt")
        if versions and len(versions) > 0:
            print(f"    ✓ Found {len(versions)} version(s)")
        else:
            print("    ✗ Version listing failed")
            return False
        
        # Test 5: Log audit
        print("  Testing log_audit...")
        db.log_audit(
            action="TEST",
            object_key="test/setup_test.txt",
            user_id="setup_script",
            username="Setup Script",
            success=True,
            metadata={"test": "audit_log"}
        )
        print("    ✓ Audit logged")
        
        # Test 6: Get audit logs
        print("  Testing get_audit_logs...")
        logs = db.get_audit_logs(object_key="test/setup_test.txt", limit=10)
        if logs and len(logs) > 0:
            print(f"    ✓ Found {len(logs)} audit log(s)")
        else:
            print("    ✗ Audit log retrieval failed")
            return False
        
        # Test 7: Search objects
        print("  Testing search_objects...")
        results = db.search_objects("test", limit=10)
        if results is not None:
            print(f"    ✓ Search returned {len(results)} result(s)")
        else:
            print("    ✗ Search failed")
            return False
        
        # Test 8: Get statistics
        print("  Testing get_statistics...")
        stats = db.get_statistics()
        if stats:
            print(f"    ✓ Statistics retrieved")
            print(f"      Total versions: {stats['total_versions']}")
        else:
            print("    ✗ Statistics retrieval failed")
            return False
        
        # Cleanup test data
        print("  Cleaning up test data...")
        db.delete_object("test/setup_test.txt")
        print("    ✓ Test data cleaned up")
        
        print("\n✓ All basic operations passed")
        return True
        
    except Exception as e:
        print(f"\n✗ Operation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_connection_info():
    """Print connection information guide."""
    print("\n" + "=" * 70)
    print("PostgreSQL Connection Information")
    print("=" * 70)
    print("\nEnvironment Variables:")
    print("  POSTGRES_HOST     - Database host (default: localhost)")
    print("  POSTGRES_PORT     - Database port (default: 5432)")
    print("  POSTGRES_DB       - Database name (default: puda_storage)")
    print("  POSTGRES_USER     - Database user (default: puda)")
    print("  POSTGRES_PASSWORD - Database password (default: puda)")
    
    print("\nDocker Quick Start:")
    print("  docker-compose up -d puda-postgres")
    
    print("\nManual PostgreSQL Setup:")
    print("  sudo -u postgres psql")
    print("  CREATE DATABASE puda_storage;")
    print("  CREATE USER puda WITH PASSWORD 'puda';")
    print("  GRANT ALL PRIVILEGES ON DATABASE puda_storage TO puda;")
    
    print("\nTest Connection:")
    print("  psql -h localhost -U puda -d puda_storage")
    print("=" * 70)


def main():
    """Main setup script."""
    print("=" * 70)
    print("PostgreSQL Storage Database Setup")
    print("=" * 70)
    
    # Get connection parameters from environment or use defaults
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", 5432))
    database = os.getenv("POSTGRES_DB", "puda_storage")
    user = os.getenv("POSTGRES_USER", "puda")
    password = os.getenv("POSTGRES_PASSWORD", "puda")
    
    print(f"\nConnection Parameters:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {database}")
    print(f"  User: {user}")
    print(f"  Password: {'*' * len(password)}")
    
    # Test connection
    if not test_connection(host, port, database, user, password):
        print("\n✗ Setup failed: Could not connect to PostgreSQL")
        print_connection_info()
        sys.exit(1)
    
    # Initialize database
    db = initialize_database(host, port, database, user, password)
    if db is None:
        print("\n✗ Setup failed: Could not initialize database")
        sys.exit(1)
    
    # Test operations
    if not test_basic_operations(db):
        print("\n✗ Setup failed: Basic operations test failed")
        sys.exit(1)
    
    # Success!
    print("\n" + "=" * 70)
    print("PostgreSQL Storage Database Setup Complete!")
    print("=" * 70)
    print("\nYou can now use PostgreSQL with the storage layer:")
    print("\n  from src.storage import PostgreSQLStorageDB")
    print("  db = PostgreSQLStorageDB()")
    print("\nFor examples, see:")
    print("  - POSTGRES_SETUP.md")
    print("  - storage_integration_example.py")
    print("=" * 70)
    
    # Close database
    db.close()


if __name__ == "__main__":
    main()
