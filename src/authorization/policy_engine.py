"""
Policy Engine - Attribute-Based Access Control (ABAC)

Implements flexible policy rules for document access control based on user
and document attributes.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import re


class ConfidentialityLevel(Enum):
    """Document confidentiality levels."""
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3
    
    @classmethod
    def from_string(cls, level_str: str) -> 'ConfidentialityLevel':
        """Convert string to confidentiality level."""
        level_map = {
            'public': cls.PUBLIC,
            'internal': cls.INTERNAL,
            'confidential': cls.CONFIDENTIAL,
            'restricted': cls.RESTRICTED
        }
        return level_map.get(level_str.lower(), cls.INTERNAL)
    
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented
    
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
    
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


@dataclass
class AccessRule:
    """
    ABAC access rule definition.
    
    Rules are evaluated using attribute conditions. Examples:
    - user.department == document.department
    - user.clearance_level >= document.confidentiality_level
    - user.roles.contains('admin')
    """
    name: str
    description: str
    condition: str  # Python expression evaluated with user/document context
    priority: int = 100  # Higher priority = evaluated first
    allow: bool = True  # True = allow if matched, False = deny if matched


class PolicyEngine:
    """
    Attribute-Based Access Control (ABAC) engine.
    
    Evaluates access rules based on user and document attributes to
    determine if access should be granted.
    
    Features:
    - Flexible rule conditions
    - Priority-based evaluation
    - Default deny policy
    - Role-based and attribute-based rules
    """
    
    def __init__(self):
        """Initialize policy engine with default rules."""
        self.rules: List[AccessRule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default access control rules."""
        
        # Rule 1: Admin has access to everything
        self.add_rule(AccessRule(
            name="admin_full_access",
            description="Admins have full access to all documents",
            condition="'admin' in user.roles",
            priority=1000,
            allow=True
        ))
        
        # Rule 2: Clearance level check
        self.add_rule(AccessRule(
            name="clearance_level_check",
            description="User clearance must be >= document confidentiality",
            condition="user.clearance_level >= document.get('confidentiality_level', 1)",
            priority=900,
            allow=True
        ))
        
        # Rule 3: Department matching for confidential+ documents
        self.add_rule(AccessRule(
            name="department_matching",
            description="Confidential+ documents require department match",
            condition=(
                "document.get('confidentiality_level', 1) < 2 or "
                "user.department == document.get('department', 'general') or "
                "'admin' in user.roles"
            ),
            priority=800,
            allow=True
        ))
        
        # Rule 4: Owner access
        self.add_rule(AccessRule(
            name="owner_access",
            description="Document owner has access",
            condition="document.get('owner') == user.username",
            priority=850,
            allow=True
        ))
        
        # Rule 5: Public documents accessible to all
        self.add_rule(AccessRule(
            name="public_access",
            description="Public documents accessible to everyone",
            condition="document.get('confidentiality_level', 1) == 0",
            priority=700,
            allow=True
        ))
    
    def add_rule(self, rule: AccessRule):
        """
        Add access rule to policy engine.
        
        Args:
            rule: AccessRule to add
        """
        self.rules.append(rule)
        # Sort by priority (descending)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, rule_name: str):
        """
        Remove access rule by name.
        
        Args:
            rule_name: Name of rule to remove
        """
        self.rules = [r for r in self.rules if r.name != rule_name]
    
    def check_access(
        self,
        user: Any,  # User object with attributes
        document: Dict[str, Any],  # Document attributes
        action: str = "view"  # Action being performed
    ) -> bool:
        """
        Check if user has access to document.
        
        Args:
            user: User object with attributes (department, clearance_level, roles, etc.)
            document: Document attributes dictionary
            action: Action being performed (view, edit, delete, etc.)
            
        Returns:
            True if access allowed, False otherwise
        """
        # Create evaluation context
        context = {
            'user': user,
            'document': document,
            'action': action,
            # Helper functions
            'contains': lambda lst, item: item in lst if isinstance(lst, list) else False,
        }
        
        # Evaluate rules in priority order
        for rule in self.rules:
            try:
                # Evaluate rule condition
                result = eval(rule.condition, {"__builtins__": {}}, context)
                
                if result:
                    # Rule matched - return allow/deny
                    return rule.allow
            except Exception as e:
                # Rule evaluation failed - skip
                print(f"Warning: Rule '{rule.name}' evaluation failed: {e}")
                continue
        
        # Default deny if no rules matched
        return False
    
    def explain_decision(
        self,
        user: Any,
        document: Dict[str, Any],
        action: str = "view"
    ) -> Dict[str, Any]:
        """
        Explain access control decision with matched rules.
        
        Args:
            user: User object
            document: Document attributes
            action: Action being performed
            
        Returns:
            Dictionary with decision and reasoning
        """
        context = {
            'user': user,
            'document': document,
            'action': action,
            'contains': lambda lst, item: item in lst if isinstance(lst, list) else False,
        }
        
        matched_rules = []
        decision = False
        
        for rule in self.rules:
            try:
                result = eval(rule.condition, {"__builtins__": {}}, context)
                
                if result:
                    matched_rules.append({
                        'name': rule.name,
                        'description': rule.description,
                        'condition': rule.condition,
                        'priority': rule.priority,
                        'allow': rule.allow
                    })
                    
                    if decision is False:  # First match determines decision
                        decision = rule.allow
            except Exception as e:
                continue
        
        return {
            'allowed': decision,
            'matched_rules': matched_rules,
            'user': {
                'username': user.username,
                'department': user.department,
                'clearance_level': user.clearance_level,
                'roles': user.roles
            },
            'document': {
                'page_id': document.get('page_id', 'unknown'),
                'confidentiality_level': document.get('confidentiality_level', 1),
                'department': document.get('department', 'general'),
                'owner': document.get('owner', 'unknown')
            }
        }
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all rules as dictionaries."""
        return [
            {
                'name': r.name,
                'description': r.description,
                'condition': r.condition,
                'priority': r.priority,
                'allow': r.allow
            }
            for r in self.rules
        ]
    
    def escalate_confidentiality(
        self,
        document: Dict[str, Any],
        reason: str = "PII detected"
    ) -> int:
        """
        Escalate document confidentiality level.
        
        Args:
            document: Document attributes
            reason: Reason for escalation
            
        Returns:
            New confidentiality level
        """
        current_level = document.get('confidentiality_level', 1)
        
        # Escalate to at least CONFIDENTIAL (2) when PII detected
        new_level = max(current_level, ConfidentialityLevel.CONFIDENTIAL.value)
        
        document['confidentiality_level'] = new_level
        document['confidentiality_reason'] = reason
        
        return new_level


class AccessContext:
    """
    Context manager for access control checks.
    
    Provides convenient way to check access and automatically
    log audit events.
    """
    
    def __init__(
        self,
        policy_engine: PolicyEngine,
        audit_logger: Optional[Any] = None
    ):
        """
        Initialize access context.
        
        Args:
            policy_engine: PolicyEngine instance
            audit_logger: Optional AuditLogger instance
        """
        self.policy_engine = policy_engine
        self.audit_logger = audit_logger
    
    def check_and_log(
        self,
        user: Any,
        document: Dict[str, Any],
        action: str = "view",
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Check access and log audit event.
        
        Args:
            user: User object
            document: Document attributes
            action: Action being performed
            ip_address: Client IP address
            
        Returns:
            True if access allowed
            
        Raises:
            AuthorizationError: If access denied
        """
        from .user_manager import AuthorizationError
        
        allowed = self.policy_engine.check_access(user, document, action)
        
        # Log audit event
        if self.audit_logger:
            self.audit_logger.log_access(
                user_id=user.user_id,
                username=user.username,
                action=action,
                document_id=document.get('page_id', 'unknown'),
                allowed=allowed,
                ip_address=ip_address
            )
        
        if not allowed:
            raise AuthorizationError(
                f"Access denied: User '{user.username}' cannot {action} document"
            )
        
        return True
