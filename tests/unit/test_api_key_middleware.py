"""
Unit tests for API Key validation middleware.

Tests the middleware that validates API keys in the x-api-key header.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Optional, Dict, Any


class TestAPIKeyMiddleware:
    """Test suite for API key validation middleware."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = Mock()
        request.headers = {}
        request.url = Mock()
        request.url.path = "/api/v1/test"
        return request
    
    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""
        async def call_next(request):
            response = Mock()
            response.status_code = 200
            response.body = b'{"message": "success"}'
            return response
        return call_next
    
    @pytest.fixture
    def api_key_config(self):
        """API key configuration."""
        return {
            "api_key": "test_api_key_123",
            "header_name": "x-api-key"
        }
    
    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self, mock_request, mock_call_next, api_key_config):
        """Test that missing API key returns 401 Unauthorized."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        middleware = APIKeyMiddleware(api_key=api_key_config["api_key"])
        response = await middleware(mock_request, mock_call_next)
        
        assert response.status_code == 401
        assert b"INVALID_API_KEY" in response.body
        assert b"API key is missing" in response.body
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_401(self, mock_request, mock_call_next, api_key_config):
        """Test that invalid API key returns 401 Unauthorized."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        mock_request.headers["x-api-key"] = "wrong_api_key"
        
        middleware = APIKeyMiddleware(api_key=api_key_config["api_key"])
        response = await middleware(mock_request, mock_call_next)
        
        assert response.status_code == 401
        assert b"INVALID_API_KEY" in response.body
        assert b"Provided API key is invalid" in response.body
    
    @pytest.mark.asyncio
    async def test_valid_api_key_passes_through(self, mock_request, mock_call_next, api_key_config):
        """Test that valid API key allows request to pass through."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        mock_request.headers["x-api-key"] = api_key_config["api_key"]
        
        middleware = APIKeyMiddleware(api_key=api_key_config["api_key"])
        response = await middleware(mock_request, mock_call_next)
        
        assert response.status_code == 200
        assert response.body == b'{"message": "success"}'
    
    @pytest.mark.asyncio
    async def test_api_key_from_environment(self, mock_request, mock_call_next, monkeypatch):
        """Test that API key can be loaded from environment variable."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        monkeypatch.setenv("API_KEY", "env_api_key_456")
        mock_request.headers["x-api-key"] = "env_api_key_456"
        
        middleware = APIKeyMiddleware()  # Should load from env
        response = await middleware(mock_request, mock_call_next)
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_case_insensitive_header(self, mock_request, mock_call_next, api_key_config):
        """Test that header name is case-insensitive."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        # Try different case variations
        mock_request.headers["X-API-Key"] = api_key_config["api_key"]
        
        middleware = APIKeyMiddleware(api_key=api_key_config["api_key"])
        response = await middleware(mock_request, mock_call_next)
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_excluded_paths_bypass_validation(self, mock_request, mock_call_next, api_key_config):
        """Test that certain paths can bypass API key validation."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        # Health check endpoint should bypass
        mock_request.url.path = "/health"
        
        middleware = APIKeyMiddleware(
            api_key=api_key_config["api_key"],
            exclude_paths=["/health", "/api/v1/docs"]
        )
        response = await middleware(mock_request, mock_call_next)
        
        assert response.status_code == 200
        assert "x-api-key" not in mock_request.headers
    
    @pytest.mark.asyncio
    async def test_request_id_generation(self, mock_request, mock_call_next, api_key_config):
        """Test that request ID is generated for tracking."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        mock_request.headers["x-api-key"] = api_key_config["api_key"]
        
        middleware = APIKeyMiddleware(api_key=api_key_config["api_key"])
        response = await middleware(mock_request, mock_call_next)
        
        # Check that request has a request_id attached
        assert hasattr(mock_request.state, "request_id")
        assert mock_request.state.request_id is not None
        assert len(mock_request.state.request_id) > 0
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, mock_request, mock_call_next, api_key_config):
        """Test that error responses follow the standard format."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        import json
        
        middleware = APIKeyMiddleware(api_key=api_key_config["api_key"])
        response = await middleware(mock_request, mock_call_next)
        
        # Parse the error response
        error_data = json.loads(response.body)
        
        assert "error" in error_data
        assert "code" in error_data["error"]
        assert "message" in error_data["error"]
        assert "request_id" in error_data["error"]
        assert error_data["error"]["code"] == "INVALID_API_KEY"
    
    @pytest.mark.asyncio
    async def test_api_key_logging(self, mock_request, mock_call_next, api_key_config, caplog):
        """Test that API key validation is logged."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        import logging
        
        caplog.set_level(logging.INFO)
        
        mock_request.headers["x-api-key"] = "wrong_key"
        
        middleware = APIKeyMiddleware(api_key=api_key_config["api_key"])
        await middleware(mock_request, mock_call_next)
        
        # Check that validation failure was logged
        assert "Invalid API key attempt" in caplog.text
    
    @pytest.mark.asyncio
    async def test_multiple_api_keys_support(self, mock_request, mock_call_next):
        """Test support for multiple valid API keys."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        mock_request.headers["x-api-key"] = "key2"
        
        middleware = APIKeyMiddleware(
            api_key=["key1", "key2", "key3"]  # Multiple valid keys
        )
        response = await middleware(mock_request, mock_call_next)
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_api_key_rate_limiting_tracking(self, mock_request, mock_call_next, api_key_config):
        """Test that API key usage is tracked for rate limiting."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        mock_request.headers["x-api-key"] = api_key_config["api_key"]
        
        middleware = APIKeyMiddleware(
            api_key=api_key_config["api_key"],
            enable_rate_limit_tracking=True
        )
        
        # Make multiple requests
        for _ in range(3):
            response = await middleware(mock_request, mock_call_next)
            assert response.status_code == 200
        
        # Check that usage was tracked
        assert hasattr(mock_request.state, "api_key_usage_count")
    
    @pytest.mark.asyncio
    async def test_cors_headers_on_error(self, mock_request, mock_call_next, api_key_config):
        """Test that CORS headers are included in error responses."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        middleware = APIKeyMiddleware(api_key=api_key_config["api_key"])
        response = await middleware(mock_request, mock_call_next)
        
        assert response.status_code == 401
        assert hasattr(response, "headers")
        assert "Access-Control-Allow-Origin" in response.headers
    
    def test_middleware_initialization_without_api_key_raises_error(self, monkeypatch):
        """Test that middleware requires an API key to be configured."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        # Ensure API_KEY env var is not set
        monkeypatch.delenv("API_KEY", raising=False)
        
        with pytest.raises(ValueError, match="API_KEY must be configured"):
            middleware = APIKeyMiddleware(api_key=None)
    
    @pytest.mark.asyncio
    async def test_api_key_extraction_from_query_params(self, mock_request, mock_call_next, api_key_config):
        """Test that API key can be extracted from query parameters as fallback."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        # No header, but query param present
        mock_request.query_params = {"api_key": api_key_config["api_key"]}
        
        middleware = APIKeyMiddleware(
            api_key=api_key_config["api_key"],
            allow_query_param=True
        )
        response = await middleware(mock_request, mock_call_next)
        
        assert response.status_code == 200