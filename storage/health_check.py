"""
Storage health check operations module.

This module handles health monitoring and status checks for the storage service
and its dependencies including storage backend and authentication middleware.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any

from .base import StorageBase


logger = logging.getLogger(__name__)


class HealthCheckMixin:
    """Mixin class for health check and monitoring functionality."""
    
    async def get_health(self, detailed: bool = False) -> Dict[str, Any]:
        """
        Get the health status of the storage service and its dependencies.
        
        Args:
            detailed: Whether to include detailed health information
            
        Returns:
            Dictionary with health status information
        """
        # Get current time for calculations
        current_time = time.time()
        startup_time = getattr(self, '_startup_time', current_time)
        uptime_seconds = int(current_time - startup_time)
        
        # Initialize health data
        health_data = {
            "status": "healthy",  # Will be updated based on dependencies
            "service": "storage",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "storage_backend": self.storage_backend,
            "internal_only": True,
            "streaming_enabled": self.enable_streaming,
            "startup_time": datetime.fromtimestamp(startup_time, timezone.utc).isoformat(),
            "uptime_seconds": uptime_seconds,
            "dependencies": {},
            "configuration": {
                "storage_backend": self.storage_backend,
                "internal_only": True,
                "streaming_enabled": self.enable_streaming,
                "port": self.config_manager.get_port() if hasattr(self.config_manager, 'get_port') else 8003,
                "allowed_internal_services": ["backend", "functions", "docker_network"]
            }
        }
        
        if detailed:
            health_data["detailed"] = True
        
        # Initialize metrics
        health_data["metrics"] = {
            "total_requests": getattr(self, '_total_requests', 0),
            "error_count": getattr(self, '_error_count', 0),
            "uptime_seconds": uptime_seconds
        }
        
        # Check storage backend health
        storage_backend_health = await self._check_storage_backend_health()
        health_data["dependencies"]["storage_backend"] = storage_backend_health
        
        # Check auth middleware health
        auth_middleware_health = await self._check_auth_middleware_health()
        health_data["dependencies"]["auth_middleware"] = auth_middleware_health
        
        # Determine overall health status
        dependency_statuses = [
            storage_backend_health["status"],
            auth_middleware_health["status"]
        ]
        
        # Count different status types
        error_count = sum(1 for status in dependency_statuses if status == "error")
        unhealthy_count = sum(1 for status in dependency_statuses if status == "unhealthy")
        healthy_count = sum(1 for status in dependency_statuses if status == "healthy")
        unknown_count = sum(1 for status in dependency_statuses if status == "unknown")
        
        # Determine overall status based on dependency health
        if error_count > 0:
            health_data["status"] = "unhealthy"
        elif unhealthy_count > 0:
            if unhealthy_count >= len(dependency_statuses):
                health_data["status"] = "unhealthy"
            else:
                health_data["status"] = "degraded"
        elif healthy_count > 0 or unknown_count == len(dependency_statuses):
            # If all dependencies are healthy, or all are unknown (service itself is healthy)
            health_data["status"] = "healthy"
        
        # Store startup time for future calls
        if not hasattr(self, '_startup_time'):
            self._startup_time = startup_time
            
        return health_data
    
    async def _check_storage_backend_health(self) -> Dict[str, Any]:
        """Check storage backend health."""
        try:
            if hasattr(self, '_storage_backend') and hasattr(self._storage_backend, 'get_health'):
                health = await self._storage_backend.get_health()
                return health
            else:
                return {
                    "status": "unknown",
                    "message": "Storage backend health check not implemented"
                }
        except Exception as e:
            logger.error(f"Storage backend health check failed: {e}")
            return {
                "status": "error", 
                "error": f"Storage backend health check error: {str(e).lower()}"
            }
    
    async def _check_auth_middleware_health(self) -> Dict[str, Any]:
        """Check auth middleware health."""
        try:
            if hasattr(self.auth_middleware, 'get_health'):
                health = await self.auth_middleware.get_health()
                return health
            else:
                return {
                    "status": "unknown",
                    "message": "Auth middleware health check not implemented"
                }
        except Exception as e:
            logger.error(f"Auth middleware health check failed: {e}")
            return {
                "status": "error",
                "error": f"Auth middleware health check error: {str(e).lower()}"
            }