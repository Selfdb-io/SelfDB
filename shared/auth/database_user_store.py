"""
Database User Store Implementation for SelfDB.

This module provides a database-backed implementation of the UserStoreInterface
using PostgreSQL with asyncpg for high-performance user operations.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
import bcrypt
import uuid

from shared.auth.user_store import UserStoreInterface, UserNotFoundError, UserAlreadyExistsError, UserValidationError, UserStoreError
from shared.models.user import User, UserRole
from shared.database.connection_manager import DatabaseConnectionManager

logger = logging.getLogger(__name__)


class DatabaseUserStore(UserStoreInterface):
    """
    Database implementation of user storage using PostgreSQL.

    This class provides all user CRUD operations with proper error handling,
    validation, and database transaction management.
    """

    def __init__(self, db_manager: DatabaseConnectionManager):
        """
        Initialize database user store.

        Args:
            db_manager: Database connection manager instance
        """
        self.db_manager = db_manager

    # Removed pool initialization - PgBouncer handles connection pooling automatically

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User object if found, None if not found
        """
        try:
            logger.info(f"Getting user by email: {email}")
            async with self.db_manager.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, email, password_hash, first_name, last_name, role, is_active,
                           created_at, updated_at, last_login_at
                    FROM users
                    WHERE email = $1
                    """,
                    email
                )

                if row:
                    return User(
                        id=row['id'],
                        email=row['email'],
                        hashed_password=row['password_hash'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        role=UserRole(row['role']),
                        is_active=row['is_active'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        last_login_at=row['last_login_at']
                    )
                return None

        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            logger.error(f"Error type: {type(e)}")
            raise UserStoreError(f"Failed to get user by email: {e}")

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            User object if found, None if not found
        """
        try:
            async with self.db_manager.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, email, password_hash, first_name, last_name, role, is_active,
                           created_at, updated_at, last_login_at
                    FROM users
                    WHERE id = $1
                    """,
                    user_id
                )

                if row:
                    return User(
                        id=row['id'],
                        email=row['email'],
                        hashed_password=row['password_hash'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        role=UserRole(row['role']),
                        is_active=row['is_active'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        last_login_at=row['last_login_at']
                    )
                return None

        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            raise UserStoreError(f"Failed to get user by ID: {e}")

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
            UserAlreadyExistsError: If user already exists
            UserValidationError: If validation fails
        """
        try:
            # Validate role
            if role not in ["USER", "ADMIN"]:
                raise UserValidationError(f"Invalid role: {role}")

            user_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            async with self.db_manager.acquire() as conn:
                async with conn.transaction():
                    # Check if user already exists
                    existing = await conn.fetchval(
                        "SELECT id FROM users WHERE email = $1",
                        email
                    )

                    if existing:
                        raise UserAlreadyExistsError(f"User with email {email} already exists")

                    # Insert new user
                    await conn.execute(
                        """
                        INSERT INTO users (id, email, password_hash, first_name, last_name, role, is_active, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        user_id, email, password_hash, first_name, last_name, role, True, now, now
                    )

                    # Fetch and return the created user
                    row = await conn.fetchrow(
                        """
                        SELECT id, email, password_hash, first_name, last_name, role, is_active,
                               created_at, updated_at, last_login_at
                        FROM users
                        WHERE id = $1
                        """,
                        user_id
                    )

                    return User(
                        id=row['id'],
                        email=row['email'],
                        hashed_password=row['password_hash'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        role=UserRole(row['role']),
                        is_active=row['is_active'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        last_login_at=row['last_login_at']
                    )

        except UserAlreadyExistsError:
            raise
        except UserValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            raise UserStoreError(f"Failed to create user: {e}")

    async def update_user(self, user: User) -> User:
        """
        Update existing user.

        Args:
            user: User object with updated data

        Returns:
            Updated User object

        Raises:
            UserNotFoundError: If user not found
            UserValidationError: If validation fails
        """
        try:
            now = datetime.now(timezone.utc)

            async with self.db_manager.acquire() as conn:
                async with conn.transaction():
                    # Update user
                    result = await conn.execute(
                        """
                        UPDATE users
                        SET email = $2, first_name = $3, last_name = $4, role = $5,
                            is_active = $6, updated_at = $7
                        WHERE id = $1
                        """,
                        user.id, user.email, user.first_name, user.last_name,
                        user.role.value, user.is_active, now
                    )

                    if result == "UPDATE 0":
                        raise UserNotFoundError(f"User with ID {user.id} not found")

                    # Fetch and return updated user
                    row = await conn.fetchrow(
                        """
                        SELECT id, email, password_hash, first_name, last_name, role, is_active,
                               created_at, updated_at, last_login_at
                        FROM users
                        WHERE id = $1
                        """,
                        user.id
                    )

                    return User(
                        id=row['id'],
                        email=row['email'],
                        hashed_password=row['password_hash'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        role=UserRole(row['role']),
                        is_active=row['is_active'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        last_login_at=row['last_login_at']
                    )

        except UserNotFoundError:
            raise
        except UserValidationError:
            raise
        except Exception as e:
            logger.error(f"Error updating user {user.id}: {e}")
            raise UserStoreError(f"Failed to update user: {e}")

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user by ID.

        Args:
            user_id: User's unique identifier

        Returns:
            True if user was deleted, False if user not found
        """
        try:
            async with self.db_manager.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM users WHERE id = $1",
                    user_id
                )

                return result == "DELETE 1"

        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise UserStoreError(f"Failed to delete user: {e}")

    async def list_users(self, limit: int = 50, offset: int = 0) -> List[User]:
        """
        List users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of User objects
        """
        try:
            async with self.db_manager.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, email, password_hash, first_name, last_name, role, is_active,
                           created_at, updated_at, last_login_at
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit, offset
                )

                return [
                    User(
                        id=row['id'],
                        email=row['email'],
                        hashed_password=row['password_hash'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        role=UserRole(row['role']),
                        is_active=row['is_active'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        last_login_at=row['last_login_at']
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise UserStoreError(f"Failed to list users: {e}")

    async def update_user_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User's unique identifier
        """
        try:
            now = datetime.now(timezone.utc)

            async with self.db_manager.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET last_login_at = $1 WHERE id = $2",
                    now, user_id
                )

        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            raise UserStoreError(f"Failed to update last login: {e}")

    async def update_user_password(self, user_id: str, password_hash: str) -> bool:
        """
        Update a user's password hash in the database.

        Args:
            user_id: User's unique identifier
            password_hash: Bcrypt-hashed password

        Returns:
            True if update succeeded

        Raises:
            UserNotFoundError: If the user does not exist
            UserStoreError: On other failures
        """
        try:
            now = datetime.now(timezone.utc)

            async with self.db_manager.acquire() as conn:
                async with conn.transaction():
                    result = await conn.execute(
                        """
                        UPDATE users
                        SET password_hash = $2, updated_at = $3
                        WHERE id = $1
                        """,
                        user_id, password_hash, now
                    )

                    # asyncpg returns strings like 'UPDATE 1' on success
                    if result == "UPDATE 0":
                        raise UserNotFoundError(f"User with ID {user_id} not found")

            return True

        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {e}")
            raise UserStoreError(f"Failed to update user password: {e}")

    async def is_email_available(self, email: str) -> bool:
        """
        Check if email address is available for registration.

        Args:
            email: Email address to check

        Returns:
            True if email is available, False if already taken
        """
        try:
            async with self.db_manager.acquire() as conn:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM users WHERE email = $1",
                    email
                )
                return count == 0

        except Exception as e:
            logger.error(f"Error checking email availability {email}: {e}")
            raise UserStoreError(f"Failed to check email availability: {e}")

    async def count_users(self) -> int:
        """
        Count total number of users.

        Returns:
            Total number of users in the system
        """
        try:
            async with self.db_manager.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM users")
                return count

        except Exception as e:
            logger.error(f"Error counting users: {e}")
            raise UserStoreError(f"Failed to count users: {e}")


