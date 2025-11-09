"""
Authorization Layer

Provides:
- User management with authentication
- Attribute-Based Access Control (ABAC)
- PII detection and confidentiality escalation
- Audit trail for all document access
- Encryption (AES-256 at rest, TLS in transit)
"""

from .user_manager import User, UserManager, AuthenticationError, AuthorizationError
from .policy_engine import PolicyEngine, AccessRule, ConfidentialityLevel
from .pii_detector import PIIDetector, PIIMatch
from .audit_logger import AuditLogger, AuditAction
from .encryption import EncryptionManager

__all__ = [
    'User',
    'UserManager',
    'AuthenticationError',
    'AuthorizationError',
    'PolicyEngine',
    'AccessRule',
    'ConfidentialityLevel',
    'PIIDetector',
    'PIIMatch',
    'AuditLogger',
    'AuditAction',
    'EncryptionManager',
]
