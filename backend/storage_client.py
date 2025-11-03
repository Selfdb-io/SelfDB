"""
Internal storage service HTTP client.

Provides HTTP client for backend-to-storage service communication with
connection pooling, service discovery, health checks, and fault tolerance.
"""

import httpx
import asyncio
import time
import json
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StorageClient:
    """
    HTTP client for internal storage service communication.
    
    Provides optimized HTTP client with connection pooling, service discovery,
    health monitoring, retry logic, and circuit breaker pattern.
    """
    
    def __init__(self, config_manager, service_discovery):
        """Initialize storage client with configuration and service discovery."""
        self.config_manager = config_manager
        self.service_discovery = service_discovery
        
        # Configuration settings
        self._connection_pool_size = config_manager.get_setting("connection_pool_size")
        self._health_check_interval = config_manager.get_setting("health_check_interval")
        self._retry_attempts = 3
        self._retry_backoff = 1.0
        
        # Service discovery cache
        self._cached_service_url = None
        self._service_url_cache_time = 0
        self._cache_ttl = 300  # 5 minutes
        
        # Circuit breaker state
        self._circuit_breaker_enabled = False
        self._circuit_breaker_open = False
        self._failure_count = 0
        self._failure_threshold = 5
        self._recovery_timeout = 60
        self._last_failure_time = 0
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "active_connections": 0
        }
        
        # Initialize HTTP client
        self._http_client = self._create_http_client()
        self._initialized = True
        
        logger.info("StorageClient initialized successfully")
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """Create optimized HTTP client for internal service communication."""
        # Connection limits optimized for internal microservices
        limits = httpx.Limits(
            max_connections=self._connection_pool_size,
            max_keepalive_connections=10
        )
        
        # Fast timeouts for internal service communication
        timeout = httpx.Timeout(
            connect=5.0,    # Fast connection for internal services
            read=60.0,      # Standard operations
            write=60.0,     # Standard operations
            pool=5.0        # Pool acquisition
        )
        
        return httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            follow_redirects=False  # Internal services shouldn't redirect
        )
    
    def is_initialized(self) -> bool:
        """Check if client is properly initialized."""
        return self._initialized and not self._http_client.is_closed
    
    def get_service_url(self) -> str:
        """Get storage service URL."""
        storage_host = self.config_manager.get_setting("storage_host")
        storage_port = self.config_manager.get_setting("storage_port")
        return f"http://{storage_host}:{storage_port}"
    
    def get_http_client(self) -> httpx.AsyncClient:
        """Get the HTTP client for testing."""
        return self._http_client
    
    async def discover_storage_service(self) -> str:
        """Discover storage service URL using service discovery."""
        current_time = time.time()
        
        # Check cache first
        if (self._cached_service_url and 
            current_time - self._service_url_cache_time < self._cache_ttl):
            return self._cached_service_url
        
        # Use service discovery
        try:
            service_url = self.service_discovery.get_service_url("storage")
            if service_url:
                self._cached_service_url = service_url
                self._service_url_cache_time = current_time
                return service_url
        except Exception as e:
            logger.warning(f"Service discovery failed: {e}")
        
        # Fallback to configuration
        return self.get_service_url()
    
    async def check_service_health(self) -> bool:
        """Check if storage service is healthy."""
        try:
            return self.service_discovery.is_service_healthy("storage")
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def get_cached_service_url(self) -> Optional[str]:
        """Get cached service URL."""
        return self._cached_service_url
    
    async def make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None,
                          headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Make HTTP request to storage service.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/api/v1/files")
            data: Request data to serialize
            headers: Request headers
            
        Returns:
            Deserialized response or error information
        """
        # Check circuit breaker
        if self._circuit_breaker_open:
            if time.time() - self._last_failure_time < self._recovery_timeout:
                return {
                    "status": "circuit_breaker_open",
                    "error_message": "Circuit breaker is open"
                }
            else:
                # Try to recover
                self._circuit_breaker_open = False
                self._failure_count = 0
        
        try:
            # Build full URL
            service_url = await self.discover_storage_service()
            full_url = f"{service_url}{endpoint}"
            
            # Prepare request
            request_kwargs = {
                "method": method,
                "url": full_url
            }
            
            if headers:
                request_kwargs["headers"] = headers
            
            if data:
                if method in ["POST", "PUT", "PATCH"]:
                    request_kwargs["json"] = data
                else:
                    request_kwargs["params"] = data
            
            # Make request
            self._stats["total_requests"] += 1
            response = await self._http_client.request(**request_kwargs)
            
            # Handle response
            if response.status_code < 400:
                self._stats["successful_requests"] += 1
                self._reset_circuit_breaker()
                return self._deserialize_response(response)
            else:
                self._stats["failed_requests"] += 1
                # Only trigger circuit breaker for server errors (5xx), not client errors (4xx)
                if response.status_code >= 500:
                    self._handle_failure()
                
                # For error responses, try to deserialize the error content
                try:
                    error_content = self._deserialize_response(response)
                    if isinstance(error_content, dict):
                        return error_content
                except Exception:
                    pass
                
                return {
                    "status": "error",
                    "error_type": "http_error",
                    "error_message": f"HTTP {response.status_code}",
                    "status_code": response.status_code
                }
                
        except httpx.ConnectError as e:
            self._stats["failed_requests"] += 1
            self._handle_failure()
            return {
                "status": "error",
                "error_type": "connection_error",
                "error_message": str(e)
            }
        except httpx.TimeoutException as e:
            self._stats["failed_requests"] += 1
            self._handle_failure()
            return {
                "status": "error",
                "error_type": "timeout_error",
                "error_message": str(e)
            }
        except httpx.HTTPStatusError as e:
            self._stats["failed_requests"] += 1
            self._handle_failure()
            return {
                "status": "error",
                "error_type": "http_error",
                "error_message": str(e)
            }
        except Exception as e:
            self._stats["failed_requests"] += 1
            self._handle_failure()
            return {
                "status": "error",
                "error_type": "generic_error",
                "error_message": str(e)
            }
    
    def _deserialize_response(self, response: httpx.Response) -> Any:
        """Deserialize response based on content type."""
        content_type = response.headers.get("Content-Type", "").lower()
        
        if "application/json" in content_type:
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"error": "Invalid JSON response"}
        else:
            return response.content
    
    def get_timeout_config(self, operation_type: str) -> Dict[str, float]:
        """Get timeout configuration for different operation types."""
        timeout_configs = {
            "quick_operation": {
                "connect": 5.0,
                "read": 5.0,
                "write": 5.0
            },
            "standard_operation": {
                "connect": 5.0,
                "read": 30.0,
                "write": 30.0
            },
            "long_operation": {
                "connect": 5.0,
                "read": 300.0,
                "write": 300.0
            },
            "file_upload": {
                "connect": 5.0,
                "read": 600.0,
                "write": 600.0
            }
        }
        
        return timeout_configs.get(operation_type, timeout_configs["standard_operation"])
    
    async def check_detailed_health(self) -> Dict[str, Any]:
        """Check detailed health status of storage service."""
        try:
            response = await self.make_request("GET", "/health")
            return response if isinstance(response, dict) else {"status": "unknown"}
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            "active_connections": self._stats["active_connections"],
            "total_requests": self._stats["total_requests"],
            "successful_requests": self._stats["successful_requests"],
            "failed_requests": self._stats["failed_requests"],
            "success_rate": (
                self._stats["successful_requests"] / max(1, self._stats["total_requests"])
            ) * 100
        }
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get client configuration."""
        return {
            "service_url": self.get_service_url(),
            "connection_pool_size": self._connection_pool_size,
            "health_check_interval": self._health_check_interval,
            "retry_attempts": self._retry_attempts,
            "retry_backoff": self._retry_backoff,
            "circuit_breaker_enabled": self._circuit_breaker_enabled,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout": self._recovery_timeout
        }
    
    def validate_configuration(self) -> bool:
        """Validate client configuration."""
        try:
            # Check required settings
            if not self.get_service_url():
                return False
            if self._connection_pool_size <= 0:
                return False
            if self._health_check_interval <= 0:
                return False
            if self._retry_attempts < 0:
                return False
            
            return True
        except Exception:
            return False
    
    async def make_request_with_retry(self, method: str, endpoint: str,
                                     max_retries: int = None, **kwargs) -> Dict[str, Any]:
        """Make request with retry logic."""
        max_retries = max_retries or self._retry_attempts
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = await self.make_request(method, endpoint, **kwargs)
                
                # If successful (no error status or not an error dict), return immediately
                if not isinstance(result, dict) or result.get("status") != "error":
                    return result
                
                # If it's an HTTP error with 4xx status (client error), don't retry
                if (result.get("error_type") == "http_error" and 
                    result.get("status_code", 0) >= 400 and 
                    result.get("status_code", 0) < 500):
                    return result
                
                last_error = result
                
                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = self._retry_backoff * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                last_error = {
                    "status": "error",
                    "error_type": "retry_failed",
                    "error_message": str(e)
                }
        
        return last_error or {
            "status": "error",
            "error_type": "max_retries_exceeded",
            "error_message": "Maximum retry attempts exceeded"
        }
    
    def enable_circuit_breaker(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        """Enable circuit breaker with specified thresholds."""
        self._circuit_breaker_enabled = True
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        logger.info(f"Circuit breaker enabled: threshold={failure_threshold}, recovery={recovery_timeout}s")
    
    def _handle_failure(self):
        """Handle request failure for circuit breaker."""
        if not self._circuit_breaker_enabled:
            return
        
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self._failure_threshold:
            self._circuit_breaker_open = True
            logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker on successful request."""
        if self._circuit_breaker_enabled:
            self._failure_count = 0
            if self._circuit_breaker_open:
                self._circuit_breaker_open = False
                logger.info("Circuit breaker closed - service recovered")
    
    def is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is currently open."""
        return self._circuit_breaker_open
    
    async def cleanup(self):
        """Clean up resources."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        self._initialized = False
        logger.info("StorageClient cleanup completed")