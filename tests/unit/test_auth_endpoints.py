"""
Unit tests for authentication endpoints.

Tests the auth endpoints: register, login, refresh token operations.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any


class TestAuthEndpoints:
    """Test suite for authentication endpoints."""
    
    @pytest.fixture
    def api_key(self):
        """Valid API key for testing."""
        return "test_api_key_auth"
    
    @pytest.fixture
    def jwt_service(self):
        """JWT service for testing."""
        from shared.auth.jwt_service import JWTService
        return JWTService(
            secret_key="test_auth_secret",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_hours=24 * 7  # 7 days
        )
    
    @pytest.fixture
    def mock_user_store(self):
        """Mock user storage for testing."""
        store = Mock()
        store.get_user_by_email = AsyncMock()
        store.get_user_by_id = AsyncMock()
        store.create_user = AsyncMock()
        store.update_user_last_login = AsyncMock()
        return store
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for registration."""
        return {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "first_name": "John",
            "last_name": "Doe"
        }
    
    @pytest.fixture
    def existing_user(self):
        """Mock existing user object."""
        user = Mock()
        user.id = "user_123"
        user.email = "existing@example.com"
        user.password_hash = "$2b$12$hash_here"  # Mock bcrypt hash
        user.role = "USER"
        user.is_active = True
        user.created_at = datetime.now(timezone.utc)
        user.last_login = None
        return user
    
    @pytest.mark.asyncio
    async def test_register_new_user_success(
        self, api_key, jwt_service, mock_user_store, sample_user_data
    ):
        """Test successful user registration."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Mock that user doesn't exist
        mock_user_store.get_user_by_email.return_value = None
        
        # Mock user creation
        new_user = Mock()
        new_user.id = "new_user_456"
        new_user.email = sample_user_data["email"]
        new_user.role = "USER"
        new_user.is_active = True
        mock_user_store.create_user.return_value = new_user
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.register(
            api_key=api_key,
            **sample_user_data
        )
        
        assert result["success"] is True
        assert result["user"]["email"] == sample_user_data["email"]
        assert result["user"]["role"] == "USER"
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["expires_in"] == 1800  # 30 minutes in seconds
        
        # Verify user store methods were called
        mock_user_store.get_user_by_email.assert_called_once_with(sample_user_data["email"])
        mock_user_store.create_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_already_exists(
        self, api_key, jwt_service, mock_user_store, sample_user_data, existing_user
    ):
        """Test registration when user already exists."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Mock that user already exists
        mock_user_store.get_user_by_email.return_value = existing_user
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.register(
            api_key=api_key,
            **sample_user_data
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "USER_ALREADY_EXISTS"
        assert "email" in result["error"]["message"]
        assert result["error"]["details"]["email"] == sample_user_data["email"]
    
    @pytest.mark.asyncio
    async def test_register_invalid_api_key(
        self, jwt_service, mock_user_store, sample_user_data
    ):
        """Test registration with invalid API key."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key="correct_key",
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.register(
            api_key="wrong_key",
            **sample_user_data
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_API_KEY"
    
    @pytest.mark.asyncio
    async def test_register_missing_required_fields(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test registration with missing required fields."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        # Test missing email (pass empty string)
        result = await auth_endpoints.register(
            api_key=api_key,
            email="",  # Empty email
            password="password123",
            first_name="John",
            last_name="Doe"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "email" in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_register_weak_password(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test registration with weak password."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.register(
            api_key=api_key,
            email="user@example.com",
            password="weak",  # Too short
            first_name="John",
            last_name="Doe"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "WEAK_PASSWORD"
        assert "8 characters" in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_login_success(
        self, api_key, jwt_service, mock_user_store, existing_user
    ):
        """Test successful login."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Mock user exists and password verification
        mock_user_store.get_user_by_email.return_value = existing_user
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        with patch('bcrypt.checkpw', return_value=True):
            result = await auth_endpoints.login(
                api_key=api_key,
                email=existing_user.email,
                password="correct_password"
            )
        
        assert result["success"] is True
        assert result["user"]["id"] == existing_user.id
        assert result["user"]["email"] == existing_user.email
        assert result["user"]["role"] == existing_user.role
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["expires_in"] == 1800  # 30 minutes
        
        # Verify last login was updated
        mock_user_store.update_user_last_login.assert_called_once_with(existing_user.id)
    
    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test login with non-existent user."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Mock user doesn't exist
        mock_user_store.get_user_by_email.return_value = None
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.login(
            api_key=api_key,
            email="nonexistent@example.com",
            password="password123"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_CREDENTIALS"
        assert "email or password" in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self, api_key, jwt_service, mock_user_store, existing_user
    ):
        """Test login with wrong password."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        mock_user_store.get_user_by_email.return_value = existing_user
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        with patch('bcrypt.checkpw', return_value=False):
            result = await auth_endpoints.login(
                api_key=api_key,
                email=existing_user.email,
                password="wrong_password"
            )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_CREDENTIALS"
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test login with inactive user."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        inactive_user = Mock()
        inactive_user.id = "inactive_123"
        inactive_user.email = "inactive@example.com"
        inactive_user.password_hash = "$2b$12$hash_here"
        inactive_user.role = "USER"
        inactive_user.is_active = False  # Inactive user
        
        mock_user_store.get_user_by_email.return_value = inactive_user
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        with patch('bcrypt.checkpw', return_value=True):
            result = await auth_endpoints.login(
                api_key=api_key,
                email=inactive_user.email,
                password="correct_password"
            )
        
        assert result["success"] is False
        assert result["error"]["code"] == "ACCOUNT_INACTIVE"
        assert result["error"]["details"]["user_id"] == inactive_user.id
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self, api_key, jwt_service, mock_user_store, existing_user
    ):
        """Test successful token refresh."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Generate valid refresh token
        user_payload = {
            "user_id": existing_user.id,
            "email": existing_user.email,
            "role": existing_user.role,
            "is_active": existing_user.is_active
        }
        refresh_token = jwt_service.generate_refresh_token(user_payload)
        
        mock_user_store.get_user_by_id.return_value = existing_user
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.refresh_token(
            api_key=api_key,
            refresh_token=refresh_token
        )
        
        assert result["success"] is True
        assert "access_token" in result
        assert "refresh_token" in result  # New refresh token
        assert result["expires_in"] == 1800
        assert result["user"]["id"] == existing_user.id
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test refresh with invalid token."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.refresh_token(
            api_key=api_key,
            refresh_token="invalid.refresh.token"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_REFRESH_TOKEN"
    
    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test refresh when user no longer exists."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Generate token for non-existent user
        user_payload = {
            "user_id": "deleted_user_789",
            "email": "deleted@example.com",
            "role": "USER",
            "is_active": True
        }
        refresh_token = jwt_service.generate_refresh_token(user_payload)
        
        mock_user_store.get_user_by_id.return_value = None  # User doesn't exist
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.refresh_token(
            api_key=api_key,
            refresh_token=refresh_token
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "USER_NOT_FOUND"
        assert result["error"]["details"]["user_id"] == "deleted_user_789"
    
    @pytest.mark.asyncio
    async def test_refresh_token_inactive_user(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test refresh for inactive user."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        inactive_user = Mock()
        inactive_user.id = "inactive_456"
        inactive_user.email = "inactive@example.com"
        inactive_user.role = "USER"
        inactive_user.is_active = False
        
        user_payload = {
            "user_id": inactive_user.id,
            "email": inactive_user.email,
            "role": inactive_user.role,
            "is_active": True  # Token was valid when issued
        }
        refresh_token = jwt_service.generate_refresh_token(user_payload)
        
        mock_user_store.get_user_by_id.return_value = inactive_user
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.refresh_token(
            api_key=api_key,
            refresh_token=refresh_token
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "ACCOUNT_INACTIVE"
    
    @pytest.mark.asyncio
    async def test_logout_success(
        self, api_key, jwt_service, mock_user_store, existing_user
    ):
        """Test successful logout (token blacklisting)."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Generate tokens
        user_payload = {
            "user_id": existing_user.id,
            "email": existing_user.email,
            "role": existing_user.role,
            "is_active": existing_user.is_active
        }
        access_token = jwt_service.generate_access_token(user_payload)
        refresh_token = jwt_service.generate_refresh_token(user_payload)
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.logout(
            api_key=api_key,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        assert result["success"] is True
        assert result["message"] == "Successfully logged out"
        
        # Verify tokens are blacklisted
        assert jwt_service.validate_access_token(access_token) is None
        assert jwt_service.validate_refresh_token(refresh_token) is None
    
    @pytest.mark.asyncio
    async def test_logout_invalid_tokens(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test logout with invalid tokens."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.logout(
            api_key=api_key,
            access_token="invalid.access.token",
            refresh_token="invalid.refresh.token"
        )
        
        # Should still succeed (logout is idempotent)
        assert result["success"] is True
        assert result["message"] == "Successfully logged out"
    
    @pytest.mark.asyncio
    async def test_get_current_user(
        self, api_key, jwt_service, mock_user_store, existing_user
    ):
        """Test getting current user from token."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Generate valid token
        user_payload = {
            "user_id": existing_user.id,
            "email": existing_user.email,
            "role": existing_user.role,
            "is_active": existing_user.is_active
        }
        access_token = jwt_service.generate_access_token(user_payload)
        
        mock_user_store.get_user_by_id.return_value = existing_user
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.get_current_user(
            api_key=api_key,
            access_token=access_token
        )
        
        assert result["success"] is True
        assert result["user"]["id"] == existing_user.id
        assert result["user"]["email"] == existing_user.email
        assert result["user"]["role"] == existing_user.role

    @pytest.mark.asyncio
    async def test_change_password_success(self, api_key, jwt_service, mock_user_store):
        """Test change password flow (user changes own password)."""
        from shared.auth.auth_endpoints import AuthEndpoints

        # Prepare mock user
        user = Mock()
        user.id = "user_change_1"
        user.email = "change@test.com"
        user.hashed_password = "$2b$12$fakehash"
        user.is_active = True

        async def fake_get_user_by_id(uid):
            return user

        mock_user_store.get_user_by_id.side_effect = fake_get_user_by_id
        mock_user_store.update_user_password = AsyncMock(return_value=True)

        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )

        # Simulate correct current password
        with patch('bcrypt.checkpw', return_value=True):
            result = await auth_endpoints.change_password(
                api_key=api_key,
                user_id=user.id,
                current_password="OldPass123!",
                new_password="NewPass123!"
            )

        assert result["success"] is True
        mock_user_store.update_user_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, api_key, jwt_service, mock_user_store):
        """Test change password fails when current password is wrong."""
        from shared.auth.auth_endpoints import AuthEndpoints

        user = Mock()
        user.id = "user_change_2"
        user.email = "change2@test.com"
        user.hashed_password = "$2b$12$fakehash"
        user.is_active = True

        async def fake_get_user_by_id(uid):
            return user

        mock_user_store.get_user_by_id.side_effect = fake_get_user_by_id
        mock_user_store.update_user_password = AsyncMock(return_value=True)

        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )

        # Simulate wrong current password
        with patch('bcrypt.checkpw', return_value=False):
            result = await auth_endpoints.change_password(
                api_key=api_key,
                user_id=user.id,
                current_password="WrongOld",
                new_password="NewPass123!"
            )

        assert result["success"] is False
        assert result["error"]["code"] in ("INVALID_CREDENTIALS", "WEAK_PASSWORD", "VALIDATION_ERROR") or "password" in result.get("error", {}).get("message", "")

    @pytest.mark.asyncio
    async def test_admin_set_user_password_success(self, api_key, jwt_service, mock_user_store):
        """Test admin sets another user's password successfully."""
        from shared.auth.auth_endpoints import AuthEndpoints

        admin_user = Mock()
        admin_user.id = "admin_1"
        admin_user.email = "admin@test.com"
        admin_user.role = "ADMIN"
        admin_user.is_active = True

        target_user = Mock()
        target_user.id = "target_1"
        target_user.email = "target@test.com"
        target_user.is_active = True

        async def fake_get_user_by_id(uid):
            return admin_user if uid == admin_user.id else target_user

        mock_user_store.get_user_by_id.side_effect = fake_get_user_by_id
        mock_user_store.update_user_password = AsyncMock(return_value=True)

        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )

        result = await auth_endpoints.admin_set_user_password(
            api_key=api_key,
            admin_user_id=admin_user.id,
            target_user_id=target_user.id,
            new_password="AdminSet123!"
        )

        assert result["success"] is True
        mock_user_store.update_user_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_set_user_password_forbidden(self, api_key, jwt_service, mock_user_store):
        """Test admin set password is forbidden when caller is not admin."""
        from shared.auth.auth_endpoints import AuthEndpoints

        non_admin = Mock()
        non_admin.id = "user_not_admin"
        non_admin.email = "notadmin@test.com"
        non_admin.role = "USER"
        non_admin.is_active = True

        target_user = Mock()
        target_user.id = "target_2"
        target_user.email = "target2@test.com"
        target_user.is_active = True

        async def fake_get_user_by_id(uid):
            return non_admin if uid == non_admin.id else target_user

        mock_user_store.get_user_by_id.side_effect = fake_get_user_by_id
        mock_user_store.update_user_password = AsyncMock(return_value=True)

        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )

        result = await auth_endpoints.admin_set_user_password(
            api_key=api_key,
            admin_user_id=non_admin.id,
            target_user_id=target_user.id,
            new_password="ShouldNotWork123!"
        )

        assert result["success"] is False
    
    @pytest.mark.asyncio
    async def test_auth_endpoint_rate_limiting(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test rate limiting for auth endpoints."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Mock user with proper password hash
        rate_limit_user = Mock()
        rate_limit_user.id = "rate_limit_user"
        rate_limit_user.email = "test@example.com"
        rate_limit_user.password_hash = "$2b$12$fake_hash"  # Mock bcrypt hash
        rate_limit_user.role = "USER"
        rate_limit_user.is_active = True
        
        mock_user_store.get_user_by_email.return_value = rate_limit_user
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store,
            enable_rate_limiting=True,
            max_attempts_per_minute=3
        )
        
        # Simulate rapid login attempts
        with patch('bcrypt.checkpw', return_value=False):  # Wrong password
            for i in range(4):  # One more than the limit
                result = await auth_endpoints.login(
                    api_key=api_key,
                    email="test@example.com",
                    password="password"
                )
                
                if i < 3:
                    # First 3 attempts should be processed (but fail due to invalid creds)
                    assert result["error"]["code"] == "INVALID_CREDENTIALS"
                else:
                    # 4th attempt should be rate limited
                    assert result["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    
    def test_auth_endpoints_initialization(self, api_key, jwt_service, mock_user_store):
        """Test AuthEndpoints initialization."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store,
            enable_rate_limiting=True,
            max_attempts_per_minute=5
        )
        
        assert auth_endpoints.api_key == api_key
        assert auth_endpoints.jwt_service == jwt_service
        assert auth_endpoints.user_store == mock_user_store
        assert auth_endpoints.enable_rate_limiting is True
        assert auth_endpoints.max_attempts_per_minute == 5
    
    def test_auth_endpoints_missing_jwt_service_raises_error(self, api_key, mock_user_store):
        """Test that AuthEndpoints requires a JWT service."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        with pytest.raises(ValueError, match="JWT service must be provided"):
            AuthEndpoints(api_key=api_key, jwt_service=None, user_store=mock_user_store)