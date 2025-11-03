"""
Backend streaming proxy implementation.

Provides unified API gateway with streaming proxy functionality to eliminate
direct storage service exposure. Handles large file streaming without memory
buffering and forwards authentication context securely.
"""

import httpx
import asyncio
import time
from typing import Dict, Any, Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class ProxyResponse:
    """Wrapper for proxy responses with streaming support."""
    
    def __init__(self, status_code: int, headers: Dict[str, str], content: bytes = None, stream_generator=None):
        self.status_code = status_code
        self.headers = headers
        self._content = content
        self._stream_generator = stream_generator
    
    @property
    def content(self) -> bytes:
        """Get response content for non-streaming responses."""
        if self._content is not None:
            return self._content
        return b""
    
    def json(self) -> Dict[str, Any]:
        """Parse response content as JSON."""
        import json
        return json.loads(self.content.decode())
    
    async def stream_content(self) -> AsyncGenerator[bytes, None]:
        """Stream response content without buffering."""
        if self._stream_generator:
            async for chunk in self._stream_generator:
                yield chunk


class StreamingProxy:
    """
    Core streaming proxy for backend API gateway.
    
    Provides memory-efficient streaming proxy functionality with connection pooling,
    authentication forwarding, and proper error handling.
    """
    
    def __init__(self, config_manager, auth_middleware):
        """Initialize streaming proxy with configuration and auth middleware."""
        self.config_manager = config_manager
        self.auth_middleware = auth_middleware
        
        # Performance metrics tracking
        self._metrics = {
            "total_requests": 0,
            "total_bytes_streamed": 0,
            "average_request_time": 0.0,
            "connection_pool_stats": {}
        }
        
        # Initialize HTTP client with optimized settings for microservices
        self._http_client = self._create_http_client()
        self._initialized = True
        
        logger.info("StreamingProxy initialized successfully")
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """Create optimized HTTP client for internal service communication."""
        # Connection limits optimized for microservices
        limits = httpx.Limits(
            max_connections=100,        # Support concurrent operations
            max_keepalive_connections=20  # Reuse connections efficiently
        )
        
        # Timeouts optimized for large file operations
        timeout = httpx.Timeout(
            connect=10.0,   # Connection timeout
            read=300.0,     # Long timeout for large files
            write=300.0,    # Long timeout for uploads
            pool=10.0       # Pool acquisition timeout
        )
        
        return httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            follow_redirects=True
        )
    
    def is_initialized(self) -> bool:
        """Check if proxy is properly initialized."""
        return self._initialized and not self._http_client.is_closed
    
    def get_storage_base_url(self) -> str:
        """Get base URL for storage service."""
        storage_host = self.config_manager.get_setting("storage_host")
        storage_port = self.config_manager.get_setting("storage_port")
        return f"http://{storage_host}:{storage_port}"
    
    def get_http_client(self) -> httpx.AsyncClient:
        """Get the configured HTTP client for testing."""
        return self._http_client
    
    async def proxy_request(self, method: str, path: str, headers: Dict[str, str],
                           data: bytes = None) -> ProxyResponse:
        """
        Proxy a request to the storage service.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: Request path (e.g., "/api/v1/files/bucket/file.txt")
            headers: Request headers to forward
            data: Request body data (for uploads)
            
        Returns:
            ProxyResponse with status, headers, and content
        """
        start_time = time.time()
        
        try:
            # Build full URL to storage service
            storage_url = f"{self.get_storage_base_url()}{path}"
            
            # Sanitize headers (remove hop-by-hop headers)
            sanitized_headers = self._sanitize_headers(headers)
            
            # Make request to storage service
            response = await self._http_client.request(
                method=method,
                url=storage_url,
                headers=sanitized_headers,
                content=data
            )
            
            # Update metrics
            self._update_metrics(start_time, len(response.content))
            
            return ProxyResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=response.content
            )
            
        except httpx.TimeoutException:
            logger.warning(f"Timeout occurred for {method} {path}")
            return ProxyResponse(
                status_code=504,
                headers={"Content-Type": "application/json"},
                content=b'{"error": "Gateway timeout", "code": "TIMEOUT"}'
            )
        except Exception as e:
            logger.error(f"Proxy error for {method} {path}: {e}")
            return ProxyResponse(
                status_code=500,
                headers={"Content-Type": "application/json"},
                content=b'{"error": "Internal proxy error", "code": "PROXY_ERROR"}'
            )
    
    async def stream_response(self, method: str, path: str, headers: Dict[str, str],
                             data: bytes = None) -> ProxyResponse:
        """
        Stream a response from storage service without buffering.
        
        Args:
            method: HTTP method
            path: Request path
            headers: Request headers to forward
            data: Request body data
            
        Returns:
            ProxyResponse with streaming generator
        """
        start_time = time.time()
        
        try:
            # Build full URL to storage service
            storage_url = f"{self.get_storage_base_url()}{path}"
            
            # Sanitize headers
            sanitized_headers = self._sanitize_headers(headers)
            
            # Create streaming request
            async with self._http_client.stream(
                method=method,
                url=storage_url,
                headers=sanitized_headers,
                content=data
            ) as response:
                
                async def stream_generator():
                    """Generator for streaming response chunks."""
                    total_bytes = 0
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        total_bytes += len(chunk)
                        yield chunk
                    
                    # Update metrics after streaming completes
                    self._update_metrics(start_time, total_bytes)
                
                return ProxyResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    stream_generator=stream_generator()
                )
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout occurred for streaming {method} {path}")
            return ProxyResponse(
                status_code=504,
                headers={"Content-Type": "application/json"},
                content=b'{"error": "Gateway timeout", "code": "TIMEOUT"}'
            )
        except Exception as e:
            logger.error(f"Streaming proxy error for {method} {path}: {e}")
            return ProxyResponse(
                status_code=500,
                headers={"Content-Type": "application/json"},
                content=b'{"error": "Internal proxy error", "code": "PROXY_ERROR"}'
            )
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Sanitize headers for forwarding, removing hop-by-hop headers.
        
        Args:
            headers: Original request headers
            
        Returns:
            Sanitized headers safe for forwarding
        """
        # Headers that should not be forwarded (hop-by-hop headers)
        hop_by_hop = {
            "connection", "keep-alive", "proxy-authenticate",
            "proxy-authorization", "te", "trailers", "transfer-encoding",
            "upgrade", "host"
        }
        
        return {
            key: value for key, value in headers.items()
            if key.lower() not in hop_by_hop
        }
    
    def _update_metrics(self, start_time: float, bytes_processed: int):
        """Update performance metrics."""
        request_time = time.time() - start_time
        
        self._metrics["total_requests"] += 1
        self._metrics["total_bytes_streamed"] += bytes_processed
        
        # Update average request time
        total_requests = self._metrics["total_requests"]
        current_avg = self._metrics["average_request_time"]
        self._metrics["average_request_time"] = (
            (current_avg * (total_requests - 1) + request_time) / total_requests
        )
        
        # Update connection pool stats
        if hasattr(self._http_client, '_pool'):
            pool = self._http_client._pool
            self._metrics["connection_pool_stats"] = {
                "active_connections": len(pool._connections_by_origin),
                "available_connections": sum(
                    len(connections) for connections in pool._connections_by_origin.values()
                )
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self._metrics.copy()
    
    async def cleanup(self):
        """Clean up resources and close connections."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        self._initialized = False
        logger.info("StreamingProxy cleanup completed")