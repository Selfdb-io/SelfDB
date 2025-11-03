"""
JWT token service for SelfDB authentication.

Handles JWT token generation, validation, refresh, and blacklisting.
"""

import os
import jwt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Set
from threading import Lock


logger = logging.getLogger(__name__)


class JWTService:
    """Service for JWT token operations."""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_hours: int = 24 * 7,  # 7 days
        issuer: str = "selfdb"
    ):
        """
        Initialize JWT service.
        
        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token expiration in minutes
            refresh_token_expire_hours: Refresh token expiration in hours
            issuer: JWT issuer claim
        """
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY must be configured")
        
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_hours = refresh_token_expire_hours
        self.issuer = issuer
        
        # Thread-safe blacklist for tokens
        self._blacklisted_tokens: Set[str] = set()
        self._blacklist_lock = Lock()
    
    @classmethod
    def from_environment(cls) -> 'JWTService':
        """
        Create JWT service from environment variables.
        
        Returns:
            JWTService instance configured from environment
        """
        secret_key = os.environ.get("JWT_SECRET_KEY", "")
        algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
        access_expire = int(os.environ.get("JWT_ACCESS_EXPIRE_MINUTES", "30"))
        refresh_expire = int(os.environ.get("JWT_REFRESH_EXPIRE_HOURS", str(24 * 7)))
        issuer = os.environ.get("JWT_ISSUER", "selfdb")
        
        return cls(
            secret_key=secret_key,
            algorithm=algorithm,
            access_token_expire_minutes=access_expire,
            refresh_token_expire_hours=refresh_expire,
            issuer=issuer
        )
    
    def generate_access_token(self, payload: Dict[str, Any]) -> str:
        """
        Generate an access token.
        
        Args:
            payload: User data to include in token
            
        Returns:
            JWT access token string
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=self.access_token_expire_minutes)
        
        token_payload = {
            **payload,
            "token_type": "access",
            "iat": now,
            "exp": exp,
            "iss": self.issuer
        }
        
        return jwt.encode(token_payload, self.secret_key, algorithm=self.algorithm)
    
    def generate_refresh_token(self, payload: Dict[str, Any]) -> str:
        """
        Generate a refresh token.
        
        Args:
            payload: User data to include in token
            
        Returns:
            JWT refresh token string
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(hours=self.refresh_token_expire_hours)
        
        token_payload = {
            **payload,
            "token_type": "refresh",
            "iat": now,
            "exp": exp,
            "iss": self.issuer
        }
        
        return jwt.encode(token_payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate an access token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Token payload if valid, None otherwise
        """
        return self._validate_token(token, expected_type="access")
    
    def validate_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a refresh token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Token payload if valid, None otherwise
        """
        return self._validate_token(token, expected_type="refresh")
    
    def _validate_token(self, token: str, expected_type: str) -> Optional[Dict[str, Any]]:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token to validate
            expected_type: Expected token type (access/refresh)
            
        Returns:
            Token payload if valid, None otherwise
        """
        if not token:
            return None
        
        # Check if token is blacklisted
        with self._blacklist_lock:
            if token in self._blacklisted_tokens:
                logger.warning("Attempted to use blacklisted token")
                return None
        
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer
            )
            
            # Check token type
            if payload.get("token_type") != expected_type:
                logger.warning(f"Token type mismatch: expected {expected_type}, got {payload.get('token_type')}")
                return None
            
            return payload
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token if refresh token is valid, None otherwise
        """
        payload = self.validate_refresh_token(refresh_token)
        if not payload:
            return None
        
        # Create new access token with same user data
        user_payload = {
            key: value for key, value in payload.items()
            if key not in ["token_type", "iat", "exp", "iss"]
        }
        
        return self.generate_access_token(user_payload)
    
    def blacklist_token(self, token: str) -> None:
        """
        Blacklist a token (logout functionality).
        
        Args:
            token: Token to blacklist
        """
        with self._blacklist_lock:
            self._blacklisted_tokens.add(token)
        
        logger.info("Token blacklisted successfully")
    
    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Get token expiration time.
        
        Args:
            token: JWT token
            
        Returns:
            Expiration datetime if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Don't verify expiration for this check
            )
            
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_token_remaining_time(self, token: str) -> Optional[timedelta]:
        """
        Get remaining time for token.
        
        Args:
            token: JWT token
            
        Returns:
            Remaining time as timedelta if token is valid, None otherwise
        """
        exp_time = self.get_token_expiration(token)
        if not exp_time:
            return None
        
        now = datetime.now(timezone.utc)
        remaining = exp_time - now
        
        # Return None if token is already expired
        if remaining.total_seconds() <= 0:
            return None
        
        return remaining
    
    def extract_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Extract user information from token without full validation.
        
        Args:
            token: JWT token
            
        Returns:
            User information if token is decodable, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                options={"verify_exp": False}
            )
            
            # Extract only user-related fields
            user_fields = ["user_id", "email", "role", "is_active"]
            user_info = {
                field: payload.get(field)
                for field in user_fields
                if field in payload
            }
            
            # Include custom fields if present
            for key, value in payload.items():
                if key not in ["token_type", "iat", "exp", "iss"] + user_fields:
                    user_info[key] = value
            
            return user_info if user_info else None
        
        except jwt.InvalidTokenError:
            return None