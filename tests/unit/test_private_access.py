"""
Unit tests for private access requiring API key + JWT.

Tests the combined authentication: API key validation + JWT token validation
for accessing private resources (buckets, tables, files).
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any


class TestPrivateAccess:
    """Test suite for private resource access requiring API key + JWT."""
    
    @pytest.fixture
    def api_key(self):
        """Valid API key for testing."""
        return "test_api_key_123"
    
    @pytest.fixture
    def jwt_service(self):
        """Mock JWT service for testing."""
        from shared.auth.jwt_service import JWTService
        return JWTService(
            secret_key="test_jwt_secret",
            algorithm="HS256",
            access_token_expire_minutes=30
        )
    
    @pytest.fixture
    def sample_user_payload(self):
        """Sample user data for JWT."""
        return {
            "user_id": "user_123",
            "email": "user@example.com",
            "role": "USER",
            "is_active": True
        }
    
    @pytest.fixture
    def sample_admin_payload(self):
        """Sample admin user data for JWT."""
        return {
            "user_id": "admin_456", 
            "email": "admin@example.com",
            "role": "ADMIN",
            "is_active": True
        }
    
    @pytest.fixture
    def mock_private_bucket(self):
        """Create a mock private bucket."""
        bucket = Mock()
        bucket.id = "bucket_private_123"
        bucket.name = "private-documents"
        bucket.public = False
        bucket.owner_id = "user_123"
        return bucket
    
    @pytest.fixture
    def mock_private_table(self):
        """Create a mock private table."""
        table = Mock()
        table.name = "user_data"
        table.public = False
        table.owner_id = "user_123"
        return table
    
    @pytest.mark.asyncio
    async def test_private_bucket_access_with_api_key_and_jwt(
        self, api_key, jwt_service, sample_user_payload, mock_private_bucket
    ):
        """Test that private bucket can be accessed with API key + valid JWT."""
        from shared.auth.private_access import PrivateAccessControl
        
        # Generate valid JWT
        jwt_token = jwt_service.generate_access_token(sample_user_payload)
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=api_key,
            jwt_token=jwt_token
        )
        
        assert is_allowed is True
        assert mock_private_bucket.public is False
    
    @pytest.mark.asyncio
    async def test_private_bucket_denied_without_jwt(
        self, api_key, jwt_service, mock_private_bucket
    ):
        """Test that private bucket cannot be accessed with API key only."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=api_key,
            jwt_token=None
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_private_bucket_denied_with_invalid_jwt(
        self, api_key, jwt_service, mock_private_bucket
    ):
        """Test that private bucket cannot be accessed with invalid JWT."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=api_key,
            jwt_token="invalid.jwt.token"
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_private_bucket_denied_without_api_key(
        self, jwt_service, sample_user_payload, mock_private_bucket
    ):
        """Test that private bucket cannot be accessed without API key."""
        from shared.auth.private_access import PrivateAccessControl
        
        jwt_token = jwt_service.generate_access_token(sample_user_payload)
        
        private_access = PrivateAccessControl(
            api_key="valid_api_key",
            jwt_service=jwt_service
        )
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=None,
            jwt_token=jwt_token
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_private_table_crud_with_api_key_and_jwt(
        self, api_key, jwt_service, sample_user_payload, mock_private_table
    ):
        """Test that private table allows CRUD with API key + JWT."""
        from shared.auth.private_access import PrivateAccessControl
        
        jwt_token = jwt_service.generate_access_token(sample_user_payload)
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        # Test all CRUD operations
        operations = ["create", "read", "update", "delete"]
        
        for operation in operations:
            is_allowed = await private_access.check_private_access(
                resource_type="table",
                resource=mock_private_table,
                api_key=api_key,
                jwt_token=jwt_token,
                operation=operation
            )
            assert is_allowed is True, f"Operation {operation} should be allowed on private table"
    
    @pytest.mark.asyncio
    async def test_expired_jwt_denies_private_access(
        self, api_key, mock_private_bucket
    ):
        """Test that expired JWT denies access to private resources."""
        from shared.auth.private_access import PrivateAccessControl
        from shared.auth.jwt_service import JWTService
        
        # Create JWT service with very short expiration
        jwt_service = JWTService(
            secret_key="test_secret",
            access_token_expire_minutes=0  # Expires immediately
        )
        
        jwt_token = jwt_service.generate_access_token({
            "user_id": "user_123",
            "email": "user@example.com",
            "role": "USER"
        })
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        # Wait a moment to ensure token expires
        import asyncio
        await asyncio.sleep(0.1)
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=api_key,
            jwt_token=jwt_token
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_user_can_access_own_resources(
        self, api_key, jwt_service, sample_user_payload
    ):
        """Test that users can access their own private resources."""
        from shared.auth.private_access import PrivateAccessControl
        
        jwt_token = jwt_service.generate_access_token(sample_user_payload)
        
        # Create resource owned by the same user
        user_bucket = Mock()
        user_bucket.id = "user_bucket_123"
        user_bucket.name = "my-private-bucket"
        user_bucket.public = False
        user_bucket.owner_id = sample_user_payload["user_id"]  # Same user
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=user_bucket,
            api_key=api_key,
            jwt_token=jwt_token,
            check_ownership=True
        )
        
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_resources(
        self, api_key, jwt_service, sample_user_payload
    ):
        """Test that users cannot access other users' private resources."""
        from shared.auth.private_access import PrivateAccessControl
        
        jwt_token = jwt_service.generate_access_token(sample_user_payload)
        
        # Create resource owned by different user
        other_user_bucket = Mock()
        other_user_bucket.id = "other_bucket_456"
        other_user_bucket.name = "other-user-bucket"
        other_user_bucket.public = False
        other_user_bucket.owner_id = "different_user_456"  # Different user
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=other_user_bucket,
            api_key=api_key,
            jwt_token=jwt_token,
            check_ownership=True
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_can_access_any_private_resource(
        self, api_key, jwt_service, sample_admin_payload
    ):
        """Test that admin users can access any private resource."""
        from shared.auth.private_access import PrivateAccessControl
        
        jwt_token = jwt_service.generate_access_token(sample_admin_payload)
        
        # Create resource owned by different user
        user_bucket = Mock()
        user_bucket.id = "user_bucket_789"
        user_bucket.name = "user-private-bucket"
        user_bucket.public = False
        user_bucket.owner_id = "different_user_789"
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=user_bucket,
            api_key=api_key,
            jwt_token=jwt_token,
            check_ownership=True
        )
        
        assert is_allowed is True  # Admin can access any resource
    
    @pytest.mark.asyncio
    async def test_inactive_user_denied_access(
        self, api_key, jwt_service, mock_private_bucket
    ):
        """Test that inactive users are denied access to private resources."""
        from shared.auth.private_access import PrivateAccessControl
        
        inactive_user_payload = {
            "user_id": "inactive_user_123",
            "email": "inactive@example.com",
            "role": "USER",
            "is_active": False  # User is inactive
        }
        
        jwt_token = jwt_service.generate_access_token(inactive_user_payload)
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=api_key,
            jwt_token=jwt_token
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_private_file_operations_require_jwt(
        self, api_key, jwt_service, sample_user_payload
    ):
        """Test that private file operations require JWT."""
        from shared.auth.private_access import PrivateAccessControl
        
        jwt_token = jwt_service.generate_access_token(sample_user_payload)
        
        private_bucket = Mock()
        private_bucket.id = "private_files_bucket"
        private_bucket.public = False
        private_bucket.owner_id = sample_user_payload["user_id"]
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        # Test file operations
        file_operations = [
            ("upload", {"bucket": private_bucket, "filename": "document.pdf"}),
            ("download", {"bucket": private_bucket, "file_id": "file_123"}),
            ("delete", {"bucket": private_bucket, "file_id": "file_123"}),
            ("list", {"bucket": private_bucket})
        ]
        
        for operation, params in file_operations:
            is_allowed = await private_access.check_file_operation(
                operation=operation,
                api_key=api_key,
                jwt_token=jwt_token,
                **params
            )
            assert is_allowed is True, f"File operation {operation} should be allowed with JWT"
    
    @pytest.mark.asyncio
    async def test_private_access_error_responses(
        self, api_key, jwt_service, mock_private_bucket
    ):
        """Test error responses for private access failures."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        # Test missing JWT error
        error = await private_access.get_access_error(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=api_key,
            jwt_token=None
        )
        
        assert error["code"] == "JWT_REQUIRED"
        assert "JWT token is required" in error["message"]
        assert error["details"]["resource_type"] == "bucket"
    
    @pytest.mark.asyncio
    async def test_private_access_logging(
        self, api_key, jwt_service, sample_user_payload, mock_private_bucket, caplog
    ):
        """Test that private access attempts are logged."""
        from shared.auth.private_access import PrivateAccessControl
        import logging
        
        caplog.set_level(logging.INFO)
        
        jwt_token = jwt_service.generate_access_token(sample_user_payload)
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_private_bucket,
            api_key=api_key,
            jwt_token=jwt_token
        )
        
        assert "Private access granted" in caplog.text
        assert sample_user_payload["user_id"] in caplog.text
    
    @pytest.mark.asyncio
    async def test_combined_middleware_integration(
        self, api_key, jwt_service, sample_user_payload
    ):
        """Test integration with API key middleware and JWT validation."""
        from shared.auth.private_access import PrivateAccessControl
        from shared.auth.api_key_middleware import APIKeyMiddleware
        
        jwt_token = jwt_service.generate_access_token(sample_user_payload)
        
        # Test that both middlewares work together
        api_middleware = APIKeyMiddleware(api_key=api_key)
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        # Mock request with both headers
        mock_request = Mock()
        mock_request.headers = {
            "x-api-key": api_key,
            "authorization": f"Bearer {jwt_token}"
        }
        mock_request.url = Mock()
        mock_request.url.path = "/api/v1/buckets"
        mock_request.state = Mock()
        
        # Simulate middleware processing
        extracted_api_key = mock_request.headers["x-api-key"]
        extracted_jwt = mock_request.headers["authorization"].replace("Bearer ", "")
        
        assert extracted_api_key == api_key
        assert extracted_jwt == jwt_token
        
        # Validate both
        assert extracted_api_key in api_middleware.api_keys
        user_info = jwt_service.extract_user_info(extracted_jwt)
        assert user_info["user_id"] == sample_user_payload["user_id"]
    
    def test_private_access_control_initialization(self, api_key, jwt_service):
        """Test PrivateAccessControl initialization."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service,
            enable_logging=True,
            check_user_active=True
        )
        
        assert private_access.api_key == api_key
        assert private_access.jwt_service == jwt_service
        assert private_access.enable_logging is True
        assert private_access.check_user_active is True
    
    def test_private_access_control_missing_jwt_service_raises_error(self, api_key):
        """Test that PrivateAccessControl requires a JWT service."""
        from shared.auth.private_access import PrivateAccessControl
        
        with pytest.raises(ValueError, match="JWT service must be provided"):
            PrivateAccessControl(api_key=api_key, jwt_service=None)