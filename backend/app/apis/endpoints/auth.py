from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.security import create_access_token
from ...schemas.token import TokenWithUserInfo, RefreshTokenRequest, Token
from ...schemas.user import User, UserCreate
from ...crud.user import authenticate_user, create_user, get_user_by_email
from ...crud.refresh_token import create_refresh_token_db, get_refresh_token, revoke_refresh_token
from ..deps import get_db

router = APIRouter()

@router.post("/login", response_model=TokenWithUserInfo)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    Also returns basic user info including superuser status.
    """
    user = await authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Create access token
    access_token = create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token, _ = await create_refresh_token_db(db, user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "is_superuser": user.is_superuser,
        "email": user.email,
        "user_id": str(user.id)
    }

@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get a new access token using a refresh token.
    """
    # Get refresh token from database
    db_token = await get_refresh_token(db, refresh_request.refresh_token)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get associated user
    result = await db.execute(f"SELECT email FROM users WHERE id = '{db_token.user_id}'")
    user_email = result.scalar_one_or_none()
    
    if not user_email:
        # Revoke the token if user doesn't exist
        await revoke_refresh_token(db, refresh_request.refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    return {
        "access_token": create_access_token(
            subject=user_email, 
            expires_delta=access_token_expires
        ),
        "token_type": "bearer"
    }

@router.post("/register", response_model=User)
async def register_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Register a new user.
    """
    user = await get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists.",
        )
    user = await create_user(db, user_in=user_in)
    return user
