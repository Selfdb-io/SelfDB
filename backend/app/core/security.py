from datetime import datetime, timedelta
from typing import Any, Union, Optional
import secrets

from jose import jwt
from passlib.context import CryptContext

from .config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: The subject of the token, typically the user's email or ID.
        expires_delta: Optional expiration time delta. If not provided, uses the default from settings.
        
    Returns:
        The encoded JWT token as a string.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: Union[str, Any]) -> tuple[str, datetime]:
    """
    Create a refresh token for a user.
    
    Args:
        user_id: The user ID to associate with the refresh token.
        
    Returns:
        A tuple containing the refresh token string and its expiration datetime.
    """
    # Generate a secure random token
    token = secrets.token_urlsafe(64)
    
    # Set expiration time
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    return token, expires_at

def verify_refresh_token(token: str, user_id: str) -> bool:
    """
    Verify that a refresh token is valid for a given user.
    This doesn't actually verify the token itself (that's done via database lookup)
    but checks that the token is associated with the correct user.
    
    Args:
        token: The refresh token to verify.
        user_id: The user ID that should be associated with the token.
        
    Returns:
        True if valid, False otherwise.
    """
    # This is a placeholder. In practice, this would check the token in the database.
    # The actual implementation will be in the crud module that handles database operations.
    return True

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: The plain-text password to verify.
        hashed_password: The hashed password to compare against.
        
    Returns:
        True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: The plain-text password to hash.
        
    Returns:
        The hashed password.
    """
    return pwd_context.hash(password)
