"""
Additional tests for auth endpoints to achieve 95%+ coverage.

These tests cover edge cases and error conditions not covered by main tests.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone


class TestAuthEndpointsEdgeCases:
    """Additional tests for auth endpoints edge cases."""
    
    @pytest.fixture
    def jwt_service(self):
        """JWT service for testing."""
        from shared.auth.jwt_service import JWTService
        return JWTService(
            secret_key="test_auth_secret",
            algorithm="HS256", 
            access_token_expire_minutes=30,
            refresh_token_expire_hours=24 * 7
        )
    
    @pytest.fixture
    def api_key(self):
        """Valid API key for testing."""
        return "test_api_key_auth"
    
    @pytest.fixture
    def mock_user_store(self):
        """Mock user storage for testing."""
        from unittest.mock import AsyncMock
        store = Mock()
        store.get_user_by_email = AsyncMock()
        store.get_user_by_id = AsyncMock()
        store.create_user = AsyncMock()
        store.update_user_last_login = AsyncMock()
        return store
    
    @pytest.mark.asyncio
    async def test_register_invalid_email_format(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test registration with invalid email format."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        mock_user_store.get_user_by_email.return_value = None
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.register(
            api_key=api_key,
            email="invalid-email",  # Invalid format
            password="password123",
            first_name="John", 
            last_name="Doe"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_EMAIL"
        assert "Invalid email format" in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_register_missing_multiple_fields(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test registration missing multiple required fields."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.register(
            api_key=api_key,
            email="",  # Missing email
            password="",  # Missing password
            first_name="John",
            last_name=""  # Missing last name
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert len(result["error"]["details"]["missing_fields"]) == 3
        assert "email" in result["error"]["details"]["missing_fields"]
        assert "password" in result["error"]["details"]["missing_fields"]
        assert "last_name" in result["error"]["details"]["missing_fields"]
    
    def test_auth_endpoints_missing_user_store_raises_error(self, api_key, jwt_service):
        """Test that AuthEndpoints requires a user store."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        with pytest.raises(ValueError, match="User store must be provided"):
            AuthEndpoints(api_key=api_key, jwt_service=jwt_service, user_store=None)
    
    def test_validate_email_edge_cases(self, api_key, jwt_service, mock_user_store):
        """Test email validation with edge cases."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        # Test valid emails
        assert auth_endpoints._validate_email("user@example.com") is True
        assert auth_endpoints._validate_email("test+tag@domain.co.uk") is True
        assert auth_endpoints._validate_email("user.name@example-domain.com") is True
        
        # Test invalid emails  
        assert auth_endpoints._validate_email("invalid-email") is False
        assert auth_endpoints._validate_email("@example.com") is False
        assert auth_endpoints._validate_email("user@") is False
        assert auth_endpoints._validate_email("user@domain") is False
        assert auth_endpoints._validate_email("") is False
    
    def test_password_strength_validation(self, api_key, jwt_service, mock_user_store):
        """Test password strength validation."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        # Test valid passwords
        assert auth_endpoints._validate_password_strength("password123") is True
        assert auth_endpoints._validate_password_strength("verylongpassword") is True
        
        # Test invalid passwords
        assert auth_endpoints._validate_password_strength("short") is False
        assert auth_endpoints._validate_password_strength("1234567") is False  # 7 chars
        assert auth_endpoints._validate_password_strength("") is False
    
    def test_hash_and_verify_password(self, api_key, jwt_service, mock_user_store):
        """Test password hashing and verification."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        password = "testpassword123"
        hashed = auth_endpoints._hash_password(password)
        
        # Hash should be different from password
        assert hashed != password
        assert hashed.startswith("$2b$")
        
        # Verification should work
        assert auth_endpoints._verify_password(password, hashed) is True
        assert auth_endpoints._verify_password("wrongpassword", hashed) is False
    
    def test_serialize_user_with_optional_fields(self, api_key, jwt_service, mock_user_store):
        """Test user serialization with optional fields."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        # Create user with minimal fields - configure the mock to not have optional attributes
        minimal_user = Mock(spec=['id', 'email', 'role', 'is_active'])
        minimal_user.id = "user_123"
        minimal_user.email = "user@example.com"
        minimal_user.role = "USER"
        minimal_user.is_active = True
        
        serialized = auth_endpoints._serialize_user(minimal_user)
        
        assert serialized["id"] == "user_123"
        assert serialized["email"] == "user@example.com"
        assert serialized["role"] == "USER"
        assert serialized["is_active"] is True
        assert serialized["first_name"] is None
        assert serialized["last_name"] is None
        assert serialized["created_at"] is None
        assert serialized["updated_at"] is None
        assert serialized["last_login_at"] is None
        
        # Create user with all fields
        full_user = Mock()
        full_user.id = "user_456"
        full_user.email = "full@example.com"
        full_user.role = "ADMIN"
        full_user.is_active = True
        full_user.first_name = "John"
        full_user.last_name = "Doe"
        full_user.created_at = datetime.now(timezone.utc)
        full_user.updated_at = datetime.now(timezone.utc)
        full_user.last_login_at = datetime.now(timezone.utc)

        serialized = auth_endpoints._serialize_user(full_user)

        assert serialized["first_name"] == "John"
        assert serialized["last_name"] == "Doe"
        assert serialized["created_at"] is not None
        assert serialized["updated_at"] is not None
        assert serialized["last_login_at"] is not None
    
    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test get_current_user when user no longer exists."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        # Generate valid token
        user_payload = {
            "user_id": "deleted_user_123",
            "email": "deleted@example.com",
            "role": "USER",
            "is_active": True
        }
        access_token = jwt_service.generate_access_token(user_payload)
        
        # Mock user not found
        mock_user_store.get_user_by_id.return_value = None
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.get_current_user(
            api_key=api_key,
            access_token=access_token
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "USER_NOT_FOUND"
        assert result["error"]["details"]["user_id"] == "deleted_user_123"
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test get_current_user with invalid token."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.get_current_user(
            api_key=api_key,
            access_token="invalid.access.token"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_ACCESS_TOKEN"
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_api_key(
        self, jwt_service, mock_user_store
    ):
        """Test get_current_user with invalid API key."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key="correct_key",
            jwt_service=jwt_service,
            user_store=mock_user_store
        )
        
        result = await auth_endpoints.get_current_user(
            api_key="wrong_key",
            access_token="some.valid.token"
        )
        
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_API_KEY"
    
    def test_rate_limiting_disabled_by_default(self, api_key, jwt_service, mock_user_store):
        """Test that rate limiting is disabled by default."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store
            # enable_rate_limiting not specified - should default to False
        )
        
        # Rate limiting check should always return False
        assert auth_endpoints._check_rate_limit("any_key") is False
        assert auth_endpoints._check_rate_limit("another_key") is False
    
    @pytest.mark.asyncio
    async def test_register_rate_limiting(
        self, api_key, jwt_service, mock_user_store
    ):
        """Test rate limiting for registration endpoint."""
        from shared.auth.auth_endpoints import AuthEndpoints
        
        auth_endpoints = AuthEndpoints(
            api_key=api_key,
            jwt_service=jwt_service,
            user_store=mock_user_store,
            enable_rate_limiting=True,
            max_attempts_per_minute=2
        )
        
        registration_data = {
            "email": "ratelimit@example.com",
            "password": "password123",
            "first_name": "Rate",
            "last_name": "Limited"
        }
        
        # First 2 attempts should be processed
        for i in range(3):
            result = await auth_endpoints.register(
                api_key=api_key,
                **registration_data
            )
            
            if i < 2:
                # Should be processed (may fail for other reasons)
                assert result["error"]["code"] != "RATE_LIMIT_EXCEEDED"
            else:
                # 3rd attempt should be rate limited
                assert result["error"]["code"] == "RATE_LIMIT_EXCEEDED"
                assert "Too many registration attempts" in result["error"]["message"]