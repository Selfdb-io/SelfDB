from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func

from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate
from ..core.security import get_password_hash, verify_password

async def get_user(db: AsyncSession, user_id: str) -> Optional[User]:
    """
    Get a user by ID.
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get a user by email.
    """
    # Execute the query without keeping transaction open
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    
    # If this is a standalone transaction (not part of a larger one), commit it
    if db.in_transaction() and not db.in_nested_transaction():
        await db.commit()
        
    return user

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """
    Get multiple users with pagination.
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

async def count_regular_users(db: AsyncSession) -> int:
    """
    Get the total count of regular users (excluding superusers).
    """
    result = await db.execute(
        select(func.count(User.id)).filter(User.is_superuser == False)
    )
    return result.scalar() or 0

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """
    Create a new user.
    """
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active,
        is_superuser=user_in.is_superuser,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user(db: AsyncSession, user_id: str, user_in: UserUpdate) -> Optional[User]:
    """
    Update a user.
    """
    user = await get_user(db, user_id)
    if not user:
        return None
    
    update_data = user_in.dict(exclude_unset=True)
    
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    return user

async def change_user_password(db: AsyncSession, user: User, current_password: str, new_password: str) -> bool:
    """
    Change a user's password by verifying the current password first.
    """
    if not verify_password(current_password, user.hashed_password):
        return False
    
    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    return True

async def delete_user(db: AsyncSession, user_id: str) -> bool:
    """
    Delete a user.
    """
    user = await get_user(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.
    """
    # Use a transaction to ensure it's committed or rolled back
    async with db.begin():
        user = await get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        # Transaction will be committed when this block exits
    return user
