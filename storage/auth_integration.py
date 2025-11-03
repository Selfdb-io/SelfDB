"""
Storage authentication integration module.

This module handles authentication middleware integration including API key validation,
permission checks, and access validation for buckets and files.
"""

import logging
from typing import Dict, Any

from .base import StorageBase


logger = logging.getLogger(__name__)


class AuthIntegrationMixin:
    """Mixin class for authentication integration functionality."""
    
    async def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Validate an API key using the authentication middleware.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Dictionary with validation result
        """
        try:
            if hasattr(self.auth_middleware, 'validate_api_key'):
                result = await self.auth_middleware.validate_api_key(api_key)
                return result
            
            # Fallback for tests without auth middleware
            return {
                "valid": False,
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": "Authentication service not available"
                }
            }
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return {
                "valid": False,
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": f"Auth service error: {str(e).lower()}"
                }
            }
    
    async def check_permission(
        self, 
        user_id: str, 
        resource: str, 
        action: str
    ) -> Dict[str, Any]:
        """
        Check user permissions using the authentication middleware.
        
        Args:
            user_id: User ID to check permissions for
            resource: Resource being accessed
            action: Action being performed
            
        Returns:
            Dictionary with permission result
        """
        try:
            if hasattr(self.auth_middleware, 'check_permission'):
                result = await self.auth_middleware.check_permission(
                    user_id, resource, action
                )
                return result
            
            # Fallback for tests without auth middleware
            return {
                "allowed": False,
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": "Authentication service not available"
                }
            }
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return {
                "allowed": False,
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": f"Auth service error: {str(e).lower()}"
                }
            }
    
    async def validate_bucket_access(
        self, 
        user_id: str, 
        bucket_id: str, 
        action: str
    ) -> Dict[str, Any]:
        """
        Validate user access to a bucket using the authentication middleware.
        
        Args:
            user_id: User ID requesting access
            bucket_id: Bucket ID to access
            action: Action being performed (read, write, delete)
            
        Returns:
            Dictionary with access validation result
        """
        try:
            if hasattr(self.auth_middleware, 'validate_bucket_access'):
                result = await self.auth_middleware.validate_bucket_access(
                    user_id, bucket_id, action
                )
                return result
            
            # Fallback for tests without auth middleware
            return {
                "allowed": False,
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": "Authentication service not available"
                }
            }
            
        except Exception as e:
            logger.error(f"Bucket access validation failed: {e}")
            return {
                "allowed": False,
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": f"Auth service error: {str(e).lower()}"
                }
            }
    
    async def validate_file_access(
        self, 
        user_id: str, 
        file_id: str, 
        bucket_id: str, 
        action: str
    ) -> Dict[str, Any]:
        """
        Validate user access to a file using the authentication middleware.
        
        Args:
            user_id: User ID requesting access
            file_id: File ID to access
            bucket_id: Bucket ID containing the file
            action: Action being performed (read, write, delete)
            
        Returns:
            Dictionary with access validation result
        """
        try:
            if hasattr(self.auth_middleware, 'validate_file_access'):
                result = await self.auth_middleware.validate_file_access(
                    user_id, file_id, bucket_id, action
                )
                return result
            
            # Fallback for tests without auth middleware
            return {
                "allowed": False,
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": "Authentication service not available"
                }
            }
            
        except Exception as e:
            logger.error(f"File access validation failed: {e}")
            return {
                "allowed": False,
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": f"Auth service error: {str(e).lower()}"
                }
            }
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information using the authentication middleware.
        
        Args:
            user_id: User ID to get information for
            
        Returns:
            Dictionary with user information
        """
        try:
            if hasattr(self.auth_middleware, 'get_user_info'):
                result = await self.auth_middleware.get_user_info(user_id)
                return result
            
            # Fallback for tests without auth middleware
            return {
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": "Authentication service not available"
                }
            }
            
        except Exception as e:
            logger.error(f"Get user info failed: {e}")
            return {
                "error": {
                    "code": "AUTH_SERVICE_ERROR",
                    "message": f"Auth service error: {str(e).lower()}"
                }
            }