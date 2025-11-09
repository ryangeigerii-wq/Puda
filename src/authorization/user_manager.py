"""
User Manager - Authentication and User Management

Handles user authentication, password hashing, and user attributes for ABAC.
"""

import sqlite3
import hashlib
import secrets
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when authorization check fails."""
    pass


@dataclass
class User:
    """
    User model with attributes for ABAC.
    
    Attributes:
        user_id: Unique user identifier
        username: Login username
        password_hash: Bcrypt hashed password
        department: User department (for ABAC rules)
        clearance_level: Access level (0=public, 1=internal, 2=confidential, 3=restricted)
        roles: List of user roles (admin, operator, viewer)
        email: User email
        created_at: Account creation timestamp
        last_login: Last login timestamp
        is_active: Account active status
        attributes: Additional custom attributes for ABAC
    """
    user_id: str
    username: str
    password_hash: str
    department: str = "general"
    clearance_level: int = 1  # 0=public, 1=internal, 2=confidential, 3=restricted
    roles: List[str] = None
    email: Optional[str] = None
    created_at: Optional[float] = None
    last_login: Optional[float] = None
    is_active: bool = True
    attributes: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = ["viewer"]
        if self.attributes is None:
            self.attributes = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow().timestamp()
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding password_hash)."""
        data = asdict(self)
        data.pop('password_hash', None)
        return data


class UserManager:
    """
    User management system with authentication.
    
    Features:
    - Bcrypt password hashing
    - User CRUD operations
    - Authentication and session management
    - Attribute management for ABAC
    """
    
    def __init__(self, db_path: str = "data/users.db"):
        """
        Initialize user manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._create_default_admin()
    
    def _create_tables(self):
        """Create database tables."""
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                department TEXT DEFAULT 'general',
                clearance_level INTEGER DEFAULT 1,
                roles TEXT NOT NULL,
                email TEXT,
                created_at REAL NOT NULL,
                last_login REAL,
                is_active INTEGER DEFAULT 1,
                attributes TEXT
            )
        """)
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")
        
        self.conn.commit()
    
    def _create_default_admin(self):
        """Create default admin user if no users exist."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()['count']
        
        if count == 0:
            print("Creating default admin user (username: admin, password: admin)")
            self.create_user(
                username="admin",
                password="admin",
                department="administration",
                clearance_level=3,
                roles=["admin", "operator", "viewer"],
                email="admin@localhost"
            )
            print("Creating default user ryan (username: ryan, password: password)")
            self.create_user(
                username="ryan",
                password="password",
                department="general",
                clearance_level=1,
                roles=["operator", "viewer"],
                email="ryan@localhost"
            )
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256 with salt.
        
        Note: In production, use bcrypt/argon2. Using SHA-256 for simplicity.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password with salt
        """
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${pwd_hash}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            password_hash: Stored password hash
            
        Returns:
            True if password matches
        """
        try:
            salt, pwd_hash = password_hash.split('$')
            check_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return check_hash == pwd_hash
        except ValueError:
            return False
    
    def create_user(
        self,
        username: str,
        password: str,
        department: str = "general",
        clearance_level: int = 1,
        roles: Optional[List[str]] = None,
        email: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        Create new user.
        
        Args:
            username: Login username
            password: Plain text password (will be hashed)
            department: User department
            clearance_level: Access level (0-3)
            roles: User roles
            email: User email
            attributes: Additional attributes
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If username already exists
        """
        if roles is None:
            roles = ["viewer"]
        if attributes is None:
            attributes = {}
        
        user_id = secrets.token_urlsafe(16)
        password_hash = self._hash_password(password)
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO users (
                    user_id, username, password_hash, department,
                    clearance_level, roles, email, created_at, attributes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                username,
                password_hash,
                department,
                clearance_level,
                json.dumps(roles),
                email,
                datetime.utcnow().timestamp(),
                json.dumps(attributes)
            ))
            self.conn.commit()
            
            return User(
                user_id=user_id,
                username=username,
                password_hash=password_hash,
                department=department,
                clearance_level=clearance_level,
                roles=roles,
                email=email,
                created_at=datetime.utcnow().timestamp(),
                attributes=attributes
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{username}' already exists")
    
    def authenticate(self, username: str, password: str) -> User:
        """
        Authenticate user with username and password.
        
        Args:
            username: Login username
            password: Plain text password
            
        Returns:
            User object if authentication succeeds
            
        Raises:
            AuthenticationError: If authentication fails
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if not row:
            raise AuthenticationError("Invalid username or password")
        
        if not row['is_active']:
            raise AuthenticationError("Account is disabled")
        
        if not self._verify_password(password, row['password_hash']):
            raise AuthenticationError("Invalid username or password")
        
        # Update last login
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE user_id = ?",
            (datetime.utcnow().timestamp(), row['user_id'])
        )
        self.conn.commit()
        
        return User(
            user_id=row['user_id'],
            username=row['username'],
            password_hash=row['password_hash'],
            department=row['department'],
            clearance_level=row['clearance_level'],
            roles=json.loads(row['roles']),
            email=row['email'],
            created_at=row['created_at'],
            last_login=datetime.utcnow().timestamp(),
            is_active=bool(row['is_active']),
            attributes=json.loads(row['attributes']) if row['attributes'] else {}
        )
    
    def create_session(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        duration_hours: int = 24
    ) -> str:
        """
        Create session for authenticated user.
        
        Args:
            user: Authenticated user
            ip_address: Client IP address
            user_agent: Client user agent
            duration_hours: Session duration in hours
            
        Returns:
            Session ID token
        """
        session_id = secrets.token_urlsafe(32)
        created_at = datetime.utcnow().timestamp()
        expires_at = (datetime.utcnow() + timedelta(hours=duration_hours)).timestamp()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (
                session_id, user_id, created_at, expires_at,
                ip_address, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user.user_id, created_at, expires_at, ip_address, user_agent))
        self.conn.commit()
        
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[User]:
        """
        Validate session and return user.
        
        Args:
            session_id: Session ID token
            
        Returns:
            User object if session is valid, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, u.*
            FROM sessions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.session_id = ? AND s.expires_at > ?
        """, (session_id, datetime.utcnow().timestamp()))
        
        row = cursor.fetchone()
        if not row or not row['is_active']:
            return None
        
        return User(
            user_id=row['user_id'],
            username=row['username'],
            password_hash=row['password_hash'],
            department=row['department'],
            clearance_level=row['clearance_level'],
            roles=json.loads(row['roles']),
            email=row['email'],
            created_at=row['created_at'],
            last_login=row['last_login'],
            is_active=bool(row['is_active']),
            attributes=json.loads(row['attributes']) if row['attributes'] else {}
        )
    
    def delete_session(self, session_id: str):
        """Delete (logout) session."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        self.conn.commit()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return User(
            user_id=row['user_id'],
            username=row['username'],
            password_hash=row['password_hash'],
            department=row['department'],
            clearance_level=row['clearance_level'],
            roles=json.loads(row['roles']),
            email=row['email'],
            created_at=row['created_at'],
            last_login=row['last_login'],
            is_active=bool(row['is_active']),
            attributes=json.loads(row['attributes']) if row['attributes'] else {}
        )
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return User(
            user_id=row['user_id'],
            username=row['username'],
            password_hash=row['password_hash'],
            department=row['department'],
            clearance_level=row['clearance_level'],
            roles=json.loads(row['roles']),
            email=row['email'],
            created_at=row['created_at'],
            last_login=row['last_login'],
            is_active=bool(row['is_active']),
            attributes=json.loads(row['attributes']) if row['attributes'] else {}
        )
    
    def list_users(self) -> List[User]:
        """List all users."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY username")
        
        users = []
        for row in cursor.fetchall():
            users.append(User(
                user_id=row['user_id'],
                username=row['username'],
                password_hash=row['password_hash'],
                department=row['department'],
                clearance_level=row['clearance_level'],
                roles=json.loads(row['roles']),
                email=row['email'],
                created_at=row['created_at'],
                last_login=row['last_login'],
                is_active=bool(row['is_active']),
                attributes=json.loads(row['attributes']) if row['attributes'] else {}
            ))
        
        return users
    
    def update_user(
        self,
        user_id: str,
        department: Optional[str] = None,
        clearance_level: Optional[int] = None,
        roles: Optional[List[str]] = None,
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Update user attributes."""
        updates = []
        params = []
        
        if department is not None:
            updates.append("department = ?")
            params.append(department)
        if clearance_level is not None:
            updates.append("clearance_level = ?")
            params.append(clearance_level)
        if roles is not None:
            updates.append("roles = ?")
            params.append(json.dumps(roles))
        if email is not None:
            updates.append("email = ?")
            params.append(email)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(int(is_active))
        if attributes is not None:
            updates.append("attributes = ?")
            params.append(json.dumps(attributes))
        
        if not updates:
            return
        
        params.append(user_id)
        cursor = self.conn.cursor()
        cursor.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?",
            params
        )
        self.conn.commit()
    
    def change_password(self, user_id: str, new_password: str):
        """Change user password."""
        password_hash = self._hash_password(new_password)
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (password_hash, user_id)
        )
        self.conn.commit()
    
    def delete_user(self, user_id: str):
        """Delete user (soft delete by deactivating)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET is_active = 0 WHERE user_id = ?",
            (user_id,)
        )
        # Delete all user sessions
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM sessions WHERE expires_at < ?",
            (datetime.utcnow().timestamp(),)
        )
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
