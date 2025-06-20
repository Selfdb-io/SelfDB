from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.refresh_token import RefreshToken
from ..core.security import create_refresh_token

async def create_refresh_token_db(db: AsyncSession, user_id: UUID) -> tuple[str, datetime]:
    """
    Create a new refresh token for a user and store it in the database.
    
    Args:
        db: Database session
        user_id: UUID of the user to create a token for
        
    Returns:
        Tuple of (token string, expiration datetime)
    """
    # Generate a new refresh token
    token_str, expires_at = create_refresh_token(user_id)
    
    # Create the database record
    db_refresh_token = RefreshToken(
        token=token_str,
        expires_at=expires_at,
        user_id=user_id
    )
    
    # Add to database
    db.add(db_refresh_token)
    await db.commit()
    await db.refresh(db_refresh_token)
    
    return token_str, expires_at

async def get_refresh_token(db: AsyncSession, token: str) -> Optional[RefreshToken]:
    """
    Retrieve a refresh token from the database by token string.
    
    Args:
        db: Database session
        token: The refresh token string
        
    Returns:
        The RefreshToken object if found and valid, None otherwise
    """
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token == token)
        .where(RefreshToken.revoked == False)
        .where(RefreshToken.expires_at > datetime.utcnow())
    )
    return result.scalars().first()

async def revoke_refresh_token(db: AsyncSession, token: str) -> bool:
    """
    Revoke a refresh token so it can no longer be used.
    
    Args:
        db: Database session
        token: The refresh token string
        
    Returns:
        True if token was found and revoked, False otherwise
    """
    db_token = await get_refresh_token(db, token)
    if not db_token:
        return False
    
    # Mark as revoked
    db_token.revoked = True
    await db.commit()
    await db.refresh(db_token)
    
    return True

async def revoke_all_user_tokens(db: AsyncSession, user_id: UUID) -> int:
    """
    Revoke all refresh tokens for a specific user.
    Useful for forced logout on all devices or after password change.
    
    Args:
        db: Database session
        user_id: UUID of the user
        
    Returns:
        Number of tokens revoked
    """
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.user_id == user_id)
        .where(RefreshToken.revoked == False)
        .where(RefreshToken.expires_at > datetime.utcnow())
    )
    tokens = result.scalars().all()
    
    count = 0
    for token in tokens:
        token.revoked = True
        count += 1
    
    await db.commit()
    return count 