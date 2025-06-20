from typing import Generator, AsyncGenerator, Optional, Union, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import jwt, JWTError
from pydantic import ValidationError
import time

from ..services.storage_service import StorageServiceClient

from ..db.session import AsyncSessionLocal
from ..core.config import settings
from ..schemas.token import TokenPayload
from ..models.user import User
from ..crud.user import get_user_by_email

# Constant for anonymous user role
ANON_USER_ROLE = "anon"

# Asynchronous dependency to get a DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an asynchronous database session.
    Ensures the session is closed after the request is finished.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

# API Key header scheme for anonymous access
api_key_header = APIKeyHeader(name="apikey", auto_error=False)

# Dependency to get the current user from a JWT token
async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """
    Validates the JWT token and returns the current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenPayload(sub=email)
    except (JWTError, ValidationError):
        raise credentials_exception

    user = await get_user_by_email(db, email=token_data.sub)
    if user is None:
        raise credentials_exception
    return user

# Dependency to get the current user or anonymous user
async def get_current_user_or_anon(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> Union[User, Literal["anon"], None]:
    """
    Validates the JWT token or API key and returns:
    - User object if valid JWT token
    - "anon" string if valid API key
    - None if neither is valid
    """
    # First try JWT token authentication
    if token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            email: str = payload.get("sub")
            if email is None:
                return None
            token_data = TokenPayload(sub=email)

            user = await get_user_by_email(db, email=token_data.sub)
            if user and user.is_active:
                return user
        except (JWTError, ValidationError):
            pass

    # Then try API key authentication
    if api_key and settings.ANON_KEY and api_key == settings.ANON_KEY:
        return ANON_USER_ROLE

    # If neither authentication method worked
    return None

# Dependency to get the current active user
async def get_current_active_user(
    current_user_or_anon: Union[User, Literal["anon"], None] = Depends(get_current_user_or_anon),
) -> User:
    """
    Checks if the current user is active and not anonymous.
    """
    if current_user_or_anon is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if current_user_or_anon == ANON_USER_ROLE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication with user credentials required for this endpoint",
        )

    if not current_user_or_anon.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return current_user_or_anon

# Dependency to get the current active superuser
async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Checks if the current user is a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


async def get_storage_service_client(current_user: Optional[User] = Depends(get_current_active_user)) -> StorageServiceClient:
    """
    Returns a configured storage service client.
    This replaces the MinIO client dependency.
    """
    token = None
    if current_user:
        # Generate a JWT token for the user to authenticate with the storage service
        token_data = {
            "sub": str(current_user.id),
            "exp": int(time.time() + 3600)  # 1 hour expiry
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    client = StorageServiceClient(
        base_url=settings.STORAGE_SERVICE_URL,
        token=token,
        anon_key=settings.ANON_KEY
    )
    
    try:
        yield client
    finally:
        await client.close()

async def get_storage_service_client_anon() -> StorageServiceClient:
    """
    Returns a storage service client with anonymous access.
    """
    client = StorageServiceClient(
        base_url=settings.STORAGE_SERVICE_URL,
        anon_key=settings.ANON_KEY
    )
    
    try:
        yield client
    finally:
        await client.close()
