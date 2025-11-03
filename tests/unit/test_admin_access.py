"""
Unit tests for admin-only operations requiring ADMIN role.

Tests operations that are restricted to users with ADMIN role only.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any


class TestAdminAccess:
    """Test suite for admin-only operations."""
    
    @pytest.fixture
    def api_key(self):
        """Valid API key for testing."""
        return "test_api_key_admin"
    
    @pytest.fixture
    def jwt_service(self):
        """JWT service for testing."""
        from shared.auth.jwt_service import JWTService
        return JWTService(
            secret_key="test_admin_secret",
            algorithm="HS256",
            access_token_expire_minutes=30
        )
    
    @pytest.fixture
    def admin_user_payload(self):
        """Sample admin user data."""
        return {
            "user_id": "admin_123",
            "email": "admin@example.com",
            "role": "ADMIN",
            "is_active": True
        }
    
    @pytest.fixture
    def regular_user_payload(self):
        """Sample regular user data."""
        return {
            "user_id": "user_456",
            "email": "user@example.com", 
            "role": "USER",
            "is_active": True
        }
    
    @pytest.mark.asyncio
    async def test_admin_can_list_all_users(self, api_key, jwt_service, admin_user_payload):
        """Test that admin users can list all users."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await admin_access.check_admin_operation(
            operation="list_users",
            api_key=api_key,
            jwt_token=admin_jwt
        )
        
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_regular_user_cannot_list_all_users(self, api_key, jwt_service, regular_user_payload):
        """Test that regular users cannot list all users."""
        from shared.auth.admin_access import AdminAccessControl
        
        user_jwt = jwt_service.generate_access_token(regular_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await admin_access.check_admin_operation(
            operation="list_users",
            api_key=api_key,
            jwt_token=user_jwt
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_can_delete_any_user(self, api_key, jwt_service, admin_user_payload):
        """Test that admin users can delete any user."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await admin_access.check_admin_operation(
            operation="delete_user",
            api_key=api_key,
            jwt_token=admin_jwt,
            target_user_id="any_user_123"
        )
        
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_regular_user_cannot_delete_users(self, api_key, jwt_service, regular_user_payload):
        """Test that regular users cannot delete other users."""
        from shared.auth.admin_access import AdminAccessControl
        
        user_jwt = jwt_service.generate_access_token(regular_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await admin_access.check_admin_operation(
            operation="delete_user",
            api_key=api_key,
            jwt_token=user_jwt,
            target_user_id="other_user_789"
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_can_manage_system_settings(self, api_key, jwt_service, admin_user_payload):
        """Test that admin users can manage system settings."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        admin_operations = [
            "update_system_config",
            "view_system_logs",
            "manage_api_keys",
            "backup_database",
            "restore_database"
        ]
        
        for operation in admin_operations:
            is_allowed = await admin_access.check_admin_operation(
                operation=operation,
                api_key=api_key,
                jwt_token=admin_jwt
            )
            assert is_allowed is True, f"Admin should be allowed to perform {operation}"
    
    @pytest.mark.asyncio
    async def test_regular_user_cannot_manage_system_settings(self, api_key, jwt_service, regular_user_payload):
        """Test that regular users cannot manage system settings."""
        from shared.auth.admin_access import AdminAccessControl
        
        user_jwt = jwt_service.generate_access_token(regular_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        admin_operations = [
            "update_system_config",
            "view_system_logs",
            "manage_api_keys",
            "backup_database",
            "restore_database"
        ]
        
        for operation in admin_operations:
            is_allowed = await admin_access.check_admin_operation(
                operation=operation,
                api_key=api_key,
                jwt_token=user_jwt
            )
            assert is_allowed is False, f"Regular user should not be allowed to perform {operation}"
    
    @pytest.mark.asyncio
    async def test_admin_can_access_any_user_data(self, api_key, jwt_service, admin_user_payload):
        """Test that admin users can access any user's private data."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        # Create user resource owned by different user
        user_resource = Mock()
        user_resource.id = "resource_456"
        user_resource.owner_id = "different_user_789"
        user_resource.public = False
        
        is_allowed = await admin_access.check_admin_resource_access(
            resource_type="bucket",
            resource=user_resource,
            api_key=api_key,
            jwt_token=admin_jwt
        )
        
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_admin_operation_requires_valid_api_key(self, jwt_service, admin_user_payload):
        """Test that admin operations require valid API key."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        admin_access = AdminAccessControl(
            api_key="correct_key",
            jwt_service=jwt_service
        )
        
        # Test with wrong API key
        is_allowed = await admin_access.check_admin_operation(
            operation="list_users",
            api_key="wrong_key",
            jwt_token=admin_jwt
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_operation_requires_valid_jwt(self, api_key, jwt_service):
        """Test that admin operations require valid JWT."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        # Test with invalid JWT
        is_allowed = await admin_access.check_admin_operation(
            operation="list_users",
            api_key=api_key,
            jwt_token="invalid.jwt.token"
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_inactive_admin_denied_access(self, api_key, jwt_service):
        """Test that inactive admin users are denied access."""
        from shared.auth.admin_access import AdminAccessControl
        
        inactive_admin_payload = {
            "user_id": "inactive_admin_123",
            "email": "inactive_admin@example.com",
            "role": "ADMIN",
            "is_active": False  # Admin is inactive
        }
        
        admin_jwt = jwt_service.generate_access_token(inactive_admin_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await admin_access.check_admin_operation(
            operation="list_users",
            api_key=api_key,
            jwt_token=admin_jwt
        )
        
        assert is_allowed is False
    
    @pytest.mark.asyncio
    async def test_admin_can_impersonate_users(self, api_key, jwt_service, admin_user_payload):
        """Test that admin users can impersonate other users."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await admin_access.check_admin_operation(
            operation="impersonate_user",
            api_key=api_key,
            jwt_token=admin_jwt,
            target_user_id="target_user_123"
        )
        
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_admin_access_error_responses(self, api_key, jwt_service, regular_user_payload):
        """Test error responses for admin access failures."""
        from shared.auth.admin_access import AdminAccessControl
        
        user_jwt = jwt_service.generate_access_token(regular_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        # Test insufficient privileges error
        error = await admin_access.get_admin_access_error(
            operation="delete_user",
            api_key=api_key,
            jwt_token=user_jwt
        )
        
        assert error["code"] == "INSUFFICIENT_PRIVILEGES"
        assert "ADMIN role required" in error["message"]
        assert error["details"]["user_role"] == "USER"
        assert error["details"]["operation"] == "delete_user"
    
    @pytest.mark.asyncio
    async def test_admin_access_logging(
        self, api_key, jwt_service, admin_user_payload, caplog
    ):
        """Test that admin operations are logged."""
        from shared.auth.admin_access import AdminAccessControl
        import logging
        
        caplog.set_level(logging.INFO)
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        await admin_access.check_admin_operation(
            operation="list_users",
            api_key=api_key,
            jwt_token=admin_jwt
        )
        
        assert "Admin operation granted" in caplog.text
        assert "list_users" in caplog.text
        assert admin_user_payload["user_id"] in caplog.text
    
    @pytest.mark.asyncio
    async def test_admin_can_manage_cors_origins(self, api_key, jwt_service, admin_user_payload):
        """Test that admin users can manage CORS origins."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        cors_operations = [
            "list_cors_origins",
            "add_cors_origin",
            "remove_cors_origin"
        ]
        
        for operation in cors_operations:
            is_allowed = await admin_access.check_admin_operation(
                operation=operation,
                api_key=api_key,
                jwt_token=admin_jwt
            )
            assert is_allowed is True, f"Admin should be allowed to perform {operation}"
    
    @pytest.mark.asyncio
    async def test_admin_can_view_function_logs(self, api_key, jwt_service, admin_user_payload):
        """Test that admin users can view any function's logs."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await admin_access.check_admin_operation(
            operation="view_function_logs",
            api_key=api_key,
            jwt_token=admin_jwt,
            function_id="any_function_123"
        )
        
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_regular_user_cannot_view_other_function_logs(
        self, api_key, jwt_service, regular_user_payload
    ):
        """Test that regular users cannot view other users' function logs."""
        from shared.auth.admin_access import AdminAccessControl
        
        user_jwt = jwt_service.generate_access_token(regular_user_payload)
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service
        )
        
        is_allowed = await admin_access.check_admin_operation(
            operation="view_function_logs",
            api_key=api_key,
            jwt_token=user_jwt,
            function_id="other_user_function_456"
        )
        
        assert is_allowed is False
    
    def test_admin_access_control_initialization(self, api_key, jwt_service):
        """Test AdminAccessControl initialization."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service,
            enable_logging=True,
            strict_admin_check=True
        )
        
        assert admin_access.api_key == api_key
        assert admin_access.jwt_service == jwt_service
        assert admin_access.enable_logging is True
        assert admin_access.strict_admin_check is True
    
    def test_admin_access_control_missing_jwt_service_raises_error(self, api_key):
        """Test that AdminAccessControl requires a JWT service."""
        from shared.auth.admin_access import AdminAccessControl
        
        with pytest.raises(ValueError, match="JWT service must be provided"):
            AdminAccessControl(api_key=api_key, jwt_service=None)
    
    @pytest.mark.asyncio
    async def test_admin_operations_list_is_configurable(self, api_key, jwt_service, admin_user_payload):
        """Test that admin operations list is configurable."""
        from shared.auth.admin_access import AdminAccessControl
        
        admin_jwt = jwt_service.generate_access_token(admin_user_payload)
        
        # Custom admin operations
        custom_admin_ops = [
            "custom_operation_1",
            "custom_operation_2",
            "special_admin_task"
        ]
        
        admin_access = AdminAccessControl(
            api_key=api_key,
            jwt_service=jwt_service,
            admin_operations=custom_admin_ops
        )
        
        # Test custom operations
        for operation in custom_admin_ops:
            is_allowed = await admin_access.check_admin_operation(
                operation=operation,
                api_key=api_key,
                jwt_token=admin_jwt
            )
            assert is_allowed is True, f"Admin should be allowed to perform custom {operation}"
        
        # Test non-admin operation
        is_allowed = await admin_access.check_admin_operation(
            operation="non_admin_operation",
            api_key=api_key,
            jwt_token=admin_jwt
        )
        assert is_allowed is False, "Non-admin operation should be denied even for admin"