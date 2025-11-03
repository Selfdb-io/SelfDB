"""
Unit tests for internal storage service HTTP client.

Tests the HTTP client for backend-to-storage service communication with
connection pooling, service discovery, and health checks.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from typing import Dict, Any


class TestStorageClient:
    """Test suite for internal storage service HTTP client."""
    
    @pytest.fixture
    def config_manager(self):
        """Mock configuration manager."""
        config = Mock()
        config.get_setting.side_effect = lambda key: {
            "storage_port": 8003,
            "storage_host": "localhost",
            "backend_port": 8000,
            "connection_pool_size": 20,
            "health_check_interval": 30
        }.get(key, "localhost")
        return config
    
    @pytest.fixture
    def service_discovery(self):
        """Mock service discovery."""
        discovery = Mock()
        discovery.get_service_url.return_value = "http://localhost:8003"
        discovery.is_service_healthy.return_value = True
        return discovery
    
    @pytest.fixture
    def storage_client(self, config_manager, service_discovery):
        """StorageClient instance for testing."""
        from storage_client import StorageClient
        
        return StorageClient(
            config_manager=config_manager,
            service_discovery=service_discovery
        )
    
    def test_storage_client_initialization(self, storage_client):
        """Test that storage client initializes correctly."""
        assert storage_client is not None
        assert storage_client.is_initialized() is True
        assert storage_client.get_service_url() == "http://localhost:8003"
    
    def test_storage_client_connection_pool_config(self, storage_client):
        """Test connection pool configuration for microservices."""
        http_client = storage_client.get_http_client()
        
        # Should have proper configuration for internal service communication
        assert hasattr(http_client, 'timeout')
        assert http_client.timeout.connect == 5.0  # Fast connection for internal services
        assert http_client.timeout.read >= 60.0    # Reasonable timeout for operations
        
        # Should not be closed
        assert not http_client.is_closed
    
    @pytest.mark.asyncio
    async def test_storage_client_service_discovery(self, storage_client):
        """Test service discovery integration."""
        # Test successful service discovery
        service_url = await storage_client.discover_storage_service()
        assert service_url == "http://localhost:8003"
        
        # Test service health check
        is_healthy = await storage_client.check_service_health()
        assert is_healthy is True
        
        # Test service URL caching
        cached_url = storage_client.get_cached_service_url()
        assert cached_url == "http://localhost:8003"
    
    @pytest.mark.asyncio
    async def test_storage_client_request_serialization(self, storage_client):
        """Test request serialization for storage service calls."""
        # Mock request data
        request_data = {
            "bucket": "test-bucket",
            "path": "documents/test.txt",
            "metadata": {
                "content_type": "text/plain",
                "size": 1024
            }
        }
        
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "status": "success",
            "file_id": "file-123"
        }
        
        with patch.object(storage_client._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            result = await storage_client.make_request(
                method="POST",
                endpoint="/api/v1/files",
                data=request_data,
                headers={"Authorization": "Bearer token"}
            )
            
            # Verify request was serialized correctly
            assert result["status"] == "success"
            assert result["file_id"] == "file-123"
            
            # Verify request parameters
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "POST"
            assert "/api/v1/files" in call_args[1]["url"]
            assert "Authorization" in call_args[1]["headers"]
    
    @pytest.mark.asyncio
    async def test_storage_client_response_deserialization(self, storage_client):
        """Test response deserialization from storage service."""
        # Test different response types
        response_scenarios = [
            # Successful JSON response
            {
                "status_code": 200,
                "content_type": "application/json",
                "body": b'{"result": "success", "data": {"id": 123}}',
                "expected": {"result": "success", "data": {"id": 123}}
            },
            # Error JSON response
            {
                "status_code": 400,
                "content_type": "application/json",
                "body": b'{"error": "Bad request", "code": "INVALID_INPUT"}',
                "expected": {"error": "Bad request", "code": "INVALID_INPUT"}
            },
            # Binary response
            {
                "status_code": 200,
                "content_type": "application/octet-stream",
                "body": b"binary file content",
                "expected": b"binary file content"
            }
        ]
        
        for scenario in response_scenarios:
            mock_response = Mock()
            mock_response.status_code = scenario["status_code"]
            mock_response.headers = {"Content-Type": scenario["content_type"]}
            mock_response.content = scenario["body"]
            if scenario["content_type"] == "application/json":
                import json
                mock_response.json.return_value = json.loads(scenario["body"])
            
            with patch.object(storage_client._http_client, 'request', new_callable=AsyncMock) as mock_request:
                mock_request.return_value = mock_response
                
                result = await storage_client.make_request(
                    method="GET",
                    endpoint="/api/v1/test"
                )
                
                if scenario["content_type"] == "application/json":
                    assert result == scenario["expected"]
                else:
                    assert result == scenario["expected"]
    
    @pytest.mark.asyncio
    async def test_storage_client_error_handling(self, storage_client):
        """Test error handling for storage service communication."""
        import httpx
        
        error_scenarios = [
            # Connection error
            (httpx.ConnectError("Connection failed"), "connection_error"),
            # Timeout error
            (httpx.TimeoutException("Request timed out"), "timeout_error"),
            # HTTP error
            (httpx.HTTPStatusError("HTTP error", request=Mock(), response=Mock()), "http_error"),
            # Generic error
            (Exception("Unexpected error"), "generic_error")
        ]
        
        for exception, error_type in error_scenarios:
            with patch.object(storage_client._http_client, 'request', new_callable=AsyncMock) as mock_request:
                mock_request.side_effect = exception
                
                result = await storage_client.make_request(
                    method="GET",
                    endpoint="/api/v1/test"
                )
                
                # Verify error handling
                assert result["status"] == "error"
                assert result["error_type"] == error_type
                assert "error_message" in result
    
    @pytest.mark.asyncio
    async def test_storage_client_timeout_configuration(self, storage_client):
        """Test timeout configuration for different operation types."""
        # Test different timeout configurations
        timeout_scenarios = [
            ("quick_operation", 5.0),
            ("standard_operation", 30.0),
            ("long_operation", 300.0),
            ("file_upload", 600.0)
        ]
        
        for operation_type, expected_timeout in timeout_scenarios:
            timeout_config = storage_client.get_timeout_config(operation_type)
            
            assert timeout_config["read"] >= expected_timeout
            assert timeout_config["connect"] <= 10.0  # Connection should be fast for internal services
    
    @pytest.mark.asyncio
    async def test_storage_client_health_check_integration(self, storage_client):
        """Test health check integration with storage service."""
        # Mock health check response
        mock_health_response = Mock()
        mock_health_response.status_code = 200
        mock_health_response.headers = {"Content-Type": "application/json"}
        mock_health_response.json.return_value = {
            "status": "healthy",
            "version": "1.0.0",
            "uptime": 3600,
            "dependencies": {
                "database": "healthy",
                "storage_backend": "healthy"
            }
        }
        
        with patch.object(storage_client._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_health_response
            
            health_status = await storage_client.check_detailed_health()
            
            # Verify health check
            assert health_status["status"] == "healthy"
            assert health_status["version"] == "1.0.0"
            assert health_status["dependencies"]["database"] == "healthy"
            
            # Verify health check endpoint was called
            call_args = mock_request.call_args
            assert "/health" in call_args[1]["url"]
            assert call_args[1]["method"] == "GET"
    
    @pytest.mark.asyncio
    async def test_storage_client_connection_pooling(self, storage_client):
        """Test connection pooling and reuse."""
        # Make multiple requests to test connection reuse
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"result": "success"}
        
        with patch.object(storage_client._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            # Make multiple concurrent requests
            tasks = []
            for i in range(5):
                task = asyncio.create_task(
                    storage_client.make_request(
                        method="GET",
                        endpoint=f"/api/v1/test/{i}"
                    )
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # All requests should succeed
            for result in results:
                assert result["result"] == "success"
            
            # Should have made 5 requests
            assert mock_request.call_count == 5
        
        # Test connection pool stats
        pool_stats = storage_client.get_connection_pool_stats()
        assert "active_connections" in pool_stats
        assert "total_requests" in pool_stats
    
    def test_storage_client_configuration(self, storage_client):
        """Test storage client configuration."""
        config = storage_client.get_configuration()
        
        # Verify configuration settings
        assert config["service_url"] == "http://localhost:8003"
        assert config["connection_pool_size"] > 0
        assert config["health_check_interval"] > 0
        assert config["retry_attempts"] >= 3
        assert config["retry_backoff"] > 0
        
        # Test configuration validation
        assert storage_client.validate_configuration() is True
    
    @pytest.mark.asyncio
    async def test_storage_client_retry_mechanism(self, storage_client):
        """Test retry mechanism for failed requests."""
        # Mock responses: first two fail, third succeeds
        mock_responses = []
        
        # First failure
        failure_response_1 = Mock()
        failure_response_1.status_code = 500
        failure_response_1.headers = {}
        failure_response_1.content = b''
        mock_responses.append(failure_response_1)
        
        # Second failure  
        failure_response_2 = Mock()
        failure_response_2.status_code = 503
        failure_response_2.headers = {}
        failure_response_2.content = b''
        mock_responses.append(failure_response_2)
        
        # Third success
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {"Content-Type": "application/json"}
        success_response.json.return_value = {"result": "success"}
        mock_responses.append(success_response)
        
        with patch.object(storage_client._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = mock_responses
            
            result = await storage_client.make_request_with_retry(
                method="GET",
                endpoint="/api/v1/test",
                max_retries=3
            )
            
            # Should eventually succeed
            assert result["result"] == "success"
            
            # Should have made 3 attempts
            assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_storage_client_circuit_breaker(self, storage_client):
        """Test circuit breaker pattern for failing service."""
        # Enable circuit breaker
        storage_client.enable_circuit_breaker(failure_threshold=3, recovery_timeout=60)
        
        # Mock consecutive failures
        mock_response = Mock()
        mock_response.status_code = 500
        
        with patch.object(storage_client._http_client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            # Make requests until circuit breaker opens
            for i in range(5):
                result = await storage_client.make_request(
                    method="GET",
                    endpoint="/api/v1/test"
                )
                
                if i < 3:
                    # First 3 requests should reach the service
                    assert result["status"] == "error"
                else:
                    # After threshold, circuit breaker should be open
                    assert result["status"] == "circuit_breaker_open"
        
        # Verify circuit breaker state
        assert storage_client.is_circuit_breaker_open() is True
    
    async def test_storage_client_cleanup(self, storage_client):
        """Test proper cleanup of resources."""
        # Verify client is initially open
        assert not storage_client._http_client.is_closed
        
        # Cleanup
        await storage_client.cleanup()
        
        # Verify client is closed
        assert storage_client._http_client.is_closed
        assert storage_client.is_initialized() is False