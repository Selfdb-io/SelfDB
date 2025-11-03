"""
Additional tests for private access to achieve 95%+ coverage.

These tests cover edge cases and error conditions.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone


class TestPrivateAccessEdgeCases:
    """Additional tests for private access edge cases."""
    
    @pytest.fixture
    def jwt_service(self):
        """Mock JWT service for testing."""
        from shared.auth.jwt_service import JWTService
        return JWTService(
            secret_key="test_secret",
            algorithm="HS256",
            access_token_expire_minutes=30
        )
    
    @pytest.fixture
    def api_key(self):
        """Valid API key for testing."""
        return "test_api_key_123"
    
    @pytest.fixture
    def sample_payload(self):
        """Sample user payload."""
        return {
            "user_id": "user_123",
            "email": "user@example.com",
            "role": "USER",
            "is_active": True
        }
    
    @pytest.mark.asyncio
    async def test_access_denied_with_logging_disabled(self, api_key, jwt_service):
        """Test access denial with logging disabled."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service,
            enable_logging=False  # Logging disabled
        )
        
        mock_resource = Mock()
        mock_resource.public = False
        
        # Test various denial scenarios without logging
        scenarios = [
            {"api_key": None, "jwt_token": "valid_jwt"},  # Missing API key
            {"api_key": "wrong_key", "jwt_token": "valid_jwt"},  # Wrong API key
            {"api_key": api_key, "jwt_token": None},  # Missing JWT
            {"api_key": api_key, "jwt_token": "invalid.jwt"},  # Invalid JWT
        ]
        
        for scenario in scenarios:
            is_allowed = await private_access.check_private_access(
                resource_type="bucket",
                resource=mock_resource,
                api_key=scenario["api_key"],
                jwt_token=scenario["jwt_token"]
            )
            assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_check_user_active_disabled(self, api_key, jwt_service):
        """Test private access with user active checking disabled."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service,
            check_user_active=False  # Don't check user active status
        )
        
        # Create JWT for inactive user
        inactive_payload = {
            "user_id": "inactive_user",
            "email": "inactive@example.com",
            "role": "USER",
            "is_active": False  # User is inactive
        }
        jwt_token = jwt_service.generate_access_token(inactive_payload)
        
        mock_resource = Mock()
        mock_resource.public = False
        
        # Should allow access even for inactive user when checking is disabled
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_resource,
            api_key=api_key,
            jwt_token=jwt_token
        )
        
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_get_access_error_api_key_scenarios(self, jwt_service):
        """Test get_access_error for API key related errors."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key="correct_key",
            jwt_service=jwt_service
        )
        
        mock_resource = Mock()
        
        # Test missing API key error
        error = await private_access.get_access_error(
            resource_type="bucket",
            resource=mock_resource,
            api_key=None,
            jwt_token="some_jwt"
        )
        assert error["code"] == "API_KEY_REQUIRED"
        
        # Test invalid API key error
        error = await private_access.get_access_error(
            resource_type="bucket",
            resource=mock_resource,
            api_key="wrong_key",
            jwt_token="some_jwt"
        )
        assert error["code"] == "INVALID_API_KEY"
    
    @pytest.mark.asyncio
    async def test_get_access_error_jwt_scenarios(self, api_key, jwt_service, sample_payload):
        """Test get_access_error for JWT related errors."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        mock_resource = Mock()
        
        # Test missing JWT error
        error = await private_access.get_access_error(
            resource_type="table",
            resource=mock_resource,
            api_key=api_key,
            jwt_token=None
        )
        assert error["code"] == "JWT_REQUIRED"
        
        # Test invalid JWT error
        error = await private_access.get_access_error(
            resource_type="table",
            resource=mock_resource,
            api_key=api_key,
            jwt_token="invalid.jwt.token"
        )
        assert error["code"] == "INVALID_JWT"
    
    @pytest.mark.asyncio
    async def test_get_access_error_inactive_user(self, api_key, jwt_service):
        """Test get_access_error for inactive user."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service,
            check_user_active=True
        )
        
        # Create JWT for inactive user
        inactive_payload = {
            "user_id": "inactive_123",
            "email": "inactive@example.com",
            "role": "USER",
            "is_active": False
        }
        jwt_token = jwt_service.generate_access_token(inactive_payload)
        
        mock_resource = Mock()
        
        error = await private_access.get_access_error(
            resource_type="file",
            resource=mock_resource,
            api_key=api_key,
            jwt_token=jwt_token
        )
        
        assert error["code"] == "USER_INACTIVE"
        assert error["details"]["user_id"] == "inactive_123"
    
    @pytest.mark.asyncio
    async def test_get_access_error_access_denied_scenarios(self, api_key, jwt_service, sample_payload):
        """Test get_access_error for general access denied cases."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        jwt_token = jwt_service.generate_access_token(sample_payload)
        
        # Test different resource types
        test_cases = [
            {
                "resource_type": "bucket",
                "resource": Mock(id="bucket_123"),
                "expected_key": "bucket_id"
            },
            {
                "resource_type": "table", 
                "resource": Mock(name="users"),
                "expected_key": "table_name"
            },
            {
                "resource_type": "custom",
                "resource": Mock(id="custom_456"),
                "expected_key": "custom_id"
            }
        ]
        
        for case in test_cases:
            error = await private_access.get_access_error(
                resource_type=case["resource_type"],
                resource=case["resource"],
                api_key=api_key,
                jwt_token=jwt_token
            )
            
            assert error["code"] == "ACCESS_DENIED"
            assert case["expected_key"] in error["details"]
            assert error["details"]["user_id"] == sample_payload["user_id"]
    
    @pytest.mark.asyncio
    async def test_ownership_check_with_no_owner_id(self, api_key, jwt_service, sample_payload):
        """Test ownership checking when resource has no owner_id."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        jwt_token = jwt_service.generate_access_token(sample_payload)
        
        # Resource with no owner_id attribute
        resource_no_owner = Mock()
        resource_no_owner.public = False
        # No owner_id attribute set
        
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=resource_no_owner,
            api_key=api_key,
            jwt_token=jwt_token,
            check_ownership=True
        )
        
        # Should be denied since user_id doesn't match None
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_jwt_payload_missing_role(self, api_key, jwt_service):
        """Test access with JWT payload missing role field."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        # Create JWT without role field
        payload_no_role = {
            "user_id": "user_no_role",
            "email": "norole@example.com",
            "is_active": True
            # No role field
        }
        jwt_token = jwt_service.generate_access_token(payload_no_role)
        
        mock_resource = Mock()
        mock_resource.public = False
        mock_resource.owner_id = "different_user"
        
        # Should default to USER role and deny access to other's resource
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_resource,
            api_key=api_key,
            jwt_token=jwt_token,
            check_ownership=True
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_jwt_payload_missing_is_active_defaults_to_true(self, api_key, jwt_service):
        """Test that missing is_active in JWT defaults to True."""
        from shared.auth.private_access import PrivateAccessControl
        
        private_access = PrivateAccessControl(
            api_key=api_key,
            jwt_service=jwt_service,
            check_user_active=True
        )
        
        # Create JWT without is_active field
        payload_no_active = {
            "user_id": "user_no_active",
            "email": "noactive@example.com",
            "role": "USER"
            # No is_active field - should default to True
        }
        jwt_token = jwt_service.generate_access_token(payload_no_active)
        
        mock_resource = Mock()
        mock_resource.public = False
        
        # Should allow access since is_active defaults to True
        is_allowed = await private_access.check_private_access(
            resource_type="bucket",
            resource=mock_resource,
            api_key=api_key,
            jwt_token=jwt_token
        )
        
        assert is_allowed is True