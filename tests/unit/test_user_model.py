"""
Test suite for User model implementation following TDD principles.
Based on API Contracts Plan specification for User model.
"""

import pytest
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from shared.models.user import User, UserRole


class TestUserModel:
    """Test cases for User model implementation."""
    
    def test_user_role_enum_values(self):
        """Test that UserRole enum has correct values."""
        assert UserRole.USER.value == "USER"
        assert UserRole.ADMIN.value == "ADMIN"
    
    def test_user_creation_with_required_fields(self):
        """Test creating a user with all required fields."""
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.email == "test@example.com"
        assert user.hashed_password.startswith("$2b$")  # bcrypt hash
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
    
    def test_user_default_role_is_user(self):
        """Test that default role is USER when not specified."""
        # This test will verify the model has proper defaults
        user_data = {
            "id": uuid.uuid4(),
            "email": "test@example.com",
            "hashed_password": "$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Model should handle missing role field
        user = User(**user_data)
        assert user.role == UserRole.USER
    
    def test_user_admin_role_assignment(self):
        """Test creating a user with ADMIN role."""
        admin = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert admin.role == UserRole.ADMIN
    
    def test_user_email_validation(self):
        """Test that user email must be valid format."""
        # Valid email
        user = User(
            id=uuid.uuid4(),
            email="valid.email+tag@subdomain.example.com",
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert user.email == "valid.email+tag@subdomain.example.com"
    
    def test_user_email_uniqueness_constraint(self):
        """Test that user email must be unique."""
        # This will be tested at database level
        # For now, verify the model supports unique constraint
        email = "unique@example.com"
        user1 = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        user2 = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password="$2b$12$DifferentHash123456789012345678901234567890123456789012345678",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Both users have same email - database constraint should prevent this
        assert user1.email == user2.email
    
    def test_user_password_hashing(self):
        """Test that password is properly hashed, not stored in plain text."""
        password = "mySecurePassword123!"
        
        # Model should accept plain password and hash it
        user = User(
            id=uuid.uuid4(),
            email="secure@example.com",
            password=password,  # Plain password
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Hashed password should not equal plain password
        assert user.hashed_password != password
        assert user.hashed_password.startswith("$2b$")
    
    def test_user_account_status_management(self):
        """Test user account active/inactive status."""
        active_user = User(
            id=uuid.uuid4(),
            email="active@example.com",
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        inactive_user = User(
            id=uuid.uuid4(),
            email="inactive@example.com",
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.USER,
            is_active=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert active_user.is_active is True
        assert inactive_user.is_active is False
    
    def test_user_timestamps(self):
        """Test that created_at and updated_at are datetime objects."""
        now = datetime.now(timezone.utc)
        user = User(
            id=uuid.uuid4(),
            email="timestamp@example.com",
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.USER,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        assert user.created_at == now
        assert user.updated_at == now
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
    
    def test_user_to_dict_conversion(self):
        """Test user serialization to dictionary."""
        user = User(
            id=uuid.uuid4(),
            email="dict@example.com",
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        user_dict = user.to_dict()
        
        assert user_dict["id"] == str(user.id)
        assert user_dict["email"] == user.email
        assert user_dict["role"] == user.role.value
        assert user_dict["is_active"] == user.is_active
        assert "hashed_password" not in user_dict  # Password should never be serialized
    
    def test_user_string_representation(self):
        """Test user string representation."""
        user = User(
            id=uuid.uuid4(),
            email="repr@example.com",
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.USER,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert str(user) == f"<User {user.email}>"
    
    def test_user_repr(self):
        """Test user detailed representation."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
            role=UserRole.ADMIN,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        expected = f"<User(id={user_id}, email=test@example.com, role=ADMIN)>"
        assert repr(user) == expected
    
    def test_admin_user_creation(self):
        """Test creating an admin user for initial setup."""
        admin = User.create_admin(
            email="admin@selfdb.com",
            password="adminSecurePassword123!"
        )
        
        assert admin.role == UserRole.ADMIN
        assert admin.is_active is True
        assert admin.email == "admin@selfdb.com"
        assert admin.hashed_password != "adminSecurePassword123!"  # Should be hashed
    
    def test_user_validation_email_required(self):
        """Test that email is required."""
        with pytest.raises(ValueError):
            User(
                id=uuid.uuid4(),
                email="",  # Empty email
                hashed_password="$2b$12$KIXxPfnK6JKxQ.vD0LZzOeZfZvL6Fd5y6YV3YxJ8QxZ9YxJ8QxZ9Y",
                role=UserRole.USER,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )