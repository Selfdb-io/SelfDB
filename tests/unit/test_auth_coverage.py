"""
Additional tests to achieve 95%+ coverage for authentication module.

These tests cover edge cases and less common code paths.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import logging


class TestAPIKeyMiddlewareEdgeCases:
    """Additional tests for API key middleware edge cases."""
    
    @pytest.mark.asyncio
    async def test_middleware_with_app_initialization(self):
        """Test middleware initialization with an ASGI app."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        mock_app = Mock()
        middleware = APIKeyMiddleware(
            app=mock_app,
            api_key="test_key"
        )
        
        # Should call parent's __init__ with app
        assert middleware.api_keys == ["test_key"]
    
    @pytest.mark.asyncio
    async def test_dispatch_method_coverage(self):
        """Test the dispatch method that delegates to __call__."""
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        middleware = APIKeyMiddleware(api_key="test_key")
        
        mock_request = Mock()
        mock_request.headers = {"x-api-key": "test_key"}
        mock_request.url = Mock()
        mock_request.url.path = "/api/test"
        mock_request.state = Mock()
        
        async def mock_call_next(request):
            return Mock(status_code=200)
        
        # Test dispatch method
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200


class TestAccessControlEdgeCases:
    """Additional tests for access control edge cases."""
    
    @pytest.mark.asyncio
    async def test_get_access_error_missing_api_key_path(self):
        """Test error response when API key is missing."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Test with missing API key (line 194)
        error = await access_control.get_access_error(
            resource_type="file",
            resource=Mock(),
            api_key=None,
            jwt_token=None
        )
        
        assert error["code"] == "INVALID_API_KEY"
        assert error["message"] == "API key is missing"
    
    @pytest.mark.asyncio
    async def test_get_access_error_invalid_api_key_path(self):
        """Test error response when API key is invalid."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl(valid_api_keys=["valid_key"])
        
        # Test with invalid API key (line 202)
        error = await access_control.get_access_error(
            resource_type="file",
            resource=Mock(),
            api_key="invalid_key",
            jwt_token=None
        )
        
        assert error["code"] == "INVALID_API_KEY"
        assert error["message"] == "Provided API key is invalid"
    
    @pytest.mark.asyncio
    async def test_get_access_error_table_resource_type(self):
        """Test error response for table resource type."""
        from shared.auth.access_control import AccessControl
        
        # Initialize AccessControl with valid API key to bypass validation
        access_control = AccessControl(valid_api_keys=["valid_key"])
        
        mock_table = Mock()
        mock_table.name = "users"
        
        # Test table resource type branch - with valid API key should return FORBIDDEN_PUBLIC
        error = await access_control.get_access_error(
            resource_type="table",
            resource=mock_table,
            api_key="valid_key",
            jwt_token=None
        )
        
        assert error["code"] == "FORBIDDEN_PUBLIC"
        assert error["details"]["table_name"] == "users"
    
    @pytest.mark.asyncio
    async def test_get_access_error_other_resource_type(self):
        """Test error response for other resource types."""
        from shared.auth.access_control import AccessControl
        
        # Initialize AccessControl with valid API key to bypass validation
        access_control = AccessControl(valid_api_keys=["valid_key"])
        
        mock_resource = Mock()
        mock_resource.id = "resource_123"
        
        # Test else branch for unknown resource types - with valid API key should return FORBIDDEN_PUBLIC
        error = await access_control.get_access_error(
            resource_type="custom",
            resource=mock_resource,
            api_key="valid_key",
            jwt_token=None
        )
        
        assert error["code"] == "FORBIDDEN_PUBLIC"
        assert error["details"]["custom_id"] == "resource_123"
    
    @pytest.mark.asyncio
    async def test_webhook_access_with_invalid_token(self):
        """Test webhook access with invalid/missing token."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl(enable_logging=True)
        
        # Test with no token (lines 254-256)
        is_allowed = await access_control.check_webhook_access(
            webhook_token="",
            function_id="func_123"
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_webhook_access_logging_disabled(self):
        """Test webhook access with logging disabled."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl(enable_logging=False)
        
        # Test with valid token but logging disabled
        is_allowed = await access_control.check_webhook_access(
            webhook_token="valid_token",
            function_id="func_456"
        )
        
        assert is_allowed is True
        
        # Test with invalid token and logging disabled
        is_allowed = await access_control.check_webhook_access(
            webhook_token="",
            function_id="func_789"
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_public_access_logging_disabled(self):
        """Test public access with logging disabled."""
        from shared.auth.access_control import AccessControl
        
        # Initialize with valid API key and logging disabled
        access_control = AccessControl(valid_api_keys=["test_key"], enable_logging=False)
        
        mock_bucket = Mock()
        mock_bucket.public = True
        mock_bucket.name = "test-bucket"
        
        # Test successful public access without logging
        is_allowed = await access_control.check_public_access(
            resource_type="bucket",
            resource=mock_bucket,
            api_key="test_key",
            jwt_token=None
        )
        
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_public_access_private_resource_logging_disabled(self):
        """Test private resource access attempt with logging disabled."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl(enable_logging=False)
        
        mock_bucket = Mock()
        mock_bucket.public = False
        
        # Test private resource without logging
        is_allowed = await access_control.check_public_access(
            resource_type="bucket",
            resource=mock_bucket,
            api_key="test_key",
            jwt_token=None
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_access_control_with_empty_api_key_list(self):
        """Test AccessControl with empty API key in environment."""
        from shared.auth.access_control import AccessControl
        import os
        
        # Temporarily remove API_KEY from environment
        old_api_key = os.environ.get("API_KEY")
        if old_api_key:
            del os.environ["API_KEY"]
        
        try:
            access_control = AccessControl()
            
            # Should accept any non-empty API key when no valid keys configured
            mock_resource = Mock()
            mock_resource.public = True
            
            is_allowed = await access_control.check_public_access(
                resource_type="bucket",
                resource=mock_resource,
                api_key="any_key",
                jwt_token=None
            )
            
            assert is_allowed is True
        finally:
            # Restore environment
            if old_api_key:
                os.environ["API_KEY"] = old_api_key