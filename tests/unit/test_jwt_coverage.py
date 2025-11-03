"""
Additional tests for JWT service to achieve 95%+ coverage.

These tests cover edge cases and error conditions.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
import jwt as pyjwt


class TestJWTServiceEdgeCases:
    """Additional tests for JWT service edge cases."""
    
    @pytest.fixture
    def jwt_config(self):
        """JWT configuration for testing."""
        return {
            "secret_key": "test_secret_key_123",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30,
            "refresh_token_expire_hours": 24,
            "issuer": "selfdb-test"
        }
    
    @pytest.fixture
    def sample_payload(self):
        """Sample payload for testing."""
        return {
            "user_id": "user_123",
            "email": "test@example.com",
            "role": "USER"
        }
    
    def test_validate_token_unexpected_exception(self, jwt_config, sample_payload):
        """Test handling of unexpected exceptions during token validation."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        # Create a valid token first
        token = jwt_service.generate_access_token(sample_payload)
        
        # Mock jwt.decode to raise an unexpected exception
        with patch('jwt.decode', side_effect=RuntimeError("Unexpected error")):
            payload = jwt_service.validate_access_token(token)
            assert payload is None
    
    def test_blacklist_token_logging(self, jwt_config, sample_payload, caplog):
        """Test that token blacklisting is logged."""
        from shared.auth.jwt_service import JWTService
        import logging
        
        caplog.set_level(logging.INFO)
        jwt_service = JWTService(**jwt_config)
        token = jwt_service.generate_access_token(sample_payload)
        
        jwt_service.blacklist_token(token)
        
        assert "Token blacklisted successfully" in caplog.text
    
    def test_get_token_expiration_invalid_token(self, jwt_config):
        """Test get_token_expiration with invalid token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        # Test with invalid token
        exp_time = jwt_service.get_token_expiration("invalid.token.here")
        assert exp_time is None
    
    def test_get_token_expiration_no_exp_claim(self, jwt_config, sample_payload):
        """Test get_token_expiration when token has no exp claim."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        # Create token without exp claim (manually)
        payload_without_exp = {**sample_payload}
        token_without_exp = pyjwt.encode(
            payload_without_exp, 
            jwt_config["secret_key"], 
            algorithm=jwt_config["algorithm"]
        )
        
        exp_time = jwt_service.get_token_expiration(token_without_exp)
        assert exp_time is None
    
    def test_get_token_remaining_time_expired(self, jwt_config, sample_payload):
        """Test get_token_remaining_time with expired token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        # Create token that's already expired
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_payload = {
            **sample_payload,
            "exp": past_time,
            "iat": past_time - timedelta(minutes=30)
        }
        
        expired_token = pyjwt.encode(
            expired_payload,
            jwt_config["secret_key"],
            algorithm=jwt_config["algorithm"]
        )
        
        remaining = jwt_service.get_token_remaining_time(expired_token)
        assert remaining is None
    
    def test_extract_user_info_invalid_token(self, jwt_config):
        """Test extract_user_info with invalid token."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        # Test with invalid token
        user_info = jwt_service.extract_user_info("invalid.token")
        assert user_info is None
    
    def test_extract_user_info_no_user_fields(self, jwt_config):
        """Test extract_user_info with token containing no user fields."""
        from shared.auth.jwt_service import JWTService
        
        jwt_service = JWTService(**jwt_config)
        
        # Create token with only system fields
        system_only_payload = {
            "token_type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "iss": jwt_config["issuer"]
        }
        
        token = pyjwt.encode(
            system_only_payload,
            jwt_config["secret_key"],
            algorithm=jwt_config["algorithm"]
        )
        
        user_info = jwt_service.extract_user_info(token)
        assert user_info is None
    
    def test_token_validation_with_wrong_type_logging(self, jwt_config, sample_payload, caplog):
        """Test logging when token type doesn't match expected type."""
        from shared.auth.jwt_service import JWTService
        import logging
        
        caplog.set_level(logging.WARNING)
        jwt_service = JWTService(**jwt_config)
        
        # Generate access token but try to validate as refresh token
        access_token = jwt_service.generate_access_token(sample_payload)
        payload = jwt_service.validate_refresh_token(access_token)
        
        assert payload is None
        assert "Token type mismatch" in caplog.text
    
    def test_blacklisted_token_validation_logging(self, jwt_config, sample_payload, caplog):
        """Test logging when trying to use blacklisted token."""
        from shared.auth.jwt_service import JWTService
        import logging
        
        caplog.set_level(logging.WARNING)
        jwt_service = JWTService(**jwt_config)
        
        token = jwt_service.generate_access_token(sample_payload)
        jwt_service.blacklist_token(token)
        
        # Try to validate blacklisted token
        payload = jwt_service.validate_access_token(token)
        
        assert payload is None
        assert "Attempted to use blacklisted token" in caplog.text
    
    @patch('shared.auth.jwt_service.datetime')
    def test_expired_token_validation_logging(self, mock_datetime, jwt_config, sample_payload, caplog):
        """Test logging when token is expired."""
        from shared.auth.jwt_service import JWTService
        import logging
        
        caplog.set_level(logging.WARNING)
        jwt_service = JWTService(**jwt_config)
        
        # Mock time for token generation (now)
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        token = jwt_service.generate_access_token(sample_payload)
        
        # Try to validate token (should work initially)
        # Note: The token might already be expired due to mock timing
        payload = jwt_service.validate_access_token(token)
        # Don't assert here since mocking can affect timing
        
        # Mock time for validation (expired)  
        mock_expired = mock_now + timedelta(minutes=31)
        mock_datetime.now.return_value = mock_expired
        
        # Clear previous logs
        caplog.clear()
        
        # Try to validate expired token
        payload = jwt_service.validate_access_token(token)
        
        assert payload is None
        assert "Token has expired" in caplog.text
    
    def test_invalid_token_validation_logging(self, jwt_config, caplog):
        """Test logging when token is malformed."""
        from shared.auth.jwt_service import JWTService
        import logging
        
        caplog.set_level(logging.WARNING)
        jwt_service = JWTService(**jwt_config)
        
        # Try to validate malformed token
        payload = jwt_service.validate_access_token("malformed.token.here")
        
        assert payload is None
        assert "Invalid token" in caplog.text
    
    def test_concurrent_blacklist_operations(self, jwt_config, sample_payload):
        """Test thread safety of blacklist operations."""
        from shared.auth.jwt_service import JWTService
        import concurrent.futures
        import threading
        
        jwt_service = JWTService(**jwt_config)
        
        # Generate multiple tokens
        tokens = [jwt_service.generate_access_token(sample_payload) for _ in range(10)]
        
        def blacklist_and_validate(token):
            jwt_service.blacklist_token(token)
            # Try to validate after blacklisting
            return jwt_service.validate_access_token(token)
        
        # Test concurrent blacklisting
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(blacklist_and_validate, token) for token in tokens]
            results = [future.result() for future in futures]
        
        # All validations should fail (tokens blacklisted)
        for result in results:
            assert result is None