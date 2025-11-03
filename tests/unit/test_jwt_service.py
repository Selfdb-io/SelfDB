"""
Unit tests for JWT token generation and validation.

Tests JWT token lifecycle: generation, validation, refresh, and expiration.
Following TDD methodology - tests written before implementation.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
import time
from typing import Optional, Dict, Any


class TestJWTService:
    """Test suite for JWT token service."""
    
    @pytest.fixture
    def jwt_config(self):
        """JWT configuration for testing."""
        return {
            "secret_key": "test_jwt_secret_key_12345",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30,
            "refresh_token_expire_hours": 24 * 7,  # 7 days
            "issuer": "selfdb-test"
        }
    
    @pytest.fixture
    def sample_user_payload(self):
        """Sample user data for JWT payload."""
        return {
            "user_id": "user_123",
            "email": "test@example.com",
            "role": "USER",
            "is_active": True
        }
    
    @pytest.fixture
    def sample_admin_payload(self):
        """Sample admin user data for JWT payload."""
        return {
            "user_id": "admin_456",
            "email": "admin@example.com", 
            "role": "ADMIN",
            "is_active": True
        }
    
    def test_jwt_service_initialization(self, jwt_config):
        """Test JWT service initialization with configuration."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(
            secret_key=jwt_config["secret_key"],
            algorithm=jwt_config["algorithm"],
            access_token_expire_minutes=jwt_config["access_token_expire_minutes"],
            refresh_token_expire_hours=jwt_config["refresh_token_expire_hours"],
            issuer=jwt_config["issuer"]
        )
        
        assert jwt_service.secret_key == jwt_config["secret_key"]
        assert jwt_service.algorithm == jwt_config["algorithm"]
        assert jwt_service.access_token_expire_minutes == 30
        assert jwt_service.refresh_token_expire_hours == 24 * 7
        assert jwt_service.issuer == "selfdb-test"
    
    def test_jwt_service_from_environment(self, monkeypatch):
        """Test JWT service initialization from environment variables."""
        from shared.auth.jwt_service import JWTService
        
        monkeypatch.setenv("JWT_SECRET_KEY", "env_secret")
        monkeypatch.setenv("JWT_ALGORITHM", "HS512")
        monkeypatch.setenv("JWT_ACCESS_EXPIRE_MINUTES", "60")
        monkeypatch.setenv("JWT_REFRESH_EXPIRE_HOURS", "48")
        
        jwt_service = JWTService.from_environment()
        
        assert jwt_service.secret_key == "env_secret"
        assert jwt_service.algorithm == "HS512"
        assert jwt_service.access_token_expire_minutes == 60
        assert jwt_service.refresh_token_expire_hours == 48
    
    def test_generate_access_token(self, jwt_config, sample_user_payload):
        """Test access token generation."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_user_payload)
        
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts separated by dots
        assert token.count('.') == 2
    
    def test_generate_refresh_token(self, jwt_config, sample_user_payload):
        """Test refresh token generation."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_refresh_token(sample_user_payload)
        
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts separated by dots
        assert token.count('.') == 2
    
    def test_validate_access_token_valid(self, jwt_config, sample_user_payload):
        """Test validation of valid access token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_user_payload)
        
        payload = jwt_service.validate_access_token(token)
        
        assert payload is not None
        assert payload["user_id"] == sample_user_payload["user_id"]
        assert payload["email"] == sample_user_payload["email"]
        assert payload["role"] == sample_user_payload["role"]
        assert payload["token_type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "iss" in payload
    
    def test_validate_refresh_token_valid(self, jwt_config, sample_user_payload):
        """Test validation of valid refresh token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_refresh_token(sample_user_payload)
        
        payload = jwt_service.validate_refresh_token(token)
        
        assert payload is not None
        assert payload["user_id"] == sample_user_payload["user_id"]
        assert payload["token_type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_validate_token_invalid_signature(self, jwt_config, sample_user_payload):
        """Test validation of token with invalid signature."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_user_payload)
        
        # Corrupt the token signature
        corrupted_token = token[:-5] + "wrong"
        
        payload = jwt_service.validate_access_token(corrupted_token)
        assert payload is None
    
    def test_validate_token_malformed(self, jwt_config):
        """Test validation of malformed token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        # Test various malformed tokens
        malformed_tokens = [
            "not.a.jwt",
            "too.few.parts",
            "too.many.parts.here.error",
            "",
            "invalid_token",
            None
        ]
        
        for bad_token in malformed_tokens:
            payload = jwt_service.validate_access_token(bad_token)
            assert payload is None, f"Token {bad_token} should be invalid"
    
    @patch('shared.auth.jwt_service.datetime')
    def test_validate_token_expired(self, mock_datetime, jwt_config, sample_user_payload):
        """Test validation of expired token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        # Mock time for token generation (now)
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.utcnow.return_value = mock_now
        
        token = jwt_service.generate_access_token(sample_user_payload)
        
        # Mock time for validation (31 minutes later - expired)
        mock_expired = mock_now + timedelta(minutes=31)
        mock_datetime.now.return_value = mock_expired
        mock_datetime.utcnow.return_value = mock_expired
        
        payload = jwt_service.validate_access_token(token)
        assert payload is None
    
    def test_refresh_access_token_valid_refresh(self, jwt_config, sample_user_payload):
        """Test refreshing access token with valid refresh token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        refresh_token = jwt_service.generate_refresh_token(sample_user_payload)
        
        new_access_token = jwt_service.refresh_access_token(refresh_token)
        
        assert new_access_token is not None
        assert isinstance(new_access_token, str)
        
        # Validate the new access token
        payload = jwt_service.validate_access_token(new_access_token)
        assert payload is not None
        assert payload["user_id"] == sample_user_payload["user_id"]
        assert payload["token_type"] == "access"
    
    def test_refresh_access_token_invalid_refresh(self, jwt_config):
        """Test refreshing access token with invalid refresh token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        # Try to refresh with invalid tokens
        invalid_tokens = ["invalid", None, "wrong.token.here"]
        
        for invalid_token in invalid_tokens:
            new_token = jwt_service.refresh_access_token(invalid_token)
            assert new_token is None
    
    def test_refresh_access_token_with_access_token(self, jwt_config, sample_user_payload):
        """Test that access tokens cannot be used to refresh."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        access_token = jwt_service.generate_access_token(sample_user_payload)
        
        # Should not work - access token used for refresh
        new_token = jwt_service.refresh_access_token(access_token)
        assert new_token is None
    
    def test_token_payload_includes_required_claims(self, jwt_config, sample_user_payload):
        """Test that tokens include required standard claims."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_user_payload)
        payload = jwt_service.validate_access_token(token)
        
        # Check required claims
        assert "exp" in payload  # Expiration time
        assert "iat" in payload  # Issued at
        assert "iss" in payload  # Issuer
        assert payload["iss"] == jwt_config["issuer"]
        
        # Check token type
        assert "token_type" in payload
        assert payload["token_type"] == "access"
    
    def test_admin_token_generation(self, jwt_config, sample_admin_payload):
        """Test JWT generation for admin users."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_admin_payload)
        payload = jwt_service.validate_access_token(token)
        
        assert payload["role"] == "ADMIN"
        assert payload["user_id"] == sample_admin_payload["user_id"]
    
    def test_token_blacklisting(self, jwt_config, sample_user_payload):
        """Test JWT token blacklisting functionality."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_user_payload)
        
        # Token should be valid initially
        payload = jwt_service.validate_access_token(token)
        assert payload is not None
        
        # Blacklist the token
        jwt_service.blacklist_token(token)
        
        # Token should now be invalid
        payload = jwt_service.validate_access_token(token)
        assert payload is None
    
    def test_get_token_expiration_time(self, jwt_config, sample_user_payload):
        """Test getting token expiration time."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_user_payload)
        
        exp_time = jwt_service.get_token_expiration(token)
        assert exp_time is not None
        assert isinstance(exp_time, datetime)
        
        # Should be roughly 30 minutes from now
        now = datetime.now(timezone.utc)
        expected_exp = now + timedelta(minutes=30)
        time_diff = abs((exp_time - expected_exp).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance
    
    def test_token_remaining_time(self, jwt_config, sample_user_payload):
        """Test getting remaining time for token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_user_payload)
        
        remaining = jwt_service.get_token_remaining_time(token)
        assert remaining is not None
        assert isinstance(remaining, timedelta)
        
        # Should be roughly 30 minutes
        assert 25 * 60 < remaining.total_seconds() < 31 * 60
    
    def test_extract_user_info_from_token(self, jwt_config, sample_user_payload):
        """Test extracting user information from token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_user_payload)
        
        user_info = jwt_service.extract_user_info(token)
        
        assert user_info is not None
        assert user_info["user_id"] == sample_user_payload["user_id"]
        assert user_info["email"] == sample_user_payload["email"]
        assert user_info["role"] == sample_user_payload["role"]
        assert user_info["is_active"] == sample_user_payload["is_active"]
    
    def test_token_generation_with_custom_claims(self, jwt_config):
        """Test token generation with custom claims."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        custom_payload = {
            "user_id": "user_789",
            "email": "custom@example.com",
            "role": "USER",
            "custom_field": "custom_value",
            "permissions": ["read", "write"],
            "tenant_id": "tenant_123"
        }
        
        token = jwt_service.generate_access_token(custom_payload)
        payload = jwt_service.validate_access_token(token)
        
        assert payload["custom_field"] == "custom_value"
        assert payload["permissions"] == ["read", "write"]
        assert payload["tenant_id"] == "tenant_123"
    
    def test_jwt_service_missing_secret_key_raises_error(self):
        """Test that JWT service requires a secret key."""
        from shared.auth.jwt_service import JWTService
        
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be configured"):
            JWTService(secret_key="")
        
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be configured"):
            JWTService(secret_key=None)
    
    def test_concurrent_token_validation(self, jwt_config, sample_user_payload):
        """Test that token validation is thread-safe."""
        from shared.auth.jwt_service import JWTService
        import concurrent.futures
        
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_user_payload)
        
        def validate_token():
            return jwt_service.validate_access_token(token)
        
        # Test concurrent validation
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(validate_token) for _ in range(10)]
            results = [future.result() for future in futures]
        
        # All validations should succeed
        for result in results:
            assert result is not None
            assert result["user_id"] == sample_user_payload["user_id"]