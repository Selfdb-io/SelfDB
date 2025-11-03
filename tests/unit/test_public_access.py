"""
Unit tests for public access with API key only.

Tests the access control for public resources that only require API key.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Optional, Dict, Any
from shared.models.bucket import Bucket
from shared.models.table import Table


class TestPublicAccess:
    """Test suite for public resource access with API key only."""
    
    @pytest.fixture
    def api_key(self):
        """Valid API key for testing."""
        return "test_api_key_123"
    
    @pytest.fixture
    def mock_public_bucket(self):
        """Create a mock public bucket."""
        bucket = Mock(spec=Bucket)
        bucket.id = "bucket_123"
        bucket.name = "public-assets"
        bucket.public = True
        bucket.owner_id = "user_456"
        return bucket
    
    @pytest.fixture
    def mock_private_bucket(self):
        """Create a mock private bucket."""
        bucket = Mock(spec=Bucket)
        bucket.id = "bucket_789"
        bucket.name = "private-docs"
        bucket.public = False
        bucket.owner_id = "user_456"
        return bucket
    
    @pytest.fixture
    def mock_public_table(self):
        """Create a mock public table."""
        table = Mock(spec=Table)
        table.name = "products"
        table.public = True
        table.owner_id = "user_456"
        return table
    
    @pytest.fixture
    def mock_private_table(self):
        """Create a mock private table."""
        table = Mock(spec=Table)
        table.name = "user_profiles"
        table.public = False
        table.owner_id = "user_456"
        return table
    
    @pytest.mark.asyncio
    async def test_public_bucket_access_with_api_key_only(self, api_key, mock_public_bucket):
        """Test that public bucket can be accessed with just API key."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Check if access is allowed with just API key for public bucket
        is_allowed = await access_control.check_public_access(
            resource_type="bucket",
            resource=mock_public_bucket,
            api_key=api_key,
            jwt_token=None
        )
        
        assert is_allowed is True
        assert mock_public_bucket.public is True
    
    @pytest.mark.asyncio
    async def test_private_bucket_denied_with_api_key_only(self, api_key, mock_private_bucket):
        """Test that private bucket cannot be accessed with just API key."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Check if access is denied with just API key for private bucket
        is_allowed = await access_control.check_public_access(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=api_key,
            jwt_token=None
        )
        
        assert is_allowed is False
        assert mock_private_bucket.public is False
    
    @pytest.mark.asyncio
    async def test_public_table_crud_with_api_key_only(self, api_key, mock_public_table):
        """Test that public table allows full CRUD with just API key."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Test all CRUD operations
        operations = ["create", "read", "update", "delete"]
        
        for operation in operations:
            is_allowed = await access_control.check_public_access(
                resource_type="table",
                resource=mock_public_table,
                api_key=api_key,
                jwt_token=None,
                operation=operation
            )
            assert is_allowed is True, f"Operation {operation} should be allowed on public table"
    
    @pytest.mark.asyncio
    async def test_private_table_denied_with_api_key_only(self, api_key, mock_private_table):
        """Test that private table denies access with just API key."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Test all CRUD operations should be denied
        operations = ["create", "read", "update", "delete"]
        
        for operation in operations:
            is_allowed = await access_control.check_public_access(
                resource_type="table",
                resource=mock_private_table,
                api_key=api_key,
                jwt_token=None,
                operation=operation
            )
            assert is_allowed is False, f"Operation {operation} should be denied on private table"
    
    @pytest.mark.asyncio
    async def test_file_inherits_bucket_public_status(self, api_key, mock_public_bucket):
        """Test that files inherit public/private status from their bucket."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Create a file in a public bucket
        mock_file = Mock()
        mock_file.bucket_id = mock_public_bucket.id
        mock_file.name = "document.pdf"
        
        # File should be accessible if bucket is public
        is_allowed = await access_control.check_file_access(
            file=mock_file,
            bucket=mock_public_bucket,
            api_key=api_key,
            jwt_token=None
        )
        
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_missing_api_key_denies_public_access(self, mock_public_bucket):
        """Test that even public resources require an API key."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # No API key provided
        is_allowed = await access_control.check_public_access(
            resource_type="bucket",
            resource=mock_public_bucket,
            api_key=None,
            jwt_token=None
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_denies_public_access(self, mock_public_bucket):
        """Test that invalid API key denies access to public resources."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl(valid_api_keys=["correct_key"])
        
        # Wrong API key
        is_allowed = await access_control.check_public_access(
            resource_type="bucket",
            resource=mock_public_bucket,
            api_key="wrong_key",
            jwt_token=None
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_public_resource_error_response_format(self, api_key, mock_private_bucket):
        """Test error response when accessing private resource with API key only."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Try to access private resource
        error = await access_control.get_access_error(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=api_key,
            jwt_token=None
        )
        
        assert error["code"] == "FORBIDDEN_PUBLIC"
        assert "JWT authentication" in error["message"]
        assert error["details"]["resource_type"] == "bucket"
        assert error["details"]["bucket_id"] == mock_private_bucket.id
    
    @pytest.mark.asyncio
    async def test_public_file_operations(self, api_key, mock_public_bucket):
        """Test file operations on public bucket with API key only."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Test file operations
        file_operations = [
            ("upload", {"bucket": mock_public_bucket, "filename": "test.txt"}),
            ("download", {"bucket": mock_public_bucket, "file_id": "file_123"}),
            ("delete", {"bucket": mock_public_bucket, "file_id": "file_123"}),
            ("list", {"bucket": mock_public_bucket})
        ]
        
        for operation, params in file_operations:
            is_allowed = await access_control.check_file_operation(
                operation=operation,
                api_key=api_key,
                jwt_token=None,
                **params
            )
            assert is_allowed is True, f"File operation {operation} should be allowed on public bucket"
    
    @pytest.mark.asyncio
    async def test_public_table_query_operations(self, api_key, mock_public_table):
        """Test query operations on public table with API key only."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Test various query operations
        query_operations = [
            {"type": "select", "table": mock_public_table},
            {"type": "insert", "table": mock_public_table},
            {"type": "update", "table": mock_public_table},
            {"type": "delete", "table": mock_public_table}
        ]
        
        for query_op in query_operations:
            is_allowed = await access_control.check_table_query(
                api_key=api_key,
                jwt_token=None,
                **query_op
            )
            assert is_allowed is True, f"Query {query_op['type']} should be allowed on public table"
    
    @pytest.mark.asyncio
    async def test_public_access_logging(self, api_key, mock_public_bucket, caplog):
        """Test that public access attempts are logged."""
        from shared.auth.access_control import AccessControl
        import logging
        
        caplog.set_level(logging.INFO)
        access_control = AccessControl()
        
        await access_control.check_public_access(
            resource_type="bucket",
            resource=mock_public_bucket,
            api_key=api_key,
            jwt_token=None
        )
        
        assert "Public access granted" in caplog.text
        assert mock_public_bucket.name in caplog.text
    
    @pytest.mark.asyncio
    async def test_resource_not_found_handling(self, api_key):
        """Test handling of non-existent resources."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Resource is None
        is_allowed = await access_control.check_public_access(
            resource_type="bucket",
            resource=None,
            api_key=api_key,
            jwt_token=None
        )
        
        assert is_allowed is False
    
    def test_access_control_initialization(self):
        """Test AccessControl initialization with configuration."""
        from shared.auth.access_control import AccessControl
        
        # Test with custom API keys
        access_control = AccessControl(
            valid_api_keys=["key1", "key2"],
            enable_logging=True
        )
        
        assert len(access_control.valid_api_keys) == 2
        assert access_control.enable_logging is True
    
    @pytest.mark.asyncio
    async def test_public_webhook_access(self, api_key):
        """Test that webhooks can be accessed without JWT (special case)."""
        from shared.auth.access_control import AccessControl
        
        access_control = AccessControl()
        
        # Webhooks have special token-based auth, not JWT
        is_allowed = await access_control.check_webhook_access(
            webhook_token="webhook_secret_123",
            function_id="func_456"
        )
        
        # Should validate webhook token, not require JWT
        assert is_allowed is True