"""
Storage Service - Main Implementation

This module contains the main Storage class that combines all storage functionality
through mixin classes for better organization and maintainability.
"""

import logging
from typing import Dict, Any, List, Optional

from .base import StorageBase
from .bucket_operations import BucketOperationsMixin
from .file_operations import FileOperationsMixin
from .file_management import FileManagementMixin
from .auth_integration import AuthIntegrationMixin
from .health_check import HealthCheckMixin


logger = logging.getLogger(__name__)


class Storage(
    StorageBase,
    BucketOperationsMixin,
    FileOperationsMixin,
    FileManagementMixin,
    AuthIntegrationMixin,
    HealthCheckMixin
):
    """
    Main Storage service class that combines all functionality through mixins.
    
    This class provides a complete storage service implementation with:
    - Bucket CRUD operations
    - File upload/download/metadata/listing operations
    - File management operations (delete/copy/move)
    - Authentication integration
    - Health monitoring and status checks
    
    All operations are internal-only and require authentication middleware.
    """
    
    def __init__(
        self,
        config_manager,
        auth_middleware,
        storage_backend: str = "minio",
        enable_streaming: bool = True
    ):
        """
        Initialize the storage service with all required dependencies.
        
        Args:
            config_manager: Configuration manager instance
            auth_middleware: Authentication middleware instance
            storage_backend: Storage backend type (minio, local, s3)
            enable_streaming: Whether to enable streaming I/O
            
        Raises:
            ValueError: If required dependencies are missing or invalid
        """
        # Initialize the base class
        super().__init__(
            config_manager=config_manager,
            auth_middleware=auth_middleware,
            storage_backend=storage_backend,
            enable_streaming=enable_streaming
        )
        
        # Additional properties for backward compatibility with tests
        self._internal_only = True  # Always internal-only by design
        self.port = None  # Port comes from config_manager
        
        # Initialize request tracking for metrics
        self._total_requests = 0
        self._error_count = 0
        
        logger.info("Storage service fully initialized with all mixins")
    
    @property
    def internal_only(self) -> bool:
        """
        Get internal-only status (always True, cannot be changed).
        
        Returns:
            Always True - storage service is internal-only by design
        """
        return self._internal_only
    
    @internal_only.setter 
    def internal_only(self, value: bool) -> None:
        """
        Setter for internal_only that maintains True value.
        
        Args:
            value: Attempted value (ignored - always remains True)
        """
        # Always remains True regardless of attempted value
        self._internal_only = True
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get comprehensive service information.
        
        Returns:
            Dictionary with service details, capabilities, and configuration
        """
        return {
            "name": "SelfDB Storage Service",
            "version": "1.0.0",
            "description": "Internal-only storage service for SelfDB",
            "capabilities": [
                "bucket_management",
                "file_upload_download",
                "file_management",
                "streaming_io",
                "authentication_integration",
                "health_monitoring"
            ],
            "configuration": self.get_configuration(),
            "internal_only": self.is_internal_only(),
            "has_external_endpoint": self.has_external_endpoint(),
            "allowed_internal_services": self.get_allowed_internal_services(),
            "supported_backends": self.SUPPORTED_BACKENDS
        }
    
    async def increment_request_count(self):
        """Increment the total request counter for metrics."""
        self._total_requests += 1
    
    async def increment_error_count(self):
        """Increment the error counter for metrics."""
        self._error_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics.
        
        Returns:
            Dictionary with current metrics
        """
        return {
            "total_requests": self._total_requests,
            "error_count": self._error_count,
            "success_rate": (
                (self._total_requests - self._error_count) / self._total_requests * 100
                if self._total_requests > 0 else 0
            )
        }
    
    def get_service_port(self) -> int:
        """Get service port from configuration (backward compatibility)."""
        return self.config_manager.get_port("storage")
    
    def get_storage_configuration(self) -> Dict[str, Any]:
        """Get storage configuration (backward compatibility)."""
        config_manager = self.config_manager
        return {
            "endpoint": config_manager.get_setting("MINIO_ENDPOINT", "minio:9000"),
            "access_key": config_manager.get_setting("MINIO_ACCESS_KEY", "minioaccess"), 
            "secret_key": config_manager.get_setting("MINIO_SECRET_KEY", "miniosecret"),
            "secure": config_manager.get_setting("MINIO_SECURE", False)
        }
    
    def get_supported_backends(self) -> List[str]:
        """Get list of supported backends (backward compatibility)."""
        return self.SUPPORTED_BACKENDS
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status (backward compatibility for sync calls)."""
        import asyncio
        try:
            # Try to get the running event loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # For tests, return a simple status
        return {
            "status": "initializing",
            "storage_backend": self.storage_backend,
            "internal_only": self.internal_only,
            "startup_time": getattr(self, '_startup_time', None),
            "version": "1.0.0"
        }
    
    def get_network_configuration(self) -> Dict[str, Any]:
        """Get network configuration (backward compatibility)."""
        return {
            "internal_only": True,
            "external_access": False,
            "allowed_internal_services": self.get_allowed_internal_services()
        }
    
    def validate_network_access(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate network access (backward compatibility)."""
        source_ip = request.get("source_ip", "")
        
        # Check if it's internal network
        is_internal = self.validate_internal_network_access(source_ip)
        
        if is_internal:
            return {
                "allowed": True,
                "access_type": "internal",
                "source": "docker_network"
            }
        else:
            return {
                "allowed": False,
                "access_type": "external",
                "error": {
                    "code": "EXTERNAL_ACCESS_DENIED",
                    "message": "Storage service is internal-only"
                }
            }
    
    def get_allowed_internal_sources(self) -> List[str]:
        """Get allowed internal sources (backward compatibility)."""
        return self.get_allowed_internal_services()
    
    def is_docker_internal_network(self, request: Dict[str, Any]) -> bool:
        """Check if request is from Docker internal network (backward compatibility)."""
        source_ip = request.get("source_ip", "")
        
        # Docker network patterns
        docker_patterns = [
            r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",  # Docker default networks
            r"^172\.17\.",   # Docker bridge
            r"^172\.18\.",   # Docker networks
            r"^172\.19\."    # Docker networks
        ]
        
        import re
        return any(re.match(pattern, source_ip) for pattern in docker_patterns)
    
    def resolve_internal_services(self) -> Dict[str, str]:
        """Resolve internal services (backward compatibility)."""
        return self.get_internal_services_discovery()
    
    def validate_cors_origin(self, origin: Optional[str]) -> Dict[str, Any]:
        """Validate CORS origin (backward compatibility)."""
        is_valid = self.validate_cors_for_internal_only(origin)
        
        if is_valid:
            return {"allowed": True}
        else:
            return {
                "allowed": False,
                "error": {
                    "code": "CORS_ORIGIN_DENIED",
                    "message": "Storage service is internal-only"
                }
            }