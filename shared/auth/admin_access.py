"""
Admin access control module for admin-only operations.

Handles access control for operations that require ADMIN role:
- User management (list all users, delete any user)
- System administration (config, logs, backups)
- Resource access (can access any user's private resources)
"""

import logging
from typing import Optional, Dict, Any, List
from .jwt_service import JWTService


logger = logging.getLogger(__name__)


class AdminAccessControl:
    """Manages access control for admin-only operations."""
    
    def __init__(
        self,
        api_key: str,
        jwt_service: JWTService,
        enable_logging: bool = True,
        strict_admin_check: bool = True,
        admin_operations: Optional[List[str]] = None
    ):
        """
        Initialize admin access control.
        
        Args:
            api_key: Valid API key for first-layer validation
            jwt_service: JWT service for token validation
            enable_logging: Enable access logging
            strict_admin_check: Strict validation of admin privileges
            admin_operations: List of admin-only operations (if None, use default)
        """
        if not jwt_service:
            raise ValueError("JWT service must be provided")
        
        self.api_key = api_key
        self.jwt_service = jwt_service
        self.enable_logging = enable_logging
        self.strict_admin_check = strict_admin_check
        
        # Default admin operations
        if admin_operations is None:
            self.admin_operations = {
                "list_users",
                "delete_user", 
                "update_system_config",
                "view_system_logs",
                "manage_api_keys",
                "backup_database",
                "restore_database",
                "impersonate_user",
                "list_cors_origins",
                "add_cors_origin", 
                "remove_cors_origin",
                "view_function_logs"
            }
        else:
            self.admin_operations = set(admin_operations)
    
    async def check_admin_operation(
        self,
        operation: str,
        api_key: Optional[str],
        jwt_token: Optional[str],
        **kwargs
    ) -> bool:
        """
        Check if admin operation is allowed.
        
        Args:
            operation: Operation being performed
            api_key: API key from request
            jwt_token: JWT token from request
            **kwargs: Additional operation parameters
            
        Returns:
            True if operation is allowed, False otherwise
        """
        # Must be a valid admin operation
        if operation not in self.admin_operations:
            if self.enable_logging:
                logger.warning(f"Admin operation denied: {operation} not in admin operations list")
            return False
        
        # First layer: API key validation
        if not api_key or api_key != self.api_key:
            if self.enable_logging:
                logger.warning(f"Admin operation denied: Invalid API key for {operation}")
            return False
        
        # Second layer: JWT validation
        if not jwt_token:
            if self.enable_logging:
                logger.warning(f"Admin operation denied: Missing JWT token for {operation}")
            return False
        
        # Validate JWT token
        payload = self.jwt_service.validate_access_token(jwt_token)
        if not payload:
            if self.enable_logging:
                logger.warning(f"Admin operation denied: Invalid JWT token for {operation}")
            return False
        
        # Check if user is active
        if not payload.get("is_active", True):
            if self.enable_logging:
                logger.warning(f"Admin operation denied: Inactive user {payload.get('user_id')} for {operation}")
            return False
        
        # Check admin role
        user_role = payload.get("role", "USER")
        if user_role != "ADMIN":
            if self.enable_logging:
                logger.warning(f"Admin operation denied: User {payload.get('user_id')} with role {user_role} attempted {operation}")
            return False
        
        # Admin operation granted
        if self.enable_logging:
            logger.info(f"Admin operation granted: User {payload.get('user_id')} performing {operation}")
        return True
    
    async def check_admin_resource_access(
        self,
        resource_type: str,
        resource: Any,
        api_key: Optional[str],
        jwt_token: Optional[str]
    ) -> bool:
        """
        Check if admin can access any user's resource.
        
        Args:
            resource_type: Type of resource (bucket, table, file)
            resource: The resource object
            api_key: API key from request
            jwt_token: JWT token from request
            
        Returns:
            True if admin access is allowed, False otherwise
        """
        # Resource must exist
        if resource is None:
            if self.enable_logging:
                logger.warning(f"Admin resource access denied: {resource_type} not found")
            return False
        
        # First layer: API key validation
        if not api_key or api_key != self.api_key:
            if self.enable_logging:
                logger.warning(f"Admin resource access denied: Invalid API key for {resource_type}")
            return False
        
        # Second layer: JWT validation
        if not jwt_token:
            if self.enable_logging:
                logger.warning(f"Admin resource access denied: Missing JWT token for {resource_type}")
            return False
        
        # Validate JWT token
        payload = self.jwt_service.validate_access_token(jwt_token)
        if not payload:
            if self.enable_logging:
                logger.warning(f"Admin resource access denied: Invalid JWT token for {resource_type}")
            return False
        
        # Check if user is active
        if not payload.get("is_active", True):
            if self.enable_logging:
                logger.warning(f"Admin resource access denied: Inactive user {payload.get('user_id')} for {resource_type}")
            return False
        
        # Check admin role
        user_role = payload.get("role", "USER")
        if user_role != "ADMIN":
            if self.enable_logging:
                logger.warning(f"Admin resource access denied: User {payload.get('user_id')} with role {user_role} attempted to access {resource_type}")
            return False
        
        # Admin can access any resource
        if self.enable_logging:
            logger.info(f"Admin resource access granted: User {payload.get('user_id')} accessing {resource_type}")
        return True
    
    async def get_admin_access_error(
        self,
        operation: str,
        api_key: Optional[str],
        jwt_token: Optional[str]
    ) -> Dict[str, Any]:
        """
        Get error details for admin access denial.
        
        Args:
            operation: Operation being attempted
            api_key: API key from request
            jwt_token: JWT token from request
            
        Returns:
            Error details dictionary
        """
        # Check API key first
        if not api_key:
            return {
                "code": "API_KEY_REQUIRED",
                "message": "API key is required for admin operations",
                "details": {"operation": operation}
            }
        
        if api_key != self.api_key:
            return {
                "code": "INVALID_API_KEY", 
                "message": "Provided API key is invalid",
                "details": {"operation": operation}
            }
        
        # Check JWT token
        if not jwt_token:
            return {
                "code": "JWT_REQUIRED",
                "message": "JWT token is required for admin operations",
                "details": {"operation": operation}
            }
        
        # Validate JWT
        payload = self.jwt_service.validate_access_token(jwt_token)
        if not payload:
            return {
                "code": "INVALID_JWT",
                "message": "Provided JWT token is invalid or expired",
                "details": {"operation": operation}
            }
        
        # Check if user is active
        if not payload.get("is_active", True):
            return {
                "code": "USER_INACTIVE",
                "message": "User account is inactive",
                "details": {
                    "operation": operation,
                    "user_id": payload.get("user_id")
                }
            }
        
        # Must be insufficient privileges
        return {
            "code": "INSUFFICIENT_PRIVILEGES",
            "message": "ADMIN role required for this operation",
            "details": {
                "operation": operation,
                "user_role": payload.get("role", "USER"),
                "user_id": payload.get("user_id")
            }
        }