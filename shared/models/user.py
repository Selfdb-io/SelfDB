"""
User model implementation following API Contracts Plan specification.
Based on Phase 2.2.1 User Model Foundation requirements.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
import bcrypt


class UserRole(str, Enum):
    """User role enumeration as specified in API Contracts Plan."""
    USER = "USER"
    ADMIN = "ADMIN"


class User:
    """
    User model with UUID, email, hashed_password, role-based access control.
    
    Attributes:
        id: UUID primary key
        email: Unique email address
        hashed_password: Bcrypt hashed password
        first_name: User's first name
        last_name: User's last name
        role: UserRole.USER or UserRole.ADMIN
        is_active: Account status (active/disabled)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        last_login_at: Last login timestamp
    """
    
    def __init__(
        self,
        id: uuid.UUID,
        email: str,
        hashed_password: Optional[str] = None,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None
    ):
        """
        Initialize a User instance.
        
        Args:
            id: UUID for the user
            email: Email address (must be valid)
            hashed_password: Pre-hashed password (if password not provided)
            password: Plain password to hash (if hashed_password not provided)
            role: User role (defaults to USER)
            is_active: Account status (defaults to True)
            created_at: Creation timestamp (defaults to now)
            updated_at: Update timestamp (defaults to now)
        """
        if not email:
            raise ValueError("Email is required")
        
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.is_active = is_active
        
        # Handle password hashing
        if password:
            self.hashed_password = self._hash_password(password)
        elif hashed_password:
            self.hashed_password = hashed_password
        else:
            raise ValueError("Either password or hashed_password must be provided")
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.last_login_at = last_login_at
    
    def _hash_password(self, password: str) -> str:
        """Hash a plain text password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @classmethod
    def create_admin(cls, email: str, password: str) -> 'User':
        """
        Create an admin user for initial setup.
        
        Args:
            email: Admin email address
            password: Admin password
            
        Returns:
            User instance with ADMIN role
        """
        return cls(
            id=uuid.uuid4(),
            email=email,
            password=password,
            role=UserRole.ADMIN,
            is_active=True
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert user to dictionary, excluding sensitive data.
        
        Returns:
            Dictionary representation of user (password excluded)
        """
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }
    
    def __str__(self) -> str:
        """String representation of user."""
        return f"<User {self.email}>"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return f"<User(id={self.id}, email={self.email}, role={self.role.value})>"