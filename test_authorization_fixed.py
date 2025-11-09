#!/usr/bin/env python3
"""
Test Authorization Layer

Tests user management, ABAC, PII detection, audit logging, and encryption.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.authorization import (
    UserManager, PolicyEngine, PIIDetector,
    AuditLogger, EncryptionManager, ConfidentialityLevel
)


def test_user_management():
    """Test user management and authentication."""
    print("\n=== Testing User Management ===")
    
    user_mgr = UserManager(db_path="data/test_users.db")
    
    # Test default admin user
    try:
        admin = user_mgr.authenticate("admin", "admin")
        print(f"[OK] Admin authentication successful: {admin.username}")
        print(f"  Department: {admin.department}")
        print(f"  Clearance: {admin.clearance_level}")
        print(f"  Roles: {admin.roles}")
    except Exception as e:
        print(f"[X] Admin authentication failed: {e}")
    
    # Create test users
    print("\nCreating test users...")
    try:
        user1 = user_mgr.create_user(
            username="john_doe",
            password="password123",
            department="finance",
            clearance_level=2,
            roles=["viewer", "operator"],
            email="john@example.com"
        )
        print(f"[OK] Created user: {user1.username} (Finance, Clearance 2)")
        
        user2 = user_mgr.create_user(
            username="jane_smith",
            password="secure456",
            department="hr",
            clearance_level=1,
            roles=["viewer"],
            email="jane@example.com"
        )
        print(f"[OK] Created user: {user2.username} (HR, Clearance 1)")
    except ValueError as e:
        print(f"Note: {e}")
    
    # Test authentication
    print("\nTesting authentication...")
    try:
        user = user_mgr.authenticate("john_doe", "password123")
        print(f"[OK] Authentication successful for {user.username}")
        
        # Create session
        session_id = user_mgr.create_session(user, ip_address="127.0.0.1")
        print(f"[OK] Session created: {session_id[:16]}...")
        
        # Validate session
        validated_user = user_mgr.validate_session(session_id)
        if validated_user:
            print(f"[OK] Session validated for {validated_user.username}")
        
    except Exception as e:
        print(f"[X] Authentication failed: {e}")
    
    user_mgr.close()
    print("\n[OK] User management tests completed")


def test_policy_engine():
    """Test ABAC policy engine."""
    print("\n=== Testing Policy Engine ===")
    
    engine = PolicyEngine()
    
    # Create test user and documents
    user_mgr = UserManager(db_path="data/test_users.db")
    
    # Test with admin
    admin = user_mgr.authenticate("admin", "admin")
    
    # Test documents with various confidentiality levels
    documents = [
        {
            'page_id': 'DOC001',
            'owner': 'admin',
            'department': 'finance',
            'confidentiality_level': 0,  # Public
        },
        {
            'page_id': 'DOC002',
            'owner': 'john_doe',
            'department': 'finance',
            'confidentiality_level': 2,  # Confidential
        },
        {
            'page_id': 'DOC003',
            'owner': 'jane_smith',
            'department': 'hr',
            'confidentiality_level': 3,  # Restricted
        },
    ]
    
    print("\nTesting admin access:")
    for doc in documents:
        allowed = engine.check_access(admin, doc)
        print(f"  {doc['page_id']} (Level {doc['confidentiality_level']}): {'[OK] Allowed' if allowed else '[X] Denied'}")
    
    # Test with regular user
    print("\nTesting john_doe access (Finance, Clearance 2):")
    john = user_mgr.get_user_by_username("john_doe")
    if john:
        for doc in documents:
            allowed = engine.check_access(john, doc)
            explanation = engine.explain_decision(john, doc)
            print(f"  {doc['page_id']} (Level {doc['confidentiality_level']}): {'[OK] Allowed' if allowed else '[X] Denied'}")
            if explanation['matched_rules']:
                print(f"    Matched rule: {explanation['matched_rules'][0]['name']}")
    
    # Test with jane (HR, lower clearance)
    print("\nTesting jane_smith access (HR, Clearance 1):")
    jane = user_mgr.get_user_by_username("jane_smith")
    if jane:
        for doc in documents:
            allowed = engine.check_access(jane, doc)
            print(f"  {doc['page_id']} (Level {doc['confidentiality_level']}): {'[OK] Allowed' if allowed else '[X] Denied'}")
    
    user_mgr.close()
    print("\n[OK] Policy engine tests completed")


def test_pii_detection():
    """Test PII detection."""
    print("\n=== Testing PII Detection ===")
    
    detector = PIIDetector()
    
    # Test texts with PII
    test_cases = [
        ("John Doe, SSN: 123-45-6789", "SSN"),
        ("Credit Card: 4532-1234-5678-9010", "Credit Card"),
        ("Contact: john@example.com or call 555-123-4567", "Email and Phone"),
        ("Date of Birth: 01/15/1990", "Date of Birth"),
        ("No PII here, just normal text", "No PII"),
    ]
    
    for text, description in test_cases:
        matches = detector.detect(text)
        print(f"\n{description}:")
        print(f"  Text: {text}")
        if matches:
            print(f"  [OK] Found {len(matches)} PII match(es):")
            for match in matches:
                print(f"    - {match.pii_type.value}: {match.value} (confidence: {match.confidence:.2f})")
        else:
            print(f"  No PII detected")
    
    # Test document scanning with escalation
    print("\n\nTesting document scanning with confidentiality escalation:")
    document = {
        'page_id': 'TEST_DOC',
        'ocr_text': 'Patient record: John Doe, SSN: 987-65-4321, DOB: 05/20/1985',
        'confidentiality_level': 1  # Internal
    }
    
    print(f"Original confidentiality: {document['confidentiality_level']}")
    result = detector.scan_document(document)
    
    print(f"PII found: {result['has_pii']}")
    print(f"PII types: {result['pii_types']}")
    print(f"Escalated: {result['escalated']}")
    if result['escalated']:
        print(f"New confidentiality: {result['new_confidentiality']}")
    
    # Test redaction
    print("\n\nTesting PII redaction:")
    original = "Contact me at john.doe@example.com or 555-123-4567"
    redacted = detector.redact_pii(original)
    print(f"Original: {original}")
    print(f"Redacted: {redacted}")
    
    print("\n[OK] PII detection tests completed")


def test_audit_logging():
    """Test audit logging."""
    print("\n=== Testing Audit Logging ===")
    
    logger = AuditLogger(db_path="data/test_audit.db")
    
    # Log some test events
    print("\nLogging test events...")
    logger.log_access(
        user_id="user_001",
        username="john_doe",
        action="view",
        document_id="DOC001",
        allowed=True,
        ip_address="192.168.1.100"
    )
    
    logger.log_access(
        user_id="user_002",
        username="jane_smith",
        action="download",
        document_id="DOC002",
        allowed=False,
        ip_address="192.168.1.101"
    )
    
    logger.log_search(
        user_id="user_001",
        username="john_doe",
        search_query="invoice",
        results_count=25,
        ip_address="192.168.1.100"
    )
    
    print("[OK] Logged 3 events")
    
    # Get statistics
    print("\nAudit statistics:")
    stats = logger.get_statistics()
    print(f"  Total events: {stats['total_events']}")
    print(f"  By action: {stats['by_action']}")
    print(f"  Denied events: {stats['denied_count']}")
    
    # Get user activity
    print("\nUser activity for john_doe:")
    events = logger.get_user_activity("user_001", limit=5)
    for event in events:
        print(f"  - {event['action']} on {event['resource_id']} at {event['timestamp']}")
    
    logger.close()
    print("\n[OK] Audit logging tests completed")


def test_encryption():
    """Test encryption."""
    print("\n=== Testing Encryption ===")
    
    try:
        mgr = EncryptionManager(key_file="data/test_encryption_key.bin")
        
        # Test text encryption
        print("\nTesting text encryption:")
        original_text = "This is a confidential document with sensitive information."
        encrypted_text = mgr.encrypt_text(original_text, context="test_doc")
        decrypted_text = mgr.decrypt_text(encrypted_text, context="test_doc")
        
        print(f"  Original:  {original_text}")
        print(f"  Encrypted: {encrypted_text[:50]}...")
        print(f"  Decrypted: {decrypted_text}")
        
        if original_text == decrypted_text:
            print("  [OK] Encryption/decryption successful")
        else:
            print("  [X] Encryption/decryption failed")
        
        # Test file encryption
        print("\nTesting file encryption:")
        test_file = Path("data/test_file.txt")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("This is a test file with sensitive data.")
        
        metadata = mgr.encrypt_file(test_file, document_id="test_file")
        print(f"  [OK] File encrypted: {metadata['output_path']}")
        print(f"    Original size: {metadata['original_size']} bytes")
        print(f"    Encrypted size: {metadata['encrypted_size']} bytes")
        
        decrypted_path = mgr.decrypt_file(
            Path(metadata['output_path']),
            document_id="test_file"
        )
        print(f"  [OK] File decrypted: {decrypted_path}")
        
        # Verify content
        if test_file.read_text() == decrypted_path.read_text():
            print("  [OK] File content verified")
        else:
            print("  [X] File content mismatch")
        
        print("\n[OK] Encryption tests completed")
        
    except ImportError as e:
        print(f"\n⊘ Encryption tests skipped: {e}")
        print("  Install cryptography: pip install cryptography")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Authorization Layer Tests")
    print("=" * 60)
    
    tests = [
        test_user_management,
        test_policy_engine,
        test_pii_detection,
        test_audit_logging,
        test_encryption,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n[X] Test failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("All tests completed")
    print("=" * 60)


if __name__ == "__main__":
    main()

