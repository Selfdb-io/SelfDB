"""
Additional tests for admin access to achieve 95%+ coverage.

These tests cover edge cases and error conditions not covered by main tests.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone


class TestAdminAccessEdgeCases:
    """Additional tests for admin access edge cases."""
    
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
    def admin_payload(self):
        """Sample admin payload."""
        return {
            "user_id": "admin_123",
            "email": "admin@example.com",
            "role": "ADMIN",
            "is_active": True
        }
    
    @pytest.mark.asyncio
    async def test_admin_resource_access_with_none_resource(self, api_key, jwt_service, admin_payload):
        """Test admin resource access with None resource."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await admin_access.check_admin_resource_access(
            resource_type="bucket",
            resource=None,  # None resource
            api_key=api_key,
            jwt_token=admin_jwt
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_resource_access_invalid_api_key(self, api_key, jwt_service, admin_payload):
        """Test admin resource access with invalid API key."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        mock_resource = Mock()
        mock_resource.id = "resource_123"
        
        is_allowed = await admin_access.check_admin_resource_access(
            resource_type="table",
            resource=mock_resource,
            api_key="wrong_key",  # Invalid API key
            jwt_token=admin_jwt
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_resource_access_missing_jwt(self, api_key, jwt_service):
        """Test admin resource access with missing JWT."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        mock_resource = Mock()
        mock_resource.name = "test_table"
        
        is_allowed = await admin_access.check_admin_resource_access(
            resource_type="table",
            resource=mock_resource,
            api_key=api_key,
            jwt_token=None  # Missing JWT
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_resource_access_invalid_jwt(self, api_key, jwt_service):
        """Test admin resource access with invalid JWT."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        mock_resource = Mock()
        mock_resource.id = "file_456"
        
        is_allowed = await admin_access.check_admin_resource_access(
            resource_type="file",
            resource=mock_resource,
            api_key=api_key,
            jwt_token="invalid.jwt.token"  # Invalid JWT
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_resource_access_inactive_admin(self, api_key, jwt_service):
        """Test admin resource access with inactive admin."""
        from shared.auth.admin_access import AdminAccessControl
        
        inactive_admin = {
            "user_id": "inactive_admin",
            "email": "inactive@admin.com",
            "role": "ADMIN",
            "is_active": False  # Inactive admin
        }
        
        admin_jwt = jwt_service.generate_access_token(inactive_admin)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        mock_resource = Mock()
        mock_resource.id = "bucket_789"
        
        is_allowed = await admin_access.check_admin_resource_access(
            resource_type="bucket",
            resource=mock_resource,
            api_key=api_key,
            jwt_token=admin_jwt
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_resource_access_non_admin_user(self, api_key, jwt_service):
        """Test admin resource access with non-admin user."""
        from shared.auth.admin_access import AdminAccessControl
        
        regular_user = {
            "user_id": "user_456",
            "email": "user@example.com", 
            "role": "USER",  # Not admin
            "is_active": True
        }
        
        user_jwt = jwt_service.generate_access_token(regular_user)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        mock_resource = Mock()
        mock_resource.id = "function_321"
        
        is_allowed = await admin_access.check_admin_resource_access(
            resource_type="function",
            resource=mock_resource,
            api_key=api_key,
            jwt_token=user_jwt
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_access_error_missing_api_key(self, jwt_service, admin_payload):
        """Test admin access error with missing API key."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_payload)
        
        admin_access = AdminAccessControl(
            api_key="valid_key",
            jwt_service=jwt_service
        )
        
        error = await admin_access.get_admin_access_error(
            operation="list_users",
            api_key=None,  # Missing API key
            jwt_token=admin_jwt
        )
        
        assert error["code"] == "API_KEY_REQUIRED"
        assert error["details"]["operation"] == "list_users"
    
    @pytest.mark.asyncio
    async def test_admin_access_error_invalid_api_key(self, jwt_service, admin_payload):
        """Test admin access error with invalid API key."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_payload)
        
        admin_access = AdminAccessControl(
            api_key="correct_key",
            jwt_service=jwt_service
        )
        
        error = await admin_access.get_admin_access_error(
            operation="delete_user",
            api_key="wrong_key",  # Invalid API key
            jwt_token=admin_jwt
        )
        
        assert error["code"] == "INVALID_API_KEY"
        assert error["details"]["operation"] == "delete_user"
    
    @pytest.mark.asyncio
    async def test_admin_access_error_missing_jwt(self, api_key, jwt_service):
        """Test admin access error with missing JWT."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        error = await admin_access.get_admin_access_error(
            operation="backup_database",
            api_key=api_key,
            jwt_token=None  # Missing JWT
        )
        
        assert error["code"] == "JWT_REQUIRED"
        assert error["details"]["operation"] == "backup_database"
    
    @pytest.mark.asyncio
    async def test_admin_access_error_invalid_jwt(self, api_key, jwt_service):
        """Test admin access error with invalid JWT."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        error = await admin_access.get_admin_access_error(
            operation="manage_api_keys",
            api_key=api_key,
            jwt_token="invalid.jwt.token"  # Invalid JWT
        )
        
        assert error["code"] == "INVALID_JWT"
        assert error["details"]["operation"] == "manage_api_keys"
    
    @pytest.mark.asyncio
    async def test_admin_access_error_inactive_user(self, api_key, jwt_service):
        """Test admin access error with inactive user."""
        from shared.auth.admin_access import AdminAccessControl
        
        inactive_admin = {
            "user_id": "inactive_admin_789",
            "email": "inactive_admin@example.com",
            "role": "ADMIN",
            "is_active": False  # Inactive
        }
        
        admin_jwt = jwt_service.generate_access_token(inactive_admin)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        error = await admin_access.get_admin_access_error(
            operation="restore_database",
            api_key=api_key,
            jwt_token=admin_jwt
        )
        
        assert error["code"] == "USER_INACTIVE"
        assert error["details"]["operation"] == "restore_database"
        assert error["details"]["user_id"] == "inactive_admin_789"
    
    @pytest.mark.asyncio
    async def test_admin_access_error_insufficient_privileges(self, api_key, jwt_service):
        """Test admin access error with insufficient privileges."""
        from shared.auth.admin_access import AdminAccessControl
        
        regular_user = {
            "user_id": "regular_user_123",
            "email": "regular@example.com",
            "role": "USER",  # Not admin
            "is_active": True
        }
        
        user_jwt = jwt_service.generate_access_token(regular_user)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        error = await admin_access.get_admin_access_error(
            operation="view_system_logs",
            api_key=api_key,
            jwt_token=user_jwt
        )
        
        assert error["code"] == "INSUFFICIENT_PRIVILEGES"
        assert error["details"]["operation"] == "view_system_logs"
        assert error["details"]["user_role"] == "USER"
        assert error["details"]["user_id"] == "regular_user_123"
    
    @pytest.mark.asyncio
    async def test_admin_access_with_logging_disabled(self, api_key, jwt_service, admin_payload):
        """Test admin access with logging disabled."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service,
            enable_logging=False  # Logging disabled
        )
        
        # Test various scenarios with logging disabled
        scenarios = [
            {"operation": "invalid_operation", "expected": False},  # Invalid operation
            {"operation": "list_users", "api_key": None, "expected": False},  # Missing API key
            {"operation": "list_users", "jwt_token": None, "expected": False},  # Missing JWT
            {"operation": "list_users", "jwt_token": "invalid.jwt", "expected": False},  # Invalid JWT
        ]
        
        for scenario in scenarios:
            is_allowed = await admin_access.check_admin_operation(
                operation=scenario["operation"],
                api_key=scenario.get("api_key", api_key),
                jwt_token=scenario.get("jwt_token", admin_jwt)
            )
            assert is_allowed == scenario["expected"]
    
    @pytest.mark.asyncio
    async def test_admin_resource_access_with_logging_disabled(self, api_key, jwt_service, admin_payload):
        """Test admin resource access with logging disabled."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service,
            enable_logging=False  # Logging disabled
        )
        
        mock_resource = Mock()
        mock_resource.id = "test_resource"
        
        # Test various denial scenarios without logging
        scenarios = [
            {"resource": None, "expected": False},  # None resource
            {"api_key": None, "expected": False},  # Missing API key
            {"api_key": "wrong_key", "expected": False},  # Wrong API key
            {"jwt_token": None, "expected": False},  # Missing JWT
            {"jwt_token": "invalid.jwt", "expected": False},  # Invalid JWT
        ]
        
        for scenario in scenarios:
            is_allowed = await admin_access.check_admin_resource_access(
                resource_type="bucket",
                resource=scenario.get("resource", mock_resource),
                api_key=scenario.get("api_key", api_key),
                jwt_token=scenario.get("jwt_token", admin_jwt)
            )
            assert is_allowed == scenario["expected"]