"""
Authentication endpoints implementation.

Handles user registration, login, token refresh, and logout operations.
"""

import logging
import re
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Protocol
from .jwt_service import JWTService
from .user_store import UserStoreInterface
from shared.models.user import User


logger = logging.getLogger(__name__)


# Use the proper UserStoreInterface instead of defining our own protocol
UserStore = UserStoreInterface


class AuthEndpoints:
    """Authentication endpoints for user management."""
    
    def __init__(
        self,
        api_key: str,
        jwt_service: JWTService,
        user_store: UserStore,
        enable_rate_limiting: bool = False,
        max_attempts_per_minute: int = 10
    ):
        """
        Initialize authentication endpoints.
        
        Args:
            api_key: Valid API key for first-layer validation
            jwt_service: JWT service for token operations
            user_store: User storage implementation
            enable_rate_limiting: Enable rate limiting protection
            max_attempts_per_minute: Max attempts per minute per IP
        """
        if not jwt_service:
            raise ValueError("JWT service must be provided")
        if not user_store:
            raise ValueError("User store must be provided")
        
        self.api_key = api_key
        self.jwt_service = jwt_service
        self.user_store = user_store
        self.enable_rate_limiting = enable_rate_limiting
        self.max_attempts_per_minute = max_attempts_per_minute
        
        # Simple in-memory rate limiting (in production use Redis)
        self._rate_limit_store: Dict[str, Dict[str, Any]] = {}
    
    def _validate_api_key(self, api_key: Optional[str]) -> bool:
        """Validate API key."""
        return api_key is not None and api_key == self.api_key
    
    def _validate_password_strength(self, password: str) -> bool:
        """Validate password meets minimum requirements."""
        if len(password) < 8:
            return False
        # Could add more requirements: uppercase, numbers, special chars
        return True
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    def _check_rate_limit(self, key: str) -> bool:
        """Check if rate limit is exceeded for key."""
        if not self.enable_rate_limiting:
            return False
        
        now = datetime.now(timezone.utc)
        minute_key = now.strftime("%Y-%m-%d %H:%M")
        
        if key not in self._rate_limit_store:
            self._rate_limit_store[key] = {}
        
        if minute_key not in self._rate_limit_store[key]:
            self._rate_limit_store[key][minute_key] = 0
        
        self._rate_limit_store[key][minute_key] += 1
        
        # Clean old entries
        cutoff = now - timedelta(minutes=5)
        for old_key in list(self._rate_limit_store[key].keys()):
            try:
                old_time = datetime.strptime(old_key, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                if old_time < cutoff:
                    del self._rate_limit_store[key][old_key]
            except ValueError:
                continue
        
        return self._rate_limit_store[key][minute_key] > self.max_attempts_per_minute
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def _serialize_user(self, user: User) -> Dict[str, Any]:
        """Serialize user object for response."""
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "is_active": user.is_active,
            "first_name": getattr(user, 'first_name', None),
            "last_name": getattr(user, 'last_name', None),
            "created_at": getattr(user, 'created_at', None).isoformat() if getattr(user, 'created_at', None) else None,
            "updated_at": getattr(user, 'updated_at', None).isoformat() if getattr(user, 'updated_at', None) else None,
            "last_login_at": getattr(user, 'last_login_at', None).isoformat() if getattr(user, 'last_login_at', None) else None
        }
    
    async def register(
        self,
        api_key: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            api_key: API key for validation
            email: User email address
            password: User password
            first_name: User's first name
            last_name: User's last name
            **kwargs: Additional user data
            
        Returns:
            Registration result with tokens or error
        """
        # Rate limiting
        if self._check_rate_limit(f"register:{email}"):
            return {
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many registration attempts. Please try again later.",
                    "details": {"email": email}
                }
            }
        
        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Provided API key is invalid",
                    "details": {}
                }
            }
        
        # Validate required fields
        if not all([email, password, first_name, last_name]):
            missing_fields = []
            if not email: missing_fields.append("email")
            if not password: missing_fields.append("password") 
            if not first_name: missing_fields.append("first_name")
            if not last_name: missing_fields.append("last_name")
            
            return {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Missing required fields: {', '.join(missing_fields)}",
                    "details": {"missing_fields": missing_fields}
                }
            }
        
        # Validate email format
        if not self._validate_email(email):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_EMAIL",
                    "message": "Invalid email format",
                    "details": {"email": email}
                }
            }
        
        # Validate password strength
        if not self._validate_password_strength(password):
            return {
                "success": False,
                "error": {
                    "code": "WEAK_PASSWORD",
                    "message": "Password must be at least 8 characters long",
                    "details": {}
                }
            }
        
        # Check if user already exists
        existing_user = await self.user_store.get_user_by_email(email)
        if existing_user:
            return {
                "success": False,
                "error": {
                    "code": "USER_ALREADY_EXISTS",
                    "message": f"User with email {email} already exists",
                    "details": {"email": email}
                }
            }
        
        # Hash password and create user
        password_hash = self._hash_password(password)
        new_user = await self.user_store.create_user(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            role="USER"
        )
        
        # Generate tokens
        user_payload = {
            "user_id": new_user.id,
            "email": new_user.email,
            "role": new_user.role,
            "is_active": new_user.is_active
        }
        
        access_token = self.jwt_service.generate_access_token(user_payload)
        refresh_token = self.jwt_service.generate_refresh_token(user_payload)
        
        logger.info(f"New user registered: {email}")
        
        return {
            "success": True,
            "user": self._serialize_user(new_user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.jwt_service.access_token_expire_minutes * 60
        }
    
    async def login(
        self,
        api_key: str,
        email: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Login user and return tokens.
        
        Args:
            api_key: API key for validation
            email: User email
            password: User password
            
        Returns:
            Login result with tokens or error
        """
        # Rate limiting
        if self._check_rate_limit(f"login:{email}"):
            return {
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many login attempts. Please try again later.",
                    "details": {"email": email}
                }
            }
        
        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Provided API key is invalid",
                    "details": {}
                }
            }
        
        # Get user by email
        user = await self.user_store.get_user_by_email(email)
        if not user:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                    "details": {}
                }
            }
        
        # Verify password
        if not self._verify_password(password, user.hashed_password):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                    "details": {}
                }
            }
        
        # Check if user is active
        if not user.is_active:
            return {
                "success": False,
                "error": {
                    "code": "ACCOUNT_INACTIVE",
                    "message": "User account is inactive",
                    "details": {"user_id": user.id}
                }
            }
        
        # Update last login
        await self.user_store.update_user_last_login(user.id)

        # Fetch updated user to get the latest last_login_at
        updated_user = await self.user_store.get_user_by_email(email)
        if updated_user:
            user = updated_user

        # Generate tokens
        user_payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
        
        access_token = self.jwt_service.generate_access_token(user_payload)
        refresh_token = self.jwt_service.generate_refresh_token(user_payload)
        
        logger.info(f"User logged in: {email}")
        
        return {
            "success": True,
            "user": self._serialize_user(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.jwt_service.access_token_expire_minutes * 60
        }
    
    async def refresh_token(
        self,
        api_key: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            api_key: API key for validation
            refresh_token: Valid refresh token
            
        Returns:
            New tokens or error
        """
        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Provided API key is invalid",
                    "details": {}
                }
            }
        
        # Validate refresh token
        payload = self.jwt_service.validate_refresh_token(refresh_token)
        if not payload:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_REFRESH_TOKEN",
                    "message": "Invalid or expired refresh token",
                    "details": {}
                }
            }
        
        # Get current user
        user = await self.user_store.get_user_by_id(payload["user_id"])
        if not user:
            return {
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User no longer exists",
                    "details": {"user_id": payload["user_id"]}
                }
            }
        
        # Check if user is still active
        if not user.is_active:
            return {
                "success": False,
                "error": {
                    "code": "ACCOUNT_INACTIVE",
                    "message": "User account is inactive",
                    "details": {"user_id": user.id}
                }
            }
        
        # Blacklist old refresh token
        self.jwt_service.blacklist_token(refresh_token)
        
        # Generate new tokens
        user_payload = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
        
        new_access_token = self.jwt_service.generate_access_token(user_payload)
        new_refresh_token = self.jwt_service.generate_refresh_token(user_payload)
        
        logger.info(f"Token refreshed for user: {user.email}")
        
        return {
            "success": True,
            "user": self._serialize_user(user),
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": self.jwt_service.access_token_expire_minutes * 60
        }
    
    async def logout(
        self,
        api_key: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Logout user by blacklisting tokens.
        
        Args:
            api_key: API key for validation
            access_token: Access token to blacklist
            refresh_token: Refresh token to blacklist
            
        Returns:
            Logout result
        """
        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Provided API key is invalid",
                    "details": {}
                }
            }
        
        # Blacklist tokens (if valid)
        if access_token:
            self.jwt_service.blacklist_token(access_token)
        if refresh_token:
            self.jwt_service.blacklist_token(refresh_token)
        
        logger.info("User logged out")
        
        return {
            "success": True,
            "message": "Successfully logged out"
        }
    
    async def get_current_user(
        self,
        api_key: str,
        access_token: str
    ) -> Dict[str, Any]:
        """
        Get current user from access token.
        
        Args:
            api_key: API key for validation
            access_token: Valid access token
            
        Returns:
            Current user data or error
        """
        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Provided API key is invalid",
                    "details": {}
                }
            }
        
        # Validate access token
        payload = self.jwt_service.validate_access_token(access_token)
        if not payload:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_ACCESS_TOKEN",
                    "message": "Invalid or expired access token",
                    "details": {}
                }
            }
        
        # Get current user
        user = await self.user_store.get_user_by_id(payload["user_id"])
        if not user:
            return {
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User no longer exists",
                    "details": {"user_id": payload["user_id"]}
                }
            }
        
        return {
            "success": True,
            "user": self._serialize_user(user)
        }

    async def list_users(
        self,
        api_key: str,
        limit: int = 50,
        offset: int = 0,
        sort: str = "created_at:desc",
        filter_role: Optional[str] = None,
        filter_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        List users with pagination and filtering (admin only).

        Args:
            api_key: API key for validation
            limit: Maximum number of users to return
            offset: Number of users to skip
            sort: Sort field and direction (field:direction)
            filter_role: Filter by user role
            filter_active: Filter by active status

        Returns:
            Paginated list of users
        """
        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Provided API key is invalid",
                    "details": {}
                }
            }

        # Parse sort parameter
        sort_field, sort_direction = "created_at", "desc"
        if ":" in sort:
            sort_field, sort_direction = sort.split(":", 1)

        # Build filters
        filters = {}
        if filter_role:
            filters["role"] = filter_role
        if filter_active is not None:
            filters["is_active"] = filter_active

        try:
            # Get users from store (using the current interface)
            users = await self.user_store.list_users(limit=limit, offset=offset)

            # For now, we'll do filtering and sorting in memory
            # TODO: Update database_user_store to support filtering and sorting
            filtered_users = users

            # Apply role filter
            if filter_role:
                filtered_users = [u for u in filtered_users if u.role == filter_role]

            # Apply active filter
            if filter_active is not None:
                filtered_users = [u for u in filtered_users if u.is_active == filter_active]

            # Apply sorting (simple implementation)
            reverse = sort_direction.lower() == "desc"
            if sort_field == "created_at":
                filtered_users.sort(key=lambda u: u.created_at or datetime.min, reverse=reverse)
            elif sort_field == "email":
                filtered_users.sort(key=lambda u: u.email.lower(), reverse=reverse)

            # Get total count for pagination
            total_count = await self.user_store.count_users()

            return {
                "success": True,
                "users": [self._serialize_user(user) for user in filtered_users],
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
            }
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to list users",
                    "details": {}
                }
            }

    async def get_user_by_id(
        self,
        api_key: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get user by ID (admin only).

        Args:
            api_key: API key for validation
            user_id: User ID to retrieve

        Returns:
            User details or error
        """
        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Provided API key is invalid",
                    "details": {}
                }
            }

        try:
            user = await self.user_store.get_user_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": {
                        "code": "USER_NOT_FOUND",
                        "message": "User not found",
                        "details": {"user_id": user_id}
                    }
                }

            return {
                "success": True,
                "user": self._serialize_user(user)
            }
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to get user",
                    "details": {}
                }
            }

    async def update_user(
        self,
        api_key: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user (admin only).

        Args:
            api_key: API key for validation
            user_id: User ID to update
            updates: Fields to update

        Returns:
            Updated user or error
        """
        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Provided API key is invalid",
                    "details": {}
                }
            }

        # Validate updates
        allowed_fields = {"email", "role", "is_active", "first_name", "last_name"}
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_UPDATE",
                    "message": f"Invalid fields for update: {', '.join(invalid_fields)}",
                    "details": {"invalid_fields": list(invalid_fields)}
                }
            }

        try:
            # Check if user exists
            existing_user = await self.user_store.get_user_by_id(user_id)
            if not existing_user:
                return {
                    "success": False,
                    "error": {
                        "code": "USER_NOT_FOUND",
                        "message": "User not found",
                        "details": {"user_id": user_id}
                    }
                }

            # Create updated user object
            from shared.models.user import User, UserRole

            updated_fields = dict(existing_user.__dict__)
            updated_fields.update(updates)

            # Convert role string to UserRole enum if needed
            if 'role' in updates and isinstance(updates['role'], str):
                updated_fields['role'] = UserRole(updates['role'])

            # Create User object with updated fields
            updated_user_obj = User(**updated_fields)

            # Update user
            updated_user = await self.user_store.update_user(updated_user_obj)
            if not updated_user:
                return {
                    "success": False,
                    "error": {
                        "code": "UPDATE_FAILED",
                        "message": "Failed to update user",
                        "details": {"user_id": user_id}
                    }
                }

            return {
                "success": True,
                "user": self._serialize_user(updated_user)
            }
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to update user",
                    "details": {}
                }
            }

    async def delete_user(
        self,
        api_key: str,
        user_id: str,
        soft_delete: bool = True
    ) -> Dict[str, Any]:
        """
        Delete user (admin only).

        Args:
            api_key: API key for validation
            user_id: User ID to delete
            soft_delete: If True, mark as inactive instead of deleting

        Returns:
            Deletion result
        """
        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Provided API key is invalid",
                    "details": {}
                }
            }

        try:
            # Check if user exists
            existing_user = await self.user_store.get_user_by_id(user_id)
            if not existing_user:
                return {
                    "success": False,
                    "error": {
                        "code": "USER_NOT_FOUND",
                        "message": "User not found",
                        "details": {"user_id": user_id}
                    }
                }

            # Delete user
            if soft_delete:
                # Soft delete - mark as inactive
                # Create updated user object
                from shared.models.user import User

                updated_fields = dict(existing_user.__dict__)
                updated_fields["is_active"] = False

                # Create User object with updated fields
                updated_user_obj = User(**updated_fields)

                # Update user
                result = await self.user_store.update_user(updated_user_obj)
                success = result is not None
            else:
                # Hard delete
                success = await self.user_store.delete_user(user_id)

            if not success:
                return {
                    "success": False,
                    "error": {
                        "code": "DELETE_FAILED",
                        "message": "Failed to delete user",
                        "details": {"user_id": user_id}
                    }
                }

            return {
                "success": True,
                "message": "User deleted successfully",
                "soft_deleted": soft_delete
            }
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to delete user",
                    "details": {}
                }
            }

    async def change_password(
        self,
        api_key: str,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Change password for an authenticated user.
        """
        # Rate limiting
        if self._check_rate_limit(f"change_password:{user_id}"):
            return {
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many attempts. Please try again later.",
                    "details": {"user_id": user_id}
                }
            }

        # Validate API key
        if not self._validate_api_key(api_key):
            return {
                "success": False,
                "error": {"code": "INVALID_API_KEY", "message": "Provided API key is invalid", "details": {}}
            }

        # Fetch user
        user = await self.user_store.get_user_by_id(user_id)
        if not user:
            return {"success": False, "error": {"code": "USER_NOT_FOUND", "message": "User not found", "details": {"user_id": user_id}}}

        # Verify current password
        if not self._verify_password(current_password, user.hashed_password):
            return {"success": False, "error": {"code": "INVALID_CURRENT_PASSWORD", "message": "Current password is incorrect", "details": {}}}

        # Validate new password strength
        if not self._validate_password_strength(new_password):
            return {"success": False, "error": {"code": "WEAK_PASSWORD", "message": "Password must be at least 8 characters long", "details": {}}}

        # Hash and store new password
        password_hash = self._hash_password(new_password)
        try:
            updated = await self.user_store.update_user_password(user_id=user_id, password_hash=password_hash)
            if not updated:
                return {"success": False, "error": {"code": "UPDATE_FAILED", "message": "Failed to update password", "details": {}}}

            # Optionally blacklist tokens - attempt to invalidate any refresh tokens for this user
            # If jwt_service supports per-user invalidation, call it here. We'll at least log.
            logger.info(f"Password changed for user {user.email}")

            return {"success": True, "message": "Password changed successfully"}
        except Exception as e:
            logger.error(f"Error changing password for {user_id}: {str(e)}")
            return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "Failed to change password", "details": {}}}

    async def admin_set_user_password(
        self,
        api_key: str,
        admin_user_id: str,
        target_user_id: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Admin operation to set/reset another user's password.
        """
        # Validate API key
        if not self._validate_api_key(api_key):
            return {"success": False, "error": {"code": "INVALID_API_KEY", "message": "Provided API key is invalid", "details": {}}}

        # Verify admin privileges - fetch admin user and ensure role
        admin_user = await self.user_store.get_user_by_id(admin_user_id)
        if not admin_user:
            return {"success": False, "error": {"code": "ADMIN_NOT_FOUND", "message": "Admin user not found", "details": {"admin_user_id": admin_user_id}}}
        if getattr(admin_user, 'role', None) != "ADMIN" and getattr(admin_user, 'role', None) != "UserRole.ADMIN":
            # Try enum comparison
            if hasattr(admin_user, 'role') and str(admin_user.role) != "ADMIN":
                return {"success": False, "error": {"code": "INSUFFICIENT_PRIVILEGES", "message": "Admin access required", "details": {}}}

        # Validate new password strength
        if not self._validate_password_strength(new_password):
            return {"success": False, "error": {"code": "WEAK_PASSWORD", "message": "Password must be at least 8 characters long", "details": {}}}

        # Fetch target user
        target_user = await self.user_store.get_user_by_id(target_user_id)
        if not target_user:
            return {"success": False, "error": {"code": "USER_NOT_FOUND", "message": "Target user not found", "details": {"user_id": target_user_id}}}

        # Hash and update
        password_hash = self._hash_password(new_password)
        try:
            updated = await self.user_store.update_user_password(user_id=target_user_id, password_hash=password_hash)
            if not updated:
                return {"success": False, "error": {"code": "UPDATE_FAILED", "message": "Failed to update password", "details": {}}}

            logger.info(f"Admin {admin_user.email} set password for user {target_user.email}")
            return {"success": True, "message": "Password updated successfully"}
        except Exception as e:
            logger.error(f"Error admin setting password for {target_user_id}: {str(e)}")
            return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": "Failed to set password", "details": {}}}