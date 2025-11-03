"""
Unit tests for backend streaming proxy core functionality.

Tests the main streaming proxy infrastructure, connection management, and request routing.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
from typing import Dict, Any, Optional
import asyncio


class TestStreamingProxyCore:
    """Test suite for core streaming proxy functionality."""
    
    @pytest.fixture
    def config_manager(self):
        """Mock configuration manager."""
        config = Mock()
        config.get_setting.side_effect = lambda key: {
            "storage_port": 8003,
            "backend_port": 8000,
            "storage_host": "localhost"
        }.get(key, "localhost")
        return config
    
    @pytest.fixture
    def auth_middleware(self):
        """Mock authentication middleware."""
        auth = AsyncMock()
        auth.validate_api_key.return_value = {
            "user_id": "test-user-123",
            "permissions": ["read", "write"]
        }
        return auth
    
    @pytest.fixture
    def streaming_proxy(self, config_manager, auth_middleware):
        """StreamingProxy instance for testing."""
        from backend.streaming_proxy import StreamingProxy
        
        return StreamingProxy(
            config_manager=config_manager,
            auth_middleware=auth_middleware
        )
    
    def test_streaming_proxy_initialization(self, streaming_proxy):
        """Test that streaming proxy initializes correctly."""
        assert streaming_proxy is not None
        assert streaming_proxy.is_initialized() is True
        assert streaming_proxy.get_storage_base_url() == "http://localhost:8003"
    
    def test_streaming_proxy_connection_pooling_config(self, streaming_proxy):
        """Test that connection pooling is configured correctly for microservices."""
        http_client = streaming_proxy.get_http_client()
        
        # Should use httpx.AsyncClient with proper limits
        assert isinstance(http_client, httpx.AsyncClient)
        
        # Should have connection and timeout configuration
        # Check that the timeout is properly configured for large files
        assert http_client.timeout.read >= 300.0  # Long timeout for large files
        assert http_client.timeout.connect == 10.0  # Connection timeout
        assert http_client.timeout.write == 300.0   # Write timeout for uploads
        
        # Verify the client is configured (we can't easily access internal limits,
        # but we can verify it's properly initialized)
        assert not http_client.is_closed
    
    @pytest.mark.asyncio
    async def test_streaming_proxy_request_routing_basic(self, streaming_proxy):
        """Test basic request routing to storage service."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"status": "success"}'
        
        with patch.object(streaming_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await streaming_proxy.proxy_request(
                method="GET",
                path="/api/v1/health",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert result.status_code == 200
            assert result.headers["Content-Type"] == "application/json"
            
            # Verify request was made to storage service
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "GET"
            assert call_args[1]["url"] == "http://localhost:8003/api/v1/health"
            assert "Authorization" in call_args[1]["headers"]
    
    @pytest.mark.asyncio
    async def test_streaming_proxy_response_streaming(self, streaming_proxy):
        """Test that responses are properly streamed without buffering."""
        # Create a mock streaming response
        class AsyncIteratorMock:
            def __init__(self, items):
                self.items = items
                self.index = 0
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/octet-stream", "Content-Length": "18"}
        # Create an async iterator that returns the chunks
        def mock_aiter_bytes(chunk_size=8192):
            return AsyncIteratorMock([b"chunk1", b"chunk2", b"chunk3"])
        mock_response.aiter_bytes = mock_aiter_bytes
        
        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_context_manager.__aexit__.return_value = None
        
        with patch.object(streaming_proxy._http_client, 'stream', return_value=mock_context_manager) as mock_stream_request:
            result = await streaming_proxy.stream_response(
                method="GET",
                path="/api/v1/files/bucket/large-file.bin",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should return a streaming response
            assert hasattr(result, 'stream_content')
            
            # Collect streamed chunks
            chunks = []
            async for chunk in result.stream_content():
                chunks.append(chunk)
            
            assert chunks == [b"chunk1", b"chunk2", b"chunk3"]
    
    @pytest.mark.asyncio
    async def test_streaming_proxy_connection_management(self, streaming_proxy):
        """Test connection reuse and proper cleanup."""
        # Make multiple requests to verify connection reuse
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'{"test": true}'
        
        with patch.object(streaming_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            # Make multiple requests
            for i in range(3):
                await streaming_proxy.proxy_request(
                    method="GET",
                    path=f"/api/v1/test/{i}",
                    headers={"Authorization": "Bearer test-token"}
                )
            
            # Should reuse the same client connection
            assert mock_request.call_count == 3
            
        # Test cleanup
        await streaming_proxy.cleanup()
        assert streaming_proxy._http_client.is_closed
    
    @pytest.mark.asyncio
    async def test_streaming_proxy_timeout_handling(self, streaming_proxy):
        """Test proper timeout handling for long-running requests."""
        with patch.object(streaming_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            # Simulate timeout
            mock_request.side_effect = httpx.TimeoutException("Request timed out")
            
            result = await streaming_proxy.proxy_request(
                method="GET",
                path="/api/v1/files/bucket/large-file.bin",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should return proper error response
            assert result.status_code == 504  # Gateway Timeout
            assert "timeout" in result.content.decode().lower()
    
    @pytest.mark.asyncio
    async def test_streaming_proxy_error_propagation(self, streaming_proxy):
        """Test that storage service errors are properly propagated."""
        # Mock storage service error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"error": "File not found", "code": "FILE_NOT_FOUND"}'
        
        with patch.object(streaming_proxy._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await streaming_proxy.proxy_request(
                method="GET",
                path="/api/v1/files/bucket/missing-file.bin",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should preserve storage service error
            assert result.status_code == 404
            assert result.headers["Content-Type"] == "application/json"
            error_data = result.json()
            assert error_data["error"] == "File not found"
            assert error_data["code"] == "FILE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_streaming_proxy_memory_usage_validation(self, streaming_proxy):
        """Test that proxy doesn't buffer large responses in memory."""
        # This test ensures streaming behavior by checking memory usage patterns
        try:
            import psutil
            import os
        except ImportError:
            pytest.skip("psutil not available for memory testing")
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Mock a large file response (simulate 10MB with smaller chunks for memory test)
        large_chunks = [b"x" * 1024 for _ in range(10240)]  # 10240 x 1KB chunks = 10MB
        
        class AsyncIteratorMock:
            def __init__(self, items):
                self.items = items
                self.index = 0
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/octet-stream"}
        def mock_aiter_bytes(chunk_size=8192):
            return AsyncIteratorMock(large_chunks)
        mock_response.aiter_bytes = mock_aiter_bytes
        
        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_response
        mock_context_manager.__aexit__.return_value = None
        
        with patch.object(streaming_proxy._http_client, 'stream', return_value=mock_context_manager) as mock_stream_request:
            
            result = await streaming_proxy.stream_response(
                method="GET",
                path="/api/v1/files/bucket/large-file.bin",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Process chunks one by one (simulating streaming)
            chunk_count = 0
            async for chunk in result.stream_content():
                chunk_count += 1
                # Memory shouldn't grow significantly during streaming
                current_memory = process.memory_info().rss
                memory_growth = current_memory - initial_memory
                assert memory_growth < 20 * 1024 * 1024  # Less than 20MB growth (reasonable for 10MB test)
            
            assert chunk_count == 10240  # Updated for new chunk count
    
    def test_streaming_proxy_performance_metrics(self, streaming_proxy):
        """Test that proxy tracks performance metrics."""
        metrics = streaming_proxy.get_performance_metrics()
        
        assert "total_requests" in metrics
        assert "total_bytes_streamed" in metrics
        assert "average_request_time" in metrics
        assert "connection_pool_stats" in metrics
        
        # Initial values should be zero
        assert metrics["total_requests"] == 0
        assert metrics["total_bytes_streamed"] == 0