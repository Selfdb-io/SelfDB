"""
Private access control module for API key + JWT authentication.

Handles access control for private resources that require both:
- Valid API key (first layer)  
- Valid JWT token (second layer)
"""

import logging
from typing import Optional, Dict, Any
from .jwt_service import JWTService


logger = logging.getLogger(__name__)


class PrivateAccessControl:
    """Manages access control for private resources requiring API key + JWT."""
    
    def __init__(
        self,
        api_key: str,
        jwt_service: JWTService,
        enable_logging: bool = True,
        check_user_active: bool = True
    ):
        """
        Initialize private access control.
        
        Args:
            api_key: Valid API key for first-layer validation
            jwt_service: JWT service for token validation
            enable_logging: Enable access logging
            check_user_active: Check if user is active in JWT payload
        """
        if not jwt_service:
            raise ValueError("JWT service must be provided")
        
        self.api_key = api_key
        self.jwt_service = jwt_service
        self.enable_logging = enable_logging
        self.check_user_active = check_user_active
    
    async def check_private_access(
        self,
        resource_type: str,
        resource: Any,
        api_key: Optional[str],
        jwt_token: Optional[str],
        operation: Optional[str] = None,
        check_ownership: bool = False
    ) -> bool:
        """
        Check if private access is allowed for a resource.
        
        Requires both valid API key AND valid JWT token.
        
        Args:
            resource_type: Type of resource (bucket, table, file)
            resource: The resource object
            api_key: API key from request
            jwt_token: JWT token from request
            operation: Operation being performed (create, read, update, delete)
            check_ownership: Whether to check if user owns the resource
            
        Returns:
            True if access is allowed, False otherwise
        """
        # Resource must exist
        if resource is None:
            if self.enable_logging:
                logger.warning(f"Access denied: {resource_type} not found")
            return False
        
        # First layer: API key validation
        if not api_key or api_key != self.api_key:
            if self.enable_logging:
                logger.warning(f"Access denied: Invalid API key for {resource_type}")
            return False
        
        # Second layer: JWT validation
        if not jwt_token:
            if self.enable_logging:
                logger.warning(f"Access denied: Missing JWT token for {resource_type}")
            return False
        
        # Validate JWT token
        payload = self.jwt_service.validate_access_token(jwt_token)
        if not payload:
            if self.enable_logging:
                logger.warning(f"Access denied: Invalid JWT token for {resource_type}")
            return False
        
        # Check if user is active
        if self.check_user_active and not payload.get("is_active", True):
            if self.enable_logging:
                logger.warning(f"Access denied: Inactive user {payload.get('user_id')} for {resource_type}")
            return False
        
        # Check ownership if required
        if check_ownership:
            user_role = payload.get("role", "USER")
            user_id = payload.get("user_id")
            resource_owner_id = getattr(resource, "owner_id", None)
            
            # Admin users can access any resource
            if user_role == "ADMIN":
                if self.enable_logging:
                    logger.info(f"Private access granted: Admin user {user_id} accessing {resource_type}")
                return True
            
            # Regular users can only access their own resources
            if resource_owner_id != user_id:
                if self.enable_logging:
                    logger.warning(f"Access denied: User {user_id} cannot access {resource_type} owned by {resource_owner_id}")
                return False
        
        # Access granted
        if self.enable_logging:
            logger.info(f"Private access granted: User {payload.get('user_id')} accessing {resource_type}")
        return True
    
    async def check_file_operation(
        self,
        operation: str,
        api_key: Optional[str],
        jwt_token: Optional[str],
        bucket: Any,
        **kwargs
    ) -> bool:
        """
        Check if file operation is allowed on private bucket.
        
        Args:
            operation: File operation (upload, download, delete, list)
            api_key: API key from request
            jwt_token: JWT token from request
            bucket: Bucket for the operation
            **kwargs: Additional operation parameters
            
        Returns:
            True if operation is allowed, False otherwise
        """
        # File operations depend on bucket access
        return await self.check_private_access(
            resource_type="bucket",
            resource=bucket,
            api_key=api_key,
            jwt_token=jwt_token,
            operation=operation,
            check_ownership=True
        )
    
    async def get_access_error(
        self,
        resource_type: str,
        resource: Any,
        api_key: Optional[str],
        jwt_token: Optional[str]
    ) -> Dict[str, Any]:
        """
        Get error details for private access denial.
        
        Args:
            resource_type: Type of resource
            resource: The resource object
            api_key: API key from request
            jwt_token: JWT token from request
            
        Returns:
            Error details dictionary
        """
        # Check API key first
        if not api_key:
            return {
                "code": "API_KEY_REQUIRED",
                "message": "API key is required for private resource access",
                "details": {"resource_type": resource_type}
            }
        
        if api_key != self.api_key:
            return {
                "code": "INVALID_API_KEY",
                "message": "Provided API key is invalid",
                "details": {"resource_type": resource_type}
            }
        
        # Check JWT token
        if not jwt_token:
            return {
                "code": "JWT_REQUIRED",
                "message": "JWT token is required for private resource access",
                "details": {"resource_type": resource_type}
            }
        
        # Validate JWT
        payload = self.jwt_service.validate_access_token(jwt_token)
        if not payload:
            return {
                "code": "INVALID_JWT",
                "message": "Provided JWT token is invalid or expired",
                "details": {"resource_type": resource_type}
            }
        
        # Check if user is active
        if self.check_user_active and not payload.get("is_active", True):
            return {
                "code": "USER_INACTIVE",
                "message": "User account is inactive",
                "details": {
                    "resource_type": resource_type,
                    "user_id": payload.get("user_id")
                }
            }
        
        # Must be ownership or permission issue
        resource_id = None
        if resource_type == "bucket":
            resource_id = getattr(resource, 'id', None)
            details_key = "bucket_id"
        elif resource_type == "table":
            resource_id = getattr(resource, 'name', None)
            details_key = "table_name"
        else:
            details_key = f"{resource_type}_id"
            resource_id = getattr(resource, 'id', None)
        
        return {
            "code": "ACCESS_DENIED",
            "message": f"Access denied to {resource_type}. Check ownership or permissions.",
            "details": {
                "resource_type": resource_type,
                details_key: resource_id,
                "user_id": payload.get("user_id")
            }
        }