"""
Access control module for managing public/private resource access.

Handles the logic for determining if a resource can be accessed with:
- API key only (public resources)
- API key + JWT (private resources)
- API key + JWT with admin role (admin operations)
"""

import os
import logging
from typing import Optional, List, Dict, Any, Union


logger = logging.getLogger(__name__)


class AccessControl:
    """Manages access control for public and private resources."""
    
    def __init__(
        self,
        valid_api_keys: Optional[List[str]] = None,
        enable_logging: bool = True
    ):
        """
        Initialize access control.
        
        Args:
            valid_api_keys: List of valid API keys
            enable_logging: Enable access logging
        """
        self.valid_api_keys = valid_api_keys or [os.environ.get("API_KEY", "")]
        self.enable_logging = enable_logging
    
    async def check_public_access(
        self,
        resource_type: str,
        resource: Any,
        api_key: Optional[str],
        jwt_token: Optional[str],
        operation: Optional[str] = None
    ) -> bool:
        """
        Check if public access is allowed for a resource.
        
        Args:
            resource_type: Type of resource (bucket, table, file)
            resource: The resource object
            api_key: API key from request
            jwt_token: JWT token from request (not required for public)
            operation: Operation being performed (create, read, update, delete)
            
        Returns:
            True if access is allowed, False otherwise
        """
        # Resource must exist
        if resource is None:
            return False
        
        # API key is always required
        # If no valid_api_keys configured, accept any non-empty key (for testing)
        if not api_key:
            if self.enable_logging:
                logger.warning(f"Missing API key for {resource_type} access")
            return False
        
        # If valid_api_keys is configured and non-empty, validate against it
        if self.valid_api_keys and self.valid_api_keys[0] and api_key not in self.valid_api_keys:
            if self.enable_logging:
                logger.warning(f"Invalid API key for {resource_type} access")
            return False
        
        # Check if resource is public
        is_public = getattr(resource, 'public', False)
        
        if is_public:
            if self.enable_logging:
                resource_name = getattr(resource, 'name', 'unknown')
                logger.info(f"Public access granted to {resource_type}: {resource_name}")
            return True
        
        # Private resource requires JWT
        if self.enable_logging:
            logger.warning(f"Private {resource_type} requires JWT authentication")
        return False
    
    async def check_file_access(
        self,
        file: Any,
        bucket: Any,
        api_key: Optional[str],
        jwt_token: Optional[str]
    ) -> bool:
        """
        Check file access - files inherit bucket's public status.
        
        Args:
            file: File object
            bucket: Bucket containing the file
            api_key: API key from request
            jwt_token: JWT token from request
            
        Returns:
            True if access is allowed, False otherwise
        """
        # Files inherit public status from their bucket
        return await self.check_public_access(
            resource_type="bucket",
            resource=bucket,
            api_key=api_key,
            jwt_token=jwt_token
        )
    
    async def check_file_operation(
        self,
        operation: str,
        api_key: Optional[str],
        jwt_token: Optional[str],
        bucket: Any,
        **kwargs
    ) -> bool:
        """
        Check if file operation is allowed.
        
        Args:
            operation: File operation (upload, download, delete, list)
            api_key: API key from request
            jwt_token: JWT token from request
            bucket: Bucket for the operation
            **kwargs: Additional operation parameters
            
        Returns:
            True if operation is allowed, False otherwise
        """
        # File operations depend on bucket's public status
        return await self.check_public_access(
            resource_type="bucket",
            resource=bucket,
            api_key=api_key,
            jwt_token=jwt_token,
            operation=operation
        )
    
    async def check_table_query(
        self,
        type: str,
        table: Any,
        api_key: Optional[str],
        jwt_token: Optional[str],
        **kwargs
    ) -> bool:
        """
        Check if table query operation is allowed.
        
        Args:
            type: Query type (select, insert, update, delete)
            table: Table object
            api_key: API key from request
            jwt_token: JWT token from request
            **kwargs: Additional query parameters
            
        Returns:
            True if query is allowed, False otherwise
        """
        return await self.check_public_access(
            resource_type="table",
            resource=table,
            api_key=api_key,
            jwt_token=jwt_token,
            operation=type
        )
    
    async def get_access_error(
        self,
        resource_type: str,
        resource: Any,
        api_key: Optional[str],
        jwt_token: Optional[str]
    ) -> Dict[str, Any]:
        """
        Get error details for access denial.
        
        Args:
            resource_type: Type of resource
            resource: The resource object
            api_key: API key from request
            jwt_token: JWT token from request
            
        Returns:
            Error details dictionary
        """
        if not api_key:
            return {
                "code": "INVALID_API_KEY",
                "message": "API key is missing",
                "details": {"resource_type": resource_type}
            }
        
        # Check if API key is valid when validation is enabled
        if self.valid_api_keys and self.valid_api_keys[0] and api_key not in self.valid_api_keys:
            return {
                "code": "INVALID_API_KEY",
                "message": "Provided API key is invalid",
                "details": {"resource_type": resource_type}
            }
        
        # Must be a private resource accessed with API key only
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
            "code": "FORBIDDEN_PUBLIC",
            "message": "Operation requires JWT authentication for private resources. Use public buckets/tables for API Key-only access.",
            "details": {
                "resource_type": resource_type,
                details_key: resource_id
            }
        }
    
    async def check_webhook_access(
        self,
        webhook_token: str,
        function_id: str
    ) -> bool:
        """
        Check webhook access using webhook token.
        
        Webhooks use token-based auth, not JWT.
        
        Args:
            webhook_token: Webhook authentication token
            function_id: Function ID for the webhook
            
        Returns:
            True if webhook token is valid, False otherwise
        """
        # In a real implementation, this would validate the webhook token
        # against the function's stored webhook token
        # For now, we'll just check if a token is provided
        if webhook_token:
            if self.enable_logging:
                logger.info(f"Webhook access granted for function {function_id}")
            return True
        
        if self.enable_logging:
            logger.warning(f"Invalid webhook token for function {function_id}")
        return False