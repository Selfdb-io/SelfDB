"""
User Store Interface for SelfDB.

This module defines the interface for user storage operations that can be
implemented by different storage backends (database, in-memory, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Protocol
from shared.models.user import User


class UserStoreInterface(Protocol):
    """
    Protocol for user storage operations.

    This interface defines all the methods that user storage implementations
    must provide. It follows the Protocol pattern for better type checking
    and cleaner dependency injection.
    """

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User object if found, None if not found
        """
        ...

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            User object if found, None if not found
        """
        ...

    async def create_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        role: str = "USER"
    ) -> User:
        """
        Create a new user.

        Args:
            email: User's email address
            password_hash: Bcrypt hashed password
            first_name: User's first name
            last_name: User's last name
            role: User role (USER or ADMIN)

        Returns:
            Created User object

        Raises:
            ValueError: If user already exists or validation fails
        """
        ...

    async def update_user(self, user: User) -> User:
        """
        Update existing user.

        Args:
            user: User object with updated data

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found or validation fails
        """
        ...

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            True if user was deleted, False if user not found
        """
        ...

    async def list_users(self, limit: int = 50, offset: int = 0) -> List[User]:
        """
        List users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of User objects
        """
        ...

    async def update_user_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User's unique identifier
        """
        ...

    async def update_user_password(self, user_id: str, password_hash: str) -> bool:
        """
        Update a user's password hash.

        Args:
            user_id: User's unique identifier
            password_hash: Bcrypt-hashed password string

        Returns:
            True if update succeeded, False otherwise
        """
        ...

    async def is_email_available(self, email: str) -> bool:
        """
        Check if email address is available for registration.

        Args:
            email: Email address to check

        Returns:
            True if email is available, False if already taken
        """
        ...

    async def count_users(self) -> int:
        """
        Count total number of users.

        Returns:
            Total number of users in the system
        """
        ...


class UserStoreError(Exception):
    """Base exception for user store operations."""
    pass


class UserNotFoundError(UserStoreError):
    """Raised when user is not found."""
    pass


class UserAlreadyExistsError(UserStoreError):
    """Raised when trying to create a user that already exists."""
    pass


class UserValidationError(UserStoreError):
    """Raised when user data validation fails."""
    pass